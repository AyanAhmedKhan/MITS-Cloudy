from rest_framework import generics, permissions, status
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth.models import User
from .models import (
    AcademicSession, Department, Folder, FileItem, ShareLink, 
    UserProfile, FileCategory, FileAuditLog, Notification, LogFile
)
from .serializers import (
    AcademicSessionSerializer, DepartmentSerializer, FolderSerializer,
    FileItemSerializer, ShareLinkSerializer, UserProfileSerializer,
    FileCategorySerializer, LogFileSerializer
) 
from .models import AllowedExtension
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_scan_manual_files(request):
    """Admin endpoint to scan for manually added files"""
    try:
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Capture the output
        output = StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            # Run the scan command
            call_command('scan_media_files', verbosity=1)
            result = output.getvalue()
        finally:
            sys.stdout = old_stdout
        
        # Count the results
        files_created = result.count('Created file:')
        folders_created = result.count('Created folder:')
        
        return Response({
            'success': True,
            'message': f'Scan completed successfully! Created {files_created} files and {folders_created} folders.',
            'details': result,
            'files_created': files_created,
            'folders_created': folders_created
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error scanning manual files: {str(e)}',
            'details': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_stats(request):
    from django.db.models import Sum
    total_bytes = FileItem.objects.aggregate(total=Sum('file_size')).get('total') or 0

    # Human-readable display
    def humanize_bytes(num: int) -> str:
        size = float(num)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0 or unit == 'TB':
                return f"{size:.1f} {unit}" if unit != 'B' else f"{int(size)} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    return Response({
        'users': User.objects.count(),
        'sessions': AcademicSession.objects.count(),
        'departments': Department.objects.count(),
        'folders': Folder.objects.count(),
        'files': FileItem.objects.count(),
        'sharelinks': ShareLink.objects.count(),
        'notifications': Notification.objects.count(),
        'allowed_extensions': AllowedExtension.objects.count(),
        'storage': humanize_bytes(total_bytes),
        'storage_bytes': total_bytes,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_all_sessions(request):
    """Return all sessions (active and inactive) for super admin"""
    sessions = AcademicSession.objects.all().order_by('-year', '-is_active')
    serializer = AcademicSessionSerializer(sessions, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_recent_activity(request):
    logs = FileAuditLog.objects.select_related('file_item', 'user').order_by('-timestamp')[:10]
    data = [{
        'user': log.user.username,
        'action': log.get_action_display(),
        'file': log.file_item.name,
        'timestamp': log.timestamp.isoformat(timespec='minutes'),
    } for log in logs]
    return Response({'logs': data})


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([permissions.IsAdminUser])
def admin_allowed_extensions(request):
    if request.method == 'GET':
        return Response({'extensions': list(AllowedExtension.objects.values_list('name', flat=True))})
    if request.method == 'POST':
        name = (request.data.get('name') or '').strip().lower().lstrip('.')
        if not name:
            return Response({'detail': 'name required'}, status=400)
        AllowedExtension.objects.get_or_create(name=name)
        return Response({'detail': 'Added'})
    if request.method == 'DELETE':
        name = (request.data.get('name') or '').strip().lower().lstrip('.')
        AllowedExtension.objects.filter(name=name).delete()
        return Response({'detail': 'Removed'})


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_recycle_bin(request):
    files = FileItem.objects.filter(is_deleted=True)
    folders = Folder.objects.filter(is_deleted=True)
    return Response({
        'files': FileItemSerializer(files, many=True).data,
        'folders': FolderSerializer(folders, many=True).data,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_restore_file(request, pk):
    try:
        item = FileItem.objects.get(pk=pk, is_deleted=True)
    except FileItem.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)
    item.is_deleted = False
    item.deleted_at = None
    item.deleted_by = None
    item.save(update_fields=['is_deleted','deleted_at','deleted_by'])
    return Response({'detail': 'Restored'})


@api_view(['DELETE'])
@permission_classes([permissions.IsAdminUser])
def admin_purge_file(request, pk):
    try:
        item = FileItem.objects.get(pk=pk)
    except FileItem.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)
    try:
        if item.file:
            item.file.delete(save=False)
    except Exception:
        pass
    item.delete()
    return Response({'detail': 'Purged'})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_restore_folder(request, pk):
    try:
        folder = Folder.objects.get(pk=pk, is_deleted=True)
    except Folder.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)
    # Restore folder and all descendants
    def iter_descendants(root: Folder):
        pending = [root]
        seen = set()
        while pending:
            f = pending.pop()
            if f.id in seen:
                continue
            seen.add(f.id)
            yield f
            for ch in Folder.objects.filter(parent=f).only('id'):
                pending.append(ch)
    for f in iter_descendants(folder):
        Folder.objects.filter(pk=f.pk).update(is_deleted=False, deleted_at=None, deleted_by=None)
        FileItem.objects.filter(folder=f).update(is_deleted=False, deleted_at=None, deleted_by=None)
    return Response({'detail': 'Restored'})


@api_view(['DELETE'])
@permission_classes([permissions.IsAdminUser])
def admin_purge_folder(request, pk):
    try:
        folder = Folder.objects.get(pk=pk)
    except Folder.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)
    # Delete physical files in tree, then delete folders
    def iter_descendants(root: Folder):
        pending = [root]
        seen = set()
        while pending:
            f = pending.pop()
            if f.id in seen:
                continue
            seen.add(f.id)
            yield f
            for ch in Folder.objects.filter(parent=f).only('id'):
                pending.append(ch)
    for f in iter_descendants(folder):
        for item in FileItem.objects.filter(folder=f).only('id','file'):
            try:
                if item.file:
                    item.file.delete(save=False)
                item.delete()
            except Exception:
                pass
        f.delete()
    return Response({'detail': 'Purged'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def file_toggle_visibility(request, pk):
    try:
        item = FileItem.objects.get(pk=pk)
    except FileItem.DoesNotExist:
        return Response({'detail': 'File not found'}, status=404)
    
    owner = (item.owner_id == request.user.id)
    is_public = str(request.data.get('is_public', '')).lower() in ('1','true','yes','on')

    # Only faculty or admin can make items public. Owners/admins can make private.
    try:
        is_faculty = bool(getattr(request.user.profile, 'is_faculty', False))
    except Exception:
        is_faculty = False

    if is_public:
        if not (request.user.is_staff or (owner and is_faculty)):
            return Response({'detail': 'Only faculty or admin can make files public'}, status=403)
    else:
        if not (request.user.is_staff or owner):
            return Response({'detail': 'Forbidden'}, status=403)

    item.is_public = is_public
    item.save()
    return Response({'detail': 'Updated', 'is_public': item.is_public})


def _set_folder_visibility_recursive(folder: Folder, is_public: bool):
    folder.is_public = is_public
    folder.save()
    for f in folder.files.all():
        f.is_public = is_public
        f.save()
    for ch in folder.children.all():
        _set_folder_visibility_recursive(ch, is_public)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def folder_toggle_visibility(request, pk):
    try:
        folder = Folder.objects.get(pk=pk)
    except Folder.DoesNotExist:
        return Response({'detail': 'Folder not found'}, status=404)
    
    owner = (folder.owner_id == request.user.id)
    is_public = str(request.data.get('is_public', '')).lower() in ('1','true','yes','on')

    # Only faculty or admin can make folders public. Owners/admin can make them private.
    try:
        is_faculty = bool(getattr(request.user.profile, 'is_faculty', False))
    except Exception:
        is_faculty = False

    if is_public:
        if not (request.user.is_staff or (owner and is_faculty)):
            return Response({'detail': 'Only faculty or admin can make folders public'}, status=403)
    else:
        if not (request.user.is_staff or owner):
            return Response({'detail': 'Forbidden'}, status=403)
 
    _set_folder_visibility_recursive(folder, is_public)
    return Response({'detail': 'Updated', 'is_public': is_public})


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_chart_uploads_per_day(request):
    from django.db.models.functions import TruncDate
    qs = FileItem.objects.annotate(day=TruncDate('created_at')) \
        .values('day').order_by('day') \
        .annotate(count=models.Count('id'))
    labels = [x['day'].isoformat() for x in qs]
    data = [x['count'] for x in qs]
    return Response({'labels': labels, 'data': data})


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_chart_files_by_department(request):
    qs = FileItem.objects.values('department__name').order_by('department__name') \
        .annotate(count=models.Count('id'))
    labels = [x['department__name'] or 'Unknown' for x in qs]
    data = [x['count'] for x in qs]
    return Response({'labels': labels, 'data': data})


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_users(request):
    users = User.objects.all().select_related('profile')
    data = []
    for u in users:
        profile = getattr(u, 'profile', None)
        data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'is_staff': u.is_staff,
            'is_superuser': u.is_superuser,
            'is_active': u.is_active,
            'is_faculty': getattr(profile, 'is_faculty', False),
            'department': getattr(profile, 'department_id', None),
        })
    return Response({'users': data})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_user_update(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=404)
    is_staff = request.data.get('is_staff')
    is_superuser = request.data.get('is_superuser')
    is_faculty = request.data.get('is_faculty')
    dept = request.data.get('department')
    if is_staff is not None:
        user.is_staff = str(is_staff).lower() in ('1','true','yes','on')
    if is_superuser is not None:
        user.is_superuser = str(is_superuser).lower() in ('1','true','yes','on')
    user.save()
    from .models import UserProfile, Department
    profile, _ = UserProfile.objects.get_or_create(user=user)
    # Faculty status changes: allow superuser to set True, allow staff/superuser to set False
    if is_faculty is not None:
        requested_val = str(is_faculty).lower() in ('1','true','yes','on')
        if requested_val:
            if not request.user.is_superuser:
                return Response({'detail': 'Only super admin can mark faculty'}, status=403)
        else:
            if not request.user.is_staff and not request.user.is_superuser:
                return Response({'detail': 'Only admin can unmark faculty'}, status=403)
        profile.is_faculty = requested_val
    if dept:
        try:
            profile.department = Department.objects.get(pk=dept)
        except Department.DoesNotExist:
            pass
    profile.save()
    return Response({'detail': 'Updated'})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_session_activate(request, pk):
    try:
        target = AcademicSession.objects.get(pk=pk)
    except AcademicSession.DoesNotExist:
        return Response({'detail': 'Session not found'}, status=404)
    
    # Deactivate all sessions first
    AcademicSession.objects.update(is_active=False)
    
    # Activate the target session using update() to bypass model validation
    AcademicSession.objects.filter(pk=pk).update(is_active=True)
    return Response({'detail': 'Session activated'})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_department_update(request, pk):
    try:
        dept = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response({'detail': 'Department not found'}, status=404)
    
    # Handle head of department
    head = request.data.get('head_of_dept')
    if head is not None:
        try:
            dept.head_of_dept = User.objects.get(pk=head)
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=404)
    
    # Handle department active status
    is_active = request.data.get('is_active')
    if is_active is not None:
        dept.is_active = str(is_active).lower() in ('1','true','yes','on')
    
    # Handle active session override
    active_session_override = request.data.get('active_session_override')
    if active_session_override is not None:
        if active_session_override == '' or active_session_override is None:
            # Clear the override (set to None)
            dept.active_session_override = None
        else:
            try:
                session = AcademicSession.objects.get(pk=active_session_override)
                dept.active_session_override = session
            except AcademicSession.DoesNotExist:
                return Response({'detail': 'Session not found'}, status=404)
    
    dept.save()
    return Response({'detail': 'Department updated'})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_session_deactivate(request, pk):
    try:
        target = AcademicSession.objects.get(pk=pk)
    except AcademicSession.DoesNotExist:
        return Response({'detail': 'Session not found'}, status=404)
    target.is_active = False
    target.save()
    return Response({'detail': 'Session deactivated'})



