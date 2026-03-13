from django.http import JsonResponse
"""
URL configuration for auth_service project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('health/', lambda r: JsonResponse({'status': 'ok', 'service': 'auth-service'})),
    path('auth/health/', lambda r: JsonResponse({'status': 'ok', 'service': 'auth-service'})),
    path('admin/', admin.site.urls),
    path('auth/', include('users.urls')),  # Gateway sends /auth/login/, /auth/register/, etc.
]
