# Research Report: Parking Slot Occupancy Detection Model

**Task:** ISSUE-AI-PARKING | **Date:** 2026-03-16 | **Type:** Mixed (Codebase + Library + Tech Eval)

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Repo đã có `slot_detection.py` đang chạy** — dùng OpenCV thuần (edge density + contour + color variance), KHÔNG có ML model. Đây là component cần upgrade.
> 2. **`ultralytics==8.4.18` đã install** kèm `parking_management.py` có sẵn trong venv — zero new dependencies, chỉ cần thêm logic YOLO vào `SlotDetector` hiện tại.
> 3. **Recommended model: YOLO11n (pretrained COCO)** — detect car/truck/bus/motorcycle (class 2/3/5/7), auto-download 6MB weights, ~30ms/frame CPU, pattern 100% consistent với codebase (banknote + license plate đều dùng YOLO).

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File | Mục đích | Relevance | Có thể tái dụng? |
|------|----------|-----------|-----------------|
| `ai-service-fastapi/app/engine/slot_detection.py` | Detect occupancy từ frame camera | **HIGH** | **Yes** — upgrade để thêm YOLO layer |
| `ai-service-fastapi/app/engine/camera_monitor.py` | Background worker poll camera 30s, gọi slot_detector | **HIGH** | Yes — không cần sửa |
| `ai-service-fastapi/app/engine/camera_capture.py` | Capture frame từ MJPEG/RTSP/HTTP | HIGH | Yes — không cần sửa |
| `ai-service-fastapi/app/engine/detector.py` | BanknoteDetector dùng YOLO (pattern mẫu) | HIGH | Yes — copy pattern YOLO loading |
| `ai-service-fastapi/app/engine/plate_detector.py` | LicensePlateDetector dùng YOLO (pattern mẫu) | HIGH | Yes — copy pattern YOLO loading |
| `ai-service-fastapi/app/routers/parking.py` | Parking check-in/out endpoints | MED | Yes — có thể thêm `/ai/parking/detect-slots/` |
| `ai-service-fastapi/app/config.py` | Settings (PLATE_MODEL_PATH pattern) | MED | Yes — thêm `SLOT_MODEL_PATH` setting |
| `parking-service/infrastructure/models.py` | Django models cho parking slots | MED | Đọc để biết schema |

### 2.2 Pattern Đang Dùng trong Codebase

**YOLO loading pattern (detector.py — dùng làm mẫu):**
```python
# Source: ai-service-fastapi/app/engine/detector.py
class BanknoteDetector:
    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        if model_path:
            self._try_load_model(model_path)

    def _try_load_model(self, path: str) -> None:
        try:
            from ultralytics import YOLO
            self._model = YOLO(path)
            logger.info(f"✅ YOLOv8 model loaded from {path}")
        except Exception as e:
            logger.warning(f"⚠️ Model unavailable: {e}. Fallback mode.")
            self._model = None
```

**SlotDetector hiện tại (cần upgrade):**
```python
# Source: ai-service-fastapi/app/engine/slot_detection.py
class SlotDetector:
    def _detect_single_slot(self, gray, color_frame, bbox) -> SlotDetectionResult:
        # Method 1: Edge density (Canny)    — weight 0.4
        # Method 2: Contour analysis        — weight 0.3
        # Method 3: Color variance (HSV)    — weight 0.3
        # → combined_score >= 0.5 = OCCUPIED
        # method tag = "edge_contour_color"  ← sẽ thành "yolo_v11n" sau upgrade
```

**Data contract (FrameDetectionResult) — không thay đổi:**
```python
# Source: ai-service-fastapi/app/engine/slot_detection.py
@dataclass
class SlotDetectionResult:
    slot_id: str
    slot_code: str
    zone_id: str
    status: SlotStatus           # "available" | "occupied" | "unknown"
    confidence: float
    method: str                  # sẽ update: "yolo_v11n" | "edge_contour_color"
    processing_time_ms: float
```

**Camera monitor pipeline (30s polling):**
```python
# Source: ai-service-fastapi/app/engine/camera_monitor.py
SCAN_INTERVAL_S = 30
# Flow: poll parking-service API → get camera+slot mappings
# → capture_frame(camera_url) → slot_detector.detect_occupancy(frame, slots)
# → push updates to realtime-service
```

### 2.3 Potential Conflicts

- `SlotDetector` là singleton (`get_slot_detector()`) → YOLO model load một lần khi khởi động
- `SCAN_INTERVAL_S = 30` giây → đủ thời gian cho inference ngay cả CPU
- Camera monitor dùng `asyncio` background task → YOLO inference là sync, cần chạy trong `executor` để không block event loop

