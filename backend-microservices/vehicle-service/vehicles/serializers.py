"""
Serializers for vehicle-service.
Uses standard snake_case model fields - CamelCaseJSONRenderer/Parser handles conversion automatically.
"""

from rest_framework import serializers
from .models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    """
    Serializer for Vehicle model.
    
    CamelCaseJSONRenderer auto-converts output: license_plate → licensePlate
    CamelCaseJSONParser auto-converts input: licensePlate → license_plate
    So we just use the model field names directly.
    """
    
    name = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ['id', 'user_id', 'license_plate', 'vehicle_type', 'brand', 'model', 'color', 'is_default', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']
    
    def get_name(self, obj):
        """Compute display name from brand, model, and license plate."""
        if obj.brand and obj.model:
            return f"{obj.brand} {obj.model} ({obj.license_plate})"
        return obj.license_plate
    
    def create(self, validated_data):
        """Set user_id from request context."""
        request = self.context.get('request')
        if request and hasattr(request, 'user_id'):
            validated_data['user_id'] = request.user_id
        return super().create(validated_data)
    
    def to_representation(self, instance):
        """Ensure vehicle_type is capitalized (Car/Motorbike)."""
        data = super().to_representation(instance)
        # Normalize vehicle_type to match frontend expectations
        vehicle_type = data.get('vehicle_type', '')
        if vehicle_type:
            if vehicle_type.lower() == 'car':
                data['vehicle_type'] = 'Car'
            elif vehicle_type.lower() in ['motorbike', 'motorcycle', 'bike']:
                data['vehicle_type'] = 'Motorbike'
        return data


