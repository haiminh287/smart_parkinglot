# Research Report: ESP32 Check-In API Flow — Backend Trace

**Task:** ESP32 Check-In Flow Analysis | **Date:** 2026-04-10 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Root cause of failure**: Khi `qr_data` field **KHÔNG** được gửi trong request body, ESP32 check-in endpoint tự mở DroidCam stream tại `http://192.168.100.130:4747/video` để quét QR → fail vì camera không reachable.
> 2. **Fix đơn giản**: Unity client **đã gửi** `qr_data` → endpoint **đã có logic** skip camera khi `qr_data` có giá trị. Bug có thể ở phía client (field name mismatch hoặc `qr_data` gửi rỗng).
> 3. **Gateway routing**: `ai/` prefix → AI Service (port 8009). ESP32 endpoints ở `/ai/parking/esp32/*`. Yêu cầu JWT session auth qua gateway.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 ALL ESP32-Related Endpoints

| #   | Method | Path                                         | File                                      | Lines      | Description                              |
| --- | ------ | -------------------------------------------- | ----------------------------------------- | ---------- | ---------------------------------------- |
| 1   | POST   | `/ai/parking/esp32/check-in/`                | `ai-service-fastapi/app/routers/esp32.py` | L680-1000  | Gate-in: QR + plate OCR + barrier        |
| 2   | POST   | `/ai/parking/esp32/check-out/`               | `ai-service-fastapi/app/routers/esp32.py` | L1035-1300 | Gate-out: QR + plate + payment + barrier |
| 3   | POST   | `/ai/parking/esp32/verify-slot/`             | `ai-service-fastapi/app/routers/esp32.py` | L1355-1530 | Slot-level: QR → booking→slot match      |
| 4   | POST   | `/ai/parking/esp32/cash-payment/`            | `ai-service-fastapi/app/routers/esp32.py` | L1535-1700 | Cash insertion → AI detect → accumulate  |
| 5   | GET    | `/ai/parking/esp32/status/`                  | `ai-service-fastapi/app/routers/esp32.py` | L1730-1790 | Health + camera status check             |
| 6   | POST   | `/ai/parking/esp32/register`                 | `ai-service-fastapi/app/routers/esp32.py` | L1830-1870 | ESP32 registers on boot                  |
| 7   | POST   | `/ai/parking/esp32/heartbeat`                | `ai-service-fastapi/app/routers/esp32.py` | L1880-1900 | Periodic keepalive                       |
| 8   | POST   | `/ai/parking/esp32/log`                      | `ai-service-fastapi/app/routers/esp32.py` | L1910-1960 | ESP32 sends log messages                 |
| 9   | GET    | `/ai/parking/esp32/devices`                  | `ai-service-fastapi/app/routers/esp32.py` | L1965-1980 | List all registered ESP32 devices        |
| 10  | GET    | `/ai/parking/esp32/devices/{device_id}/logs` | `ai-service-fastapi/app/routers/esp32.py` | L1985-2010 | Get logs for one device                  |

**Non-ESP32 check-in endpoints (parking.py router):**

| #   | Method | Path                      | File                                        | Lines    | Description                                               |
| --- | ------ | ------------------------- | ------------------------------------------- | -------- | --------------------------------------------------------- |
| 11  | POST   | `/ai/parking/check-in/`   | `ai-service-fastapi/app/routers/parking.py` | L159-280 | Web check-in: UploadFile image + Form qr_data (NO camera) |
| 12  | POST   | `/ai/parking/check-out/`  | `ai-service-fastapi/app/routers/parking.py` | L283-400 | Web check-out: UploadFile image + Form qr_data            |
| 13  | POST   | `/ai/parking/scan-plate/` | `ai-service-fastapi/app/routers/parking.py` | L130-158 | Standalone plate OCR (no booking)                         |

### 2.2 The DroidCam Camera URL Configuration

| File                               | Line | Setting               | Default Value                                  |
| ---------------------------------- | ---- | --------------------- | ---------------------------------------------- |
| `ai-service-fastapi/app/config.py` | L24  | `CAMERA_DROIDCAM_URL` | `http://192.168.100.130:4747`                  |
| `ai-service-fastapi/app/config.py` | L25  | `CAMERA_RTSP_URL`     | `rtsp://user:password@192.168.1.100:554/H.264` |
| `ai-service-fastapi/app/config.py` | L26  | `CAMERA_HTTP_URL`     | `http://192.168.100.130:80`                    |

