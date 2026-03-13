"""
Admin configuration for bookings app.
"""

from django.contrib import admin
from .models import PackagePricing, Booking
from .incident_models import Incident


@admin.register(PackagePricing)
class PackagePricingAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    ordering = ['-created_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    ordering = ['-created_at']


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'status', 'user_id', 'security_notified', 'created_at']
    list_filter = ['status', 'type', 'security_notified']
    search_fields = ['user_id', 'description']
    ordering = ['-created_at']


