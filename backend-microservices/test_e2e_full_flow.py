#!/usr/bin/env python3
"""
ParkSmart Full E2E Test — Complete Parking Flow
=================================================
Tests the entire user journey:
  1. Register & Login
  2. Register vehicle (plate: 51A-224.56)
  3. Find nearest parking lot
  4. View package pricing (hourly/daily/weekly/monthly)
  5. Create booking — online payment → auto success
  6. Create booking — pay at lot (on_exit)
  7. Test pricing for all packages
  8. Process payment (online booking)
  9. AI scan plate from image
 10. Check-in: QR + matching plate → SUCCESS
 11. Check-in: QR + wrong plate → REJECTED
 12. Check-out after check-in (with AI plate match)
 13. Scan second plate image

Run with: python test_e2e_full_flow.py
"""

import json
import os
import re
import sys
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Optional

import requests

# ─── Service URLs (local, no Docker) ───────────────────────────────────
AUTH_URL     = "http://localhost:8001"
PARKING_URL  = "http://localhost:8002"
VEHICLE_URL  = "http://localhost:8003"
BOOKING_URL  = "http://localhost:8004"
PAYMENT_URL  = "http://localhost:8007"
AI_URL       = "http://localhost:8009"

GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET")
if not GATEWAY_SECRET:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET")
    if not GATEWAY_SECRET:
        raise RuntimeError("GATEWAY_SECRET env var required. Set it or create .env")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "ai-service-fastapi", "app", "images")

# Test data
TEST_EMAIL    = f"e2etest_{uuid.uuid4().hex[:6]}@parksmart.com"
TEST_USERNAME = f"e2etest_{uuid.uuid4().hex[:6]}"
TEST_PASSWORD = "TestPass123!"
TEST_PLATE    = "51A-224.56"   # matches the test image
WRONG_PLATE_IMG = "30E-922.91.jpg"  # second image in images/
RIGHT_PLATE_IMG = "51A-224.56.jpg"  # correct plate image

# Camera RTSP (for future use — test with static images for now)
CAMERA_RTSP = "rtsp://user:password@192.168.1.100:554/H264/ch1/sub/av_stream"


class Colors:
    OK    = "\033[92m"
    FAIL  = "\033[91m"
    WARN  = "\033[93m"
    INFO  = "\033[94m"
    BOLD  = "\033[1m"
    END   = "\033[0m"


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    c = {"INFO": Colors.INFO, "OK": Colors.OK, "FAIL": Colors.FAIL, "WARN": Colors.WARN}
    prefix = c.get(level, Colors.INFO)
    print(f"{prefix}[{ts}] [{level:4s}]{Colors.END} {msg}")


def header(title):
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}{Colors.END}\n")


def gw_headers(user_id: str, email: str = ""):
    """Simulate gateway-injected headers for direct service calls."""
    return {
        "X-Gateway-Secret": GATEWAY_SECRET,
        "X-User-ID": user_id,
        "X-User-Email": email,
        "Content-Type": "application/json",
    }


def gw_headers_form(user_id: str, email: str = ""):
    """Gateway headers without Content-Type (for multipart)."""
    return {
        "X-Gateway-Secret": GATEWAY_SECRET,
        "X-User-ID": user_id,
        "X-User-Email": email,
    }


def _get_results(data):
    """Extract results list from DRF paginated or plain list response."""
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []


def _norm_plate(text):
    """Normalize plate text for comparison."""
    return re.sub(r'[\s.\-]', '', text.upper())


passed = 0
failed = 0
total  = 0


