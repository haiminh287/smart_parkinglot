"""
Proxy User model for microservice authentication.
Since user authentication happens in auth-service, this service
only needs a minimal User model to store the UUID from sessions.
"""

from django.contrib.auth.models import AbstractBaseUser
from django.db import models
import uuid


class User(AbstractBaseUser):
    """
    Minimal proxy User model for session authentication.
    The actual User data lives in auth-service.
    This model only stores the UUID for session management.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    
    # Required for Django admin
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    
    class Meta:
        db_table = 'auth_user_proxy'
        managed = True  # Allow Django to manage this table for migration
    
    def __str__(self):
        return self.email
    
    # CRITICAL: Required for session authentication
    @property
    def is_authenticated(self):
        """Always return True for logged-in users."""
        return True
    
    @property
    def is_anonymous(self):
        """Always return False for logged-in users."""
        return False
    
    # Minimal permissions for compatibility
    def has_perm(self, perm, obj=None):
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        return self.is_superuser
