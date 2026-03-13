"""
Admin configuration for infrastructure app.
"""

from django.contrib import admin
from .models import ParkingLot, Floor, Zone, CarSlot, Camera


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    ordering = ['-created_at']


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    ordering = ['-created_at']


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    ordering = ['-created_at']


@admin.register(CarSlot)
class CarSlotAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    ordering = ['-created_at']


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    ordering = ['-created_at']


