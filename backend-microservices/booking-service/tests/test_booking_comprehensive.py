"""
Comprehensive tests for booking-service.
Tests: PackagePricing model, Booking CRUD, check-in/check-out, cancellation,
       payment flow, booking stats, QR code, slot availability.
"""

import os
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from bookings import services
from bookings import views_lifecycle
from bookings.models import Booking, OutboxEvent, PackagePricing
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

# ═══════════════════════════════════════════════════
# FIXTURE HELPERS
# ═══════════════════════════════════════════════════


def gateway_headers(
    user_id="00000000-0000-0000-0000-000000000001", email="test@parksmart.com"
):
    """Return gateway auth headers dict for APIClient credentials."""
    return {
        "HTTP_X_GATEWAY_SECRET": os.environ.get("GATEWAY_SECRET", "test-secret-for-ci"),
        "HTTP_X_USER_ID": str(user_id),
        "HTTP_X_USER_EMAIL": email,
    }


def create_pricing(vehicle_type="Car", package_type="hourly", price="10000.00"):
    return PackagePricing.objects.create(
        vehicle_type=vehicle_type,
        package_type=package_type,
        price=Decimal(price),
    )


def create_booking(user_id=None, **kwargs):
    """Create a test booking with sensible defaults."""
    defaults = {
        "user_id": user_id or uuid.uuid4(),
        "user_email": "test@parksmart.com",
        "vehicle_id": uuid.uuid4(),
        "vehicle_license_plate": "51A-123.45",
        "vehicle_type": "Car",
        "parking_lot_id": uuid.uuid4(),
        "parking_lot_name": "Test Lot",
        "floor_id": uuid.uuid4(),
        "floor_level": 1,
        "zone_id": uuid.uuid4(),
        "zone_name": "Zone A",
        "slot_id": uuid.uuid4(),
        "slot_code": "A-01",
        "package_type": "hourly",
        "start_time": timezone.now(),
        "end_time": timezone.now() + timedelta(hours=2),
        "price": Decimal("20000.00"),
        "payment_status": "pending",
        "payment_method": "online",
        "check_in_status": "not_checked_in",
    }
    defaults.update(kwargs)
    return Booking.objects.create(**defaults)


# ═══════════════════════════════════════════════════
# PACKAGE PRICING MODEL TESTS
# ═══════════════════════════════════════════════════


class TestPackagePricingModel(TestCase):
    """Test PackagePricing model."""

    def test_create_hourly_car_pricing(self):
        pricing = create_pricing("Car", "hourly", "10000.00")
        assert pricing.vehicle_type == "Car"
        assert pricing.package_type == "hourly"
        assert pricing.price == Decimal("10000.00")

    def test_create_monthly_motorbike_pricing(self):
        pricing = create_pricing("Motorbike", "monthly", "200000.00")
        assert pricing.vehicle_type == "Motorbike"
        assert pricing.package_type == "monthly"

    def test_pricing_uuid_pk(self):
        pricing = create_pricing()
        assert isinstance(pricing.id, uuid.UUID)


# ═══════════════════════════════════════════════════
# BOOKING MODEL TESTS
# ═══════════════════════════════════════════════════


class TestBookingModel(TestCase):
    """Test Booking model fields and defaults."""

    def test_create_booking(self):
        booking = create_booking()
        assert isinstance(booking.id, uuid.UUID)
        assert booking.check_in_status == "not_checked_in"
        assert booking.payment_status == "pending"

    def test_booking_default_qr_code_data(self):
        booking = create_booking()
        # qr_code_data should be generated on create
        assert booking.qr_code_data is not None or booking.qr_code_data == ""

    def test_booking_check_in_status_choices(self):
        """Verify valid check_in_status values."""
        valid_statuses = [
            "not_checked_in",
            "checked_in",
            "checked_out",
            "no_show",
            "cancelled",
        ]
        for s in valid_statuses:
            booking = create_booking(check_in_status=s)
            assert booking.check_in_status == s

    def test_booking_payment_status_choices(self):
        valid_statuses = ["pending", "processing", "completed", "failed", "refunded"]
        for s in valid_statuses:
            booking = create_booking(payment_status=s)
            assert booking.payment_status == s

    def test_booking_hourly_fields(self):
        now = timezone.now()
        booking = create_booking(
            hourly_start=now,
            hourly_end=now + timedelta(hours=1),
            extended_until=now + timedelta(hours=2),
            late_fee_applied=True,
        )
        assert booking.hourly_start is not None
        assert booking.late_fee_applied is True


