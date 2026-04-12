# Research Report: ANPR Detection Flow — Save + View Capability

**Task:** ANPR Detection History | **Date:** 2026-04-11 | **Type:** Codebase Analysis (Mixed)

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **ESP32 flow đã save plate images** vào `app/images/` khi check-in/check-out — nhưng **`scan-plate/` endpoint và `check-in/` / `check-out/` trong `parking.py` KHÔNG save images**
> 2. **`PredictionLog` table đã tồn tại** và ghi metadata (plate_text, confidence, decision) cho mọi scan — nhưng **KHÔNG lưu bounding box, KHÔNG lưu image path, KHÔNG lưu cropped plate image**
> 3. **Web frontend không có Detection History page** — `CamerasPage` chỉ xem live stream, `KioskPage` là self-service gate UI. Không có trang nào hiển thị lịch sử ANPR
> 4. **Database không có dedicated ANPR detection table** — chỉ có `api_predictionlog` (generic cho tất cả AI predictions)

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File                                              | Mục đích                                               | Relevance  | Có thể tái dụng?                                     |
| ------------------------------------------------- | ------------------------------------------------------ | ---------- | ---------------------------------------------------- |
| `ai-service-fastapi/app/routers/parking.py`       | scan-plate, check-in, check-out endpoints              | **High**   | Yes — thêm image saving vào đây                      |
| `ai-service-fastapi/app/routers/esp32.py`         | ESP32 gate integration (đã save images)                | **High**   | Yes — `_save_plate_image()` function có thể tái dụng |
| `ai-service-fastapi/app/routers/detection.py`     | License plate detect API `/ai/detect/license-plate/`   | **Medium** | Yes — trả bbox nhưng cũng không save image           |
| `ai-service-fastapi/app/routers/camera.py`        | Camera live stream + `/read-plate` endpoint            | **Medium** | No — chỉ xử lý frames, không save                    |
| `ai-service-fastapi/app/routers/metrics.py`       | `GET /ai/models/predictions/` — list PredictionLog     | **High**   | Yes — đã có endpoint query predictions               |
| `ai-service-fastapi/app/models/ai.py`             | `PredictionLog`, `CameraFeed`, `ModelVersion` models   | **High**   | Yes — extend hoặc thêm model mới                     |
| `ai-service-fastapi/app/engine/plate_pipeline.py` | `PlatePipeline.process()` → `PlatePipelineResult`      | **High**   | Yes — đã return bbox, confidence, text               |
| `ai-service-fastapi/app/engine/plate_detector.py` | YOLO detector → `PlateDetectionResult` with `PlateBox` | **High**   | Yes — bbox (x1,y1,x2,y2,conf) đã có                  |
| `ai-service-fastapi/app/main.py`                  | Static mount `/ai/images` → `app/images/`              | **High**   | Yes — images đã serve qua HTTP                       |
| `spotlove-ai/src/pages/CamerasPage.tsx`           | Camera monitoring page                                 | **Low**    | No — chỉ live stream                                 |
| `spotlove-ai/src/pages/KioskPage.tsx`             | Gate kiosk UI                                          | **Low**    | No — self-service gate                               |
| `spotlove-ai/src/services/api/ai.api.ts`          | AI API client                                          | **High**   | Yes — thêm detection history API call                |
| `ParkingSimulatorUnity/.../DataModels.cs`         | `PlateScanResult` class                                | **Medium** | Có thể extend nếu cần                                |
| `ParkingSimulatorUnity/.../ApiService.cs`         | `AIRecognizePlate()` method                            | **Medium** | Có thể extend                                        |

### 2.2 Current Scan-Plate Flow (Endpoint → Model → Response)

```
POST /ai/parking/scan-plate/
  ├── 1. Read uploaded image bytes
  ├── 2. PlatePipeline.process(img_bytes)
  │     ├── cv2.imdecode(img)
  │     ├── LicensePlateDetector.detect(img)  → PlateDetectionResult
  │     │     └── YOLO inference → PlateBox(x1,y1,x2,y2,confidence)
  │     │                        → cropped plate region (np.ndarray)
  │     ├── read_plate_text(plate_img)  → OCRResult
  │     │     └── TrOCR → EasyOCR → Tesseract (cascade)
  │     └── Return PlatePipelineResult
  ├── 3. _log_prediction(db, "plate_scan", {...})   ← Saves to PredictionLog
  └── 4. Return JSON response
```

**Response fields (scan-plate):**

