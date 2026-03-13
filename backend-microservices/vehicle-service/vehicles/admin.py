"""
Admin configuration for vehicles app.
"""

from django.contrib import admin
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    ordering = ['-created_at']


