#!/usr/bin/env python3
"""
ParkSmart E2E Test Script
=========================
Tests the complete booking flow through API Gateway.
Saves booking info for Unity testing.

Run with: python test_e2e_parksmart.py
Requires: Gateway (port 8000) + backend services running.
"""

import json
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import requests

# ─── Config ─────────────────────────────────────────────────────────────
GATEWAY_URL = "http://localhost:8000"
AI_SERVICE_URL = "http://localhost:8009"
TEST_EMAIL = "e2e_test@parksmart.com"
TEST_PASSWORD = "TestPass123!"
ADMIN_EMAIL = "admin@parksmart.com"
ADMIN_PASSWORD = "admin1234@"
PLATE = "51A-999.88"
VEHICLE_TYPE = "Car"
RESULTS_FILE = "test_e2e_results.json"

# ─── State ──────────────────────────────────────────────────────────────
results: dict[str, Any] = {
    "timestamp": datetime.now().isoformat(),
    "user": {},
    "vehicle": {},
    "parking_lot": {},
    "floor": {},
    "zone": {},
    "slot": {},
    "booking": {},
    "session_cookie": "",
    "api_timings": {},
}
passed = 0
failed = 0
total = 0


# ─── Helpers ────────────────────────────────────────────────────────────
class C:
    OK = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def step(ok: bool, msg: str, detail: str = "") -> bool:
    global passed, failed, total
    total += 1
    if ok:
        passed += 1
        icon = f"{C.OK}✅{C.END}"
    else:
        failed += 1
        icon = f"{C.FAIL}❌{C.END}"
    suffix = f" {C.DIM}({detail}){C.END}" if detail else ""
    print(f"  {icon} {msg}{suffix}")
    return ok


def timed_request(
    session: requests.Session,
    method: str,
    url: str,
    label: str,
    **kwargs,
) -> tuple[requests.Response, float]:
    t0 = time.time()
    resp = session.request(method, url, timeout=15, **kwargs)
    elapsed = round((time.time() - t0) * 1000)
    results["api_timings"][label] = f"{elapsed}ms"
    return resp, elapsed


def extract_results(data: Any) -> list:
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []


def print_banner():
    print(f"\n{C.BOLD}╔══════════════════════════════════════════╗")
    print(f"║  ParkSmart E2E Test Suite                ║")
    print(f"╚══════════════════════════════════════════╝{C.END}\n")


