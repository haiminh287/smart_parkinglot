"""
Serializers for booking-service with nested objects matching frontend expectations.
"""

from rest_framework import serializers
from django.db import connection, transaction
from django.utils import timezone
import uuid
import json
import os
import requests as http_requests
import logging
from .models import PackagePricing, Booking

logger = logging.getLogger(__name__)

PARKING_SERVICE_URL = os.environ.get('PARKING_SERVICE_URL', 'http://parking-service:8000')
VEHICLE_SERVICE_URL = os.environ.get('VEHICLE_SERVICE_URL', 'http://vehicle-service:8000')


def _get_gateway_secret():
    """Lazy-read GATEWAY_SECRET from Django settings (avoid module-level fail)."""
    from django.conf import settings as django_settings
    return django_settings.GATEWAY_SECRET


def _get_service_headers(user_id=None, user_email=None):
    """Build headers for inter-service calls."""
    headers = {
        'Content-Type': 'application/json',
        'X-Gateway-Secret': _get_gateway_secret(),
    }
    if user_id:
        headers['X-User-ID'] = str(user_id)
    if user_email:
        headers['X-User-Email'] = str(user_email)
    return headers


def _fetch_vehicle_info(vehicle_id, user_id=None, user_email=None):
    """Fetch vehicle details from vehicle-service."""
    try:
        headers = _get_service_headers(user_id, user_email)
        resp = http_requests.get(
            f'{VEHICLE_SERVICE_URL}/vehicles/{vehicle_id}/',
            headers=headers,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'license_plate': data.get('licensePlate', data.get('license_plate', '')),
                'vehicle_type': data.get('vehicleType', data.get('vehicle_type', 'Car')),
            }
    except Exception as e:
        logger.warning(f"Failed to fetch vehicle {vehicle_id}: {e}")
    return None


def _fetch_parking_lot_info(lot_id):
    """Fetch parking lot details from parking-service."""
    try:
        headers = _get_service_headers()
        resp = http_requests.get(
            f'{PARKING_SERVICE_URL}/parking/lots/{lot_id}/',
            headers=headers,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'name': data.get('name', ''),
            }
    except Exception as e:
        logger.warning(f"Failed to fetch parking lot {lot_id}: {e}")
    return None


def _fetch_zone_info(zone_id):
    """Fetch zone details from parking-service."""
    try:
        headers = _get_service_headers()
        resp = http_requests.get(
            f'{PARKING_SERVICE_URL}/parking/zones/{zone_id}/',
            headers=headers,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'name': data.get('name', ''),
                'floor_id': data.get('floorId', data.get('floor_id', None)),
                'vehicle_type': data.get('vehicleType', data.get('vehicle_type', 'Car')),
                'capacity': data.get('capacity', 0),
                'available_slots': data.get('availableSlots', data.get('available_slots', 0)),
            }
    except Exception as e:
        logger.warning(f"Failed to fetch zone {zone_id}: {e}")
    return None


def _fetch_floor_info(floor_id):
    """Fetch floor details from parking-service."""
    try:
        headers = _get_service_headers()
        resp = http_requests.get(
            f'{PARKING_SERVICE_URL}/parking/floors/{floor_id}/',
            headers=headers,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'level': data.get('level', 1),
                'name': data.get('name', ''),
                'parking_lot_id': data.get('parkingLotId', data.get('parking_lot_id', '')),
            }
    except Exception as e:
        logger.warning(f"Failed to fetch floor {floor_id}: {e}")
    return None


def _fetch_slot_info(slot_id):
    """Fetch slot details from parking-service."""
    try:
        headers = _get_service_headers()
        resp = http_requests.get(
            f'{PARKING_SERVICE_URL}/parking/slots/{slot_id}/',
            headers=headers,
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'code': data.get('code', ''),
                'zone_id': data.get('zoneId', data.get('zone_id', '')),
                'status': data.get('status', 'available'),
            }
    except Exception as e:
        logger.warning(f"Failed to fetch slot {slot_id}: {e}")
    return None


class PackagePricingSerializer(serializers.ModelSerializer):
    """Serializer for PackagePricing model."""

    class Meta:
        model = PackagePricing
        fields = '__all__'


