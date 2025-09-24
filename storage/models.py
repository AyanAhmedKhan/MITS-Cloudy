from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.apps import apps
import uuid


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    employee_id = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    is_faculty = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.department.name if self.department else 'No Dept'}"
    
    def get_active_session(self):
        """Get the active session for this user/faculty"""
        if self.department:
            return self.department.get_active_session()
        # Fall back to global active session
        return AcademicSession.objects.filter(is_active=True).first()


class AcademicSession(models.Model):
    name = models.CharField(max_length=64, unique=True, help_text="e.g., 2024-25")
    year = models.IntegerField(unique=True)
    is_active = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-is_active', '-year']
        constraints = [
            models.UniqueConstraint(fields=['name'], name='unique_session_name'),
            models.UniqueConstraint(fields=['year'], name='unique_session_year'),
        ]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Save the session"""
        super().save(*args, **kwargs)


class Department(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    head_of_dept = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # Override active session for this specific faculty
    active_session_override = models.ForeignKey('AcademicSession', on_delete=models.SET_NULL, null=True, blank=True,
                                               help_text="Override active session for this faculty (leave blank to use global active session)")

    def __str__(self):
        return self.name
    
    def get_active_session(self):
        """Get the active session for this department"""
        if self.active_session_override:
            return self.active_session_override
        # Fall back to global active session
        return AcademicSession.objects.filter(is_active=True).first()


class FileCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#3B82F6")  # Hex color
    
    def __str__(self):
        return self.name


class AllowedExtension(models.Model):
    name = models.CharField(max_length=20, unique=True, help_text="File extension without dot, e.g., pdf, jpg, java")

    def __str__(self):
        return self.name


def validate_dynamic_extension(file):
    filename = getattr(file, 'name', '')
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    # Base defaults
    default_allowed = {
        'pdf','doc','docx','ppt','pptx','xls','xlsx','txt','zip','rar','jpg','jpeg','png','gif'
    }
    try:
        AllowedExt = apps.get_model('storage', 'AllowedExtension')
        dynamic = set(AllowedExt.objects.values_list('name', flat=True))
    except Exception:
        dynamic = set()
    allowed = default_allowed | dynamic
    if ext not in allowed:
        raise ValidationError(f"File type .{ext or 'unknown'} is not allowed")


class Folder(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    is_manual = models.BooleanField(default=False, help_text="True if folder was manually added to media directory")
    category = models.ForeignKey(FileCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'department', 'parent', 'name')

    def __str__(self):
        return self.name


def upload_to_file(instance, filename):
    # year_session/department/filepath
    session_part = f"{instance.session.year}_{instance.session.name}"
    dept_part = instance.department.code
    folder_chain = []
    folder = instance.folder
    while folder is not None:
        folder_chain.append(folder.name)
        folder = folder.parent
    folder_chain.reverse()
    path = "/".join([session_part, dept_part] + folder_chain + [filename])
    return path


class FileItem(models.Model):
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    folder = models.ForeignKey(Folder, null=True, blank=True, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to=upload_to_file,
        max_length=500,
        validators=[validate_dynamic_extension]
    )
    name = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255, blank=True, default='')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    is_manual = models.BooleanField(default=False, help_text="True if file was manually added to media directory")
    category = models.ForeignKey(FileCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    file_size = models.BigIntegerField(default=0)  # in bytes
    download_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            if not self.original_filename:
                self.original_filename = self.file.name
        super().save(*args, **kwargs)


class ShareLink(models.Model):
    SHARE_TYPES = [
        ('public', 'Public Link'),
        ('email', 'Email Restricted'),
        ('password', 'Password Protected'),
    ]
    
    file_item = models.ForeignKey(FileItem, related_name='share_links', on_delete=models.CASCADE, null=True, blank=True)
    folder = models.ForeignKey(Folder, related_name='share_links', on_delete=models.CASCADE, null=True, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    share_type = models.CharField(max_length=20, choices=SHARE_TYPES, default='public')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    password = models.CharField(max_length=128, blank=True)
    max_downloads = models.IntegerField(null=True, blank=True)
    download_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_downloads and self.download_count >= self.max_downloads:
            return False
        return True

    def clean(self):
        # Ensure exactly one of file_item or folder is provided
        if bool(self.file_item) == bool(self.folder):
            from django.core.exceptions import ValidationError
            raise ValidationError('Provide exactly one of file_item or folder when creating a ShareLink.')


class FileAuditLog(models.Model):
    ACTION_CHOICES = [
        ('upload', 'File Uploaded'),
        ('download', 'File Downloaded'),
        ('delete', 'File Deleted'),
        ('share', 'File Shared'),
        ('view', 'File Viewed'),
    ]
    
    file_item = models.ForeignKey(FileItem, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} by {self.user.username} on {self.file_item.name}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('file_shared', 'File Shared With You'),
        ('session_activated', 'Session Activated'),
        ('file_uploaded', 'New File Uploaded'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_file = models.ForeignKey(FileItem, on_delete=models.CASCADE, null=True, blank=True)
    related_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} for {self.user.username}"


class LogFile(models.Model):
    """Model to track generated log files"""
    LOG_TYPE_CHOICES = [
        ('general', 'General Logs'),
        ('errors', 'Error Logs'),
        ('access', 'Access Logs'),
        ('security', 'Security Logs'),
        ('custom', 'Custom Logs'),
    ]
    
    name = models.CharField(max_length=255)
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, default='general')
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0)
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.name} ({self.log_type}) - {self.generated_by.username}"
    
    @property
    def file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def is_expired(self):
        """Check if the log file has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

