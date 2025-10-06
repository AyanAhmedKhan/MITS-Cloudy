from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.admin.sites import NotRegistered
from .models import (
    UserProfile, AcademicSession, Department, FileCategory, 
    Folder, FileItem, ShareLink, FileAuditLog, Notification, LogFile, AllowedExtension
)
from django.contrib import admin


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'employee_id', 'is_faculty', 'created_at')
    list_filter = ('department', 'is_faculty', 'created_at')
    search_fields = ('user__username', 'user__email', 'employee_id')
    readonly_fields = ('created_at',)


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "is_active", "start_date", "end_date", "created_by", "created_at")
    list_filter = ("is_active", "year", "created_at")
    search_fields = ("name", "description")
    actions = ["make_active", "make_inactive", "duplicate_session"]
    readonly_fields = ('created_at', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Activate selected session (deactivates others)")
    def make_active(self, request, queryset):
        AcademicSession.objects.update(is_active=False)
        queryset.update(is_active=True)
        self.message_user(request, f"Activated {queryset.count()} session(s)")

    @admin.action(description="Deactivate selected session")
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} session(s)")

    @admin.action(description="Duplicate selected session")
    def duplicate_session(self, request, queryset):
        for session in queryset:
            new_session = AcademicSession.objects.create(
                name=f"{session.name} (Copy)",
                year=session.year + 1,
                is_active=False,
                description=f"Copy of {session.name}",
                created_by=request.user
            )
        self.message_user(request, f"Duplicated {queryset.count()} session(s)")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "head_of_dept", "is_active", "active_session_override", "get_current_active_session")
    list_filter = ("is_active", "active_session_override")
    search_fields = ("name", "code", "description")
    fields = ("name", "code", "description", "head_of_dept", "is_active", "active_session_override")
    actions = ["set_active_session_override", "clear_active_session_override"]
    
    def get_current_active_session(self, obj):
        """Display the current active session for this department"""
        session = obj.get_active_session()
        if session:
            if obj.active_session_override:
                return format_html(
                    '<span style="color: orange;">{}</span> <small>(Override)</small>',
                    session.name
                )
            else:
                return format_html(
                    '<span style="color: green;">{}</span> <small>(Global)</small>',
                    session.name
                )
        return "No active session"
    get_current_active_session.short_description = "Current Active Session"
    
    def set_active_session_override(self, request, queryset):
        """Bulk action to set active session override for selected departments"""
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        # Redirect to a custom admin page for session selection
        ids = ','.join(str(obj.id) for obj in queryset)
        return HttpResponseRedirect(
            reverse('admin:set_department_session') + f'?ids={ids}'
        )
    set_active_session_override.short_description = "Set Active Session Override"
    
    def clear_active_session_override(self, request, queryset):
        """Clear active session override for selected departments"""
        updated = queryset.update(active_session_override=None)
        self.message_user(
            request,
            f"Cleared active session override for {updated} department(s). They will now use the global active session."
        )
    clear_active_session_override.short_description = "Clear Active Session Override (Use Global)"


@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "color_preview", "file_count")
    search_fields = ("name", "description")
    
    def color_preview(self, obj):
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border-radius: 3px;"></div>',
            obj.color
        )
    color_preview.short_description = "Color"
    
    def file_count(self, obj):
        return FileItem.objects.filter(category=obj).count()
    file_count.short_description = "Files"


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "session", "parent", "owner", "is_public", "category", "created_at", "delete_link")
    list_filter = ("department", "session", "is_public", "category", "created_at")
    search_fields = ("name", "description", "owner__username")
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('parent', 'owner', 'category')
    inlines = []
    actions = ["delete_folders_and_contents"]
    actions_on_top = True
    actions_on_bottom = True

    def get_inlines(self, request, obj=None):
        return [FolderChildrenInline, FileItemInline]

    def delete_link(self, obj):
        url = reverse('admin:storage_folder_delete', args=[obj.pk])
        return format_html('<a class="button" href="{}">Delete</a>', url)
    delete_link.short_description = "Delete"

    @admin.action(description="Delete selected folders with all nested files and subfolders")
    def delete_folders_and_contents(self, request, queryset):
        from django.db import transaction

        def iter_descendants(root_folders):
            pending = list(root_folders)
            seen = set()
            while pending:
                f = pending.pop()
                if f.id in seen:
                    continue
                seen.add(f.id)
                yield f
                children = Folder.objects.filter(parent=f).only("id")
                pending.extend(children)

        deleted_files_count = 0
        deleted_folders_count = 0
        with transaction.atomic():
            # Collect all folders to remove (including descendants)
            all_folders = list(iter_descendants(queryset))
            # Delete all files' blobs first to avoid orphaned media
            for folder in all_folders:
                for file_item in FileItem.objects.filter(folder=folder).only("id", "file"):
                    try:
                        if file_item.file:
                            file_item.file.delete(save=False)
                        file_item.delete()
                        deleted_files_count += 1
                    except Exception as e:
                        self.message_user(request, f"Error deleting file '{getattr(file_item, 'name', 'unknown')}': {e}", level='ERROR')
            # Now delete folders (children first). Django CASCADE will handle children when parent is deleted,
            # but we count them explicitly for feedback.
            for folder in all_folders:
                try:
                    folder.delete()
                    deleted_folders_count += 1
                except Exception as e:
                    self.message_user(request, f"Error deleting folder '{getattr(folder, 'name', 'unknown')}': {e}", level='ERROR')

        self.message_user(request, f"Deleted {deleted_files_count} file(s) and {deleted_folders_count} folder(s).")


