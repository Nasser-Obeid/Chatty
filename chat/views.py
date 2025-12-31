"""
Views for chat functionality.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q, Max, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.conf import settings

from .models import (
    Conversation, ConversationParticipant, Message, 
    AIBot, ChatBackup, MessageReadReceipt
)
from accounts.models import User
from accounts.views import log_activity


@login_required
def chat_list_view(request):
    """Display list of all conversations for the user."""
    # Get user's conversations with latest message info
    conversations = Conversation.objects.filter(
        participants=request.user,
        conversation_participants__is_archived=False
    ).annotate(
        last_message_time=Max('messages__created_at')
    ).order_by('-last_message_time', '-updated_at')
    
    # Add metadata for each conversation
    chat_data = []
    for conv in conversations:
        participant = conv.conversation_participants.get(user=request.user)
        last_msg = conv.get_last_message()
        
        chat_data.append({
            'conversation': conv,
            'display_name': conv.get_display_name(request.user),
            'other_user': conv.get_other_participant(request.user),
            'last_message': last_msg,
            'unread_count': conv.get_unread_count(request.user),
            'is_muted': participant.is_muted,
        })
    
    # Get AI bots for sidebar
    ai_bots = AIBot.objects.filter(is_active=True)
    
    return render(request, 'chat/chat_list.html', {
        'chats': chat_data,
        'ai_bots': ai_bots,
    })


@login_required
def chat_view(request, conversation_id):
    """Display a specific conversation."""
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related('participants'),
        id=conversation_id,
        participants=request.user
    )
    
    # Mark as read
    participant = conversation.conversation_participants.get(user=request.user)
    participant.mark_as_read()
    
    # Get messages with pagination
    messages_qs = conversation.messages.select_related('sender').order_by('-created_at')
    paginator = Paginator(messages_qs, 50)
    page = request.GET.get('page', 1)
    messages_page = paginator.get_page(page)
    
    # Get all user conversations for sidebar
    all_conversations = Conversation.objects.filter(
        participants=request.user,
        conversation_participants__is_archived=False
    ).annotate(
        last_message_time=Max('messages__created_at')
    ).order_by('-last_message_time')[:20]
    
    sidebar_chats = []
    for conv in all_conversations:
        sidebar_chats.append({
            'conversation': conv,
            'display_name': conv.get_display_name(request.user),
            'other_user': conv.get_other_participant(request.user),
            'last_message': conv.get_last_message(),
            'unread_count': conv.get_unread_count(request.user),
            'is_active': conv.id == conversation.id,
        })
    
    return render(request, 'chat/chat_room.html', {
        'conversation': conversation,
        'chat_messages': reversed(list(messages_page)),
        'has_more': messages_page.has_next(),
        'other_user': conversation.get_other_participant(request.user),
        'sidebar_chats': sidebar_chats,
        'participant': participant,
    })


@login_required
def start_chat_view(request, user_id):
    """Start a new direct conversation with a user."""
    other_user = get_object_or_404(User, id=user_id, is_active=True)
    
    if other_user == request.user:
        messages.error(request, "You can't start a chat with yourself.")
        return redirect('chat:chat_list')
    
    conversation, created = Conversation.get_or_create_direct(request.user, other_user)
    
    if created:
        log_activity(request.user, 'chat_created', request, {
            'with_user': str(other_user.id)
        })
    
    return redirect('chat:chat_room', conversation_id=conversation.id)


@login_required
def create_group_view(request):
    """Create a new group chat."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        participant_ids = request.POST.getlist('participants')
        
        if not name:
            return JsonResponse({'error': 'Group name is required'}, status=400)
        
        if len(participant_ids) < 1:
            return JsonResponse({'error': 'Select at least one participant'}, status=400)
        
        # Create group conversation
        conversation = Conversation.objects.create(
            name=name,
            description=description,
            conversation_type='group',
            created_by=request.user
        )
        
        # Handle group image
        if 'group_image' in request.FILES:
            conversation.group_image = request.FILES['group_image']
            conversation.save()
        
        # Add creator as owner
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=request.user,
            role='owner'
        )
        
        # Add participants
        for user_id in participant_ids:
            try:
                user = User.objects.get(id=user_id, is_active=True)
                if user != request.user:
                    ConversationParticipant.objects.create(
                        conversation=conversation,
                        user=user,
                        role='member'
                    )
            except User.DoesNotExist:
                continue
        
        # Create system message
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            message_type='system',
            content=f'{request.user.get_display_name()} created the group "{name}"'
        )
        
        log_activity(request.user, 'group_created', request, {
            'group_id': str(conversation.id),
            'group_name': name
        })
        
        return JsonResponse({
            'success': True,
            'conversation_id': str(conversation.id)
        })
    
    # GET request - show form
    return render(request, 'chat/create_group.html')


@login_required
def start_ai_chat_view(request, bot_id):
    """Start a chat with an AI bot."""
    bot = get_object_or_404(AIBot, id=bot_id, is_active=True)
    
    # Check for existing AI conversation
    existing = Conversation.objects.filter(
        conversation_type='ai',
        created_by=request.user,
        ai_model=bot.model_name
    ).first()
    
    if existing:
        return redirect('chat:chat_room', conversation_id=existing.id)
    
    # Create new AI conversation
    conversation = Conversation.objects.create(
        name=f"Chat with {bot.name}",
        conversation_type='ai',
        created_by=request.user,
        ai_model=bot.model_name
    )
    
    ConversationParticipant.objects.create(
        conversation=conversation,
        user=request.user,
        role='owner'
    )
    
    # Add welcome message from AI
    Message.objects.create(
        conversation=conversation,
        sender=None,  # AI messages have no sender
        message_type='ai',
        content=f"Hello! I'm {bot.name}. How can I help you today?"
    )
    
    return redirect('chat:chat_room', conversation_id=conversation.id)


