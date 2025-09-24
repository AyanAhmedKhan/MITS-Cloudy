from django import template
from django.contrib.auth.models import User
from storage.models import (
    AcademicSession, Department, Folder, FileItem, ShareLink, FileAuditLog, Notification
)

register = template.Library()


@register.simple_tag
def count_users():
    return User.objects.count()


@register.simple_tag
def count_sessions():
    return AcademicSession.objects.count()


@register.simple_tag
def count_departments():
    return Department.objects.count()


@register.simple_tag
def count_folders():
    return Folder.objects.count()


@register.simple_tag
def count_files():
    return FileItem.objects.count()


@register.simple_tag
def count_sharelinks():
    return ShareLink.objects.count()


@register.simple_tag
def count_notifications():
    return Notification.objects.count()


@register.inclusion_tag('admin/_recent_activity.html')
def recent_activity(limit: int = 10):
    logs = FileAuditLog.objects.select_related('file_item', 'user').order_by('-timestamp')[:limit]
    return {'logs': logs}


