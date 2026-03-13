"""
Custom authentication backend to support UUID primary keys.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class UUIDModelBackend(ModelBackend):
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            if isinstance(user_id, str):
                import uuid
                try:
                    user_id = uuid.UUID(user_id)
                except (ValueError, AttributeError):
                    return None
            
            # For unmanaged proxy models, create in-memory User
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