### 2.4 Dependencies Đã Có (tránh install trùng)

- `ultralytics==8.4.18` ✓ — đã có, hỗ trợ YOLO11
- `torch==1.13.1+cu116` ✓ — CUDA 11.6 GPU support
- `torchvision==0.14.1+cu116` ✓
- `opencv-python==4.10.0.84` ✓
- `numpy==1.26.4` ✓
- `huggingface_hub==1.5.0` ✓ — nếu cần pull custom weights
- `timm==1.0.25` ✓ — nếu cần ViT/ResNet approach
- `venv/Lib/site-packages/ultralytics/solutions/parking_management.py` ✓ — **đã có sẵn**

---

## 3. External Research

### 3.1 Ultralytics YOLO11 + ParkingManagement Solution

**Ultralytics `parking_management.py` (đã có trong venv):**
```python
# Source: https://docs.ultralytics.com/guides/parking-management | ultralytics==8.4.18
from ultralytics import solutions

parkingmanager = solutions.ParkingManagement(
    model="yolo11n.pt",           # Auto-download ~6MB, COCO pretrained
    json_file="parking_regions.json",  # Polygon regions per slot
)
# im0 = frame từ camera
results = parkingmanager(im0)
# results.pr_info → {"Occupancy": 5, "Available": 15}
```

**YOLO11n COCO pretrained classes (relevant):**
- class 2: `car` ← primary
- class 3: `motorcycle`
- class 5: `bus`
- class 7: `truck`

**YOLO11n specs:**
| Metric | Value |
|--------|-------|
| Model size | ~6 MB (.pt) |
| Parameters | 2.6M |
| GFLOPs | 6.5 |
| mAP50-95 (COCO) | 39.5 |
| Inference CPU (ms) | ~30ms/frame |
| Inference GPU (ms) | ~1ms/frame |

Source: https://docs.ultralytics.com/models/yolo11/ | Version: 8.4.18 | Date: 2026-03

### 3.2 PKLot Dataset — Domain-specific parking lot weights

- **PKLot** (UFPR): 12,417 images từ overhead parking cameras (Brazil)
- **CNRPark-EXT**: 144,965 patches từ overhead cameras Italy
- Cả hai cho phép train ResNet18/VGG classifier hoặc fine-tune YOLO
- HuggingFace có một số fine-tuned weights: `nickmuchi/yolos-small-finetuned-parkingslot`
- Trade-off: domain-specific nhưng cần download thêm ~30-100MB, không có official Ultralytics weights

Source: https://github.com/fabiocarrara/deep-parking | PKLot: 2018

### 3.3 ROI-based Classifier (ResNet18/MobileNetV2)

- Crop từng slot ROI → binary classify Empty/Occupied
- `timm==1.0.25` đã có → `timm.create_model("mobilenetv2_100", pretrained=True)`
- MobileNetV2: 3.5M params, ~5MB, <5ms/slot trên CPU
- NOT pretrained cho parking → cần fine-tune hoặc dùng transfer learning
- Simpler pipeline nhưng kém robust với shadows, lighting changes

---

## 4. So Sánh Phương Án

| Tiêu chí | **Option A: YOLO11n (COCO pretrained)** | **Option B: YOLO fine-tuned PKLot** | **Option C: ResNet18/MobileNet ROI classifier** |
|----------|----------------------------------------|--------------------------------------|------------------------------------------------|
| Cần train từ đầu? | ❌ Không — COCO weights sẵn | ⚠️ Cần fine-tune (~2h on GPU) | ⚠️ Cần fine-tune hoặc zero-shot |
| New dependencies | ❌ Không — ultralytics đã có | ❌ Không | ❌ Không — timm đã có |
| Model size | ~6 MB | ~6–25 MB | ~5–15 MB |
| Accuracy (overhead cam) | ⭐⭐⭐⭐ COCO cars khá tốt | ⭐⭐⭐⭐⭐ Domain-specific tốt nhất | ⭐⭐⭐ Phụ thuộc lighting |
| Inference latency | ~30ms/frame CPU, ~1ms GPU | ~30ms/frame CPU | ~3ms/slot CPU (no full frame) |
| Integration effort | **Thấp** — extend SlotDetector | Trung bình — cần download/train weights | Trung bình — cần inference per-slot |
| Consistency với codebase | ✅ Same YOLO pattern | ✅ Same YOLO pattern | ⚠️ Different pattern |
| Fallback support | ✅ Fallback sang OpenCV hiện tại | ✅ Fallback sang OpenCV | ✅ Fallback sang OpenCV |
| Production stability | ✅ Official Ultralytics support | ✅ Official | ⚠️ Community weights |
| Camera angle (overhead) | ✅ Tốt — COCO có overhead examples | ✅ Tốt nhất — PKLot là overhead | ⚠️ Cần calibration |

**Note:** Đây là facts để Architect quyết định.

---

## 5. ⚠️ Gotchas & Known Issues

- [ ] **[NOTE]** `torch==1.13.1+cu116` — version cũ (2022). YOLO11 officially supports torch>=1.8, vẫn chạy được nhưng nên upgrade lên torch 2.x khi có cơ hội. Không block MVP.
- [ ] **[WARNING]** Camera monitor dùng `asyncio` — YOLO inference là **synchronous blocking**. Phải wrap bằng `await loop.run_in_executor(None, yolo_predict, frame)` để tránh block event loop.
- [ ] **[NOTE]** `yolo11n.pt` auto-downloads từ internet lần đầu (~6MB). Trong Docker production cần **pre-download** vào image hoặc mount volume. Add `RUN python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"` vào Dockerfile.
- [ ] **[NOTE]** RTSP cameras (EZVIZ) đã có `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp` trong `camera_capture.py` — không cần thêm.
- [ ] **[NOTE]** `ultralytics==8.4.18` — model name có thể là `yolo11n.pt` (YOLO11, released Oct 2024) hoặc `yolov8n.pt` (YOLOv8). Cả hai supported, YOLO11n có accuracy cao hơn ~2% mAP.
- [ ] **[WARNING]** Parking lots với overhead camera góc cao có thể detect roof của car, không phải whole car. YOLO11n vẫn hoạt động tốt vì COCO training set có various angles. Nhưng nếu accuracy thấp, cần fine-tune với custom overhead data.
- [ ] **[NOTE]** SlotBbox hiện tại dùng rectangular bbox (`x1,y1,x2,y2`). `ParkingManagement` của Ultralytics dùng polygon regions (JSON). Nếu dùng `ParkingManagement` directly, cần convert slot bbox → polygon format.

---

## 6. Code Examples từ Official Docs

**Option A — Extend SlotDetector với YOLO11n (recommended approach):**
```python
# Pattern: thêm YOLO layer vào SlotDetector hiện tại
# Source: codebase pattern từ plate_detector.py + ultralytics docs
# Version: ultralytics==8.4.18

class SlotDetector:
    VEHICLE_CLASSES = {2, 3, 5, 7}  # car, motorcycle, bus, truck (COCO)

    def __init__(self, model_path: Optional[str] = None, ...):
        self._yolo = None
        if model_path and os.path.exists(model_path):
            try:
                from ultralytics import YOLO
                self._yolo = YOLO(model_path)
                logger.info(f"✅ YOLO slot detector loaded from {model_path}")
            except Exception as e:
                logger.warning(f"⚠️ YOLO unavailable: {e}. Fallback to OpenCV.")

    def _detect_single_slot(self, gray, color_frame, bbox) -> SlotDetectionResult:
        if self._yolo is not None:
            return self._detect_yolo(color_frame, bbox)
        return self._detect_opencv(gray, color_frame, bbox)  # existing logic

    def _detect_yolo(self, frame, bbox) -> SlotDetectionResult:
        roi = frame[bbox.y1:bbox.y2, bbox.x1:bbox.x2]
        results = self._yolo(roi, verbose=False, conf=0.25)
        for r in results:
            for box in r.boxes:
                if int(box.cls[0]) in self.VEHICLE_CLASSES:
                    return SlotDetectionResult(
                        status=SlotStatus.OCCUPIED,
                        confidence=float(box.conf[0]),
                        method="yolo_v11n",
                        ...
                    )
        return SlotDetectionResult(status=SlotStatus.AVAILABLE, confidence=0.9, method="yolo_v11n", ...)
```

**Ultralytics ParkingManagement (alternative full solution):**
```python
# Source: https://docs.ultralytics.com/guides/parking-management | ultralytics==8.4.18
from ultralytics import solutions
parkingmanager = solutions.ParkingManagement(
    model="yolo11n.pt",
    json_file="bounding_boxes.json",  # slot polygons
)
results = parkingmanager(frame)
# results.pr_info = {"Occupancy": 5, "Available": 15}
# results.plot_im = annotated frame
```

**Async-safe YOLO call pattern (quan trọng với asyncio):**
```python
# Pattern: wrap sync YOLO inference trong executor
import asyncio

async def _detect_frame_async(self, frame, slots, camera_id):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        self._slot_detector.detect_occupancy, frame, slots, camera_id
    )
    return result
```

---

## 7. Checklist cho Implementer

