"""
Models for booking-service with denormalized data for microservices.
"""

import uuid
from django.db import models

# Import proxy User model for session authentication
from .models_user import User


class PackagePricing(models.Model):
    """PackagePricing model for different booking packages."""

    PACKAGE_TYPES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    VEHICLE_TYPES = [
        ('Car', 'Car'),
        ('Motorbike', 'Motorbike'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'package_pricing'
        unique_together = [['package_type', 'vehicle_type']]

    def __str__(self):
        return f"{self.package_type} - {self.vehicle_type}: {self.price}đ"


class Booking(models.Model):
    """
    Booking model with denormalized data from other services.
    This allows booking-service to operate independently.
    """

    PAYMENT_METHODS = [
        ('online', 'Online'),
        ('on_exit', 'On Exit'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    CHECK_IN_STATUS = [
        ('not_checked_in', 'Not Checked In'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User info (denormalized from auth-service)
    user_id = models.UUIDField(db_index=True)
    user_email = models.EmailField()
    
    # Vehicle info (denormalized from vehicle-service)
    vehicle_id = models.UUIDField()
    vehicle_license_plate = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=20)
    
    # Parking info (denormalized from parking-service)
    parking_lot_id = models.UUIDField()
    parking_lot_name = models.CharField(max_length=255)
    floor_id = models.UUIDField(null=True, blank=True)
    floor_level = models.IntegerField(null=True, blank=True)
    zone_id = models.UUIDField()
    zone_name = models.CharField(max_length=100)
    slot_id = models.UUIDField(null=True, blank=True)
    slot_code = models.CharField(max_length=20, blank=True)
    
    # Booking details
    package_type = models.CharField(max_length=20, default='hourly')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Payment
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Check-in/out
    check_in_status = models.CharField(max_length=20, choices=CHECK_IN_STATUS, default='not_checked_in')
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    
    # QR code for check-in
    qr_code_data = models.TextField(blank=True)
    
    # Hourly package fields
    hourly_start = models.DateTimeField(null=True, blank=True, help_text="Scheduled start time for hourly package")
    hourly_end = models.DateTimeField(null=True, blank=True, help_text="Scheduled end time for hourly package")
    extended_until = models.DateTimeField(null=True, blank=True, help_text="Extended end time if user requests extension")
    late_fee_applied = models.BooleanField(default=False, help_text="Whether late fee was applied for overtime")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'booking'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['slot_id']),
            models.Index(fields=['check_in_status']),
            models.Index(fields=['start_time', 'end_time']),
        ]

    def __str__(self):
        return f"{self.user_email} - {self.slot_code} ({self.check_in_status})"