```json
{
  "plate_text": "51A-224.56",
  "decision": "success",
  "confidence": 0.952,
  "detection_confidence": 0.891,
  "is_blurry": false,
  "blur_score": 12.5,
  "ocr_method": "trocr",
  "raw_candidates": ["51A-224.56", "51A-22456"],
  "warning": null,
  "message": "...",
  "processing_time_ms": 342.5
}
```

**What's MISSING in response:**

- `plate_image_url` — no image saved or returned
- `bbox` — not included (though detection.py `/ai/detect/license-plate/` does include it)
- `detection_id` — no unique ID for this detection event

### 2.3 What's Saved vs Not Saved

| Data Point            | scan-plate (parking.py)      | check-in/out (parking.py) | ESP32 check-in/out (esp32.py)            | /detect/license-plate/ (detection.py)    |
| --------------------- | ---------------------------- | ------------------------- | ---------------------------------------- | ---------------------------------------- |
| plate_text            | ✅ PredictionLog.output_data | ✅ PredictionLog          | ✅ PredictionLog                         | ✅ PredictionLog                         |
| confidence            | ✅ PredictionLog.confidence  | ✅ PredictionLog          | ✅ PredictionLog                         | ✅ PredictionLog                         |
| bbox                  | ❌ NOT saved                 | ❌ NOT saved              | ❌ NOT saved                             | ❌ NOT saved (returned in response only) |
| original image        | ❌ NOT saved                 | ❌ NOT saved              | ✅ `_save_plate_image()` → `app/images/` | ❌ NOT saved                             |
| cropped plate image   | ❌ NOT saved                 | ❌ NOT saved              | ❌ NOT saved                             | ❌ NOT saved                             |
| image URL in response | ❌ N/A                       | ❌ N/A                    | ✅ `plate_image_url` field               | ❌ N/A                                   |
| booking_id context    | ❌ N/A                       | ✅ in input_data          | ✅ in input_data                         | ❌ N/A                                   |
| camera_id             | ❌ NOT tracked               | ❌ NOT tracked            | ✅ via gate_id                           | ❌ NOT tracked                           |

### 2.4 Detection Image Storage (Current State)

**ESP32 flow saves images:**

- Function: `_save_plate_image()` in `esp32.py:457-483`
- Location: `ai-service-fastapi/app/images/`
- Naming: `plate_{action}_{booking_id_short}_{timestamp}.jpg`
- Example files already on disk:
  - `plate_checkin_6ceac4e0_20260402_230413.jpg`
  - `plate_checkin_6f147099_20260402_230347.jpg`
  - `plate_checkin_bfa4189b_20260228_231759.jpg`
- Served via: `app.mount("/ai/images", StaticFiles(...))` (main.py:67-69)
- Accessible at: `http://localhost:8009/ai/images/plate_checkin_xxx.jpg`

**parking.py flow does NOT save images** — they are discarded after OCR processing.

### 2.5 Existing `PredictionLog` Table Schema

```python
# app/models/ai.py
class PredictionLog(Base):
    __tablename__ = "api_predictionlog"
    id            = Column(CHAR(36), PK)           # UUID
    prediction_type = Column(String(50), indexed)   # "plate_scan", "check_in_success", etc.
    input_data    = Column(JSON)                    # {"filename": "..."}
    output_data   = Column(JSON)                    # {"plate_text": "...", "decision": "...", "confidence": 0.95}
    confidence    = Column(Float)
    model_version = Column(String(50), indexed)     # "license-plate-finetune-v1m"
    processing_time = Column(Float)                 # seconds
    created_at    = Column(DateTime)
```

**Issues with PredictionLog for detection history:**

- Generic (shared by license plate, cash, banknote, all AI predictions)
- No `image_path` column
- No `bbox` in output_data (for scan-plate — detection.py does save it in output_data but unstructured)
- No `camera_id` / `gate_id` tracking
- No `booking_id` field (sometimes embedded in input_data JSON)

### 2.6 Existing Query Endpoint

```
GET /ai/models/predictions/?prediction_type=plate_scan&page=1&page_size=20
```

- Source: `metrics.py:64-80`
- Returns: list of `PredictionLogResponse` with pagination
- Filters: `prediction_type` only
- **No filter by date range, camera, or plate text**

---

## 3. Unity Side — How Results Are Received

### 3.1 PlateScanResult (DataModels.cs:318-330)

```csharp
public class PlateScanResult
{
    [JsonProperty("plateText")] public string PlateText;
    [JsonProperty("decision")] public string Decision;
    [JsonProperty("confidence")] public float Confidence;
    [JsonProperty("detectionConfidence")] public float DetectionConfidence;
    [JsonProperty("isBlurry")] public bool IsBlurry;
    [JsonProperty("blurScore")] public float BlurScore;
    [JsonProperty("ocrMethod")] public string OcrMethod;
    [JsonProperty("rawCandidates")] public List<string> RawCandidates;
    [JsonProperty("warning")] public string Warning;
    [JsonProperty("message")] public string Message;
    [JsonProperty("processingTimeMs")] public float ProcessingTimeMs;
}
```

**Observations:**

- No `plateImageUrl` field — Unity does NOT expect an image URL back
- No `bbox` field
- No `detectionId` field
- Used in: `ApiService.AIRecognizePlate()` (line 397), `ParkingManager` (line 370), `GateCameraSimulator` (line 185)

### 3.2 ESP32Response (from esp32.py, used in KioskPage)

```python
class ESP32Response(CamelModel):
    plate_image_url: Optional[str] = None  # ← This field EXISTS but only in ESP32 flow
```

---

## 4. Web Frontend Detection Pages

### 4.1 Existing Pages

| Page                        | Path               | Purpose                                         | ANPR Detection History?  |
| --------------------------- | ------------------ | ----------------------------------------------- | ------------------------ |
| `CamerasPage.tsx`           | `/cameras`         | Live camera monitoring (6 virtual + 2 physical) | ❌ No                    |
| `AdminCamerasPage.tsx`      | `/admin/cameras`   | Admin camera management                         | ❌ No                    |
| `KioskPage.tsx`             | `/kiosk`           | Self-service gate UI (ESP32 check-in/out)       | ❌ Shows last event only |
| `BanknoteDetectionPage.tsx` | `/detect/banknote` | Banknote recognition test                       | ❌ No (banknote only)    |

### 4.2 Frontend AI API (ai.api.ts)

- `aiApi.scanPlate(image)` — calls `POST /ai/parking/scan-plate/`
- Returns `PlateOCRResponse` — no `plateImageUrl`, no `bbox`, no `detectionId`
- **No method for fetching detection history**
- **No method for fetching prediction logs**

### 4.3 Missing Frontend Components

- No `DetectionHistoryPage` component
- No `DetectionCard` / `DetectionList` component
- No API client for `GET /ai/models/predictions/?prediction_type=plate_scan`

---

## 5. Database/Storage

### 5.1 init-mysql.sql

- **No dedicated ANPR detection table** — only chatbot tables are created here
- Django services (booking-service, parking-service, auth-service) manage their own migrations
- AI service uses SQLAlchemy with `api_predictionlog`, `api_camerafeed`, `api_modelversion`

### 5.2 No Detection History Table

There is no table like:

```sql
CREATE TABLE anpr_detection (
    id CHAR(36) PRIMARY KEY,
    plate_text VARCHAR(20),
    confidence FLOAT,
    bbox JSON,
    image_path VARCHAR(255),
    camera_id VARCHAR(50),
    gate_id VARCHAR(50),
    booking_id CHAR(36),
    action VARCHAR(20),        -- scan, check_in, check_out
    created_at DATETIME
);
```

---

## 6. ⚠️ Gaps

### Gap A: scan-plate does NOT save images

- `parking.py:scan_plate()` reads image, runs OCR, returns text, discards image
- The `_save_plate_image()` helper exists in `esp32.py` but is NOT used by `parking.py`

### Gap B: PredictionLog lacks ANPR-specific fields

- No `image_path` — can't link back to saved image
- No structured `bbox` — buried in JSON (and only in detection.py flow)
- No `camera_id` / `gate_id` tracking
- No dedicated filter/search by plate_text

### Gap C: No detection history API endpoint with image URLs

- `GET /ai/models/predictions/` exists but returns raw PredictionLog without image URLs
- No endpoint to search by plate text, date range, or camera

### Gap D: No web frontend Detection History page

- No page, no component, no API client method

### Gap E: Bounding box not returned by scan-plate

- `PlatePipelineResult` has `detection_result.box` (PlateBox with x1,y1,x2,y2,confidence)
- But `scan_plate()` endpoint **does not include bbox in response**
- `detection.py:/detect/license-plate/` **does** return bbox

---

## 7. Recommended Minimal Approach

**Option A: Extend PredictionLog (least disruptive, ~2-3 files changed)**

1. **AI Service — parking.py `scan_plate()`:**
   - Save image using existing `_save_plate_image()` pattern (extract from esp32.py or import)
   - Add `bbox` to response
   - Add `plate_image_url` to response
   - Store `image_path` in PredictionLog `output_data` JSON

