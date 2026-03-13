from django.http import JsonResponse
"""
URL configuration for booking_service project.
"""

from django.urls import path, include
from bookings.echo_views import echo_headers
from bookings.debug_views import debug_user

urlpatterns = [
    path('health/', lambda r: JsonResponse({'status': 'ok', 'service': 'booking-service'})),
    path('bookings/health/', lambda r: JsonResponse({'status': 'ok', 'service': 'booking-service'})),
    path('incidents/health/', lambda r: JsonResponse({'status': 'ok', 'service': 'booking-service'})),
    path('_test/echo/', echo_headers),
    path('_debug/user/', debug_user),
    path('bookings/', include('bookings.urls')),  # Gateway sends /bookings/...
    path('bookings/admin/', include('bookings.admin_urls')),  # Admin revenue endpoints
    path('incidents/', include('bookings.incident_urls')),  # Gateway sends /incidents/...
]
