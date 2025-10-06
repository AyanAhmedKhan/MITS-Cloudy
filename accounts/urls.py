from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.OneClickGoogleAuthView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('signup/', views.OneClickGoogleAuthView.as_view(), name='signup'),
    path('department-setup/', views.DepartmentSetupView.as_view(), name='department_setup'),
]


