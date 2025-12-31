"""
URL patterns for core app.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.settings_view, name='settings'),
    path('appearance/', views.appearance_settings_view, name='appearance'),
    path('profile/', views.profile_settings_view, name='profile'),
    path('security/', views.security_settings_view, name='security'),
    path('privacy/', views.privacy_settings_view, name='privacy'),
    path('delete-account/', views.delete_account_view, name='delete_account'),
    path('update-theme/', views.update_theme_view, name='update_theme'),
]
