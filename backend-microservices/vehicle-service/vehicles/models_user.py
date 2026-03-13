"""
Proxy User model for microservice authentication.
"""
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
import uuid

class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    
    class Meta:
        db_table = 'auth_user_proxy'
        managed = False  # Table managed by parking-service
    
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
    
    def has_perm(self, perm, obj=None):
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        return self.is_superuser
