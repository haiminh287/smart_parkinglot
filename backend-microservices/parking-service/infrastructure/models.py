"""
Models for parking-service with proper ForeignKey relationships.
"""

import uuid
from django.db import models

# Import proxy User model for session authentication
from .models_user import User


class ParkingLot(models.Model):
    """ParkingLot model - Root entity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    total_slots = models.IntegerField()
    available_slots = models.IntegerField(default=0)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=10000)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'parking_lot'
        ordering = ['name']
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['is_open']),
        ]

    def __str__(self):
        return self.name


class Floor(models.Model):
    """Floor model - Belongs to ParkingLot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='floors')
    level = models.IntegerField()
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'floor'
        unique_together = [['parking_lot', 'level']]
        ordering = ['level']

    def __str__(self):
        return f"{self.parking_lot.name} - {self.name}"


class Zone(models.Model):
    """Zone model - Belongs to Floor."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=20, choices=[('Car', 'Car'), ('Motorbike', 'Motorbike')])
    capacity = models.IntegerField()
    available_slots = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'zone'
        indexes = [
            models.Index(fields=['vehicle_type']),
        ]

    def __str__(self):
        return f"{self.floor.parking_lot.name} - {self.floor.name} - {self.name}"
    
    @property
    def occupied_slots(self):
        return self.slots.filter(status='occupied').count()
    
    @property
    def reserved_slots(self):
        return self.slots.filter(status='reserved').count()


class CarSlot(models.Model):
    """CarSlot model - Belongs to Zone."""
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Maintenance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='slots')
    code = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    camera = models.ForeignKey('Camera', on_delete=models.SET_NULL, null=True, blank=True, related_name='monitored_slots')
    
    # Bounding box coordinates for AI detection
    x1 = models.IntegerField(null=True, blank=True)
    y1 = models.IntegerField(null=True, blank=True)
    x2 = models.IntegerField(null=True, blank=True)
    y2 = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'car_slot'
        unique_together = [['zone', 'code']]
        ordering = ['code']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.code} ({self.zone.name})"


class Camera(models.Model):
    """Camera model - Belongs to Zone."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=45)
    port = models.IntegerField()
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='cameras', null=True, blank=True)
    stream_url = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'infrastructure_camera'

    def __str__(self):
        return str(self.id)


