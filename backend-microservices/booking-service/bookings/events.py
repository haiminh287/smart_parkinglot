"""Event helpers for transactional outbox pattern."""

from bookings.models import OutboxEvent
from django.utils import timezone


def create_slot_event(slot_id, status, booking=None):
    """Write slot status change event to outbox."""
    payload = {
        "slot_id": str(slot_id),
        "status": status,
    }
    if booking:
        payload["booking_id"] = str(booking.id)
        payload["user_id"] = str(booking.user_id)
    OutboxEvent.objects.create(
        event_type="slot.status_changed",
        payload=payload,
    )


def create_booking_event(event_type, booking):
    """Write booking lifecycle event to outbox."""
    OutboxEvent.objects.create(
        event_type=event_type,
        payload={
            "booking_id": str(booking.id),
            "user_id": str(booking.user_id),
            "slot_id": str(booking.slot_id) if booking.slot_id else None,
            "check_in_status": booking.check_in_status,
            "timestamp": timezone.now().isoformat(),
        },
    )
