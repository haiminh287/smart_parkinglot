from django.http import JsonResponse
"""
URL configuration for parking_service project.
"""

from django.urls import path, include

urlpatterns = [
    path('health/', lambda r: JsonResponse({'status': 'ok', 'service': 'parking-service'})),
    path('parking/health/', lambda r: JsonResponse({'status': 'ok', 'service': 'parking-service'})),
    path('parking/', include('infrastructure.urls')),  # Gateway sends /parking/...
]
