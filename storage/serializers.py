from rest_framework import serializers
class NullablePKRelatedField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        if data in (None, ""):
            return None
        return super().to_internal_value(data)

from .models import (
    AcademicSession, Department, Folder, FileItem, ShareLink, 
    UserProfile, FileCategory, FileAuditLog, Notification, LogFile
)


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'department', 'employee_id', 'phone', 'is_faculty', 'created_at']
        read_only_fields = ['created_at']


class FileCategorySerializer(serializers.ModelSerializer):
    file_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FileCategory
        fields = ['id', 'name', 'description', 'color', 'file_count']
    
    def get_file_count(self, obj):
        return obj.fileitem_set.count()


class AcademicSessionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = AcademicSession
        fields = ['id', 'name', 'year', 'is_active', 'start_date', 'end_date', 'description', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['created_by', 'created_at']
    
    def validate(self, data):
        """Validate session data"""
        # Check for duplicate name
        if 'name' in data:
            existing = AcademicSession.objects.filter(name=data['name'])
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({'name': 'A session with this name already exists.'})
        
        # Check for duplicate year
        if 'year' in data:
            existing = AcademicSession.objects.filter(year=data['year'])
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({'year': 'A session with this year already exists.'})
        
        # Note: Active session validation is handled in admin views, not here
        return data


class DepartmentSerializer(serializers.ModelSerializer):
    head_of_dept_name = serializers.CharField(source='head_of_dept.username', read_only=True)
    active_session_override = NullablePKRelatedField(queryset=AcademicSession.objects.all(), required=False, allow_null=True, default=None)
    active_session_override_name = serializers.CharField(source='active_session_override.name', read_only=True)
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'description', 'head_of_dept', 'head_of_dept_name', 'is_active', 'active_session_override', 'active_session_override_name']


class FolderSerializer(serializers.ModelSerializer):
    parent = NullablePKRelatedField(queryset=Folder.objects.all(), required=False, allow_null=True, default=None)
    department_name = serializers.CharField(source='department.name', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    children_count = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = [
            'id', 'session', 'session_name', 'department', 'department_name', 
            'name', 'parent', 'owner', 'owner_name', 'is_public', 'is_manual', 'category', 
            'category_name', 'description', 'children_count', 'files_count', 
            'created_at', 'updated_at', 'is_deleted', 'deleted_at', 'deleted_by'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at', 'is_deleted', 'deleted_at', 'deleted_by']
        extra_kwargs = {
            'parent': {'required': False, 'allow_null': True, 'default': None},
            'session': {'required': False, 'allow_null': True, 'default': None},
            'department': {'required': False, 'allow_null': True, 'default': None},
        }
    
    def validate(self, attrs):
        session = attrs.get('session') or getattr(self.instance, 'session', None)
        request = self.context.get('request')
        if session and not session.is_active and (not request or not request.user.is_staff):
            raise serializers.ValidationError('Folder changes allowed only in active session.')
        # Coerce empty parent to None for root-level folders
        if 'parent' in attrs and not attrs['parent']:
            attrs['parent'] = None
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        parent = validated_data.get('parent')
        # Inherit from parent first
        if parent is not None:
            if validated_data.get('session') is None:
                validated_data['session'] = parent.session
            if validated_data.get('department') is None:
                validated_data['department'] = parent.department
            if validated_data.get('is_public') is None:
                validated_data['is_public'] = parent.is_public
        # Fallback to user profile
        if request is not None and (validated_data.get('session') is None or validated_data.get('department') is None):
            try:
                profile = request.user.profile
                if validated_data.get('session') is None:
                    validated_data['session'] = profile.get_active_session()
                if validated_data.get('department') is None:
                    validated_data['department'] = profile.department
            except Exception:
                pass
        return super().create(validated_data)
    
    def get_children_count(self, obj):
        return obj.children.count()
    
    def get_files_count(self, obj):
        return obj.files.count()


class FileItemSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    file_size_display = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()
    folder_path = serializers.SerializerMethodField()
    
    class Meta:
        model = FileItem
        fields = [
            'id', 'session', 'session_name', 'department', 'department_name', 
            'folder', 'folder_name', 'file', 'name', 'original_filename', 
            'owner', 'owner_name', 'is_public', 'is_manual', 'category', 'category_name', 
            'description', 'file_size', 'file_size_display', 'file_extension', 'folder_path',
            'download_count', 'created_at', 'updated_at', 'is_deleted', 'deleted_at', 'deleted_by'
        ]
        read_only_fields = ['owner', 'file_size', 'download_count', 'created_at', 'updated_at', 'is_deleted', 'deleted_at', 'deleted_by']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True},
            'session': {'required': False, 'allow_null': True},
            'department': {'required': False, 'allow_null': True},
        }
    
    def validate(self, attrs):
        session = attrs.get('session') or getattr(self.instance, 'session', None)
        request = self.context.get('request')
        if session and not session.is_active and (not request or not request.user.is_staff):
            raise serializers.ValidationError('Uploads allowed only in active session.')
        # Default name to uploaded file name if not provided
        if not attrs.get('name') and request and request.FILES.get('file'):
            attrs['name'] = request.data.get('name') or request.FILES['file'].name
        return attrs
    
    def get_file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size // 1024} KB"
        else:
            return f"{obj.file_size // (1024 * 1024)} MB"
    
    def get_file_extension(self, obj):
        if obj.original_filename:
            return obj.original_filename.split('.')[-1].upper()
        return ''

    def get_folder_path(self, obj):
        # Build human-readable folder path like FolderA/FolderB
        parts = []
        folder = obj.folder
        while folder is not None:
            parts.append(folder.name)
            folder = folder.parent
        parts.reverse()
        return "/".join(parts)


class ShareLinkSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file_item.name', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    share_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ShareLink
        fields = [
            'id', 'file_item', 'file_name', 'folder', 'folder_name', 'token', 'share_type', 'created_by', 
            'created_by_name', 'created_at', 'expires_at', 'email', 'password', 
            'max_downloads', 'download_count', 'is_active', 'share_url'
        ]
        read_only_fields = ['token', 'created_by', 'created_at', 'download_count']
    
    def get_share_url(self, obj):
        request = self.context.get('request')
        if request:
            return f"{request.scheme}://{request.get_host()}/share/{obj.token}/"
        return f"/share/{obj.token}/"

    def validate(self, attrs):
        # Ensure exactly one of file_item or folder
        file_item = attrs.get('file_item') or getattr(self.instance, 'file_item', None)
        folder = attrs.get('folder') or getattr(self.instance, 'folder', None)
        if bool(file_item) == bool(folder):
            raise serializers.ValidationError('Provide exactly one of file_item or folder.')
        return attrs


class FileAuditLogSerializer(serializers.ModelSerializer):
    file_name = serializers.CharField(source='file_item.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = FileAuditLog
        fields = ['id', 'file_item', 'file_name', 'user', 'user_name', 'action', 'ip_address', 'timestamp', 'details']
        read_only_fields = ['timestamp']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at', 'related_file', 'related_session']
        read_only_fields = ['created_at']


class LogFileSerializer(serializers.ModelSerializer):
    generated_by_username = serializers.CharField(source='generated_by.username', read_only=True)
    file_size_display = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = LogFile
        fields = [
            'id', 'name', 'log_type', 'file_path', 'file_size', 'file_size_display',
            'generated_by', 'generated_by_username', 'generated_at', 'expires_at',
            'download_count', 'is_active', 'is_expired', 'download_url'
        ]
        read_only_fields = ['generated_at', 'download_count']
    
    def get_download_url(self, obj):
        """Generate download URL for the log file"""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/logs/{obj.id}/download/')
        return None