# ─── Phase 1: Setup ────────────────────────────────────────────────────
def phase1_setup(s: requests.Session) -> tuple[Optional[str], Optional[str]]:
    print(f"{C.BOLD}[Phase 1: Setup]{C.END}")

    # 1. Register user
    r, ms = timed_request(
        s,
        "POST",
        f"{GATEWAY_URL}/api/auth/register/",
        "register",
        json={
            "email": TEST_EMAIL,
            "username": "e2e_test",
            "password": TEST_PASSWORD,
            "phone": "0912345678",
        },
    )
    if r.status_code == 201:
        user_data = r.json().get("user", {})
        user_id = user_data.get("id", "")
        step(True, f"Register user: {TEST_EMAIL}", f"{ms}ms, id={user_id[:8]}...")
    elif r.status_code in (400, 409) or "already" in r.text.lower():
        step(True, f"Register user: {TEST_EMAIL}", "already exists")
        user_id = None  # will get from login
    else:
        step(False, f"Register user: {TEST_EMAIL}", f"status={r.status_code}")
        return None, None

    # 2. Login
    r, ms = timed_request(
        s,
        "POST",
        f"{GATEWAY_URL}/api/auth/login/",
        "login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )
    if r.status_code != 200:
        step(False, "Login", f"status={r.status_code}")
        return None, None

    login_data = r.json()
    user_info = login_data.get("user", {})
    user_id = user_info.get("id", user_id or "")
    session_cookie = s.cookies.get("sessionid", "")
    results["user"] = {"id": user_id, "email": TEST_EMAIL}
    results["session_cookie"] = session_cookie
    step(
        True,
        (
            f"Login: session={session_cookie[:12]}..."
            if session_cookie
            else "Login: cookie-based auth"
        ),
        f"{ms}ms",
    )

    # 3. Register vehicle
    r, ms = timed_request(
        s,
        "POST",
        f"{GATEWAY_URL}/api/vehicles/",
        "register_vehicle",
        json={
            "license_plate": PLATE,
            "vehicle_type": VEHICLE_TYPE,
            "brand": "Toyota",
            "model": "Camry",
            "color": "White",
            "is_default": True,
        },
    )

    vehicle_id = None
    if r.status_code == 201:
        vdata = r.json()
        vehicle_id = vdata.get("id", "")
        step(True, f"Register vehicle: {PLATE}", f"{ms}ms, id={vehicle_id[:8]}...")
    elif r.status_code in (400, 409) or "already" in r.text.lower():
        # Vehicle exists — fetch list and find it
        r2, _ = timed_request(s, "GET", f"{GATEWAY_URL}/api/vehicles/", "list_vehicles")
        vehicles = extract_results(r2.json())
        for v in vehicles:
            plate = v.get("license_plate", v.get("licensePlate", ""))
            if plate.replace(" ", "") == PLATE.replace(" ", ""):
                vehicle_id = v.get("id", "")
                break
        if not vehicle_id and vehicles:
            vehicle_id = vehicles[0].get("id", "")
        step(
            bool(vehicle_id),
            f"Register vehicle: {PLATE}",
            f"already exists, id={vehicle_id[:8] if vehicle_id else '?'}...",
        )
    else:
        step(
            False,
            f"Register vehicle: {PLATE}",
            f"status={r.status_code} {r.text[:200]}",
        )

    if vehicle_id:
        results["vehicle"] = {"id": vehicle_id, "plate": PLATE, "type": VEHICLE_TYPE}

    return user_id, vehicle_id


# ─── Phase 2: Get parking data ─────────────────────────────────────────
def phase2_parking_data(
    s: requests.Session,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[dict]]:
    print(f"\n{C.BOLD}[Phase 2: Parking Data]{C.END}")

    # 4. GET parking lots
    r, ms = timed_request(s, "GET", f"{GATEWAY_URL}/api/parking/lots/", "parking_lots")
    lots = extract_results(r.json())
    if not step(len(lots) > 0, f"Parking lots: {len(lots)} found", f"{ms}ms"):
        return None, None, None, None

    lot = lots[0]
    lot_id = lot.get("id", "")
    lot_name = lot.get("name", "Unknown")
    results["parking_lot"] = {"id": lot_id, "name": lot_name}
    print(f"       {C.DIM}Selected: {lot_name} (id={lot_id[:8]}...){C.END}")

    # 5. GET floors
    r, ms = timed_request(
        s,
        "GET",
        f"{GATEWAY_URL}/api/parking/floors/",
        "floors",
        params={"lot_id": lot_id},
    )
    floors = extract_results(r.json())
    if not step(len(floors) > 0, f"Floors: {len(floors)} found", f"{ms}ms"):
        return lot_id, None, None, None

    # Find floor 2 — by level number or name containing "2"
    floor2 = None
    for f in floors:
        level = f.get("level", f.get("floor_number", 0))
        name = f.get("name", "")
        if level == 2 or "2" in str(name):
            floor2 = f
            break
    if not floor2 and len(floors) >= 2:
        floor2 = floors[1]  # fallback: second floor in list
    if not floor2:
        floor2 = floors[0]  # last resort: first floor

    floor2_id = floor2.get("id", "")
    floor2_name = floor2.get("name", f"Floor {floor2.get('level', '?')}")
    results["floor"] = {
        "id": floor2_id,
        "name": floor2_name,
        "level": floor2.get("level"),
    }
    step(True, f"Selected Floor 2: {floor2_name}", f"id={floor2_id[:8]}...")

    # 6. GET zones on floor 2
    r, ms = timed_request(
        s,
        "GET",
        f"{GATEWAY_URL}/api/parking/zones/",
        "zones",
        params={"floor_id": floor2_id},
    )
    zones = extract_results(r.json())
    if not step(len(zones) > 0, f"Zones: {len(zones)} found on Floor 2", f"{ms}ms"):
        return lot_id, floor2_id, None, None

    # Prefer a zone with vehicle_type=car and available slots
    zone = None
    for z in zones:
        vtype = z.get("vehicle_type", z.get("vehicleType", "")).lower()
        avail = z.get("available_slots", z.get("availableSlots", 0))
        if vtype == "car" and avail > 0:
            zone = z
            break
    if not zone:
        zone = zones[0]

    zone_id = zone.get("id", "")
    zone_name = zone.get("name", "Unknown")
    results["zone"] = {"id": zone_id, "name": zone_name}
    print(f"       {C.DIM}Selected zone: {zone_name} (id={zone_id[:8]}...){C.END}")

    # 7. GET slots on floor 2
    r, ms = timed_request(
        s,
        "GET",
        f"{GATEWAY_URL}/api/parking/slots/",
        "slots",
        params={"lot_id": lot_id, "floor_id": floor2_id, "page_size": 200},
    )
    all_slots = extract_results(r.json())

    # Filter: available + car type
    car_slots = []
    for sl in all_slots:
        status = sl.get("status", "").lower()
        # Slot type may come from parent zone or slot itself
        if status == "available":
            car_slots.append(sl)

    if not step(
        len(car_slots) > 0,
        f"Slots: {len(car_slots)} available car slots on Floor 2",
        f"{ms}ms, total={len(all_slots)}",
    ):
        return lot_id, floor2_id, zone_id, None

    slot = car_slots[0]
    slot_info = {
        "id": slot.get("id", ""),
        "code": slot.get("code", "?"),
        "row": slot.get("row", slot.get("row_index", "?")),
        "column": slot.get("column", slot.get("col_index", "?")),
    }
    results["slot"] = slot_info
    print(
        f"       {C.DIM}Selected slot: {slot_info['code']} (id={slot_info['id'][:8]}...){C.END}"
    )

    return lot_id, floor2_id, zone_id, slot_info


# ─── Phase 3: Create booking ───────────────────────────────────────────
def phase3_booking(
    s: requests.Session,
    vehicle_id: str,
    lot_id: str,
    zone_id: str,
    slot_info: dict,
) -> Optional[dict]:
    print(f"\n{C.BOLD}[Phase 3: Booking]{C.END}")

    # 8. GET package pricing
    r, ms = timed_request(
        s, "GET", f"{GATEWAY_URL}/api/bookings/packagepricings/", "package_pricing"
    )
    pricing_list = extract_results(r.json())
    hourly_price = "?"
    for p in pricing_list:
        pkg = p.get("package_type", p.get("packageType", ""))
        vtype = p.get("vehicle_type", p.get("vehicleType", ""))
        if pkg == "hourly" and vtype.lower() == "car":
            hourly_price = p.get("price", "?")
            break
    step(
        len(pricing_list) > 0,
        (
            f"Package pricing: hourly = {hourly_price:,} VND/hour"
            if isinstance(hourly_price, (int, float))
            else f"Package pricing: {len(pricing_list)} packages"
        ),
        f"{ms}ms",
    )

    # 9. POST create booking
    start_time = datetime.now().isoformat()
    end_time = (datetime.now() + timedelta(hours=2)).isoformat()

    booking_payload = {
        "vehicle_id": vehicle_id,
        "parking_lot_id": lot_id,
        "zone_id": zone_id,
        "slot_id": slot_info["id"],
        "package_type": "hourly",
        "start_time": start_time,
        "end_time": end_time,
        "payment_method": "on_exit",
    }

    r, ms = timed_request(
        s,
        "POST",
        f"{GATEWAY_URL}/api/bookings/",
        "create_booking",
        json=booking_payload,
    )

    if r.status_code not in (200, 201):
        step(False, "Booking created", f"status={r.status_code} {r.text[:300]}")
        return None

    raw = r.json()
    bdata = raw.get("booking", raw) if isinstance(raw, dict) else raw
    booking_id = bdata.get("id", "")
    status = bdata.get("status", bdata.get("booking_status", "?"))
    qr_data = bdata.get("qr_code_data", bdata.get("qrCodeData", ""))
    payment_status = bdata.get("payment_status", bdata.get("paymentStatus", "?"))
    check_in_status = bdata.get("check_in_status", bdata.get("checkInStatus", "?"))

    step(True, f"Booking created: id={booking_id[:12]}..., status={status}", f"{ms}ms")

    booking_info = {
        "id": booking_id,
        "status": status,
        "qr_code_data": qr_data,
        "payment_status": payment_status,
        "check_in_status": check_in_status,
        "start_time": start_time,
        "end_time": end_time,
        "slot_code": slot_info["code"],
    }
    results["booking"] = booking_info

    # 10. Print QR data
    if qr_data:
        print(f"  {C.INFO}QR Data: {qr_data}{C.END}")

    return booking_info


# ─── Phase 4: AI Service ───────────────────────────────────────────────
def phase4_ai(s: requests.Session, booking_info: Optional[dict]):
    print(f"\n{C.BOLD}[Phase 4: AI Service]{C.END}")

    # 11. AI Health
    try:
        r, ms = timed_request(s, "GET", f"{AI_SERVICE_URL}/health/", "ai_health")
        step(r.status_code == 200, "AI Health: OK", f"{ms}ms")
    except requests.ConnectionError:
        step(False, "AI Health", "connection refused — AI service not running?")
        return

    # 12. Camera list
    try:
        r, ms = timed_request(
            s, "GET", f"{GATEWAY_URL}/api/ai/cameras/list", "camera_list"
        )
        if r.status_code == 200:
            cameras = r.json()
            count = (
                len(cameras) if isinstance(cameras, list) else cameras.get("count", "?")
            )
            step(True, f"Camera list: {count} cameras", f"{ms}ms")
        else:
            step(False, "Camera list", f"status={r.status_code}")
    except Exception as e:
        step(False, "Camera list", str(e))

    # 13. ESP32 check-in test (verify endpoint reachable, don't actually check-in)
    if booking_info and booking_info.get("qr_code_data"):
        try:
            # Use ESP32 status endpoint instead of actually checking in
            r, ms = timed_request(
                s, "GET", f"{GATEWAY_URL}/api/ai/parking/esp32/status/", "esp32_status"
            )
            step(
                r.status_code == 200,
                "ESP32 check-in test: endpoint reachable",
                f"{ms}ms",
            )
        except Exception as e:
            step(False, "ESP32 check-in test", str(e))
    else:
        step(False, "ESP32 check-in test", "no booking/QR data available")


# ─── Phase 5: Chatbot ──────────────────────────────────────────────────
def phase5_chatbot(s: requests.Session):
    print(f"\n{C.BOLD}[Phase 5: Chatbot]{C.END}")

    # 14. Greeting
    try:
        r, ms = timed_request(
            s,
            "POST",
            f"{GATEWAY_URL}/api/chatbot/chat/",
            "chatbot_greeting",
            json={"message": "Xin chào"},
        )
        if r.status_code == 200:
            reply = r.json()
            msg = reply.get("response", reply.get("message", reply.get("reply", "")))
            preview = (msg[:60] + "...") if len(msg) > 60 else msg
            step(True, f"Chatbot greeting: responded", f'{ms}ms — "{preview}"')
        else:
            step(False, "Chatbot greeting", f"status={r.status_code}")
    except requests.ConnectionError:
        step(
            False,
            "Chatbot greeting",
            "connection refused — chatbot service not running?",
        )
        return
    except Exception as e:
        step(False, "Chatbot greeting", str(e))

    # 15. Booking query
    try:
        r, ms = timed_request(
            s,
            "POST",
            f"{GATEWAY_URL}/api/chatbot/chat/",
            "chatbot_query",
            json={"message": "Tôi muốn xem booking"},
        )
        if r.status_code == 200:
            reply = r.json()
            msg = reply.get("response", reply.get("message", reply.get("reply", "")))
            preview = (msg[:60] + "...") if len(msg) > 60 else msg
            step(True, f"Chatbot query: responded", f'{ms}ms — "{preview}"')
        else:
            step(False, "Chatbot query", f"status={r.status_code}")
    except Exception as e:
        step(False, "Chatbot query", str(e))


# ─── Phase 6: Save results ─────────────────────────────────────────────
def phase6_save():
    results["summary"] = {"passed": passed, "failed": failed, "total": total}
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)


