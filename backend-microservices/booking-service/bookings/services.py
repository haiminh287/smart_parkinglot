"""
Business logic layer for booking-service.
All price calculations, late fee logic, validation, and
check-in/check-out rules live here. Views ONLY call service methods.
"""

import logging
import math
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import requests
from django.conf import settings as django_settings
from django.db import connection, transaction
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .events import create_booking_event, create_slot_event
from .models import Booking, PackagePricing

logger = logging.getLogger(__name__)

SLOT_LOCK_TIMEOUT_SECONDS = 5
CHECKIN_REALLOCATION_RETRIES = 3


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
    return None


def _get_service_headers(user_id: str = "system") -> dict:
    return {
        "Content-Type": "application/json",
        "X-Gateway-Secret": django_settings.GATEWAY_SECRET,
        "X-User-ID": str(user_id),
    }


def _normalize_slot_payload(raw: dict) -> dict | None:
    slot_id = raw.get("id")
    if not slot_id:
        return None
    return {
        "id": str(slot_id),
        "code": raw.get("code", ""),
        "zone_id": raw.get("zone", raw.get("zoneId", raw.get("zone_id"))),
    }


def _fetch_slots(*, status: str, vehicle_type: str, zone_id=None, lot_id=None) -> list:
    try:
        params = {
            "status": status,
            "vehicle_type": vehicle_type,
        }
        if zone_id:
            params["zone_id"] = str(zone_id)
        if lot_id:
            params["lot_id"] = str(lot_id)

        response = requests.get(
            f"{django_settings.PARKING_SERVICE_URL}/parking/slots/",
            params=params,
            headers=_get_service_headers(),
            timeout=5,
        )
        if response.status_code != 200:
            logger.warning(
                "Slot query failed (%s): %s",
                response.status_code,
                response.text[:150],
            )
            return []

        payload = response.json()
        rows = payload.get("results", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            return []

        slots = []
        for row in rows:
            normalized = _normalize_slot_payload(row)
            if normalized:
                slots.append(normalized)
        return slots
    except requests.RequestException as exc:
        logger.warning("Failed to fetch slot candidates: %s", exc)
        return []


def _fetch_zone_info(zone_id) -> dict | None:
    try:
        response = requests.get(
            f"{django_settings.PARKING_SERVICE_URL}/parking/zones/{zone_id}/",
            headers=_get_service_headers(),
            timeout=5,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return {
            "name": data.get("name", ""),
            "floor_id": data.get("floorId", data.get("floor_id")),
        }
    except requests.RequestException:
        return None


def _fetch_floor_info(floor_id) -> dict | None:
    try:
        response = requests.get(
            f"{django_settings.PARKING_SERVICE_URL}/parking/floors/{floor_id}/",
            headers=_get_service_headers(),
            timeout=5,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return {
            "level": data.get("level"),
            "parking_lot_id": data.get("parkingLotId", data.get("parking_lot_id")),
        }
    except requests.RequestException:
        return None


def _fetch_lot_info(lot_id) -> dict | None:
    try:
        response = requests.get(
            f"{django_settings.PARKING_SERVICE_URL}/parking/lots/{lot_id}/",
            headers=_get_service_headers(),
            timeout=5,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return {"name": data.get("name", "")}
    except requests.RequestException:
        return None


def _slot_has_overlap(
    slot_id,
    window_start,
    window_end,
    *,
    exclude_booking_id,
) -> bool:
    query = (
        Booking.objects.filter(
            slot_id=slot_id,
            check_in_status__in=["not_checked_in", "checked_in"],
            start_time__lt=window_end,
        )
        .filter(Q(end_time__isnull=True) | Q(end_time__gt=window_start))
        .exclude(id=exclude_booking_id)
    )
    return query.exists()


def _normalize_uuid(raw_id):
    if not raw_id:
        return None
    if isinstance(raw_id, UUID):
        return raw_id
    try:
        return UUID(str(raw_id))
    except (TypeError, ValueError, AttributeError):
        return None


def _build_slot_plan(
    booking: Booking, slot_payload: dict, arrival_time, new_end_time
) -> dict:
    slot_id = _normalize_uuid(slot_payload.get("id")) or booking.slot_id
    slot_code = slot_payload.get("code") or booking.slot_code
    zone_id = _normalize_uuid(slot_payload.get("zone_id")) or booking.zone_id

    zone_name = booking.zone_name
    floor_id = booking.floor_id
    floor_level = booking.floor_level
    parking_lot_id = booking.parking_lot_id
    parking_lot_name = booking.parking_lot_name

    if zone_id and zone_id != booking.zone_id:
        zone_info = _fetch_zone_info(zone_id)
        if zone_info:
            zone_name = zone_info.get("name") or zone_name
            floor_id = _normalize_uuid(zone_info.get("floor_id")) or floor_id

    if floor_id and floor_id != booking.floor_id:
        floor_info = _fetch_floor_info(floor_id)
        if floor_info:
            floor_level = floor_info.get("level", floor_level)
            parking_lot_id = (
                _normalize_uuid(floor_info.get("parking_lot_id")) or parking_lot_id
            )

    if parking_lot_id and parking_lot_id != booking.parking_lot_id:
        lot_info = _fetch_lot_info(parking_lot_id)
        if lot_info:
            parking_lot_name = lot_info.get("name") or parking_lot_name

    return {
        "arrival_time": arrival_time,
        "start_time": arrival_time,
        "end_time": new_end_time,
        "hourly_start": arrival_time,
        "hourly_end": new_end_time,
        "slot_id": slot_id,
        "slot_code": slot_code,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "floor_id": floor_id,
        "floor_level": floor_level,
        "parking_lot_id": parking_lot_id,
        "parking_lot_name": parking_lot_name,
    }


@contextmanager
def _acquire_slot_assignment_lock(slot_id):
    """Acquire a short-lived per-slot DB lock for concurrent check-in safety."""
    normalized_slot_id = _normalize_uuid(slot_id)
    if not normalized_slot_id:
        yield
        return

    lock_key = f"booking-checkin-slot:{normalized_slot_id}"
    vendor = connection.vendor
    mysql_lock_acquired = False

    try:
        with connection.cursor() as cursor:
            if vendor == "mysql":
                cursor.execute(
                    "SELECT GET_LOCK(%s, %s)",
                    [lock_key, SLOT_LOCK_TIMEOUT_SECONDS],
                )
                row = cursor.fetchone()
                mysql_lock_acquired = bool(row and row[0] == 1)
                if not mysql_lock_acquired:
                    raise RuntimeError("Unable to acquire slot lock")
            elif vendor == "postgresql":
                # Transaction-scoped advisory lock; auto-released on commit/rollback.
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    [lock_key],
                )

        yield
    finally:
        if vendor == "mysql" and mysql_lock_acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT RELEASE_LOCK(%s)", [lock_key])


def build_checkin_reallocation_plan(booking: Booking) -> dict:
    """Compute slot/time reassignment plan for early-arrival check-in."""
    arrival_time = timezone.now()
    if (
        booking.start_time
        and booking.end_time
        and booking.end_time > booking.start_time
    ):
        original_duration = booking.end_time - booking.start_time
    elif (
        booking.hourly_start
        and booking.hourly_end
        and booking.hourly_end > booking.hourly_start
    ):
        original_duration = booking.hourly_end - booking.hourly_start
    else:
        original_duration = timedelta(hours=1)
    new_end_time = arrival_time + original_duration

    if booking.slot_id and not _slot_has_overlap(
        booking.slot_id,
        arrival_time,
        new_end_time,
        exclude_booking_id=booking.id,
    ):
        current_slot = {
            "id": str(booking.slot_id),
            "code": booking.slot_code,
            "zone_id": str(booking.zone_id),
        }
        return {
            "ok": True,
            "plan": _build_slot_plan(booking, current_slot, arrival_time, new_end_time),
        }

    same_zone_slots = _fetch_slots(
        status="available",
        vehicle_type=booking.vehicle_type,
        zone_id=booking.zone_id,
    )
    for slot in same_zone_slots:
        slot_id = _normalize_uuid(slot.get("id"))
        if not slot_id:
            continue
        if _slot_has_overlap(
            slot_id,
            arrival_time,
            new_end_time,
            exclude_booking_id=booking.id,
        ):
            continue
        return {
            "ok": True,
            "plan": _build_slot_plan(booking, slot, arrival_time, new_end_time),
        }

    lot_slots = _fetch_slots(
        status="available",
        vehicle_type=booking.vehicle_type,
        lot_id=booking.parking_lot_id,
    )
    for slot in lot_slots:
        slot_id = _normalize_uuid(slot.get("id"))
        if not slot_id:
            continue
        if _slot_has_overlap(
            slot_id,
            arrival_time,
            new_end_time,
            exclude_booking_id=booking.id,
        ):
            continue
        return {
            "ok": True,
            "plan": _build_slot_plan(booking, slot, arrival_time, new_end_time),
        }

    return {
        "ok": False,
        "error": "Không còn slot phù hợp cho khung giờ mới khi check-in sớm.",
    }


def _commit_checkin_with_plan(booking: Booking, checkin_plan: dict) -> Booking:
    """Apply booking changes and write outbox events in deterministic order."""
    previous_slot_id = booking.slot_id
    perform_checkin(booking, checkin_plan)

    new_slot_id = booking.slot_id
    if previous_slot_id and previous_slot_id != new_slot_id:
        create_slot_event(previous_slot_id, "available", booking)
    if new_slot_id:
        create_slot_event(new_slot_id, "occupied", booking)
    create_booking_event("booking.checked_in", booking)
    return booking


def perform_checkin_with_reallocation(booking: Booking) -> dict:
    """Transactional check-in with in-txn revalidation and ordered event writes."""
    with transaction.atomic():
        locked_booking = Booking.objects.select_for_update().get(pk=booking.pk)

        error = validate_checkin(locked_booking)
        if error:
            return {"ok": False, "status_code": 400, "error": error}

        for _ in range(CHECKIN_REALLOCATION_RETRIES):
            plan_result = build_checkin_reallocation_plan(locked_booking)
            if not plan_result.get("ok"):
                return {
                    "ok": False,
                    "status_code": 409,
                    "error": plan_result.get(
                        "error", "No slot available for check-in"
                    ),
                }

            checkin_plan = plan_result["plan"]
            slot_id = checkin_plan.get("slot_id", locked_booking.slot_id)
            if not slot_id:
                return {
                    "ok": False,
                    "status_code": 409,
                    "error": "Booking has no valid slot for check-in",
                }

            try:
                with _acquire_slot_assignment_lock(slot_id):
                    if _slot_has_overlap(
                        slot_id,
                        checkin_plan["start_time"],
                        checkin_plan["end_time"],
                        exclude_booking_id=locked_booking.id,
                    ):
                        continue
                    booking_after_checkin = _commit_checkin_with_plan(
                        locked_booking,
                        checkin_plan,
                    )
                    return {"ok": True, "booking": booking_after_checkin}
            except RuntimeError:
                logger.warning("Could not acquire slot lock for slot_id=%s", slot_id)
                continue

        return {
            "ok": False,
            "status_code": 409,
            "error": "No slot available for check-in after concurrent revalidation",
        }


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


def perform_checkin(booking: Booking, plan: dict | None = None) -> Booking:
    """Execute check-in on a validated booking using resolved slot/time plan."""
    checkin_plan = plan or build_checkin_reallocation_plan(booking).get("plan", {})
    arrival_time = checkin_plan.get("arrival_time", timezone.now())

    booking.check_in_status = "checked_in"
    booking.checked_in_at = arrival_time
    booking.start_time = checkin_plan.get("start_time", booking.start_time)
    booking.end_time = checkin_plan.get("end_time", booking.end_time)
    booking.hourly_start = checkin_plan.get("hourly_start", booking.hourly_start)
    booking.hourly_end = checkin_plan.get("hourly_end", booking.hourly_end)
    booking.slot_id = checkin_plan.get("slot_id", booking.slot_id)
    booking.slot_code = checkin_plan.get("slot_code", booking.slot_code)
    booking.zone_id = checkin_plan.get("zone_id", booking.zone_id)
    booking.zone_name = checkin_plan.get("zone_name", booking.zone_name)
    booking.floor_id = checkin_plan.get("floor_id", booking.floor_id)
    booking.floor_level = checkin_plan.get("floor_level", booking.floor_level)
    booking.parking_lot_id = checkin_plan.get("parking_lot_id", booking.parking_lot_id)
    booking.parking_lot_name = checkin_plan.get(
        "parking_lot_name", booking.parking_lot_name
    )

    with transaction.atomic():
        booking.save(
            update_fields=[
                "check_in_status",
                "checked_in_at",
                "start_time",
                "end_time",
                "hourly_start",
                "hourly_end",
                "slot_id",
                "slot_code",
                "zone_id",
                "zone_name",
                "floor_id",
                "floor_level",
                "parking_lot_id",
                "parking_lot_name",
                "updated_at",
            ]
        )
    return booking


def perform_checkout(booking: Booking) -> dict:
    """
    Execute checkout atomically with in-txn locked-state revalidation.

    Returns:
        - {"ok": True, "pricing": {...}} on success
        - {"ok": False, "status_code": int, "error": str} when locked state is invalid
    """
    with transaction.atomic():
        locked_booking = Booking.objects.select_for_update().get(pk=booking.pk)

        error = validate_checkout(locked_booking)
        if error:
            return {"ok": False, "status_code": 409, "error": error}

        locked_booking.check_in_status = "checked_out"
        locked_booking.checked_out_at = timezone.now()

        pricing = calculate_checkout_price(locked_booking)
        locked_booking.price = pricing["total_amount"]
        locked_booking.late_fee_applied = pricing["late_fee_applied"]
        locked_booking.save(
            update_fields=[
                "check_in_status",
                "checked_out_at",
                "price",
                "late_fee_applied",
            ]
        )

        if locked_booking.slot_id:
            create_slot_event(locked_booking.slot_id, "available", locked_booking)
        create_booking_event("booking.checked_out", locked_booking)

        return {"ok": True, "pricing": pricing}


def perform_cancel(booking: Booking) -> dict:
    """
    Execute cancellation atomically with in-txn locked-state revalidation.

    Returns:
        - {"ok": True, "booking": Booking} on success
        - {"ok": False, "status_code": int, "error": str} when locked state is invalid
    """
    with transaction.atomic():
        locked_booking = Booking.objects.select_for_update().get(pk=booking.pk)

        error = validate_cancel(locked_booking)
        if error:
            return {"ok": False, "status_code": 409, "error": error}

        locked_booking.check_in_status = "cancelled"
        locked_booking.save(update_fields=["check_in_status"])

        if locked_booking.slot_id:
            create_slot_event(locked_booking.slot_id, "available", locked_booking)
        create_booking_event("booking.cancelled", locked_booking)

        return {"ok": True, "booking": locked_booking}


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
