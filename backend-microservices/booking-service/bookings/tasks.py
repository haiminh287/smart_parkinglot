"""
Celery tasks for booking-service.
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings as django_settings
from datetime import timedelta
from .models import Booking
import requests
import os
import logging

logger = logging.getLogger(__name__)


@shared_task
def auto_cancel_unpaid_bookings():
    """
    Auto-cancel bookings with payment_method='online' that are still 'pending' 
    after 15 minutes of creation.
    """
    logger.info("Running auto_cancel_unpaid_bookings task")
    
    # Find bookings that are:
    # 1. payment_method = 'online'
    # 2. payment_status = 'pending'
    # 3. check_in_status = 'not_checked_in'
    # 4. created > 15 minutes ago
    cutoff_time = timezone.now() - timedelta(minutes=15)
    
    bookings_to_cancel = Booking.objects.filter(
        payment_method='online',
        payment_status='pending',
        check_in_status='not_checked_in',
        created_at__lt=cutoff_time
    )
    
    cancelled_count = 0
    for booking in bookings_to_cancel:
        booking.check_in_status = 'cancelled'
        booking.save(update_fields=['check_in_status', 'updated_at'])
        cancelled_count += 1
        
        # Broadcast slot release if slot was reserved
        if booking.slot_id:
            try:
                REALTIME_SERVICE_URL = os.environ.get('REALTIME_SERVICE_URL', 'http://realtime-service:8006')
                requests.post(
                    f'{REALTIME_SERVICE_URL}/api/broadcast/slot-status/',
                    json={
                        'slotId': str(booking.slot_id),
                        'zoneId': str(booking.zone_id) if booking.zone_id else None,
                        'status': 'available',
                        'vehicleType': booking.vehicle_type,
                    },
                    timeout=2
                )
            except Exception as e:
                logger.warning("Failed to broadcast slot release: %s", e)

        if booking.slot_id:
            try:
                PARKING_SERVICE_URL = os.environ.get('PARKING_SERVICE_URL', 'http://parking-service:8000')
                GATEWAY_SECRET = django_settings.GATEWAY_SECRET
                requests.patch(
                    f'{PARKING_SERVICE_URL}/parking/slots/{booking.slot_id}/update-status/',
                    json={'status': 'available'},
                    headers={
                        'X-Gateway-Secret': GATEWAY_SECRET,
                        'Content-Type': 'application/json'
                    },
                    timeout=3
                )
            except Exception as e:
                logger.warning("Failed to release slot %s in parking-service on auto-cancel: %s", booking.slot_id, e)

        # TODO: Send notification to user
        try:
            NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:8000')
            requests.post(
                f'{NOTIFICATION_SERVICE_URL}/notifications/',
                json={
                    'userId': str(booking.user_id),
                    'type': 'booking_cancelled',
                    'title': 'Booking Auto-Cancelled',
                    'message': f'Your booking at {booking.parking_lot_name} was cancelled due to unpaid payment within 15 minutes.',
                    'relatedId': str(booking.id)
                },
                headers={'X-Gateway-Secret': os.environ.get('GATEWAY_SECRET', '')},
                timeout=2
            )
        except Exception as e:
            logger.warning("Failed to send notification: %s", e)
    
    logger.info("Auto-cancelled %s unpaid bookings", cancelled_count)
    return cancelled_count


@shared_task
def check_no_show_bookings():
    """
    Check for hourly bookings with on_exit payment that haven't checked in 
    30 minutes after scheduled start time. Send warning notification.
    """
    logger.info("Running check_no_show_bookings task")
    
    # Find hourly bookings that:
    # 1. package_type = 'hourly'
    # 2. payment_method = 'on_exit'
    # 3. check_in_status = 'not_checked_in'
    # 4. hourly_start + 30 minutes < now
    cutoff_time = timezone.now() - timedelta(minutes=30)
    
    no_show_bookings = Booking.objects.filter(
        package_type='hourly',
        check_in_status='not_checked_in',
        hourly_start__lt=cutoff_time
    ).exclude(
        check_in_status='no_show'  # Don't notify twice
    )
    
    warned_count = 0
    for booking in no_show_bookings:
        # Mark as no_show
        booking.check_in_status = 'no_show'
        booking.save(update_fields=['check_in_status', 'updated_at'])
        warned_count += 1
        
        # Increment user no_show_count in auth-service
        try:
            AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth-service:8000')
            requests.post(
                f'{AUTH_SERVICE_URL}/users/{booking.user_id}/increment-no-show/',
                headers={'X-Gateway-Secret': os.environ.get('GATEWAY_SECRET', '')},
                timeout=2
            )
        except Exception as e:
            logger.warning("Failed to increment no-show count: %s", e)
        
        # Send warning notification with extension option
        try:
            NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://notification-service:8000')
            requests.post(
                f'{NOTIFICATION_SERVICE_URL}/notifications/',
                json={
                    'userId': str(booking.user_id),
                    'type': 'no_show_warning',
                    'title': 'No-Show Warning',
                    'message': f'You missed your hourly booking at {booking.parking_lot_name}. Would you like to extend your booking time?',
                    'relatedId': str(booking.id),
                    'actionUrl': f'/bookings/{booking.id}/extend'
                },
                headers={'X-Gateway-Secret': os.environ.get('GATEWAY_SECRET', '')},
                timeout=2
            )
        except Exception as e:
            logger.warning("Failed to send no-show notification: %s", e)
    
    logger.info("Sent no-show warnings for %s bookings", warned_count)
    return warned_count
