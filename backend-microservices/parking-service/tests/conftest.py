"""
Shared test fixtures for parking-service.
"""

import uuid
import pytest
from rest_framework.test import APIClient
from infrastructure.models import ParkingLot, Floor, Zone, CarSlot, Camera

GATEWAY_SECRET = "gateway-internal-secret-key"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def gateway_headers():
    return {
        "HTTP_X_GATEWAY_SECRET": GATEWAY_SECRET,
        "HTTP_X_USER_ID": str(uuid.uuid4()),
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
def parking_lot(db):
    return ParkingLot.objects.create(
        name="Test Lot",
        address="123 Test St",
        latitude=10.762622,
        longitude=106.660172,
        total_slots=100,
        is_open=True,
    )


@pytest.fixture
def floor(db, parking_lot):
    return Floor.objects.create(
        parking_lot=parking_lot,
        name="Floor 1",
        level=1,
    )


@pytest.fixture
def zone(db, floor):
    return Zone.objects.create(
        floor=floor,
        name="Zone A",
        vehicle_type="Car",
        capacity=20,
    )


@pytest.fixture
def car_slot(db, zone):
    return CarSlot.objects.create(
        zone=zone,
        code="A-01",
        status="available",
    )


@pytest.fixture
def camera(db, zone):
    return Camera.objects.create(
        name="Test Camera",
        ip_address="192.168.100.23",
        port=554,
        zone=zone,
        stream_url="rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main",
        is_active=True,
    )
