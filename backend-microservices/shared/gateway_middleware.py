"""
Gateway authentication middleware for microservices.

Microservices should ONLY accept requests from gateway.
Gateway adds user context in headers: X-User-ID, X-User-Email, X-Gateway-Secret

This middleware:
1. Validates gateway secret
2. Extracts user info from headers
3. Sets request.user_id and request.user_email (NOT request.user)
"""
from django.http import JsonResponse
from django.conf import settings


class GatewayAuthMiddleware:
    """
    Lightweight middleware for gateway-based authentication.
    
    Does NOT use Django's User model or authentication system.
    Simply extracts user context from trusted gateway headers.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip for health checks and test endpoints
        if request.path.endswith('/health/') or '/_test/' in request.path:
            return self.get_response(request)
        
        # Public endpoints that don't need gateway secret
        public_paths = [
            '/auth/login/', '/auth/register/', '/auth/logout/',
            '/auth/forgot-password/', '/auth/reset-password/',
            '/auth/password-reset/',  # Keep old endpoint for compatibility
            '/auth/google/', '/auth/facebook/'
        ]
        is_public = any(request.path.startswith(path) for path in public_paths)
        
        # Check gateway secret for ALL non-public requests
        gateway_secret = (request.headers.get('X-Gateway-Secret') or '').strip()
        expected_secret = (getattr(settings, 'GATEWAY_SECRET', '') or '').strip()
        
        if not is_public and (not gateway_secret or gateway_secret != expected_secret):
            return JsonResponse({
                'error': 'Forbidden - Direct access not allowed',
                'message': 'All requests must go through API Gateway'
            }, status=403)
        
        # Extract user context from gateway headers
        user_id_str = request.headers.get('X-User-ID')
        user_email = request.headers.get('X-User-Email')
        
        # Set user context on request object
        # Allow user_id without email (inter-service calls may omit email)
        if user_id_str:
            # Store as UUID string (microservices use UUID)
            request.user_id = user_id_str
            request.user_email = user_email or ''
            request.is_authenticated = True
        else:
            # No user context - anonymous request
            request.user_id = None
            request.user_email = None
            request.is_authenticated = False
        
        response = self.get_response(request)
        return response
