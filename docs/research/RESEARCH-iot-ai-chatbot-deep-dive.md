# Research Report: IoT/Hardware + AI Pipeline + Chatbot Deep Dive

**Date:** 2026-04-06 | **Type:** Codebase Analysis (Mixed)

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **Hardware**: ESP32 (WiFi + OLED + HTTP) ↔ Arduino (Servo barrier) qua UART 9600 baud. 2 nút bấm trigger check-in/check-out → AI Service xử lý QR + plate → trả barrier_action → mở/đóng cổng.
> 2. **AI Service (port 8009)**: 5 AI pipelines — License Plate (YOLOv8 + TrOCR), Slot Occupancy (YOLO11n + IoU), Banknote Recognition (Hybrid: Color HSV + MobileNetV3), Cash Recognition (ResNet50), QR Code (OpenCV). Tổng cộng 25+ endpoints.
> 3. **Chatbot (port riêng)**: Gemini `gemini-3-flash-preview` + 5-stage pipeline (Intent→Gate→Safety→Action→Response) + Hybrid Confidence (0.5*LLM + 0.3*entity + 0.2\*context) + Booking Wizard multi-step + Proactive notifications via RabbitMQ.

---

## 2. PART A: IoT/Hardware

### 2.1 Arduino — Barrier Control

| Thuộc tính   | Chi tiết                                                |
| ------------ | ------------------------------------------------------- |
| **File**     | `hardware/arduino/barrier_control/barrier_control.ino`  |
| **MCU**      | Arduino (Uno/Nano — any with Servo library)             |
| **Hardware** | 2x Servo motors (barrier gates) + Built-in LED (Pin 13) |
| **Protocol** | UART 9600 baud, newline-terminated commands             |
| **Library**  | `Servo.h`                                               |

**Pin Assignments:**

| Pin        | Function                             | PWM Range                       |
| ---------- | ------------------------------------ | ------------------------------- |
| Pin 10     | Servo Entry Gate (Lane 1 — Cổng VÀO) | 1500μs (closed) → 3000μs (open) |
| Pin 9      | Servo Exit Gate (Lane 2 — Cổng RA)   | 1500μs (closed) → 3000μs (open) |
| Pin 13     | Status LED (built-in)                | HIGH when any gate open         |
| Pin 0 (RX) | UART RX ← ESP32 TX2 (GPIO17)         | —                               |

**Command Protocol (UART):**

| Command     | Action           | ACK Response                          |
| ----------- | ---------------- | ------------------------------------- |
| `OPEN_1\n`  | Open entry gate  | `ACK:OPEN_1`                          |
| `CLOSE_1\n` | Close entry gate | `ACK:CLOSE_1`                         |
| `OPEN_2\n`  | Open exit gate   | `ACK:OPEN_2`                          |
| `CLOSE_2\n` | Close exit gate  | `ACK:CLOSE_2`                         |
| `STATUS\n`  | Query both gates | `LANE1:OPEN/CLOSED,LANE2:OPEN/CLOSED` |

**Auto-close:** Both barriers auto-close after **5 seconds** (`AUTO_CLOSE_MS = 5000`).

**Wiring:**

```
ESP32 GPIO17 (TX2) ──► Arduino RX (Pin 0)
ESP32 GND          ──► Arduino GND
Servo IN  signal   ──► Arduino Pin 10
Servo OUT signal   ──► Arduino Pin 9
Servo VCC          ──► 5V (external power recommended)
Servo GND          ──► GND
```

---

### 2.2 ESP32 — Gate Controller

| Thuộc tính        | Chi tiết                                                                |
| ----------------- | ----------------------------------------------------------------------- |
| **File**          | `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino`        |
| **MCU**           | ESP32 DevKit (WiFi + Bluetooth)                                         |
| **Firmware**      | `v1.0.0-parksmart`                                                      |
| **Communication** | WiFi HTTP/JSON → AI Service + UART → Arduino                            |
| **Libraries**     | WiFi, HTTPClient, ArduinoJson v7+, Wire, Adafruit_GFX, Adafruit_SSD1306 |

**Pin Assignments:**

