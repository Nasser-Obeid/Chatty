"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, EmailVerification, LoginLink, ActivityLog, DataDeletionRequest


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""
    
    list_display = [
        'username', 'email', 'name', 'is_verified', 'is_active', 
        'is_staff', 'date_joined', 'last_seen_display'
    ]
    list_filter = ['is_verified', 'is_active', 'is_staff', 'theme', 'date_joined']
    search_fields = ['username', 'email', 'name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('username', 'name', 'age', 'bio', 'profile_pic')}),
        ('Preferences', {'fields': ('theme', 'chat_background')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'last_seen')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login', 'last_seen']
    
    def last_seen_display(self, obj):
        if obj.is_online:
            return format_html('<span style="color: green;">● Online</span>')
        return obj.last_seen.strftime('%Y-%m-%d %H:%M') if obj.last_seen else 'Never'
    last_seen_display.short_description = 'Last Seen'


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Admin for email verifications."""
    
    list_display = ['user', 'code', 'created_at', 'expires_at', 'is_used', 'status']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['code', 'created_at']
    
    def status(self, obj):
        if obj.is_used:
            return format_html('<span style="color: gray;">Used</span>')
        elif obj.is_valid:
            return format_html('<span style="color: green;">Valid</span>')
        return format_html('<span style="color: red;">Expired</span>')


@admin.register(LoginLink)
class LoginLinkAdmin(admin.ModelAdmin):
    """Admin for login links."""
    
    list_display = ['user', 'created_at', 'expires_at', 'is_used', 'status']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['token', 'created_at']
    
    def status(self, obj):
        if obj.is_used:
            return format_html('<span style="color: gray;">Used</span>')
        elif obj.is_valid:
            return format_html('<span style="color: green;">Valid</span>')
        return format_html('<span style="color: red;">Expired</span>')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin for activity logs."""
    
    list_display = ['user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email', 'user__username', 'ip_address']
    readonly_fields = ['user', 'action', 'details', 'ip_address', 'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(admin.ModelAdmin):
    """Admin for data deletion requests."""
    
    list_display = ['user', 'status', 'requested_at', 'processed_at']
    list_filter = ['status', 'requested_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['user', 'reason', 'requested_at']
    
    actions = ['process_deletion', 'cancel_deletion']
    
    def process_deletion(self, request, queryset):
        for deletion_request in queryset.filter(status='pending'):
            user = deletion_request.user
            user.delete()
            deletion_request.status = 'completed'
            deletion_request.processed_at = timezone.now()
            deletion_request.save()
        self.message_user(request, f'Processed {queryset.count()} deletion requests.')
    process_deletion.short_description = 'Process selected deletion requests'
    
    def cancel_deletion(self, request, queryset):
        queryset.update(status='cancelled')
        # Reactivate users
        for dr in queryset:
            dr.user.is_active = True
            dr.user.save()
        self.message_user(request, f'Cancelled {queryset.count()} deletion requests.')
    cancel_deletion.short_description = 'Cancel selected deletion requests'


from django.utils import timezone
