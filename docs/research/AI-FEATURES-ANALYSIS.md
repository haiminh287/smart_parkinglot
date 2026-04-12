# Research Report: Phân Tích Toàn Bộ AI Features — ParkSmart

**Task:** AI Features Analysis | **Date:** 2026-03-25 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **2 AI services**: `ai-service-fastapi` (port 8009) và `chatbot-service-fastapi` (port 8008) — cả hai đã production-ready.
> 2. **ai-service** có 6 router groups, 25+ endpoints: detection, parking, esp32, camera, training, metrics.
> 3. **CREDENTIAL HARDCODE**: Camera RTSP URL có credentials plain-text (`rtsp://admin:XGIMBN@...`). Model path `/app/app/models/license-plate-finetune-v1m.pt` — nếu file này không tồn tại, plate detection fallback sang full-image (không báo lỗi, chỉ log warning).
> 4. **Gemini API Key**: Nếu `GEMINI_API_KEY` rỗng trong docker-compose, LLM bị tắt silently — chatbot hoạt động nhưng không có AI generation.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 AI Services Overview

| Service | Directory | Container Name | Port (host) | Internal Port | Python |
|---|---|---|---|---|---|
| AI Service | `ai-service-fastapi/` | `ai-service-fastapi` | `expose 8009` (no host binding) | `8009` | 3.10 |
| Chatbot Service | `chatbot-service-fastapi/` | `chatbot-service-fastapi` | `expose 8008` (no host binding) | `8008` | 3.11 |

> **Lưu ý**: Cả 2 services dùng `expose` thay vì `ports` → không access được từ host machine trực tiếp, chỉ qua Gateway `:8000`.

### 2.2 Files/Modules Liên Quan

| File | Mục đích | Relevance |
|---|---|---|
| `ai-service-fastapi/app/routers/detection.py` | License plate + banknote endpoints | High |
| `ai-service-fastapi/app/routers/parking.py` | Check-in/out + scan-plate + occupancy | High |
| `ai-service-fastapi/app/routers/esp32.py` | ESP32 gate automation (1500+ lines) | High |
| `ai-service-fastapi/app/routers/camera.py` | RTSP/HTTP camera streaming | High |
| `ai-service-fastapi/app/routers/metrics.py` | Model metrics và prediction logs | Medium |
| `ai-service-fastapi/app/routers/training.py` | Trigger model training in background | Medium |
| `ai-service-fastapi/app/engine/plate_pipeline.py` | License plate YOLO+OCR pipeline | High |
| `ai-service-fastapi/app/engine/plate_detector.py` | YOLOv8 plate bounding box detection | High |
| `ai-service-fastapi/app/engine/plate_ocr.py` | TrOCR → EasyOCR → Tesseract pipeline | High |
| `ai-service-fastapi/app/engine/slot_detection.py` | YOLO11n parking occupancy detection | High |
| `ai-service-fastapi/app/engine/pipeline.py` | Banknote recognition pipeline | High |
| `ai-service-fastapi/app/engine/detector.py` | YOLOv8 banknote detector | High |
| `ai-service-fastapi/app/engine/ai_classifier.py` | Neural net banknote classifier | High |
| `ai-service-fastapi/app/engine/color_classifier.py` | HSV color-based denomination | High |
| `ai-service-fastapi/app/engine/camera_capture.py` | OpenCV camera capture wrapper | High |
| `ai-service-fastapi/app/engine/qr_reader.py` | QR code reader (cv2 + pyzbar) | High |
| `chatbot-service-fastapi/app/routers/chat.py` | Chat + quickactions + feedback | High |
| `chatbot-service-fastapi/app/routers/conversation.py` | CRUD conversations | High |
| `chatbot-service-fastapi/app/engine/orchestrator.py` | Chatbot orchestrator v3 pipeline | High |
| `chatbot-service-fastapi/app/infrastructure/llm/gemini_client.py` | Google Gemini 2.0 Flash client | High |

### 2.3 Model Files & Paths

