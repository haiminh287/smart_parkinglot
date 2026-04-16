"""
Business logic layer for booking-service.
All price calculations, late fee logic, validation, and
check-in/check-out rules live here. Views ONLY call service methods.
"""

import logging
import math
from datetime import timedelta
from decimal import Decimal

import requests
from django.conf import settings as django_settings
from django.db.models import Count, DurationField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import Booking, PackagePricing

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pricing helpers
# ---------------------------------------------------------------------------


def get_hourly_price(vehicle_type: str) -> Decimal:
    """Get hourly price for a vehicle type from PackagePricing table."""
    try:
        pricing = PackagePricing.objects.get(
            package_type="hourly",
            vehicle_type=vehicle_type,
        )
        return pricing.price
    except PackagePricing.DoesNotExist:
        # Fallback defaults
        if vehicle_type == "Car":
            return Decimal("15000.00")  # 15,000 VND/h
        return Decimal("5000.00")  # 5,000 VND/h


def _get_package_duration_hours(package_type: str) -> int | None:
    """Return the expected duration in hours for a package type, or None for hourly."""
    return {
        "daily": 24,
        "weekly": 168,  # 7 days
        "monthly": 720,  # 30 days
    }.get(package_type)


def calculate_checkout_price(booking: Booking) -> dict:
    """
    Calculate final price, late fee, and duration at checkout time.

    Logic per package type:
    - hourly: base = scheduled hours × hourly_price; overtime at 1.5× surcharge
    - daily/weekly/monthly: base = booking.price (package price, already paid);
      overtime ONLY if actual parking exceeds the package duration,
      charged at hourly_rate × 1.5 surcharge factor.

    Returns a dict with:
        total_amount, base_amount, late_fee, late_fee_applied, total_hours,
        hourly_price, package_type
    """
    now = timezone.now()
    checked_in_at = booking.checked_in_at or now
    duration = now - checked_in_at
    total_hours = duration.total_seconds() / 3600
    hourly_price = get_hourly_price(booking.vehicle_type)

    late_fee = Decimal("0")
    late_fee_applied = False

    package_duration_hours = _get_package_duration_hours(booking.package_type)

    if package_duration_hours is not None:
        # ----- daily / weekly / monthly -----
        # Base price is the package price set at booking time
        base_amount = booking.price

        effective_end = booking.extended_until or booking.hourly_end
        if effective_end:
            overtime_seconds = (now - effective_end).total_seconds()
        else:
            overtime_seconds = (total_hours - package_duration_hours) * 3600

        if overtime_seconds > 0:
            overtime_hours = math.ceil(overtime_seconds / 3600)
            late_fee_rate = hourly_price * Decimal("1.5")  # 50% surcharge
            late_fee = overtime_hours * late_fee_rate
            late_fee_applied = True

        total_amount = base_amount + late_fee

    elif booking.package_type == "hourly" and booking.hourly_end:
        # ----- hourly with scheduled end -----
        effective_end = booking.extended_until or booking.hourly_end
        overtime_seconds = (now - effective_end).total_seconds()
        if overtime_seconds > 0:
            overtime_hours = math.ceil(overtime_seconds / 3600)
            scheduled_seconds = (
                (effective_end - booking.hourly_start).total_seconds()
                if booking.hourly_start
                else 0
            )
            scheduled_hours = math.ceil(scheduled_seconds / 3600)

            base_amount = scheduled_hours * hourly_price
            late_fee_rate = hourly_price * Decimal("1.5")  # 50% surcharge
            late_fee = overtime_hours * late_fee_rate
            total_amount = base_amount + late_fee
            late_fee_applied = True
        else:
            if booking.hourly_start:
                scheduled_seconds = (
                    effective_end - booking.hourly_start
                ).total_seconds()
                scheduled_hours = math.ceil(scheduled_seconds / 3600)
            else:
                scheduled_hours = math.ceil(total_hours)
            base_amount = scheduled_hours * hourly_price
            total_amount = base_amount
    else:
        # ----- hourly without scheduled end (fallback) -----
        billable_hours = math.ceil(total_hours) if total_hours > 0 else 1
        base_amount = billable_hours * hourly_price
        total_amount = base_amount

    return {
        "total_amount": total_amount,
        "base_amount": base_amount,
        "late_fee": late_fee,
        "late_fee_applied": late_fee_applied,
        "total_hours": total_hours,
        "hourly_price": hourly_price,
        "package_type": booking.package_type,
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
        "duration_minutes": duration_minutes,
        "current_cost": round(current_cost, 2),
        "hours_parked": round(hours_parked, 2),
        "billable_hours": billable_hours,
        "hourly_rate": hourly_rate,
    }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_checkin(booking: Booking) -> str | None:
    """Return error message if booking cannot be checked-in, else None."""
    if booking.check_in_status != "not_checked_in":
        status_map = {
            "checked_in": "already checked in",
            "checked_out": "already checked out",
            "cancelled": "cancelled",
            "no_show": "marked as no-show",
        }
        msg = status_map.get(
            booking.check_in_status, f"invalid status: {booking.check_in_status}"
        )
        return f"Cannot check in: booking is {msg}"
    if booking.start_time and timezone.now() < booking.start_time - timedelta(
        minutes=30
    ):
        return "Chưa đến giờ check-in. Vui lòng đến trong vòng 30 phút trước giờ đặt."
    return None


