"""
Custom User model and related models for authentication.
"""

import uuid
import random
import string
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


def generate_verification_code():
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)


def user_profile_pic_path(instance, filename):
    """Generate file path for user profile pictures."""
    ext = filename.split('.')[-1]
    filename = f'{instance.id}_{uuid.uuid4().hex[:8]}.{ext}'
    return f'profile_pics/{filename}'


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model with email authentication."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(13), MaxValueValidator(150)]
    )
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = models.ImageField(
        upload_to=user_profile_pic_path, 
        null=True, 
        blank=True
    )
    
    # Account status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    # User preferences
    theme = models.CharField(
        max_length=10, 
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='dark'
    )
    chat_background = models.CharField(max_length=50, default='default')
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']
    
    class Meta:
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.username
    
    def get_display_name(self):
        return self.name or self.username
    
    def update_last_seen(self):
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])
    
    @property
    def is_online(self):
        """Check if user was active in the last 5 minutes."""
        if self.last_seen:
            return (timezone.now() - self.last_seen).total_seconds() < 300
        return False


class EmailVerification(models.Model):
    """Model for email verification codes."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    code = models.CharField(max_length=6, default=generate_verification_code)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=1)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Verification for {self.user.email}"


class LoginLink(models.Model):
    """Model for passwordless login links."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_links')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Login link for {self.user.email}"


class ActivityLog(models.Model):
    """Model for tracking user activity (for admin)."""
    
    ACTION_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('signup', 'User Signup'),
        ('password_change', 'Password Changed'),
        ('profile_update', 'Profile Updated'),
        ('message_sent', 'Message Sent'),
        ('file_upload', 'File Uploaded'),
        ('account_deleted', 'Account Deleted'),
        ('chat_created', 'Chat Created'),
        ('group_created', 'Group Created'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='activity_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.action} at {self.created_at}"


class DataDeletionRequest(models.Model):
    """Model for tracking user data deletion requests."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deletion_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Deletion request by {self.user.email} - {self.status}"
