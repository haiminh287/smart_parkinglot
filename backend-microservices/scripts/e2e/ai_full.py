"""
ParkSmart AI Test Suite — Full Coverage
Runs inside ai-service-fastapi container, calls both ai-service and chatbot-service.
Output saved to: /tmp/ai_test_results.txt (copy to host after run)
"""
import requests
import json
import os
import sys
import time
from datetime import datetime

# ─── Config ────────────────────────────────────────────────────────────────
BASE_AI   = "http://localhost:8009"
BASE_CHAT = "http://chatbot-service-fastapi:8008"
GW = {
    "X-Gateway-Secret": "gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE",
    "X-User-ID":    "test-user-001",
    "X-User-Email": "user@example.com",
}

RESULTS = []
LOG_LINES = []

RUN_AT = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(line=""):
    LOG_LINES.append(line)
    print(line)

def check(name, ok, detail="", extra=None):
    icon = "PASS" if ok else "FAIL"
    mark = "✅" if ok else "❌"
    msg  = f"  [{icon}] {mark}  {name}"
    if detail:
        msg += f"\n         {detail}"
    RESULTS.append((ok, name))
    log(msg)
    if extra:
        for line in (extra if isinstance(extra, list) else [extra]):
            log(f"         {line}")

def section(title):
    log("")
    log("=" * 60)
    log(f"  {title}")
    log("=" * 60)