class FolderChildrenInline(admin.TabularInline):
    model = Folder
    fk_name = 'parent'
    extra = 0
    fields = ("name", "is_public", "category", "owner", "created_at")
    readonly_fields = ("created_at",)


class FileItemInline(admin.TabularInline):
    model = FileItem
    extra = 0
    fields = ("name", "is_public", "category", "file_size", "download_count", "created_at")
    readonly_fields = ("file_size", "download_count", "created_at")


@admin.register(FileItem)
class FileItemAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "session", "folder", "owner", "is_public", "category", "file_size_display", "download_count", "created_at", "delete_link")
    list_filter = ("department", "session", "is_public", "category", "created_at")
    search_fields = ("name", "description", "owner__username", "original_filename")
    readonly_fields = ('file_size', 'download_count', 'created_at', 'updated_at')
    autocomplete_fields = ('folder', 'owner', 'category')
    actions = ["make_public", "make_private", "reset_download_count", "delete_files_and_blobs"]
    actions_on_top = True
    actions_on_bottom = True
    
    def file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size // 1024} KB"
        else:
            return f"{obj.file_size // (1024 * 1024)} MB"
    file_size_display.short_description = "Size"
    
    @admin.action(description="Make selected files public")
    def make_public(self, request, queryset):
        queryset.update(is_public=True)
        self.message_user(request, f"Made {queryset.count()} file(s) public")
    
    @admin.action(description="Make selected files private")
    def make_private(self, request, queryset):
        queryset.update(is_public=False)
        self.message_user(request, f"Made {queryset.count()} file(s) private")
    
    @admin.action(description="Reset download count")
    def reset_download_count(self, request, queryset):
        queryset.update(download_count=0)
        self.message_user(request, f"Reset download count for {queryset.count()} file(s)")

    @admin.action(description="Delete selected files (including stored file)")
    def delete_files_and_blobs(self, request, queryset):
        deleted_count = 0
        for file_item in queryset:
            try:
                if file_item.file:
                    file_item.file.delete(save=False)
                file_item.delete()
                deleted_count += 1
            except Exception as e:
                self.message_user(request, f"Error deleting {getattr(file_item, 'name', 'file')}: {e}", level='ERROR')
        self.message_user(request, f"Deleted {deleted_count} file(s)")

    def delete_link(self, obj):
        url = reverse('admin:storage_fileitem_delete', args=[obj.pk])
        return format_html('<a class="button" href="{}">Delete</a>', url)
    delete_link.short_description = "Delete"


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ("file_item", "share_type", "token", "email", "created_by", "is_active", "download_count", "created_at", "expires_at")
    list_filter = ("share_type", "is_active", "created_at")
    search_fields = ("token", "email", "file_item__name", "created_by__username")
    readonly_fields = ('token', 'download_count', 'created_at')
    actions = ["deactivate_links", "extend_expiry"]
    
    @admin.action(description="Deactivate selected links")
    def deactivate_links(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} share link(s)")
    
    @admin.action(description="Extend expiry by 30 days")
    def extend_expiry(self, request, queryset):
        from datetime import timedelta
        for link in queryset:
            if link.expires_at:
                link.expires_at += timedelta(days=30)
                link.save()
        self.message_user(request, f"Extended expiry for {queryset.count()} share link(s)")


