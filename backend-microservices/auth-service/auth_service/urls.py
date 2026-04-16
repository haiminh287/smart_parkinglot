from django.http import JsonResponse

"""
URL configuration for auth_service project.
"""

from django.urls import include, path

urlpatterns = [
    path('health/', lambda r: JsonResponse({'status': 'ok', 'service': 'auth-service'})),
    path('auth/health/', lambda r: JsonResponse({'status': 'ok', 'service': 'auth-service'})),
    # admin/ removed — gateway trust model, no admin interface
    path('auth/', include('users.urls')),  # Gateway sends /auth/login/, /auth/register/, etc.
]
]