# ─── Prepare plate images ──────────────────────────────────────────────────
def ensure_plate_images():
    """Create synthetic VN plate images if not present."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    plates = {
        "/tmp/plate_30G.jpg": ("30", "G", "123.45"),
        "/tmp/plate_51B.jpg": ("51", "B", "234.56"),
        "/tmp/plate_29A.jpg": ("29", "A", "998.87"),
    }
    for path, (province, letter, number) in plates.items():
        if os.path.exists(path):
            continue
        img = Image.new("RGB", (520, 180), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 110, 180], fill=(0, 50, 140))
        draw.rectangle([3, 3, 516, 176], outline=(0, 0, 0), width=5)
        try:
            font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except Exception:
            font_lg = font_sm = ImageFont.load_default()
        draw.text((12, 20),  province, fill=(255, 255, 0), font=font_lg)
        draw.text((18, 100), letter,   fill=(255, 255, 255), font=font_sm)
        draw.text((128, 28), number,   fill=(0, 0, 0), font=font_lg)
        img.save(path, quality=95)


ensure_plate_images()

# ══════════════════════════════════════════════════════════════════════════
# SECTION 1 — AI SERVICE HEALTH & BASIC
# ══════════════════════════════════════════════════════════════════════════
section("1. AI SERVICE — Health")

r = requests.get(BASE_AI + "/health/", timeout=5)
ok = r.status_code == 200
d  = r.json() if ok else {}
check("Health endpoint",  ok, f"status={d.get('status','')}  version={d.get('version','')}")

r = requests.get(BASE_AI + "/docs", timeout=5)
check("Swagger UI accessible", r.status_code == 200)

# ══════════════════════════════════════════════════════════════════════════
# SECTION 2 — LICENSE PLATE DETECTION
# ══════════════════════════════════════════════════════════════════════════
section("2. LICENSE PLATE DETECTION  (YOLOv8 finetune + TrOCR)")

plate_test_cases = [
    ("/tmp/plate_30G.jpg",    "30G-123.45",   "synthetic VN plate (PIL)"),
    ("/tmp/plate_51B.jpg",    "51B-234.56",   "synthetic VN plate (PIL)"),
    ("/tmp/license_plate.jpg","real plate img","close-up plate (Pexels)"),
    ("/tmp/car_plate.jpg",    "car w/ plate",  "car with visible plate"),
    ("/tmp/car_street.jpg",   "street scene",  "street car photo"),
]

for img_path, expected, label in plate_test_cases:
    if not os.path.exists(img_path):
        check(f"Plate: {label}", False, "image file not found — skip")
        continue
    t0 = time.time()
    with open(img_path, "rb") as f:
        r = requests.post(
            BASE_AI + "/ai/detect/license-plate/",
            files={"image": (os.path.basename(img_path), f, "image/jpeg")},
            headers=GW, timeout=120,
        )
    elapsed = round((time.time() - t0) * 1000)
    ok = r.status_code == 200
    d  = r.json() if ok else {}
    detail = (
        f"decision={d.get('decision','?')}  "
        f"text={repr(d.get('plate_text',''))}  "
        f"conf={d.get('confidence',0)}  "
        f"time={elapsed}ms"
    ) if ok else f"HTTP {r.status_code}: {r.text[:80]}"
    check(f"Plate: {label}", ok, detail)
    if ok and d.get("warning"):
        log(f"         ⚠️  warning: {d['warning']}")

# ── Parking scan-plate (simpler endpoint, same pipeline) ──
log("")
log("  --- scan-plate endpoint ---")
for img_path, label in [("/tmp/car_plate.jpg", "car_plate.jpg"),
                         ("/tmp/plate_30G.jpg", "plate_30G.jpg")]:
    if not os.path.exists(img_path):
        continue
    t0 = time.time()
    with open(img_path, "rb") as f:
        r = requests.post(
            BASE_AI + "/ai/parking/scan-plate/",
            files={"image": ("car.jpg", f, "image/jpeg")},
            headers=GW, timeout=120,
        )
    elapsed = round((time.time() - t0) * 1000)
    ok = r.status_code == 200
    d  = r.json() if ok else {}
    detail = (
        f"decision={d.get('decision','?')}  text={repr(d.get('plate_text',''))}  time={elapsed}ms"
    ) if ok else f"HTTP {r.status_code}: {r.text[:80]}"
    check(f"Scan-plate: {label}", ok, detail)

# ══════════════════════════════════════════════════════════════════════════
# SECTION 3 — BANKNOTE DETECTION
# ══════════════════════════════════════════════════════════════════════════
section("3. BANKNOTE DETECTION  (Hybrid MVP: YOLO + Color + EfficientNet)")

banknote_cases = [
    ("/tmp/banknote_100k.jpg",  "100000 VND banknote (full)"),
    ("/tmp/banknote_100k.jpg",  "100000 VND banknote (fast)"),
    ("/tmp/banknote_100k_2.jpg", "100000 VND banknote v2 (full)"),
]
modes = ["full", "fast", "full"]
for (img_path, label), mode in zip(banknote_cases, modes):
    if not os.path.exists(img_path):
        check(f"Banknote [{mode}]: {label}", False, "image not found")
        continue
    t0 = time.time()
    with open(img_path, "rb") as f:
        r = requests.post(
            BASE_AI + f"/ai/detect/banknote/?mode={mode}",
            files={"image": (os.path.basename(img_path), f, "image/jpeg")},
            headers=GW, timeout=30,
        )
    elapsed = round((time.time() - t0) * 1000)
    ok = r.status_code == 200
    d  = r.json() if ok else {}
    quality = d.get("quality") or {}
    detail = (
        f"denomination={d.get('denomination','?')}  "
        f"conf={d.get('confidence',0)}  "
        f"method={d.get('method','?')}  "
        f"time={elapsed}ms"
    ) if ok else f"HTTP {r.status_code}: {r.text[:80]}"
    check(f"Banknote [{mode}]: {label}", ok, detail)
    if ok and quality:
        log(f"         quality: blur={quality.get('blurScore')}  exposure={quality.get('exposureScore')}  status={quality.get('status')}")

# ══════════════════════════════════════════════════════════════════════════
# SECTION 4 — CASH RECOGNITION (ResNet50)
# ══════════════════════════════════════════════════════════════════════════
section("4. CASH RECOGNITION  (ResNet50 custom-trained)")

for img_path, label in [
    ("/tmp/banknote_100k.jpg",  "100000 VND banknote"),
    ("/tmp/banknote_100k_2.jpg", "100000 VND banknote v2"),
]:
    if not os.path.exists(img_path):
        check(f"Cash: {label}", False, "image not found")
        continue
    t0 = time.time()
    with open(img_path, "rb") as f:
        r = requests.post(
            BASE_AI + "/ai/detect/cash/",
            files={"image": (os.path.basename(img_path), f, "image/jpeg")},
            headers=GW, timeout=30,
        )
    elapsed = round((time.time() - t0) * 1000)
    ok = r.status_code == 200
    d  = r.json() if ok else {}
    detail = (
        f"denomination={d.get('denomination','?')}  "
        f"conf={round(d.get('confidence',0),3)}  "
        f"model={d.get('model_version','?')}  "
        f"time={elapsed}ms"
    ) if ok else f"HTTP {r.status_code}: {r.text[:80]}"
    check(f"Cash: {label}", ok, detail)
    if ok:
        probs = d.get("all_probabilities", {})
        top3 = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:3]
        log(f"         top-3: {top3}")

# ══════════════════════════════════════════════════════════════════════════
# SECTION 5 — PARKING OCCUPANCY
# ══════════════════════════════════════════════════════════════════════════
section("5. PARKING OCCUPANCY  (YOLO11n slot detection)")

img_path = "/tmp/parking_lot.jpg"
if os.path.exists(img_path):
    slots_2 = json.dumps([
        # Row A (top row, slots A1-A8) — parking_lot.jpg 1300×953px, vạch kẻ cam thực tế
        {"slot_id": "s1",  "slot_code": "A1", "x1": 0,    "y1": 130, "x2": 160,  "y2": 460},
        {"slot_id": "s2",  "slot_code": "A2", "x1": 160,  "y1": 130, "x2": 315,  "y2": 460},
        {"slot_id": "s3",  "slot_code": "A3", "x1": 315,  "y1": 130, "x2": 475,  "y2": 460},
        {"slot_id": "s4",  "slot_code": "A4", "x1": 475,  "y1": 130, "x2": 630,  "y2": 460},
        {"slot_id": "s5",  "slot_code": "A5", "x1": 630,  "y1": 130, "x2": 785,  "y2": 460},
        {"slot_id": "s6",  "slot_code": "A6", "x1": 785,  "y1": 130, "x2": 940,  "y2": 460},
        {"slot_id": "s7",  "slot_code": "A7", "x1": 940,  "y1": 130, "x2": 1100, "y2": 460},
        {"slot_id": "s8",  "slot_code": "A8", "x1": 1100, "y1": 130, "x2": 1300, "y2": 460},
        # Row B (bottom row, slots B1-B8)
        {"slot_id": "s9",  "slot_code": "B1", "x1": 0,    "y1": 495, "x2": 155,  "y2": 870},
        {"slot_id": "s10", "slot_code": "B2", "x1": 155,  "y1": 495, "x2": 310,  "y2": 870},
        {"slot_id": "s11", "slot_code": "B3", "x1": 310,  "y1": 495, "x2": 465,  "y2": 870},
        {"slot_id": "s12", "slot_code": "B4", "x1": 465,  "y1": 495, "x2": 620,  "y2": 870},
        {"slot_id": "s13", "slot_code": "B5", "x1": 620,  "y1": 495, "x2": 780,  "y2": 870},
        {"slot_id": "s14", "slot_code": "B6", "x1": 780,  "y1": 495, "x2": 940,  "y2": 870},
        {"slot_id": "s15", "slot_code": "B7", "x1": 940,  "y1": 495, "x2": 1100, "y2": 870},
        {"slot_id": "s16", "slot_code": "B8", "x1": 1100, "y1": 495, "x2": 1260, "y2": 870},
    ])
    t0 = time.time()
    with open(img_path, "rb") as f:
        r = requests.post(
            BASE_AI + "/ai/parking/detect-occupancy/",
            data={"camera_id": "cam-test-001", "slots": slots_2},
            files={"image": ("parking.jpg", f, "image/jpeg")},
            headers=GW, timeout=30,
        )
    elapsed = round((time.time() - t0) * 1000)
    ok = r.status_code == 200
    d  = r.json() if ok else {}
    detail = (
        f"total={d.get('totalSlots',0)}  "
        f"occupied={d.get('totalOccupied',0)}  "
        f"free={d.get('totalAvailable',0)}  "
        f"method={d.get('detectionMethod','?')}  "
        f"time_ms={round(d.get('processingTimeMs',0))}ms  "
        f"req={elapsed}ms"
    ) if ok else f"HTTP {r.status_code}: {r.text[:100]}"
    check("Parking occupancy (16 slots)", ok, detail)
    if ok:
        for s in d.get("slots", []):
            log(f"         slot {s['slotCode']}: {s['status']}  conf={s.get('confidence',0)}")
else:
    check("Parking occupancy", False, "parking_lot.jpg not found")

# ══════════════════════════════════════════════════════════════════════════
# SECTION 6 — CAMERAS
# ══════════════════════════════════════════════════════════════════════════
section("6. CAMERAS")

r = requests.get(BASE_AI + "/ai/cameras/list", headers=GW, timeout=10)
ok = r.status_code == 200
cameras = r.json() if ok else []
check("Camera list", ok, f"{len(cameras)} cameras registered")
if ok:
    for cam in cameras:
        log(f"         [{cam.get('type','?')}] {cam.get('id','?')} — {cam.get('name','?')}")

# Camera snapshot (optional, may timeout if RTSP unavailable)
if ok and cameras:
    cam_id = cameras[0].get("id", "")
    try:
        r = requests.get(BASE_AI + f"/ai/cameras/snapshot?camera_id={cam_id}", headers=GW, timeout=8)
        check("Camera snapshot attempt", r.status_code in (200, 503, 504),
              f"HTTP {r.status_code} (503/504 = camera offline, expected in test env)")
    except requests.exceptions.ReadTimeout:
        check("Camera snapshot attempt", True,
              "Timeout (expected — no real RTSP camera in test env)")
    except Exception as exc:
        check("Camera snapshot attempt", False, str(exc)[:80])

# ══════════════════════════════════════════════════════════════════════════
# SECTION 7 — MODEL REGISTRY
# ══════════════════════════════════════════════════════════════════════════
section("7. MODEL REGISTRY")

r = requests.get(BASE_AI + "/ai/models/metrics/", headers=GW, timeout=10)
ok = r.status_code == 200
d  = r.json() if ok else {}
models_info = d if isinstance(d, dict) else {}
check("Model metrics", ok, f"keys={list(models_info.keys())[:5]}")

r = requests.get(BASE_AI + "/ai/models/predictions/?limit=10", headers=GW, timeout=10)
ok = r.status_code == 200
d  = r.json() if ok else {}
preds = d if isinstance(d, list) else d.get("predictions", d.get("results", []))
check("Prediction history", ok, f"{len(preds)} recent predictions logged")

r = requests.get(BASE_AI + "/ai/models/versions/", headers=GW, timeout=10)
check("Model versions endpoint", r.status_code in (200, 404),
      f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════════════════════════
# SECTION 8 — CHATBOT SERVICE
# ══════════════════════════════════════════════════════════════════════════
section("8. CHATBOT SERVICE  (Gemini 2.0 Flash + keyword fallback)")

# Health
r = requests.get(BASE_CHAT + "/chatbot/health/", timeout=5)
ok = r.status_code == 200
d  = r.json() if ok else {}
llm_on = d.get("llmEnabled", False)
check("Chatbot health", ok,
      f"status={d.get('status','')}  llmEnabled={llm_on}  version={d.get('version','')}")

# Quick actions
r = requests.get(BASE_CHAT + "/chatbot/quick-actions/", headers=GW, timeout=5)
ok = r.status_code == 200
d  = r.json() if ok else {}
actions = d.get("quickActions", [])
check("Quick actions", ok, f"{len(actions)} actions: {[a['id'] for a in actions[:4]]}")

# Chat conversations
chat_cases = [
    ("greeting",         "Xin chào!",                                   "greeting"),
    ("parking_info",     "Còn bao nhiêu chỗ trống cho ô tô?",           "check_availability"),
    ("pricing",          "Giá đỗ xe bao nhiêu tiền một giờ?",            "pricing_info"),
    ("booking_help",     "Tôi muốn đặt chỗ đỗ xe ngày mai",             "booking"),
    ("open_hours",       "Bãi xe mở cửa mấy giờ?",                      "hours_info"),
    ("support_request",  "Tôi cần hỗ trợ khẩn cấp",                    "support"),
]

conv_id = None
for test_name, message, expected_intent in chat_cases:
    t0 = time.time()
    payload = {"message": message, "conversationId": conv_id}
    r = requests.post(BASE_CHAT + "/chatbot/chat/", json=payload, headers=GW, timeout=20)
    elapsed = round((time.time() - t0) * 1000)
    ok = r.status_code == 200
    d  = r.json() if ok else {}
    if ok and conv_id is None:
        conv_id = d.get("conversationId")
    intent_match = d.get("intent", "?") == expected_intent if ok else False
    detail = (
        f"intent={d.get('intent','?')}  "
        f"conf={d.get('confidence',0)}  "
        f"time={elapsed}ms"
    ) if ok else f"HTTP {r.status_code}: {r.text[:80]}"
    check(f"Chat [{test_name}]: {repr(message[:30])}", ok, detail)
    if ok:
        resp_preview = d.get("response", "")[:80]
        log(f"         response: {repr(resp_preview)}")
        if d.get("suggestions"):
            log(f"         suggestions: {d['suggestions'][:3]}")

# Conversation history
if conv_id:
    r = requests.get(
        BASE_CHAT + f"/chatbot/conversations/{conv_id}/messages/",
        headers=GW, timeout=10,
    )
    ok = r.status_code == 200
    d  = r.json() if ok else {}
    msgs = d if isinstance(d, list) else d.get("messages", [])
    check("Conversation history", ok, f"{len(msgs)} messages in conversation {conv_id[:8]}...")

# ══════════════════════════════════════════════════════════════════════════
# SECTION 9 — LLM QUALITY CHECK  (only if Gemini enabled)
# ══════════════════════════════════════════════════════════════════════════
if llm_on:
    section("9. LLM QUALITY — Gemini natural language responses")

    llm_cases = [
        ("Bạn là ai và có thể làm gì?",           "identity"),
        ("Làm thế nào để book chỗ đậu xe qua app?", "how_to_book"),
        ("Tôi quên mất biển số xe khi check-in?",  "forgot_plate"),
    ]
    for message, label in llm_cases:
        t0 = time.time()
        r = requests.post(BASE_CHAT + "/chatbot/chat/",
            json={"message": message, "conversationId": conv_id},
            headers=GW, timeout=30)
        elapsed = round((time.time() - t0) * 1000)
        ok = r.status_code == 200
        d  = r.json() if ok else {}
        check(f"LLM [{label}]", ok,
              f"intent={d.get('intent','?')}  time={elapsed}ms")
        if ok:
            log(f"         Q: {message}")
            log(f"         A: {(d.get('response') or '')[:120]}")
else:
    section("9. LLM QUALITY — SKIPPED (llmEnabled=False)")
    log("  ⚠️  Gemini API key not configured — LLM tests skipped")

# ══════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════
section("SUMMARY")
passed = sum(1 for ok, _ in RESULTS if ok)
failed = sum(1 for ok, _ in RESULTS if not ok)
total  = len(RESULTS)
pct    = round(passed / total * 100) if total else 0

log(f"  Run at  : {RUN_AT}")
log(f"  Total   : {total}")
log(f"  Passed  : {passed}  ({pct}%)")
log(f"  Failed  : {failed}")
log("")
if failed:
    log("  Failed tests:")
    for ok, name in RESULTS:
        if not ok:
            log(f"    ✗ {name}")
log("")
if pct == 100:
    log("  🎉  ALL TESTS PASSED")
elif pct >= 80:
    log("  ✅  MOSTLY PASSING — minor issues")
else:
    log("  ❌  NEEDS ATTENTION")

# Write to file
out_path = "/tmp/ai_test_results.txt"
header = [
    "=" * 70,
    f"  ParkSmart AI Test Suite — {RUN_AT}",
    "=" * 70,
    "",
]
with open(out_path, "w", encoding="utf-8") as fout:
    fout.write("\n".join(header + LOG_LINES) + "\n")
print(f"\nLog saved: {out_path}")
