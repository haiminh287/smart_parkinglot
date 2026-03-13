"""
Custom authentication backend to support UUID primary keys.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class UUIDModelBackend(ModelBackend):
    """
    Custom authentication backend that properly handles UUID primary keys.
    Django's default backend expects integer PKs for session storage.
    """
    
    def get_user(self, user_id):
        """
        Override get_user to handle UUID conversion.
        
        Args:
            user_id: Can be either string (UUID) or UUID object
            
        Returns:
            User object or None
        """
        UserModel = get_user_model()
        try:
            # Convert string to UUID if needed
            if isinstance(user_id, str):
                import uuid
                try:
                    user_id = uuid.UUID(user_id)
                except (ValueError, AttributeError):
                    return None
            
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
