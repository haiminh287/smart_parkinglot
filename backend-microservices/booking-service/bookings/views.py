"""
Views for booking-service.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import requests
import os
import logging
from shared.gateway_permissions import IsGatewayAuthenticated
from .models import PackagePricing, Booking
from .serializers import PackagePricingSerializer, BookingSerializer, CreateBookingSerializer

# Realtime service URL for WebSocket broadcasting
REALTIME_SERVICE_URL = os.environ.get('REALTIME_SERVICE_URL', 'http://realtime-service:8006')
logger = logging.getLogger(__name__)


def broadcast_slot_status(slot_id, zone_id, slot_status, vehicle_type):
    """Broadcast slot status update to WebSocket clients via realtime-service."""
    try:
        requests.post(
            f'{REALTIME_SERVICE_URL}/api/broadcast/slot-status/',
            json={
                'slotId': slot_id,
                'zoneId': zone_id,
                'status': slot_status,
                'vehicleType': vehicle_type,
            },
            timeout=2
        )
    except Exception as e:
        # Log but don't fail the booking if broadcast fails
        logger.warning("Failed to broadcast slot status: %s", e)


class PackagePricingViewSet(viewsets.ModelViewSet):
    """ViewSet for PackagePricing."""

    queryset = PackagePricing.objects.all()
    serializer_class = PackagePricingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for Booking."""

    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsGatewayAuthenticated]
    
    def get_serializer_class(self):
        """Use CreateBookingSerializer for POST, BookingSerializer for GET."""
        if self.action == 'create':
            return CreateBookingSerializer
        return BookingSerializer
    
    def get_queryset(self):
        """Filter bookings by current user from gateway headers.
        
        Special case: user_id == 'system' returns all bookings
        (for inter-service calls from AI service, etc.)
        """
        user_id = getattr(self.request, 'user_id', None)
        if user_id == 'system':
            return Booking.objects.all()
        if user_id:
            return Booking.objects.filter(user_id=user_id)
        return Booking.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create booking and return full BookingSerializer response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        
        if booking.slot_id:
            broadcast_slot_status(
                slot_id=str(booking.slot_id),
                zone_id=str(booking.zone_id) if booking.zone_id else None,
                slot_status='occupied' ,
                # slot_status='occupied' if booking.status in ['confirmed', 'active'] else 'reserved',
                vehicle_type=booking.vehicle_type
            )

        output_serializer = BookingSerializer(booking)
        return Response({
            'booking': output_serializer.data,
            'message': 'Booking created successfully',
            'qrCode': booking.qr_code_data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='checkin')
    def checkin(self, request, pk=None):
        """Check-in to a booking (scan QR code at entry gate)."""
        booking = self.get_object()
        
        if booking.check_in_status != 'not_checked_in':
            status_map = {
                'checked_in': 'already checked in',
                'checked_out': 'already checked out',
                'cancelled': 'cancelled',
                'no_show': 'marked as no-show',
            }
            msg = status_map.get(booking.check_in_status, f'invalid status: {booking.check_in_status}')
            return Response(
                {'error': f'Cannot check in: booking is {msg}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.check_in_status = 'checked_in'
        booking.checked_in_at = timezone.now()
        booking.save(update_fields=['check_in_status', 'checked_in_at'])
        
        if booking.slot_id:
            broadcast_slot_status(
                slot_id=str(booking.slot_id),
                zone_id=str(booking.zone_id) if booking.zone_id else None,
                slot_status='occupied',
                vehicle_type=booking.vehicle_type
            )
            # Update slot in parking-service
            try:
                PARKING_SERVICE_URL = os.environ.get('PARKING_SERVICE_URL', 'http://parking-service:8000')
                GATEWAY_SECRET_VAL = os.environ.get('GATEWAY_SECRET', '')
                requests.patch(
                    f'{PARKING_SERVICE_URL}/parking/slots/{booking.slot_id}/update-status/',
                    json={'status': 'occupied'},
                    headers={
                        'X-Gateway-Secret': GATEWAY_SECRET_VAL,
                        'Content-Type': 'application/json',
                    },
                    timeout=3,
                )
            except Exception as e:
                logger.warning("Failed to update slot in parking-service: %s", e)
        
        serializer = self.get_serializer(booking)
        return Response({
            'booking': serializer.data,
            'message': 'Check-in successful',
            'checkedInAt': booking.checked_in_at.isoformat() if booking.checked_in_at else None,
        })
    
    @action(detail=True, methods=['post'], url_path='checkout')
    def checkout(self, request, pk=None):
        """Check-out from a booking (scan QR code at exit)."""
        booking = self.get_object()
        
        if booking.check_in_status != 'checked_in':
            return Response(
                {'error': 'Only checked-in bookings can be checked out'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.check_in_status = 'checked_out'
        booking.checked_out_at = timezone.now()

        duration = booking.checked_out_at - booking.checked_in_at
        total_hours = duration.total_seconds() / 3600

        hourly_price = self._get_hourly_price(booking.vehicle_type)
        late_fee = 0

        import math
        
        # Calculate late fee for hourly bookings
        if booking.package_type == 'hourly' and booking.hourly_end:
            # Check if checked out after scheduled end time
            overtime_seconds = (booking.checked_out_at - booking.hourly_end).total_seconds()
            if overtime_seconds > 0:
                # Apply late fee: 30,000đ/hour instead of 20,000đ/hour
                overtime_hours = math.ceil(overtime_seconds / 3600)
                
                # Calculate scheduled hours
                if booking.hourly_start:
                    scheduled_seconds = (booking.hourly_end - booking.hourly_start).total_seconds()
                    scheduled_hours = math.ceil(scheduled_seconds / 3600)
                else:
                    scheduled_hours = 0
                
                # Base price for scheduled hours
                base_amount = scheduled_hours * hourly_price
                
                # Late fee for overtime hours (30k/h for cars, 10k/h for motorbikes)
                late_fee_rate = hourly_price * Decimal('1.5')  # 50% surcharge
                late_fee = overtime_hours * late_fee_rate
                
                total_amount = base_amount + late_fee
                booking.late_fee_applied = True
            else:
                # No overtime - charge for scheduled hours
                if booking.hourly_start:
                    scheduled_seconds = (booking.hourly_end - booking.hourly_start).total_seconds()
                    scheduled_hours = math.ceil(scheduled_seconds / 3600)
                else:
                    scheduled_hours = math.ceil(total_hours)
                total_amount = scheduled_hours * hourly_price
        else:
            # Non-hourly or no hourly_end - charge for actual duration
            billable_hours = math.ceil(total_hours) if total_hours > 0 else 1
            total_amount = billable_hours * hourly_price

        booking.price = total_amount
        booking.save(update_fields=['check_in_status', 'checked_out_at', 'price', 'late_fee_applied'])

        if booking.slot_id:
            broadcast_slot_status(
                slot_id=str(booking.slot_id),
                zone_id=str(booking.zone_id) if booking.zone_id else None,
                slot_status='available',
                vehicle_type=booking.vehicle_type
            )
            # Release slot in parking-service (Bug #5 fix)
            try:
                PARKING_SERVICE_URL = os.environ.get('PARKING_SERVICE_URL', 'http://parking-service:8000')
                GATEWAY_SECRET = os.environ.get('GATEWAY_SECRET', '')
                requests.patch(
                    f'{PARKING_SERVICE_URL}/parking/slots/{booking.slot_id}/update-status/',
                    json={'status': 'available'},
                    headers={
                        'X-Gateway-Secret': GATEWAY_SECRET,
                        'Content-Type': 'application/json',
                    },
                    timeout=3,
                )
            except Exception as e:
                logger.warning("Failed to release slot in parking-service: %s", e)
        
        serializer = self.get_serializer(booking)
        return Response({
            'booking': serializer.data,
            'message': 'Check-out successful',
            'durationHours': round(total_hours, 2),
            'totalAmount': float(total_amount),
            'pricePerHour': float(hourly_price),
            'lateFee': float(late_fee) if late_fee > 0 else 0,
            'lateFeeApplied': booking.late_fee_applied
        })
    
    def _get_hourly_price(self, vehicle_type):
        """Get hourly price for vehicle type from PackagePricing."""
        from decimal import Decimal
        try:
            pricing = PackagePricing.objects.get(
                package_type='hourly',
                vehicle_type=vehicle_type
            )
            return pricing.price
        except PackagePricing.DoesNotExist:
            # Default pricing if not configured
            if vehicle_type == 'Car':
                return Decimal('15000.00')  # 15,000 VND per hour for cars
            else:
                return Decimal('5000.00')   # 5,000 VND per hour for motorbikes
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking."""
        booking = self.get_object()
        
        if booking.check_in_status in ['checked_in', 'checked_out']:
            return Response(
                {'error': 'Cannot cancel booking that has already started or completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.check_in_status = 'cancelled'
        booking.save(update_fields=['check_in_status'])
        
        # TODO: Process refund if paid online
        
        serializer = self.get_serializer(booking)
        return Response({
            'booking': serializer.data,
            'message': 'Booking cancelled successfully'
        })
    
    @action(detail=False, methods=['get'], url_path='current-parking')
    def current_parking(self, request):
        """Get current parking session (checked_in status)."""
        # Permission already checked by IsGatewayAuthenticated
        booking = Booking.objects.filter(
            user_id=request.user_id,
            check_in_status='checked_in'
        ).first()
        
        if not booking:
            return Response({'detail': 'No active parking session'}, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate duration and current cost
        if booking.checked_in_at:
            duration = (timezone.now() - booking.checked_in_at).total_seconds() / 60  # in minutes
        else:
            duration = 0
        
        # Calculate cost based on hourly rate and actual time
        import math
        hourly_rate = self._get_hourly_price(booking.vehicle_type)
        hours_parked = duration / 60
        billable_hours = math.ceil(hours_parked) if hours_parked > 0 else 1
        current_cost = float(billable_hours * hourly_rate)
        
        serializer = self.get_serializer(booking)
        return Response({
            'booking': serializer.data,
            'duration': int(duration),
            'currentCost': round(current_cost, 2),
            'hoursParked': round(hours_parked, 2),
            'billableHours': billable_hours,
            'pricePerHour': float(hourly_rate),
            'message': 'Current parking session'
        })
    
    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming_bookings(self, request):
        """Get upcoming bookings (not checked in yet)."""
        # Permission already checked by IsGatewayAuthenticated
        bookings_qs = Booking.objects.filter(
            user_id=request.user_id,
            check_in_status='not_checked_in',
            start_time__gte=timezone.now()
        ).order_by('start_time')
        
        # Get count before slicing
        count = bookings_qs.count()
        bookings = bookings_qs[:5]
        
        serializer = self.get_serializer(bookings, many=True)
        return Response({
            'results': serializer.data,
            'count': count,
            'message': 'Upcoming bookings'
        })
    
    @action(detail=False, methods=['get'], url_path='stats')
    def booking_stats(self, request):
        """Get user booking statistics with monthly breakdown."""
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncMonth
        from decimal import Decimal
        
        user_bookings = Booking.objects.filter(user_id=request.user_id)
        
        total_spent = user_bookings.filter(
            payment_status='completed'
        ).aggregate(total=Sum('price'))['total'] or Decimal('0')
        
        # Also count money from checked_out bookings (on_exit payments)
        exit_spent = user_bookings.filter(
            check_in_status='checked_out'
        ).aggregate(total=Sum('price'))['total'] or Decimal('0')
        
        actual_total_spent = max(total_spent, exit_spent)
        
        # Calculate total hours parked using Django aggregation
        from django.db.models import F, ExpressionWrapper, DurationField
        completed_bookings = user_bookings.filter(
            check_in_status__in=['checked_out'],
            checked_in_at__isnull=False,
            checked_out_at__isnull=False
        )
        total_duration = completed_bookings.annotate(
            duration=ExpressionWrapper(
                F('checked_out_at') - F('checked_in_at'),
                output_field=DurationField()
            )
        ).aggregate(total=Sum('duration'))
        total_hours = total_duration['total'].total_seconds() / 3600 if total_duration['total'] else 0
        
        # Monthly expenses breakdown (last 6 months)
        from datetime import timedelta
        from django.utils import timezone as tz
        
        six_months_ago = tz.now() - timedelta(days=180)
        monthly_data = user_bookings.filter(
            created_at__gte=six_months_ago
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('price'),
            count=Count('id')
        ).order_by('month')
        
        monthly_expenses = []
        for item in monthly_data:
            monthly_expenses.append({
                'month': item['month'].strftime('%Y-%m') if item['month'] else '',
                'amount': float(item['total'] or 0),
                'count': item['count']
            })
        
        return Response({
            'total_bookings': user_bookings.count(),
            'total_spent': float(actual_total_spent),
            'total_hours': round(total_hours, 1),
            'no_show_count': user_bookings.filter(check_in_status='no_show').count(),
            'completed_bookings': user_bookings.filter(check_in_status='checked_out').count(),
            'cancelled_bookings': user_bookings.filter(check_in_status='cancelled').count(),
            'active_bookings': user_bookings.filter(check_in_status='checked_in').count(),
            'monthly_expenses': monthly_expenses,
        })
   
    
    @action(detail=False, methods=['post'], url_path='payment/verify')
    def verify_payment(self, request):
        """Verify payment callback."""
        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response({'error': 'transaction_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        # TODO: Verify with payment gateway
        return Response({
            'success': True,
            'message': 'Payment verified'
        })
    
    @action(detail=True, methods=['get'], url_path='qr-code')
    def qr_code(self, request, pk=None):
        """Get QR code for booking."""
        booking = self.get_object()
        return Response({
            'qr_code': booking.qr_code_data,
            'expires_at': (booking.start_time).isoformat() if booking.start_time else None
        })

    @action(detail=False, methods=['post'], url_path='check-slot-bookings')
    def check_slot_bookings(self, request):
        """Check which slots have overlapping bookings in given time range.
        Used by parking-service to determine slot availability.
        """
        slot_ids = request.data.get('slot_ids', [])
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        
        if not slot_ids or not start_time:
            return Response(
                {'error': 'slot_ids and start_time are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from datetime import datetime
        from django.db.models import Q
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                # If no end_time, check from start_time onwards
                end_dt = None
        except ValueError:
            return Response(
                {'error': 'Invalid datetime format. Use ISO 8601'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find bookings that overlap with the requested time range
        # A booking overlaps if: booking_start < end_time AND booking_end > start_time
        query = Q(slot_id__in=slot_ids, check_in_status__in=['not_checked_in', 'checked_in'])
        
        if end_dt:
            query &= Q(start_time__lt=end_dt) & Q(end_time__gt=start_dt)
        else:
            query &= Q(end_time__gt=start_dt)
        
        overlapping_bookings = Booking.objects.filter(query)
        booked_slot_ids = list(overlapping_bookings.values_list('slot_id', flat=True).distinct())
        
        return Response({
            'booked_slot_ids': [str(sid) for sid in booked_slot_ids],
            'count': len(booked_slot_ids)
        })
    

    
    @action(detail=True, methods=['post'])
    def payment(self, request, pk=None):
        """Initiate payment for a specific booking."""
        booking = self.get_object()
        payment_method = request.data.get('payment_method')
        
        if not payment_method:
            return Response(
                {'error': 'payment_method is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Integrate with payment gateway (MoMo, VNPay, ZaloPay)
        payment_url = f"https://payment-gateway.com/pay?booking={booking.id}&method={payment_method}"
        
        booking.payment_status = 'processing'
        booking.save(update_fields=['payment_status'])
        
        return Response({
            'payment_url': payment_url,
            'booking_id': str(booking.id),
            'amount': float(booking.price)
        })
    
    @action(detail=False, methods=['post'], url_path='payment')
    def initiate_payment(self, request):
        """Initiate payment (expects booking_id in body)."""
        import uuid as uuid_lib
        
        booking_id = request.data.get('booking_id')
        payment_method = request.data.get('payment_method')
        
        if not booking_id:
            return Response(
                {'error': 'booking_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not payment_method:
            return Response(
                {'error': 'payment_method is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate UUID before querying
        try:
            uuid_lib.UUID(booking_id)
        except (ValueError, AttributeError):
            return Response(
                {'error': 'Invalid booking_id format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            booking = Booking.objects.get(id=booking_id, user_id=request.user_id)
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # TODO: Integrate with payment gateway
        payment_url = f"https://payment-gateway.com/pay?booking={booking.id}&method={payment_method}"
        
        booking.payment_status = 'processing'
        booking.save(update_fields=['payment_status'])
        
        return Response({
            'payment_url': payment_url,
            'booking_id': str(booking.id),
            'amount': float(booking.price)
        })
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current parking session (checked-in or parked booking)."""
        booking = Booking.objects.filter(
            user_id=request.user_id,
            check_in_status='checked_in'
        ).first()
        
        if not booking:
            return Response({'detail': 'No active parking session'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(booking)
        
        # Calculate current duration and cost (handle None checked_in_at)
        from datetime import timedelta
        duration = (timezone.now() - booking.checked_in_at) if booking.checked_in_at else timedelta(0)
        hours = duration.total_seconds() / 3600
        # TODO: Calculate current cost based on package pricing
        
        return Response({
            'booking': serializer.data,
            'duration_minutes': int(duration.total_seconds() / 60),
            'current_cost': float(booking.price)
        })
    

