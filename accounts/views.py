"""
Views for user authentication, registration, and profile management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.template.loader import render_to_string

from .models import EmailVerification, LoginLink, ActivityLog
from .forms import (
    SignUpForm, LoginForm, EmailLoginForm, VerificationCodeForm,
    ProfileUpdateForm, PasswordChangeForm, DeleteAccountForm
)

User = get_user_model()


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_activity(user, action, request=None, details=None):
    """Log user activity."""
    ActivityLog.objects.create(
        user=user,
        action=action,
        details=details or {},
        ip_address=get_client_ip(request) if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
    )


def signup_view(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect('chat:chat_list')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create verification code
            verification = EmailVerification.objects.create(user=user)
            
            # Send verification email
            subject = 'Verify your Chatty account'
            message = f'''
Welcome to Chatty!

Your verification code is: {verification.code}

This code will expire in 1 hour.

If you didn't create this account, please ignore this email.
            '''
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                # In development, just log the code
                print(f"Verification code for {user.email}: {verification.code}")
            
            # Store user ID in session for verification
            request.session['pending_verification_user'] = str(user.id)
            
            log_activity(user, 'signup', request)
            
            return redirect('accounts:verify_email')
    else:
        form = SignUpForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


def verify_email_view(request):
    """Handle email verification."""
    user_id = request.session.get('pending_verification_user')
    if not user_id:
        messages.error(request, 'No pending verification found.')
        return redirect('accounts:signup')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            verification = EmailVerification.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).first()
            
            if verification and verification.is_valid:
                verification.is_used = True
                verification.save()
                
                user.is_verified = True
                user.save()
                
                # Clear session
                del request.session['pending_verification_user']
                
                # Log user in
                login(request, user)
                messages.success(request, 'Email verified successfully! Welcome to Messenger.')
                
                return redirect('chat:chat_list')
            else:
                messages.error(request, 'Invalid or expired verification code.')
    else:
        form = VerificationCodeForm()
    
    return render(request, 'accounts/verify_email.html', {
        'form': form,
        'email': user.email
    })


def resend_verification_view(request):
    """Resend verification code."""
    user_id = request.session.get('pending_verification_user')
    if not user_id:
        return JsonResponse({'error': 'No pending verification'}, status=400)
    
    user = get_object_or_404(User, id=user_id)
    
    # Invalidate old codes
    EmailVerification.objects.filter(user=user, is_used=False).update(is_used=True)
    
    # Create new verification
    verification = EmailVerification.objects.create(user=user)
    
    # Send email
    try:
        send_mail(
            'Your new verification code',
            f'Your new verification code is: {verification.code}\n\nThis code expires in 1 hour.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        print(f"New verification code for {user.email}: {verification.code}")
    
    return JsonResponse({'success': True, 'message': 'New code sent!'})


def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('chat:chat_list')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if not user.is_verified:
                    # Send to verification
                    request.session['pending_verification_user'] = str(user.id)
                    verification = EmailVerification.objects.create(user=user)
                    print(f"Verification code for {user.email}: {verification.code}")
                    messages.info(request, 'Please verify your email first.')
                    return redirect('accounts:verify_email')
                
                login(request, user)
                
                if not remember_me:
                    request.session.set_expiry(0)
                
                log_activity(user, 'login', request)
                user.update_last_seen()
                
                return redirect('chat:chat_list')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def email_login_view(request):
    """Handle passwordless email login."""
    if request.user.is_authenticated:
        return redirect('chat:chat_list')
    
    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Create login link
            login_link = LoginLink.objects.create(user=user)
            
            # Build login URL
            login_url = request.build_absolute_uri(
                reverse('accounts:magic_login', kwargs={'token': login_link.token})
            )
            
            # Send email
            try:
                send_mail(
                    'Your Chatty login link',
                    f'Click here to log in: {login_url}\n\nThis link expires in 15 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'Login link sent! Check your email.')
            except Exception:
                print(f"Login link for {email}: {login_url}")
                messages.success(request, 'Login link sent! Check your email (or console in development).')
            
            return redirect('accounts:login')
    else:
        form = EmailLoginForm()
    
    return render(request, 'accounts/email_login.html', {'form': form})


def magic_login_view(request, token):
    """Handle magic link login."""
    login_link = get_object_or_404(LoginLink, token=token)
    
    if not login_link.is_valid:
        messages.error(request, 'This login link has expired or already been used.')
        return redirect('accounts:login')
    
    # Mark as used
    login_link.is_used = True
    login_link.save()
    
    # Log user in
    user = login_link.user
    login(request, user)
    
    log_activity(user, 'login', request, {'method': 'magic_link'})
    user.update_last_seen()
    
    messages.success(request, 'Welcome back!')
    return redirect('chat:chat_list')


@login_required
def logout_view(request):
    """Handle user logout."""
    log_activity(request.user, 'logout', request)
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """View user profile."""
    return render(request, 'accounts/profile.html', {'profile_user': request.user})


@login_required
def profile_edit_view(request):
    """Edit user profile."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'profile_update', request)
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:settings')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def change_password_view(request):
    """Change user password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            if not request.user.check_password(form.cleaned_data['current_password']):
                messages.error(request, 'Current password is incorrect.')
            else:
                request.user.set_password(form.cleaned_data['new_password'])
                request.user.save()
                
                # Re-authenticate user
                login(request, request.user)
                
                log_activity(request.user, 'password_change', request)
                messages.success(request, 'Password changed successfully!')
                return redirect('core:settings')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def delete_account_view(request):
    """Request account deletion."""
    if request.method == 'POST':
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            from .models import DataDeletionRequest
            
            DataDeletionRequest.objects.create(
                user=request.user,
                reason=form.cleaned_data.get('reason', '')
            )
            
            log_activity(request.user, 'account_deleted', request)
            
            # Deactivate account
            request.user.is_active = False
            request.user.save()
            
            logout(request)
            messages.success(request, 'Your account deletion request has been submitted.')
            return redirect('accounts:login')
    else:
        form = DeleteAccountForm()
    
    return render(request, 'accounts/delete_account.html', {'form': form})


def user_search_view(request):
    """Search for users."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        is_active=True,
        is_verified=True
    ).exclude(
        id=request.user.id
    ).filter(
        models.Q(username__icontains=query) | models.Q(name__icontains=query)
    )[:10]
    
    results = [{
        'id': str(user.id),
        'username': user.username,
        'name': user.name,
        'profile_pic': user.profile_pic.url if user.profile_pic else None,
        'is_online': user.is_online,
    } for user in users]
    
    return JsonResponse({'users': results})


# Import models for user search
from django.db import models
