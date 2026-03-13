"""
Incident model for reporting parking incidents.
"""
import uuid
from django.db import models
from django.utils import timezone


class Incident(models.Model):
    """Incident model - User reports incidents (panic button, theft, damage, etc.)"""
    
    TYPE_CHOICES = [
        ('emergency', 'Emergency'),
        ('theft', 'Theft'),
        ('vehicle_damage', 'Vehicle Damage'),
        ('accident', 'Accident'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User who reported
    user_id = models.UUIDField()
    
    # Incident details
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Location (optional - may not have booking)
    booking_id = models.UUIDField(null=True, blank=True)
    parking_lot_id = models.UUIDField(null=True, blank=True)
    zone_id = models.UUIDField(null=True, blank=True)
    slot_id = models.UUIDField(null=True, blank=True)
    
    # Geolocation
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Security response
    security_notified = models.BooleanField(default=False)
    security_notified_at = models.DateTimeField(null=True, blank=True)
    
    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.UUIDField(null=True, blank=True)  # Admin/security user_id
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'incident'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['user_id', '-id']),
            models.Index(fields=['status']),
            models.Index(fields=['type']),
        ]
    
    def __str__(self):
        return f"{self.type} - {self.status} ({self.created_at})"
