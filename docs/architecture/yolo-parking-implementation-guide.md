# Implementation Guide — YOLO11n Parking Slot Occupancy Detection

**ADR:** `docs/architecture/adr-004-yolo11n-parking-occupancy.md`  
**Service:** `backend-microservices/ai-service-fastapi`

---

## Dependency Order (implement theo thứ tự này)

```
1. app/config.py                          — 3 config keys mới
2. app/engine/slot_detection.py           — YOLO logic + IoU
3. app/schemas/ai.py                      — 2 schema mới cho endpoint
4. app/routers/parking.py                 — 1 endpoint mới
5. app/main.py                            — pre-warm detector trong lifespan
```

---

## 1. `app/config.py` — Thêm 3 keys

```python
YOLO_PARKING_MODEL_PATH: str = "/app/ml/models/yolo11n.pt"
YOLO_PARKING_IOU_THRESHOLD: float = 0.15
YOLO_PARKING_CONF_THRESHOLD: float = 0.25
```

**Ghi chú:** `yolo11n.pt` sẽ được auto-download bởi ultralytics nếu đường dẫn không tồn tại và tên file là chuẩn ultralytics model name. Nếu muốn control download location, set `YOLO_PARKING_MODEL_PATH = "yolo11n.pt"` để ultralytics tự quản lý trong `~/.config/Ultralytics/`.

---

## 2. `app/engine/slot_detection.py` — Thay đổi cụ thể

### 2a. Thêm constant ở đầu file (sau imports)

```python
# COCO class IDs cho vehicle detection
VEHICLE_CLASS_IDS: frozenset[int] = frozenset({2, 3, 5, 7})
# 2=car, 3=motorcycle, 5=bus, 7=truck
```

### 2b. Sửa `SlotDetector.__init__`

Thêm `yolo_model_path: Optional[str] = None` parameter:

```python
def __init__(
    self,
    occupancy_threshold: float = 0.15,
    min_contour_area_ratio: float = 0.25,
    yolo_model_path: Optional[str] = None,
) -> None:
    self._occupancy_threshold = occupancy_threshold
    self._min_contour_area_ratio = min_contour_area_ratio
    self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=500, varThreshold=50, detectShadows=True
    )
    self._yolo_model = None
    self._iou_threshold: float = 0.15
    self._yolo_conf_threshold: float = 0.25
    if yolo_model_path:
        self._load_yolo(yolo_model_path)
```

### 2c. Thêm method `_load_yolo`

```python
def _load_yolo(self, model_path: str) -> None:
    """Load YOLO11n model. ultralytics auto-downloads if model_path is a known name."""
    try:
        from ultralytics import YOLO
        self._yolo_model = YOLO(model_path)
        # Warm-up với dummy inference để tránh slow first request
        import numpy as np as _np
        dummy = _np.zeros((64, 64, 3), dtype=_np.uint8)
        self._yolo_model(dummy, verbose=False)
        logger.info("YOLO11n parking model loaded from %s", model_path)
    except Exception as exc:
        logger.warning(
            "YOLO11n model unavailable (%s) — falling back to OpenCV detection", exc
        )
        self._yolo_model = None
```

**Lưu ý:** warm-up chạy trong `__init__` nên chỉ xảy ra 1 lần khi singleton tạo.

### 2d. Sửa `detect_occupancy` — try YOLO first

```python
def detect_occupancy(
    self,
    frame: np.ndarray,
    slots: list[SlotBbox],
    camera_id: str = "unknown",
) -> FrameDetectionResult:
    if self._yolo_model is not None:
        try:
            return self._detect_with_yolo(frame, slots, camera_id)
        except Exception as exc:
            logger.warning(
                "YOLO detection failed for camera %s, falling back to OpenCV: %s",
                camera_id, exc,
            )
    # Original OpenCV flow (unchanged)
    t0 = time.time()
    # ... rest of existing code unchanged ...
```

### 2e. Thêm method `_detect_with_yolo`

