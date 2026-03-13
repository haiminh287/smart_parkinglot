"""
Chatbot Multi-Turn E2E Test
Tests all 5 fixes: context follow-up, keyword coverage, handoff threshold,
confidence gate, and rich responses.
"""
import requests
import json
import time
import sys

BASE = "http://localhost:8000"
session = requests.Session()

def login():
    r = session.post(f"{BASE}/auth/login/", json={
        "email": "chattest@parksmart.com",
        "password": "Test@1234"
    })
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    print("✅ Login OK")
    return r.json()

def chat(message, conv_id=None):
    body = {"message": message}
    if conv_id:
        body["conversationId"] = conv_id
    r = session.post(f"{BASE}/chatbot/chat/", json=body)
    if r.status_code != 200:
        print(f"  ❌ HTTP {r.status_code}: {r.text[:200]}")
        return None
    data = r.json()
    return data

def test(name, result, checks):
    """Run assertions on a chat result"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    if result is None:
        print("  ❌ FAILED - No response")
        return False
    
    print(f"  Intent:     {result.get('intent', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 'N/A')}")
    print(f"  GateAction: {result.get('gateAction', 'N/A')}")
    resp = result.get('response', '')
    # Truncate long responses for readability
    if len(resp) > 200:
        print(f"  Response:   {resp[:200]}...")
    else:
        print(f"  Response:   {resp}")
    print(f"  Suggestions: {result.get('suggestions', [])}")
    
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
    
    return all_ok


def main():
    print("=" * 60)
    print("CHATBOT MULTI-TURN E2E TEST")
    print("=" * 60)
    
    login()
    passed = 0
    failed = 0
    
    # ========================================
    # TEST 1: Greeting
    # ========================================
    r = chat("Xin chào")
    conv_id = r.get("conversationId") if r else None
    ok = test("1. Greeting", r, {
        "intent=greeting": lambda r: r.get("intent") == "greeting",
        "confidence=1.0": lambda r: r.get("confidence", 0) >= 0.9,
        "has conversationId": lambda r: bool(r.get("conversationId")),
        "response contains greeting": lambda r: any(w in r.get("response", "").lower() for w in ["chào", "xin chào", "👋"]),
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 2: "Xem chỗ trống" → should ask for vehicle_type OR execute
    # ========================================
    r = chat("Xem chỗ trống", conv_id)
    ok = test("2. Xem chỗ trống (check availability)", r, {
        "intent=check_availability": lambda r: r.get("intent") == "check_availability",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
        "confidence > 0": lambda r: r.get("confidence", 0) > 0.3,
    })
    passed += ok; failed += not ok
    gate2 = r.get("gateAction") if r else None
    time.sleep(0.5)
    
    # ========================================
    # TEST 3: "Ô tô" → CRITICAL: context follow-up should merge entity
    # ========================================
    if gate2 == "clarify":
        r = chat("Ô tô", conv_id)
        ok = test("3. 'Ô tô' follow-up (CRITICAL context test)", r, {
            "intent=check_availability (context follow-up)": lambda r: r.get("intent") == "check_availability",
            "NOT handoff": lambda r: r.get("gateAction") != "handoff",
            "NOT unknown": lambda r: r.get("intent") != "unknown",
            "NOT clarify again": lambda r: r.get("gateAction") != "clarify",
            "response has data": lambda r: any(w in r.get("response", "") for w in ["chỗ", "slot", "trống", "khu", "zone", "🅿️"]),
        })
        passed += ok; failed += not ok
    else:
        print("\n  ℹ️  Test 3 skipped (Test 2 didn't clarify, went directly to execute)")
        r = chat("Ô tô", conv_id)  # still test it standalone
        ok = test("3. 'Ô tô' standalone", r, {
            "NOT handoff": lambda r: r.get("gateAction") != "handoff",
            "NOT unknown": lambda r: r.get("intent") != "unknown",
        })
        passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 4: "Ô tô còn mấy chỗ trống" → single message, full entity
    # ========================================
    r = chat("Ô tô còn mấy chỗ trống", conv_id)
    ok = test("4. 'Ô tô còn mấy chỗ trống' (single message)", r, {
        "intent=check_availability": lambda r: r.get("intent") == "check_availability",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
        "confidence >= 0.5": lambda r: r.get("confidence", 0) >= 0.5,
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 5: "Giá đậu xe bao nhiêu?" → pricing
    # ========================================
    r = chat("Giá đậu xe bao nhiêu?", conv_id)
    ok = test("5. 'Giá đậu xe bao nhiêu?' (pricing)", r, {
        "intent=pricing": lambda r: r.get("intent") == "pricing",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 6: "Cho tôi xem lịch đặt" → my_bookings
    # ========================================
    r = chat("Cho tôi xem lịch đặt", conv_id)
    ok = test("6. 'Cho tôi xem lịch đặt' (my_bookings)", r, {
        "intent=my_bookings": lambda r: r.get("intent") == "my_bookings",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 7: "Xem giá" → pricing (short form)
    # ========================================
    r = chat("Xem giá", conv_id)
    ok = test("7. 'Xem giá' (short pricing)", r, {
        "intent=pricing": lambda r: r.get("intent") == "pricing",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 8: "Tôi muốn đặt chỗ cho xe máy" → book_slot
    # ========================================
    r = chat("Tôi muốn đặt chỗ cho xe máy", conv_id)
    ok = test("8. 'Tôi muốn đặt chỗ cho xe máy' (book_slot)", r, {
        "intent=book_slot": lambda r: r.get("intent") == "book_slot",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 9: "oto con may cho" → accent-free Vietnamese
    # ========================================
    r = chat("oto con may cho", conv_id)
    ok = test("9. 'oto con may cho' (no-accent Vietnamese)", r, {
        "intent=check_availability": lambda r: r.get("intent") == "check_availability",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 10: "Xe hơi còn bao nhiêu chỗ" → check_availability
    # ========================================
    r = chat("Xe hơi còn bao nhiêu chỗ", conv_id)
    ok = test("10. 'Xe hơi còn bao nhiêu chỗ' (synonym)", r, {
        "intent=check_availability": lambda r: r.get("intent") == "check_availability",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 11: New conversation - multi-turn booking flow
    # ========================================
    r = chat("Tôi muốn đặt chỗ")
    conv_id2 = r.get("conversationId") if r else None
    ok = test("11. 'Tôi muốn đặt chỗ' (new conv, book_slot)", r, {
        "intent=book_slot": lambda r: r.get("intent") == "book_slot",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "has new conversationId": lambda r: bool(r.get("conversationId")),
    })
    passed += ok; failed += not ok
    gate11 = r.get("gateAction") if r else None
    time.sleep(0.5)
    
    # TEST 12: Follow up with vehicle type
    if gate11 == "clarify" and conv_id2:
        r = chat("Xe máy", conv_id2)
        ok = test("12. 'Xe máy' follow-up (book_slot context)", r, {
            "intent=book_slot (context)": lambda r: r.get("intent") == "book_slot",
            "NOT handoff": lambda r: r.get("gateAction") != "handoff",
            "NOT unknown": lambda r: r.get("intent") != "unknown",
        })
        passed += ok; failed += not ok
    else:
        print("\n  ℹ️  Test 12 skipped (Test 11 didn't clarify)")
    time.sleep(0.5)
    
    # ========================================
    # TEST 13: Help
    # ========================================
    r = chat("Giúp tôi", conv_id)
    ok = test("13. 'Giúp tôi' (help)", r, {
        "intent=help": lambda r: r.get("intent") == "help",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 14: Cancel booking
    # ========================================
    r = chat("Hủy đặt chỗ", conv_id)
    ok = test("14. 'Hủy đặt chỗ' (cancel_booking)", r, {
        "intent=cancel_booking": lambda r: r.get("intent") == "cancel_booking",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
        "NOT unknown": lambda r: r.get("intent") != "unknown",
    })
    passed += ok; failed += not ok
    time.sleep(0.5)
    
    # ========================================
    # TEST 15: Goodbye
    # ========================================
    r = chat("Tạm biệt", conv_id)
    ok = test("15. 'Tạm biệt' (goodbye)", r, {
        "intent=goodbye": lambda r: r.get("intent") == "goodbye",
        "NOT handoff": lambda r: r.get("gateAction") != "handoff",
    })
    passed += ok; failed += not ok
    
    # ========================================
    # SUMMARY
    # ========================================
    total = passed + failed
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} PASSED, {failed}/{total} FAILED")
    print(f"{'='*60}")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()
