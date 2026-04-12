"""
Views for parking-service.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime
import os
from shared.gateway_permissions import IsGatewayAuthenticated
from .models import ParkingLot, Floor, Zone, CarSlot, Camera
from .serializers import ParkingLotSerializer, FloorSerializer, ZoneSerializer, CarSlotSerializer, CameraSerializer


class ParkingLotViewSet(viewsets.ModelViewSet):
    """ViewSet for ParkingLot."""

    queryset = ParkingLot.objects.all()
    serializer_class = ParkingLotSerializer
    permission_classes = [IsGatewayAuthenticated]
    
    def get_queryset(self):
        """Filter parking lots by location, vehicle type, and status."""
        queryset = super().get_queryset()
        
        # Filter by location (lat, lng, radius in km)
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius', '10')  # Default 10km
        
        if lat and lng:
            try:
                from math import radians, cos, sin, asin, sqrt
                
                lat = float(lat)
                lng = float(lng)
                radius = float(radius)
                
                # Simple distance filter (Haversine)
                # For production, use PostGIS or similar
                filtered_lots = []
                for lot in queryset:
                    if lot.latitude and lot.longitude:
                        # Calculate distance
                        lon1, lat1, lon2, lat2 = map(radians, [lng, lat, lot.longitude, lot.latitude])
                        dlon = lon2 - lon1
                        dlat = lat2 - lat1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        c = 2 * asin(sqrt(a))
                        km = 6371 * c  # Radius of earth in kilometers
                        
                        if km <= radius:
                            filtered_lots.append(lot.id)
                
                queryset = queryset.filter(id__in=filtered_lots)
            except (ValueError, TypeError):
                pass  # Invalid coordinates, return unfiltered
        
        # Filter by vehicle type
        vehicle_type = self.request.query_params.get('vehicle_type')
        if vehicle_type:
            # Filter lots that have floors with zones for this vehicle type
            queryset = queryset.filter(floors__zones__vehicle_type=vehicle_type).distinct()
        
        # Filter by open status
        is_open = self.request.query_params.get('is_open')
        if is_open is not None:
            queryset = queryset.filter(is_open=(is_open.lower() == 'true'))
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='nearest')
    def nearest(self, request):
        """Find nearest available parking lot based on user location."""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        vehicle_type = request.query_params.get('vehicle_type', 'Car')
        limit = int(request.query_params.get('limit', '5'))
        
        if not lat or not lng:
            return Response(
                {'error': 'Latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from math import radians, cos, sin, asin, sqrt
            
            lat = float(lat)
            lng = float(lng)
            
            # Bug 17 fix: Bounding box pre-filter before Haversine
            radius_km = float(request.query_params.get('radius', '10'))
            lat_range = radius_km / 111.0
            lon_range = radius_km / (111.0 * cos(radians(lat)))
            prefiltered = ParkingLot.objects.filter(
                is_open=True,
                latitude__range=(lat - lat_range, lat + lat_range),
                longitude__range=(lng - lon_range, lng + lon_range),
            ).prefetch_related('floors__zones__slots')  # Bug 20: N+1 fix
            
            # Calculate distance for pre-filtered lots
            lots_with_distance = []
            for lot in prefiltered:
                if lot.latitude and lot.longitude:
                    # Haversine formula
                    lon1, lat1, lon2, lat2 = map(radians, [lng, lat, lot.longitude, lot.latitude])
                    dlon = lon2 - lon1
                    dlat = lat2 - lat1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a))
                    distance = 6371 * c  # km
                    
                    # Check if has available slots for vehicle type
                    available_count = CarSlot.objects.filter(
                        zone__floor__parking_lot=lot,
                        zone__vehicle_type=vehicle_type,
                        status='available'
                    ).count()
                    
                    if available_count > 0:
                        lots_with_distance.append({
                            'lot': lot,
                            'distance': round(distance, 2),
                            'available_slots': available_count
                        })
            
            # Sort by distance
            lots_with_distance.sort(key=lambda x: x['distance'])
            
            # Serialize top N results
            results = []
            for item in lots_with_distance[:limit]:
                lot_data = ParkingLotSerializer(item['lot']).data
                lot_data['distance'] = item['distance']
                lot_data['availableSlots'] = item['available_slots']
                results.append(lot_data)
            
            return Response({
                'results': results,
                'count': len(results)
            })
            
        except (ValueError, TypeError) as e:
            return Response(
                {'error': f'Invalid coordinates: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], url_path='availability')
    def availability(self, request, pk=None):
        """Get real-time availability summary for parking lot."""
        lot = self.get_object()
        
        # Aggregate slot counts from all zones in this lot
        from django.db.models import Count, Q
        
        slots = CarSlot.objects.filter(zone__floor__parking_lot=lot)
        total = slots.count()
        available = slots.filter(status='available').count()
        occupied = slots.filter(status='occupied').count()
        reserved = slots.filter(status='reserved').count()
        maintenance = slots.filter(status='maintenance').count()
        
        # By vehicle type
        car_slots = slots.filter(zone__vehicle_type='Car')
        car_total = car_slots.count()
        car_available = car_slots.filter(status='available').count()
        
        bike_slots = slots.filter(zone__vehicle_type='Motorbike')
        bike_total = bike_slots.count()
        bike_available = bike_slots.filter(status='available').count()
        
        return Response({
            'lot_id': str(lot.id),
            'lot_name': lot.name,
            'total': total,
            'available': available,
            'occupied': occupied,
            'reserved': reserved,
            'maintenance': maintenance,
            'occupancy_rate': round((occupied / total * 100) if total > 0 else 0, 1),
            'by_vehicle_type': {
                'car': {
                    'total': car_total,
                    'available': car_available,
                    'occupancy_rate': round((car_total - car_available) / car_total * 100 if car_total > 0 else 0, 1)
                },
                'motorbike': {
                    'total': bike_total,
                    'available': bike_available,
                    'occupancy_rate': round((bike_total - bike_available) / bike_total * 100 if bike_total > 0 else 0, 1)
                }
            }
        })


class FloorViewSet(viewsets.ModelViewSet):
    """ViewSet for Floor."""

    queryset = Floor.objects.all()
    serializer_class = FloorSerializer

    def get_queryset(self):
        """Filter floors by lot_id."""
        queryset = super().get_queryset()
        
        lot_id = self.request.query_params.get('lot_id')
        if lot_id:
            try:
                # Validate UUID format before filtering
                import uuid
                uuid.UUID(lot_id)
                queryset = queryset.filter(parking_lot_id=lot_id)
            except (ValueError, TypeError):
                # Invalid UUID format, return empty queryset
                queryset = queryset.none()
        
        return queryset


class ZoneViewSet(viewsets.ModelViewSet):
    """ViewSet for Zone."""

    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    
    def get_queryset(self):
        """Filter zones by lot_id, floor_id, vehicle_type."""
        queryset = super().get_queryset()
        
        lot_id = self.request.query_params.get('lot_id')
        if lot_id:
            try:
                # Validate UUID format before filtering
                import uuid
                uuid.UUID(lot_id)
                queryset = queryset.filter(floor__parking_lot_id=lot_id)
            except (ValueError, TypeError, AttributeError):
                # Invalid UUID format, return empty queryset
                queryset = queryset.none()
        
        floor_id = self.request.query_params.get('floor_id')
        if floor_id:
            try:
                import uuid
                uuid.UUID(floor_id)
                queryset = queryset.filter(floor_id=floor_id)
            except (ValueError, TypeError):
                queryset = queryset.none()
        
        vehicle_type = self.request.query_params.get('vehicle_type')
        if vehicle_type:
            queryset = queryset.filter(vehicle_type=vehicle_type)
        
        return queryset


class CarSlotViewSet(viewsets.ModelViewSet):
    """ViewSet for CarSlot."""

    queryset = CarSlot.objects.all()
    serializer_class = CarSlotSerializer
    permission_classes = [IsGatewayAuthenticated]
    
    def get_queryset(self):
        """Filter slots by zone_id, status, vehicle_type."""
        queryset = super().get_queryset()
        
        zone_id = self.request.query_params.get('zone_id')
        if zone_id:
            try:
                import uuid
                uuid.UUID(zone_id)
                queryset = queryset.filter(zone_id=zone_id)
            except (ValueError, TypeError, AttributeError):
                queryset = queryset.none()
        
        slot_status = self.request.query_params.get('status')
        if slot_status:
            queryset = queryset.filter(status=slot_status)
        
        vehicle_type = self.request.query_params.get('vehicle_type')
        if vehicle_type:
            queryset = queryset.filter(zone__vehicle_type=vehicle_type)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='check-slots-availability')
    def check_slots_availability(self, request):
        """Check multiple slots availability against existing bookings."""
        zone_id = request.data.get('zone_id')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        
        if not all([zone_id, start_time]):
            return Response(
                {'error': 'zone_id and start_time are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            import requests
            from datetime import datetime
            
            # Get all slots in zone
            slots = self.queryset.filter(zone_id=zone_id)
            
            # Call booking-service to check which slots have bookings
            BOOKING_SERVICE = os.environ.get('BOOKING_SERVICE_URL', 'http://booking-service:8000')
            try:
                response = requests.post(
                    f'{BOOKING_SERVICE}/bookings/check-slot-bookings/',
                    json={
                        'slot_ids': [str(s.id) for s in slots],
                        'start_time': start_time,
                        'end_time': end_time
                    },
                    headers={'X-Gateway-Secret': os.environ.get('GATEWAY_SECRET', '')},
                    timeout=3
                )
                if response.status_code == 200:
                    booked_slot_ids = response.json().get('booked_slot_ids', [])
                else:
                    booked_slot_ids = []
            except Exception as e:
                booked_slot_ids = []
            
            # Update availability based on booking status
            results = []
            for slot in slots:
                is_available = (
                    slot.status == 'available' and 
                    str(slot.id) not in booked_slot_ids
                )
                slot_data = CarSlotSerializer(slot).data
                slot_data['is_available'] = is_available
                results.append(slot_data)
            
            return Response({
                'results': results,
                'count': len(results)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='check-availability')
    def check_availability(self, request, pk=None):
        """Check if specific slot is available for given time range."""
        slot = self.get_object()
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        
        if not start_time:
            return Response(
                {'error': 'start_time is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse datetime strings
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None
        except ValueError as e:
            return Response(
                {'error': f'Invalid datetime format: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for booking conflicts
        # Note: This requires accessing booking-service data
        # For now, just check slot status
        is_available = slot.status == 'available'
        
        # TODO: Query booking-service for time-based conflicts
        # conflicts = requests.get(f'http://booking-service:8004/api/bookings/?slot={slot.id}&start={start_time}&end={end_time}')
        
        return Response({
            'is_available': is_available,
            'slot_status': slot.status,
            'message': 'Available' if is_available else f'Slot is {slot.status}'
        })

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """Update slot status and auto-sync zone available_slots.

        Called by ai-service ESP32 endpoints when check-in/check-out.
        Requires X-Gateway-Secret header.
        """
        slot = self.get_object()
        new_status = request.data.get('status')

        valid_statuses = [choice[0] for choice in CarSlot.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = slot.status
        slot.status = new_status
        slot.save(update_fields=['status', 'updated_at'])

        # Auto-sync Zone.available_slots count
        zone = slot.zone
        zone.available_slots = zone.slots.filter(status='available').count()
        zone.save(update_fields=['available_slots', 'updated_at'])

        # Also update ParkingLot.available_slots
        lot = zone.floor.parking_lot
        lot.available_slots = CarSlot.objects.filter(
            zone__floor__parking_lot=lot,
            status='available'
        ).count()
        lot.save(update_fields=['available_slots', 'updated_at'])

        return Response({
            'slot_id': str(slot.id),
            'old_status': old_status,
            'new_status': new_status,
            'zone_available': zone.available_slots,
            'lot_available': lot.available_slots,
            'message': f'Slot {slot.code} updated to {new_status}'
        })


class CameraViewSet(viewsets.ModelViewSet):
    """ViewSet for Camera."""

    queryset = Camera.objects.all()
    serializer_class = CameraSerializer
    permission_classes = [IsGatewayAuthenticated]
    
    def get_queryset(self):
        """Filter cameras by zone, floor, status."""
        queryset = super().get_queryset()
        
        zone_id = self.request.query_params.get('zone_id')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        
        floor = self.request.query_params.get('floor')
        if floor:
            queryset = queryset.filter(zone__floor__level=floor)
        
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(is_active=(status_param == 'online'))
        
        return queryset
    
    @action(detail=True, methods=['get'], url_path='stream')
    def get_stream(self, request, pk=None):
        """Get camera stream URL."""
        camera = self.get_object()
        
        if not camera.is_active:
            return Response(
                {'error': 'Camera is offline'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        return Response({
            'stream_url': camera.stream_url or f'rtsp://camera-server/{camera.id}/stream',
            'is_active': camera.is_active,
            'camera_id': camera.id,
            'name': camera.name,
            'zone': camera.zone.name if camera.zone else None,
        })


