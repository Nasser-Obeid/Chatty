"""
API views for chat functionality.
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Max
from django.shortcuts import get_object_or_404

from .models import Conversation, Message, AIBot
from .serializers import ConversationSerializer, MessageSerializer, UserSerializer
from accounts.models import User


class ConversationListAPIView(generics.ListAPIView):
    """List all conversations for the authenticated user."""
    
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user,
            conversation_participants__is_archived=False
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time')


class ConversationDetailAPIView(generics.RetrieveAPIView):
    """Get details of a specific conversation."""
    
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)


class MessageListAPIView(generics.ListAPIView):
    """List messages in a conversation."""
    
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=self.request.user
        )
        return conversation.messages.select_related('sender').order_by('-created_at')[:50]


class UserSearchAPIView(APIView):
    """Search for users."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return Response({'users': []})
        
        users = User.objects.filter(
            is_active=True,
            is_verified=True
        ).exclude(
            id=request.user.id
        ).filter(
            Q(username__icontains=query) | Q(name__icontains=query)
        )[:10]
        
        serializer = UserSerializer(users, many=True)
        return Response({'users': serializer.data})


class OnlineUsersAPIView(APIView):
    """Get list of online users."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get users from user's conversations who are online
        conversation_users = User.objects.filter(
            conversations__in=request.user.conversations.all()
        ).exclude(id=request.user.id).distinct()
        
        online_users = [u for u in conversation_users if u.is_online]
        
        serializer = UserSerializer(online_users, many=True)
        return Response({'users': serializer.data})


class AIChatAPIView(APIView):
    """Handle AI chat requests."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Send message to AI and get response."""
        conversation_id = request.data.get('conversation_id')
        message = request.data.get('message', '').strip()
        
        if not conversation_id or not message:
            return Response(
                {'error': 'conversation_id and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=request.user,
            conversation_type='ai'
        )
        
        # Save user message
        user_message = Message(
            conversation=conversation,
            sender=request.user,
            message_type='text',
        )
        user_message.content = message
        user_message.save()
        
        # Generate AI response (placeholder - integrate with actual AI API)
        ai_response = self.generate_ai_response(message, conversation)
        
        # Save AI response
        ai_message = Message(
            conversation=conversation,
            sender=None,
            message_type='ai',
        )
        ai_message.content = ai_response
        ai_message.save()
        
        return Response({
            'user_message': user_message.to_dict(),
            'ai_message': ai_message.to_dict(),
        })
    
    def generate_ai_response(self, message, conversation):
        """Generate AI response - placeholder for actual AI integration."""
        # This is a placeholder. In production, integrate with:
        # - OpenAI API
        # - Anthropic Claude API
        # - Other AI providers
        
        responses = [
            "That's an interesting thought! Could you tell me more?",
            "I understand. How can I help you with that?",
            "Great question! Let me think about that...",
            "Thanks for sharing. What would you like to explore further?",
        ]
        
        import random
        return random.choice(responses)