# ═══════════════════════════════════════════════════
# BOOKING CRUD API TESTS
# ═══════════════════════════════════════════════════


class TestBookingCRUD(TestCase):
    """Test booking list, create, retrieve, update, delete endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user_id = "00000000-0000-0000-0000-000000000001"
        self.client.credentials(**gateway_headers(self.user_id))
        create_pricing("Car", "hourly", "10000.00")

    def test_list_bookings(self):
        create_booking(user_id=uuid.UUID(self.user_id))
        response = self.client.get("/bookings/")
        assert response.status_code == 200

    def test_list_bookings_returns_only_user_bookings(self):
        our_booking = create_booking(user_id=uuid.UUID(self.user_id))
        other_booking = create_booking(user_id=uuid.uuid4())
        response = self.client.get("/bookings/")
        data = response.json()
        results = data if isinstance(data, list) else data.get("results", data)
        booking_ids = [b["id"] for b in results] if isinstance(results, list) else []
        assert isinstance(results, list)
        assert str(our_booking.id) in booking_ids
        assert str(other_booking.id) not in booking_ids

    def test_create_booking(self):
        response = self.client.post(
            "/bookings/",
            {
                "vehicle_id": str(uuid.uuid4()),
                "parking_lot_id": str(uuid.uuid4()),
                "zone_id": str(uuid.uuid4()),
                "slot_id": str(uuid.uuid4()),
                "package_type": "hourly",
                "start_time": timezone.now().isoformat(),
                "end_time": (timezone.now() + timedelta(hours=2)).isoformat(),
                "payment_method": "online",
            },
            format="json",
        )
        assert response.status_code in [201, 200]

    def test_retrieve_booking(self):
        booking = create_booking(user_id=uuid.UUID(self.user_id))
        response = self.client.get(f"/bookings/{booking.id}/")
        assert response.status_code == 200
        assert response.json()["id"] == str(booking.id)

    def test_retrieve_other_users_booking_forbidden(self):
        other_booking = create_booking(user_id=uuid.uuid4())
        response = self.client.get(f"/bookings/{other_booking.id}/")
        assert response.status_code in [403, 404]


# ═══════════════════════════════════════════════════
# CHECK-IN TESTS
# ═══════════════════════════════════════════════════


class TestCheckIn(TestCase):
    """Test booking check-in endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.client.credentials(**gateway_headers(str(self.user_id)))

    def test_checkin_success(self):
        booking = create_booking(
            user_id=self.user_id,
            check_in_status="not_checked_in",
            payment_status="completed",
        )
        response = self.client.post(f"/bookings/{booking.id}/checkin/")
        assert response.status_code == 200
        booking.refresh_from_db()
        assert booking.check_in_status == "checked_in"
        assert booking.checked_in_at is not None

    def test_checkin_already_checked_in(self):
        booking = create_booking(
            user_id=self.user_id,
            check_in_status="checked_in",
            checked_in_at=timezone.now(),
        )
        response = self.client.post(f"/bookings/{booking.id}/checkin/")
        assert response.status_code == 400

    def test_checkin_cancelled_booking(self):
        booking = create_booking(
            user_id=self.user_id,
            check_in_status="cancelled",
        )
        response = self.client.post(f"/bookings/{booking.id}/checkin/")
        assert response.status_code == 400

    def test_checkin_returns_409_when_reallocation_plan_fails(self):
        booking = create_booking(
            user_id=self.user_id,
            check_in_status="not_checked_in",
            payment_status="completed",
        )
        with patch.object(
            views_lifecycle.services,
            "build_checkin_reallocation_plan",
            return_value={"ok": False, "error": "No slot available"},
        ):
            response = self.client.post(f"/bookings/{booking.id}/checkin/")

        assert response.status_code == 409
        assert response.json()["error"] == "No slot available"


@pytest.mark.django_db
def test_should_return_conflict_when_slot_lock_retries_exhausted(monkeypatch):
    booking = create_booking(
        check_in_status="not_checked_in",
        payment_status="completed",
    )
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

    def fixed_plan(_booking: Booking):
        plan_calls["count"] += 1
        return {"ok": True, "plan": checkin_plan}

    monkeypatch.setattr(services, "build_checkin_reallocation_plan", fixed_plan)

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
        lambda _slot_id: AlwaysFailLock(),
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


