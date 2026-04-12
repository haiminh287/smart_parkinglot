# Research Report: Unity Camera → AI Detection Full Flow

**Date:** 2026-04-05 | **Type:** Mixed (Codebase analysis)

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **detect-occupancy endpoint** nhận multipart form: `image` (JPEG file), `camera_id` (string), `slots` (JSON array với bbox pixel coords) — yêu cầu `X-Gateway-Secret` header qua middleware
> 2. **6 virtual cameras** trong Unity gửi JPEG frames qua `POST /ai/cameras/frame` với headers `X-Camera-ID` + `X-Gateway-Secret` — default resolution 640×480 @ 75% JPEG quality @ 5 FPS
> 3. **Floor 1 (B1)** có 72 car slots (V1-01..V1-72) + 20 moto (V2) + 5 garage (G). **Floor 2** có 36 car (A-01..A-18 + B-01..B-18) + 20 moto (C) + 5 garage (G)

---

## 2. OccupancyDetectionResponse Schema

Source: `ai-service-fastapi/app/schemas/ai.py`

### OccupancyDetectionResponse (top-level)

| Field                | Type                        | Description                        |
| -------------------- | --------------------------- | ---------------------------------- |
| `camera_id`          | `str`                       | Camera that produced the frame     |
| `total_slots`        | `int`                       | Total slots analyzed               |
| `total_available`    | `int`                       | Count of available slots           |
| `total_occupied`     | `int`                       | Count of occupied slots            |
| `detection_method`   | `str`                       | `"yolo11n"` or `"opencv_fallback"` |
| `processing_time_ms` | `float`                     | Processing time in milliseconds    |
| `slots`              | `list[SlotOccupancyResult]` | Per-slot detection results         |

### SlotOccupancyResult (per slot)

| Field        | Type    | Description                                          |
| ------------ | ------- | ---------------------------------------------------- |
| `slot_id`    | `str`   | Unique slot identifier                               |
| `slot_code`  | `str`   | Human-readable code (e.g. "V1-01", "A-03")           |
| `zone_id`    | `str`   | Zone identifier                                      |
| `status`     | `str`   | `"available"` / `"occupied"` / `"unknown"`           |
| `confidence` | `float` | 0.0 – 1.0                                            |
| `method`     | `str`   | `"yolo11n_iou"` / `"edge_contour_color"` / `"error"` |

**Note:** Schema uses `CamelModel` base → JSON response keys are camelCase (e.g. `cameraId`, `totalSlots`, `slotCode`).

---

## 3. How to Call POST /ai/parking/detect-occupancy/

### Endpoint

```
POST http://localhost:8009/ai/parking/detect-occupancy/
```

### Auth (GatewayAuthMiddleware)

Path `/ai/parking/detect-occupancy/` is NOT exempt → requires gateway secret header.

```
X-Gateway-Secret: gateway-internal-secret-key
```

Optional user context headers (set by middleware on `request.state`):

```
X-User-ID: <user-id>
X-User-Email: <email>
X-User-Role: <role>
```

### Form Data (multipart/form-data)

| Field       | Type         | Required | Description                                      |
| ----------- | ------------ | -------- | ------------------------------------------------ |
| `image`     | `UploadFile` | Yes      | JPEG image file from camera                      |
| `camera_id` | `str` (Form) | Yes      | Camera identifier (e.g. `"virtual-f1-overview"`) |
| `slots`     | `str` (Form) | Yes      | JSON-encoded array of slot bboxes                |

### Slots JSON Format

```json
[
  {
    "slot_id": "slot-uuid-or-id",
    "slot_code": "V1-01",
    "zone_id": "zone-v1",
    "x1": 0,
    "y1": 0,
    "x2": 100,
    "y2": 100
  }
]
```

**Fields**: `slot_id`, `slot_code`, `zone_id` (all strings), `x1`, `y1`, `x2`, `y2` (all ints — pixel coordinates in the image).

### Example Call (Python httpx)

```python
import json, httpx

headers = {
    "X-Gateway-Secret": "gateway-internal-secret-key",
    "X-User-ID": "test-user",
}

slots = json.dumps([
    {"slot_id": "s1", "slot_code": "A1", "zone_id": "z1",
     "x1": 0, "y1": 0, "x2": 100, "y2": 100},
])

with open("test_annotated.jpg", "rb") as f:
    files = {"image": ("frame.jpg", f, "image/jpeg")}
    data = {"camera_id": "virtual-f1-overview", "slots": slots}
    r = httpx.post("http://localhost:8009/ai/parking/detect-occupancy/",
                   headers=headers, files=files, data=data)
print(r.json())
```

### Example Call (curl)

```bash
curl -X POST http://localhost:8009/ai/parking/detect-occupancy/ \
  -H "X-Gateway-Secret: gateway-internal-secret-key" \
  -F "image=@test_annotated.jpg" \
  -F "camera_id=virtual-f1-overview" \
  -F 'slots=[{"slot_id":"s1","slot_code":"A1","zone_id":"z1","x1":0,"y1":0,"x2":100,"y2":100}]'
```

---

## 4. How to Call POST /ai/cameras/frame

### Endpoint

```
POST http://localhost:8009/ai/cameras/frame
```

### Headers (all required)

| Header             | Value                         | Description       |
| ------------------ | ----------------------------- | ----------------- |
| `X-Camera-ID`      | One of 6 valid virtual IDs    | Camera identifier |
| `X-Gateway-Secret` | `gateway-internal-secret-key` | Auth secret       |

**Note:** Path `/ai/cameras/` is EXEMPT from GatewayAuthMiddleware. However the `/frame` endpoint checks `X-Gateway-Secret` explicitly in code (line 167).

### Body

Raw JPEG bytes (application/octet-stream). Max 500KB.

### Valid Camera IDs

```
virtual-f1-overview
virtual-f2-overview
virtual-gate-in
virtual-gate-out
virtual-zone-south
virtual-zone-north
```

### Response

```json
{ "success": true, "camera_id": "virtual-f1-overview", "size": 12345 }
```

### Frame Retrieval

Frames stored in `_virtual_frame_buffer` dict. Get via:

```
GET /ai/cameras/snapshot?camera_id=virtual-f1-overview
```

Returns JPEG image or 503 if stale/missing.

---

## 5. Virtual Camera Configuration (Unity Side)

Source: `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraManager.cs` + `ApiConfig.cs`

### Default Resolution

```
Width:  640 px
Height: 480 px
JPEG Quality: 75
Capture FPS: 5
```

### 6 Camera Configs

| Camera ID             | Display Name       | Position     | Rotation     | FOV | Purpose                                            |
| --------------------- | ------------------ | ------------ | ------------ | --- | -------------------------------------------------- |
| `virtual-f1-overview` | Floor 1 Overview   | (0, 35, 0)   | (90, 0, 0)   | 80° | Top-down Floor 1 (B1)                              |
| `virtual-f2-overview` | Floor 2 Overview   | (0, 38.5, 0) | (90, 0, 0)   | 80° | Top-down Floor 2                                   |
| `virtual-gate-in`     | Entry Gate         | (33, 4, 2)   | (15, -90, 0) | 60° | Watches entry gate for check-in                    |
| `virtual-gate-out`    | Exit Gate          | (-33, 4, 2)  | (15, 90, 0)  | 60° | Watches exit gate for check-out                    |
| `virtual-zone-south`  | South Zone Monitor | (0, 20, -25) | (50, 0, 0)   | 65° | Angled view: south rows V1-01..V1-18, V1-37..V1-54 |
| `virtual-zone-north`  | North Zone Monitor | (0, 20, 25)  | (50, 180, 0) | 65° | Angled view: north rows V1-19..V1-36, V1-55..V1-72 |

**Note:** Overview cameras are straight-down (90° X rotation). Zone cameras are angled at 50°. Gate cameras are near-level (15°).

---

## 6. Parking Lot Slot Layout

Source: `ParkingSimulatorUnity/Assets/Scripts/Parking/ParkingLotGenerator.cs`

### Configuration Constants

- **Floors:** 2
- **Floor height:** 3.5m
- **Painted slots per row:** 18
- **Painted rows per floor:** 2 (inner rows) + 2 more outer rows on Floor 0 only
- **Slot size:** 2.5m × 5m (car), 3m × 6m (garage), 1m × 2m (moto)
- **Lane width:** 6m
- **Platform:** 70m × 60m

### Floor 0 (DB Zone: B1)

| Slot Range     | Zone | Row | Count | Z Position            | Description               |
| -------------- | ---- | --- | ----- | --------------------- | ------------------------- |
| V1-01 .. V1-18 | V1   | 1   | 18    | ≈ -5.5 (south inner)  | Inner south row           |
| V1-19 .. V1-36 | V1   | 2   | 18    | ≈ +5.5 (north inner)  | Inner north row           |
| V1-37 .. V1-54 | V1   | 3   | 18    | ≈ -16.5 (south outer) | Outer south row           |
| V1-55 .. V1-72 | V1   | 4   | 18    | ≈ +16.5 (north outer) | Outer north row           |
| V2-01 .. V2-20 | V2   | —   | 20    | NE corner             | Motorbike zone            |
| G-01 .. G-05   | —    | —   | 5     | South edge            | Garage slots (no DB zone) |

**Total Floor 0:** 72 car + 20 moto + 5 garage = **97 slots**

### Floor 1 (DB Zone: Tầng 1)

