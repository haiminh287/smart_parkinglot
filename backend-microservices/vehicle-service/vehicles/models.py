"""
Models for vehicle-service with proper user relationship.
"""

import uuid
from django.db import models

# Import proxy User model for session authentication
from .models_user import User


class Vehicle(models.Model):
    """
    Vehicle model - Stores user vehicles.
    Note: user_id is UUID reference to auth-service (microservice pattern).
    """

    VEHICLE_TYPE_CHOICES = [
        ('Car', 'Car'),
        ('Motorbike', 'Motorbike'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)  # Reference to auth-service User
    license_plate = models.CharField(max_length=50, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=50, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['license_plate']),
        ]

    def __str__(self):
        return f"{self.license_plate} ({self.vehicle_type})"
    
    def save(self, *args, **kwargs):
        # If this is set as default, unset all other defaults for this user
        if self.is_default:
            Vehicle.objects.filter(user_id=self.user_id, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