# ═══════════════════════════════════════════════════
# CHECK-OUT TESTS
# ═══════════════════════════════════════════════════


class TestCheckOut(TestCase):
    """Test booking check-out endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.client.credentials(**gateway_headers(str(self.user_id)))

    def test_checkout_success(self):
        booking = create_booking(
            user_id=self.user_id,
            check_in_status="checked_in",
            checked_in_at=timezone.now() - timedelta(hours=1),
            payment_status="completed",
        )
        response = self.client.post(f"/bookings/{booking.id}/checkout/")
        assert response.status_code == 200
        booking.refresh_from_db()
        assert booking.check_in_status == "checked_out"

    def test_checkout_not_checked_in(self):
        booking = create_booking(
            user_id=self.user_id,
            check_in_status="not_checked_in",
        )
        response = self.client.post(f"/bookings/{booking.id}/checkout/")
        assert response.status_code == 400


# ═══════════════════════════════════════════════════
# CANCELLATION TESTS
# ═══════════════════════════════════════════════════


class TestCancellation(TestCase):
    """Test booking cancellation."""

    def setUp(self):
        self.client = APIClient()
        self.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.client.credentials(**gateway_headers(str(self.user_id)))

    def test_cancel_booking_success(self):
        booking = create_booking(
            user_id=self.user_id,
            check_in_status="not_checked_in",
        )
        response = self.client.post(f"/bookings/{booking.id}/cancel/")
        assert response.status_code == 200
        booking.refresh_from_db()
        assert booking.check_in_status == "cancelled"

    def test_cancel_already_checked_in(self):
        booking = create_booking(
            user_id=self.user_id,
            check_in_status="checked_in",
            checked_in_at=timezone.now(),
        )
        response = self.client.post(f"/bookings/{booking.id}/cancel/")
        assert response.status_code == 400


# ═══════════════════════════════════════════════════
# CUSTOM ENDPOINT TESTS
# ═══════════════════════════════════════════════════


class TestCustomEndpoints(TestCase):
    """Test current-parking, upcoming, stats, QR, check-slot-bookings."""

    def setUp(self):
        self.client = APIClient()
        self.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.client.credentials(**gateway_headers(str(self.user_id)))

    def test_current_parking(self):
        create_booking(
            user_id=self.user_id,
            check_in_status="checked_in",
            checked_in_at=timezone.now(),
        )
        response = self.client.get("/bookings/current-parking/")
        assert response.status_code == 200

    def test_current_parking_no_active(self):
        response = self.client.get("/bookings/current-parking/")
        assert response.status_code in [200, 404]

    def test_upcoming_bookings(self):
        create_booking(
            user_id=self.user_id,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
        )
        response = self.client.get("/bookings/upcoming/")
        assert response.status_code == 200

    def test_booking_stats(self):
        response = self.client.get("/bookings/stats/")
        assert response.status_code == 200

    def test_qr_code_endpoint(self):
        booking = create_booking(user_id=self.user_id)
        response = self.client.get(f"/bookings/{booking.id}/qr-code/")
        assert response.status_code == 200

    def test_check_slot_bookings(self):
        slot_id = str(uuid.uuid4())
        response = self.client.post(
            "/bookings/check-slot-bookings/",
            {
                "slot_ids": [slot_id],
                "start_time": timezone.now().isoformat(),
            },
            format="json",
        )
        assert response.status_code in [200, 400]


# ═══════════════════════════════════════════════════
# PACKAGE PRICING API TESTS
# ═══════════════════════════════════════════════════


class TestPackagePricingAPI(TestCase):
    """Test package pricing CRUD API."""

    def setUp(self):
        self.client = APIClient()
        self.client.credentials(**gateway_headers())

    def test_list_package_pricings(self):
        create_pricing("Car", "hourly", "10000.00")
        create_pricing("Motorbike", "daily", "5000.00")
        response = self.client.get("/bookings/packagepricings/")
        assert response.status_code == 200

    def test_create_package_pricing(self):
        response = self.client.post(
            "/bookings/packagepricings/",
            {
                "vehicle_type": "Car",
                "package_type": "weekly",
                "price": "150000.00",
            },
            format="json",
        )
        assert response.status_code in [201, 200]
