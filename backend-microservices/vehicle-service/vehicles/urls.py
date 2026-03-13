"""
URL configuration for vehicle-service.
"""

from django.urls import path
from . import views

# Gateway sends /vehicles/... → main urls.py strips to /
# So these URLs are relative: / → list, /<pk>/ → detail
urlpatterns = [
    # List and create
    path('', views.VehicleViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='vehicle-list'),
    
    # Detail, update, delete
    path('<uuid:pk>/', views.VehicleViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='vehicle-detail'),
    
    # Custom actions
    path('<uuid:pk>/set-default/', views.VehicleViewSet.as_view({
        'post': 'set_default'
    }), name='vehicle-set-default'),
    
    path('default/', views.VehicleViewSet.as_view({
        'get': 'get_default'
    }), name='vehicle-get-default'),
]
