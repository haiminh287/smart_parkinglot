"""
Celery tasks for booking-service.
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings as django_settings
from django.db.models import F
from datetime import timedelta
from .models import Booking
import json
import os
import pika
import requests
import logging

from .events import create_slot_event, create_booking_event

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
        
        # Release slot via outbox event
        if booking.slot_id:
            create_slot_event(booking.slot_id, 'available', booking)
        create_booking_event('booking.cancelled', booking)

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


# ---------------------------------------------------------------------------
# Outbox publish tasks
# ---------------------------------------------------------------------------

DLQ_THRESHOLD = 5

_amqp_connection = None
_amqp_channel = None


def _get_amqp_channel():
    """Get or create persistent AMQP channel for outbox publishing."""
    global _amqp_connection, _amqp_channel
    if _amqp_connection is None or _amqp_connection.is_closed:
        _amqp_connection = pika.BlockingConnection(
            pika.URLParameters(os.environ.get('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/'))
        )
        _amqp_channel = _amqp_connection.channel()
        _amqp_channel.exchange_declare('parksmart.events', exchange_type='topic', durable=True)
        _amqp_channel.exchange_declare('parksmart.events.dlq', exchange_type='topic', durable=True)
    return _amqp_channel


@shared_task
def publish_outbox_events():
    """Poll outbox table and publish pending events to RabbitMQ. Runs every 2s."""
    from bookings.models import OutboxEvent

    events = OutboxEvent.objects.filter(
        published_at__isnull=True,
        dead_lettered_at__isnull=True,
        error_count__lt=DLQ_THRESHOLD,
    ).order_by('created_at')[:100]

    if not events.exists():
        return

    channel = _get_amqp_channel()

    for event in events:
        try:
            payload = {**event.payload, 'event_id': str(event.event_id)}
            channel.basic_publish(
                exchange='parksmart.events',
                routing_key=event.event_type,
                body=json.dumps(payload, default=str),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    message_id=str(event.event_id),
                ),
            )
            event.published_at = timezone.now()
            event.save(update_fields=['published_at'])
        except Exception as exc:
            logger.warning("Outbox publish failed for %s: %s", event.event_id, exc)
            OutboxEvent.objects.filter(id=event.id).update(
                error_count=F('error_count') + 1,
                last_error=str(exc)[:500],
            )
            global _amqp_connection
            _amqp_connection = None


@shared_task
def process_dead_letter_events():
    """Move events that failed too many times to DLQ exchange. Runs every 5 min."""
    from bookings.models import OutboxEvent

    failed = OutboxEvent.objects.filter(
        published_at__isnull=True,
        dead_lettered_at__isnull=True,
        error_count__gte=DLQ_THRESHOLD,
    )

    if not failed.exists():
        return

    channel = _get_amqp_channel()

    for event in failed:
        try:
            payload = {**event.payload, 'event_id': str(event.event_id), 'dlq_reason': event.last_error}
            channel.basic_publish(
                exchange='parksmart.events.dlq',
                routing_key=event.event_type,
                body=json.dumps(payload, default=str),
                properties=pika.BasicProperties(delivery_mode=2),
            )
        except Exception as exc:
            logger.error("DLQ publish failed for %s: %s", event.event_id, exc)

    count = failed.count()
    failed.update(dead_lettered_at=timezone.now())
    if count:
        logger.error("Moved %s events to DLQ", count)
