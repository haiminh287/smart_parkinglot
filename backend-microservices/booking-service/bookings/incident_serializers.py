"""
Serializer for Incident model.
"""
from rest_framework import serializers
from .incident_models import Incident


class IncidentSerializer(serializers.ModelSerializer):
    """Serializer for Incident."""
    
    # Read-only enriched fields from booking
    zone_name = serializers.SerializerMethodField()
    slot_code = serializers.SerializerMethodField()
    
    class Meta:
        model = Incident
        fields = [
            'id', 'user_id', 'type', 'description', 'status',
            'booking_id', 'parking_lot_id', 'zone_id', 'slot_id',
            'latitude', 'longitude',
            'security_notified', 'security_notified_at',
            'resolved_at', 'resolution_notes', 'resolved_by',
            'zone_name', 'slot_code',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']
    
    def get_zone_name(self, obj):
        """Get zone name from the associated booking."""
        if obj.booking_id:
            try:
                from .models import Booking
                booking = Booking.objects.filter(id=obj.booking_id).first()
                if booking and booking.zone_name:
                    return booking.zone_name
            except Exception:
                pass
        return None
    
    def get_slot_code(self, obj):
        """Get slot code from the associated booking."""
        if obj.booking_id:
            try:
                from .models import Booking
                booking = Booking.objects.filter(id=obj.booking_id).first()
                if booking and booking.slot_code:
                    return booking.slot_code
            except Exception:
                pass
        return None
    
    def create(self, validated_data):
        """Create incident with user_id from request."""
        request = self.context.get('request')
        validated_data['user_id'] = request.user_id
        return super().create(validated_data)