**How the QR camera URL is constructed** (esp32.py L172-173):

```python
DEFAULT_QR_CAMERA_URL = f"{settings.CAMERA_DROIDCAM_URL}/video"
# → "http://192.168.100.130:4747/video"
```

### 2.3 The Check-In Code Path — DETAILED TRACE

#### ESP32 Check-In Flow (esp32.py `esp32_check_in()` L680+)

```
Unity sends POST /api/ai/parking/esp32/check-in/
  Body: { "gate_id": "GATE-IN-01", "qr_data": "{\"booking_id\":\"...\",\"user_id\":\"...\"}" }
```

**Step 1: QR Data Resolution (L700-740)**

```python
if payload.qr_data:                          # ← IF qr_data IS PROVIDED
    qr_text = payload.qr_data.strip()        # ← Use it directly, NO camera
    qr_payload_parsed = QRPayload.from_json(qr_text)
    booking_id = qr_payload_parsed.booking_id
    user_id = qr_payload_parsed.user_id
else:                                         # ← IF qr_data IS EMPTY/NONE
    qr_url = payload.qr_camera_url or _get_camera_url("qr")
    # → _get_camera_url("qr") returns DEFAULT_QR_CAMERA_URL
    # → "http://192.168.100.130:4747/video"  ← THIS IS THE FAILURE POINT
    capture = get_camera_capture()
    qr_reader = get_qr_reader()
    _qr_frame, qr_text = await capture.scan_qr_loop(
        qr_url, qr_reader, timeout_s=30
    )
    # → CameraCaptureError("Cannot open QR camera stream: http://192.168.100.130:4747/video")
```

**Step 2: Fetch Booking (L745-770)**

```python
booking = await _get_booking(booking_id, user_id)
# → GET http://booking-service:8000/bookings/{booking_id}/
# Headers: X-Gateway-Secret, X-User-ID
```

**Step 3: Validate booking** — status must be `not_checked_in`, time window ≤15 min early, payment check for online bookings.

**Step 4: Plate Image Capture (L820-870)**

```python
# Priority 1: Virtual camera buffer (Unity VirtualCameraStreamer → POST /ai/cameras/frame)
_virtual_cam_id = "virtual-gate-in"
with _buffer_lock:
    _vf = _virtual_frame_buffer.get(_virtual_cam_id)
# If virtual camera frame is fresh (< STALE_THRESHOLD): use it

# Priority 2: Real RTSP camera
plate_url = payload.plate_camera_url or _get_camera_url("plate")
# → settings.CAMERA_RTSP_URL (rtsp://...)

# Priority 3: Static test image fallback
_static_plate_img = _LOCAL_IMAGES / "51A-224.56.jpg"
```

**Step 5: OCR + Plate Match** — Only enforced when plate came from real/virtual camera, skipped for test images.

**Step 6: Call booking-service checkin**

```python
checkin_resp = await _call_booking_checkin(booking_id, user_id)
# → POST http://booking-service:8000/bookings/{booking_id}/checkin/
# Headers: X-Gateway-Secret, X-User-ID
```

**Step 7: Update slot status + broadcast events + Unity spawn vehicle**

### 2.4 Camera Capture Code (the error source)

File: `ai-service-fastapi/app/engine/camera_capture.py`

```python
# L186-192: _scan_qr_loop_sync()
cap = cv2.VideoCapture(stream_url)   # tries to open http://192.168.100.130:4747/video
if not cap.isOpened():
    cap.release()
    raise CameraCaptureError(
        f"Cannot open QR camera stream: {stream_url}"
    )
# ↑ THIS is the exact error message seen in the Unity error log
```

### 2.5 Gateway Routing

File: `gateway-service-go/internal/config/config.go` L160:

```go
{"ai/", ServiceRoute{"ai", c.AIServiceURL, false}},
```

