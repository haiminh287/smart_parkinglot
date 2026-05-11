from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from bookings import services
from django.utils import timezone


@dataclass
class BookingStub:
    id: object = field(default_factory=uuid4)
    check_in_status: str = "not_checked_in"
    checked_in_at: object = None
    checked_out_at: object = None
    vehicle_type: str = "Car"
    package_type: str = "daily"
    start_time: object = None
    end_time: object = None
    hourly_end: object = None
    hourly_start: object = None
    slot_id: object = field(default_factory=uuid4)
    slot_code: str = "A-01"
    zone_id: object = field(default_factory=uuid4)
    zone_name: str = "Zone A"
    floor_id: object = field(default_factory=uuid4)
    floor_level: int = 1
    parking_lot_id: object = field(default_factory=uuid4)
    parking_lot_name: str = "Test Lot"
    price: Decimal = Decimal("0")
    late_fee_applied: bool = False
    update_fields_history: list[list[str]] = field(default_factory=list)

    def save(self, update_fields: list[str]) -> None:
        self.update_fields_history.append(update_fields)


def test_should_validate_checkin_status() -> None:
    assert (
        services.validate_checkin(BookingStub(check_in_status="not_checked_in")) is None
    )
    assert (
        services.validate_checkin(BookingStub(check_in_status="checked_in"))
        == "Cannot check in: booking is already checked in"
    )


def test_should_validate_checkout_status() -> None:
    assert services.validate_checkout(BookingStub(check_in_status="checked_in")) is None
    assert (
        services.validate_checkout(BookingStub(check_in_status="cancelled"))
        == "Only checked-in bookings can be checked out"
    )


def test_should_validate_cancel_status() -> None:
    assert (
        services.validate_cancel(BookingStub(check_in_status="not_checked_in")) is None
    )
    assert (
        services.validate_cancel(BookingStub(check_in_status="checked_out"))
        == "Cannot cancel booking that has already started or completed"
    )


def test_should_perform_checkin_and_save_expected_fields(monkeypatch) -> None:
    fixed_now = timezone.now()
    monkeypatch.setattr(services.timezone, "now", lambda: fixed_now)
    monkeypatch.setattr(services.transaction, "atomic", lambda: nullcontext())
    booking = BookingStub(check_in_status="not_checked_in")
    checkin_plan = {"arrival_time": fixed_now}

    result = services.perform_checkin(booking, checkin_plan)

    assert result.check_in_status == "checked_in"
    assert result.checked_in_at == fixed_now
    assert "check_in_status" in booking.update_fields_history[-1]
    assert "checked_in_at" in booking.update_fields_history[-1]


def test_should_keep_original_slot_when_early_arrival_slot_has_no_conflict(
    monkeypatch,
) -> None:
    fixed_now = timezone.now()
    original_start = fixed_now + timedelta(minutes=30)
    original_end = original_start + timedelta(hours=2)
    booking = BookingStub(start_time=original_start, end_time=original_end)

    monkeypatch.setattr(services.timezone, "now", lambda: fixed_now)
    monkeypatch.setattr(services, "_slot_has_overlap", lambda *args, **kwargs: False)

    plan_result = services.build_checkin_reallocation_plan(booking)

    assert plan_result["ok"] is True
    plan = plan_result["plan"]
    assert plan["slot_id"] == booking.slot_id
    assert plan["start_time"] == fixed_now
    assert plan["end_time"] == fixed_now + timedelta(hours=2)


def test_should_reallocate_to_same_zone_slot_when_original_slot_conflicts(
    monkeypatch,
) -> None:
    fixed_now = timezone.now()
    original_start = fixed_now + timedelta(minutes=15)
    original_end = original_start + timedelta(hours=1)
    booking = BookingStub(start_time=original_start, end_time=original_end)
    replacement_slot_id = uuid4()

    monkeypatch.setattr(services.timezone, "now", lambda: fixed_now)

    def fake_overlap(slot_id, *_args, **_kwargs):
        return slot_id == booking.slot_id

    monkeypatch.setattr(services, "_slot_has_overlap", fake_overlap)

    def fake_fetch_slots(*, status, vehicle_type, zone_id=None, lot_id=None):
        if zone_id:
            return [
                {
                    "id": str(replacement_slot_id),
                    "code": "A-02",
                    "zone_id": str(booking.zone_id),
                }
            ]
        return []

    monkeypatch.setattr(services, "_fetch_slots", fake_fetch_slots)

    plan_result = services.build_checkin_reallocation_plan(booking)

    assert plan_result["ok"] is True
    plan = plan_result["plan"]
    assert plan["slot_id"] == replacement_slot_id
    assert plan["slot_code"] == "A-02"
    assert plan["zone_id"] == booking.zone_id


def test_should_fail_checkin_plan_when_no_slot_matches_new_window(monkeypatch) -> None:
    fixed_now = timezone.now()
    original_start = fixed_now + timedelta(minutes=45)
    original_end = original_start + timedelta(hours=1)
    booking = BookingStub(start_time=original_start, end_time=original_end)

    monkeypatch.setattr(services.timezone, "now", lambda: fixed_now)
    monkeypatch.setattr(services, "_slot_has_overlap", lambda *args, **kwargs: True)

    monkeypatch.setattr(
        services,
        "_fetch_slots",
        lambda **_kwargs: [
            {"id": str(uuid4()), "code": "A-09", "zone_id": str(booking.zone_id)}
        ],
    )

    plan_result = services.build_checkin_reallocation_plan(booking)

    assert plan_result["ok"] is False
    assert "Không còn slot phù hợp" in plan_result["error"]


