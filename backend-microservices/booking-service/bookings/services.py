"""
Business logic layer for booking-service.
All price calculations, late fee logic, validation, and
check-in/check-out rules live here. Views ONLY call service methods.
"""

import math
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from .models import PackagePricing, Booking


# ---------------------------------------------------------------------------
# Pricing helpers
# ---------------------------------------------------------------------------

def get_hourly_price(vehicle_type: str) -> Decimal:
    """Get hourly price for a vehicle type from PackagePricing table."""
    try:
        pricing = PackagePricing.objects.get(
            package_type='hourly',
            vehicle_type=vehicle_type,
        )
        return pricing.price
    except PackagePricing.DoesNotExist:
        # Fallback defaults
        if vehicle_type == 'Car':
            return Decimal('15000.00')  # 15,000 VND/h
        return Decimal('5000.00')       # 5,000 VND/h


def calculate_checkout_price(booking: Booking) -> dict:
    """
    Calculate final price, late fee, and duration at checkout time.

    Returns a dict with:
        total_amount, late_fee, late_fee_applied, total_hours,
        billable_hours, hourly_price
    """
    now = timezone.now()
    checked_in_at = booking.checked_in_at or now
    duration = now - checked_in_at
    total_hours = duration.total_seconds() / 3600
    hourly_price = get_hourly_price(booking.vehicle_type)

    late_fee = Decimal('0')
    late_fee_applied = False

    if booking.package_type == 'hourly' and booking.hourly_end:
        overtime_seconds = (now - booking.hourly_end).total_seconds()
        if overtime_seconds > 0:
            overtime_hours = math.ceil(overtime_seconds / 3600)
            scheduled_seconds = (
                (booking.hourly_end - booking.hourly_start).total_seconds()
                if booking.hourly_start else 0
            )
            scheduled_hours = math.ceil(scheduled_seconds / 3600)

            base_amount = scheduled_hours * hourly_price
            late_fee_rate = hourly_price * Decimal('1.5')  # 50% surcharge
            late_fee = overtime_hours * late_fee_rate
            total_amount = base_amount + late_fee
            late_fee_applied = True
        else:
            if booking.hourly_start:
                scheduled_seconds = (booking.hourly_end - booking.hourly_start).total_seconds()
                scheduled_hours = math.ceil(scheduled_seconds / 3600)
            else:
                scheduled_hours = math.ceil(total_hours)
            total_amount = scheduled_hours * hourly_price
    else:
        billable_hours = math.ceil(total_hours) if total_hours > 0 else 1
        total_amount = billable_hours * hourly_price

    return {
        'total_amount': total_amount,
        'late_fee': late_fee,
        'late_fee_applied': late_fee_applied,
        'total_hours': total_hours,
        'hourly_price': hourly_price,
    }


def calculate_current_cost(booking: Booking) -> dict:
    """
    Calculate running cost for a currently checked-in booking.

    Returns dict with: duration_minutes, current_cost, hours_parked,
    billable_hours, hourly_rate
    """
    if booking.checked_in_at:
        duration_seconds = (timezone.now() - booking.checked_in_at).total_seconds()
    else:
        duration_seconds = 0

    duration_minutes = int(duration_seconds / 60)
    hours_parked = duration_seconds / 3600
    hourly_rate = get_hourly_price(booking.vehicle_type)
    billable_hours = math.ceil(hours_parked) if hours_parked > 0 else 1
    current_cost = float(billable_hours * hourly_rate)

    return {
        'duration_minutes': duration_minutes,
        'current_cost': round(current_cost, 2),
        'hours_parked': round(hours_parked, 2),
        'billable_hours': billable_hours,
        'hourly_rate': hourly_rate,
    }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_checkin(booking: Booking) -> str | None:
    """Return error message if booking cannot be checked-in, else None."""
    if booking.check_in_status != 'not_checked_in':
        return 'Only confirmed bookings can be checked in'
    return None


def validate_checkout(booking: Booking) -> str | None:
    """Return error message if booking cannot be checked-out, else None."""
    if booking.check_in_status != 'checked_in':
        return 'Only checked-in bookings can be checked out'
    return None


def validate_cancel(booking: Booking) -> str | None:
    """Return error message if booking cannot be cancelled, else None."""
    if booking.check_in_status in ['checked_in', 'checked_out']:
        return 'Cannot cancel booking that has already started or completed'
    return None


# ---------------------------------------------------------------------------
# Action executors
# ---------------------------------------------------------------------------

def perform_checkin(booking: Booking) -> Booking:
    """Execute check-in on a validated booking."""
    booking.check_in_status = 'checked_in'
    booking.checked_in_at = timezone.now()
    booking.save(update_fields=['check_in_status', 'checked_in_at'])
    return booking


def perform_checkout(booking: Booking) -> dict:
    """
    Execute checkout: set status, calculate price, save.
    Returns pricing info dict.
    """
    booking.check_in_status = 'checked_out'
    booking.checked_out_at = timezone.now()

    pricing = calculate_checkout_price(booking)
    booking.price = pricing['total_amount']
    booking.late_fee_applied = pricing['late_fee_applied']
    booking.save(update_fields=[
        'check_in_status', 'checked_out_at', 'price', 'late_fee_applied',
    ])
    return pricing


def perform_cancel(booking: Booking) -> Booking:
    """Execute cancellation on a validated booking."""
    booking.check_in_status = 'cancelled'
    booking.save(update_fields=['check_in_status'])
    return booking


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def get_user_stats(user_id) -> dict:
    """Aggregate booking statistics for a user using DB-level operations."""
    user_bookings = Booking.objects.filter(user_id=user_id)

    total_spent = user_bookings.filter(
        payment_status='completed'
    ).aggregate(total=Sum('price'))['total'] or Decimal('0')

    exit_spent = user_bookings.filter(
        check_in_status='checked_out'
    ).aggregate(total=Sum('price'))['total'] or Decimal('0')

    actual_total_spent = max(total_spent, exit_spent)

    # Django aggregation for total hours (Bug 10 fix)
    completed_qs = user_bookings.filter(
        check_in_status='checked_out',
        checked_in_at__isnull=False,
        checked_out_at__isnull=False,
    )
    total_duration = completed_qs.annotate(
        duration=ExpressionWrapper(
            F('checked_out_at') - F('checked_in_at'),
            output_field=DurationField(),
        )
    ).aggregate(total=Sum('duration'))
    total_hours = (
        total_duration['total'].total_seconds() / 3600
        if total_duration['total'] else 0
    )

    return {
        'total_bookings': user_bookings.count(),
        'total_spent': float(actual_total_spent),
        'total_hours': round(total_hours, 1),
        'no_show_count': user_bookings.filter(check_in_status='no_show').count(),
        'completed_bookings': completed_qs.count(),
        'cancelled_bookings': user_bookings.filter(check_in_status='cancelled').count(),
        'active_bookings': user_bookings.filter(check_in_status='checked_in').count(),
    }
