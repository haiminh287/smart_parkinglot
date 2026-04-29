from contextlib import nullcontext
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from bookings import services
from bookings.models import Booking, OutboxEvent
from django.utils import timezone


def _create_booking(*, slot_id=None, start_time=None, end_time=None) -> Booking:
    now = timezone.now()
    booking_start = start_time or now + timedelta(hours=1)
    booking_end = end_time or booking_start + timedelta(hours=2)
    return Booking.objects.create(
        user_id=uuid4(),
        user_email="test@parksmart.com",
        vehicle_id=uuid4(),
        vehicle_license_plate="51A-123.45",
        vehicle_type="Car",
        parking_lot_id=uuid4(),
        parking_lot_name="Test Lot",
        floor_id=uuid4(),
        floor_level=1,
        zone_id=uuid4(),
        zone_name="Zone A",
        slot_id=slot_id or uuid4(),
        slot_code="A-01",
        package_type="hourly",
        start_time=booking_start,
        end_time=booking_end,
        payment_status="completed",
        payment_method="online",
        price=Decimal("20000.00"),
        check_in_status="not_checked_in",
    )


@pytest.mark.django_db
def test_should_fail_second_checkin_when_two_bookings_contend_for_same_replacement_slot(
    monkeypatch,
) -> None:
    replacement_slot_id = uuid4()
    now = timezone.now()
    checkin_start = now
    checkin_end = now + timedelta(hours=2)

    booking_a = _create_booking(slot_id=uuid4())
    booking_b = _create_booking(slot_id=uuid4())

    def fixed_plan(_booking: Booking) -> dict:
        return {
            "ok": True,
            "plan": {
                "arrival_time": checkin_start,
                "start_time": checkin_start,
                "end_time": checkin_end,
                "hourly_start": checkin_start,
                "hourly_end": checkin_end,
                "slot_id": replacement_slot_id,
                "slot_code": "A-77",
            },
        }

    monkeypatch.setattr(services, "build_checkin_reallocation_plan", fixed_plan)
    monkeypatch.setattr(services, "_acquire_slot_assignment_lock", lambda _sid: nullcontext())

    first_result = services.perform_checkin_with_reallocation(booking_a)
    second_result = services.perform_checkin_with_reallocation(booking_b)

    assert first_result["ok"] is True
    assert second_result["ok"] is False
    assert second_result["status_code"] == 409
    assert "concurrent revalidation" in second_result["error"]


@pytest.mark.django_db
def test_should_emit_events_in_expected_order_when_slot_changes() -> None:
    old_slot_id = uuid4()
    new_slot_id = uuid4()
    booking = _create_booking(slot_id=old_slot_id)

    now = timezone.now()
    checkin_plan = {
        "arrival_time": now,
        "start_time": now,
        "end_time": now + timedelta(hours=2),
        "hourly_start": now,
        "hourly_end": now + timedelta(hours=2),
        "slot_id": new_slot_id,
        "slot_code": "B-09",
    }

    services._commit_checkin_with_plan(booking, checkin_plan)

    events = list(OutboxEvent.objects.order_by("id"))
    assert len(events) == 3
    assert events[0].event_type == "slot.status_changed"
    assert events[0].payload["slot_id"] == str(old_slot_id)
    assert events[0].payload["status"] == "available"
    assert events[1].event_type == "slot.status_changed"
    assert events[1].payload["slot_id"] == str(new_slot_id)
    assert events[1].payload["status"] == "occupied"
    assert events[2].event_type == "booking.checked_in"
    assert events[2].payload["slot_id"] == str(new_slot_id)


@pytest.mark.django_db
def test_should_not_persist_partial_outbox_events_when_checkin_commit_fails(
    monkeypatch,
) -> None:
    old_slot_id = uuid4()
    new_slot_id = uuid4()
    booking = _create_booking(slot_id=old_slot_id)
    now = timezone.now()

    checkin_plan = {
        "arrival_time": now,
        "start_time": now,
        "end_time": now + timedelta(hours=2),
        "hourly_start": now,
        "hourly_end": now + timedelta(hours=2),
        "slot_id": new_slot_id,
        "slot_code": "B-11",
    }

    monkeypatch.setattr(
        services,
        "build_checkin_reallocation_plan",
        lambda _booking: {"ok": True, "plan": checkin_plan},
    )
    monkeypatch.setattr(services, "_acquire_slot_assignment_lock", lambda _sid: nullcontext())

    original_create_slot_event = services.create_slot_event
    call_count = {"count": 0}

    def fail_on_second_slot_event(slot_id, status, booking_obj=None):
        call_count["count"] += 1
        if call_count["count"] == 2:
            raise ValueError("forced outbox failure")
        return original_create_slot_event(slot_id, status, booking_obj)

    monkeypatch.setattr(services, "create_slot_event", fail_on_second_slot_event)

    with pytest.raises(ValueError, match="forced outbox failure"):
        services.perform_checkin_with_reallocation(booking)

    booking.refresh_from_db()
    assert booking.check_in_status == "not_checked_in"
    assert booking.checked_in_at is None
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db
def test_should_fail_when_slot_lock_cannot_be_acquired_after_all_retries(
    monkeypatch,
) -> None:
    booking = _create_booking(slot_id=uuid4())
    now = timezone.now()

    checkin_plan = {
        "arrival_time": now,
        "start_time": now,
        "end_time": now + timedelta(hours=2),
        "hourly_start": now,
        "hourly_end": now + timedelta(hours=2),
        "slot_id": booking.slot_id,
        "slot_code": booking.slot_code,
    }

    plan_calls = {"count": 0}

    def fixed_plan(_booking: Booking) -> dict:
        plan_calls["count"] += 1
        return {"ok": True, "plan": checkin_plan}

    monkeypatch.setattr(
        services,
        "build_checkin_reallocation_plan",
        fixed_plan,
    )

    attempts = {"count": 0}

    class AlwaysFailLock:
        def __enter__(self):
            attempts["count"] += 1
            raise RuntimeError("Unable to acquire slot lock")

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    monkeypatch.setattr(
        services,
        "_acquire_slot_assignment_lock",
        lambda _sid: AlwaysFailLock(),
    )

    result = services.perform_checkin_with_reallocation(booking)

    assert result["ok"] is False
    assert result["status_code"] == 409
    assert "concurrent revalidation" in result["error"]
    assert attempts["count"] == services.CHECKIN_REALLOCATION_RETRIES
    assert plan_calls["count"] == services.CHECKIN_REALLOCATION_RETRIES

    booking.refresh_from_db()
    assert booking.check_in_status == "not_checked_in"
    assert booking.checked_in_at is None
    assert OutboxEvent.objects.count() == 0