class CreateBookingSerializer(serializers.Serializer):
    """Write-only serializer for creating bookings with minimal frontend input."""
    
    vehicle_id = serializers.CharField()
    slot_id = serializers.UUIDField(required=False, allow_null=True)
    zone_id = serializers.UUIDField()
    parking_lot_id = serializers.UUIDField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    package_type = serializers.ChoiceField(choices=['hourly', 'daily', 'weekly', 'monthly'], default='hourly')
    payment_method = serializers.ChoiceField(choices=['online', 'on_exit'], default='on_exit')
    
    def create(self, validated_data):
        request = self.context.get('request')
        user_id = getattr(request, 'user_id', None)
        user_email = getattr(request, 'user_email', 'unknown@example.com')
        
        if not user_id:
            raise serializers.ValidationError({'userId': 'User authentication required'})
        
        vehicle_id_input = validated_data['vehicle_id']
        slot_id = validated_data.get('slot_id')
        zone_id = validated_data['zone_id']
        parking_lot_id = validated_data['parking_lot_id']
        package_type = validated_data.get('package_type', 'hourly')
        start_time = validated_data['start_time']
        end_time = validated_data.get('end_time')
        
        # ===== Fetch real vehicle info from vehicle-service =====
        vehicle_license_plate = ''
        vehicle_type = 'Car'
        try:
            vehicle_id = uuid.UUID(vehicle_id_input)
            vehicle_info = _fetch_vehicle_info(vehicle_id, user_id, user_email)
            if vehicle_info:
                vehicle_license_plate = vehicle_info['license_plate']
                vehicle_type = vehicle_info['vehicle_type']
            else:
                vehicle_license_plate = str(vehicle_id)
        except (ValueError, AttributeError):
            # Not a UUID, treat as license plate
            vehicle_license_plate = vehicle_id_input
            # Try to register vehicle
            try:
                vehicle_payload = {
                    'licensePlate': vehicle_license_plate,
                    'vehicleType': 'Car',
                    'userId': str(user_id)
                }
                headers = _get_service_headers(user_id, user_email)
                resp = http_requests.post(
                    f'{VEHICLE_SERVICE_URL}/vehicles/',
                    json=vehicle_payload,
                    headers=headers,
                    timeout=3
                )
                if resp.status_code in [200, 201]:
                    vdata = resp.json()
                    vehicle_id = uuid.UUID(vdata.get('id', str(uuid.uuid5(uuid.NAMESPACE_DNS, f"vehicle-{vehicle_id_input}"))))
                    vehicle_type = vdata.get('vehicleType', vdata.get('vehicle_type', 'Car'))
                else:
                    vehicle_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"vehicle-{vehicle_id_input}")
            except Exception:
                vehicle_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"vehicle-{vehicle_id_input}")
        
        # ===== Fetch real parking lot info =====
        parking_lot_name = ''
        lot_info = _fetch_parking_lot_info(parking_lot_id)
        if lot_info:
            parking_lot_name = lot_info['name']
        
        # ===== Fetch real zone info =====
        zone_name = ''
        floor_id = None
        floor_level = None
        zone_info = _fetch_zone_info(zone_id)
        if zone_info:
            zone_name = zone_info['name']
            floor_id_str = zone_info.get('floor_id')
            if floor_id_str:
                try:
                    floor_id = uuid.UUID(str(floor_id_str))
                    # Fetch floor level
                    floor_info = _fetch_floor_info(floor_id)
                    if floor_info:
                        floor_level = floor_info.get('level')
                except (ValueError, TypeError):
                    pass
            # Use zone's vehicle_type if we didn't get it from vehicle
            if not vehicle_license_plate:
                vehicle_type = zone_info.get('vehicle_type', vehicle_type)
        
        # ===== Fetch real slot info =====
        slot_code = ''
        if slot_id:
            slot_info = _fetch_slot_info(slot_id)
            if slot_info:
                slot_code = slot_info['code']
        
        # ===== Calculate price from PackagePricing =====
        price = 0
        try:
            pricing = PackagePricing.objects.get(
                package_type=package_type,
                vehicle_type=vehicle_type
            )
            if package_type == 'hourly' and start_time and end_time:
                import math
                hours = (end_time - start_time).total_seconds() / 3600
                price = math.ceil(hours) * float(pricing.price)
            else:
                price = float(pricing.price)
        except PackagePricing.DoesNotExist:
            pass
        
        # ===== Generate QR code data =====
        booking_id = uuid.uuid4()
        qr_data = json.dumps({
            'booking_id': str(booking_id),
            'user_id': str(user_id),
            'timestamp': timezone.now().isoformat()
        })
        
        # ===== Create booking with real data =====
        # Advisory lock prevents double-booking race (S1-CRIT-5)
        lock_name = f"slot_booking_{slot_id}" if slot_id else None
        lock_acquired = False

        try:
            if lock_name:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT GET_LOCK(%s, 5)", [lock_name])
                    lock_acquired = cursor.fetchone()[0] == 1
                if not lock_acquired:
                    raise serializers.ValidationError({
                        'slot_id': 'Hệ thống đang bận xử lý slot này, vui lòng thử lại.'
                    })

            with transaction.atomic():
                if slot_id and end_time and start_time:
                    conflict = Booking.objects.filter(
                        slot_id=slot_id,
                        check_in_status__in=['not_checked_in', 'checked_in'],
                        start_time__lt=end_time,
                        end_time__gt=start_time,
                    ).exists()
                    if conflict:
                        raise serializers.ValidationError({
                            'slot_id': 'Slot đã được đặt trong khoảng thời gian này. Vui lòng chọn thời gian khác.'
                        })

                booking = Booking.objects.create(
                    id=booking_id,
                    user_id=user_id,
                    user_email=user_email,
                    vehicle_id=vehicle_id,
                    vehicle_license_plate=vehicle_license_plate,
                    vehicle_type=vehicle_type,
                    parking_lot_id=parking_lot_id,
                    parking_lot_name=parking_lot_name,
                    floor_id=floor_id,
                    floor_level=floor_level,
                    zone_id=zone_id,
                    zone_name=zone_name,
                    slot_id=slot_id,
                    slot_code=slot_code,
                    package_type=package_type,
                    start_time=start_time,
                    end_time=end_time,
                    hourly_start=start_time if package_type == 'hourly' else None,
                    hourly_end=end_time if package_type == 'hourly' else None,
                    payment_method=validated_data.get('payment_method', 'on_exit'),
                    payment_status='pending',
                    price=price,
                    check_in_status='not_checked_in',
                    qr_code_data=qr_data
                )

            # ===== Mark slot as reserved in parking-service =====
            if slot_id:
                try:
                    headers = _get_service_headers()
                    http_requests.patch(
                        f'{PARKING_SERVICE_URL}/parking/slots/{slot_id}/',
                        json={'status': 'reserved'},
                        headers=headers,
                        timeout=3
                    )
                except Exception as e:
                    logger.warning(f"Failed to reserve slot {slot_id}: {e}")

            return booking
        finally:
            if lock_acquired and lock_name:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT RELEASE_LOCK(%s)", [lock_name])


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for Booking model with nested objects.
    Builds Vehicle, ParkingLot, Floor, Zone, CarSlot objects from denormalized data.
    """

    vehicle = serializers.SerializerMethodField()
    parkingLot = serializers.SerializerMethodField(method_name='get_parking_lot')
    floor = serializers.SerializerMethodField()
    zone = serializers.SerializerMethodField()
    carSlot = serializers.SerializerMethodField(method_name='get_car_slot')

    userId = serializers.UUIDField(source='user_id')
    packageType = serializers.CharField(source='package_type')
    startTime = serializers.DateTimeField(source='start_time')
    endTime = serializers.DateTimeField(source='end_time')
    paymentType = serializers.CharField(source='payment_method')
    paymentStatus = serializers.CharField(source='payment_status')
    checkInStatus = serializers.CharField(source='check_in_status')
    checkedInAt = serializers.DateTimeField(source='checked_in_at')
    checkedOutAt = serializers.DateTimeField(source='checked_out_at')
    qrCodeData = serializers.CharField(source='qr_code_data')
    createdAt = serializers.DateTimeField(source='created_at')
    
    # Add hourly booking fields
    hourlyStart = serializers.DateTimeField(source='hourly_start', allow_null=True, required=False)
    hourlyEnd = serializers.DateTimeField(source='hourly_end', allow_null=True, required=False)
    extendedUntil = serializers.DateTimeField(source='extended_until', allow_null=True, required=False)
    lateFeeApplied = serializers.BooleanField(source='late_fee_applied', required=False)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'userId', 'vehicle', 'packageType', 'startTime', 'endTime',
            'floor', 'zone', 'carSlot', 'parkingLot',
            'paymentType', 'paymentStatus', 'checkInStatus', 'price',
            'checkedInAt', 'checkedOutAt', 'qrCodeData', 'createdAt',
            'hourlyStart', 'hourlyEnd', 'extendedUntil', 'lateFeeApplied'
        ]
    
    def get_vehicle(self, obj):
        """Build Vehicle object - fetch real data if license plate is empty."""
        vehicle_type = obj.vehicle_type
        if vehicle_type:
            vt = vehicle_type.lower()
            if vt == 'car':
                vehicle_type = 'Car'
            elif vt in ['motorbike', 'motorcycle', 'bike']:
                vehicle_type = 'Motorbike'
        
        license_plate = obj.vehicle_license_plate
        if not license_plate or license_plate == 'PLACEHOLDER':
            vehicle_info = _fetch_vehicle_info(obj.vehicle_id, obj.user_id)
            if vehicle_info:
                license_plate = vehicle_info['license_plate']
                vehicle_type = vehicle_info['vehicle_type']
                # Update denormalized data
                Booking.objects.filter(id=obj.id).update(
                    vehicle_license_plate=license_plate,
                    vehicle_type=vehicle_type
                )
        
        return {
            'id': str(obj.vehicle_id),
            'userId': str(obj.user_id),
            'licensePlate': license_plate or '',
            'vehicleType': vehicle_type or 'Car',
            'name': license_plate or ''
        }
    
    def get_parking_lot(self, obj):
        """Build ParkingLot object - fetch real data if name is empty."""
        name = obj.parking_lot_name
        if not name:
            lot_info = _fetch_parking_lot_info(obj.parking_lot_id)
            if lot_info:
                name = lot_info['name']
                # Update denormalized data for future reads
                Booking.objects.filter(id=obj.id).update(parking_lot_name=name)
        return {
            'id': str(obj.parking_lot_id),
            'name': name or ''
        }
    
    def get_floor(self, obj):
        """Build Floor object - fetch real data if floor_id missing."""
        floor_id = obj.floor_id
        floor_level = obj.floor_level
        
        # Try to resolve floor from zone if missing
        if not floor_id and obj.zone_id:
            zone_info = _fetch_zone_info(obj.zone_id)
            if zone_info and zone_info.get('floor_id'):
                try:
                    floor_id = uuid.UUID(str(zone_info['floor_id']))
                    floor_info = _fetch_floor_info(floor_id)
                    if floor_info:
                        floor_level = floor_info.get('level')
                    # Update denormalized data
                    Booking.objects.filter(id=obj.id).update(
                        floor_id=floor_id, floor_level=floor_level
                    )
                except (ValueError, TypeError):
                    pass
        
        if not floor_id:
            return None
        return {
            'id': str(floor_id),
            'parkingLotId': str(obj.parking_lot_id),
            'level': floor_level,
            'zones': []
        }
    
    def get_zone(self, obj):
        """Build Zone object - fetch real data for capacity/slots."""
        vehicle_type = obj.vehicle_type
        if vehicle_type:
            vt = vehicle_type.lower()
            if vt == 'car':
                vehicle_type = 'Car'
            elif vt in ['motorbike', 'motorcycle', 'bike']:
                vehicle_type = 'Motorbike'
        
        zone_name = obj.zone_name
        floor_id = obj.floor_id
        capacity = 0
        available_slots = 0
        
        # Fetch real zone info if name is empty or to get real capacity
        if not zone_name or zone_name == 'PLACEHOLDER':
            zone_info = _fetch_zone_info(obj.zone_id)
            if zone_info:
                zone_name = zone_info['name']
                capacity = zone_info.get('capacity', 0)
                available_slots = zone_info.get('available_slots', 0)
                if zone_info.get('floor_id') and not floor_id:
                    try:
                        floor_id = uuid.UUID(str(zone_info['floor_id']))
                    except (ValueError, TypeError):
                        pass
                # Update denormalized data
                updates = {'zone_name': zone_name}
                if floor_id:
                    updates['floor_id'] = floor_id
                Booking.objects.filter(id=obj.id).update(**updates)
        else:
            # Still fetch capacity for display
            zone_info = _fetch_zone_info(obj.zone_id)
            if zone_info:
                capacity = zone_info.get('capacity', 0)
                available_slots = zone_info.get('available_slots', 0)
                if zone_info.get('floor_id') and not floor_id:
                    try:
                        floor_id = uuid.UUID(str(zone_info['floor_id']))
                        Booking.objects.filter(id=obj.id).update(floor_id=floor_id)
                    except (ValueError, TypeError):
                        pass
        
        return {
            'id': str(obj.zone_id),
            'floorId': str(floor_id) if floor_id else None,
            'name': zone_name or '',
            'vehicleType': vehicle_type,
            'capacity': capacity,
            'availableSlots': available_slots
        }
    
    def get_car_slot(self, obj):
        """Build CarSlot object - fetch real data if code is empty."""
        if not obj.slot_id:
            return None
        
        slot_code = obj.slot_code
        if not slot_code or slot_code == 'PLACEHOLDER':
            slot_info = _fetch_slot_info(obj.slot_id)
            if slot_info:
                slot_code = slot_info['code']
                Booking.objects.filter(id=obj.id).update(slot_code=slot_code)
        
        return {
            'id': str(obj.slot_id),
            'zoneId': str(obj.zone_id),
            'code': slot_code or '',
            'isAvailable': False
        }


