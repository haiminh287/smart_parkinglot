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
        print(f"[BACKEND] get_user called with user_id: {user_id}, type: {type(user_id)}")
        UserModel = get_user_model()
        try:
            # Convert string to UUID if needed
            if isinstance(user_id, str):
                import uuid
                try:
                    user_id = uuid.UUID(user_id)
                    print(f"[BACKEND] Converted to UUID: {user_id}")
                except (ValueError, AttributeError):
                    print(f"[BACKEND] Invalid UUID format: {user_id}")
                    return None
            
            # For unmanaged proxy models, create an in-memory User object
            # instead of querying the database
            if UserModel._meta.managed is False:
                print(f"[BACKEND] Creating in-memory User for UUID: {user_id}")
                user = UserModel(
                    id=user_id,
                    email=f"user-{user_id}@system",
                    is_active=True,
                    is_staff=False,
                    is_superuser=False
                )
                # Mark as authenticated
                user.backend = f'{self.__module__}.{self.__class__.__name__}'
                print(f"[BACKEND] User created: {user}, is_authenticated: {user.is_authenticated}")
                return user
            
            # For managed models, query normally
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            print(f"[BACKEND] User not found: {user_id}")
            return None
        except Exception as e:
            print(f"[BACKEND] Error getting user: {e}")
            return None