class SessionListCreateAPI(generics.ListCreateAPIView):
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return all sessions for dashboard selection"""
        # Return all sessions ordered by active status and year
        return AcademicSession.objects.all().order_by('-is_active', '-year')


class SessionRetrieveUpdateAPI(generics.RetrieveUpdateAPIView):
    queryset = AcademicSession.objects.all()
    serializer_class = AcademicSessionSerializer
    permission_classes = [permissions.IsAuthenticated]


class DepartmentListCreateAPI(generics.ListCreateAPIView):
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class FileCategoryListCreateAPI(generics.ListCreateAPIView):
    queryset = FileCategory.objects.all()
    serializer_class = FileCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class FolderListCreateAPI(generics.ListCreateAPIView):
    serializer_class = FolderSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'upload'

    def get_queryset(self):
        qs = Folder.objects.all()
        qs = qs.filter(is_deleted=False)
        if not self.request.user.is_staff:
            # Filter by user's specific active session (including overrides)
            # Exclude manually added folders for non-admin users
            try:
                profile = self.request.user.profile
                user_active_session = profile.get_active_session()
                if user_active_session:
                    qs = qs.filter(owner=self.request.user, session=user_active_session, is_manual=False)
                else:
                    qs = qs.filter(owner=self.request.user, is_manual=False)
            except Exception:
                qs = qs.filter(owner=self.request.user, is_manual=False)
        # Admin users can see all folders including manual ones
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        try:
            profile = user.profile
            session = profile.get_active_session()
            department = profile.department
        except Exception:
            session = None
            department = None
        # Inherit visibility from parent folder if provided
        parent = None
        parent_id = self.request.data.get('parent')
        if parent_id:
            try:
                parent = Folder.objects.get(pk=parent_id)
            except Folder.DoesNotExist:
                parent = None
        is_public_requested = bool(str(self.request.data.get('is_public', '')).lower() in ('1','true','yes','on'))
        # Only allow public if parent is public and user is faculty/admin
        try:
            is_faculty = bool(getattr(user.profile, 'is_faculty', False))
        except Exception:
            is_faculty = False
        if parent:
            # Child inherits parent's visibility regardless of request
            is_public = parent.is_public
        else:
            if is_public_requested:
                # Only faculty or admin can create public root folders
                if not (user.is_staff or is_faculty):
                    is_public = False
                else:
                    is_public = True
            else:
                is_public = False
        serializer.save(owner=user, session=session, department=department, is_public=is_public)


class FolderDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FolderSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Folder.objects.filter(is_deleted=False)

    def destroy(self, request, *args, **kwargs):
        folder: Folder = self.get_object()
        if not (request.user.is_staff or folder.owner_id == request.user.id):
            return Response({'detail': 'Forbidden'}, status=403)
        from django.utils import timezone
        # Soft-delete folder and descendants
        def iter_descendants(root: Folder):
            pending = [root]
            seen = set()
            while pending:
                f = pending.pop()
                if f.id in seen:
                    continue
                seen.add(f.id)
                yield f
                for ch in Folder.objects.filter(parent=f).only('id'):
                    pending.append(ch)
        now = timezone.now()
        for f in iter_descendants(folder):
            Folder.objects.filter(pk=f.pk).update(is_deleted=True, deleted_at=now, deleted_by=request.user)
            FileItem.objects.filter(folder=f, is_deleted=False).update(is_deleted=True, deleted_at=now, deleted_by=request.user)
        # Disable any share links for this folder
        ShareLink.objects.filter(folder=folder).update(is_active=False)
        return Response(status=204)


class FileListCreateAPI(generics.ListCreateAPIView):
    serializer_class = FileItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'upload'

    def get_queryset(self):
        qs = FileItem.objects.filter(is_deleted=False)
        if self.request.user.is_authenticated:
            if not self.request.user.is_staff:
                # Filter by user's specific active session (including overrides)
                # Exclude manually added files for non-admin users
                try:
                    profile = self.request.user.profile
                    user_active_session = profile.get_active_session()
                    if user_active_session:
                        qs = qs.filter(owner=self.request.user, session=user_active_session, is_manual=False)
                    else:
                        qs = qs.filter(owner=self.request.user, is_manual=False)
                except Exception:
                    qs = qs.filter(owner=self.request.user, is_manual=False)
            # Admin users can see all files including manual ones
        else:
            qs = qs.filter(is_public=True, is_manual=False)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        
        # Get session and department from request data first, fallback to profile
        session_id = self.request.data.get('session')
        department_id = self.request.data.get('department')
        
        session = None
        department = None
        
        if session_id:
            try:
                session = AcademicSession.objects.get(pk=session_id)
            except AcademicSession.DoesNotExist:
                pass
        
        if department_id:
            try:
                department = Department.objects.get(pk=department_id)
            except Department.DoesNotExist:
                pass
        
        # Fallback to user profile if not provided in request
        if not session or not department:
            try:
                profile = user.profile
                if not session:
                    session = profile.get_active_session()
                if not department:
                    department = profile.department
            except Exception:
                pass
        
        # Inherit and enforce visibility from parent folder if provided
        is_public_requested = bool(str(self.request.data.get('is_public', '')).lower() in ('1','true','yes','on'))
        folder = None
        folder_id = self.request.data.get('folder')
        if folder_id:
            try:
                folder = Folder.objects.get(pk=folder_id)
                # Files follow folder visibility
                is_public = folder.is_public
            except Folder.DoesNotExist:
                folder = None
        else:
            # No folder: enforce faculty/admin rule for making root files public
            try:
                is_faculty = bool(getattr(user.profile, 'is_faculty', False))
            except Exception:
                is_faculty = False
            if is_public_requested:
                if not (user.is_staff or is_faculty):
                    is_public = False
                else:
                    is_public = True
            else:
                is_public = False
        file_item = serializer.save(
            owner=user,
            name=self.request.data.get('name') or self.request.FILES['file'].name,
            session=session,
            department=department,
            is_public=is_public,
        )
        
        # Log the upload
        FileAuditLog.objects.create(
            file_item=file_item,
            user=self.request.user,
            action='upload',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )


class FileDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FileItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = FileItem.objects.filter(is_deleted=False)
    
    def retrieve(self, request, *args, **kwargs):
        file_item = self.get_object()
        
        # Log the view
        FileAuditLog.objects.create(
            file_item=file_item,
            user=request.user,
            action='view',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return super().retrieve(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        item: FileItem = self.get_object()
        if not (request.user.is_staff or item.owner_id == request.user.id):
            return Response({'detail': 'Forbidden'}, status=403)
        from django.utils import timezone
        item.is_deleted = True
        item.deleted_at = timezone.now()
        item.deleted_by = request.user
        item.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        # Disable share links
        ShareLink.objects.filter(file_item=item).update(is_active=False)
        # Log action
        try:
            FileAuditLog.objects.create(
                file_item=item,
                user=request.user,
                action='delete',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'soft_delete': True}
            )
        except Exception:
            pass
        return Response(status=204)


class ShareResolveAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        link = get_object_or_404(ShareLink, token=token)
        if not link.is_valid():
            return Response({"detail": "Link expired or invalid"}, status=410)
        
        # Check access permissions
        if link.share_type == 'email':
            if not request.user.is_authenticated or request.user.email.lower() != link.email.lower():
                return Response({"detail": "Email access required"}, status=403)
        elif link.share_type == 'password':
            password = request.GET.get('password')
            if not password or password != link.password:
                return Response({"detail": "Password required"}, status=401)
        
        # File share (JSON)
        if link.file_item_id:
            item = link.file_item
            link.download_count += 1
            link.save()
            if request.user.is_authenticated:
                FileAuditLog.objects.create(
                    file_item=item,
                    user=request.user,
                    action='download',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            # Build safe minimal payload without touching FileField.url when missing
            try:
                file_url = item.file.url
            except Exception:
                file_url = ''
            return Response({
                'id': item.id,
                'name': item.name,
                'file': file_url,
                'is_public': item.is_public,
                'file_size': item.file_size,
                'download_count': item.download_count,
                'department': item.department_id,
                'session': item.session_id,
            })

        # Folder share: return folder tree (recursive) and metadata
        folder = link.folder
        def serialize_folder_contents(f):
            children = Folder.objects.filter(parent=f, is_deleted=False)
            files = FileItem.objects.filter(folder=f, is_deleted=False)
            return {
                'id': f.id,
                'name': f.name,
                'children': [serialize_folder_contents(ch) for ch in children],
                'files': FileItemSerializer(files, many=True).data,
            }
        data = serialize_folder_contents(folder)
        return Response(data)


def share_view(request, token):
    """Render a proper HTML page for share links instead of JSON API response"""
    from django.shortcuts import render
    from django.http import Http404
    
    try:
        link = ShareLink.objects.get(token=token)
    except ShareLink.DoesNotExist:
        from django.shortcuts import render
        return render(request, 'storage/share_error.html', {
            'error_type': 'not_found',
            'message': 'This share link was not found or may have been deleted.'
        }, status=404)
    
    # Check if link is valid
    if not link.is_valid():
        return render(request, 'storage/share_error.html', {
            'error_type': 'expired',
            'message': 'This share link has expired or is no longer valid.'
        })
    
    # Check access permissions
    if link.share_type == 'email':
        if not request.user.is_authenticated or request.user.email.lower() != link.email.lower():
            return render(request, 'storage/share_error.html', {
                'error_type': 'email_required',
                'message': 'This share link requires email authentication. Please log in with the correct email address.'
            })
    elif link.share_type == 'password':
        password = request.GET.get('password')
        if not password or password != link.password:
            return render(request, 'storage/share_password.html', {
                'token': token,
                'error': 'Invalid password' if password else None
            })
    
    # Increment download count
    link.download_count += 1
    link.save()
    
    # Log the access
    if request.user.is_authenticated:
        if link.file_item:
            FileAuditLog.objects.create(
                file_item=link.file_item,
                user=request.user,
                action='view',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
    
    # Prepare context data
    context = {
        'link': link,
        'share_type': link.share_type,
        'created_by': link.created_by,
        'created_at': link.created_at,
        'download_count': link.download_count,
    }
    
    if link.file_item:
        # File share
        # Format file size
        file_size = link.file_item.file_size or 0
        if file_size < 1024:
            file_size_display = f"{file_size} B"
        elif file_size < 1024 * 1024:
            file_size_display = f"{file_size // 1024} KB"
        else:
            file_size_display = f"{file_size // (1024 * 1024)} MB"

        # Get file extension
        file_extension = ''
        if link.file_item.original_filename:
            file_extension = link.file_item.original_filename.split('.')[-1].upper()

        # Guard missing physical file to avoid exceptions during tests or manual records
        try:
            file_url = link.file_item.file.url
        except Exception:
            file_url = ''

        context.update({
            'item': link.file_item,
            'item_type': 'file',
            'file_url': file_url,
            'file_name': link.file_item.name,
            'file_size': file_size_display,
            'file_extension': file_extension,
        })
        if not file_url:
            return render(request, 'storage/file_missing.html', context, status=404)
        return render(request, 'storage/share_file.html', context)
    else:
        # Folder share
        def serialize_folder_contents(f):
            children = Folder.objects.filter(parent=f)
            files = FileItem.objects.filter(folder=f)
            
            # Format file data
            files_data = []
            for file in files:
                # Format file size
                file_size = file.file_size
                if file_size < 1024:
                    file_size_display = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    file_size_display = f"{file_size // 1024} KB"
                else:
                    file_size_display = f"{file_size // (1024 * 1024)} MB"
                
                # Get file extension
                file_extension = ''
                if file.original_filename:
                    file_extension = file.original_filename.split('.')[-1].upper()
                
                files_data.append({
                    'id': file.id,
                    'name': file.name,
                    'file_url': file.file.url,
                    'file_size': file_size_display,
                    'file_extension': file_extension,
                })
            
            return {
                'id': f.id,
                'name': f.name,
                'children': [serialize_folder_contents(ch) for ch in children],
                'files': files_data,
            }
        
        import json
        context.update({
            'item': link.folder,
            'item_type': 'folder',
            'folder_name': link.folder.name,
            'folder_contents': json.dumps(serialize_folder_contents(link.folder)),
        })
        return render(request, 'storage/share_folder.html', context)


class ShareLinkCreateAPI(generics.ListCreateAPIView):
    serializer_class = ShareLinkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ShareLink.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        share_link = serializer.save(created_by=self.request.user, is_active=True)
        
        # Log the share (only if file)
        if share_link.file_item_id:
            FileAuditLog.objects.create(
                file_item=share_link.file_item,
                user=self.request.user,
                action='share',
                ip_address=self.request.META.get('REMOTE_ADDR'),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                details={'share_type': share_link.share_type, 'email': share_link.email, 'folder': share_link.folder_id}
            )
        
        # Send email notifications
        from .email_utils import send_file_shared_email, send_public_file_notification
        
        # Send email to specific recipient if email is provided
        if share_link.email and share_link.share_type in ['email', 'password']:
            send_file_shared_email(share_link, recipient_email=share_link.email)
        
        # Send notification for public shares
        if share_link.share_type == 'public':
            send_public_file_notification(share_link)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_folder_tree(request):
	# Recursive tree: sessions -> departments -> folders/files (public only)
	def serialize_folder(folder):
		children = Folder.objects.filter(parent=folder, is_public=True, is_deleted=False)
		files = FileItem.objects.filter(folder=folder, is_public=True, is_deleted=False)
		return {
			'id': folder.id,
			'name': folder.name,
			'children': [serialize_folder(ch) for ch in children],
			'files': FileItemSerializer(files, many=True).data,
		}

	# Get all sessions (active first, then archived) and all active departments
	all_sessions = AcademicSession.objects.all().order_by('-is_active', '-year')
	departments = Department.objects.filter(is_active=True)
	data = []

	for session in all_sessions:
		s_obj = {
			"id": session.id,
			"name": session.name,
			"year": session.year,
			"is_active": session.is_active,
			"departments": []
		}

		# For each session, include ALL departments; attach their public content scoped to that session
		for department in departments:
			root_folders = Folder.objects.filter(
				session=session,
				department=department,
				is_public=True,
				is_deleted=False,
				parent__isnull=True
			)
			root_files = FileItem.objects.filter(
				session=session,
				department=department,
				is_public=True,
				is_deleted=False,
				folder__isnull=True
			)

			d_obj = {
				"id": department.id,
				"name": department.name,
				"folders": [serialize_folder(f) for f in root_folders],
				"files": FileItemSerializer(root_files, many=True).data
			}
			s_obj["departments"].append(d_obj)

		# Always include the session
		data.append(s_obj)

	return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def folder_children(request, pk):
    folder = get_object_or_404(Folder, pk=pk)
    subfolders = Folder.objects.filter(parent=folder, is_deleted=False)
    files = FileItem.objects.filter(folder=folder, is_deleted=False)
    return Response({
        'folder': FolderSerializer(folder).data,
        'children': FolderSerializer(subfolders, many=True).data,
        'files': FileItemSerializer(files, many=True).data,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def session_browse(request):
    """Return folders/files for a given session and department, limited to:
    - Public items of that department
    - PLUS private items owned by the requesting user
    This supports the "Browse Previous Sessions" UI.
    """
    session_id = request.GET.get('session')
    dept_id = request.GET.get('department')

    if not session_id or not dept_id:
        return Response({'detail': 'session and department are required'}, status=400)

    try:
        session = AcademicSession.objects.get(pk=session_id)
        department = Department.objects.get(pk=dept_id)
    except (AcademicSession.DoesNotExist, Department.DoesNotExist):
        return Response({'detail': 'Invalid session or department'}, status=404)

    user = request.user

    # Helper to serialize folder tree recursively with visibility rules
    def serialize_folder_tree(folder: Folder):
        children = Folder.objects.filter(parent=folder, is_deleted=False).filter(
            models.Q(is_public=True) | models.Q(owner=user)
        )
        files = FileItem.objects.filter(folder=folder, is_deleted=False).filter(
            models.Q(is_public=True) | models.Q(owner=user)
        )
        return {
            'id': folder.id,
            'name': folder.name,
            'is_public': folder.is_public,
            'children': [serialize_folder_tree(ch) for ch in children],
            'files': FileItemSerializer(files, many=True).data,
        }

    # Root folders in this session/department visible to user
    root_folders = Folder.objects.filter(
        session=session,
        department=department,
        parent__isnull=True,
        is_deleted=False
    ).filter(
        models.Q(is_public=True) | models.Q(owner=user)
    )

    # Root files (no folder) visible to user
    root_files = FileItem.objects.filter(
        session=session,
        department=department,
        folder__isnull=True,
        is_deleted=False
    ).filter(
        models.Q(is_public=True) | models.Q(owner=user)
    )

    tree = [serialize_folder_tree(f) for f in root_folders]

    return Response({
        'folders_tree': tree,
        'root_files': FileItemSerializer(root_files, many=True).data,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_files(request):
    query = request.GET.get('q', '')
    if not query:
        return Response({"detail": "Query parameter 'q' is required"}, status=400)
    
    files = FileItem.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query) |
        Q(original_filename__icontains=query)
    )
    
    if not request.user.is_staff:
        files = files.filter(Q(owner=request.user) | Q(is_public=True))
    
    serializer = FileItemSerializer(files, many=True)
    # Do not echo raw query back to avoid reflecting unescaped input
    return Response({
        'results': serializer.data,
        'count': files.count()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_profile(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    except UserProfile.DoesNotExist:
        return Response({"detail": "Profile not found"}, status=404)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_profile(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        # Restrict department change: only staff can change once set
        if 'department' in request.data:
            # If department already set and user is not staff, block
            if profile.department_id and not request.user.is_staff:
                return Response({"detail": "Department change not allowed"}, status=403)
        data = request.data.copy()
        # Prevent non-superusers from modifying faculty status via profile update
        if 'is_faculty' in data and not request.user.is_superuser:
            data.pop('is_faculty')
        serializer = UserProfileSerializer(profile, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    except UserProfile.DoesNotExist:
        return Response({"detail": "Profile not found"}, status=404)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_profile_user(request):
    user: User = request.user
    username = request.data.get('username')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    email = request.data.get('email')
    # Basic validations
    if username and username != user.username:
        if User.objects.filter(username=username).exclude(pk=user.pk).exists():
            return Response({'detail': 'Username already taken'}, status=400)
        user.username = username
    if email and email != user.email:
        if User.objects.filter(email=email).exclude(pk=user.pk).exists():
            return Response({'detail': 'Email already in use'}, status=400)
        user.email = email
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    user.save()
    return Response({'detail': 'Profile updated'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_profile_password(request):
    user: User = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    if not new_password:
        return Response({'detail': 'New password required'}, status=400)
    # If current_password provided, verify
    if current_password is not None and not user.check_password(current_password):
        return Response({'detail': 'Current password is incorrect'}, status=400)
    user.set_password(new_password)
    user.save()
    return Response({'detail': 'Password changed'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    serializer = FileItemSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({"detail": "Notification marked as read"})
    except Notification.DoesNotExist:
        return Response({"detail": "Notification not found"}, status=404)


# Log Management Views
import os
import zipfile
import tempfile
from django.http import HttpResponse, Http404
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_log_files(request):
    """List all available log files for the user"""
    if not request.user.is_staff:
        return Response({"detail": "Permission denied"}, status=403)
    
    log_files = LogFile.objects.filter(is_active=True).order_by('-generated_at')
    serializer = LogFileSerializer(log_files, many=True, context={'request': request})
    return Response(serializer.data)

@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_log_file(request):
    """Generate a new log file"""
    if not request.user.is_staff:
        return Response({"detail": "Permission denied"}, status=403)
    
    log_type = request.data.get('log_type', 'general')
    days_back = int(request.data.get('days_back', 7))
    include_errors = request.data.get('include_errors', True)
    
    try:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Generate filename
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"mits_cloud_{log_type}_{timestamp}.log"
        file_path = os.path.join(logs_dir, filename)
        
        # Collect log content
        log_content = []
        
        # Add general logs
        general_log_path = os.path.join(logs_dir, 'mits_cloud.log')
        if os.path.exists(general_log_path):
            with open(general_log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Get last N days of logs
                cutoff_date = timezone.now() - timedelta(days=days_back)
                for line in lines:
                    if log_type == 'general' or 'INFO' in line or 'DEBUG' in line:
                        log_content.append(line)
        
        # Add error logs if requested
        if include_errors:
            error_log_path = os.path.join(logs_dir, 'mits_cloud_errors.log')
            if os.path.exists(error_log_path):
                with open(error_log_path, 'r', encoding='utf-8') as f:
                    error_lines = f.readlines()
                    log_content.extend([f"[ERROR] {line}" for line in error_lines])
        
        # Write to new log file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"MITS Cloud Log File\n")
            f.write(f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Log Type: {log_type}\n")
            f.write(f"Days Back: {days_back}\n")
            f.write(f"Generated By: {request.user.username}\n")
            f.write("=" * 80 + "\n\n")
            f.writelines(log_content)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create LogFile record
        log_file = LogFile.objects.create(
            name=filename,
            log_type=log_type,
            file_path=file_path,
            file_size=file_size,
            generated_by=request.user,
            expires_at=timezone.now() + timedelta(days=30)  # Expire after 30 days
        )
        
        # Log the action
        logger.info(f"Log file generated: {filename} by {request.user.username}")
        
        serializer = LogFileSerializer(log_file, context={'request': request})
        return Response(serializer.data, status=201)
        
    except Exception as e:
        logger.error(f"Error generating log file: {str(e)}")
        return Response({"detail": f"Error generating log file: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_log_file(request, pk):
    """Download a specific log file"""
    if not request.user.is_staff:
        return Response({"detail": "Permission denied"}, status=403)
    
    try:
        log_file = LogFile.objects.get(pk=pk, is_active=True)
        
        # Check if file exists
        if not os.path.exists(log_file.file_path):
            return Response({"detail": "Log file not found"}, status=404)
        
        # Check if expired
        if log_file.is_expired():
            return Response({"detail": "Log file has expired"}, status=410)
        
        # Increment download count
        log_file.download_count += 1
        log_file.save()
        
        # Read file content
        with open(log_file.file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{log_file.name}"'
            response['Content-Length'] = log_file.file_size
            return response
            
    except LogFile.DoesNotExist:
        return Response({"detail": "Log file not found"}, status=404)
    except Exception as e:
        logger.error(f"Error downloading log file: {str(e)}")
        return Response({"detail": f"Error downloading log file: {str(e)}"}, status=500)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_log_file(request, pk):
    """Delete a log file"""
    if not request.user.is_staff:
        return Response({"detail": "Permission denied"}, status=403)
    
    try:
        log_file = LogFile.objects.get(pk=pk, is_active=True)
        
        # Delete physical file
        if os.path.exists(log_file.file_path):
            os.remove(log_file.file_path)
        
        # Mark as inactive
        log_file.is_active = False
        log_file.save()
        
        logger.info(f"Log file deleted: {log_file.name} by {request.user.username}")
        return Response({"detail": "Log file deleted successfully"})
        
    except LogFile.DoesNotExist:
        return Response({"detail": "Log file not found"}, status=404)
    except Exception as e:
        logger.error(f"Error deleting log file: {str(e)}")
        return Response({"detail": f"Error deleting log file: {str(e)}"}, status=500)