| Model | Path trong container | Tồn tại? | Notes |
|---|---|---|---|
| License Plate YOLO | `/app/app/models/license-plate-finetune-v1m.pt` | ❓ Cần kiểm tra | Fallback sang full-image nếu missing |
| YOLO11n Parking | `/app/ml/models/yolo11n.pt` | ❓ Cần kiểm tra | Fallback sang OpenCV nếu missing |
| Cash Recognition ResNet50 | `/app/ml/models/cash_recognition_best.pth` | ❓ Cần kiểm tra | 503 nếu missing |
| Banknote Pipeline | `/app/ml/models/` (multiple files) | ❓ Cần kiểm tra | `hybrid-mvp-v1` pipeline |
| TrOCR | Từ HuggingFace Hub (auto-download) | ✅ Auto | `microsoft/trocr-base-printed` |
| EasyOCR | Từ HuggingFace Hub (auto-download) | ✅ Auto | Fallback của TrOCR |

---

## 3. AI Endpoints — Danh Sách Đầy Đủ

### 3.1 AI Service (`ai-service-fastapi`) — Port 8009

#### Router 1: Detection (`/ai/detect`)

| Method | URL | Feature | Input | Output |
|---|---|---|---|---|
| `POST` | `/ai/detect/license-plate/` | License Plate OCR | `multipart/form-data`: `image` (file) | `{detections: [{plate_text, confidence, bbox}], processing_time, model_version}` |
| `POST` | `/ai/detect/cash/` | Cash Recognition (ResNet50) | `multipart/form-data`: `image` (file) | `{denomination, confidence, all_probabilities, processing_time, model_version}` |
| `POST` | `/ai/detect/banknote/` | Banknote Recognition (Hybrid MVP) | `multipart/form-data`: `image` (file), query: `mode=full\|fast` | Xem schema đầy đủ ở §4.1 |

#### Router 2: Parking (`/ai/parking`)

| Method | URL | Feature | Input | Output |
|---|---|---|---|---|
| `POST` | `/ai/parking/scan-plate/` | Scan plate (preview/test) | `multipart/form-data`: `image` (file) | `{plate_text, decision, confidence, detection_confidence, warning, processing_time_ms}` |
| `POST` | `/ai/parking/check-in/` | Check-in với QR + plate | `multipart/form-data`: `image` (file), `qr_data` (JSON string) | Booking check-in result |
| `POST` | `/ai/parking/check-out/` | Check-out với QR + plate | `multipart/form-data`: `image` (file), `qr_data` (JSON string) | Booking check-out result |
| `POST` | `/ai/parking/detect-occupancy/` | Parking slot occupancy | `multipart/form-data`: `image` (file), `camera_id` (string), `slots` (JSON string) | `OccupancyDetectionResponse` |

#### Router 3: ESP32 (`/ai/parking/esp32`) — Bypass Gateway Auth

| Method | URL | Feature | Input (JSON Body) | Output |
|---|---|---|---|---|
| `POST` | `/ai/parking/esp32/check-in/` | ESP32 gate-in automation | `{gate_id, qr_data?, qr_camera_url?, plate_camera_url?, request_id?}` | `ESP32Response` |
| `POST` | `/ai/parking/esp32/check-out/` | ESP32 gate-out automation | `{gate_id, qr_data?, qr_camera_url?, plate_camera_url?, request_id?}` | `ESP32Response` |
| `POST` | `/ai/parking/esp32/verify-slot/` | ESP32 slot verification | `{slot_code, zone_id, gate_id, qr_data?, qr_camera_url?, request_id?}` | `ESP32Response` |
| `POST` | `/ai/parking/esp32/cash-payment/` | Cash payment via AI + barrier | `{booking_id, gate_id, image_base64?, camera_url?, request_id?}` | `ESP32Response` |
| `GET` | `/ai/parking/esp32/status/` | Health + camera check | — | `{status, devices, cameras}` |
| `POST` | `/ai/parking/esp32/register` | ESP32 self-registration | `{device_id, ip, firmware, gpio_config?}` | `ESP32AckResponse` |
| `POST` | `/ai/parking/esp32/heartbeat` | ESP32 keepalive | `{device_id, status, wifi_rssi?}` | `ESP32AckResponse` |
| `POST` | `/ai/parking/esp32/log` | ESP32 log sender | `{device_id, level, message}` | `ESP32AckResponse` |
| `GET` | `/ai/parking/esp32/devices` | List registered devices (frontend) | — | `ESP32DeviceListResponse` |
| `GET` | `/ai/parking/esp32/devices/{device_id}/logs` | Device logs (frontend) | — | `ESP32DeviceLogsResponse` |

