"""
Chat models for messaging functionality.
"""

import uuid
import os
from django.db import models
from django.conf import settings
from django.utils import timezone
from cryptography.fernet import Fernet
import base64
import hashlib


def get_encryption_key():
    """Get or generate encryption key."""
    key = settings.ENCRYPTION_KEY
    # Ensure key is 32 bytes for Fernet
    key_bytes = hashlib.sha256(key.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


def encrypt_message(text):
    """Encrypt message content."""
    if not text:
        return text
    f = Fernet(get_encryption_key())
    return f.encrypt(text.encode()).decode()


def decrypt_message(encrypted_text):
    """Decrypt message content."""
    if not encrypted_text:
        return encrypted_text
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(encrypted_text.encode()).decode()
    except Exception:
        return "[Unable to decrypt message]"


def chat_file_path(instance, filename):
    """Generate file path for chat attachments."""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4().hex}.{ext}'
    return f'chat_files/{instance.conversation.id}/{filename}'


class Conversation(models.Model):
    """Model for chat conversations (both 1-on-1 and groups)."""
    
    CONVERSATION_TYPES = [
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
        ('ai', 'AI Chat'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=True)  # For group chats
    conversation_type = models.CharField(max_length=10, choices=CONVERSATION_TYPES, default='direct')
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ConversationParticipant',
        related_name='conversations'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Group chat specific
    group_image = models.ImageField(upload_to='group_images/', null=True, blank=True)
    description = models.TextField(max_length=500, blank=True)
    
    # AI Chat specific
    ai_model = models.CharField(max_length=50, blank=True)  # e.g., 'gpt-4', 'claude'
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.name:
            return self.name
        if self.conversation_type == 'direct':
            participants = self.participants.all()[:2]
            return f"Chat: {' & '.join([p.username for p in participants])}"
        return f"Conversation {self.id}"
    
    def get_display_name(self, for_user):
        """Get display name for a specific user."""
        if self.name:
            return self.name
        if self.conversation_type == 'direct':
            other = self.participants.exclude(id=for_user.id).first()
            return other.get_display_name() if other else "Unknown"
        return "Group Chat"
    
    def get_other_participant(self, user):
        """Get the other participant in a direct message."""
        if self.conversation_type != 'direct':
            return None
        return self.participants.exclude(id=user.id).first()
    
    def get_last_message(self):
        """Get the most recent message."""
        return self.messages.order_by('-created_at').first()
    
    def get_unread_count(self, user):
        """Get unread message count for user."""
        participant = self.conversation_participants.filter(user=user).first()
        if not participant:
            return 0
        return self.messages.filter(
            created_at__gt=participant.last_read_at
        ).exclude(sender=user).count()
    
    @classmethod
    def get_or_create_direct(cls, user1, user2):
        """Get or create a direct conversation between two users."""
        # Look for existing conversation
        conversations = cls.objects.filter(
            conversation_type='direct',
            participants=user1
        ).filter(
            participants=user2
        )
        
        if conversations.exists():
            return conversations.first(), False
        
        # Create new conversation
        conversation = cls.objects.create(
            conversation_type='direct',
            created_by=user1
        )
        ConversationParticipant.objects.create(conversation=conversation, user=user1)
        ConversationParticipant.objects.create(conversation=conversation, user=user2)
        
        return conversation, True


class ConversationParticipant(models.Model):
    """Through model for conversation participants."""
    
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('admin', 'Admin'),
        ('owner', 'Owner'),
    ]
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='conversation_participants'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_memberships'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(default=timezone.now)
    is_muted = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    nickname = models.CharField(max_length=50, blank=True)  # Custom nickname for this chat
    
    class Meta:
        unique_together = ['conversation', 'user']
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} in {self.conversation}"
    
    def mark_as_read(self):
        """Mark all messages as read."""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])


class Message(models.Model):
    """Model for chat messages with encryption."""
    
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System'),
        ('ai', 'AI Response'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages'
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    
    # Encrypted content
    _content = models.TextField(db_column='content', blank=True)
    
    # File attachment
    file = models.FileField(upload_to=chat_file_path, null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    # Reply to another message
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    class Meta:
        ordering = ['created_at']
    
    @property
    def content(self):
        """Decrypt and return message content."""
        if self.is_deleted:
            return "[Message deleted]"
        return decrypt_message(self._content)
    
    @content.setter
    def content(self, value):
        """Encrypt and store message content."""
        self._content = encrypt_message(value)
    
    def __str__(self):
        return f"Message from {self.sender} at {self.created_at}"
    
    def save(self, *args, **kwargs):
        # Update conversation's updated_at
        if not self.pk:
            self.conversation.updated_at = timezone.now()
            self.conversation.save(update_fields=['updated_at'])
        super().save(*args, **kwargs)
    
    def soft_delete(self):
        """Soft delete the message."""
        self.is_deleted = True
        self._content = ''
        if self.file:
            self.file.delete()
        self.save()
    
    def to_dict(self):
        """Convert message to dictionary for API/WebSocket."""
        data = {
            'id': str(self.id),
            'conversation_id': str(self.conversation.id),
            'sender': {
                'id': str(self.sender.id) if self.sender else None,
                'username': self.sender.username if self.sender else 'System',
                'name': self.sender.get_display_name() if self.sender else 'System',
                'profile_pic': self.sender.profile_pic.url if self.sender and self.sender.profile_pic else None,
            },
            'message_type': self.message_type,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'is_edited': self.is_edited,
            'is_deleted': self.is_deleted,
        }
        
        if self.file:
            data['file'] = {
                'url': self.file.url,
                'name': self.file_name,
                'size': self.file_size,
            }
        
        if self.reply_to:
            data['reply_to'] = {
                'id': str(self.reply_to.id),
                'content': self.reply_to.content[:100],
                'sender': self.reply_to.sender.username if self.reply_to.sender else 'Unknown',
            }
        
        return data


class MessageReadReceipt(models.Model):
    """Track who has read each message."""
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']


class AIBot(models.Model):
    """Model for AI chatbots."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='ai_avatars/', null=True, blank=True)
    model_name = models.CharField(max_length=50)  # e.g., 'claude-3', 'gpt-4'
    system_prompt = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class ChatBackup(models.Model):
    """Model for chat backup requests."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file = models.FileField(upload_to='backups/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"Backup for {self.user.username} - {self.status}"