```python
def _detect_with_yolo(
    self,
    frame: np.ndarray,
    slots: list[SlotBbox],
    camera_id: str,
) -> FrameDetectionResult:
    """Run YOLO11n on full frame, IoU-match detections to slot boxes."""
    t0 = time.time()
    h, w = frame.shape[:2]

    # Single YOLO inference on entire frame
    yolo_results = self._yolo_model(
        frame, verbose=False, conf=self._yolo_conf_threshold
    )

    # Collect vehicle detections (filter by COCO vehicle class IDs)
    vehicles: list[tuple[int, int, int, int, float]] = []  # x1,y1,x2,y2,conf
    for r in yolo_results:
        for box in r.boxes:
            if int(box.cls[0]) not in VEHICLE_CLASS_IDS:
                continue
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            vehicles.append((
                max(0, x1), max(0, y1), min(w, x2), min(h, y2), conf
            ))

    # IoU matching per slot
    slot_results: list[SlotDetectionResult] = []
    for slot in slots:
        best_iou = 0.0
        best_conf = 0.0
        for vx1, vy1, vx2, vy2, vconf in vehicles:
            iou = self._compute_iou(slot, vx1, vy1, vx2, vy2)
            if iou > best_iou:
                best_iou = iou
                best_conf = vconf

        is_occupied = best_iou >= self._iou_threshold
        if is_occupied:
            status = SlotStatus.OCCUPIED
            confidence = round(best_conf, 3)
        else:
            # Confidence that slot is available: inversely proportional to IoU
            confidence = round(max(0.5, 1.0 - best_iou), 3)
            status = SlotStatus.AVAILABLE

        slot_results.append(SlotDetectionResult(
            slot_id=slot.slot_id,
            slot_code=slot.slot_code,
            zone_id=slot.zone_id,
            status=status,
            confidence=confidence,
            method="yolo11n_iou",
            processing_time_ms=0.0,
        ))

    total_time = (time.time() - t0) * 1000
    available = sum(1 for r in slot_results if r.status == SlotStatus.AVAILABLE)
    occupied = sum(1 for r in slot_results if r.status == SlotStatus.OCCUPIED)

    logger.info(
        "YOLO frame detection camera %s: %d vehicles found, %d slots "
        "(%d available, %d occupied) in %.1fms",
        camera_id, len(vehicles), len(slot_results), available, occupied, total_time,
    )

    return FrameDetectionResult(
        camera_id=camera_id,
        slots=slot_results,
        total_available=available,
        total_occupied=occupied,
        processing_time_ms=total_time,
    )
```

### 2f. Thêm static method `_compute_iou`

```python
@staticmethod
def _compute_iou(
    slot: SlotBbox, vx1: int, vy1: int, vx2: int, vy2: int
) -> float:
    """Compute IoU between a slot bbox and a vehicle bbox."""
    ix1 = max(slot.x1, vx1)
    iy1 = max(slot.y1, vy1)
    ix2 = min(slot.x2, vx2)
    iy2 = min(slot.y2, vy2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    slot_area = (slot.x2 - slot.x1) * (slot.y2 - slot.y1)
    veh_area = (vx2 - vx1) * (vy2 - vy1)
    union = slot_area + veh_area - inter
    return inter / union if union > 0 else 0.0
```

### 2g. Sửa `get_slot_detector` — thêm `yolo_model_path`

```python
def get_slot_detector(
    occupancy_threshold: float = 0.15,
    min_contour_area_ratio: float = 0.25,
    yolo_model_path: Optional[str] = None,
) -> SlotDetector:
    global _slot_detector
    if _slot_detector is None:
        _slot_detector = SlotDetector(
            occupancy_threshold=occupancy_threshold,
            min_contour_area_ratio=min_contour_area_ratio,
            yolo_model_path=yolo_model_path,
        )
    return _slot_detector
```

**QUAN TRỌNG:** Singleton chỉ nhận `yolo_model_path` khi **tạo lần đầu**. Lần gọi sau trả về instance đã có. Vì vậy phải pre-initialize trong `main.py` lifespan TRƯỚC camera_monitor.

---

## 3. `app/schemas/ai.py` — Thêm 2 schema

```python
class SlotOccupancyResult(CamelModel):
    slot_id: str
    slot_code: str
    zone_id: str
    status: str          # "available" | "occupied" | "unknown"
    confidence: float    # 0.0 – 1.0
    method: str          # "yolo11n_iou" | "edge_contour_color" | "error"


class OccupancyDetectionResponse(CamelModel):
    camera_id: str
    total_slots: int
    total_available: int
    total_occupied: int
    detection_method: str          # "yolo11n" | "opencv_fallback"
    processing_time_ms: float
    slots: list[SlotOccupancyResult]
```

---

## 4. `app/routers/parking.py` — Thêm 1 endpoint

Import thêm ở đầu file:

```python
import json as _json
import cv2
import numpy as np
from app.engine.slot_detection import get_slot_detector, SlotBbox
from app.schemas.ai import OccupancyDetectionResponse, SlotOccupancyResult
```