def validate_checkout(booking: Booking) -> str | None:
    """Return error message if booking cannot be checked-out, else None."""
    if booking.check_in_status != "checked_in":
        return "Only checked-in bookings can be checked out"
    return None


def validate_cancel(booking: Booking) -> str | None:
    """Return error message if booking cannot be cancelled, else None."""
    if booking.check_in_status in ["checked_in", "checked_out"]:
        return "Cannot cancel booking that has already started or completed"
    return None


# ---------------------------------------------------------------------------
# Extend booking
# ---------------------------------------------------------------------------


def calculate_extension_price(booking: Booking, additional_hours: int) -> dict:
    """Calculate price for extending a booking.

    Voluntary extensions are charged at the normal hourly rate (no surcharge).
    Returns dict with: extension_price, hourly_price, additional_hours, new_end_time
    """
    hourly_price = get_hourly_price(booking.vehicle_type)
    extension_price = hourly_price * additional_hours

    # Determine current effective end time
    current_end = booking.extended_until or booking.hourly_end or booking.end_time
    if current_end:
        new_end_time = current_end + timedelta(hours=additional_hours)
    else:
        new_end_time = timezone.now() + timedelta(hours=additional_hours)

    return {
        "extension_price": extension_price,
        "hourly_price": hourly_price,
        "additional_hours": additional_hours,
        "new_end_time": new_end_time,
    }


def perform_extend(booking: Booking, additional_hours: int) -> dict:
    """Execute booking extension: update times, create payment, return details."""
    ext = calculate_extension_price(booking, additional_hours)

    booking.extended_until = ext["new_end_time"]
    booking.hourly_end = ext["new_end_time"]
    booking.save(update_fields=["extended_until", "hourly_end", "updated_at"])

    # Best-effort: create payment record for the extension fee
    payment_result = initiate_payment(
        booking_id=booking.id,
        user_id=booking.user_id,
        payment_method=_PAYMENT_METHOD_MAP.get(booking.payment_method, "cash"),
        amount=ext["extension_price"],
    )

    return {
        "booking_id": str(booking.id),
        "additional_hours": additional_hours,
        "extension_price": float(ext["extension_price"]),
        "hourly_price": float(ext["hourly_price"]),
        "new_end_time": ext["new_end_time"].isoformat(),
        "extended_until": ext["new_end_time"].isoformat(),
        "payment_created": payment_result is not None
        and "error" not in (payment_result or {}),
    }


# ---------------------------------------------------------------------------
# Action executors
# ---------------------------------------------------------------------------


def perform_checkin(booking: Booking) -> Booking:
    """Execute check-in on a validated booking."""
    booking.check_in_status = "checked_in"
    booking.checked_in_at = timezone.now()
    booking.save(update_fields=["check_in_status", "checked_in_at"])
    return booking


def perform_checkout(booking: Booking) -> dict:
    """
    Execute checkout: set status, calculate price, save.
    Returns pricing info dict.
    """
    booking.check_in_status = "checked_out"
    booking.checked_out_at = timezone.now()

    pricing = calculate_checkout_price(booking)
    booking.price = pricing["total_amount"]
    booking.late_fee_applied = pricing["late_fee_applied"]
    booking.save(
        update_fields=[
            "check_in_status",
            "checked_out_at",
            "price",
            "late_fee_applied",
        ]
    )
    return pricing


def perform_cancel(booking: Booking) -> Booking:
    """Execute cancellation on a validated booking."""
    booking.check_in_status = "cancelled"
    booking.save(update_fields=["check_in_status"])
    return booking


# ---------------------------------------------------------------------------
# Payment service integration
# ---------------------------------------------------------------------------

# Map booking payment_method to payment service valid methods
_PAYMENT_METHOD_MAP = {
    "on_exit": "cash",
    "online": "e_wallet",
}


def _payment_service_headers(user_id):
    """Build headers for payment service inter-service calls."""
    return {
        "Content-Type": "application/json",
        "X-Gateway-Secret": django_settings.GATEWAY_SECRET,
        "X-User-ID": str(user_id),
    }


