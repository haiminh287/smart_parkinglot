from django.http import JsonResponse
"""
URL configuration for vehicle_service project.
"""

from django.urls import path, include

urlpatterns = [
    path('health/', lambda r: JsonResponse({'status': 'ok', 'service': 'vehicle-service'})),
    path('vehicles/health/', lambda r: JsonResponse({'status': 'ok', 'service': 'vehicle-service'})),
    path('vehicles/', include('vehicles.urls')),  # Gateway sends /vehicles/...
]
