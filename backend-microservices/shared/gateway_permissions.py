"""
Custom permissions for gateway-based authentication.

Use these instead of Django's default IsAuthenticated permission.
"""
from rest_framework.permissions import BasePermission


class IsGatewayAuthenticated(BasePermission):
    """
    Permission that checks if request has user_id from gateway.
    
    Gateway sets request.user_id if user is authenticated.
    This is simpler and more reliable than Django's User model.
    """
    
    def has_permission(self, request, view):
        """Check if request has user_id attribute."""
        return bool(getattr(request, 'user_id', None))
    
    message = 'Authentication required'


class IsGatewayAdmin(BasePermission):
    """
    Permission that checks if user is admin via gateway headers.

    Gateway forwards X-User-Is-Staff and X-User-Role headers.
    Falls back to Django User model if available.
    """

    def has_permission(self, request, view):
        # First check gateway headers
        is_staff_header = request.headers.get('X-User-Is-Staff', 'false')
        role_header = request.headers.get('X-User-Role', '')
        if is_staff_header == 'true' or role_header == 'admin':
            return True
        # Fallback to Django user model (for direct access / tests)
        user = getattr(request, 'user', None)
        if user and hasattr(user, 'is_staff'):
            return user.is_staff
        return False

    message = 'Admin access required'