| Pin           | Function              | Mode                      |
| ------------- | --------------------- | ------------------------- |
| GPIO 4        | Button CHECK-IN       | INPUT_PULLUP (active LOW) |
| GPIO 5        | Button CHECK-OUT      | INPUT_PULLUP (active LOW) |
| GPIO 16 (RX2) | UART RX ← Arduino TX  | Serial2                   |
| GPIO 17 (TX2) | UART TX → Arduino RX  | Serial2                   |
| GPIO 2        | Status LED (built-in) | OUTPUT                    |
| GPIO 21 (SDA) | OLED I2C SDA          | Wire                      |
| GPIO 22 (SCL) | OLED I2C SCL          | Wire                      |

**Display:**

- OLED SSD1306 128×64 at I2C address `0x3D`
- Displays: boot logo, license plate text on check-in/check-out

**Constants:**

| Constant             | Value   | Purpose                              |
| -------------------- | ------- | ------------------------------------ |
| `DEBOUNCE_MS`        | 300ms   | Button debounce                      |
| `AUTO_CLOSE_SEC`     | 5s      | Auto-close barrier after opening     |
| `HTTP_TIMEOUT_MS`    | 30000ms | HTTP timeout (plate scan takes time) |
| `SERIAL_BAUD`        | 115200  | Debug serial                         |
| `UART2_BAUD`         | 9600    | UART to Arduino                      |
| `HEARTBEAT_INTERVAL` | 10000ms | Heartbeat every 10s                  |

**Communication Flow:**

```
[Button Press GPIO4/5]
    ↓
[ESP32] ──HTTP POST JSON──► [AI Service :8009/ai/parking/esp32/check-in/]
    ↓                               ↓
[Parse JSON response]         [QR scan + Plate OCR + Booking verify]
    ↓                               ↓
[Read barrier_action]         [Return {barrierAction: "open"/"close"}]
    ↓
[UART2] ──"OPEN_1/OPEN_2"──► [Arduino] ──► [Servo opens gate]
    ↓
[Auto-close after 5s] ──"CLOSE_1/CLOSE_2"──► [Arduino]
```

**HTTP Endpoints Called by ESP32:**

| Endpoint                       | Method | Purpose                     |
| ------------------------------ | ------ | --------------------------- |
| `/ai/parking/esp32/check-in/`  | POST   | Gate-in flow                |
| `/ai/parking/esp32/check-out/` | POST   | Gate-out flow               |
| `/ai/parking/esp32/register`   | POST   | Device registration at boot |
| `/ai/parking/esp32/heartbeat`  | POST   | Health heartbeat every 10s  |
| `/ai/parking/esp32/log`        | POST   | Remote logging to backend   |

**Auth Headers:** `X-Gateway-Secret`, `X-Device-Token`, `Content-Type: application/json`

**UART Sanitization:** ESP32 strips non-printable chars (0x00-0x1F, 0x7F+) from Arduino ACKs to prevent JSON encoding errors from UART noise.

---

## 3. PART B: AI Service Deep Dive

### 3.1 Service Overview

| Thuộc tính    | Chi tiết                                     |
| ------------- | -------------------------------------------- |
| **Framework** | FastAPI (Python)                             |
| **Port**      | 8009                                         |
| **Version**   | 2.0.0                                        |
| **DB**        | MySQL (parksmartdb) via SQLAlchemy           |
| **Auth**      | Gateway Auth Middleware (`X-Gateway-Secret`) |

**Directory Structure (`ai-service-fastapi/app/`):**

