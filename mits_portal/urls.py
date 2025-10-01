"""
URL configuration for mits_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from storage.views import share_view
from core.views import (
    custom_permission_denied_view,
    custom_page_not_found_view,
    custom_server_error_view,
    media_serve,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('auth/', include('accounts.urls')),  # Changed from 'accounts/' to 'auth/'
    path('', include('core.urls')),
    path('api/', include('storage.api_urls')),
    path('share/<uuid:token>/', share_view, name='share-view'),
]

# Always serve media through our view (backed by web server for performance in production)
from django.urls import re_path
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', media_serve, name='media'),
]

# Custom error handlers
handler403 = custom_permission_denied_view
handler404 = custom_page_not_found_view
handler500 = custom_server_error_view