def create_payment_for_booking(booking):
    """Call payment service to create a payment for a confirmed booking.

    Best-effort: never raises. Returns response dict on success, None on failure.
    """
    try:
        url = f"{django_settings.PAYMENT_SERVICE_URL}/api/payments/initiate/"
        payload = {
            "bookingId": str(booking.id),
            "paymentMethod": _PAYMENT_METHOD_MAP.get(booking.payment_method, "cash"),
            "amount": float(booking.price),
        }
        headers = _payment_service_headers(booking.user_id)
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code in (200, 201):
            logger.info("Payment created for booking %s", booking.id)
            return response.json()
        logger.error(
            "Payment service returned %s: %s", response.status_code, response.text
        )
        return None
    except requests.RequestException as e:
        logger.error("Failed to create payment for booking %s: %s", booking.id, e)
        return None


def get_booking_payments(booking_id, user_id):
    """Fetch existing payments for a booking from payment service.

    Returns list of payment dicts on success, None on failure.
    """
    try:
        url = (
            f"{django_settings.PAYMENT_SERVICE_URL}/api/payments/booking/{booking_id}/"
        )
        headers = _payment_service_headers(user_id)
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        logger.error("Failed to fetch payments for booking %s: %s", booking_id, e)
        return None


def initiate_payment(booking_id, user_id, payment_method, amount):
    """Initiate a payment with a specific method via the payment service.

    Returns payment response dict on success, None on failure.
    """
    try:
        url = f"{django_settings.PAYMENT_SERVICE_URL}/api/payments/initiate/"
        payload = {
            "bookingId": str(booking_id),
            "paymentMethod": payment_method,
            "amount": float(amount),
        }
        headers = _payment_service_headers(user_id)
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code in (200, 201):
            return response.json()
        # 400 = duplicate payment or invalid method
        return {
            "error": response.json().get("detail", "Payment initiation failed"),
            "status_code": response.status_code,
        }
    except requests.RequestException as e:
        logger.error("Failed to initiate payment for booking %s: %s", booking_id, e)
        return None


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------


def get_user_stats(user_id) -> dict:
    """Aggregate booking statistics for a user using DB-level operations."""
    user_bookings = Booking.objects.filter(user_id=user_id)

    total_spent = user_bookings.filter(payment_status="completed").aggregate(
        total=Sum("price")
    )["total"] or Decimal("0")

    exit_spent = user_bookings.filter(check_in_status="checked_out").aggregate(
        total=Sum("price")
    )["total"] or Decimal("0")

    actual_total_spent = max(total_spent, exit_spent)

    # Django aggregation for total hours (Bug 10 fix)
    completed_qs = user_bookings.filter(
        check_in_status="checked_out",
        checked_in_at__isnull=False,
        checked_out_at__isnull=False,
    )
    total_duration = completed_qs.annotate(
        duration=ExpressionWrapper(
            F("checked_out_at") - F("checked_in_at"),
            output_field=DurationField(),
        )
    ).aggregate(total=Sum("duration"))
    total_hours = (
        total_duration["total"].total_seconds() / 3600 if total_duration["total"] else 0
    )

    # Monthly expenses (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_data = (
        user_bookings.filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("price"), count=Count("id"))
        .order_by("month")
    )
    monthly_expenses = [
        {
            "month": item["month"].strftime("%Y-%m") if item["month"] else "",
            "amount": float(item["total"] or 0),
            "count": item["count"],
        }
        for item in monthly_data
    ]

    return {
        "total_bookings": user_bookings.count(),
        "total_spent": float(actual_total_spent),
        "total_hours": round(total_hours, 1),
        "no_show_count": user_bookings.filter(check_in_status="no_show").count(),
        "completed_bookings": completed_qs.count(),
        "cancelled_bookings": user_bookings.filter(check_in_status="cancelled").count(),
        "active_bookings": user_bookings.filter(check_in_status="checked_in").count(),
        "monthly_expenses": monthly_expenses,
    }


def check_overlapping_bookings(
    slot_ids: list, start_time: str, end_time: str | None = None
) -> dict:
    """Check which slots have overlapping bookings in given time range.

    Returns dict with booked_slot_ids and count.
    """
    from datetime import datetime

    from django.db.models import Q

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = (
            datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            if end_time
            else None
        )
    except ValueError:
        return {"error": "Invalid datetime format. Use ISO 8601"}

    query = Q(
        slot_id__in=slot_ids,
        check_in_status__in=["not_checked_in", "checked_in"],
    )

    if end_dt:
        query &= Q(start_time__lt=end_dt) & Q(end_time__gt=start_dt)
    else:
        query &= Q(end_time__gt=start_dt)

    overlapping = Booking.objects.filter(query)
    booked_slot_ids = list(overlapping.values_list("slot_id", flat=True).distinct())

    return {
        "booked_slot_ids": [str(sid) for sid in booked_slot_ids],
        "count": len(booked_slot_ids),
    }