#### Router 4: Camera (`/ai/cameras`)

| Method | URL | Feature | Input | Output |
|---|---|---|---|---|
| `GET` | `/ai/cameras/list` | List configured cameras | — | JSON array of camera info (no credentials) |
| `GET` | `/ai/cameras/snapshot` | Single JPEG frame | query: `camera_id?`, `url?` | `image/jpeg` binary |
| `GET` | `/ai/cameras/stream` | MJPEG live stream | query: `camera_id?`, `url?`, `fps=5` | `multipart/x-mixed-replace` MJPEG stream |

#### Router 5: Training (`/ai/train`)

| Method | URL | Feature | Input |
|---|---|---|---|
| `POST` | `/ai/train/cash/` | Trigger ResNet50 training | `{train_dir, val_dir, epochs, batch_size, lr}` |
| `POST` | `/ai/train/banknote/` | Trigger bank-grade pipeline training | `{data_dir, epochs_classifier, epochs_siamese, epochs_oneclass, batch_size, lr, mlflow}` |

#### Router 6: Metrics (`/ai/models`)

| Method | URL | Feature |
|---|---|---|
| `GET` | `/ai/models/metrics/` | Metrics tất cả models |
| `GET` | `/ai/models/predictions/` | Prediction logs (paginated) |
| `GET` | `/ai/models/versions/` | Model versions list |

#### Health

| Method | URL |
|---|---|
| `GET` | `/health/` hoặc `/ai/health/` |

---

### 3.2 Chatbot Service (`chatbot-service-fastapi`) — Port 8008

#### Router: Chat (`/chatbot`)

| Method | URL | Feature | Input (JSON) | Output |
|---|---|---|---|---|
| `POST` | `/chatbot/chat/` | Main chat endpoint | `{message: str, conversationId?: str}` | `ChatResponse` (xem §4.2) |
| `GET` | `/chatbot/quick-actions/` | Quick action buttons | — | `{quickActions: [{id, label, icon, prompt}]}` |
| `POST` | `/chatbot/feedback/` | Rating (1-5 sao) | `{conversationId, rating, comment?}` | `{message, rating}` |

#### Router: Conversations (`/chatbot/conversations`)

| Method | URL | Feature |
|---|---|---|
| `GET` | `/chatbot/conversations/` | List conversations (max 20) |
| `POST` | `/chatbot/conversations/` | Tạo conversation mới |
| `GET` | `/chatbot/conversations/active/` | Get/create active conversation |
| `GET` | `/chatbot/conversations/{id}/` | Get specific conversation |
| `GET` | `/chatbot/conversations/{id}/messages/` | Chat history |
| `GET` | `/chatbot/conversations/history/latest/` | Latest history |

#### Router: Preferences (`/chatbot/preferences`)

| Method | URL | Feature |
|---|---|---|
| `GET` | `/chatbot/preferences/` | Get user preferences |
| `PUT` | `/chatbot/preferences/` | Update preferences |

#### Router: Notifications (`/chatbot/notifications`)

| Method | URL | Feature |
|---|---|---|
| `GET` | `/chatbot/notifications/` | Proactive notifications |
| `POST` | `/chatbot/notifications/{id}/status/` | Update notification status |

#### Router: Actions (`/chatbot/actions`)

| Method | URL | Feature |
|---|---|---|
| `GET` | `/chatbot/actions/` | Action log (undo support) |

#### Health

| Method | URL |
|---|---|
| `GET` | `/health/` hoặc `/chatbot/health/` |

---

## 4. Input/Output Format Chi Tiết

### 4.1 `POST /ai/detect/banknote/` — Full Response Schema

