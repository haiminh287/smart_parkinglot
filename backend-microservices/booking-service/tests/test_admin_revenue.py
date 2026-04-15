"""
Tests for admin revenue API endpoints.
"""

import os
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking

GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET", "test-secret-for-ci")


@pytest.fixture
def admin_client():
    """Authenticated admin API client."""
    client = APIClient()
    client.credentials(
        HTTP_X_GATEWAY_SECRET=GATEWAY_SECRET,
        HTTP_X_USER_ID=str(uuid.uuid4()),
        HTTP_X_USER_EMAIL="admin@parksmart.com",
        HTTP_X_USER_ROLE="admin",
        HTTP_X_USER_IS_STAFF="true",
    )
    return client


@pytest.fixture
def regular_client():
    """Authenticated non-admin API client."""
    client = APIClient()
    client.credentials(
        HTTP_X_GATEWAY_SECRET=GATEWAY_SECRET,
        HTTP_X_USER_ID=str(uuid.uuid4()),
        HTTP_X_USER_EMAIL="user@parksmart.com",
        HTTP_X_USER_ROLE="user",
        HTTP_X_USER_IS_STAFF="false",
    )
    return client


def _make_booking(
    payment_status: str = "completed",
    check_in_status: str = "checked_out",
    price: Decimal = Decimal("50000"),
    payment_method: str = "online",
    created_at=None,
) -> Booking:
    """Helper to create a booking with given attributes."""
    now = timezone.now()
    booking = Booking.objects.create(
        user_id=str(uuid.uuid4()),
        user_email="test@parksmart.com",
        vehicle_id=str(uuid.uuid4()),
        vehicle_license_plate="51A-111.22",
        vehicle_type="Car",
        parking_lot_id=str(uuid.uuid4()),
        parking_lot_name="Test Lot",
        zone_id=str(uuid.uuid4()),
        zone_name="Zone A",
        slot_id=str(uuid.uuid4()),
        slot_code="A-01",
        package_type="hourly",
        start_time=now - timedelta(hours=2),
        end_time=now,
        payment_method=payment_method,
        payment_status=payment_status,
        check_in_status=check_in_status,
        price=price,
    )
    if created_at:
        # Force-update created_at (auto_now_add prevents direct set)
        Booking.objects.filter(pk=booking.pk).update(created_at=created_at)
        booking.refresh_from_db()
    return booking


# ---------------------------------------------------------------------------
# Revenue Summary
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestRevenueSummary:
    URL = "/bookings/admin/revenue/summary/"

    def test_empty_db_returns_zeros(self, admin_client):
        resp = admin_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total_revenue"] == 0
        assert data["total_bookings"] == 0
        assert data["completed_bookings"] == 0
        assert data["cancelled_bookings"] == 0
        assert data["active_bookings"] == 0
        assert data["average_booking_value"] == 0
        assert data["payment_methods"] == {}

    def test_revenue_aggregation(self, admin_client):
        _make_booking(price=Decimal("100000"), payment_status="completed")
        _make_booking(price=Decimal("200000"), payment_status="completed")
        _make_booking(price=Decimal("50000"), payment_status="pending")  # not counted

        resp = admin_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total_revenue"] == 300000.0
        assert data["completed_bookings"] == 2
        assert data["total_bookings"] == 3
        assert data["average_booking_value"] == 150000.0

    def test_booking_status_counts(self, admin_client):
        _make_booking(check_in_status="cancelled", payment_status="refunded", price=Decimal("10000"))
        _make_booking(check_in_status="checked_in", payment_status="completed", price=Decimal("20000"))
        _make_booking(check_in_status="checked_out", payment_status="completed", price=Decimal("30000"))

        resp = admin_client.get(self.URL)
        data = resp.json()
        assert data["cancelled_bookings"] == 1
        assert data["active_bookings"] == 1
        assert data["total_bookings"] == 3

    def test_payment_method_breakdown(self, admin_client):
        _make_booking(payment_method="online", price=Decimal("100000"))
        _make_booking(payment_method="online", price=Decimal("50000"))
        _make_booking(payment_method="on_exit", price=Decimal("75000"))

        resp = admin_client.get(self.URL)
        methods = resp.json()["payment_methods"]
        assert methods["online"]["count"] == 2
        assert methods["online"]["amount"] == 150000.0
        assert methods["on_exit"]["count"] == 1
        assert methods["on_exit"]["amount"] == 75000.0

    def test_non_admin_forbidden(self, regular_client):
        resp = regular_client.get(self.URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Daily Revenue
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestDailyRevenue:
    URL = "/bookings/admin/revenue/daily/"

    def test_default_30_days(self, admin_client):
        resp = admin_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert len(data) == 30

    def test_custom_days_param(self, admin_client):
        resp = admin_client.get(self.URL, {"days": 7})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert len(data) == 7

    def test_daily_data_contains_revenue(self, admin_client):
        now = timezone.now()
        _make_booking(price=Decimal("100000"), created_at=now)

        resp = admin_client.get(self.URL, {"days": 1})
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["revenue"] == 100000.0
        assert data[0]["bookings"] == 1

    def test_missing_days_filled_with_zeros(self, admin_client):
        resp = admin_client.get(self.URL, {"days": 3})
        data = resp.json()["data"]
        assert len(data) == 3
        for entry in data:
            assert "date" in entry
            assert "revenue" in entry
            assert "bookings" in entry

    def test_non_admin_forbidden(self, regular_client):
        resp = regular_client.get(self.URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Hourly Revenue
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestHourlyRevenue:
    URL = "/bookings/admin/revenue/hourly/"

    def test_returns_24_hours(self, admin_client):
        resp = admin_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert len(data) == 24
        hours = [e["hour"] for e in data]
        assert hours == list(range(24))

    def test_invalid_date_returns_400(self, admin_client):
        resp = admin_client.get(self.URL, {"date": "not-a-date"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_admin_forbidden(self, regular_client):
        resp = regular_client.get(self.URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN
