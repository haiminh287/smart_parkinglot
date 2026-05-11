# Research Report: ESP32 Check-in Plate Detection Flow

**Task:** ESP32 check-in returns `plateText: null` | **Date:** 2026-04-15 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **ROOT CAUSE**: ESP32 check-in endpoint đọc frame từ camera `"virtual-gate-in"` (wide-angle overview, FOV 55°), nhưng camera ANPR chuyên đọc biển số là `"virtual-anpr-entry"` (FOV 35°, plate chiếm ~42% frame). Sai camera ID → plate quá nhỏ → YOLO detect NOT_FOUND → trả `plateText: null`.
> 2. Check-out endpoint có **cùng bug**: dùng `"virtual-gate-out"` thay vì `"virtual-anpr-exit"`.
> 3. Fix rất đơn giản: thay `_virtual_cam_id` trong esp32.py (2 chỗ) từ gate camera sang ANPR camera, hoặc thử ANPR trước rồi fallback gate.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File | Mục đích | Relevance | Có thể tái dụng? |
|------|----------|-----------|-------------------|
| `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | ESP32 check-in/check-out endpoints | **HIGH** | Yes — chỉ cần sửa camera ID |
| `backend-microservices/ai-service-fastapi/app/routers/camera.py` | Nhận frame từ Unity, serve snapshot/stream | HIGH | Yes — buffer `_virtual_frame_buffer` đã hoạt động |
| `backend-microservices/ai-service-fastapi/app/engine/plate_pipeline.py` | YOLO detect + OCR pipeline | HIGH | Yes — pipeline hoạt động tốt khi ảnh đủ rõ |
| `backend-microservices/ai-service-fastapi/app/engine/camera_capture.py` | Capture frame từ RTSP/HTTP camera | Medium | Yes — fallback khi virtual camera offline |
| `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraManager.cs` | Define virtual camera configs (position, FOV) | HIGH | Reference — camera configs |
| `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraStreamer.cs` | Stream JPEG frames to AI service | HIGH | Yes — streaming đã hoạt động |
| `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs` | POST frame to `/ai/cameras/frame` endpoint | Medium | Yes — đã hoạt động |
| `ParkingSimulatorUnity/Assets/Scripts/Core/ParkingManager.cs` | Unity-side check-in flow | Medium | Reference — sử dụng ANPR camera đúng |

### 2.2 Luồng Code Chi Tiết: ESP32 Check-in

```
POST /ai/parking/esp32/check-in/
│
├── Step 1: Parse QR data (esp32.py:700-738)
│   ├── payload.qr_data provided → parse JSON → extract booking_id, user_id
│   └── No qr_data → return FAILED "Thiếu QR data"
│
├── Step 2: Fetch & validate booking (esp32.py:741-805)
│   ├── GET booking from booking-service
│   ├── Validate check_in_status == "not_checked_in"
│   ├── Validate time window (allow 15 min early)
│   └── Check payment for online bookings
│
├── Step 3: Capture plate image (esp32.py:808-845)  ★ BUG HERE ★
│   ├── _virtual_cam_id = "virtual-gate-in"          ← WRONG CAMERA
│   ├── Check _virtual_frame_buffer["virtual-gate-in"]
│   │   ├── Found & fresh → use as plate_image_bytes, plate_from_real_camera=True
│   │   └── Not found → fallback RTSP → fallback static test image
│   └── Save plate image to disk
│
├── Step 4: OCR plate & compare (esp32.py:848-909)
│   ├── pipeline.process(plate_image_bytes) → YOLO detect + OCR
│   ├── Decision NOT_FOUND/BLURRY + plate_from_real_camera=True
│   │   → return "Không đọc được biển số xe"          ← THIS IS THE ERROR USER SEES
│   ├── Decision SUCCESS → compare OCR plate vs booking plate
│   │   └── Mismatch → return "Biển số không khớp!"
│   └── Test image → skip plate verification
│
└── Step 5: Call booking-service checkin (esp32.py:912-950)
    └── Return barrier_action="open"
```

### 2.3 **ROOT CAUSE: Camera ID Mismatch**

**ESP32 check-in** (`esp32.py` line 812):
```python
_virtual_cam_id = "virtual-gate-in"  # ← WRONG: wide overview camera
```

**ESP32 check-out** (`esp32.py` line 1118):
```python
_virtual_cam_id = "virtual-gate-out"  # ← WRONG: wide overview camera
```

**Unity camera configs** (`VirtualCameraManager.cs` lines 91-118):

| Camera ID | Purpose | Position | FOV | Designed For |
|-----------|---------|----------|-----|--------------|
| `virtual-gate-in` | Entry gate overview | (36, 3.5, -4) | **55°** wide | General monitoring |
| `virtual-anpr-entry` | **ANPR plate reader** | (43.5, 1.0, 0) | **35°** narrow | **Plate reading — plate fills ~42% of frame** |
| `virtual-gate-out` | Exit gate overview | (-36, 3.5, -4) | **55°** wide | General monitoring |
| `virtual-anpr-exit` | **ANPR plate reader** | (-42, 0.4, 0) | **25°** narrow | **Plate reading** |

**Contrast with Unity's ParkingManager** (`ParkingManager.cs` lines 375-376):
```csharp
// Unity CORRECTLY uses ANPR camera first, gate camera as fallback
var streamer = virtualCameraManager?.GetStreamer("virtual-anpr-entry")
            ?? virtualCameraManager?.GetStreamer("virtual-gate-in");
```

### 2.4 Frame Streaming Flow (hoạt động đúng)

```
Unity VirtualCameraStreamer                AI Service
─────────────────────────                  ──────────
CaptureLoop() @ 5fps                      
  ├── CaptureFrame() → JPEG bytes
  └── SendFrame(jpeg)
        ├── POST /ai/cameras/frame
        │   Headers:
        │     Content-Type: image/jpeg
        │     X-Camera-ID: "virtual-anpr-entry"  (or gate-in, etc.)
        │     X-Gateway-Secret: <secret>
        │                                     camera.py receive_frame()
        │                                       ├── Validate secret & camera ID
        │                                       └── Store in _virtual_frame_buffer[camera_id]
        │
        └── Repeat every 200ms (5fps)
```

**Key point**: Both `virtual-gate-in` AND `virtual-anpr-entry` are streaming frames to the AI service. The buffer has frames from both cameras. The ESP32 endpoint just reads from the wrong one.

### 2.5 Plate Pipeline Process

```
plate_pipeline.process(image_bytes)
│
├── cv2.imdecode(image_bytes) → BGR numpy array
├── Stage 1: YOLO detect plate region (conf_threshold=0.20)
│   ├── Found → crop plate region
│   └── NOT found → return PlateReadDecision.NOT_FOUND  ← Happens with gate-in camera
├── Stage 2: OCR read text (TrOCR → EasyOCR → Tesseract)
├── Stage 3: Format validation & normalization
└── Return PlatePipelineResult
```

With `virtual-gate-in` (FOV 55°), the plate is too small for YOLO to detect at `conf_threshold=0.20` → `NOT_FOUND`.
With `virtual-anpr-entry` (FOV 35°, plate fills 42% of frame) → YOLO detect succeeds → OCR reads plate → `SUCCESS`.

---

## 3. Camera Endpoint Reference

### `/ai/cameras/frame` — Receive frame from Unity (POST)
- Source: `camera.py` line 210
- Stores frame in `_virtual_frame_buffer[camera_id]`
- Valid camera IDs: `virtual-f1-overview`, `virtual-gate-in`, `virtual-gate-out`, `virtual-zone-south`, `virtual-zone-north`, `virtual-anpr-entry`, `virtual-anpr-exit`, etc.

### `/ai/cameras/read-plate` — Read plate from virtual camera (GET)
- Source: `camera.py` line 310
- Param: `camera_id` (e.g. `virtual-anpr-entry`)
- Reads latest frame from buffer → runs plate pipeline → returns plate text
- **This endpoint works correctly** when called with the right camera ID

### `/ai/cameras/snapshot` — Get latest frame as JPEG (GET)
- Source: `camera.py` line 237
- For virtual cameras: returns from `_virtual_frame_buffer`

---

## 4. ⚠️ Gotchas & Known Issues

- [x] **[ROOT CAUSE]** ESP32 check-in reads `"virtual-gate-in"` instead of `"virtual-anpr-entry"` — plate too small in wide-angle view → YOLO NOT_FOUND → `plateText: null`
- [x] **[SAME BUG]** ESP32 check-out reads `"virtual-gate-out"` instead of `"virtual-anpr-exit"`
- [ ] **[NOTE]** `SlotOccupancyDetector.cs` line ~377: "AI endpoint not yet connected" — AI slot detection snapshots are captured but not sent to any endpoint (TODO placeholder)
- [ ] **[NOTE]** Stale threshold is 30s (`_STALE_THRESHOLD = 30`) — if Unity camera is slow or stopped, the AI service will fall back to RTSP/test images

---

## 5. Fix Recommendations

### Fix 1: ESP32 check-in — Change camera ID (esp32.py line 812)

**Before:**
```python
_virtual_cam_id = "virtual-gate-in"
```

**After (recommended — ANPR first, gate fallback):**
```python
# Try ANPR camera first (optimized for plate reading, FOV 35°)
# Fall back to gate overview camera if ANPR not available
_virtual_cam_id = "virtual-anpr-entry"
_fallback_cam_id = "virtual-gate-in"
plate_image_bytes: bytes | None = None
plate_from_real_camera = False

with _buffer_lock:
    _vf = _virtual_frame_buffer.get(_virtual_cam_id)
    if not _vf or (time.monotonic() - _vf.timestamp) >= _STALE_THRESHOLD:
        _vf = _virtual_frame_buffer.get(_fallback_cam_id)
```

### Fix 2: ESP32 check-out — Change camera ID (esp32.py line 1118)

**Before:**
```python
_virtual_cam_id = "virtual-gate-out"
```

**After:**
```python
_virtual_cam_id = "virtual-anpr-exit"
_fallback_cam_id = "virtual-gate-out"
# (same pattern as check-in)
```

### Fix Files & Lines

| File | Line | Change |
|------|------|--------|
| `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | 812 | `"virtual-gate-in"` → `"virtual-anpr-entry"` (+ fallback) |
| `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | 1118 | `"virtual-gate-out"` → `"virtual-anpr-exit"` (+ fallback) |

---

## 6. Checklist cho Implementer

- [ ] Sửa `_virtual_cam_id` check-in: `"virtual-gate-in"` → `"virtual-anpr-entry"` (line 812)
- [ ] Sửa `_virtual_cam_id` check-out: `"virtual-gate-out"` → `"virtual-anpr-exit"` (line 1118)
- [ ] Thêm fallback logic: try ANPR camera → try gate camera → try RTSP → test image
- [ ] Không cần install thêm packages
- [ ] Không cần env vars mới
- [ ] Không cần migration
- [ ] Pattern reference: dùng `ParkingManager.cs:375-376` làm mẫu fallback (Unity đã làm đúng)
- [ ] Test: gọi `GET /ai/cameras/read-plate?camera_id=virtual-anpr-entry` trước để verify pipeline hoạt động với ANPR camera

---

## 7. Nguồn

| # | File | Mô tả | Lines |
|---|------|-------|-------|
| 1 | `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | ESP32 check-in handler | 700-950 |
| 2 | `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | ESP32 check-out handler | 1100-1150 |
| 3 | `backend-microservices/ai-service-fastapi/app/routers/camera.py` | Frame receive + virtual buffer | 210-330 |
| 4 | `backend-microservices/ai-service-fastapi/app/engine/plate_pipeline.py` | YOLO detect + OCR | 1-100 |
| 5 | `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraManager.cs` | Camera configs | 70-140 |
| 6 | `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraStreamer.cs` | Frame streaming to AI | Full |
| 7 | `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs` | PostCameraFrame() | 452-470 |
| 8 | `ParkingSimulatorUnity/Assets/Scripts/Core/ParkingManager.cs` | CheckInWithANPR (correct usage) | 370-410 |