```
app/
├── main.py              # FastAPI app, lifespan, routers
├── config.py            # Settings (env-based)
├── database.py          # SQLAlchemy session
├── dependencies.py      # DI helpers
├── middleware/           # GatewayAuthMiddleware
├── routers/
│   ├── camera.py        # Camera streaming & virtual frames
│   ├── detection.py     # License plate, cash, banknote detection
│   ├── esp32.py         # ESP32 gate check-in/check-out
│   ├── metrics.py       # Model metrics & prediction logs
│   ├── parking.py       # Parking check-in/check-out/occupancy
│   └── training.py      # Model training triggers
├── engine/
│   ├── plate_pipeline.py    # License plate end-to-end
│   ├── plate_detector.py    # YOLOv8 plate detection
│   ├── plate_ocr.py         # TrOCR + EasyOCR + Tesseract
│   ├── pipeline.py          # Banknote recognition (Hybrid MVP)
│   ├── detector.py          # Banknote YOLOv8n detector
│   ├── color_classifier.py  # HSV color denomination
│   ├── ai_classifier.py     # MobileNetV3-Large AI fallback
│   ├── feature_extractors.py# Gabor, LBP, Edge features
│   ├── preprocessing.py     # Quality gate + white balance
│   ├── slot_detection.py    # YOLO11n slot occupancy
│   ├── qr_reader.py         # QR code reading (OpenCV)
│   ├── camera_capture.py    # IP camera frame capture
│   ├── camera_monitor.py    # Background camera monitoring
│   └── cash_session.py      # Cash payment session manager
├── ml/
│   ├── banknote/            # Bank-grade training scripts
│   ├── inference/           # Cash recognition inference
│   └── training/            # Training utilities
├── models/
│   ├── ai.py                # PredictionLog, ModelVersion ORM
│   └── license-plate-finetune-v1m.pt  # YOLO weights
└── schemas/
    ├── base.py              # CamelModel (snake→camel aliases)
    ├── ai.py                # Detection/training schemas
    └── esp32_device.py      # ESP32 device schemas
```

### 3.2 All AI Endpoints

#### Camera Router (`/ai/cameras/`)

| Endpoint               | Method | Purpose                                            |
| ---------------------- | ------ | -------------------------------------------------- |
| `/ai/cameras/list`     | GET    | List all cameras (physical + 6 virtual)            |
| `/ai/cameras/frame`    | POST   | Receive JPEG frame from Unity (X-Camera-ID header) |
| `/ai/cameras/snapshot` | GET    | Get single JPEG from camera_id or URL              |
| `/ai/cameras/stream`   | GET    | MJPEG multipart stream for live viewing            |

**Cameras configured:**

- `plate-camera-ezviz` — EZVIZ RTSP camera for plate reading
- `qr-camera-droidcam` — DroidCam MJPEG for QR scanning
- 6 virtual cameras from Unity: `virtual-f1-overview`, `virtual-f2-overview`, `virtual-gate-in`, `virtual-gate-out`, `virtual-zone-south`, `virtual-zone-north`

#### Detection Router (`/ai/detect/`)

| Endpoint                    | Method             | Purpose                                    |
| --------------------------- | ------------------ | ------------------------------------------ |
| `/ai/detect/license-plate/` | POST (image)       | License plate OCR (YOLOv8 + TrOCR)         |
| `/ai/detect/cash/`          | POST (image)       | Vietnamese cash denomination (ResNet50)    |
| `/ai/detect/banknote/`      | POST (image, mode) | Banknote recognition (Hybrid MVP pipeline) |

#### Parking Router (`/ai/parking/`)

| Endpoint                        | Method            | Purpose                                                                    |
| ------------------------------- | ----------------- | -------------------------------------------------------------------------- |
| `/ai/parking/scan-plate/`       | POST (image)      | Plate OCR only (no booking)                                                |
| `/ai/parking/check-in/`         | POST (image + QR) | Full check-in: QR parse → booking verify → plate OCR → match → checkin API |
| `/ai/parking/check-out/`        | POST              | Full check-out: QR + plate + payment verify                                |
| `/ai/parking/detect-occupancy/` | POST              | Slot occupancy from camera frame + slot bboxes                             |

#### ESP32 Router (`/ai/parking/esp32/`)

| Endpoint                               | Method | Purpose                                                    |
| -------------------------------------- | ------ | ---------------------------------------------------------- |
| `/ai/parking/esp32/check-in/`          | POST   | ESP32 gate-in: QR camera scan + plate OCR + barrier action |
| `/ai/parking/esp32/check-out/`         | POST   | ESP32 gate-out: QR + plate + payment check                 |
| `/ai/parking/esp32/verify-slot/`       | POST   | Slot-level QR verification                                 |
| `/ai/parking/esp32/cash-payment/`      | POST   | Cash inserted → AI detect denomination → accumulate        |
| `/ai/parking/esp32/status/`            | GET    | Health + camera status                                     |
| `/ai/parking/esp32/register`           | POST   | Device registration                                        |
| `/ai/parking/esp32/heartbeat`          | POST   | Device heartbeat                                           |
| `/ai/parking/esp32/log`                | POST   | Remote device logging                                      |
| `/ai/parking/esp32/devices/`           | GET    | List registered devices                                    |
| `/ai/parking/esp32/devices/{id}/logs/` | GET    | Device log history                                         |

