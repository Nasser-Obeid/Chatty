"""
Core views for settings and general pages.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from accounts.forms import ProfileUpdateForm, PasswordChangeForm, DeleteAccountForm
from accounts.views import log_activity


def home_view(request):
    """Home page - redirect based on auth status."""
    if request.user.is_authenticated:
        return redirect('chat:chat_list')
    return redirect('accounts:login')


@login_required
def settings_view(request):
    """Main settings page."""
    return render(request, 'core/settings.html', {
        'user': request.user,
    })


@login_required
def appearance_settings_view(request):
    """Appearance settings (theme, background)."""
    if request.method == 'POST':
        theme = request.POST.get('theme', 'dark')
        chat_background = request.POST.get('chat_background', 'default')
        
        request.user.theme = theme
        request.user.chat_background = chat_background
        request.user.save(update_fields=['theme', 'chat_background'])
        
        log_activity(request.user, 'profile_update', request, {
            'updated': ['theme', 'chat_background']
        })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, 'Appearance settings updated!')
        return redirect('core:settings')
    
    return render(request, 'core/appearance_settings.html', {
        'backgrounds': [
            {'id': 'default', 'name': 'Default', 'class': 'bg-default'},
            {'id': 'gradient1', 'name': 'Ocean Blue', 'class': 'bg-ocean'},
            {'id': 'gradient2', 'name': 'Sunset Orange', 'class': 'bg-sunset'},
            {'id': 'gradient3', 'name': 'Forest Green', 'class': 'bg-forest'},
            {'id': 'gradient4', 'name': 'Purple Night', 'class': 'bg-purple'},
            {'id': 'gradient5', 'name': 'Minimal Gray', 'class': 'bg-minimal'},
        ]
    })


@login_required
def profile_settings_view(request):
    """Profile settings."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'profile_update', request)
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:settings')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'core/profile_settings.html', {'form': form})


@login_required
def security_settings_view(request):
    """Security settings (password change)."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            if not request.user.check_password(form.cleaned_data['current_password']):
                messages.error(request, 'Current password is incorrect.')
            else:
                request.user.set_password(form.cleaned_data['new_password'])
                request.user.save()
                
                from django.contrib.auth import login
                login(request, request.user)
                
                log_activity(request.user, 'password_change', request)
                messages.success(request, 'Password changed successfully!')
                return redirect('core:settings')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'core/security_settings.html', {'form': form})


@login_required
def privacy_settings_view(request):
    """Privacy settings and data management."""
    from chat.models import ChatBackup
    
    # Get user's backups
    backups = ChatBackup.objects.filter(
        user=request.user,
        status='completed'
    ).order_by('-created_at')[:5]
    
    return render(request, 'core/privacy_settings.html', {
        'backups': backups,
    })


@login_required
def delete_account_view(request):
    """Delete account page."""
    if request.method == 'POST':
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            from accounts.models import DataDeletionRequest
            from django.contrib.auth import logout
            
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
    
    return render(request, 'core/delete_account.html', {'form': form})


@login_required
@require_POST
def update_theme_view(request):
    """AJAX endpoint to update theme."""
    theme = request.POST.get('theme', 'dark')
    
    if theme in ['light', 'dark']:
        request.user.theme = theme
        request.user.save(update_fields=['theme'])
        return JsonResponse({'success': True, 'theme': theme})
    
    return JsonResponse({'error': 'Invalid theme'}, status=400)