- Path: `/api/ai/parking/esp32/check-in/` → normalized to `ai/parking/esp32/check-in/` → matched by `ai/` prefix
- Routed to: `AI_SERVICE_URL` (default: `http://ai-service:8000`, local override: `http://localhost:8009`)
- `Public: false` → **requires JWT session auth** through gateway
- Gateway injects: `X-Gateway-Secret`, `X-User-ID`, `X-User-Email`, `X-User-Role`

### 2.6 ESP32 Device Token Auth

File: `ai-service-fastapi/app/routers/esp32.py` L59-65:

```python
async def verify_device_token(x_device_token: str = Header(default="")) -> None:
    expected = settings.ESP32_DEVICE_TOKEN
    if not expected:       # ← Empty string = no token required
        return
    if not x_device_token or not hmac.compare_digest(x_device_token, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing device token.")
```

Currently `ESP32_DEVICE_TOKEN = ""` → token auth is **disabled**.

### 2.7 Booking Service Check-in Endpoint

File: `booking-service/bookings/views.py` L104-130:

```python
@action(detail=True, methods=['post'], url_path='checkin')
def checkin(self, request, pk=None):
    booking = self.get_object()
    # Validates: check_in_status == 'not_checked_in'
    # Validates: time window (30 min early allowed)
    booking.check_in_status = 'checked_in'
    booking.checked_in_at = timezone.now()
    booking.save(update_fields=['check_in_status', 'checked_in_at'])
```

URL pattern (booking-service/bookings/urls.py L64):

```python
path('<uuid:pk>/checkin/', views.BookingViewSet.as_view({'post': 'checkin'}))
```

---

## 3. Full Request Flow: Unity → Gateway → Backend

```
Unity ParkingManager.cs
  → POST http://localhost:8000/api/ai/parking/esp32/check-in/
    Headers: Cookie: session_id=xxx
    Body: { "gate_id": "GATE-IN-01", "qr_data": "{\"booking_id\":\"...\",\"user_id\":\"...\"}" }

Gateway (Go, port 8000)
  → AuthMiddleware: validate session_id cookie from Redis
  → NormalizeServicePath: "ai/parking/esp32/check-in/"
  → GetServiceRoute: matches "ai/" prefix → AI Service
  → ReverseProxy to http://ai-service:8009/ai/parking/esp32/check-in/
    Injects: X-Gateway-Secret, X-User-ID, X-User-Email, X-User-Role

AI Service (FastAPI, port 8009)
  → verify_device_token (currently disabled)
  → esp32_check_in(payload)

  IF payload.qr_data exists:
    → Parse QR JSON → booking_id, user_id (NO camera needed ✅)
  ELSE:
    → Open DroidCam at 192.168.100.130:4747/video (FAILS ❌)

  → GET booking-service:8000/bookings/{booking_id}/
  → Validate status, time, payment
  → Capture plate from virtual camera buffer / RTSP / test image
  → OCR plate → compare
  → POST booking-service:8000/bookings/{booking_id}/checkin/
  → PATCH parking-service:8000/parking/slots/{slot_id}/update-status/
  → Broadcast gate.check_in event
  → Broadcast unity.spawn_vehicle command
  → Return ESP32Response { barrier_action: "open" }
```

---

## 4. Root Cause Analysis

### The error:

```
QR camera/scan FAILED: Cannot open QR camera stream: http://192.168.100.130:4747/video
```

### Why it happens:

The `esp32_check_in()` endpoint enters the `else` branch (L730+) which means `payload.qr_data` evaluated to `None` or empty string. This triggers the camera-based QR scanning flow.

### Possible causes:

| #   | Cause                                                                        | Likelihood | How to verify                                    |
| --- | ---------------------------------------------------------------------------- | ---------- | ------------------------------------------------ |
| 1   | Unity sends `qr_data` as **empty string** `""`                               | HIGH       | Check Unity request body                         |
| 2   | Unity sends `qrData` (camelCase) but endpoint expects `qr_data` (snake_case) | MEDIUM     | ESP32CheckInRequest uses `qr_data` with no alias |
| 3   | Unity sends QR data as a different field name (e.g. `qr_code`)               | MEDIUM     | Check Unity ParkingManager.cs                    |
| 4   | Unity doesn't include `qr_data` field at all                                 | MEDIUM     | Check request construction                       |
| 5   | Gateway strips/modifies the body                                             | LOW        | Gateway proxies body as-is                       |