```json
{
  "decision": "accept | reject | no_banknote",
  "denomination": "10000 | 20000 | 50000 | 100000 | 200000 | 500000 | null",
  "confidence": 0.9512,
  "method": "color | ai_fallback | none",
  "quality": {
    "blurScore": 145.23,
    "exposureScore": 127.5,
    "status": "ok | blurry | overexposed | underexposed",
    "message": "string"
  },
  "detection": {
    "found": true,
    "confidence": 0.9871,
    "message": "string"
  },
  "allProbabilities": {
    "10000": 0.021,
    "50000": 0.958,
    "100000": 0.021
  },
  "stagesExecuted": ["preprocessing", "detection", "color_classification"],
  "processingTimeMs": 18.5,
  "processingTime": 0.0185,
  "message": "string",
  "pipelineVersion": "hybrid-mvp-v1"
}
```

**Mode `fast`**: bỏ `ai_fallback` stage → chỉ color classification (~3ms).  
**Mode `full`** (default): color → nếu thấp confidence → AI fallback (~15-40ms).

### 4.2 `POST /chatbot/chat/` — ChatResponse Schema

```json
{
  "response": "Bãi xe còn 15 chỗ trống...",
  "intent": "check_slots | book_parking | check_booking | cancel_booking | ...",
  "entities": {"zone": "A", "vehicleType": "car"},
  "suggestions": ["Đặt chỗ ngay", "Xem bản đồ"],
  "data": {},
  "conversationId": "uuid",
  "messageId": "uuid",
  "confidence": 0.85,
  "processingTimeMs": 150,
  "showMap": false,
  "showQrCode": false,
  "clarificationNeeded": false,
  "confirmationNeeded": false,
  "confidenceBreakdown": {"llm": 0.5, "entity": 0.3, "context": 0.2},
  "safetyCode": null,
  "safetyHint": null
}
```

### 4.3 `ESP32Response` Schema

```json
{
  "success": true,
  "event": "check_in_success | check_in_failed | check_out_success | check_out_awaiting_payment | check_out_failed | verify_slot_success | verify_slot_failed",
  "barrierAction": "open | close | no_action",
  "message": "✅ Check-in thành công! Thời gian giới hạn 2h.",
  "gateId": "GATE-IN-01",
  "bookingId": "uuid",
  "plateText": "51A-224.56",
  "amountDue": 50000.0,
  "amountPaid": 50000.0,
  "processingTimeMs": 1250.5,
  "details": {}
}
```

### 4.4 `OccupancyDetectionResponse` — Parking Slots

```json
{
  "camera_id": "string",
  "detection_method": "yolo11n | opencv_fallback",
  "slots": [
    {
      "slot_id": "uuid",
      "slot_code": "A-01",
      "zone_id": "uuid",
      "status": "occupied | available",
      "confidence": 0.87
    }
  ],
  "total_slots": 10,
  "occupied_count": 7,
  "available_count": 3,
  "processing_time_ms": 45.2
}
```

---

## 5. Models & Libraries Đang Dùng

### 5.1 AI Service — Model Stack

| Feature | Primary Model | Fallback 1 | Fallback 2 | Library |
|---|---|---|---|---|
| License Plate Detection | YOLOv8 (fine-tuned `license-plate-finetune-v1m.pt`) | Full image (no detection) | — | `ultralytics==8.4.18` |
| License Plate OCR | TrOCR (`microsoft/trocr-base-printed`) | EasyOCR | Tesseract | `transformers`, `easyocr==1.7.2` |
| Parking Slot Occupancy | YOLO11n (`yolo11n.pt`, COCO classes 2,3,5,7) | OpenCV edge/contour | Pixel intensity | `ultralytics==8.4.18` |
| Banknote Detection | YOLOv8n (từ pipeline) | — | — | `ultralytics==8.4.18` |
| Banknote Classification | MobileNetV3 / EfficientNetV2-S | Color HSV histogram | — | `torch==1.13.1`, `timm==1.0.25` |
| Banknote Security | Siamese Network + OneClass SVM | — | — | `torch==1.13.1` |
| Cash Recognition (legacy) | ResNet50 (`cash_recognition_best.pth`) | — | — | `torch==1.13.1` |
| QR Code Reading | OpenCV (cv2.QRCodeDetector) | pyzbar | — | `opencv-python-headless==4.10.0.84` |

### 5.2 Chatbot Service — LLM Stack

