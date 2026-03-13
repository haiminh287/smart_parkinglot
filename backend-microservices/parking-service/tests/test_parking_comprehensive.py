"""
Comprehensive tests for parking-service.
Tests: ParkingLot, Floor, Zone, CarSlot, Camera models and ViewSet CRUD.
"""

import uuid
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from infrastructure.models import ParkingLot, Floor, Zone, CarSlot, Camera


# ═══════════════════════════════════════════════════
# FIXTURE HELPERS
# ═══════════════════════════════════════════════════

def gateway_headers():
    return {
        "HTTP_X_GATEWAY_SECRET": "gateway-internal-secret-key",
        "HTTP_X_USER_ID": "00000000-0000-0000-0000-000000000001",
        "HTTP_X_USER_EMAIL": "admin@parksmart.com",
    }


def create_lot(**kwargs):
    defaults = {
        "name": "ParkSmart Central",
        "address": "123 Nguyen Hue, HCMC",
        "latitude": 10.7769,
        "longitude": 106.7009,
        "total_slots": 200,
        "is_open": True,
    }
    defaults.update(kwargs)
    return ParkingLot.objects.create(**defaults)


def create_floor(lot=None, **kwargs):
    if lot is None:
        lot = create_lot()
    defaults = {"parking_lot": lot, "name": "Floor 1", "level": 1}
    defaults.update(kwargs)
    return Floor.objects.create(**defaults)


def create_zone(floor=None, **kwargs):
    if floor is None:
        floor = create_floor()
    defaults = {
        "floor": floor,
        "name": "Zone A",
        "vehicle_type": "Car",
        "capacity": 50,
    }
    defaults.update(kwargs)
    return Zone.objects.create(**defaults)


def create_slot(zone=None, **kwargs):
    if zone is None:
        zone = create_zone()
    defaults = {
        "zone": zone,
        "code": f"A-{uuid.uuid4().hex[:4]}",
        "status": "available",
    }
    defaults.update(kwargs)
    return CarSlot.objects.create(**defaults)


def create_camera(zone=None, **kwargs):
    if zone is None:
        zone = create_zone()
    defaults = {
        "name": "Camera A1",
        "ip_address": "192.168.1.100",
        "port": 554,
        "zone": zone,
        "stream_url": "rtsp://admin:pass@192.168.1.100:554/ch1/main",
        "is_active": True,
    }
    defaults.update(kwargs)
    return Camera.objects.create(**defaults)


# ═══════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════

class TestParkingLotModel(TestCase):
    def test_create_lot(self):
        lot = create_lot()
        assert isinstance(lot.id, uuid.UUID)
        assert lot.name == "ParkSmart Central"
        assert lot.is_open is True

    def test_lot_str(self):
        lot = create_lot()
        assert str(lot) is not None

    def test_lot_capacity(self):
        lot = create_lot(total_slots=500)
        assert lot.total_slots == 500


class TestFloorModel(TestCase):
    def test_create_floor(self):
        lot = create_lot()
        floor = create_floor(lot, name="B2", level=-2)
        assert floor.name == "B2"
        assert floor.level == -2
        assert floor.parking_lot == lot

    def test_floor_lot_relationship(self):
        lot = create_lot()
        f1 = create_floor(lot, name="F1", level=1)
        f2 = create_floor(lot, name="F2", level=2)
        assert lot.floors.count() == 2


class TestZoneModel(TestCase):
    def test_create_zone(self):
        zone = create_zone(name="Zone B", vehicle_type="Motorbike", capacity=100)
        assert zone.name == "Zone B"
        assert zone.vehicle_type == "Motorbike"
        assert zone.capacity == 100

    def test_zone_floor_relationship(self):
        floor = create_floor()
        z1 = create_zone(floor, name="Z1")
        z2 = create_zone(floor, name="Z2")
        assert floor.zones.count() == 2


class TestCarSlotModel(TestCase):
    def test_create_slot(self):
        slot = create_slot(code="A-01")
        assert slot.code == "A-01"
        assert slot.status == "available"

    def test_slot_status_choices(self):
        for s in ["available", "occupied", "reserved", "maintenance"]:
            slot = create_slot(status=s)
            assert slot.status == s

    def test_slot_bounding_box(self):
        slot = create_slot(x1=10, y1=20, x2=100, y2=80)
        assert slot.x1 == 10
        assert slot.x2 == 100

    def test_slot_with_camera(self):
        zone = create_zone()
        camera = create_camera(zone)
        slot = create_slot(zone, camera=camera)
        assert slot.camera == camera


