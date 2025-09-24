from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('faculty/', views.dashboard, name='faculty'),
    path('super/', views.super_dashboard, name='super-dashboard'),
    path('drag-drop-demo/', views.drag_drop_demo, name='drag-drop-demo'),
]