def check(condition, desc, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        log(f"✅ PASS: {desc}", "OK")
    else:
        failed += 1
        log(f"❌ FAIL: {desc} — {detail}", "FAIL")
    return condition


# ═══════════════════════════════════════════════════════════════════════
#  TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_health_checks():
    header("STEP 0: Health Checks — All Services")
    services = {
        "auth":    f"{AUTH_URL}/health/",
        "parking": f"{PARKING_URL}/health/",
        "vehicle": f"{VEHICLE_URL}/health/",
        "booking": f"{BOOKING_URL}/health/",
        "payment": f"{PAYMENT_URL}/health/",
        "ai":      f"{AI_URL}/health/",
    }
    all_ok = True
    for name, url in services.items():
        try:
            r = requests.get(url, timeout=5)
            ok = check(r.status_code == 200, f"{name}-service health", f"status={r.status_code}")
            if not ok:
                all_ok = False
        except Exception as e:
            check(False, f"{name}-service health", str(e))
            all_ok = False
    if not all_ok:
        log("⚠️  Some services are DOWN — test may fail!", "WARN")


def test_register_login():
    header("STEP 1: Register & Login User")

    # Register
    log(f"Registering user: {TEST_EMAIL}")
    r = requests.post(f"{AUTH_URL}/auth/register/", json={
        "email": TEST_EMAIL,
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
    })
    log(f"  Register response: {r.status_code} {r.text[:300]}")
    check(r.status_code == 201, "User registration", f"status={r.status_code}")

    data = r.json()
    user_id = data.get("user", {}).get("id", "")
    check(bool(user_id), "User ID returned", f"id={user_id}")

    # Login
    log(f"Logging in as: {TEST_EMAIL}")
    r = requests.post(f"{AUTH_URL}/auth/login/", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    log(f"  Login response: {r.status_code}")
    check(r.status_code == 200, "User login", f"status={r.status_code}")

    login_data = r.json()
    user_id = login_data.get("user", {}).get("id", user_id)
    log(f"  User ID: {user_id}")
    log(f"  Email:   {login_data.get('user', {}).get('email')}")
    log(f"  Role:    {login_data.get('user', {}).get('role')}")

    return user_id


def test_register_vehicle(user_id):
    header("STEP 2: Register Vehicle")

    # Clean up stale vehicle record from previous test runs (different user_id)
    try:
        import pymysql
        _conn = pymysql.connect(host="127.0.0.1", port=3307, user="parksmartuser",
                                password="parksmartpass", database="parksmartdb")
        _cur = _conn.cursor()
        _cur.execute("DELETE FROM vehicle WHERE license_plate = %s AND user_id != %s",
                     (TEST_PLATE, user_id))
        if _cur.rowcount > 0:
            log(f"  Cleaned up stale vehicle for plate {TEST_PLATE} (prev test run)", "WARN")
        _conn.commit()
        _conn.close()
    except Exception as e:
        log(f"  DB cleanup skipped: {e}", "WARN")

    # CamelCaseJSONParser will convert camelCase → snake_case
    log(f"Registering vehicle: plate={TEST_PLATE}, type=Car")
    r = requests.post(f"{VEHICLE_URL}/vehicles/", json={
        "licensePlate": TEST_PLATE,
        "vehicleType": "Car",
        "brand": "Toyota",
        "model": "Vios",
        "color": "White",
        "isDefault": True,
    }, headers=gw_headers(user_id, TEST_EMAIL))

    log(f"  Response: {r.status_code} {r.text[:300]}")

    if r.status_code == 201:
        check(True, "Vehicle registered (new)")
        vdata = r.json()
        vehicle_id = vdata.get("id", "")
    elif r.status_code == 400 and "already exists" in r.text:
        # Plate already registered — look it up from the vehicle list
        log("  Plate already exists — looking up existing vehicle...", "WARN")
        r2 = requests.get(f"{VEHICLE_URL}/vehicles/",
                          headers=gw_headers(user_id, TEST_EMAIL))
        vehicles = _get_results(r2.json())
        vehicle_id = ""
        for v in vehicles:
            if _norm_plate(v.get("licensePlate", "")) == _norm_plate(TEST_PLATE):
                vehicle_id = v.get("id", "")
                break
        if not vehicle_id and vehicles:
            # If current user has no vehicles (plate owned by another user),
            # use a unique plate derived from test email
            unique_plate = f"51E-{uuid.uuid4().hex[:3].upper()}.{uuid.uuid4().hex[:2].upper()}"
            log(f"  Plate owned by another user. Registering new plate: {unique_plate}", "WARN")
            r3 = requests.post(f"{VEHICLE_URL}/vehicles/", json={
                "licensePlate": unique_plate,
                "vehicleType": "Car",
                "brand": "Toyota",
                "model": "Vios",
                "color": "White",
                "isDefault": True,
            }, headers=gw_headers(user_id, TEST_EMAIL))
            if r3.status_code == 201:
                vehicle_id = r3.json().get("id", "")
                log(f"  Registered alternative vehicle: {unique_plate} (id={vehicle_id})")
                # NOTE: plate won't match the image, but we can still test booking flow
            else:
                log(f"  Alternative registration failed: {r3.status_code}", "FAIL")
        check(bool(vehicle_id), "Vehicle found/registered", f"id={vehicle_id}")
    else:
        check(False, "Vehicle registered", f"status={r.status_code}")
        return ""

    log(f"  Vehicle ID: {vehicle_id}")
    return vehicle_id


def test_find_parking(user_id):
    header("STEP 3: Find Nearest Parking Lot")

    # List all lots
    r = requests.get(f"{PARKING_URL}/parking/lots/",
                     headers=gw_headers(user_id, TEST_EMAIL))
    log(f"  All lots: {r.status_code}")
    lots_list = _get_results(r.json())

    check(len(lots_list) > 0, "Parking lots found", f"count={len(lots_list)}")

    for lot in lots_list:
        log(f"  📍 {lot.get('name', lot.get('id','?'))}")
        log(f"     Address:   {lot.get('address')}")
        log(f"     Slots:     {lot.get('availableSlots', '?')}/{lot.get('totalSlots', '?')}")
        log(f"     Price/hr:  {lot.get('pricePerHour', '?')} VND")
        log(f"     Open:      {lot.get('isOpen')}")

    # Pick first lot
    lot = lots_list[0]
    lot_id = lot.get("id")
    log(f"\n  Selected lot: {lot.get('name')} (id={lot_id})")

    # Get zones for Car in this lot
    r = requests.get(f"{PARKING_URL}/parking/zones/",
                     params={"lot_id": lot_id, "vehicle_type": "Car"},
                     headers=gw_headers(user_id, TEST_EMAIL))
    zones = _get_results(r.json())

    car_zones = [z for z in zones if z.get("availableSlots", 0) > 0]
    check(len(car_zones) > 0, "Available Car zones found", f"count={len(car_zones)}")

    for z in car_zones[:3]:
        log(f"  🅿️  Zone {z.get('name')}: {z.get('availableSlots')}/{z.get('capacity')} available")

    zone = car_zones[0]
    zone_id = zone.get("id")
    floor_id = zone.get("floorId")
    log(f"\n  Selected zone: {zone.get('name')} (id={zone_id})")

    # Get available slot — filter by zone_id (parking view uses zone_id param)
    r = requests.get(f"{PARKING_URL}/parking/slots/",
                     params={"zone_id": zone_id, "status": "available"},
                     headers=gw_headers(user_id, TEST_EMAIL))
    slots = _get_results(r.json())

    check(len(slots) > 0, "Available slots in zone", f"count={len(slots)}")
    slot = slots[0]
    slot_id = slot.get("id")
    log(f"  Selected slot: {slot.get('code')} (id={slot_id})")

    return lot_id, zone_id, floor_id, slot_id


def test_package_pricing(user_id):
    header("STEP 4: View Package Pricing")

    # Booking service uses /bookings/packagepricings/
    r = requests.get(f"{BOOKING_URL}/bookings/packagepricings/",
                     headers=gw_headers(user_id, TEST_EMAIL))
    log(f"  Pricing response: {r.status_code}")
    pricing = _get_results(r.json())

    check(len(pricing) > 0, "Package pricing available", f"count={len(pricing)}")

    log(f"\n  {'Package':<10s} {'Vehicle':<12s} {'Price':>12s}")
    log(f"  {'-'*10} {'-'*12} {'-'*12}")
    for p in pricing:
        pkg = p.get("packageType", p.get("package_type", "?"))
        vtype = p.get("vehicleType", p.get("vehicle_type", "?"))
        price = p.get("price", "?")
        log(f"  {pkg:<10s} {vtype:<12s} {str(price)+' VND':>12s}")

    return pricing


def test_create_booking_online(user_id, vehicle_id, lot_id, zone_id, floor_id, slot_id):
    header("STEP 5: Create Booking — ONLINE Payment")

    # Booking serializer uses snake_case fields with CamelCaseJSONParser
    start_time = (datetime.now() + timedelta(minutes=5)).isoformat()
    end_time   = (datetime.now() + timedelta(hours=2, minutes=5)).isoformat()

    booking_data = {
        "vehicle_id": vehicle_id,
        "parking_lot_id": lot_id,
        "zone_id": zone_id,
        "slot_id": slot_id,
        "start_time": start_time,
        "end_time": end_time,
        "package_type": "hourly",
        "payment_method": "online",
    }
    log(f"  Creating booking: plate={TEST_PLATE}, package=hourly, payment=online")
    log(f"  Start: {start_time}")
    log(f"  End:   {end_time}")

    r = requests.post(f"{BOOKING_URL}/bookings/",
                      json=booking_data,
                      headers=gw_headers(user_id, TEST_EMAIL))
    log(f"  Response: {r.status_code}")
    log(f"  Body: {r.text[:600]}")

    check(r.status_code == 201, "Online booking created", f"status={r.status_code}")

    raw = r.json()
    # Response may be nested: {"booking": {...}} or flat {...}
    bdata = raw.get("booking", raw) if isinstance(raw, dict) else raw
    booking_id = bdata.get("id", "")
    price = bdata.get("price", "?")
    # Response uses CamelCaseJSONRenderer → camelCase keys
    payment_status = bdata.get("paymentStatus", "?")
    checkin_status = bdata.get("checkInStatus", "?")
    qr_data = bdata.get("qrCodeData", "")

    log(f"  Booking ID:      {booking_id}")
    log(f"  Price:           {price} VND")
    log(f"  Payment Status:  {payment_status}")
    log(f"  Check-in Status: {checkin_status}")
    log(f"  QR Data:         {qr_data[:120]}...")

    check(payment_status in ["pending", "processing"], "Payment status is pending/processing",
          f"got={payment_status}")
    check(checkin_status == "not_checked_in", "Check-in status is not_checked_in",
          f"got={checkin_status}")

    return booking_id, qr_data


def test_create_booking_on_exit(user_id, vehicle_id, lot_id, zone_id, floor_id):
    header("STEP 6: Create Booking — PAY AT LOT (on_exit)")

    # Get available slot
    r = requests.get(f"{PARKING_URL}/parking/slots/",
                     params={"zone_id": zone_id, "status": "available"},
                     headers=gw_headers(user_id, TEST_EMAIL))
    slots = _get_results(r.json())

    if len(slots) < 1:
        log("  No available slots for second booking!", "WARN")
        return None, None

    slot2 = slots[0]
    slot2_id = slot2.get("id")

    # Start time = now (so we can check-in immediately)
    start_time = datetime.now().isoformat()
    end_time   = (datetime.now() + timedelta(hours=3)).isoformat()

    booking_data = {
        "vehicle_id": vehicle_id,
        "parking_lot_id": lot_id,
        "zone_id": zone_id,
        "slot_id": slot2_id,
        "start_time": start_time,
        "end_time": end_time,
        "package_type": "hourly",
        "payment_method": "on_exit",
    }
    log(f"  Creating booking: plate={TEST_PLATE}, package=hourly, payment=on_exit")
    log(f"  Slot: {slot2.get('code')} (id={slot2_id})")
    log(f"  Start: {start_time} (NOW — for immediate check-in)")

    r = requests.post(f"{BOOKING_URL}/bookings/",
                      json=booking_data,
                      headers=gw_headers(user_id, TEST_EMAIL))
    log(f"  Response: {r.status_code}")
    log(f"  Body: {r.text[:600]}")

    check(r.status_code == 201, "On-exit booking created", f"status={r.status_code}")

    raw = r.json()
    bdata = raw.get("booking", raw) if isinstance(raw, dict) else raw
    booking_id = bdata.get("id", "")
    price = bdata.get("price", "?")
    payment_status = bdata.get("paymentStatus", "?")
    qr_data = bdata.get("qrCodeData", "")

    log(f"  Booking ID:      {booking_id}")
    log(f"  Price:           {price} VND (will be recalculated at checkout)")
    log(f"  Payment Status:  {payment_status}")
    log(f"  QR Data:         {qr_data[:120]}...")

    return booking_id, qr_data


def test_pricing_packages(user_id, vehicle_id, lot_id, zone_id):
    header("STEP 7: Test Price Calculation — All Packages")

    packages = [
        ("hourly",  2),   # 2 hours
        ("daily",   1),
        ("weekly",  1),
        ("monthly", 1),
    ]

    for pkg_type, duration in packages:
        # Get an available slot
        r = requests.get(f"{PARKING_URL}/parking/slots/",
                         params={"zone_id": zone_id, "status": "available"},
                         headers=gw_headers(user_id, TEST_EMAIL))
        slots = _get_results(r.json())

        if not slots:
            log(f"  No slots for {pkg_type} test", "WARN")
            continue

        slot_id = slots[0].get("id")
        start = (datetime.now() + timedelta(hours=6)).isoformat()
        if pkg_type == "hourly":
            end = (datetime.now() + timedelta(hours=6 + duration)).isoformat()
        elif pkg_type == "daily":
            end = (datetime.now() + timedelta(days=1, hours=6)).isoformat()
        elif pkg_type == "weekly":
            end = (datetime.now() + timedelta(weeks=1, hours=6)).isoformat()
        else:
            end = (datetime.now() + timedelta(days=30, hours=6)).isoformat()

        r = requests.post(f"{BOOKING_URL}/bookings/", json={
            "vehicle_id": vehicle_id,
            "parking_lot_id": lot_id,
            "zone_id": zone_id,
            "slot_id": slot_id,
            "start_time": start,
            "end_time": end,
            "package_type": pkg_type,
            "payment_method": "on_exit",
        }, headers=gw_headers(user_id, TEST_EMAIL))

        if r.status_code == 201:
            raw = r.json()
            bdata = raw.get("booking", raw) if isinstance(raw, dict) else raw
            price = bdata.get("price", "?")
            bid = bdata.get("id", "")
            log(f"  💰 {pkg_type:<10s} → {price} VND  (booking={bid[:8]}...)")
            check(True, f"Price calc: {pkg_type}", f"price={price}")
            # Cancel it so slot is freed
            requests.post(f"{BOOKING_URL}/bookings/{bid}/cancel/",
                          headers=gw_headers(user_id, TEST_EMAIL))
        else:
            log(f"  {pkg_type}: {r.status_code} {r.text[:300]}", "WARN")
            check(False, f"Price calc: {pkg_type}", f"status={r.status_code}")


def test_payment_online(user_id, booking_id):
    header("STEP 8: Process Online Payment")

    # Initiate payment (CamelModel accepts camelCase via alias_generator)
    log(f"  Initiating payment for booking: {booking_id}")
    r = requests.post(f"{PAYMENT_URL}/api/payments/initiate/", json={
        "bookingId": booking_id,
        "paymentMethod": "momo",
        "amount": 30000,
    }, headers=gw_headers(user_id, TEST_EMAIL))

    log(f"  Initiate response: {r.status_code}")
    log(f"  Body: {r.text[:500]}")

    if r.status_code in [200, 201]:
        pdata = r.json()
        payment_id = pdata.get("id", "")
        tx_id = pdata.get("transactionId", "")
        status = pdata.get("status", "")
        payment_url = pdata.get("paymentUrl", "")
        log(f"  Payment ID:      {payment_id}")
        log(f"  Transaction ID:  {tx_id}")
        log(f"  Status:          {status}")
        log(f"  Payment URL:     {payment_url}")

        check(True, "Payment initiated", f"status={status}")

        # Verify/confirm payment — POST /api/payments/verify/{payment_id}/
        log(f"  Verifying payment: payment_id={payment_id}")
        r2 = requests.post(f"{PAYMENT_URL}/api/payments/verify/{payment_id}/", json={
            "transactionId": tx_id,
            "gatewayResponse": {"status": "success", "message": "Payment completed"},
        }, headers=gw_headers(user_id, TEST_EMAIL))

        log(f"  Verify response: {r2.status_code}")
        log(f"  Body: {r2.text[:400]}")

        if r2.status_code == 200:
            vdata = r2.json()
            check(vdata.get("status") == "completed", "Payment completed",
                  f"status={vdata.get('status')}")
        else:
            check(False, "Payment verify", f"status={r2.status_code}")

        return payment_id
    else:
        check(False, "Payment initiation", f"status={r.status_code} {r.text[:300]}")
        return None


def test_ai_scan_plate(image_file, expected_plate=None):
    header(f"AI Scan Plate — {image_file}")

    img_path = os.path.join(IMAGES_DIR, image_file)
    if not os.path.exists(img_path):
        check(False, f"Image exists: {image_file}", f"path={img_path}")
        return None

    log(f"  Scanning image: {img_path}")
    with open(img_path, "rb") as f:
        r = requests.post(f"{AI_URL}/ai/parking/scan-plate/",
                          files={"image": (image_file, f, "image/jpeg")},
                          headers=gw_headers_form("system-test"))

    log(f"  Response: {r.status_code}")
    try:
        log(f"  Body: {json.dumps(r.json(), indent=2, ensure_ascii=False)[:600]}")
    except:
        log(f"  Body: {r.text[:500]}")

    if r.status_code == 200:
        result = r.json()
        plate_text = result.get("plate_text", "")
        decision = result.get("decision", "")
        confidence = result.get("confidence", 0)
        method = result.get("ocr_method", "")
        proc_time = result.get("processing_time_ms", 0)

        log(f"  🔍 Plate Text:   {plate_text}")
        log(f"  📊 Decision:     {decision}")
        log(f"  🎯 Confidence:   {confidence:.1%}")
        log(f"  🔧 OCR Method:   {method}")
        log(f"  ⏱️  Process Time: {proc_time:.0f}ms")

        if expected_plate:
            match = _norm_plate(plate_text) == _norm_plate(expected_plate)
            check(match, f"Plate matches expected '{expected_plate}'",
                  f"got='{plate_text}'")

        check(decision == "success", "Scan decision is success", f"got={decision}")
        return plate_text
    else:
        check(False, "AI scan plate", f"status={r.status_code}")
        return None


def test_checkin_matching(user_id, booking_id, qr_data):
    header("STEP 10: Check-in — MATCHING Plate (should SUCCEED)")

    img_path = os.path.join(IMAGES_DIR, RIGHT_PLATE_IMG)
    log(f"  Booking:    {booking_id}")
    log(f"  Plate img:  {RIGHT_PLATE_IMG} (expected: {TEST_PLATE})")
    log(f"  QR Data:    {qr_data[:120]}...")

    with open(img_path, "rb") as f:
        r = requests.post(f"{AI_URL}/ai/parking/check-in/",
                          files={"image": (RIGHT_PLATE_IMG, f, "image/jpeg")},
                          data={"qr_data": qr_data},
                          headers=gw_headers_form(user_id, TEST_EMAIL))

    log(f"  Response: {r.status_code}")
    try:
        result = r.json()
        log(f"  Body: {json.dumps(result, indent=2, ensure_ascii=False)[:800]}")
    except:
        log(f"  Body: {r.text[:500]}")
        result = {}

    check(r.status_code == 200, "Check-in API returned 200", f"status={r.status_code}")

    # AI parking router returns: success, plate_match, plate_text, booking_plate
    success = result.get("success", False)
    plate_match = result.get("plate_match", False)
    ocr_plate = result.get("plate_text", "")
    booking_plate = result.get("booking_plate", "")

    log(f"  ✅ Success:         {success}")
    log(f"  🔄 Plate match:     {plate_match}")
    log(f"  🔍 OCR plate:       {ocr_plate}")
    log(f"  📋 Booking plate:   {booking_plate}")

    check(success, "Check-in succeeded with matching plate")
    check(plate_match, "Plate matched booking", f"ocr={ocr_plate} vs booking={booking_plate}")

    # Verify booking status updated
    r2 = requests.get(f"{BOOKING_URL}/bookings/{booking_id}/",
                      headers=gw_headers(user_id, TEST_EMAIL))
    if r2.status_code == 200:
        bdata = r2.json()
        status = bdata.get("checkInStatus", "")
        log(f"  📋 Booking checkInStatus: {status}")
        check(status == "checked_in", "Booking status updated to checked_in", f"got={status}")

    return success


def test_checkin_wrong_plate(user_id, booking_id, qr_data):
    header("STEP 11: Check-in — WRONG Plate (should REJECT)")

    img_path = os.path.join(IMAGES_DIR, WRONG_PLATE_IMG)
    if not os.path.exists(img_path):
        log(f"  ⚠️  Wrong plate image not found: {img_path}", "WARN")
        log(f"  Skipping wrong plate test", "WARN")
        return

    log(f"  Booking:    {booking_id}")
    log(f"  Plate img:  {WRONG_PLATE_IMG} (expected mismatch with {TEST_PLATE})")

    with open(img_path, "rb") as f:
        r = requests.post(f"{AI_URL}/ai/parking/check-in/",
                          files={"image": (WRONG_PLATE_IMG, f, "image/jpeg")},
                          data={"qr_data": qr_data},
                          headers=gw_headers_form(user_id, TEST_EMAIL))

    log(f"  Response: {r.status_code}")
    try:
        result = r.json()
        log(f"  Body: {json.dumps(result, indent=2, ensure_ascii=False)[:800]}")
    except:
        log(f"  Body: {r.text[:500]}")
        result = {}

    detail = result.get("detail", {})
    if isinstance(detail, dict):
        error_type = detail.get("error", "")
        ocr_plate = detail.get("ocr_plate", "")
        booking_plate = detail.get("booking_plate", "")
        log(f"  🔍 Error type:      {error_type}")
        log(f"  🔍 OCR plate:       {ocr_plate}")
        log(f"  📋 Booking plate:   {booking_plate}")
        log(f"  💬 Message:         {detail.get('message', '')[:200]}")
        check(error_type == "plate_mismatch", "Plate mismatch error returned",
              f"error={error_type}")
        check(r.status_code == 400, "HTTP 400 for plate mismatch", f"status={r.status_code}")
    elif isinstance(detail, str):
        log(f"  💬 Detail: {detail[:300]}")
        check(r.status_code in [400, 422], "Rejected with error status",
              f"status={r.status_code}")
    else:
        # Check if it somehow succeeded (shouldn't)
        success = result.get("success", False)
        plate_match = result.get("plate_match", True)
        check(not success or not plate_match,
              "Wrong plate correctly rejected",
              f"success={success}, plate_match={plate_match}")


def test_checkout_via_ai(user_id, booking_id, qr_data):
    header("STEP 12: Check-out via AI (plate scan + booking)")

    img_path = os.path.join(IMAGES_DIR, RIGHT_PLATE_IMG)
    log(f"  Booking:    {booking_id}")
    log(f"  Plate img:  {RIGHT_PLATE_IMG} (should match)")
    log(f"  QR Data:    {qr_data[:120]}...")

    with open(img_path, "rb") as f:
        r = requests.post(f"{AI_URL}/ai/parking/check-out/",
                          files={"image": (RIGHT_PLATE_IMG, f, "image/jpeg")},
                          data={"qr_data": qr_data},
                          headers=gw_headers_form(user_id, TEST_EMAIL))

    log(f"  Response: {r.status_code}")
    try:
        result = r.json()
        log(f"  Body: {json.dumps(result, indent=2, ensure_ascii=False)[:800]}")
    except:
        log(f"  Body: {r.text[:500]}")
        result = {}

    check(r.status_code == 200, "Checkout API returned 200", f"status={r.status_code}")

    success = result.get("success", False)
    plate_match = result.get("plate_match", False)
    raw_booking = result.get("booking", {})
    # Handle nested {"booking": {"booking": {...}}} from checkout response
    booking_data = raw_booking.get("booking", raw_booking) if isinstance(raw_booking, dict) else raw_booking
    check_in_status = booking_data.get("checkInStatus", booking_data.get("check_in_status", ""))
    price = booking_data.get("price", "?")

    log(f"  ✅ Success:         {success}")
    log(f"  🔄 Plate match:     {plate_match}")
    log(f"  📋 Status:          {check_in_status}")
    log(f"  💰 Final Price:     {price} VND")

    check(success, "Check-out succeeded")
    check(plate_match, "Plate matched on checkout")
    check(check_in_status == "checked_out", "Status is checked_out", f"got={check_in_status}")

    return success


def test_checkout_direct(user_id, booking_id):
    header("STEP 12-ALT: Check-out (Direct — booking service)")

    log(f"  Checking out booking: {booking_id}")

    r = requests.post(f"{BOOKING_URL}/bookings/{booking_id}/checkout/",
                      headers=gw_headers(user_id, TEST_EMAIL))

    log(f"  Response: {r.status_code}")
    log(f"  Body: {r.text[:500]}")

    check(r.status_code == 200, "Checkout API succeeded", f"status={r.status_code}")

    if r.status_code == 200:
        result = r.json()
        status = result.get("checkInStatus", "")
        price = result.get("price", "?")
        log(f"  📋 Status:      {status}")
        log(f"  💰 Final Price: {price} VND")
        check(status == "checked_out", "Status is checked_out", f"got={status}")


def test_ai_scan_second_image():
    header("STEP 13: AI Scan — Second Plate Image (30E-922.91)")
    return test_ai_scan_plate(WRONG_PLATE_IMG, expected_plate="30E-922.91")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    header("ParkSmart Full E2E Test Suite")
    log(f"Test Email:    {TEST_EMAIL}")
    log(f"Test Plate:    {TEST_PLATE}")
    log(f"Camera RTSP:   {CAMERA_RTSP} (future use — testing with images)")
    log(f"Images dir:    {IMAGES_DIR}")
    log(f"Available images: {os.listdir(IMAGES_DIR) if os.path.isdir(IMAGES_DIR) else 'NOT FOUND'}")

    t0 = time.time()

    try:
        # Step 0: Health
        test_health_checks()

        # Step 1: Register & Login
        user_id = test_register_login()
        if not user_id:
            log("Cannot continue without user_id", "FAIL")
            return

        # Step 2: Register vehicle
        vehicle_id = test_register_vehicle(user_id)
        if not vehicle_id:
            log("Cannot continue without vehicle_id", "FAIL")
            return

        # Step 3: Find parking
        lot_id, zone_id, floor_id, slot_id = test_find_parking(user_id)

        # Step 4: View pricing
        test_package_pricing(user_id)

        # Step 5: Online booking
        online_booking_id, online_qr = test_create_booking_online(
            user_id, vehicle_id, lot_id, zone_id, floor_id, slot_id)

        # Step 6: On-exit booking (start_time=now for immediate check-in)
        exit_booking_id, exit_qr = test_create_booking_on_exit(
            user_id, vehicle_id, lot_id, zone_id, floor_id)

        # Step 7: Test pricing for all packages
        test_pricing_packages(user_id, vehicle_id, lot_id, zone_id)

        # Step 8: Online payment
        if online_booking_id:
            test_payment_online(user_id, online_booking_id)

        # Step 9: AI scan — right plate
        test_ai_scan_plate(RIGHT_PLATE_IMG, expected_plate=TEST_PLATE)

        # Step 10: Check-in with matching plate (use exit booking — start_time=now)
        if exit_booking_id and exit_qr:
            test_checkin_matching(user_id, exit_booking_id, exit_qr)

            # Step 12: Checkout via AI (plate scan + qr_data)
            test_checkout_via_ai(user_id, exit_booking_id, exit_qr)

        # Step 11: Check-in with wrong plate
        # Create another on_exit booking for the wrong plate test
        r_slots = requests.get(f"{PARKING_URL}/parking/slots/",
                               params={"zone_id": zone_id, "status": "available"},
                               headers=gw_headers(user_id, TEST_EMAIL))
        avail_slots = _get_results(r_slots.json())

        if avail_slots:
            wrong_slot = avail_slots[0]
            start_t = datetime.now().isoformat()
            end_t = (datetime.now() + timedelta(hours=2)).isoformat()
            r_b3 = requests.post(f"{BOOKING_URL}/bookings/", json={
                "vehicle_id": vehicle_id,
                "parking_lot_id": lot_id,
                "zone_id": zone_id,
                "slot_id": wrong_slot.get("id"),
                "start_time": start_t,
                "end_time": end_t,
                "package_type": "hourly",
                "payment_method": "on_exit",
            }, headers=gw_headers(user_id, TEST_EMAIL))
            if r_b3.status_code == 201:
                b3_raw = r_b3.json()
                b3_data = b3_raw.get("booking", b3_raw) if isinstance(b3_raw, dict) else b3_raw
                b3_id = b3_data.get("id")
                b3_qr = b3_data.get("qrCodeData", "")
                test_checkin_wrong_plate(user_id, b3_id, b3_qr)
            else:
                log(f"  Could not create booking for wrong-plate test: {r_b3.status_code} {r_b3.text[:200]}", "WARN")
        else:
            log("  No available slots for wrong-plate test", "WARN")

        # Step 13: AI scan second image
        test_ai_scan_second_image()

    except Exception as e:
        log(f"UNEXPECTED ERROR: {e}", "FAIL")
        traceback.print_exc()

    elapsed = time.time() - t0

    # ─── SUMMARY ───────────────────────────────────────────────────
    header("TEST SUMMARY")
    log(f"Total:   {total}")
    log(f"Passed:  {passed}", "OK")
    if failed:
        log(f"Failed:  {failed}", "FAIL")
    else:
        log(f"Failed:  {failed}", "OK")
    log(f"Time:    {elapsed:.1f}s")
    log(f"Result:  {'ALL PASSED ✅' if failed == 0 else f'{failed} FAILURES ❌'}",
        "OK" if failed == 0 else "FAIL")


if __name__ == "__main__":
    main()
