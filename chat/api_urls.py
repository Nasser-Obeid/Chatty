"""
API URL patterns for chat app.
"""

from django.urls import path
from . import api_views

app_name = 'api'

urlpatterns = [
    # Messages API
    path('conversations/', api_views.ConversationListAPIView.as_view(), name='conversations'),
    path('conversations/<uuid:pk>/', api_views.ConversationDetailAPIView.as_view(), name='conversation_detail'),
    path('conversations/<uuid:conversation_id>/messages/', api_views.MessageListAPIView.as_view(), name='messages'),
    
    # Users API
    path('users/search/', api_views.UserSearchAPIView.as_view(), name='user_search'),
    path('users/online/', api_views.OnlineUsersAPIView.as_view(), name='online_users'),
    
    # AI Chat API
    path('ai/chat/', api_views.AIChatAPIView.as_view(), name='ai_chat'),
]
