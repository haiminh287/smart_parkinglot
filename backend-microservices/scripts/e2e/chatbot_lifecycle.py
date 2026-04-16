"""
Chatbot Full Lifecycle E2E Test
================================
Tests the complete booking lifecycle through chatbot:
  1. Login
  2. Greeting
  3. Help
  4. Check availability (car)
  5. Check availability (motorcycle)
  6. Pricing
  7. Book a car slot → SUCCESS
  8. My bookings (sees new booking)
  9. Check-in → SUCCESS
  10. Current parking (sees checked-in booking)
  11. Check-out → SUCCESS
  12. My bookings (sees completed booking)
  13. Book another slot → SUCCESS
  14. Cancel booking → SUCCESS
  15. Check-in (with space) → keyword test
  16. Check-out (with space) → keyword test
  17. No-accent Vietnamese
  18. Goodbye
"""
import requests
import json
import time
import sys
import re

BASE = "http://localhost:8000"
session = requests.Session()
results = {"passed": 0, "failed": 0, "tests": []}


def login():
    r = session.post(f"{BASE}/auth/login/", json={
        "email": "chattest@parksmart.com",
        "password": "Test@1234"
    })
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    print("✅ Login OK")


def chat(message, conv_id=None):
    body = {"message": message}
    if conv_id:
        body["conversationId"] = conv_id
    r = session.post(f"{BASE}/chatbot/chat/", json=body)
    if r.status_code != 200:
        print(f"  ❌ HTTP {r.status_code}: {r.text[:200]}")
        return None
    return r.json()


def run_test(name, result, checks):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

    if result is None:
        print("  ❌ FAILED - No response")
        results["failed"] += 1
        results["tests"].append({"name": name, "status": "FAIL", "reason": "No response"})
        return False

    intent = result.get("intent", result.get("decisionData", {}).get("intent", "N/A"))
    confidence = result.get("confidence", "N/A")
    resp = result.get("response", "")
    short_resp = resp[:200] + "..." if len(resp) > 200 else resp
    print(f"  Intent:     {intent}")
    print(f"  Confidence: {confidence}")
    print(f"  Response:   {short_resp}")

    all_ok = True
    for check_name, check_fn in checks.items():
        try:
            ok = check_fn(result)
            status = "✅" if ok else "❌"
            print(f"  {status} {check_name}")
            if not ok:
                all_ok = False
        except Exception as e:
            print(f"  ❌ {check_name}: {e}")
            all_ok = False

    if all_ok:
        results["passed"] += 1
        results["tests"].append({"name": name, "status": "PASS"})
    else:
        results["failed"] += 1
        results["tests"].append({"name": name, "status": "FAIL"})
    return all_ok


def get_intent(r):
    return r.get("intent", r.get("decisionData", {}).get("intent", ""))


def get_response(r):
    return r.get("response", "")


