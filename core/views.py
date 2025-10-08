from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from django.conf import settings
from django.views.static import serve as django_static_serve
import os
from storage.models import AcademicSession
from django.contrib.auth.models import User
from storage.models import Department, Folder, FileItem, ShareLink, FileAuditLog, Notification
from storage.models import AllowedExtension
from core.utils import is_database_connected
from django.http import HttpResponse


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
    
    # Allowed extensions for client-side hinting
    try:
        allowed_exts = list(AllowedExtension.objects.values_list('name', flat=True))
    except Exception:
        allowed_exts = []

    return render(request, 'core/dashboard.html', {
        'active_session': active_session,
        'is_using_override': is_using_override,
        'is_staff': request.user.is_staff,
        'allowed_exts': allowed_exts,
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


def custom_permission_denied_view(request, exception=None):
    """Render a friendly 403 Unauthorized/Forbidden page."""
    return render(request, '403.html', status=403)


def custom_page_not_found_view(request, exception=None):
    """Render a friendly 404 page not found."""
    return render(request, '404.html', status=404)


def custom_server_error_view(request):
    """Render a friendly 500 server error page."""
    return render(request, '500.html', status=500)


def media_serve(request, path):
    """Serve MEDIA files; render a friendly page if the file is missing."""
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(full_path):
        file_name = os.path.basename(path)
        return render(request, 'storage/file_missing.html', {
            'file_name': file_name,
            'share_type': 'public',
        }, status=404)
    return django_static_serve(request, path, document_root=settings.MEDIA_ROOT)


def health(request):
    """Simple health page indicating database connectivity for uptime checks."""
    db_ok = is_database_connected()
    # Derive database info without exposing secrets
    try:
        from django.conf import settings as dj_settings
        db_cfg = dj_settings.DATABASES.get('default', {})
        engine_full = db_cfg.get('ENGINE', '')
        engine = engine_full.split('.')[-1] if engine_full else ''
        db_name = db_cfg.get('NAME')
        db_host = db_cfg.get('HOST') if engine != 'sqlite3' else None
        db_port = db_cfg.get('PORT') if engine != 'sqlite3' else None
    except Exception:
        engine = ''
        db_name = None
        db_host = None
        db_port = None
    context = {
        'db_ok': db_ok,
        'db_engine': engine,
        'db_name': db_name,
        'db_host': db_host,
        'db_port': db_port,
    }
    status_code = 200 if db_ok else 503
    return render(request, 'core/health.html', context, status=status_code)


def terms(request):
    return render(request, 'core/terms.html')


def privacy(request):
    return render(request, 'core/privacy.html')


def help_center(request):
    try:
        allowed_exts = list(AllowedExtension.objects.values_list('name', flat=True))
    except Exception:
        allowed_exts = []
    return render(request, 'core/help_center.html', {
        'allowed_exts': allowed_exts,
    })