**Key insight**: `ESP32CheckInRequest` uses Pydantic `BaseModel` (NOT `CamelModel`), so it expects **snake_case** field names in the request body: `gate_id`, `qr_data`. If Unity sends `gateId` and `qrData`, they will be ignored (treated as `None`).

---

## 5. ⚠️ Gotchas & Known Issues

- [ ] **[CRITICAL]** `ESP32CheckInRequest` uses `BaseModel` (not `CamelModel`) → expects `snake_case` fields. If Unity sends `camelCase`, `qr_data` is `None` → triggers camera fallback → FAILS.
- [ ] **[WARNING]** DroidCam URL `192.168.100.130:4747` is hardcoded as default — only matters when `qr_data` is missing AND `qr_camera_url` is not set.
- [ ] **[NOTE]** `verify_device_token` is disabled (empty token) — no auth on ESP32 endpoints beyond gateway session.
- [ ] **[NOTE]** Plate verification is **skipped** when using test images (non-real camera) — by design for dev.
- [ ] **[NOTE]** Both `parking.py` and `esp32.py` have duplicate check-in logic — `parking.py` check-in expects `UploadFile` image + `Form` qr_data; `esp32.py` check-in expects JSON body.

---

## 6. What Needs to Change to Make Check-in Work Without Camera

### Option A: Fix Unity client (most likely fix)

Ensure Unity sends **snake_case** field names:

```json
{
  "gate_id": "GATE-IN-01",
  "qr_data": "{\"booking_id\":\"xxx\",\"user_id\":\"yyy\"}"
}
```

### Option B: Add camelCase aliases to ESP32 schemas

Change `ESP32CheckInRequest` to use `CamelModel` or add `Field(alias=...)`:

```python
class ESP32CheckInRequest(CamelModel):  # Was: BaseModel
    gate_id: str = Field(...)
    qr_data: Optional[str] = Field(None)
    # CamelModel auto-aliases to camelCase: gateId, qrData
```

### Option C: Make the camera fallback non-fatal

If `qr_data` is missing AND camera fails, return a clear error instead of a cryptic camera error:

```python
if not payload.qr_data and not payload.qr_camera_url:
    return ESP32Response(
        success=False,
        message="❌ QR data required. Send qr_data in request body.",
        ...
    )
```

---

## 7. Checklist cho Implementer

- [ ] **Check Unity ParkingManager.cs**: verify the field names sent in check-in request (snake_case vs camelCase)
- [ ] **Option B**: Consider changing `ESP32CheckInRequest` base class from `BaseModel` to `CamelModel` for consistency
- [ ] **No camera needed**: When `qr_data` is provided, the endpoint already skips camera — just ensure the field arrives correctly
- [ ] **No new endpoints needed**: All slot-level check-in is handled by `/verify-slot/` endpoint
- [ ] Config: `CAMERA_DROIDCAM_URL` can be overridden via env var (`.env` file)
- [ ] Pattern reference: use `app/routers/esp32.py` check-in as the primary flow

---

## 8. Nguồn

| #   | File                                              | Mô tả                         | Lines    |
| --- | ------------------------------------------------- | ----------------------------- | -------- |
| 1   | `ai-service-fastapi/app/routers/esp32.py`         | ESP32 router (all endpoints)  | 1-2010   |
| 2   | `ai-service-fastapi/app/routers/parking.py`       | Web parking check-in/out      | 1-400    |
| 3   | `ai-service-fastapi/app/config.py`                | DroidCam URL config           | L24-27   |
| 4   | `ai-service-fastapi/app/engine/camera_capture.py` | Camera capture + QR scan loop | L186-224 |
| 5   | `ai-service-fastapi/app/engine/qr_reader.py`      | QR payload parser             | L1-100   |
| 6   | `gateway-service-go/internal/config/config.go`    | Gateway route table           | L136-165 |
| 7   | `gateway-service-go/internal/handler/proxy.go`    | Reverse proxy handler         | L1-150   |
| 8   | `gateway-service-go/internal/middleware/auth.go`  | JWT session auth              | L1-80    |
| 9   | `booking-service/bookings/views.py`               | Booking checkin endpoint      | L104-130 |
| 10  | `booking-service/bookings/urls.py`                | Booking URL routing           | L64-68   |