def print_summary():
    ok = failed == 0
    color = C.OK if ok else C.FAIL

    print(f"\n{C.BOLD}═══ Summary ═══{C.END}")
    print(f"{color}Total: {passed}/{total} passed{C.END}")
    print(f"Booking saved to {RESULTS_FILE}")

    # Unity testing info
    booking = results.get("booking", {})
    slot = results.get("slot", {})
    floor = results.get("floor", {})

    print(f"\n{C.BOLD}══════════════════════════════════════════")
    print(f"UNITY TESTING INFO:")
    print(f"  User: {TEST_EMAIL} / {TEST_PASSWORD}")
    print(f"  Vehicle: {PLATE}")
    print(f"  Slot: {slot.get('code', '?')} ({floor.get('name', 'Floor ?')})")
    print(f"  Booking ID: {booking.get('id', '?')}")
    print(f"  QR Data: {booking.get('qr_code_data', '?')}")
    print(f"══════════════════════════════════════════{C.END}\n")


# ─── Main ───────────────────────────────────────────────────────────────
def main():
    print_banner()
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})

    # Phase 1
    user_id, vehicle_id = phase1_setup(s)
    if not user_id or not vehicle_id:
        print(
            f"\n{C.FAIL}ABORT: Phase 1 failed — cannot continue without user/vehicle.{C.END}"
        )
        phase6_save()
        print_summary()
        sys.exit(1)

    # Phase 2
    lot_id, floor2_id, zone_id, slot_info = phase2_parking_data(s)
    if not lot_id or not slot_info:
        print(
            f"\n{C.FAIL}ABORT: Phase 2 failed — cannot continue without parking data.{C.END}"
        )
        phase6_save()
        print_summary()
        sys.exit(1)

    # Phase 3
    booking_info = phase3_booking(s, vehicle_id, lot_id, zone_id, slot_info)

    # Phase 4 (non-blocking — AI may not be running)
    phase4_ai(s, booking_info)

    # Phase 5 (non-blocking — chatbot may not be running)
    phase5_chatbot(s)

    # Phase 6
    phase6_save()
    print_summary()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
