"""
Forms for user authentication and registration.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class SignUpForm(forms.ModelForm):
    """Form for user registration."""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password',
        }),
        min_length=8
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        }),
        label='Confirm Password'
    )
    
    class Meta:
        model = User
        fields = ['name', 'age', 'username', 'email', 'password']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your full name',
                'autocomplete': 'name',
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your age',
                'min': 13,
                'max': 150,
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Choose a username',
                'autocomplete': 'username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your email address',
                'autocomplete': 'email',
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username').lower()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        if len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters.')
        return username
    
    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age and age < 13:
            raise forms.ValidationError('You must be at least 13 years old to sign up.')
        return age
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """Form for user login."""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your email address',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your password',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(required=False, initial=True)


class EmailLoginForm(forms.Form):
    """Form for passwordless email login."""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your email address',
            'autocomplete': 'email',
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if not User.objects.filter(email=email, is_verified=True).exists():
            raise forms.ValidationError('No verified account found with this email.')
        return email


class VerificationCodeForm(forms.Form):
    """Form for email verification code."""
    
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-input verification-code',
            'placeholder': '000000',
            'maxlength': '6',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        })
    )


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile."""
    
    class Meta:
        model = User
        fields = ['name', 'username', 'bio', 'profile_pic', 'theme', 'chat_background']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your display name',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your username',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Tell us about yourself...',
                'rows': 3,
                'maxlength': 500,
            }),
            'profile_pic': forms.FileInput(attrs={
                'class': 'form-input-file',
                'accept': 'image/*',
            }),
            'theme': forms.Select(attrs={
                'class': 'form-select',
            }),
            'chat_background': forms.Select(attrs={
                'class': 'form-select',
            }, choices=[
                ('default', 'Default'),
                ('gradient1', 'Ocean Blue'),
                ('gradient2', 'Sunset Orange'),
                ('gradient3', 'Forest Green'),
                ('gradient4', 'Purple Night'),
                ('gradient5', 'Minimal Gray'),
            ]),
        }


class PasswordChangeForm(forms.Form):
    """Form for changing password."""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Current password',
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New password',
        }),
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password',
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('New passwords do not match.')
        
        return cleaned_data


class DeleteAccountForm(forms.Form):
    """Form for requesting account deletion."""
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'placeholder': 'Optional: Tell us why you\'re leaving...',
            'rows': 3,
        })
    )
    confirm = forms.BooleanField(
        required=True,
        label='I understand that this action is irreversible'
    )
