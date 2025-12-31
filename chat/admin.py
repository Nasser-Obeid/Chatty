"""
Admin configuration for chat app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Conversation, ConversationParticipant, Message,
    MessageReadReceipt, AIBot, ChatBackup
)


class ConversationParticipantInline(admin.TabularInline):
    """Inline admin for conversation participants."""
    
    model = ConversationParticipant
    extra = 0
    readonly_fields = ['joined_at', 'last_read_at']


class MessageInline(admin.TabularInline):
    """Inline admin for messages."""
    
    model = Message
    extra = 0
    readonly_fields = ['id', 'sender', 'message_type', 'created_at']
    fields = ['sender', 'message_type', 'created_at', 'is_deleted']
    can_delete = False
    max_num = 10
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin for conversations."""
    
    list_display = [
        'id', 'name', 'conversation_type', 'participant_count',
        'message_count', 'created_at', 'updated_at'
    ]
    list_filter = ['conversation_type', 'created_at']
    search_fields = ['name', 'participants__username', 'participants__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ConversationParticipantInline, MessageInline]
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin for messages."""
    
    list_display = [
        'id', 'conversation_link', 'sender', 'message_type',
        'content_preview', 'created_at', 'is_deleted'
    ]
    list_filter = ['message_type', 'is_deleted', 'created_at']
    search_fields = ['sender__username', 'sender__email', '_content']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def conversation_link(self, obj):
        return format_html(
            '<a href="/admin/chat/conversation/{}/change/">{}</a>',
            obj.conversation.id,
            str(obj.conversation)[:30]
        )
    conversation_link.short_description = 'Conversation'
    
    def content_preview(self, obj):
        content = obj.content
        if len(content) > 50:
            return content[:50] + '...'
        return content
    content_preview.short_description = 'Content'
    
    actions = ['delete_messages']
    
    def delete_messages(self, request, queryset):
        for message in queryset:
            message.soft_delete()
        self.message_user(request, f'Deleted {queryset.count()} messages.')
    delete_messages.short_description = 'Soft delete selected messages'


@admin.register(AIBot)
class AIBotAdmin(admin.ModelAdmin):
    """Admin for AI bots."""
    
    list_display = ['name', 'model_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'model_name']
    search_fields = ['name', 'description']


@admin.register(ChatBackup)
class ChatBackupAdmin(admin.ModelAdmin):
    """Admin for chat backups."""
    
    list_display = ['user', 'conversation', 'status', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'completed_at']
