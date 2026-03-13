"""
Custom authentication backend to support UUID primary keys.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class UUIDModelBackend(ModelBackend):
    """
    Custom authentication backend that properly handles UUID primary keys.
    Django's default backend expects integer PKs for session storage.
    
    For microservices without their own User table, this creates
    a lightweight User object from session data.
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
            
            # For unmanaged proxy models, create an in-memory User object
            if UserModel._meta.managed is False:
                user = UserModel(
                    id=user_id,
                    email=f"user-{user_id}@system",
                    is_active=True,
                    is_staff=False,
                    is_superuser=False
                )
                user.backend = f'{self.__module__}.{self.__class__.__name__}'
                return user
            
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        except Exception:
            return None