2. **AI Service — metrics.py:**
   - Add `GET /ai/models/predictions/plate-detections/` specialized endpoint
   - Support filters: `prediction_type`, `date_from`, `date_to`, `plate_text` (LIKE search on output_data)
   - Enrich response with `plate_image_url` (constructed from saved path)

3. **Web Frontend:**
   - Add `aiApi.getDetectionHistory()` method in `ai.api.ts`
   - Create `DetectionHistoryPage.tsx` with table of detections + thumbnail images
   - Add route in `App.tsx`

**Option B: Dedicated ANPR Detection Table (cleaner, ~4-5 files changed)**

1. **New model `AnprDetection`** in `app/models/ai.py`:

   ```python
   class AnprDetection(Base):
       __tablename__ = "api_anprdetection"
       id, plate_text, confidence, detection_confidence,
       bbox_json, image_path, cropped_image_path,
       camera_id, gate_id, booking_id, action,
       ocr_method, decision, created_at
   ```

2. **New router `/ai/parking/detections/`** — CRUD for detection records
3. **Modify `scan_plate()`, `check_in()`, `check_out()`** to also write to AnprDetection
4. **Frontend** same as Option A

**Note:** Đây là facts. Architect quyết định chọn Option A hay B.

---

## 8. Existing Utilities Có Thể Tái Dụng

| Utility                                    | Location                          | Mục đích                                                  |
| ------------------------------------------ | --------------------------------- | --------------------------------------------------------- |
| `_save_plate_image()`                      | `esp32.py:457`                    | Save JPEG bytes → `app/images/` with timestamped filename |
| `StaticFiles mount /ai/images`             | `main.py:67-69`                   | Serve saved images via HTTP                               |
| `PredictionLog` + `_log_prediction()`      | `models/ai.py` + `parking.py:131` | Log prediction metadata to DB                             |
| `GET /ai/models/predictions/`              | `metrics.py:64`                   | Query prediction logs with pagination                     |
| `PlateBox (x1,y1,x2,y2,conf)`              | `plate_detector.py:19`            | Bounding box dataclass                                    |
| `PlatePipelineResult.detection_result.box` | `plate_pipeline.py:38`            | Access bbox after detection                               |
| `CamelModel` base                          | `schemas/base.py`                 | Auto camelCase for API responses                          |

---

## 9. Nguồn

| #   | File                                              | Mô tả                                              | Lines   |
| --- | ------------------------------------------------- | -------------------------------------------------- | ------- |
| 1   | `ai-service-fastapi/app/routers/parking.py`       | scan-plate, check-in, check-out endpoints          | 1-479   |
| 2   | `ai-service-fastapi/app/routers/esp32.py`         | ESP32 gate integration, `_save_plate_image()`      | 1-1285+ |
| 3   | `ai-service-fastapi/app/routers/detection.py`     | `/detect/license-plate/` with bbox                 | 1-300   |
| 4   | `ai-service-fastapi/app/routers/camera.py`        | Camera streaming + `/read-plate`                   | 1-300   |
| 5   | `ai-service-fastapi/app/routers/metrics.py`       | `GET /ai/models/predictions/`                      | 1-100   |
| 6   | `ai-service-fastapi/app/models/ai.py`             | PredictionLog, CameraFeed, ModelVersion SQLAlchemy | 1-60    |
| 7   | `ai-service-fastapi/app/engine/plate_pipeline.py` | PlatePipeline, PlatePipelineResult                 | 1-150   |
| 8   | `ai-service-fastapi/app/engine/plate_detector.py` | LicensePlateDetector, PlateBox                     | 1-80    |
| 9   | `ai-service-fastapi/app/main.py`                  | Static mount `/ai/images`                          | 55-80   |
| 10  | `ParkingSimulatorUnity/.../DataModels.cs`         | PlateScanResult C# class                           | 318-330 |
| 11  | `ParkingSimulatorUnity/.../ApiService.cs`         | AIRecognizePlate method                            | 397-420 |
| 12  | `spotlove-ai/src/services/api/ai.api.ts`          | Frontend AI API client                             | 1-300   |
| 13  | `spotlove-ai/src/pages/CamerasPage.tsx`           | Camera monitoring page                             | 1-170   |
| 14  | `spotlove-ai/src/pages/KioskPage.tsx`             | Gate kiosk UI                                      | 1-120   |
| 15  | `backend-microservices/init-mysql.sql`            | DB init (chatbot only)                             | 1-200   |