| Slot Range   | Zone | Row | Count | Z Position |
| ------------ | ---- | --- | ----- | ---------- |
| A-01 .. A-18 | A    | 1   | 18    | ≈ -5.5     |
| B-01 .. B-18 | B    | 2   | 18    | ≈ +5.5     |
| C-01 .. C-20 | C    | —   | 20    | NE corner  |
| G-06 .. G-10 | —    | —   | 5     | South edge |

**Total Floor 1:** 36 car + 20 moto + 5 garage = **61 slots**

### Slot X Positions

All car slots start at `x = -platformWidth/2 + 8 = -27m`, spaced `2.5m` apart:

```
x[i] = -27 + i * 2.5   for i in 0..17
→ x ranges from -27.0 to +15.5
```

### Camera-to-Slot Mapping (comments in code)

- `virtual-zone-south` monitors: V1-01..V1-18, V1-37..V1-54 (south-facing rows)
- `virtual-zone-north` monitors: V1-19..V1-36, V1-55..V1-72 (north-facing rows)
- Overview cameras see entire floor

---

## 7. Existing Test Scripts & Images

### Test Scripts

| File                                         | Purpose                                                                                                                                  |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `ai-service-fastapi/qa_probe_occupancy.py`   | ASGI-transport test of detect-occupancy: tests missing fields, invalid JSON, valid form. Uses `test_annotated.jpg` or minimal JPEG stub. |
| `ai-service-fastapi/test_banknote_camera.py` | Banknote camera testing (unrelated)                                                                                                      |
| `backend-microservices/test_ai_full.py`      | Full AI service E2E tests                                                                                                                |

### Test Images

| File                     | Location                                                                   |
| ------------------------ | -------------------------------------------------------------------------- |
| `test_annotated.jpg`     | `ai-service-fastapi/` — parking lot annotated image (usable for occupancy) |
| `test_plate_crop.jpg`    | `ai-service-fastapi/` — license plate crop                                 |
| `test_plate_crop_4x.jpg` | `ai-service-fastapi/` — 4× upscaled plate crop                             |
| `test_crop_expanded.jpg` | `ai-service-fastapi/` — expanded crop                                      |

---

## 8. Detection Pipeline Details

Source: `ai-service-fastapi/app/engine/slot_detection.py`

### SlotBbox Dataclass

```python
@dataclass
class SlotBbox:
    slot_id: str
    slot_code: str
    zone_id: str
    x1: int  # pixel coordinates in camera frame
    y1: int
    x2: int
    y2: int
```

### Detection Methods (priority order)

1. **YOLO11n** — object detection for vehicle classes (COCO IDs: 2=car, 3=motorcycle, 5=bus, 7=truck)
2. **OpenCV fallback** — edge/contour + color analysis

### Key Constants

```python
VEHICLE_CLASS_IDS = frozenset({2, 3, 5, 7})  # car, motorcycle, bus, truck
```

---

## 9. Checklist cho Test Script Implementer

- [ ] **Gateway secret:** `gateway-internal-secret-key` (from task env vars)
- [ ] **Test image:** Use `ai-service-fastapi/test_annotated.jpg` (exists)
- [ ] **Slot bbox pixel coords** must be within image dimensions (640×480 if Unity frame)
- [ ] **detect-occupancy** requires multipart form data (not JSON body)
- [ ] **cameras/frame** requires raw JPEG bytes body with `X-Camera-ID` header
- [ ] **Valid camera IDs:** `virtual-f1-overview`, `virtual-f2-overview`, `virtual-gate-in`, `virtual-gate-out`, `virtual-zone-south`, `virtual-zone-north`
- [ ] **Max frame size:** 500KB per frame for `/cameras/frame`
- [ ] Response uses camelCase keys (CamelModel base)

---

## 10. Nguồn

| #   | File                                                                  | Mô tả                                    |
| --- | --------------------------------------------------------------------- | ---------------------------------------- |
| 1   | `ai-service-fastapi/app/schemas/ai.py`                                | Response schemas                         |
| 2   | `ai-service-fastapi/app/routers/parking.py:479-530`                   | detect-occupancy endpoint                |
| 3   | `ai-service-fastapi/app/routers/camera.py:80-200`                     | cameras/frame endpoint + VIRTUAL_CAMERAS |
| 4   | `ai-service-fastapi/app/middleware/gateway_auth.py`                   | Auth middleware + exempt paths           |
| 5   | `ai-service-fastapi/app/engine/slot_detection.py:1-60`                | SlotBbox + detection pipeline            |
| 6   | `ai-service-fastapi/qa_probe_occupancy.py`                            | Existing QA probe script                 |
| 7   | `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraManager.cs` | Camera configs                           |
| 8   | `ParkingSimulatorUnity/Assets/Scripts/API/ApiConfig.cs:36-39`         | Default resolution settings              |
| 9   | `ParkingSimulatorUnity/Assets/Scripts/Parking/ParkingLotGenerator.cs` | Slot layout generation                   |
