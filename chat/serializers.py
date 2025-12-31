"""
Serializers for chat API.
"""

from rest_framework import serializers
from .models import Conversation, Message, ConversationParticipant
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    is_online = serializers.SerializerMethodField()
    profile_pic_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'bio', 'profile_pic_url', 'is_online']
    
    def get_is_online(self, obj):
        return obj.is_online
    
    def get_profile_pic_url(self, obj):
        if obj.profile_pic:
            return obj.profile_pic.url
        return None


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""
    
    sender = UserSerializer(read_only=True)
    content = serializers.CharField(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'message_type', 'content',
            'file_url', 'file_name', 'file_size', 'created_at',
            'is_edited', 'is_deleted', 'reply_to'
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model."""
    
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'name', 'conversation_type', 'participants',
            'created_at', 'updated_at', 'last_message', 'unread_count',
            'display_name', 'group_image', 'description'
        ]
    
    def get_last_message(self, obj):
        message = obj.get_last_message()
        if message:
            return MessageSerializer(message).data
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_display_name(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_display_name(request.user)
        return obj.name or "Chat"