@admin.register(FileAuditLog)
class FileAuditLogAdmin(admin.ModelAdmin):
    list_display = ("file_item", "user", "action", "ip_address", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("file_item__name", "user__username", "ip_address")
    readonly_fields = ('file_item', 'user', 'action', 'ip_address', 'user_agent', 'timestamp', 'details')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "title", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("user__username", "title", "message")
    readonly_fields = ('created_at',)
    actions = ["mark_as_read", "mark_as_unread"]
    
    @admin.action(description="Mark selected notifications as read")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"Marked {queryset.count()} notification(s) as read")
    
    @admin.action(description="Mark selected notifications as unread")
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f"Marked {queryset.count()} notification(s) as unread")


@admin.register(LogFile)
class LogFileAdmin(admin.ModelAdmin):
    list_display = ("name", "log_type", "file_size_display", "generated_by", "generated_at", "download_count", "is_active", "is_expired")
    list_filter = ("log_type", "is_active", "generated_at")
    search_fields = ("name", "generated_by__username")
    readonly_fields = ('file_size', 'download_count', 'generated_at')
    actions = ["delete_selected_logs", "extend_expiry"]
    date_hierarchy = 'generated_at'
    
    def file_size_display(self, obj):
        return obj.file_size_display
    file_size_display.short_description = "Size"
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = "Expired"
    
    @admin.action(description="Delete selected log files")
    def delete_selected_logs(self, request, queryset):
        import os
        deleted_count = 0
        for log_file in queryset:
            try:
                # Delete physical file
                if os.path.exists(log_file.file_path):
                    os.remove(log_file.file_path)
                # Mark as inactive
                log_file.is_active = False
                log_file.save()
                deleted_count += 1
            except Exception as e:
                self.message_user(request, f"Error deleting {log_file.name}: {str(e)}", level='ERROR')
        self.message_user(request, f"Deleted {deleted_count} log file(s)")
    
    @admin.action(description="Extend expiry by 30 days")
    def extend_expiry(self, request, queryset):
        from datetime import timedelta
        from django.utils import timezone
        
        updated = 0
        for log_file in queryset:
            if log_file.expires_at:
                log_file.expires_at += timedelta(days=30)
                log_file.save()
                updated += 1
            else:
                log_file.expires_at = timezone.now() + timedelta(days=30)
                log_file.save()
                updated += 1
        self.message_user(request, f"Extended expiry for {updated} log file(s)")


# Allow super admin to manage allowed file extensions
@admin.register(AllowedExtension)
class AllowedExtensionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    list_per_page = 50

# Customize admin site
admin.site.site_header = "MITS Cloud Administration"
admin.site.site_title = "MITS Cloud Admin"
admin.site.index_title = "Welcome to MITS Cloud Administration"


# --- User admin customization for roles/permissions ---

try:
    admin.site.unregister(User)
except NotRegistered:
    pass

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = 'user'
    extra = 0
    fields = ('department', 'employee_id', 'phone', 'is_faculty', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [UserProfileInline]
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_active', 'is_staff', 'is_superuser',
        'profile_is_faculty', 'profile_department',
        'last_login', 'date_joined'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser',
        ('profile__is_faculty'), 'date_joined', 'last_login'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'profile__employee_id')
    actions = ['make_admin', 'remove_admin', 'mark_faculty', 'unmark_faculty']

    def profile_is_faculty(self, obj):
        return getattr(obj.profile, 'is_faculty', False)
    profile_is_faculty.boolean = True
    profile_is_faculty.short_description = 'Faculty'

    def profile_department(self, obj):
        return getattr(getattr(obj, 'profile', None), 'department', None)
    profile_department.short_description = 'Department'

    @admin.action(description='Grant admin (staff + superuser)')
    def make_admin(self, request, queryset):
        queryset.update(is_staff=True, is_superuser=True)
        self.message_user(request, f"Granted admin to {queryset.count()} user(s)")

    @admin.action(description='Revoke admin (staff + superuser)')
    def remove_admin(self, request, queryset):
        queryset.update(is_staff=False, is_superuser=False)
        self.message_user(request, f"Revoked admin from {queryset.count()} user(s)")

    @admin.action(description='Mark as faculty')
    def mark_faculty(self, request, queryset):
        updated = 0
        for user in queryset:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if not profile.is_faculty:
                profile.is_faculty = True
                profile.save()
                updated += 1
        self.message_user(request, f"Marked {updated} user(s) as faculty")

    @admin.action(description='Unmark faculty')
    def unmark_faculty(self, request, queryset):
        updated = 0
        for user in queryset:
            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                continue
            if profile.is_faculty:
                profile.is_faculty = False
                profile.save()
                updated += 1
        self.message_user(request, f"Unmarked {updated} user(s) as faculty")