#### Training Router (`/ai/train/`)

| Endpoint              | Method | Purpose                                            |
| --------------------- | ------ | -------------------------------------------------- |
| `/ai/train/cash/`     | POST   | Train cash recognition (ResNet50) in background    |
| `/ai/train/banknote/` | POST   | Train bank-grade pipeline (3 stages) in background |

#### Metrics Router (`/ai/models/`)

| Endpoint                  | Method | Purpose                          |
| ------------------------- | ------ | -------------------------------- |
| `/ai/models/metrics/`     | GET    | Aggregate metrics for all models |
| `/ai/models/predictions/` | GET    | Paginated prediction logs        |
| `/ai/models/versions/`    | GET    | Model version history            |

#### Health

| Endpoint      | Method |
| ------------- | ------ |
| `/health/`    | GET    |
| `/ai/health/` | GET    |

---

### 3.3 License Plate Recognition Pipeline

**Models & Versions:**

- **Detection:** YOLOv8 finetune → `license-plate-finetune-v1m.pt` (custom trained on Vietnamese plates)
- **OCR (priority):**
  1. **TrOCR** — `microsoft/trocr-base-printed` (Hugging Face transformer, best for 2-row Vietnamese plates)
  2. **EasyOCR** — fallback if TrOCR unavailable
  3. **Tesseract** — last resort

**Pipeline Flow:**

```
[Image bytes]
    ↓
Stage 1: YOLO Detect Plate Region
    ├── conf_threshold = 0.20
    ├── Returns: PlateDetectionResult(found, box, cropped)
    └── Fallback: use full image if no model
    ↓
Stage 2: OCR Read Text
    ├── Blur detection (Laplacian variance < 80 = blurry)
    ├── Preprocessing: resize to 64px height, CLAHE, denoise, Otsu binarize
    ├── Scale for TrOCR: ≥200px height
    ├── TrOCR inference (proxy confidence 0.90)
    ├── Fallback → EasyOCR → Tesseract
    └── Post-processing: normalize OCR errors (O→0, I→1, L→1, etc.)
    ↓
Stage 3: Format Validation
    ├── Vietnamese patterns: \d{2}[A-Z]\d?-\d{3}.\d{2}
    ├── Examples: 51A-224.56, 30K1-123.45
    └── Reformat to standard: PREFIX-XXX.XX
    ↓
Decision:
    ├── SUCCESS: valid format + confidence ≥ 0.55
    ├── LOW_CONFIDENCE: valid format but conf < 0.55
    ├── INVALID_FORMAT: text read but wrong format
    ├── BLURRY: blur detected + conf < 0.4
    ├── NOT_FOUND: no plate region detected
    └── ERROR: image decode failure
```

---

### 3.4 Slot Occupancy Detection

**Model:** YOLO11n (auto-downloads via Ultralytics if not at configured path)

**Vehicle COCO Class IDs:** `{2: car, 3: motorcycle, 5: bus, 7: truck}`

**Detection Method:**

```
[Camera frame + slot bounding boxes]
    ↓
YOLO11n inference on full frame
    ├── conf_threshold = 0.25 (YOLO_PARKING_CONF_THRESHOLD)
    ├── Extract vehicle bounding boxes
    ↓
For each parking slot:
    ├── Compute IoU(slot_bbox, vehicle_bbox)
    ├── If IoU ≥ 0.15 (YOLO_PARKING_IOU_THRESHOLD) → OCCUPIED
    ├── Else → AVAILABLE
    └── Confidence = IoU score (or 1-IoU for available)
    ↓
Fallback (no YOLO):
    ├── Background subtraction (MOG2)
    ├── Edge density analysis
    └── Pixel intensity histogram
```

**Config:**

- `YOLO_PARKING_MODEL_PATH`: `/app/ml/models/yolo11n.pt`
- `YOLO_PARKING_IOU_THRESHOLD`: 0.15
- `YOLO_PARKING_CONF_THRESHOLD`: 0.25