@login_required
@require_POST
def send_message_view(request, conversation_id):
    """Send a message in a conversation."""
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    content = request.POST.get('content', '').strip()
    reply_to_id = request.POST.get('reply_to')
    
    # Handle file upload
    file = request.FILES.get('file')
    
    if not content and not file:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)
    
    # Create message
    message = Message(
        conversation=conversation,
        sender=request.user,
        message_type='text' if not file else ('image' if file.content_type.startswith('image/') else 'file')
    )
    
    if content:
        message.content = content
    
    if file:
        message.file = file
        message.file_name = file.name
        message.file_size = file.size
    
    if reply_to_id:
        try:
            message.reply_to = Message.objects.get(
                id=reply_to_id,
                conversation=conversation
            )
        except Message.DoesNotExist:
            pass
    
    message.save()
    
    log_activity(request.user, 'message_sent', request)
    if file:
        log_activity(request.user, 'file_upload', request, {'file_name': file.name})
    
    return JsonResponse({
        'success': True,
        'message': message.to_dict()
    })


@login_required
def load_more_messages_view(request, conversation_id):
    """Load more messages for infinite scroll."""
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    before_id = request.GET.get('before')
    limit = int(request.GET.get('limit', 50))
    
    messages_qs = conversation.messages.select_related('sender').order_by('-created_at')
    
    if before_id:
        try:
            before_msg = Message.objects.get(id=before_id)
            messages_qs = messages_qs.filter(created_at__lt=before_msg.created_at)
        except Message.DoesNotExist:
            pass
    
    messages_qs = messages_qs[:limit]
    
    return JsonResponse({
        'messages': [m.to_dict() for m in reversed(list(messages_qs))],
        'has_more': messages_qs.count() == limit
    })


@login_required
@require_POST
def delete_message_view(request, message_id):
    """Delete a message."""
    message = get_object_or_404(Message, id=message_id)
    
    # Check permission
    if message.sender != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    message.soft_delete()
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_read_view(request, conversation_id):
    """Mark conversation as read."""
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    participant = conversation.conversation_participants.get(user=request.user)
    participant.mark_as_read()
    
    return JsonResponse({'success': True})


@login_required
def search_chats_view(request):
    """Search through conversations and messages."""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Search in conversation names and participants
    conversations = Conversation.objects.filter(
        participants=request.user
    ).filter(
        Q(name__icontains=query) |
        Q(participants__username__icontains=query) |
        Q(participants__name__icontains=query)
    ).distinct()[:10]
    
    results = []
    for conv in conversations:
        results.append({
            'type': 'conversation',
            'id': str(conv.id),
            'name': conv.get_display_name(request.user),
            'conversation_type': conv.conversation_type,
        })
    
    return JsonResponse({'results': results})


@login_required
def archive_chat_view(request, conversation_id):
    """Archive a conversation."""
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    participant = conversation.conversation_participants.get(user=request.user)
    participant.is_archived = not participant.is_archived
    participant.save()
    
    return JsonResponse({
        'success': True,
        'is_archived': participant.is_archived
    })


@login_required
def mute_chat_view(request, conversation_id):
    """Mute/unmute a conversation."""
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        participants=request.user
    )
    
    participant = conversation.conversation_participants.get(user=request.user)
    participant.is_muted = not participant.is_muted
    participant.save()
    
    return JsonResponse({
        'success': True,
        'is_muted': participant.is_muted
    })


@login_required
def create_backup_view(request, conversation_id=None):
    """Create a chat backup."""
    if conversation_id:
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=request.user
        )
    else:
        conversation = None
    
    # Create backup request
    backup = ChatBackup.objects.create(
        user=request.user,
        conversation=conversation
    )
    
    # Process backup (in production, this would be a background task)
    try:
        import json
        from io import BytesIO
        
        if conversation:
            messages_qs = conversation.messages.all()
            data = {
                'conversation': {
                    'id': str(conversation.id),
                    'name': conversation.get_display_name(request.user),
                    'type': conversation.conversation_type,
                },
                'messages': [m.to_dict() for m in messages_qs]
            }
        else:
            # Backup all conversations
            data = {'conversations': []}
            for conv in request.user.conversations.all():
                conv_data = {
                    'conversation': {
                        'id': str(conv.id),
                        'name': conv.get_display_name(request.user),
                        'type': conv.conversation_type,
                    },
                    'messages': [m.to_dict() for m in conv.messages.all()]
                }
                data['conversations'].append(conv_data)
        
        # Create JSON file
        json_content = json.dumps(data, indent=2, default=str)
        
        from django.core.files.base import ContentFile
        filename = f'backup_{request.user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
        backup.file.save(filename, ContentFile(json_content.encode()))
        
        backup.status = 'completed'
        backup.completed_at = timezone.now()
        backup.save()
        
    except Exception as e:
        backup.status = 'failed'
        backup.error_message = str(e)
        backup.save()
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({
        'success': True,
        'backup_id': str(backup.id),
        'download_url': backup.file.url if backup.file else None
    })


@login_required
def download_backup_view(request, backup_id):
    """Download a chat backup."""
    backup = get_object_or_404(
        ChatBackup,
        id=backup_id,
        user=request.user,
        status='completed'
    )
    
    if not backup.file:
        return JsonResponse({'error': 'Backup file not found'}, status=404)
    
    return FileResponse(
        backup.file.open('rb'),
        as_attachment=True,
        filename=backup.file.name.split('/')[-1]
    )