| Component | Library/Model | Version |
|---|---|---|
| LLM Provider | Google Gemini 2.0 Flash | `google-generativeai==0.8.0` |
| Model ID | `gemini-2.0-flash` | — |
| Cache | Redis (DB 6) | `redis==5.0.8` |
| Message Queue | RabbitMQ (proactive events) | `aio-pika==9.4.0` |
| Framework | FastAPI | `0.134.0` |

### 5.3 AI Service — Key Libraries

```
ultralytics==8.4.18          # YOLO v8 + YOLO11n
easyocr==1.7.2               # OCR fallback
torch==1.13.1                # PyTorch
torchvision==0.14.1
timm==1.0.25                 # EfficientNetV2-S, MobileNetV3
transformers                 # TrOCR (HuggingFace)
opencv-python-headless==4.10.0.84
numpy==1.26.4
pillow==12.1.1
```

---

## 6. Docker Container Info

| Container | Image | Expose/Port | Volumes | Networks |
|---|---|---|---|---|
| `ai-service-fastapi` | `./ai-service-fastapi` | `expose 8009` | `ai_models:/app/ml/models`, `ai_datasets:/app/datasets`, `parksmart_media:/app/media` | `parksmart-network` |
| `chatbot-service-fastapi` | `./chatbot-service-fastapi` | `expose 8008` | — | `parksmart-network` |

**Gateway routing:**
- AI Service URL (trong Docker): `http://ai-service-fastapi:8009`
- Chatbot Service URL (trong Docker): `http://chatbot-service-fastapi:8008`
- Gateway env: `AI_SERVICE_URL=http://ai-service-fastapi:8009`, `CHATBOT_SERVICE_URL=http://chatbot-service-fastapi:8008`

**Healthcheck:**
- AI: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8009/health/')"` — interval 30s
- Chatbot: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8008/health/')"` — interval 30s

---

## 7. Frontend Pages Tương Ứng

| Frontend Page | File | AI Feature |
|---|---|---|
| Banknote Detection | `spotlove-ai/src/pages/BanknoteDetectionPage.tsx` | `POST /ai/detect/banknote/` (full/fast mode toggle) |
| Check-in / Check-out | `spotlove-ai/src/pages/CheckInOutPage.tsx` | `POST /ai/parking/check-in/`, `check-out/`, `scan-plate/` |
| Kiosk (self-service) | `spotlove-ai/src/pages/KioskPage.tsx` | ESP32 check-in/out + `POST /ai/parking/esp32/cash-payment/` |
| Camera Monitoring | `spotlove-ai/src/pages/CamerasPage.tsx` | `GET /ai/cameras/list`, `/snapshot`, `/stream` |
| Admin — ESP32 Devices | `spotlove-ai/src/pages/admin/AdminESP32Page.tsx` | `GET /ai/parking/esp32/devices`, `/devices/{id}/logs` |
| Chatbot | Embedded trong `UserDashboard.tsx` / `SupportPage.tsx` | `POST /chatbot/chat/`, `GET /chatbot/quick-actions/` |
| Map | `spotlove-ai/src/pages/MapPage.tsx` | Chatbot `showMap: true` response |

---

## 8. ⚠️ Gotchas & Known Issues

