from django.urls import path
from . import views

urlpatterns = [
    # Core APIs
    path('sessions/', views.SessionListCreateAPI.as_view(), name='api-sessions'),
    path('sessions/<int:pk>/', views.SessionRetrieveUpdateAPI.as_view(), name='api-session-detail'),
    path('departments/', views.DepartmentListCreateAPI.as_view(), name='api-departments'),
    path('categories/', views.FileCategoryListCreateAPI.as_view(), name='api-categories'),
    
    # Folder and File APIs
    path('folders/', views.FolderListCreateAPI.as_view(), name='api-folders'),
    path('folders/<int:pk>/', views.FolderDetailAPI.as_view(), name='api-folder-detail'),
    path('folders/<int:pk>/children/', views.folder_children, name='api-folder-children'),
    path('browse/session/', views.session_browse, name='api-session-browse'),
    path('files/', views.FileListCreateAPI.as_view(), name='api-files'),
    path('files/<int:pk>/', views.FileDetailAPI.as_view(), name='api-file-detail'),
    
    # Sharing APIs
    path('share/', views.ShareLinkCreateAPI.as_view(), name='api-share-create'),
    path('share/<uuid:token>/', views.ShareResolveAPI.as_view(), name='api-share-resolve'),
    
    # Public APIs
    path('public-tree/', views.public_folder_tree, name='api-public-tree'),
    
    # Search and Utility APIs
    path('search/', views.search_files, name='api-search'),
    path('profile/', views.user_profile, name='api-profile'),
    path('profile/update/', views.update_profile, name='api-profile-update'),
    path('profile/user/update/', views.update_profile_user, name='api-profile-user-update'),
    path('profile/password/update/', views.update_profile_password, name='api-profile-password-update'),
    path('notifications/', views.notifications, name='api-notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='api-notification-read'),

    # Admin dashboard APIs
    path('admin/stats/', views.admin_stats, name='api-admin-stats'),
    path('admin/recent/', views.admin_recent_activity, name='api-admin-recent'),
    path('admin/sessions/', views.admin_all_sessions, name='api-admin-sessions'),
    path('admin/scan-manual-files/', views.admin_scan_manual_files, name='api-admin-scan-manual-files'),
    path('admin/charts/uploads-per-day/', views.admin_chart_uploads_per_day, name='api-admin-chart-uploads'),
    path('admin/charts/files-by-department/', views.admin_chart_files_by_department, name='api-admin-chart-dept'),
    path('admin/users/', views.admin_users, name='api-admin-users'),
    path('admin/users/<int:pk>/update/', views.admin_user_update, name='api-admin-user-update'),
    path('admin/sessions/<int:pk>/activate/', views.admin_session_activate, name='api-admin-session-activate'),
    path('admin/sessions/<int:pk>/deactivate/', views.admin_session_deactivate, name='api-admin-session-deactivate'),
    path('admin/departments/<int:pk>/update/', views.admin_department_update, name='api-admin-dept-update'),
    path('admin/allowed-extensions/', views.admin_allowed_extensions, name='api-admin-allowed-extensions'),

    # Visibility toggles
    path('files/<int:pk>/visibility/', views.file_toggle_visibility, name='api-file-visibility'),
    path('folders/<int:pk>/visibility/', views.folder_toggle_visibility, name='api-folder-visibility'),
    
    # Log Management APIs
    path('logs/', views.list_log_files, name='api-logs-list'),
    path('logs/generate/', views.generate_log_file, name='api-logs-generate'),
    path('logs/<int:pk>/download/', views.download_log_file, name='api-logs-download'),
    path('logs/<int:pk>/delete/', views.delete_log_file, name='api-logs-delete'),
]


