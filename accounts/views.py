from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views import View
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from storage.models import Department, UserProfile


class DepartmentSelectionForm(forms.Form):
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        empty_label="Select your department",
        widget=forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'})
    )


class DomainRestrictedSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        empty_label="Select your department",
        required=True,
        widget=forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'})
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "department")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        
        # Check if email is in specific allowed emails
        allowed_emails = getattr(settings, 'ALLOWED_SPECIFIC_EMAILS', [])
        if email in allowed_emails:
            return email
            
        # Check if email ends with allowed domains
        allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', ['@mitsgwalior.in'])
        if any(email.endswith(d) for d in allowed_domains):
            return email
            
        # If neither, raise error
        allowed = ', '.join(allowed_domains + allowed_emails)
        raise forms.ValidationError(f"Only emails ending with: {', '.join(allowed_domains)} or specific emails: {', '.join(allowed_emails)} are allowed.")


class DomainRestrictedAuthForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        email = user.email.lower()
        
        # Check if email is in specific allowed emails
        allowed_emails = getattr(settings, 'ALLOWED_SPECIFIC_EMAILS', [])
        if email in allowed_emails:
            return
            
        # Check if email ends with allowed domains
        allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', ['@mitsgwalior.in'])
        if any(email.endswith(d) for d in allowed_domains):
            return
            
        # If neither, raise error
        allowed = ', '.join(allowed_domains + allowed_emails)
        raise forms.ValidationError(f"Login restricted to emails ending with: {', '.join(allowed_domains)} or specific emails: {', '.join(allowed_emails)}.")


class SignupView(View):
    def get(self, request):
        return render(request, 'accounts/signup.html', {"form": DomainRestrictedSignupForm()})

    def post(self, request):
        form = DomainRestrictedSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create user profile with department and faculty status
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.department = form.cleaned_data['department']
            profile.save()
            
            login(request, user)
            return redirect('/')
        return render(request, 'accounts/signup.html', {"form": form})


@method_decorator(login_required, name='dispatch')
class DepartmentSetupView(View):
    """View for users to set their department after first login (especially for Google OAuth)"""
    
    def get(self, request):
        # Check if user already has a department
        try:
            profile = request.user.profile
            if profile.department:
                return redirect('/')  # Already has department, redirect to dashboard
        except UserProfile.DoesNotExist:
            pass
        
        return render(request, 'accounts/department_setup.html', {
            "form": DepartmentSelectionForm()
        })
    
    def post(self, request):
        form = DepartmentSelectionForm(request.POST)
        if form.is_valid():
            # Create or update user profile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.department = form.cleaned_data['department']
            profile.save()
            
            return redirect('/')
        
        return render(request, 'accounts/department_setup.html', {"form": form})


class EmailDomainLoginView(View):
    def get(self, request):
        return render(request, 'accounts/login.html', {"form": DomainRestrictedAuthForm()})

    def post(self, request):
        form = DomainRestrictedAuthForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Check if user needs to set up department
                try:
                    profile = user.profile
                    if not profile.department:
                        return redirect('/auth/department-setup/')
                except UserProfile.DoesNotExist:
                    return redirect('/auth/department-setup/')
                
                return redirect('/')
        # Show friendly error for domain/invalid attempts
        from django.contrib import messages
        messages.error(
            request,
            "Oops! 😅  \nIt looks like you tried logging in with an email that isn’t a MITS-DU account.  \nPlease use your official MITS-DU email (e.g., yourname@mitsgwalior.in) to continue."
        )
        return render(request, 'accounts/login.html', {"form": form})


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('/')


class OneClickGoogleAuthView(View):
    """Single entry page for both login and signup using Google only."""
    def get(self, request):
        allowed_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', ['@mitsgwalior.in'])
        allowed_specific = getattr(settings, 'ALLOWED_SPECIFIC_EMAILS', [])
        return render(request, 'accounts/google_auth.html', {
            'allowed_domains': allowed_domains,
            'allowed_specific_emails': allowed_specific,
        })