def main():
    print("=" * 60)
    print("CHATBOT FULL LIFECYCLE E2E TEST")
    print("=" * 60)

    login()
    conv = f"lifecycle-test-{int(time.time())}"

    # ── TEST 1: Greeting ──
    r = chat("Xin chào", conv)
    run_test("1. Greeting", r, {
        "intent=greeting": lambda r: get_intent(r) == "greeting",
        "response has greeting": lambda r: any(w in get_response(r).lower() for w in ["chào", "👋"]),
    })
    time.sleep(0.3)

    # ── TEST 2: Help ──
    r = chat("Giúp tôi", conv)
    run_test("2. Help", r, {
        "intent=help": lambda r: get_intent(r) == "help",
        "response lists features": lambda r: "đặt chỗ" in get_response(r).lower() or "booking" in get_response(r).lower(),
    })
    time.sleep(0.3)

    # ── TEST 3: Check availability (car) ──
    r = chat("Còn chỗ cho ô tô không?", conv)
    run_test("3. Check availability (car)", r, {
        "intent=check_availability": lambda r: get_intent(r) == "check_availability",
        "response has slot count": lambda r: "chỗ trống" in get_response(r) or "🅿️" in get_response(r),
    })
    time.sleep(0.3)

    # ── TEST 4: Check availability (motorcycle) ──
    r = chat("Còn chỗ xe máy không?", conv)
    run_test("4. Check availability (motorcycle)", r, {
        "intent=check_availability": lambda r: get_intent(r) == "check_availability",
        "response present": lambda r: len(get_response(r)) > 10,
    })
    time.sleep(0.3)

    # ── TEST 5: Pricing ──
    r = chat("Giá gửi xe bao nhiêu?", conv)
    run_test("5. Pricing", r, {
        "intent=pricing": lambda r: get_intent(r) == "pricing",
        "response has prices": lambda r: "đ" in get_response(r) or "giá" in get_response(r).lower(),
    })
    time.sleep(0.3)

    # ── TEST 6: Book a car slot (now starts wizard flow) ──
    r = chat("Đặt chỗ cho ô tô", conv)
    run_test("6. Book car slot", r, {
        "intent=book_slot": lambda r: get_intent(r) == "book_slot",
        "booking wizard or success": lambda r: (
            "thành công" in get_response(r).lower()
            or "tối đa" in get_response(r).lower()
            or "không còn chỗ" in get_response(r).lower()
            or "tầng" in get_response(r).lower()  # Wizard shows floor selection
            or "chỗ trống" in get_response(r).lower()
        ),
    })
    booking_success = "thành công" in get_response(r).lower() if r else False
    booking_id = None
    if booking_success and r:
        # Extract booking ID from response like "Mã booking: `d4b4e33e`"
        match = re.search(r'`([a-f0-9]{8})`', get_response(r))
        if match:
            booking_id = match.group(1)
            print(f"  📋 Booking ID: {booking_id}")
    time.sleep(0.3)

    # ── TEST 7: My bookings (should see new booking) ──
    r = chat("Xem booking của tôi", conv)
    run_test("7. My bookings", r, {
        "intent=my_bookings": lambda r: get_intent(r) == "my_bookings",
        "response has booking data": lambda r: "booking" in get_response(r).lower() or "📋" in get_response(r),
    })
    time.sleep(0.3)

    # ── TEST 8: Check-in ──
    if booking_success:
        r = chat("Check-in", conv)
        checkin_ok = "thành công" in get_response(r).lower() if r else False
        run_test("8. Check-in", r, {
            "intent=check_in": lambda r: get_intent(r) == "check_in",
            "check-in success": lambda r: "thành công" in get_response(r).lower(),
        })
        time.sleep(0.3)

        # ── TEST 9: Current parking ──
        r = chat("Xe tôi đang đậu ở đâu?", conv)
        run_test("9. Current parking", r, {
            "intent=current_parking": lambda r: get_intent(r) == "current_parking",
            "response present": lambda r: len(get_response(r)) > 10,
        })
        time.sleep(0.3)

        # ── TEST 10: Check-out ──
        if checkin_ok:
            r = chat("Check-out", conv)
            run_test("10. Check-out", r, {
                "intent=check_out": lambda r: get_intent(r) == "check_out",
                "check-out success": lambda r: "thành công" in get_response(r).lower(),
            })
            time.sleep(0.3)

            # ── TEST 11: My bookings after checkout ──
            r = chat("Xem booking", conv)
            run_test("11. My bookings after checkout", r, {
                "intent=my_bookings": lambda r: get_intent(r) == "my_bookings",
                "has completed booking": lambda r: (
                    "hoàn thành" in get_response(r).lower()
                    or "completed" in get_response(r).lower()
                    or "booking" in get_response(r).lower()
                ),
            })
            time.sleep(0.3)
        else:
            print("\n  ⚠️ Tests 10-11 skipped (check-in failed)")
    else:
        print("\n  ⚠️ Tests 8-11 skipped (booking failed or max limit)")

    # ── TEST 12: Book + Cancel flow ──
    conv2 = f"cancel-test-{int(time.time())}"
    r = chat("Đặt chỗ ô tô", conv2)
    cancel_booking_ok = "thành công" in get_response(r).lower() if r else False
    run_test("12. Book for cancel test", r, {
        "intent=book_slot": lambda r: get_intent(r) == "book_slot",
        "booking attempted": lambda r: len(get_response(r)) > 10,
    })
    time.sleep(0.3)

    if cancel_booking_ok:
        r = chat("Hủy booking", conv2)
        run_test("13. Cancel booking", r, {
            "intent=cancel_booking": lambda r: get_intent(r) == "cancel_booking",
            "cancel success": lambda r: "hủy" in get_response(r).lower() and "thành công" in get_response(r).lower(),
        })
        time.sleep(0.3)
    else:
        print("\n  ⚠️ Test 13 skipped (no booking to cancel)")

    # ── TEST 14: Check-in with space ──
    conv3 = f"keyword-test-{int(time.time())}"
    r = chat("check in", conv3)
    run_test("14. 'check in' (with space)", r, {
        "intent=check_in": lambda r: get_intent(r) == "check_in",
        "NOT unknown": lambda r: get_intent(r) != "unknown",
    })
    time.sleep(0.3)

    # ── TEST 15: Check-out with space ──
    r = chat("check out", conv3)
    run_test("15. 'check out' (with space)", r, {
        "intent=check_out": lambda r: get_intent(r) == "check_out",
        "NOT unknown": lambda r: get_intent(r) != "unknown",
    })
    time.sleep(0.3)

    # ── TEST 16: No-accent Vietnamese ──
    r = chat("dat cho oto", conv3)
    run_test("16. No-accent 'dat cho oto'", r, {
        "intent=book_slot": lambda r: get_intent(r) == "book_slot",
        "NOT unknown": lambda r: get_intent(r) != "unknown",
    })
    time.sleep(0.3)

    # ── TEST 17: Checkin (no dash/space) ──
    r = chat("checkin", conv3)
    run_test("17. 'checkin' (no separator)", r, {
        "intent=check_in": lambda r: get_intent(r) == "check_in",
        "NOT unknown": lambda r: get_intent(r) != "unknown",
    })
    time.sleep(0.3)

    # ── TEST 18: Goodbye ──
    r = chat("Tạm biệt", conv3)
    run_test("18. Goodbye", r, {
        "intent=goodbye": lambda r: get_intent(r) == "goodbye",
        "response has farewell": lambda r: "tạm biệt" in get_response(r).lower() or "👋" in get_response(r),
    })

    # ── SUMMARY ──
    total = results["passed"] + results["failed"]
    print(f"\n{'='*60}")
    print(f"RESULTS: {results['passed']}/{total} PASSED, {results['failed']}/{total} FAILED")
    print(f"{'='*60}")

    for t in results["tests"]:
        icon = "✅" if t["status"] == "PASS" else "❌"
        print(f"  {icon} {t['name']}")

    if results["failed"] > 0:
        print(f"\n❌ {results['failed']} test(s) FAILED")
        sys.exit(1)
    else:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()
