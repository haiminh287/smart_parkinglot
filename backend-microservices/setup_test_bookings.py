"""
Setup: create 4 test bookings in booking-service DB for scenario tests.
Run: docker exec booking-service python3 /tmp/setup_test_bookings.py
"""
import django, os, json, uuid
os.environ["DJANGO_SETTINGS_MODULE"] = "booking_service.settings"
django.setup()

from bookings.models import Booking
from django.utils import timezone
from datetime import timedelta

UID    = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
VID1   = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01")
VID2   = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb02")
LOT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccc01")
ZONE_ID= uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddd01")

now   = timezone.now()
start = now - timedelta(hours=2)
end   = start + timedelta(hours=4)

COMMON = dict(
    user_id=UID, user_email="test-plate@parksmart.test",
    parking_lot_id=LOT_ID, parking_lot_name="ParkSmart Test Lot",
    zone_id=ZONE_ID, zone_name="Zone A",
    vehicle_type="Car", package_type="hourly",
    start_time=start, end_time=end,
    price=50000, payment_status="completed", payment_method="online",
    check_in_status="not_checked_in",
)

# Remove previous test bookings
deleted, _ = Booking.objects.filter(user_id=UID).delete()
print(f"Cleaned up {deleted} previous test booking(s)")

# A: exact target plate
bA = Booking.objects.create(vehicle_id=VID1, vehicle_license_plate="80A-339.39", **COMMON)
# B: completely wrong plate
bB = Booking.objects.create(vehicle_id=VID2, vehicle_license_plate="27A-123.45", **COMMON)
# C: no-separator variant (normalizes to same as 80A-339.39)
bC = Booking.objects.create(vehicle_id=VID1, vehicle_license_plate="80A33939",   **COMMON)
# D: for full checkout flow
bD = Booking.objects.create(vehicle_id=VID1, vehicle_license_plate="80A-339.39", **COMMON)

ids = {"A": str(bA.id), "B": str(bB.id), "C": str(bC.id), "D": str(bD.id)}
print()
print("Created bookings:")
print(f"  A (correct plate 80A-339.39):       {bA.id}")
print(f"  B (wrong plate 27A-123.45):         {bB.id}")
print(f"  C (no-sep 80A33939):                {bC.id}")
print(f"  D (checkout flow 80A-339.39):       {bD.id}")
print(f"  User ID: {UID}")

with open("/tmp/test_booking_ids.json", "w") as f:
    json.dump(ids, f)
print()
print("IDs saved to /tmp/test_booking_ids.json")
