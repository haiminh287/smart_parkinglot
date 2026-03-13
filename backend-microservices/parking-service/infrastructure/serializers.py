"""
Serializers for parking-service.

Uses snake_case field names. The djangorestframework-camel-case library
(CamelCaseJSONRenderer / CamelCaseJSONParser) automatically converts:
  - Response output: snake_case → camelCase
  - Request input:   camelCase → snake_case
This avoids the "double conversion" bug where camelCase serializer field
names + CamelCaseJSONParser caused input keys to be unrecognised.
"""

from rest_framework import serializers
from .models import ParkingLot, Floor, Zone, CarSlot, Camera


class ParkingLotSerializer(serializers.ModelSerializer):
    """Serializer for ParkingLot model."""

    class Meta:
        model = ParkingLot
        fields = [
            'id', 'name', 'address', 'latitude', 'longitude',
            'total_slots', 'available_slots', 'price_per_hour',
            'is_open', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ZoneSerializer(serializers.ModelSerializer):
    """Serializer for Zone model."""

    floor_level = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            'id', 'floor', 'floor_level', 'name', 'vehicle_type',
            'capacity', 'available_slots', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_floor_level(self, obj):
        """Get the floor level from the related Floor."""
        if obj.floor:
            return obj.floor.level
        return None


class FloorSerializer(serializers.ModelSerializer):
    """Serializer for Floor model with nested zones."""

    zones = ZoneSerializer(many=True, read_only=True)

    class Meta:
        model = Floor
        fields = [
            'id', 'parking_lot', 'level', 'name', 'zones',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CarSlotSerializer(serializers.ModelSerializer):
    """Serializer for CarSlot model with computed is_available."""

    is_available = serializers.SerializerMethodField()

    class Meta:
        model = CarSlot
        fields = [
            'id', 'zone', 'code', 'status', 'is_available', 'camera',
            'x1', 'y1', 'x2', 'y2', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_available(self, obj):
        """Compute boolean availability from status field."""
        return obj.status == 'available'


class CameraSerializer(serializers.ModelSerializer):
    """Serializer for Camera model."""

    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'ip_address', 'port', 'zone',
            'stream_url', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