Thêm endpoint mới (sau `/scan-plate/`):

```python
@router.post(
    "/detect-occupancy/",
    response_model=OccupancyDetectionResponse,
    summary="Detect vehicle occupancy for parking slots in a camera frame",
)
async def detect_occupancy(
    image: UploadFile = File(..., description="Camera frame (JPEG/PNG)"),
    camera_id: str = Form(..., description="Camera UUID"),
    slots: str = Form(
        ...,
        description=(
            'JSON array of slot bboxes: '
            '[{"slot_id":"...","slot_code":"A1","zone_id":"...","x1":0,"y1":0,"x2":100,"y2":100}]'
        ),
    ),
):
    # Parse slots JSON
    try:
        slots_data: list[dict] = _json.loads(slots)
        if not isinstance(slots_data, list):
            raise ValueError("slots must be a JSON array")
    except (ValueError, _json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid slots JSON: {exc}")

    slot_bboxes: list[SlotBbox] = []
    for i, s in enumerate(slots_data):
        try:
            slot_bboxes.append(SlotBbox(
                slot_id=str(s["slot_id"]),
                slot_code=str(s["slot_code"]),
                zone_id=str(s["zone_id"]),
                x1=int(s["x1"]),
                y1=int(s["y1"]),
                x2=int(s["x2"]),
                y2=int(s["y2"]),
            ))
        except (KeyError, ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid slot at index {i}: {exc}",
            )

    # Decode image
    contents = await image.read()
    img_array = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail="Cannot decode image")

    # Run detection
    detector = get_slot_detector(yolo_model_path=settings.YOLO_PARKING_MODEL_PATH)
    result = detector.detect_occupancy(frame, slot_bboxes, camera_id=camera_id)

    # Determine which method was actually used
    method_used = "opencv_fallback"
    if result.slots and result.slots[0].method == "yolo11n_iou":
        method_used = "yolo11n"

    return OccupancyDetectionResponse(
        camera_id=result.camera_id,
        total_slots=len(result.slots),
        total_available=result.total_available,
        total_occupied=result.total_occupied,
        detection_method=method_used,
        processing_time_ms=round(result.processing_time_ms, 1),
        slots=[
            SlotOccupancyResult(
                slot_id=s.slot_id,
                slot_code=s.slot_code,
                zone_id=s.zone_id,
                status=s.status.value,
                confidence=s.confidence,
                method=s.method,
            )
            for s in result.slots
        ],
    )
```

---

## 5. `app/main.py` — Pre-warm detector trong lifespan

Thêm import:

```python
from app.engine.slot_detection import get_slot_detector
```

Thay đổi trong `lifespan`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Service starting up...")
    seed_default_devices()
    # Pre-load YOLO slot detector BEFORE camera monitor starts
    # This triggers model download (if needed) and warm-up inference at startup
    get_slot_detector(yolo_model_path=settings.YOLO_PARKING_MODEL_PATH)
    await start_camera_monitor()
    yield
    logger.info("AI Service shutting down...")
    await stop_camera_monitor()
```

---

## Error Scenarios

| Scenario | Behavior | HTTP Status |
|----------|----------|-------------|
| `slots` không phải JSON array | HTTPException | 400 |
| Slot thiếu field `x1`/`y1`/`x2`/`y2` | HTTPException | 400 |
| Image không decode được | HTTPException | 422 |
| YOLO model chưa có | Tự fallback OpenCV, không lỗi | 200 (method=opencv_fallback) |
| YOLO inference crash | Tự fallback OpenCV, log WARNING | 200 (method=opencv_fallback) |

---

## Business Rules

- Camera monitor tiếp tục hoạt động tự động (không thay đổi flow)
- Endpoint `/detect-occupancy/` chỉ dùng cho: on-demand detection từ client / operator dashboard
- `confidence < 0.6` vẫn bị filter bởi `_push_slot_updates` trong camera_monitor (unchanged)
- `status=unknown` bị skip bởi camera_monitor (unchanged)

---

## Test Pattern Reference

Xem `tests/` directory trong cùng service để follow AAA pattern.

Test cần cover:
- `test_compute_iou`: overlap 0%, 50%, 100% cases
- `test_detect_with_yolo_fallback`: khi `_yolo_model=None` → method=`edge_contour_color`
- `test_detect_occupancy_endpoint`: mock `get_slot_detector`, verify response schema
