"""
Custom authentication backend to support UUID primary keys.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging


logger = logging.getLogger(__name__)


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
        logger.debug("UUIDModelBackend.get_user called with user_id=%s type=%s", user_id, type(user_id))
        UserModel = get_user_model()
        try:
            # Convert string to UUID if needed
            if isinstance(user_id, str):
                import uuid
                try:
                    user_id = uuid.UUID(user_id)
                    logger.debug("Converted user_id to UUID: %s", user_id)
                except (ValueError, AttributeError):
                    logger.warning("Invalid UUID format: %s", user_id)
                    return None
            
            # For unmanaged proxy models, create an in-memory User object
            # instead of querying the database
            if UserModel._meta.managed is False:
                logger.debug("Creating in-memory User for UUID: %s", user_id)
                user = UserModel(
                    id=user_id,
                    email=f"user-{user_id}@system",
                    is_active=True,
                    is_staff=False,
                    is_superuser=False
                )
                # Mark as authenticated
                user.backend = f'{self.__module__}.{self.__class__.__name__}'
                logger.debug("In-memory user created for UUID: %s", user_id)
                return user
            
            # For managed models, query normally
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            logger.warning("User not found for UUID: %s", user_id)
            return None
        except Exception as e:
            logger.error("Error getting user in UUIDModelBackend: %s", e)
            return None

