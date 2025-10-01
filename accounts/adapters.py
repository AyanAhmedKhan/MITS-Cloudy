from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django import forms
from django.conf import settings
from django.utils.text import slugify


class DomainRestrictedAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to enforce domain restrictions"""
    
    def clean_email(self, email):
        email = super().clean_email(email)
        email_l = email.lower()
        
        # Check if email is in specific allowed emails
        allowed_emails = getattr(settings, 'ALLOWED_SPECIFIC_EMAILS', [])
        if email_l in allowed_emails:
            return email
            
        # Check if email ends with allowed domains
        allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', ['@mitsgwalior.in'])
        if any(email_l.endswith(d) for d in allowed_domains):
            return email
            
        # If neither, raise error
        allowed = ', '.join(allowed_domains + allowed_emails)
        raise forms.ValidationError(f"Only emails ending with: {', '.join(allowed_domains)} or specific emails: {', '.join(allowed_emails)} are allowed.")


class DomainRestrictedSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter to enforce domain restrictions for Google OAuth"""
    
    def pre_social_login(self, request, sociallogin):
        """Allow Google OAuth to proceed to email selection first"""
        # Don't validate email domain here - let it proceed to email selection
        # We'll validate in populate_user instead
        return
    
    def is_open_for_signup(self, request, sociallogin):
        """Allow signup for any Google account initially"""
        return True
    
    def get_connect_redirect_url(self, request, socialaccount):
        """Redirect after successful connection"""
        return '/'
    
    def get_login_redirect_url(self, request):
        """Redirect after successful login"""
        # Check if user needs to set up department
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                profile = request.user.profile
                if not profile.department:
                    return '/auth/department-setup/'
            except:
                # If profile doesn't exist, redirect to department setup
                return '/auth/department-setup/'
        return '/'
    
    def populate_user(self, request, sociallogin, data):
        """Populate user data from social login"""
        user = super().populate_user(request, sociallogin, data)
        email = sociallogin.account.extra_data.get('email', '').lower()
        # Ensure username is set from email local-part to support username expectations
        try:
            local = email.split('@')[0]
        except Exception:
            local = ''
        if not getattr(user, 'username', None):
            candidate = slugify(local) or 'user'
            # Ensure uniqueness
            from django.contrib.auth.models import User
            base = candidate
            i = 0
            while User.objects.filter(username=candidate).exists():
                i += 1
                candidate = f"{base}{i}"
            user.username = candidate
        
        # Check if email is in specific allowed emails
        allowed_emails = getattr(settings, 'ALLOWED_SPECIFIC_EMAILS', [])
        if email in allowed_emails:
            return user
            
        # Check if email ends with allowed domains
        allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', ['@mitsgwalior.in'])
        if any(email.endswith(d) for d in allowed_domains):
            return user
            
        # If neither, raise error
        allowed = ', '.join(allowed_domains + allowed_emails)
        raise forms.ValidationError(f"Only Google accounts ending with: {', '.join(allowed_domains)} or specific emails: {', '.join(allowed_emails)} are allowed.")
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """Allow auto signup for valid emails"""
        email = sociallogin.account.extra_data.get('email', '').lower()
        
        # Check if email is in specific allowed emails
        allowed_emails = getattr(settings, 'ALLOWED_SPECIFIC_EMAILS', [])
        if email in allowed_emails:
            return True
            
        # Check if email ends with allowed domains
        allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', ['@mitsgwalior.in'])
        if any(email.endswith(d) for d in allowed_domains):
            return True
            
        return False
    
    def save_user(self, request, sociallogin, form=None):
        """Save user and handle domain validation"""
        try:
            return super().save_user(request, sociallogin, form)
        except forms.ValidationError as e:
            # If validation fails, redirect to login with error message
            from django.contrib import messages
            messages.error(
                request,
                "Oops! 😅  \nIt looks like you tried logging in with an email that isn’t a MITS-DU account.  \nPlease use your official MITS-DU email (e.g., yourname@mitsgwalior.in) to continue."
            )
            from django.shortcuts import redirect
            return redirect('/auth/login/')
