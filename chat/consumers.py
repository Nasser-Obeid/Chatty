"""
WebSocket consumers for real-time chat functionality.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chat functionality."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Verify user is participant
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user's online status
        await self.update_user_status(online=True)
        
        # Notify others that user is online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'is_online': True,
            }
        )
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            # Notify others that user went offline
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'is_online': False,
                }
            )
            
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        # Update user's online status
        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.update_user_status(online=False)
    
    async def receive(self, text_data):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read':
                await self.handle_read(data)
            elif message_type == 'delete':
                await self.handle_delete(data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def handle_message(self, data):
        """Handle new message."""
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to')
        
        if not content:
            return
        
        # Save message to database
        message = await self.save_message(content, reply_to_id)
        
        if message:
            # Broadcast to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                }
            )
    
    async def handle_typing(self, data):
        """Handle typing indicator."""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'is_typing': is_typing,
            }
        )
    
    async def handle_read(self, data):
        """Handle read receipt."""
        message_id = data.get('message_id')
        
        if message_id:
            await self.mark_message_read(message_id)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'user_id': str(self.user.id),
                    'message_id': message_id,
                }
            )
    
    async def handle_delete(self, data):
        """Handle message deletion."""
        message_id = data.get('message_id')
        
        if message_id:
            success = await self.delete_message(message_id)
            
            if success:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_deleted',
                        'message_id': message_id,
                    }
                )
    
    # Event handlers for group messages
    
    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send to the user who is typing
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))
    
    async def user_status(self, event):
        """Send user status update to WebSocket."""
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'status',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_online': event['is_online'],
            }))
    
    async def read_receipt(self, event):
        """Send read receipt to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'read',
            'user_id': event['user_id'],
            'message_id': event['message_id'],
        }))
    
    async def message_deleted(self, event):
        """Send message deletion notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'deleted',
            'message_id': event['message_id'],
        }))
    
    # Database operations
    
    @database_sync_to_async
    def check_participant(self):
        """Check if user is a participant in the conversation."""
        from .models import Conversation
        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.user
        ).exists()
    
    @database_sync_to_async
    def save_message(self, content, reply_to_id=None):
        """Save message to database."""
        from .models import Conversation, Message
        
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            message = Message(
                conversation=conversation,
                sender=self.user,
                message_type='text',
            )
            message.content = content
            
            if reply_to_id:
                try:
                    message.reply_to = Message.objects.get(
                        id=reply_to_id,
                        conversation=conversation
                    )
                except Message.DoesNotExist:
                    pass
            
            message.save()
            
            return message.to_dict()
        except Conversation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark a message as read."""
        from .models import Message, MessageReadReceipt
        
        try:
            message = Message.objects.get(id=message_id)
            MessageReadReceipt.objects.get_or_create(
                message=message,
                user=self.user
            )
            return True
        except Message.DoesNotExist:
            return False
    
    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete a message."""
        from .models import Message
        
        try:
            message = Message.objects.get(
                id=message_id,
                sender=self.user
            )
            message.soft_delete()
            return True
        except Message.DoesNotExist:
            return False
    
    @database_sync_to_async
    def update_user_status(self, online=True):
        """Update user's last seen status."""
        if online:
            self.user.update_last_seen()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for user notifications."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_group_name = f'user_{self.user.id}'
        
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def new_message(self, event):
        """Notify user of new message."""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'conversation_id': event['conversation_id'],
            'message': event['message'],
        }))
    
    async def conversation_update(self, event):
        """Notify user of conversation update."""
        await self.send(text_data=json.dumps({
            'type': 'conversation_update',
            'conversation_id': event['conversation_id'],
            'update_type': event['update_type'],
        }))
