from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from bookings import services


@dataclass
class BookingStub:
    check_in_status: str = "not_checked_in"
    checked_in_at: object = None
    checked_out_at: object = None
    vehicle_type: str = "Car"
    package_type: str = "daily"
    hourly_end: object = None
    hourly_start: object = None
    price: Decimal = Decimal("0")
    late_fee_applied: bool = False
    update_fields_history: list[list[str]] = field(default_factory=list)

    def save(self, update_fields: list[str]) -> None:
        self.update_fields_history.append(update_fields)


def test_should_validate_checkin_status() -> None:
    assert services.validate_checkin(BookingStub(check_in_status="not_checked_in")) is None
    assert (
        services.validate_checkin(BookingStub(check_in_status="checked_in"))
        == "Only confirmed bookings can be checked in"
    )


def test_should_validate_checkout_status() -> None:
    assert services.validate_checkout(BookingStub(check_in_status="checked_in")) is None
    assert (
        services.validate_checkout(BookingStub(check_in_status="cancelled"))
        == "Only checked-in bookings can be checked out"
    )


def test_should_validate_cancel_status() -> None:
    assert services.validate_cancel(BookingStub(check_in_status="not_checked_in")) is None
    assert (
        services.validate_cancel(BookingStub(check_in_status="checked_out"))
        == "Cannot cancel booking that has already started or completed"
    )


def test_should_perform_checkin_and_save_expected_fields(monkeypatch) -> None:
    fixed_now = timezone.now()
    monkeypatch.setattr(services.timezone, "now", lambda: fixed_now)
    booking = BookingStub(check_in_status="not_checked_in")

    result = services.perform_checkin(booking)

    assert result.check_in_status == "checked_in"
    assert result.checked_in_at == fixed_now
    assert booking.update_fields_history[-1] == ["check_in_status", "checked_in_at"]


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

    pricing = services.perform_checkout(booking)

    assert booking.check_in_status == "checked_out"
    assert booking.checked_out_at == fixed_now
    assert booking.price == Decimal("45000")
    assert booking.late_fee_applied is True
    assert pricing["late_fee"] == Decimal("5000")


def test_should_calculate_current_cost_with_rounded_hours(monkeypatch) -> None:
    fixed_now = timezone.now()
    checked_in_at = fixed_now - timedelta(minutes=90)
    monkeypatch.setattr(services.timezone, "now", lambda: fixed_now)
    monkeypatch.setattr(services, "get_hourly_price", lambda _vehicle_type: Decimal("10000"))
    booking = BookingStub(checked_in_at=checked_in_at, vehicle_type="Car")

    result = services.calculate_current_cost(booking)

    assert result["duration_minutes"] == 90
    assert result["billable_hours"] == 2
    assert result["current_cost"] == 20000.0
    assert result["hourly_rate"] == Decimal("10000")