- [ ] **[SECURITY]** Camera RTSP URL hardcode credentials trong source code:
  ```
  DEFAULT_PLATE_CAMERA_URL = "rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main"
  ```
  File: [ai-service-fastapi/app/routers/camera.py](../../backend-microservices/ai-service-fastapi/app/routers/camera.py) và [esp32.py](../../backend-microservices/ai-service-fastapi/app/routers/esp32.py#L166). Cần move sang env vars.

- [ ] **[WARNING]** `GEMINI_API_KEY` trong docker-compose.yml được set với `${GEMINI_API_KEY:-}` (empty default) → chatbot **không có LLM** nếu .env không set key. Service vẫn startup OK nhưng `llmEnabled: false`.

- [ ] **[WARNING]** Model file `license-plate-finetune-v1m.pt` tại `/app/app/models/` — nếu không có file này, detector fallback sang full-image (toàn bộ ảnh làm plate region). Không gây crash nhưng kết quả sai.

- [ ] **[WARNING]** Docker compose dùng `expose` thay vì `ports` cho ai-service (8009) và chatbot-service (8008) → không bind ra host. Muốn debug trực tiếp phải thêm `ports: "8009:8009"`.

- [ ] **[NOTE]** ESP32 device registry lưu in-memory (`_esp32_devices` dict) → **mất khi container restart**. Được seed lại 2 default devices (`GATE-IN-01`, `GATE-OUT-01`) mỗi lần startup.

- [ ] **[NOTE]** `torch==1.13.1` trong requirements.txt là version cũ (2022). Nếu cần CUDA, phải cài torch version phù hợp GPU driver. Container hiện tại chạy CPU-only.

- [ ] **[NOTE]** Check-out flow trong `esp32.py` đang dùng **static test image** thay vì camera thực cho plate OCR (code bị comment, dùng `_LOCAL_IMAGES / "51A-224.56.jpg"`). Cần bỏ comment phần camera thực khi deploy.

- [ ] **[NOTE]** TrOCR (`microsoft/trocr-base-printed`) sẽ auto-download từ HuggingFace lần đầu. Trong Docker build offline environment cần pre-bake model hoặc mount volume.

- [ ] **[NOTE]** `ai-service-fastapi` có thể tốn nhiều RAM do torch + ultralytics + easyocr loaded cùng lúc. Không có memory limit trong docker-compose.

---

## 9. Checklist cho Implementer

- [ ] **Model files cần có** trong `ai_models` Docker volume:
  - `yolo11n.pt` — parking occupancy (auto-download nếu missing)
  - `license-plate-finetune-v1m.pt` — **phải copy thủ công** vào `/app/app/models/`
  - `cash_recognition_best.pth` — train hoặc copy vào `/app/ml/models/`
  - Banknote pipeline models (multiple `.pth` files) trong `/app/ml/models/`

- [ ] **Env vars cần set** trong `.env`:
  ```
  GEMINI_API_KEY=your_key_here
  GEMINI_MODEL=gemini-2.0-flash
  ```

- [ ] **Fix security**: Move RTSP camera credentials sang env var:
  ```
  PLATE_CAMERA_URL=rtsp://...
  QR_CAMERA_URL=http://...
  ```

- [ ] **Pattern reference**: Xem `ai-service-fastapi/app/routers/detection.py` cho pattern lazy-singleton model loading.

- [ ] Breaking changes: Không có — đây là codebase đang active development.

---

## 10. Nguồn

| # | File | Mô tả |
|---|---|---|
| 1 | `ai-service-fastapi/app/main.py` | Routers registry, lifespan hooks |
| 2 | `ai-service-fastapi/app/routers/detection.py` | Detection endpoints |
| 3 | `ai-service-fastapi/app/routers/parking.py` | Parking endpoints (500+ lines) |
| 4 | `ai-service-fastapi/app/routers/esp32.py` | ESP32 endpoints (1500+ lines) |
| 5 | `ai-service-fastapi/app/routers/camera.py` | Camera streaming |
| 6 | `ai-service-fastapi/app/routers/metrics.py` | Model metrics |
| 7 | `ai-service-fastapi/app/routers/training.py` | Training triggers |
| 8 | `ai-service-fastapi/app/config.py` | Settings & model paths |
| 9 | `ai-service-fastapi/requirements.txt` | Full dependency list |
| 10 | `chatbot-service-fastapi/app/main.py` | Chatbot startup, Gemini init |
| 11 | `chatbot-service-fastapi/app/routers/chat.py` | Chat + feedback endpoints |
| 12 | `chatbot-service-fastapi/app/routers/conversation.py` | Conversation CRUD |
| 13 | `chatbot-service-fastapi/requirements.txt` | Chatbot dependencies |
| 14 | `docker-compose.yml` | Container config, volumes, ports |
| 15 | `docs/PARKSMART_SYSTEM_PROMPT.md` | Architecture reference |
| 16 | `spotlove-ai/src/services/api/ai.api.ts` | Frontend types + API calls |
| 17 | `spotlove-ai/src/services/api/chatbot.api.ts` | Frontend chatbot API |