- [ ] **Model file**: Download `yolo11n.pt` — `python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"` — file lưu tại `~/.ultralytics/assets/yolo11n.pt`. Copy sang `/app/app/models/yolo11n.pt` trong Docker.
- [ ] **Config setting**: Thêm `SLOT_MODEL_PATH: str = "/app/app/models/yolo11n.pt"` vào `app/config.py` (follow pattern của `PLATE_MODEL_PATH`)
- [ ] **Engine upgrade**: Modify `app/engine/slot_detection.py` — thêm YOLO layer vào `SlotDetector.__init__()` và `_detect_single_slot()`, giữ OpenCV làm fallback
- [ ] **Async fix**: Wrap `detect_occupancy()` call trong `camera_monitor.py` bằng `loop.run_in_executor()` (nếu chưa có)
- [ ] **Dockerfile**: Thêm `RUN python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"` để pre-download weights
- [ ] **Env vars cần thêm**: `SLOT_MODEL_PATH=/app/app/models/yolo11n.pt` — thêm vào `.env.example`
- [ ] **Install**: ❌ KHÔNG cần install thêm gì — `ultralytics==8.4.18` đã có
- [ ] **Migration cần**: ❌ Không — đây là engine-level change
- [ ] **Breaking changes**: ❌ Không — `FrameDetectionResult` schema không thay đổi, chỉ `method` field thay từ `"edge_contour_color"` → `"yolo_v11n"`
- [ ] **Pattern reference**: Dùng `app/engine/plate_detector.py` làm mẫu YOLO loading
- [ ] **Test**: Update `tests/test_detector.py` — mock YOLO model (pattern đã có trong test files)

---

## 8. Kiến Trúc Tích Hợp Đề Xuất

### 8.1 Approach: Nâng cấp service sẵn có (KHÔNG tạo service mới)

**Lý do**: `ai-service-fastapi` đã có đầy đủ:
- Camera capture → slot detection → push to realtime-service pipeline
- YOLO infrastructure (ultralytics, torch, cv2)
- `SlotDetector` singleton pattern
- Background monitor worker

Tạo service mới = duplicate infrastructure không cần thiết.

### 8.2 Draft API Contract (Endpoint mới cho on-demand detection)

```
POST /ai/parking/detect-occupancy/
```

**Request:**
```python
# multipart/form-data
image: UploadFile                    # camera frame
camera_id: str (Form)                # camera identifier
slots: str (Form, JSON string)       # list of slot bounding boxes
```

**Slots JSON format:**
```json
[
  {"slot_id": "uuid", "slot_code": "A-01", "zone_id": "zone-uuid", "x1": 100, "y1": 50, "x2": 250, "y2": 200},
  {"slot_id": "uuid", "slot_code": "A-02", "zone_id": "zone-uuid", "x1": 260, "y1": 50, "x2": 410, "y2": 200}
]
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "camera_id": "camera-uuid",
    "total_slots": 10,
    "total_available": 6,
    "total_occupied": 4,
    "processing_time_ms": 45.2,
    "model_version": "yolo11n",
    "slots": [
      {
        "slot_id": "uuid",
        "slot_code": "A-01",
        "zone_id": "zone-uuid",
        "status": "occupied",
        "confidence": 0.872,
        "method": "yolo_v11n",
        "processing_time_ms": 4.1
      }
    ]
  }
}
```

**Response (422 Unprocessable Entity):**
```json
{
  "success": false,
  "error": {"code": "ERR_VALIDATION", "message": "Invalid slots JSON format", "details": []}
}
```

### 8.3 Background Monitor (không cần thay đổi API)

```
camera_monitor.py (30s interval)
  └─ capture_frame(camera_url)          # đã có
      └─ slot_detector.detect_occupancy(frame, slots)  # upgrade YOLO
          └─ push to realtime-service   # đã có
```

---

## 9. Nguồn

| # | URL | Mô tả | Version | Date |
|---|-----|-------|---------|------|
| 1 | https://docs.ultralytics.com/guides/parking-management | Official Ultralytics Parking Management Guide | 8.4.x | 2024 |
| 2 | https://docs.ultralytics.com/models/yolo11/ | YOLO11 model specs & benchmarks | 8.4.x | Oct 2024 |
| 3 | https://docs.ultralytics.com/reference/solutions/parking_management | ParkingManagement class API reference | 8.4.x | 2024 |
| 4 | https://github.com/fabiocarrara/deep-parking | PKLot/CNRPark deep learning parking research | — | 2018-2022 |
| 5 | Codebase scan | `ai-service-fastapi/app/engine/` — slot_detection.py, detector.py, plate_detector.py | current | 2026-03-16 |
| 6 | Codebase scan | `ai-service-fastapi/requirements.txt` — ultralytics==8.4.18 confirmed | current | 2026-03-16 |
