"""
Comprehensive tests for vehicle-service.
Tests: Vehicle model, CRUD API, set-default, user isolation.
"""

import os
import uuid

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from vehicles.models import Vehicle

# ═══════════════════════════════════════════════════
# FIXTURE HELPERS
# ═══════════════════════════════════════════════════

USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"


def gateway_headers(user_id=USER_ID, email="test@parksmart.com"):
    return {
        "HTTP_X_GATEWAY_SECRET": os.environ.get("GATEWAY_SECRET", "test-secret-for-ci"),
        "HTTP_X_USER_ID": str(user_id),
        "HTTP_X_USER_EMAIL": email,
    }


def create_vehicle(user_id=USER_ID, **kwargs):
    defaults = {
        "user_id": uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        "license_plate": f"51A-{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:2]}",
        "vehicle_type": "Car",
        "brand": "Toyota",
        "model": "Camry",
        "color": "White",
        "is_default": False,
    }
    defaults.update(kwargs)
    return Vehicle.objects.create(**defaults)


# ═══════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════


class TestVehicleModel(TestCase):
    def test_create_vehicle(self):
        v = create_vehicle(license_plate="51A-123.45")
        assert isinstance(v.id, uuid.UUID)
        assert v.license_plate == "51A-123.45"
        assert v.vehicle_type == "Car"

    def test_vehicle_type_choices(self):
        car = create_vehicle(vehicle_type="Car", license_plate="51A-001.00")
        moto = create_vehicle(vehicle_type="Motorbike", license_plate="51B-002.00")
        assert car.vehicle_type == "Car"
        assert moto.vehicle_type == "Motorbike"

    def test_license_plate_unique(self):
        create_vehicle(license_plate="51A-999.99")
        with pytest.raises(Exception):
            create_vehicle(license_plate="51A-999.99")

    def test_is_default_default_false(self):
        v = create_vehicle()
        assert v.is_default is False

    def test_vehicle_str(self):
        v = create_vehicle(license_plate="51A-100.00")
        assert str(v) is not None


# ═══════════════════════════════════════════════════
# API TESTS — CRUD
# ═══════════════════════════════════════════════════


class TestVehicleCRUD(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(**gateway_headers(USER_ID))

    def test_list_vehicles(self):
        create_vehicle(user_id=USER_ID, license_plate="51A-010.10")
        response = self.client.get("/vehicles/")
        assert response.status_code == 200

    def test_create_vehicle(self):
        response = self.client.post(
            "/vehicles/",
            {
                "license_plate": "51A-888.88",
                "vehicle_type": "Car",
                "brand": "Honda",
                "model": "Civic",
                "color": "Black",
            },
            format="json",
        )
        assert response.status_code in [201, 200]
        assert Vehicle.objects.filter(license_plate="51A-888.88").exists()

    def test_retrieve_vehicle(self):
        v = create_vehicle(user_id=USER_ID, license_plate="51A-020.20")
        response = self.client.get(f"/vehicles/{v.id}/")
        assert response.status_code == 200
        data = response.json()
        assert (
            data.get("license_plate") == "51A-020.20"
            or data.get("licensePlate") == "51A-020.20"
        )

    def test_update_vehicle(self):
        v = create_vehicle(user_id=USER_ID, license_plate="51A-030.30")
        response = self.client.patch(
            f"/vehicles/{v.id}/",
            {
                "color": "Red",
            },
            format="json",
        )
        assert response.status_code == 200
        v.refresh_from_db()
        assert v.color == "Red"

    def test_delete_vehicle(self):
        v = create_vehicle(user_id=USER_ID, license_plate="51A-040.40")
        response = self.client.delete(f"/vehicles/{v.id}/")
        assert response.status_code in [204, 200]
        assert not Vehicle.objects.filter(id=v.id).exists()

    def test_create_duplicate_plate_fails(self):
        create_vehicle(user_id=USER_ID, license_plate="51A-050.50")
        response = self.client.post(
            "/vehicles/",
            {
                "license_plate": "51A-050.50",
                "vehicle_type": "Car",
            },
            format="json",
        )
        assert response.status_code == 400


# ═══════════════════════════════════════════════════
# SET DEFAULT TESTS
# ═══════════════════════════════════════════════════


class TestSetDefaultVehicle(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(**gateway_headers(USER_ID))

    def test_set_default(self):
        v1 = create_vehicle(
            user_id=USER_ID, license_plate="51A-060.60", is_default=True
        )
        v2 = create_vehicle(
            user_id=USER_ID, license_plate="51A-070.70", is_default=False
        )
        response = self.client.post(f"/vehicles/{v2.id}/set-default/")
        assert response.status_code == 200
        v2.refresh_from_db()
        assert v2.is_default is True
        v1.refresh_from_db()
        assert v1.is_default is False


# ═══════════════════════════════════════════════════
# USER ISOLATION TESTS
# ═══════════════════════════════════════════════════


class TestUserIsolation(TestCase):
    def test_cannot_see_other_users_vehicles(self):
        create_vehicle(user_id=OTHER_USER_ID, license_plate="51A-080.80")
        client = APIClient()
        client.credentials(**gateway_headers(USER_ID))
        response = client.get("/vehicles/")
        data = response.json()
        results = data if isinstance(data, list) else data.get("results", [])
        plates = (
            [v.get("license_plate") for v in results]
            if isinstance(results, list)
            else []
        )
        assert "51A-080.80" not in plates

    def test_cannot_access_other_users_vehicle(self):
        v = create_vehicle(user_id=OTHER_USER_ID, license_plate="51A-090.90")
        client = APIClient()
        client.credentials(**gateway_headers(USER_ID))
        response = client.get(f"/vehicles/{v.id}/")
        assert response.status_code in [403, 404]