def test_should_perform_checkout_and_apply_pricing(monkeypatch) -> None:
    fixed_now = timezone.now()
    monkeypatch.setattr(services.timezone, "now", lambda: fixed_now)
    monkeypatch.setattr(
        services,
        "calculate_checkout_price",
        lambda _booking: {
            "total_amount": Decimal("45000"),
            "late_fee": Decimal("5000"),
            "late_fee_applied": True,
            "total_hours": 3,
            "hourly_price": Decimal("15000"),
        },
    )
    booking = BookingStub(check_in_status="checked_in")
    booking.pk = booking.id

    class _FakeLockedQuery:
        def __init__(self, locked_booking):
            self._locked_booking = locked_booking

        def get(self, pk):
            assert pk == booking.id
            return self._locked_booking

    class _FakeBookingManager:
        def select_for_update(self):
            return _FakeLockedQuery(booking)

    monkeypatch.setattr(services, "transaction", type("_T", (), {"atomic": staticmethod(nullcontext)}))
    monkeypatch.setattr(services.Booking, "objects", _FakeBookingManager())
    monkeypatch.setattr(services, "create_slot_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "create_booking_event", lambda *_args, **_kwargs: None)

    result = services.perform_checkout(booking)
    pricing = result["pricing"]

    assert result["ok"] is True
    assert booking.check_in_status == "checked_out"
    assert booking.checked_out_at == fixed_now
    assert booking.price == Decimal("45000")
    assert booking.late_fee_applied is True
    assert pricing["late_fee"] == Decimal("5000")


def test_should_fail_second_checkout_after_locked_status_changed_and_not_emit_events(
    monkeypatch,
) -> None:
    booking = BookingStub(check_in_status="checked_in")
    booking.pk = booking.id
    locked_booking = BookingStub(id=booking.id, check_in_status="checked_out")

    class _FakeLockedQuery:
        def __init__(self, db_booking):
            self._db_booking = db_booking

        def get(self, pk):
            assert pk == booking.id
            return self._db_booking

    class _FakeBookingManager:
        def select_for_update(self):
            return _FakeLockedQuery(locked_booking)

    slot_events = []
    booking_events = []

    monkeypatch.setattr(
        services, "transaction", type("_T", (), {"atomic": staticmethod(nullcontext)})
    )
    monkeypatch.setattr(services.Booking, "objects", _FakeBookingManager())
    monkeypatch.setattr(
        services, "create_slot_event", lambda *args, **kwargs: slot_events.append(args)
    )
    monkeypatch.setattr(
        services,
        "create_booking_event",
        lambda *args, **kwargs: booking_events.append(args),
    )

    result = services.perform_checkout(booking)

    assert result == {
        "ok": False,
        "status_code": 409,
        "error": "Only checked-in bookings can be checked out",
    }
    assert slot_events == []
    assert booking_events == []


def test_should_fail_second_cancel_after_locked_status_changed_and_not_emit_events(
    monkeypatch,
) -> None:
    booking = BookingStub(check_in_status="not_checked_in")
    booking.pk = booking.id
    locked_booking = BookingStub(id=booking.id, check_in_status="checked_out")

    class _FakeLockedQuery:
        def __init__(self, db_booking):
            self._db_booking = db_booking

        def get(self, pk):
            assert pk == booking.id
            return self._db_booking

    class _FakeBookingManager:
        def select_for_update(self):
            return _FakeLockedQuery(locked_booking)

    slot_events = []
    booking_events = []

    monkeypatch.setattr(
        services, "transaction", type("_T", (), {"atomic": staticmethod(nullcontext)})
    )
    monkeypatch.setattr(services.Booking, "objects", _FakeBookingManager())
    monkeypatch.setattr(
        services, "create_slot_event", lambda *args, **kwargs: slot_events.append(args)
    )
    monkeypatch.setattr(
        services,
        "create_booking_event",
        lambda *args, **kwargs: booking_events.append(args),
    )

    result = services.perform_cancel(booking)

    assert result == {
        "ok": False,
        "status_code": 409,
        "error": "Cannot cancel booking that has already started or completed",
    }
    assert slot_events == []
    assert booking_events == []


def test_should_calculate_current_cost_with_rounded_hours(monkeypatch) -> None:
    fixed_now = timezone.now()
    checked_in_at = fixed_now - timedelta(minutes=90)
    monkeypatch.setattr(services.timezone, "now", lambda: fixed_now)
    monkeypatch.setattr(
        services, "get_hourly_price", lambda _vehicle_type: Decimal("10000")
    )
    booking = BookingStub(checked_in_at=checked_in_at, vehicle_type="Car")

    result = services.calculate_current_cost(booking)

    assert result["duration_minutes"] == 90
    assert result["billable_hours"] == 2
    assert result["current_cost"] == 20000.0
    assert result["hourly_rate"] == Decimal("10000")
