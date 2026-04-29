"""
Shared test fixtures for booking-service.
"""

import os
import uuid
from decimal import Decimal

import pytest
from bookings.models import Booking, PackagePricing
from django.utils import timezone
from rest_framework.test import APIClient

GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET", "test-secret-" + uuid.uuid4().hex[:8])
TEST_USER_ID = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def _set_gateway_secret_env(monkeypatch):
    """Ensure GATEWAY_SECRET is set for every test."""
    monkeypatch.setenv("GATEWAY_SECRET", GATEWAY_SECRET)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def gateway_headers():
    return {
        "HTTP_X_GATEWAY_SECRET": GATEWAY_SECRET,
        "HTTP_X_USER_ID": TEST_USER_ID,
        "HTTP_X_USER_EMAIL": "testuser@parksmart.com",
        "HTTP_X_USER_ROLE": "user",
        "HTTP_X_USER_IS_STAFF": "false",
    }


@pytest.fixture
def admin_gateway_headers():
    return {
        "HTTP_X_GATEWAY_SECRET": GATEWAY_SECRET,
        "HTTP_X_USER_ID": str(uuid.uuid4()),
        "HTTP_X_USER_EMAIL": "admin@parksmart.com",
        "HTTP_X_USER_ROLE": "admin",
        "HTTP_X_USER_IS_STAFF": "true",
    }


@pytest.fixture
def auth_client(api_client, gateway_headers):
    api_client.credentials(**gateway_headers)
    return api_client


@pytest.fixture
def admin_client(admin_gateway_headers):
    client = APIClient()
    client.credentials(**admin_gateway_headers)
    return client


@pytest.fixture
def pricing(db):
    """Create default package pricing."""
    return PackagePricing.objects.create(
        vehicle_type="Car",
        package_type="hourly",
        price=Decimal("10000"),
        is_active=True,
    )


@pytest.fixture
def booking(db, pricing):
    """Create a test booking."""
    now = timezone.now()
    return Booking.objects.create(
        user_id=TEST_USER_ID,
        vehicle_license_plate="51A-999.88",
        vehicle_type="Car",
        parking_lot_id=str(uuid.uuid4()),
        parking_lot_name="Test Lot",
        floor_name="F1",
        zone_id=str(uuid.uuid4()),
        zone_name="Zone A",
        slot_id=str(uuid.uuid4()),
        slot_code="A-01",
        package_type="hourly",
        start_time=now,
        end_time=now + timezone.timedelta(hours=2),
        total_amount=Decimal("20000"),
    )
