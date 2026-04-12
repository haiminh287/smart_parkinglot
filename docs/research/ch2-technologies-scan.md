# Research Report: Scan toàn bộ công nghệ ParkSmart — Bổ sung Chương 2

**Task:** Bổ sung Chương 2 (Cơ sở lý thuyết) | **Date:** 2026-04-07 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Ch2 hiện chỉ cover 4 mục:** DRF, ReactJS, IoT (ESP32+Arduino), Chatbot (Gemini LLM).
>
> **CÒN THIẾU ít nhất 12 công nghệ/stack quan trọng** đang dùng thực tế trong codebase:
>
> 1. FastAPI + Pydantic + SQLAlchemy (4 services)
> 2. Go + Gin + Gorilla WebSocket (2 services)
> 3. AI/CV: YOLO, TrOCR, MobileNetV3, ResNet50, EasyOCR, OpenCV, PyTorch
> 4. MySQL 8.0, Redis 7, RabbitMQ 3, Celery 5.4
> 5. Docker Compose (15+ containers), Nginx, Cloudflare Tunnel
> 6. Vite, TypeScript, TailwindCSS, Radix UI, shadcn/ui, Redux Toolkit, TanStack Query, Zod
> 7. Vitest, Playwright, pytest, NUnit (Unity)
> 8. Unity (C#) — Parking Simulator 3D
> 9. Microservices Architecture (API Gateway, Event-Driven, Database-per-service)

---

## 2. TECHNOLOGIES ALREADY IN CH2 (đã cover)

| #   | Công nghệ             | Mục Ch2 |
| --- | --------------------- | ------- |
| 1   | Django REST Framework | 2.1     |
| 2   | ReactJS               | 2.2     |
| 3   | IoT (ESP32 + Arduino) | 2.3     |
| 4   | Chatbot (Gemini LLM)  | 2.4     |

---

## 3. TECHNOLOGIES NOT YET IN CH2 (cần thêm vào báo cáo)

### 3.1 FastAPI (Python async web framework)

- **Version:** 0.134.0
- **Used in:** ai-service-fastapi, chatbot-service-fastapi, payment-service-fastapi, notification-service-fastapi
- **Key libraries bundled:**
  - Pydantic 2.12.5 (ai-service) / 2.9.0–2.10.4 (other services) — data validation & settings
  - Pydantic-Settings 2.13.1 / 2.5.0–2.7.1 — env-based config
  - SQLAlchemy 2.0.47 (ai-service) / 2.0.35–2.0.36 (others) — async ORM
  - Alembic 1.13.0–1.14.0 — database migrations (chatbot, payment, notification)
  - Uvicorn 0.41.0 / 0.30.0–0.34.0 — ASGI server
  - HTTPX 0.28.1 / 0.27.0 — async HTTP client (inter-service communication)
  - PyMySQL 1.1.2 — MySQL driver
- **Why it matters:** 4/9 microservices dùng FastAPI thay vì Django, chạy AI inference, chatbot streaming, payment processing, notification — tất cả yêu cầu async I/O

### 3.2 Go + Gin + Gorilla WebSocket

- **Go version:** 1.22
- **Gin version:** 1.10.0 (github.com/gin-gonic/gin)
- **Gin CORS:** 1.7.2 (github.com/gin-contrib/cors)
- **Gorilla WebSocket:** 1.5.3 (github.com/gorilla/websocket) — chỉ trong realtime-service
- **go-redis:** v9.7.0 (github.com/redis/go-redis/v9) — chỉ trong gateway-service
- **Used in:**
  - `gateway-service-go` — API Gateway (port 8000): routing, session management (Redis), CORS, auth proxy
  - `realtime-service-go` — WebSocket server (port 8006): real-time parking updates, slot status broadcast
- **Why it matters:** High-performance gateway xử lý toàn bộ API routing + concurrent WebSocket connections cho real-time updates

### 3.3 AI/Computer Vision Stack

#### 3.3.1 YOLO (Ultralytics)

- **Package:** ultralytics==8.4.18
- **Models used:**
  - `yolo11n.pt` — Parking slot occupancy detection (vehicle classes: car, motorcycle, bus, truck — COCO IDs 2,3,5,7)
  - `license-plate-finetune-v1m.pt` — License plate detection (YOLOv8 fine-tuned)
  - YOLOv8n — Banknote region detection (Stage 1 of cash pipeline)
- **Config:** IOU threshold 0.15, Confidence threshold 0.25
- **Source:** `app/engine/slot_detection.py`, `app/engine/plate_detector.py`, `app/engine/detector.py`

#### 3.3.2 TrOCR (Microsoft Transformer OCR)

- **Model:** `microsoft/trocr-base-printed` (HuggingFace)
- **Library:** transformers (via huggingface_hub==1.5.0)
- **Used for:** License plate OCR — Priority #1 in OCR cascade
- **Architecture:** Vision Encoder-Decoder (ViT encoder + text decoder)
- **Source:** `app/engine/plate_ocr.py:167-182`

#### 3.3.3 EasyOCR

- **Version:** 1.7.2
- **Used for:** Fallback OCR (Priority #2) khi TrOCR fail hoặc không available
- **Config:** Reader(['en'], gpu=False)
- **Source:** `app/engine/plate_ocr.py:220-229`

#### 3.3.4 MobileNetV3-Large (Banknote Classification)

- **Library:** torchvision.models.mobilenet_v3_large
- **Architecture:** Multi-branch model:
  - Branch 1: CNN backbone (MobileNetV3-Large, feature dim = 960)
  - Branch 2: Gabor texture features (24 dim)
  - Branch 3: LBP micro-texture features (10 dim)
  - Branch 4: Edge structural features (36 dim)
  - Total texture features: 70 dim
- **Used for:** Stage 2B — AI fallback classifier for Vietnamese banknote denominations (8 classes)
- **Source:** `app/engine/ai_classifier.py`, `app/engine/feature_extractors.py`

#### 3.3.5 ResNet50 (Cash Recognition Training)

- **Library:** torchvision.models.resnet50 (weights=ResNet50_Weights.IMAGENET1K_V2)
- **Used for:** Training pipeline for Vietnamese banknote denomination classification
- **Technique:** Transfer learning from ImageNet
- **Source:** `app/ml/training/train_cash_recognition.py`

#### 3.3.6 OpenCV

- **Version:** opencv-python-headless==4.10.0.84
- **Used for:** Image preprocessing, QR code decoding (cv2.QRCodeDetector), color space conversion (HSV), Gabor/LBP feature extraction, frame capture from camera streams (RTSP/HTTP/DroidCam)
- **Source:** Throughout `app/engine/` modules

#### 3.3.7 PyTorch

- **Version:** torch>=2.0.0,<2.6.0; torchvision>=0.15.0,<0.21.0
- **Aux:** timm==1.0.25 (PyTorch Image Models)
- **Used for:** Deep learning runtime cho tất cả AI models (YOLO, MobileNetV3, ResNet50, TrOCR)

#### 3.3.8 Pipeline Architecture

- **Cash Recognition Pipeline** (4 stages):
  - Stage 0: Preprocessing (quality gate + white balance)
  - Stage 1: Banknote Detection (YOLOv8n)
  - Stage 2A: Color-Based Denomination (HSV histogram)
  - Dynamic Confidence Check → PASS → Final → FAIL → Stage 2B: AI Classifier (MobileNetV3)
- **Plate Recognition Pipeline** (cascade fallback):
  - Step 1: Plate Detection (YOLOv8 fine-tuned)
  - Step 2: OCR cascade: TrOCR → EasyOCR → Tesseract
  - Post-processing: Vietnamese plate format validation
- **Slot Occupancy Pipeline**:
  - YOLO11n object detection → background subtraction → pixel histogram
- **Source:** `app/engine/pipeline.py`, `app/engine/plate_pipeline.py`, `app/engine/slot_detection.py`

### 3.4 Database & Message Queue & Task Queue

#### MySQL 8.0

- **Image:** mysql:8.0
- **Port:** 3307 (host) → 3306 (container)
- **Database:** parksmartdb
- **Used by:** ALL 9 microservices (shared logical database)
- **Driver:** mysqlclient==2.2.4 (Django services), PyMySQL==1.1.2 (FastAPI services)

#### Redis 7

- **Image:** redis:7-alpine
- **Port:** 6379
- **Database allocation (6 DBs):**
  - DB 0: Celery broker + result backend (booking-service)
  - DB 1: Gateway session store (gateway-service-go)
  - DB 2: Booking service cache
  - DB 3: Parking service cache / Chatbot service
  - DB 4: Vehicle service cache
  - DB 5: Realtime service pub/sub
  - DB 6: Chatbot conversation cache
- **Used for:** Caching, session management, pub/sub, Celery broker

#### RabbitMQ 3

- **Image:** rabbitmq:3-management-alpine
- **Ports:** 5672 (AMQP), 15672 (Management UI)
- **Python client:** aio-pika==9.4.0 (async, chatbot-service)
- **Used by:** auth-service, booking-service, parking-service, chatbot-service
- **Used for:** Event-driven messaging, proactive chatbot notifications

#### Celery 5.4.0

- **Used in:** booking-service (Django)
- **Components:** Worker + Beat (periodic tasks)
- **Broker:** Redis DB 0
- **Tasks:** Booking expiration, scheduled cleanup, async notification dispatch
- **Source:** `booking-service/booking_service/celery.py`

### 3.5 Docker & Containerization

#### Docker Compose

- **Total containers (docker-compose.yml):** 14 services:
  1. mysql
  2. redis
  3. rabbitmq
  4. auth-service (Django + Gunicorn)
  5. parking-service (Django + Gunicorn)
  6. vehicle-service (Django + Gunicorn)
  7. booking-service (Django + Gunicorn)
  8. booking-celery-worker
  9. booking-celery-beat
  10. notification-service-fastapi (Uvicorn)
  11. realtime-service-go
  12. payment-service-fastapi (Uvicorn)
  13. ai-service-fastapi (Uvicorn)
  14. chatbot-service-fastapi (Uvicorn)
  15. gateway-service-go
- **Production overlay (docker-compose.prod.yml)** thêm: 16. nginx (nginx:alpine)
- **Volumes:** mysql_data, redis_data, rabbitmq_data, ai_models, ai_datasets, parksmart_media
- **Network:** parksmart-network (bridge)

#### Gunicorn 22.0.0

- **Used in:** Django services (auth, parking, vehicle, booking) — production WSGI server
- **Source:** Dockerfile CMD

#### Uvicorn

- **Versions:** 0.30.0–0.41.0
- **Used in:** FastAPI services (ai, chatbot, payment, notification) — production ASGI server

### 3.6 Nginx (Reverse Proxy)

- **Image:** nginx:alpine
- **Config:** `infra/nginx/nginx.conf`
- **Features used:**
  - Serve static frontend (spotlove-ai/dist/)
  - Reverse proxy /api/\* → gateway-service-go:8000
  - WebSocket upgrade /ws/\* → realtime-service-go:8006
  - Gzip compression
  - Security headers (X-Frame-Options, CSP, HSTS, X-Content-Type-Options)
  - Static asset caching (1 year, immutable)
- **Domains:** app.ghepdoicaulong.shop, api.ghepdoicaulong.shop, ws.ghepdoicaulong.shop

### 3.7 Cloudflare Tunnel

- **Tool:** cloudflared
- **Config:** `infra/cloudflare/cloudflared/config.yml`
- **Purpose:** Expose local development/production to internet without port forwarding
- **Ingress rules:**
  - app.ghepdoicaulong.shop → localhost:80 (Nginx → FE)
  - api.ghepdoicaulong.shop → localhost:80 (Nginx → API)
  - ws.ghepdoicaulong.shop → localhost:8006 (WebSocket direct)

### 3.8 Frontend Stack (chi tiết — beyond "ReactJS")

#### Core

- **React:** 18.3.1
- **TypeScript:** 5.8.3
- **Vite:** 5.4.19 (build tool, dev server, HMR)
  - Plugin: @vitejs/plugin-react-swc 3.11.0 (SWC compiler thay Babel)

#### UI Framework

- **TailwindCSS:** 3.4.17 + tailwindcss-animate 1.0.7 + autoprefixer 10.4.21
- **Radix UI:** Full primitive set (25+ components): accordion, dialog, dropdown-menu, popover, tabs, toast, tooltip, etc.
- **shadcn/ui pattern:** Radix UI + TailwindCSS + class-variance-authority 0.7.1 + tailwind-merge 2.6.0 + clsx 2.1.1
- **Icons:** lucide-react 0.462.0
- **Charts:** recharts 2.15.4
- **Carousel:** embla-carousel-react 8.6.0

#### State Management & Data Fetching

- **Redux Toolkit:** 2.11.2 + react-redux 9.2.0 — global state
- **TanStack React Query:** 5.83.0 — server state, caching, refetching
- **Axios:** 1.13.2 — HTTP client

#### Forms & Validation

- **React Hook Form:** 7.61.1
- **Zod:** 3.25.76 — schema validation
- **@hookform/resolvers:** 3.10.0 — Zod-React Hook Form bridge

#### Routing

- **React Router DOM:** 6.30.1

#### Other notable

- **date-fns:** 3.6.0 — date formatting
- **qrcode.react:** 4.2.0 — QR code generation
- **sonner:** 1.7.4 — toast notifications
- **next-themes:** 0.3.0 — dark mode
- **js-cookie:** 3.0.5 — cookie management
- **vaul:** 0.9.9 — drawer component
- **cmdk:** 1.1.1 — command palette

### 3.9 Testing Stack

#### Frontend

- **Vitest:** 3.2.4 — unit test runner (Vite-native)
  - @testing-library/react 16.0.0 — React component testing
  - @testing-library/jest-dom 6.6.0 — DOM matchers
  - jsdom 20.0.3 — browser environment
- **Playwright:** 1.58.2 — E2E browser testing
  - Config: `playwright.config.ts` — single worker, HTML + list reporter, trace on retry

#### Backend (Python)

- **pytest:** 8.3.0–9.0.2 across services
  - pytest-asyncio — async test support
  - pytest-cov — coverage reporting
  - pytest-django — Django integration

#### Unity

- **NUnit Framework** — Unit testing (EditMode + PlayMode)
  - EditMode: DataModelsTests, MockDataProviderTests, SharedBookingStateTests
  - PlayMode: WaypointGraphTests, ParkingSlotTests, BarrierControllerTests
  - AutoTestRunner (custom CI runner)

### 3.10 Unity — Parking Simulator 3D (C#)

- **Engine:** Unity (URP — Universal Render Pipeline)
- **Language:** C#
- **Key libraries:**
  - Newtonsoft.Json (JSON serialization — API communication)
  - NativeWebSocket (WebSocket client — real-time slot updates)
  - UnityWebRequest (HTTP client — REST API calls)
- **Architecture:** API → AuthManager → ApiService (REST + WebSocket)
- **Features:** 3D parking simulation, vehicle movement, barrier control, real-time slot occupancy, QR scan integration
- **Source:** `ParkingSimulatorUnity/Assets/Scripts/`

### 3.11 Microservices Architecture Pattern

- **Total services:** 9 microservices + 3 infrastructure services
- **Patterns used:**
  - **API Gateway** (Go Gin) — single entry point, routing, auth, session, CORS
  - **Database-per-service** (logical — all share MySQL but separate Django apps / FastAPI schemas)
  - **Event-driven** (Redis pub/sub + RabbitMQ AMQP)
  - **Task queue** (Celery worker + beat for async/scheduled tasks)
  - **Cascade fallback** (AI pipeline: multiple models with prioritized fallback)
  - **Service-to-service** communication via internal Docker network (HTTP)
  - **Data denormalization** across services for performance

### 3.12 OAuth2 Social Login

- **Providers:** Google, Facebook
- **Implementation:** Custom OAuth2 flow in auth-service (Django)
- **Config:** GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET
- **Redirect URIs:** `api.ghepdoicaulong.shop/api/auth/{provider}/callback/`
- **Source:** `auth-service/auth_service/settings.py:130-138`

### 3.13 Google Generative AI (Gemini)

- **Package:** google-generativeai==0.8.0
- **Model:** gemini-2.0-flash (configurable via env: `GEMINI_MODEL`)
- **Used in:** chatbot-service-fastapi
- **Note:** Ch2 đã cover Chatbot + Gemini LLM nhưng CHƯA mention google-generativeai SDK, hoặc version cụ thể

---

## 4. Service Architecture Summary

| Service               | Framework                  | Server          | Port     | Language |
| --------------------- | -------------------------- | --------------- | -------- | -------- |
| auth-service          | Django 5.2.12 + DRF 3.15.2 | Gunicorn 22.0.0 | 8001     | Python   |
| booking-service       | Django 5.2.12 + DRF 3.15.2 | Gunicorn 22.0.0 | 8002     | Python   |
| parking-service       | Django 5.2.12 + DRF 3.15.2 | Gunicorn 22.0.0 | 8003     | Python   |
| vehicle-service       | Django 5.2.12 + DRF 3.15.2 | Gunicorn 22.0.0 | internal | Python   |
| notification-service  | FastAPI 0.134.0            | Uvicorn 0.34.0  | 8005     | Python   |
| realtime-service      | Gin 1.10.0                 | Go built-in     | 8006     | Go 1.22  |
| payment-service       | FastAPI 0.134.0            | Uvicorn 0.34.0  | 8007     | Python   |
| chatbot-service       | FastAPI 0.134.0            | Uvicorn 0.30.0  | 8008     | Python   |
| ai-service            | FastAPI 0.134.0            | Uvicorn 0.41.0  | 8009     | Python   |
| gateway-service       | Gin 1.10.0                 | Go built-in     | 8000     | Go 1.22  |
| booking-celery-worker | Celery 5.4.0               | —               | —        | Python   |
| booking-celery-beat   | Celery 5.4.0               | —               | —        | Python   |

---

## 5. Gợi ý cấu trúc Ch2 mới

Dựa trên scan, Ch2 nên bổ sung THÊM các mục sau (giữ nguyên 4 mục cũ):

```
Chương 2: Cơ sở lý thuyết

2.1 Django REST Framework (giữ nguyên)
2.2 ReactJS và hệ sinh thái Frontend (mở rộng)
    2.2.1 React 18 + TypeScript
    2.2.2 Vite (Build Tool)
    2.2.3 TailwindCSS + shadcn/ui (UI Framework)
    2.2.4 Redux Toolkit + TanStack React Query (State Management)
    2.2.5 Zod + React Hook Form (Form Validation)
2.3 IoT — ESP32 + Arduino (giữ nguyên)
2.4 Chatbot — Gemini LLM (giữ nguyên, bổ sung google-generativeai SDK)

=== CÁC MỤC MỚI CẦN THÊM ===

2.5 FastAPI (Python Async Web Framework)
2.6 Go + Gin Framework + Gorilla WebSocket
2.7 Trí tuệ nhân tạo và Thị giác máy tính
    2.7.1 YOLO (Object Detection)
    2.7.2 TrOCR (Transformer OCR)
    2.7.3 MobileNetV3-Large (Image Classification)
    2.7.4 OpenCV (Image Processing)
    2.7.5 PyTorch (Deep Learning Runtime)
2.8 Cơ sở dữ liệu và Message Queue
    2.8.1 MySQL 8.0
    2.8.2 Redis 7
    2.8.3 RabbitMQ 3 + Celery
2.9 Docker và Containerization
2.10 Kiến trúc Microservices
    2.10.1 API Gateway Pattern
    2.10.2 Event-Driven Architecture
    2.10.3 Database-per-Service
2.11 Nginx + Cloudflare Tunnel (Deployment)
2.12 Unity (Parking Simulator 3D)
2.13 Kiểm thử phần mềm
    2.13.1 Vitest + Playwright (Frontend)
    2.13.2 pytest (Backend Python)
    2.13.3 NUnit (Unity C#)
```

---

## 6. Nguồn

| #   | File/Path                                                             | Mô tả                                  |
| --- | --------------------------------------------------------------------- | -------------------------------------- |
| 1   | `backend-microservices/ai-service-fastapi/requirements.txt`           | AI service dependencies (90+ packages) |
| 2   | `backend-microservices/chatbot-service-fastapi/requirements.txt`      | Chatbot dependencies                   |
| 3   | `backend-microservices/payment-service-fastapi/requirements.txt`      | Payment dependencies                   |
| 4   | `backend-microservices/notification-service-fastapi/requirements.txt` | Notification dependencies              |
| 5   | `backend-microservices/gateway-service-go/go.mod`                     | Go gateway dependencies                |
| 6   | `backend-microservices/realtime-service-go/go.mod`                    | Go realtime dependencies               |
| 7   | `backend-microservices/docker-compose.yml`                            | 15 service definitions                 |
| 8   | `backend-microservices/docker-compose.prod.yml`                       | Production overlay + nginx             |
| 9   | `spotlove-ai/package.json`                                            | Frontend 60+ dependencies              |
| 10  | `infra/nginx/nginx.conf`                                              | Nginx reverse proxy config             |
| 11  | `infra/cloudflare/cloudflared/config.yml`                             | Cloudflare tunnel ingress              |
| 12  | `backend-microservices/ai-service-fastapi/app/engine/*.py`            | AI pipeline source code                |
| 13  | `backend-microservices/auth-service/auth_service/settings.py`         | OAuth2 config                          |
| 14  | `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino`      | ESP32 firmware                         |
| 15  | `hardware/arduino/barrier_control/barrier_control.ino`                | Arduino firmware                       |
| 16  | `backend-microservices/auth-service/requirements.txt`                 | Django service deps                    |
| 17  | `backend-microservices/booking-service/requirements.txt`              | Booking + Celery deps                  |
| 18  | `ParkingSimulatorUnity/Assets/Scripts/**/*.cs`                        | Unity C# source                        |
