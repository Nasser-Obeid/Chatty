"""
URL patterns for chat app.
"""

from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Chat list
    path('', views.chat_list_view, name='chat_list'),
    
    # Individual chat
    path('<uuid:conversation_id>/', views.chat_view, name='chat_room'),
    
    # Start new chats
    path('start/<uuid:user_id>/', views.start_chat_view, name='start_chat'),
    path('create-group/', views.create_group_view, name='create_group'),
    path('ai/<uuid:bot_id>/', views.start_ai_chat_view, name='start_ai_chat'),
    
    # Message actions
    path('<uuid:conversation_id>/send/', views.send_message_view, name='send_message'),
    path('<uuid:conversation_id>/load-more/', views.load_more_messages_view, name='load_more'),
    path('message/<uuid:message_id>/delete/', views.delete_message_view, name='delete_message'),
    path('<uuid:conversation_id>/mark-read/', views.mark_read_view, name='mark_read'),
    
    # Chat management
    path('search/', views.search_chats_view, name='search_chats'),
    path('<uuid:conversation_id>/archive/', views.archive_chat_view, name='archive_chat'),
    path('<uuid:conversation_id>/mute/', views.mute_chat_view, name='mute_chat'),
    
    # Backups
    path('backup/', views.create_backup_view, name='create_backup_all'),
    path('backup/<uuid:conversation_id>/', views.create_backup_view, name='create_backup'),
    path('backup/download/<uuid:backup_id>/', views.download_backup_view, name='download_backup'),
]