class TestCameraModel(TestCase):
    def test_create_camera(self):
        camera = create_camera()
        assert camera.is_active is True
        assert "rtsp" in camera.stream_url

    def test_camera_zone_relationship(self):
        zone = create_zone()
        c1 = create_camera(zone, name="Cam1", ip_address="192.168.1.101")
        c2 = create_camera(zone, name="Cam2", ip_address="192.168.1.102")
        assert zone.cameras.count() == 2


# ═══════════════════════════════════════════════════
# API TESTS — PARKING LOT
# ═══════════════════════════════════════════════════

class TestParkingLotAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(**gateway_headers())

    def test_list_lots(self):
        create_lot(name="Lot A")
        create_lot(name="Lot B")
        response = self.client.get("/parking/lots/")
        assert response.status_code == 200

    def test_create_lot(self):
        response = self.client.post("/parking/lots/", {
            "name": "New Lot",
            "address": "456 Le Loi",
            "latitude": 10.78,
            "longitude": 106.70,
            "total_slots": 100,
            "is_open": True,
        }, format="json")
        assert response.status_code in [201, 200]

    def test_retrieve_lot(self):
        lot = create_lot()
        response = self.client.get(f"/parking/lots/{lot.id}/")
        assert response.status_code == 200
        assert response.json()["name"] == "ParkSmart Central"

    def test_update_lot(self):
        lot = create_lot()
        response = self.client.patch(f"/parking/lots/{lot.id}/", {
            "name": "Updated Lot",
        }, format="json")
        assert response.status_code == 200
        lot.refresh_from_db()
        assert lot.name == "Updated Lot"

    def test_delete_lot(self):
        lot = create_lot()
        response = self.client.delete(f"/parking/lots/{lot.id}/")
        assert response.status_code in [204, 200]


# ═══════════════════════════════════════════════════
# API TESTS — FLOOR
# ═══════════════════════════════════════════════════

class TestFloorAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(**gateway_headers())
        self.lot = create_lot()

    def test_list_floors(self):
        create_floor(self.lot, name="F1", level=1)
        response = self.client.get("/parking/floors/")
        assert response.status_code == 200

    def test_create_floor(self):
        response = self.client.post("/parking/floors/", {
            "parking_lot": str(self.lot.id),
            "name": "F3",
            "level": 3,
        }, format="json")
        assert response.status_code in [201, 200]


# ═══════════════════════════════════════════════════
# API TESTS — ZONE
# ═══════════════════════════════════════════════════

class TestZoneAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(**gateway_headers())
        self.floor = create_floor()

    def test_list_zones(self):
        create_zone(self.floor, name="Zone X")
        response = self.client.get("/parking/zones/")
        assert response.status_code == 200

    def test_create_zone(self):
        response = self.client.post("/parking/zones/", {
            "floor": str(self.floor.id),
            "name": "Zone Y",
            "vehicle_type": "Motorbike",
            "capacity": 30,
        }, format="json")
        assert response.status_code in [201, 200]


# ═══════════════════════════════════════════════════
# API TESTS — CAR SLOT
# ═══════════════════════════════════════════════════

class TestCarSlotAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(**gateway_headers())
        self.zone = create_zone()

    def test_list_slots(self):
        create_slot(self.zone, code="B-01")
        response = self.client.get("/parking/slots/")
        assert response.status_code == 200

    def test_create_slot(self):
        response = self.client.post("/parking/slots/", {
            "zone": str(self.zone.id),
            "code": "B-99",
            "status": "available",
        }, format="json")
        assert response.status_code in [201, 200]

    def test_update_slot_status(self):
        slot = create_slot(self.zone, code="B-02")
        response = self.client.patch(f"/parking/slots/{slot.id}/", {
            "status": "maintenance",
        }, format="json")
        assert response.status_code == 200
        slot.refresh_from_db()
        assert slot.status == "maintenance"


# ═══════════════════════════════════════════════════
# API TESTS — CAMERA
# ═══════════════════════════════════════════════════

class TestCameraAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(**gateway_headers())
        self.zone = create_zone()

    def test_list_cameras(self):
        create_camera(self.zone)
        response = self.client.get("/parking/cameras/")
        assert response.status_code == 200

    def test_create_camera(self):
        response = self.client.post("/parking/cameras/", {
            "name": "Entrance Cam",
            "ip_address": "192.168.1.200",
            "port": 554,
            "zone": str(self.zone.id),
            "stream_url": "rtsp://admin:pass@192.168.1.200:554",
            "is_active": True,
        }, format="json")
        assert response.status_code in [201, 200]

    def test_deactivate_camera(self):
        camera = create_camera(self.zone)
        response = self.client.patch(f"/parking/cameras/{camera.id}/", {
            "is_active": False,
        }, format="json")
        assert response.status_code == 200
        camera.refresh_from_db()
        assert camera.is_active is False