---

### 3.5 Banknote Recognition Pipeline (Hybrid MVP)

**Pipeline Version:** `hybrid-mvp-v1`

**Models:**

- **Detection:** YOLOv8n (`banknote_yolov8n.pt`) — or full-image fallback
- **Color Classifier:** HSV histogram analysis (no ML model, rule-based)
- **AI Fallback:** MobileNetV3-Large multi-branch (`banknote_mobilenetv3.pth`)
  - 4 branches: CNN (960-dim) + Gabor (48-dim) + LBP (32-dim) + Edge (48-dim) → fused 1088-dim → classifier

**Denominations (9 classes):**
`1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000*, 500000`
(_200000 VND excluded from AI model — handled by color classifier only_)

**Pipeline Flow:**

```
[Image BGR]
    ↓
Stage 0: Preprocessing
    ├── Quality Gate: blur (Laplacian var < 50) + exposure (brightness 40-220)
    └── White Balance: LAB channel equalization
    ↓
Stage 1: Banknote Detection (YOLOv8n)
    ├── Detect banknote region, crop
    └── Fallback: full image as banknote
    ↓
Stage 2A: Color-Based Classification (HSV)
    ├── Compute 180-bin hue histogram (filter S > 30)
    ├── Score each denomination by hue center ± range
    ├── Dynamic threshold:
    │   ├── SAFE group (100k, 200k — distinctive): ≥ 0.75
    │   └── DANGER group (overlapping colors): ≥ 0.90
    └── If meets threshold → ACCEPT → done
    ↓
Out-of-Vocabulary Guard
    ├── If color detected denomination not in AI vocab (e.g. 200k)
    └── → Trust color result, skip AI fallback
    ↓
Stage 2B: AI Fallback (MobileNetV3-Large)
    ├── Enhanced multi-branch model:
    │   ├── Branch 1: MobileNetV3-Large features (960-dim)
    │   ├── Branch 2: Gabor texture features → 48-dim
    │   ├── Branch 3: LBP micro-texture → 32-dim
    │   └── Branch 4: Edge structural → 48-dim
    ├── Fusion: concatenate → 1088-dim → MLP classifier
    └── If conf > 0.3 → ACCEPT, else LOW_CONFIDENCE
```

**Color Map (HSV Hue Centers):**

| Denomination | Hue Center ± Range | Color             | Group  |
| ------------ | ------------------ | ----------------- | ------ |
| 1,000 VND    | 32 ± 8             | Yellow-Green      | DANGER |
| 2,000 VND    | 20 ± 5             | Brown-Olive       | DANGER |
| 5,000 VND    | 105 ± 10           | Blue-Gray         | DANGER |
| 10,000 VND   | 24 ± 6             | Yellow-Brown      | DANGER |
| 20,000 VND   | 110 ± 10           | Blue              | DANGER |
| 50,000 VND   | 160 ± 15           | Pink-Purple       | DANGER |
| 100,000 VND  | 55 ± 15            | Green             | SAFE   |
| 200,000 VND  | 5 ± 10 / 172 ± 8   | Red-Brown (wraps) | SAFE   |
| 500,000 VND  | 92 ± 12            | Cyan-Blue         | DANGER |

**Fast Mode:** Color-only (skips AI fallback), ~3-5ms latency.

---

### 3.6 Cash Recognition (ResNet50)

| Thuộc tính   | Chi tiết                                 |
| ------------ | ---------------------------------------- |
| **Model**    | ResNet50 custom-trained                  |
| **File**     | `ml/models/cash_recognition_best.pth`    |
| **Version**  | `resnet50_v1`                            |
| **Endpoint** | `POST /ai/detect/cash/`                  |
| **Training** | `POST /ai/train/cash/` (background task) |

---

### 3.7 QR Code Processing

| Thuộc tính           | Chi tiết                                                           |
| -------------------- | ------------------------------------------------------------------ |
| **Library**          | OpenCV `cv2.QRCodeDetector` + `cv2.QRCodeDetectorAruco` (fallback) |
| **No external deps** | Pure OpenCV, no pyzbar needed                                      |

