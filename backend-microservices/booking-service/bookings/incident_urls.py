"""
URL configuration for incidents in booking-service.
"""

from django.urls import path
from .incident_views import IncidentViewSet

# Gateway sends /incidents/... → main urls.py strips to /
urlpatterns = [
    path('', IncidentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='incident-list'),
    
    # User's own incidents
    path('my/', IncidentViewSet.as_view({
        'get': 'my_incidents'
    }), name='incident-my'),
    
    # Nearby camera lookup
    path('nearby-camera/', IncidentViewSet.as_view({
        'get': 'nearby_camera'
    }), name='incident-nearby-camera'),
    
    path('<uuid:pk>/', IncidentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='incident-detail'),
    
    path('<uuid:pk>/resolve/', IncidentViewSet.as_view({
        'post': 'resolve'
    }), name='incident-resolve'),
    
    path('<uuid:pk>/cancel/', IncidentViewSet.as_view({
        'post': 'cancel_incident'
    }), name='incident-cancel'),
    
    path('<uuid:pk>/request-security/', IncidentViewSet.as_view({
        'post': 'request_security'
    }), name='incident-request-security'),
]
