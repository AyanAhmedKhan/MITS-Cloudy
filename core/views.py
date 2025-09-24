from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from storage.models import AcademicSession
from django.contrib.auth.models import User
from storage.models import Department, Folder, FileItem, ShareLink, FileAuditLog, Notification


def landing(request):
    return render(request, 'core/landing.html')


def about(request):
    return render(request, 'core/about.html')


@login_required
@ensure_csrf_cookie
def dashboard(request):
    # Check if user needs to set up department
    try:
        profile = request.user.profile
        if not profile.department:
            from django.shortcuts import redirect
            return redirect('/auth/department-setup/')
    except:
        from django.shortcuts import redirect
        return redirect('/auth/department-setup/')
    
    # Get user's active session info for display
    user_profile = request.user.profile
    active_session = user_profile.get_active_session()
    is_using_override = user_profile.department and user_profile.department.active_session_override is not None
    
    return render(request, 'core/dashboard.html', {
        'active_session': active_session,
        'is_using_override': is_using_override,
        'is_staff': request.user.is_staff,
    })


@login_required
@ensure_csrf_cookie
def faculty(request):
    # Get faculty-specific active session
    user_profile = request.user.profile
    active_session = user_profile.get_active_session()
    
    # Get all sessions for selection (if admin wants to change)
    all_sessions = AcademicSession.objects.all().order_by('-year', '-is_active')
    
    # Onboarding: if user is faculty and has no department, show prompt via context
    needs_dept = False
    try:
        needs_dept = request.user.profile.is_faculty and request.user.profile.department_id is None
    except Exception:
        needs_dept = False
    
    return render(request, 'core/faculty.html', {
        'active_session': active_session,
        'all_sessions': all_sessions,
        'needs_dept': needs_dept,
        'is_using_override': user_profile.department and user_profile.department.active_session_override is not None,
    })


def staff_check(user):
    return user.is_staff


@login_required
@user_passes_test(staff_check)
@ensure_csrf_cookie
def super_dashboard(request):
    return render(request, 'core/super_dashboard.html')


@login_required
@ensure_csrf_cookie
def drag_drop_demo(request):
    """Demo page showcasing drag and drop functionality"""
    return render(request, 'core/drag-drop-demo.html')