**Detection Strategy:**

1. Single QR detection on BGR frame
2. Grayscale + histogram equalization → retry
3. Multi-QR ArUco detector fallback

**QR Data Format:**

```json
{
  "booking_id": "uuid",
  "user_id": "uuid",
  "vehicle_license_plate": "51A-224.56",
  "slot_code": "A-01"
}
```

Also supports plain text (booking ID only → `user_id` defaults to "system").

---

### 3.8 Cash Payment Session

- In-memory session per booking (30-min TTL)
- Tracks running total of cash denominations inserted
- Thread-safe with `threading.Lock`
- Production note: should migrate to Redis

---

### 3.9 Training Pipelines

**Cash Recognition Training:**

- ResNet50 transfer learning
- Background task via FastAPI `BackgroundTasks`
- Saves model version to DB

**Banknote Bank-Grade Training (3 stages):**

1. **EfficientNetV2-S** classifier
2. **Siamese** network (similarity learning)
3. **OneClass** anomaly detector

- Optional MLflow integration
- Saves combined model version to DB

---

### 3.10 Model Summary

| Model                   | Architecture                     | Version                      | Purpose                     | Weights File                    |
| ----------------------- | -------------------------------- | ---------------------------- | --------------------------- | ------------------------------- |
| License Plate Detection | YOLOv8 (finetune)                | v1m                          | Detect plate region         | `license-plate-finetune-v1m.pt` |
| Plate OCR               | TrOCR                            | microsoft/trocr-base-printed | Read plate text             | HuggingFace auto-download       |
| Slot Occupancy          | YOLO11n                          | COCO pretrained              | Vehicle in slot detection   | `yolo11n.pt` (auto-download)    |
| Banknote Detection      | YOLOv8n                          | custom                       | Detect banknote region      | `banknote_yolov8n.pt`           |
| Banknote AI Classifier  | MobileNetV3-Large (multi-branch) | enhanced                     | Denomination classification | `banknote_mobilenetv3.pth`      |
| Cash Recognition        | ResNet50                         | v1                           | Cash denomination           | `cash_recognition_best.pth`     |
| EfficientNetV2-S        | (training only)                  | bank-grade-v1                | Bank-grade classifier       | trained on demand               |

---

## 4. PART C: Chatbot Service Deep Dive

### 4.1 Service Overview

| Thuộc tính       | Chi tiết                                            |
| ---------------- | --------------------------------------------------- |
| **Framework**    | FastAPI (Python)                                    |
| **Version**      | v3.0                                                |
| **LLM**          | Google Gemini — model: **`gemini-3-flash-preview`** |
| **LLM SDK**      | `google-generativeai`                               |
| **LLM Config**   | temperature=0.3, top_p=0.9, max_tokens=1024         |
| **DB**           | MySQL (parksmartdb) via SQLAlchemy                  |
| **Cache**        | Redis (DB 3) — graceful degradation if unavailable  |
| **Messaging**    | RabbitMQ — proactive event consumer                 |
| **Architecture** | Hexagonal (Domain / Application / Infrastructure)   |

### 4.2 Directory Structure

```
chatbot-service-fastapi/app/
├── main.py                  # FastAPI app + lifespan (Redis, RabbitMQ, singletons)
├── config.py                # Settings (Gemini key, service URLs)
├── database.py              # SQLAlchemy
├── dependencies.py          # Auth (X-User-ID from gateway)
├── middleware/               # GatewayAuthMiddleware
├── routers/
│   ├── chat.py              # POST /chatbot/chat/ — main pipeline
│   ├── conversation.py      # CRUD conversations + history
│   ├── actions.py           # Action history (undo support)
│   ├── notifications.py     # Proactive notifications
│   └── preferences.py       # User chat preferences
├── engine/
│   └── orchestrator.py      # v3.0 Pipeline orchestrator
├── application/
│   ├── dto/                 # IntentDecision, PipelineContext, etc.
│   └── services/
│       ├── intent_service.py      # 3-step intent (classify→extract→build)
│       ├── safety_service.py      # Safety validation with reason codes
│       ├── action_service.py      # Action dispatcher + booking wizard
│       ├── response_service.py    # LLM response generation
│       ├── memory_service.py      # User style/memory with anti-noise
│       ├── observability_service.py # AI metrics collector
│       └── proactive_service.py   # Proactive notifications + anti-spam
├── domain/
│   ├── policies/
│   │   └── handoff.py       # Human handoff policy
│   ├── value_objects/
│   │   ├── intent.py        # 16 intents enum + required entities
│   │   ├── confidence.py    # HybridConfidence formula
│   │   ├── safety_result.py # SafetyResult + SafetyCode enum
│   │   ├── proactive.py     # Notification priority + cooldown
│   │   └── ai_metrics.py    # AIMetricType enum
│   └── exceptions.py
├── infrastructure/
│   ├── llm/
│   │   └── gemini_client.py # Gemini async wrapper
│   ├── cache/
│   │   └── redis.py         # Redis client
│   ├── external/
│   │   └── service_client.py # HTTP calls to booking/parking/vehicle services
│   └── messaging/
│       └── rabbitmq.py      # RabbitMQ consumer
└── models/
    └── chatbot.py           # ORM: Conversation, ChatMessage, ActionLog, etc.
```

### 4.3 Chatbot Pipeline (v3.0 — 5 Stages)

```
[User Message]
    ↓
┌─── Pre-Pipeline ───────────────────────────────┐
│ 1. Booking Wizard active? → Handle wizard step  │
│ 2. Previous turn = "confirm"? → Yes/No handler  │
└────────────────────────────────────────────────┘
    ↓
Stage 1: Intent Detection (🔥 2.1 — 3 steps)
    ├── Context follow-up check (reuse previous intent if clarifying)
    ├── Step 1: classify_intent()   — Gemini: "what intent + why"
    ├── Step 2: extract_entities()  — Schema-driven extraction
    ├── Step 3: build_decision()    — Merge + hybrid confidence
    └── Keyword fallback if LLM unavailable
    ↓
Handoff Check
    ├── frustration_score > 0.9 → handoff
    ├── clarification_count ≥ 6 → handoff
    └── Explicit keywords: "nhân viên", "agent", "manager"
    ↓
Stage 2: Confidence Gate (🔥 2.2)
    ├── hybrid_confidence = 0.5*LLM + 0.3*entity + 0.2*context
    ├── High-stakes (book/cancel/checkout) → higher threshold
    ├── Result: "execute" | "confirm" | "clarify"
    └── "clarify"/"confirm" → return early, ask user
    ↓
Stage 3: Safety Rules (🔥 2.3)
    ├── Validates: slot available, no double booking, in hours, etc.
    ├── Returns SafetyResult(ok, code, hint, details)
    └── 11 SafetyCodes: SLOT_NOT_AVAILABLE, DOUBLE_BOOKING, etc.
    ↓
Stage 4: Execute Action
    ├── ActionService dispatches to internal microservices via HTTP
    ├── Smart booking: auto-find slot, auto-resolve vehicle
    └── Booking wizard: multi-step floor → zone → book
    ↓
Stage 5: Generate Response
    ├── ResponseService uses Gemini to generate natural-language reply
    ├── Adapts to user style (from MemoryService)
    └── Includes suggestions, showMap, showQrCode flags
    ↓
Post-Pipeline:
    ├── Memory update (🔥 2.4 — anti-noise rules)
    ├── AI metrics recording (🔥 2.6)
    └── Store in Conversation context for next turn
```

### 4.4 Intent Types (16 total)

| Intent               | High-Stakes | Required Entities |
| -------------------- | ----------- | ----------------- |
| `greeting`           | No          | —                 |
| `goodbye`            | No          | —                 |
| `check_availability` | No          | vehicle_type      |
| `book_slot`          | **Yes**     | vehicle_type      |
| `rebook_previous`    | No          | —                 |
| `cancel_booking`     | **Yes**     | —                 |
| `check_in`           | No          | —                 |
| `check_out`          | **Yes**     | —                 |
| `my_bookings`        | No          | —                 |
| `current_parking`    | No          | —                 |
| `pricing`            | No          | —                 |
| `help`               | No          | —                 |
| `feedback`           | No          | —                 |
| `handoff`            | No          | —                 |
| `unknown`            | No          | —                 |
| `operating_hours`    | No          | —                 |

### 4.5 Hybrid Confidence Formula

```
hybrid_confidence = 0.5 × llm_confidence
                  + 0.3 × entity_completeness
                  + 0.2 × context_match_score
```

**Context Match Rules:**

- First message (no history) → 1.0
- Natural flow (e.g., check_availability → book_slot) → 1.0
- Same intent repeated → 0.8
- Abrupt topic switch → 0.5

### 4.6 Booking Wizard (v3.0)

Multi-step interactive flow:

```
Step 1: User says "đặt chỗ ô tô"
    → Fetch floors with zones matching vehicle_type
    → Show floor selection UI
Step 2: User picks floor
    → Show zones on that floor with available slots
Step 3: User picks zone
    → Auto-book: find slot + find vehicle + create booking
    → Return QR code + booking confirmation
```

### 4.7 Proactive Notifications (v2.5)

**Event sources:** RabbitMQ consumer listens for system events

**Anti-spam controls:**
| Control | Rule |
|---------|------|
| Priority | HIGH (5min cooldown), MEDIUM (30min), LOW (2hr) |
| User Active | Suppress non-HIGH if user active within 5 min |
| Hourly Limit | Max 5 notifications per user per hour |

**Event types handled:**

- Slot maintenance alerts
- Booking expiry reminders
- No check-in warnings
- Weather tips

### 4.8 All Chatbot Endpoints

| Endpoint                                     | Method | Purpose                         |
| -------------------------------------------- | ------ | ------------------------------- |
| `POST /chatbot/chat/`                        | POST   | Main chat pipeline              |
| `GET /chatbot/quick-actions/`                | GET    | Quick action buttons for UI     |
| `POST /chatbot/feedback/`                    | POST   | User feedback on response       |
| `GET /chatbot/conversations/`                | GET    | List user conversations         |
| `POST /chatbot/conversations/`               | POST   | Create new conversation         |
| `GET /chatbot/conversations/active/`         | GET    | Get/create active conversation  |
| `GET /chatbot/conversations/{id}/`           | GET    | Get specific conversation       |
| `GET /chatbot/conversations/{id}/messages/`  | GET    | Chat history                    |
| `GET /chatbot/conversations/history/latest/` | GET    | Latest conversation history     |
| `GET /chatbot/actions/`                      | GET    | Action history (undo support)   |
| `GET /chatbot/notifications/`                | GET    | Pending proactive notifications |
| `POST /chatbot/notifications/{id}/`          | POST   | Dismiss/act on notification     |
| `GET /chatbot/preferences/`                  | GET    | User preferences                |
| `PUT /chatbot/preferences/`                  | PUT    | Update preferences              |

---

## 5. ⚠️ Gotchas & Known Issues

- [x] **[NOTE]** ESP32 hardcoded WiFi credentials in `.ino` file (line 45-46). Production should use config portal.
- [x] **[NOTE]** Gemini API key hardcoded in chatbot `config.py` as default — should be env-only.
- [x] **[NOTE]** Cash session uses in-memory dict — data lost on restart. TODO: migrate to Redis.
- [x] **[NOTE]** TrOCR proxy confidence = 0.90 (hardcoded) — not actual per-token confidence from model.
- [x] **[NOTE]** 200,000 VND excluded from AI model training data — handled only by color classifier.
- [x] **[NOTE]** OLED I2C address `0x3D` — some SSD1306 modules use `0x3C` (requires hardware check).

---

## 6. Nguồn

| #   | Source                                                           | Mô tả                                   |
| --- | ---------------------------------------------------------------- | --------------------------------------- |
| 1   | `hardware/arduino/barrier_control/barrier_control.ino`           | Arduino barrier control firmware        |
| 2   | `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino` | ESP32 gate controller firmware          |
| 3   | `backend-microservices/ai-service-fastapi/app/`                  | AI Service source (routers, engine, ml) |
| 4   | `backend-microservices/chatbot-service-fastapi/app/`             | Chatbot Service source                  |
| 5   | `backend-microservices/ai-service-fastapi/app/config.py`         | AI Service configuration                |
| 6   | `backend-microservices/chatbot-service-fastapi/app/config.py`    | Chatbot Service configuration           |
