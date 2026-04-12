# Research Report: ParkSmart — Comprehensive Technical Inventory

**Date:** 2026-04-12 | **Type:** Codebase Inventory | **Purpose:** Graduation Thesis Reference

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **10 microservices** (4 Django, 3 FastAPI, 2 Go, 1 React SPA) + 3 infrastructure services (MySQL 8.0, Redis 7, RabbitMQ 3)
> 2. **5 AI pipelines** (Plate OCR, Slot Detection, Banknote Classification, Cash Recognition, QR Reader) powered by YOLOv8/YOLO11n + TrOCR + MobileNetV3 + ResNet50
> 3. **Chatbot v3.0** sử dụng Gemini `gemini-3-flash-preview` với Hexagonal Architecture, hybrid confidence 0.5×LLM + 0.3×entity + 0.2×context, 16 intents, booking wizard
> 4. **Unity Digital Twin** (2022.3 LTS) mô phỏng bãi đỗ 2 tầng 158 slots, 6 virtual cameras streaming 640×480 @5fps
> 5. **IoT Hardware**: ESP32 (WiFi+OLED+HTTP) ↔ UART 9600 ↔ Arduino (2 servo barriers), auto-close 5s
> 6. **Frontend**: React 18 + Vite 5 + TypeScript 5.8 + Redux Toolkit + TanStack Query + shadcn/ui (51 components) + WebSocket realtime

---

## 2. Frontend — `spotlove-ai/`

### 2.1 Framework & Build

| Attribute       | Value                                                    |
| --------------- | -------------------------------------------------------- |
| Framework       | **React (pure SPA)** — NOT Next.js                       |
| Build tool      | Vite 5.4.19 (`vite.config.ts` present, no `next.config`) |
| Language        | TypeScript 5.8.3                                         |
| Dev server port | 8080                                                     |
| SWC compiler    | `@vitejs/plugin-react-swc` 3.11.0                        |

### 2.2 Core Dependencies (exact versions from `package.json`)

| Package                    | Version                         |
| -------------------------- | ------------------------------- |
| `react`                    | ^18.3.1                         |
| `react-dom`                | ^18.3.1                         |
| `typescript`               | ^5.8.3                          |
| `vite`                     | ^5.4.19                         |
| `@reduxjs/toolkit`         | ^2.11.2                         |
| `react-redux`              | ^9.2.0                          |
| `@tanstack/react-query`    | ^5.83.0                         |
| `react-router-dom`         | ^6.30.1                         |
| `tailwindcss`              | ^3.4.17                         |
| `axios`                    | ^1.13.2                         |
| `react-hook-form`          | ^7.61.1                         |
| `@hookform/resolvers`      | ^3.10.0                         |
| `zod`                      | ^3.25.76                        |
| `recharts`                 | ^2.15.4                         |
| `sonner`                   | ^1.7.4                          |
| `qrcode.react`             | ^4.2.0                          |
| `lucide-react`             | ^0.462.0                        |
| `date-fns`                 | ^3.6.0                          |
| `class-variance-authority` | ^0.7.1                          |
| `tailwind-merge`           | ^2.6.0                          |
| `cmdk`                     | ^1.1.1                          |
| `vaul`                     | ^0.9.9                          |
| `embla-carousel-react`     | ^8.6.0                          |
| `next-themes`              | ^0.3.0 (dark mode, not Next.js) |
| `@supabase/supabase-js`    | ^2.91.0                         |
| `js-cookie`                | ^3.0.5                          |

**Dev dependencies notable:**
| Package | Version |
|---|---|
| `@playwright/test` | ^1.58.2 |
| `vitest` | ^3.2.4 |
| `@testing-library/react` | ^16.0.0 |
| `eslint` | ^9.32.0 |
| `lovable-tagger` | ^1.1.13 |

### 2.3 Pages — 28 total `.tsx` files in `src/pages/`

**Root pages (19):**

| #   | File                        | Mô tả                |
| --- | --------------------------- | -------------------- |
| 1   | `Index.tsx`                 | Landing/home         |
| 2   | `LoginPage.tsx`             | Đăng nhập            |
| 3   | `RegisterPage.tsx`          | Đăng ký              |
| 4   | `AuthCallbackPage.tsx`      | OAuth callback       |
| 5   | `UserDashboard.tsx`         | Dashboard người dùng |
| 6   | `AdminDashboard.tsx`        | Dashboard admin      |
| 7   | `BookingPage.tsx`           | Đặt chỗ              |
| 8   | `MapPage.tsx`               | Bản đồ bãi đỗ        |
| 9   | `HistoryPage.tsx`           | Lịch sử              |
| 10  | `PaymentPage.tsx`           | Thanh toán           |
| 11  | `CheckInOutPage.tsx`        | Check-in/out         |
| 12  | `CamerasPage.tsx`           | Camera giám sát      |
| 13  | `DetectionHistoryPage.tsx`  | Lịch sử nhận diện    |
| 14  | `BanknoteDetectionPage.tsx` | Nhận diện tiền       |
| 15  | `KioskPage.tsx`             | Kiosk self-service   |
| 16  | `SettingsPage.tsx`          | Cài đặt              |
| 17  | `SupportPage.tsx`           | Hỗ trợ               |
| 18  | `PanicButtonPage.tsx`       | Nút khẩn cấp         |
| 19  | `NotFound.tsx`              | 404                  |

**Admin sub-pages (9) — `src/pages/admin/`:**

| #   | File                      |
| --- | ------------------------- |
| 1   | `AdminCamerasPage.tsx`    |
| 2   | `AdminConfigPage.tsx`     |
| 3   | `AdminESP32Page.tsx`      |
| 4   | `AdminRevenuePage.tsx`    |
| 5   | `AdminSlotsPage.tsx`      |
| 6   | `AdminStatsPage.tsx`      |
| 7   | `AdminUsersPage.tsx`      |
| 8   | `AdminViolationsPage.tsx` |
| 9   | `AdminZonesPage.tsx`      |

### 2.4 Components — Total count by folder

| Folder                      | Files                              | List                                                                                                              |
| --------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `src/components/ui/`        | **51 files** (49 `.tsx` + 2 `.ts`) | shadcn/ui components (see below)                                                                                  |
| `src/components/booking/`   | 7                                  | AutoGuaranteeBooking, BookingQRCode, CalendarAutoHold, MultiDayPicker, ParkingLotSelector, PriceSummary, SlotGrid |
| `src/components/dashboard/` | 4                                  | QuickBooking, RecentBookings, SlotOverview, StatsCard                                                             |
| `src/components/map/`       | 2                                  | DirectionsPanel, InteractiveMap                                                                                   |
| `src/components/support/`   | 1                                  | ContactWidget                                                                                                     |
| `src/components/effects/`   | 1                                  | SnowfallEffect                                                                                                    |
| `src/components/layout/`    | 3                                  | AppSidebar, MainLayout, ProtectedRoute                                                                            |
| `src/components/settings/`  | 1                                  | AddVehicleDialog                                                                                                  |
| `src/components/` (root)    | 3                                  | DevLogPanel, ErrorBoundary, NavLink                                                                               |
| **TOTAL**                   | **73**                             |                                                                                                                   |

### 2.5 shadcn/ui Components — 51 files in `src/components/ui/`

accordion, alert-dialog, alert, aspect-ratio, avatar, badge, breadcrumb, button-variants, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input-otp, input, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toast, toaster, toggle-group, toggle-variants, toggle, tooltip, use-toast

### 2.6 Services & API Layer

**`src/services/api/` — 11 files:**

| File                  | Mô tả                            |
| --------------------- | -------------------------------- |
| `axios.client.ts`     | Axios instance cấu hình          |
| `endpoints.ts`        | Centralized endpoint definitions |
| `auth.api.ts`         | Auth API calls                   |
| `booking.api.ts`      | Booking API calls                |
| `parking.api.ts`      | Parking API calls                |
| `vehicle.api.ts`      | Vehicle API calls                |
| `notification.api.ts` | Notification API calls           |
| `ai.api.ts`           | AI service API calls             |
| `chatbot.api.ts`      | Chatbot API calls                |
| `admin.api.ts`        | Admin API calls                  |
| `incident.api.ts`     | Incident API calls               |

**`src/services/business/` — 8 files:**

| File                      | Mô tả                  |
| ------------------------- | ---------------------- |
| `auth.service.ts`         | Auth business logic    |
| `booking.service.ts`      | Booking business logic |
| `parking.service.ts`      | Parking business logic |
| `vehicle.service.ts`      | Vehicle business logic |
| `notification.service.ts` | Notification logic     |
| `admin.service.ts`        | Admin logic            |
| `incident.service.ts`     | Incident logic         |
| `index.ts`                | Barrel export          |

**`src/services/websocket.service.ts`** — WebSocket realtime service

**`src/services/index.ts`** — Service barrel export

### 2.7 Redux Store — 5 slices

| Slice               | File                                    | State quản lý              |
| ------------------- | --------------------------------------- | -------------------------- |
| `authSlice`         | `src/store/slices/authSlice.ts`         | User auth state            |
| `parkingSlice`      | `src/store/slices/parkingSlice.ts`      | Slot/zone/lot availability |
| `bookingSlice`      | `src/store/slices/bookingSlice.ts`      | Booking state              |
| `notificationSlice` | `src/store/slices/notificationSlice.ts` | Notifications              |
| `websocketSlice`    | `src/store/slices/websocketSlice.ts`    | WS connection state        |

Store config: `src/store/index.ts` — `configureStore` from Redux Toolkit

### 2.8 Hooks — 8 files in `src/hooks/`

`useAuth.ts`, `useBooking.ts`, `useParking.ts`, `useNotifications.ts`, `useWebSocketConnection.ts`, `use-mobile.tsx`, `use-toast.ts`, `index.ts`

### 2.9 Contexts — 6 files in `src/contexts/`

`AuthContext.tsx`, `ThemeContext.tsx`, `auth-context.ts`, `theme-context.ts`, `use-auth.ts`, `use-theme.ts`

### 2.10 Utilities — `src/lib/`

| File           | Mô tả                             |
| -------------- | --------------------------------- |
| `utils.ts`     | General utilities (clsx, cn)      |
| `dijkstra.ts`  | Dijkstra pathfinding (navigation) |
| `webLogger.ts` | Web logging utility               |

### 2.11 WebSocket Implementation

- **File:** `src/services/websocket.service.ts`
- **Protocol:** Native WebSocket (ws:// / wss://)
- **Server:** Connects to realtime-service-go port 8006
- **URL pattern:** `ws://hostname:8006/ws/parking/` (public) or `ws://hostname:8006/ws/user/{userId}/` (authenticated)
- **Message format:** `{ type: string, data: object }` (Django Channels format)
- **Message types broadcast:**
  - `slot.status_update`, `zone.availability_update`, `lot.availability_update`, `slots.batch_update`
  - `booking.status_update`, `booking.created`, `booking.cancelled`, `parking.cost_update`
  - `notification`
  - `incident.reported`, `incident.resolved`
  - `ping`, `pong`, `error`
- **Features:** Auto-reconnect (max 5 attempts, 3s delay), heartbeat ping every 30s
- **Redux integration:** Dispatches directly to Redux store slices on message receipt

### 2.12 Types — `src/types/parking.ts`

### 2.13 Testing

- **Unit:** Vitest 3.2.4 + @testing-library/react 16.0.0
- **E2E:** Playwright 1.58.2 — config at `playwright.config.ts`, tests in `e2e/`

---

## 3. Backend Microservices — `backend-microservices/`

### 3.1 Service Inventory — Complete

| #   | Service                        | Language/Framework             | Port (Host:Container) | Key Dependencies                                                              |
| --- | ------------------------------ | ------------------------------ | --------------------- | ----------------------------------------------------------------------------- |
| 1   | `auth-service`                 | **Django 5.2.12** + DRF 3.15.2 | 8001:8000             | mysqlclient, redis 5.2.1, gunicorn 22.0.0                                     |
| 2   | `booking-service`              | **Django 5.2.12** + DRF 3.15.2 | 8002:8000             | celery 5.4.0, redis 5.2.1, mysqlclient, gunicorn 22.0.0                       |
| 3   | `parking-service`              | **Django 5.2.12** + DRF 3.15.2 | 8003:8000             | redis 5.2.1, mysqlclient, gunicorn 22.0.0                                     |
| 4   | `vehicle-service`              | **Django 5.2.12** + DRF 3.15.2 | (expose only):8000    | redis 5.2.1, mysqlclient, gunicorn 22.0.0                                     |
| 5   | `notification-service-fastapi` | **FastAPI 0.134.0**            | (expose only):8005    | SQLAlchemy 2.0.36, PyMySQL, httpx, alembic 1.14.0                             |
| 6   | `payment-service-fastapi`      | **FastAPI 0.134.0**            | (expose only):8007    | SQLAlchemy 2.0.36, PyMySQL, httpx, alembic 1.14.0                             |
| 7   | `chatbot-service-fastapi`      | **FastAPI 0.134.0**            | (expose only):8008    | google-generativeai 0.8.0, redis 5.0.8, aio-pika 9.4.0, SQLAlchemy 2.0.35     |
| 8   | `ai-service-fastapi`           | **FastAPI 0.134.0**            | 8009:8009             | ultralytics 8.4.18, torch ≥2.0<2.6, timm 1.0.25, easyocr 1.7.2, opencv 4.10.0 |
| 9   | `gateway-service-go`           | **Go 1.22** + Gin 1.10.0       | 8000:8000             | go-redis/v9 9.7.0, uuid 1.6.0                                                 |
| 10  | `realtime-service-go`          | **Go 1.22** + Gin 1.10.0       | 8006:8006             | gorilla/websocket 1.5.3                                                       |

**Background workers:**

| Worker                  | Framework    | Purpose                            |
| ----------------------- | ------------ | ---------------------------------- |
| `booking-celery-worker` | Celery 5.4.0 | Async task processing              |
| `booking-celery-beat`   | Celery Beat  | Periodic tasks (auto-expire, etc.) |

### 3.2 Infrastructure Services (from `docker-compose.yml`)

| Service  | Image                          | Port(s)                | Volumes                                       | Health Check                                       |
| -------- | ------------------------------ | ---------------------- | --------------------------------------------- | -------------------------------------------------- |
| MySQL    | `mysql:8.0`                    | 3307:3306              | `mysql_data:/var/lib/mysql`, `init-mysql.sql` | mysqladmin ping, 10s interval, 10 retries          |
| Redis    | `redis:7-alpine`               | 6379:6379              | `redis_data:/data`                            | redis-cli ping, 10s interval, 5 retries            |
| RabbitMQ | `rabbitmq:3-management-alpine` | 5672:5672, 15672:15672 | `rabbitmq_data:/var/lib/rabbitmq`             | rabbitmq-diagnostics ping, 30s interval, 5 retries |

### 3.3 Redis Database Allocation

| DB # | Service                              |
| ---- | ------------------------------------ |
| 0    | Celery broker + result backend       |
| 1    | Auth service / Gateway session store |
| 2    | Booking service                      |
| 3    | Parking service                      |
| 4    | Vehicle service                      |
| 5    | Realtime service                     |
| 6    | Chatbot service                      |

### 3.4 Docker Volumes (6 named)

`mysql_data`, `redis_data`, `rabbitmq_data`, `ai_models`, `ai_datasets`, `parksmart_media`

### 3.5 Docker Network

- Single bridge: `parksmart-network`

### 3.6 Shared Library — `backend-microservices/shared/`

| File                     | Purpose                               |
| ------------------------ | ------------------------------------- |
| `gateway_middleware.py`  | Gateway auth middleware (Django)      |
| `gateway_permissions.py` | Permission classes                    |
| `permissions.py`         | Base permissions                      |
| `setup.py`               | pip installable as `parksmart_shared` |

---

## 4. AI Service — `ai-service-fastapi/`

### 4.1 ML Library Versions (from `requirements.txt`)

| Library                  | Version          | Purpose                                    |
| ------------------------ | ---------------- | ------------------------------------------ |
| `ultralytics`            | 8.4.18           | YOLOv8/YOLO11 object detection             |
| `torch`                  | ≥2.0.0, <2.6.0   | PyTorch deep learning                      |
| `torchvision`            | ≥0.15.0, <0.21.0 | Vision transforms                          |
| `timm`                   | 1.0.25           | Pre-trained models (MobileNetV3, ResNet50) |
| `easyocr`                | 1.7.2            | OCR fallback                               |
| `opencv-python-headless` | 4.10.0.84        | Image processing                           |
| `scikit-image`           | 0.25.2           | Image processing                           |
| `pillow`                 | 12.1.1           | Image I/O                                  |
| `numpy`                  | 1.26.4           | Numerical                                  |
| `matplotlib`             | 3.10.8           | Visualization                              |
| `shapely`                | 2.1.2            | Geometric operations                       |
| `polars`                 | 1.38.1           | Data processing                            |
| `huggingface_hub`        | 1.5.0            | Model downloads                            |
| `safetensors`            | 0.7.0            | Model loading                              |
| `fastapi`                | 0.134.0          | Web framework                              |
| `SQLAlchemy`             | 2.0.47           | ORM                                        |
| `PyMySQL`                | 1.1.2            | MySQL driver                               |

### 4.2 Routers — 6 files in `app/routers/`

| Router         | Mô tả                                               |
| -------------- | --------------------------------------------------- |
| `camera.py`    | Camera frame ingestion, streaming                   |
| `detection.py` | Plate/banknote detection endpoints                  |
| `esp32.py`     | ESP32 device check-in/check-out/verify/cash payment |
| `metrics.py`   | AI metrics & observability                          |
| `parking.py`   | Parking-related AI (scan plate, check-in/out)       |
| `training.py`  | Model training trigger endpoints                    |

### 4.3 Engine — 16 files in `app/engine/`

| File                    | Purpose                                        |
| ----------------------- | ---------------------------------------------- |
| `pipeline.py`           | Main detection pipeline orchestration          |
| `plate_detector.py`     | YOLOv8 license plate detection                 |
| `plate_ocr.py`          | TrOCR / EasyOCR license plate text recognition |
| `plate_pipeline.py`     | Full plate pipeline (detect → crop → OCR)      |
| `slot_detection.py`     | YOLO11n parking slot occupancy detection       |
| `detector.py`           | Generic detector wrapper                       |
| `ai_classifier.py`      | Banknote AI classification                     |
| `color_classifier.py`   | HSV color-based banknote classification        |
| `feature_extractors.py` | Feature extraction (MobileNetV3, ResNet50)     |
| `cash_session.py`       | Cash payment session management                |
| `camera_capture.py`     | Camera frame capture                           |
| `camera_monitor.py`     | Camera health monitoring                       |
| `preprocessing.py`      | Image preprocessing                            |
| `qr_reader.py`          | QR code reading (OpenCV)                       |
| `__init__.py`           | Package init                                   |

### 4.4 ML Models

| Model               | File/Path                                  | Purpose                              |
| ------------------- | ------------------------------------------ | ------------------------------------ |
| YOLOv8 (fine-tuned) | `app/models/license-plate-finetune-v1m.pt` | License plate detection              |
| YOLO11n             | `yolo11n.pt` (auto-download)               | Parking slot occupancy               |
| MobileNetV3         | `banknote_mobilenetv3.pth`                 | Banknote denomination classification |
| ResNet50            | `cash_recognition_best.pth`                | Cash recognition                     |
| TrOCR               | HuggingFace (auto-download)                | License plate OCR                    |

### 4.5 Five AI Pipelines

| #   | Pipeline                    | Models Used                     | Endpoint                                                                     |
| --- | --------------------------- | ------------------------------- | ---------------------------------------------------------------------------- |
| 1   | **Plate Recognition**       | YOLOv8 + TrOCR/EasyOCR          | `/ai/parking/scan-plate/`, `/ai/parking/check-in/`, `/ai/parking/check-out/` |
| 2   | **Slot Detection**          | YOLO11n                         | Camera-based occupancy                                                       |
| 3   | **Banknote Classification** | Hybrid: HSV color + MobileNetV3 | `/ai/detect/banknote/`                                                       |
| 4   | **Cash Recognition**        | ResNet50                        | `/ai/parking/esp32/cash-payment/`                                            |
| 5   | **QR Reader**               | OpenCV                          | QR code scanning                                                             |

### 4.6 ML Training Code — `app/ml/`

| Folder       | Files                                      | Purpose                    |
| ------------ | ------------------------------------------ | -------------------------- |
| `banknote/`  | `train_classifier.py`, `train_security.py` | Banknote model training    |
| `inference/` | `cash_recognition.py`                      | Cash recognition inference |
| `training/`  | `train_cash_recognition.py`                | Cash model training        |

---

## 5. Chatbot Service — `chatbot-service-fastapi/`

### 5.1 Architecture: **Hexagonal (Ports & Adapters)**

```
app/
├── application/         ← Use cases / Application Services
│   ├── dto/             ← Data Transfer Objects
│   └── services/        ← 7 application services
├── domain/              ← Domain core (no dependencies)
│   ├── exceptions.py
│   ├── policies/        ← handoff.py
│   └── value_objects/   ← intent.py, confidence.py, safety_result.py, proactive.py, ai_metrics.py
├── engine/              ← Orchestrator (pipeline coordinator)
│   └── orchestrator.py
├── infrastructure/      ← External adapters
│   ├── cache/           ← redis.py
│   ├── external/        ← service_client.py (HTTP to other services)
│   ├── llm/             ← gemini_client.py
│   └── messaging/       ← rabbitmq.py
├── middleware/           ← gateway_auth.py
├── models/              ← chatbot.py (SQLAlchemy ORM)
├── routers/             ← 5 FastAPI routers
├── schemas/             ← Pydantic schemas
├── config.py
├── database.py
├── dependencies.py
└── main.py
```

### 5.2 LLM Configuration

| Parameter         | Value                    | Source                                   |
| ----------------- | ------------------------ | ---------------------------------------- |
| Provider          | Google Generative AI     | `google-generativeai==0.8.0`             |
| Model             | `gemini-3-flash-preview` | `app/config.py` → `GEMINI_MODEL`         |
| Temperature       | 0.3                      | `gemini_client.py` → `generation_config` |
| Top-p             | 0.9                      | `gemini_client.py` → `generation_config` |
| Max output tokens | 1024                     | `gemini_client.py` → `generation_config` |

### 5.3 Intent Types — 16 intents (from `app/domain/value_objects/intent.py`)

| #   | Intent               | High Stakes? |
| --- | -------------------- | ------------ |
| 1   | `greeting`           | No           |
| 2   | `goodbye`            | No           |
| 3   | `check_availability` | No           |
| 4   | `book_slot`          | **Yes**      |
| 5   | `rebook_previous`    | No           |
| 6   | `cancel_booking`     | **Yes**      |
| 7   | `check_in`           | No           |
| 8   | `check_out`          | **Yes**      |
| 9   | `my_bookings`        | No           |
| 10  | `current_parking`    | No           |
| 11  | `pricing`            | No           |
| 12  | `help`               | No           |
| 13  | `feedback`           | No           |
| 14  | `handoff`            | No           |
| 15  | `unknown`            | No           |
| 16  | `operating_hours`    | No           |

### 5.4 Hybrid Confidence Formula (from `app/domain/value_objects/confidence.py`)

```
final_confidence = 0.5 × llm_confidence
                 + 0.3 × entity_completeness
                 + 0.2 × context_match_score
```

- `entity_completeness` = fraction of required entities present (1.0 if none required)
- `context_match_score` = intent-to-conversation-context alignment

### 5.5 Pipeline (from `orchestrator.py`)

```
Wizard → Intent → Confidence Gate → Safety → Action → Response → Memory
```

**v3.0 improvements:**

- 🔥 2.1: IntentService tách 3 bước (classify → extract → build)
- 🔥 2.2: Hybrid Confidence
- 🔥 2.3: SafetyResult with reason code
- 🔥 2.4: Memory anti-noise
- 🔥 2.5: Proactive cooldown + priority
- 🔥 2.6: AI Observability
- 🔥 3.0: Booking wizard multi-step (floor → zone → book)

### 5.6 Application Services — 7 files

| Service                    | Purpose                                                    |
| -------------------------- | ---------------------------------------------------------- |
| `intent_service.py`        | 3-step: classify → extract entities → build IntentDecision |
| `safety_service.py`        | Safety gate with reason codes                              |
| `action_service.py`        | Execute actions (book, cancel, checkin, checkout)          |
| `response_service.py`      | Generate natural language responses via Gemini             |
| `memory_service.py`        | User preference + behavior memory (anti-noise)             |
| `proactive_service.py`     | Proactive notifications with cooldown/priority             |
| `observability_service.py` | AI metrics collection                                      |

### 5.7 Routers — 5 files

| Router             | Mô tả                            |
| ------------------ | -------------------------------- |
| `chat.py`          | Main chat endpoint               |
| `conversation.py`  | Conversation management          |
| `actions.py`       | Action-related endpoints         |
| `notifications.py` | Proactive notification endpoints |
| `preferences.py`   | User preference endpoints        |

### 5.8 Infrastructure Adapters

| Adapter   | File                                        | Purpose                       |
| --------- | ------------------------------------------- | ----------------------------- |
| LLM       | `infrastructure/llm/gemini_client.py`       | Gemini API wrapper            |
| Cache     | `infrastructure/cache/redis.py`             | Redis DB 6                    |
| Messaging | `infrastructure/messaging/rabbitmq.py`      | RabbitMQ (aio-pika)           |
| External  | `infrastructure/external/service_client.py` | HTTP client to other services |

---

## 6. Gateway Service — `gateway-service-go/`

### 6.1 Tech Stack

| Attribute     | Value                     |
| ------------- | ------------------------- |
| Language      | **Go 1.22**               |
| Framework     | Gin 1.10.0                |
| Session store | Redis (go-redis/v9 9.7.0) |
| Port          | 8000                      |

### 6.2 Architecture — `internal/`

| Package       | Files                                                                    | Purpose                        |
| ------------- | ------------------------------------------------------------------------ | ------------------------------ |
| `config/`     | `config.go`, `config_test.go`                                            | Service route config, env vars |
| `handler/`    | `auth.go`, `proxy.go`, `health.go`, `*_test.go`                          | Request handlers               |
| `middleware/` | `auth.go`, `cors.go`, `logging.go`, `ratelimit.go`, `middleware_test.go` | Middleware chain               |
| `router/`     | `routes.go`                                                              | Single catch-all route         |
| `session/`    | `redis_store.go`                                                         | Redis session store            |

### 6.3 Authentication Mechanism: **Session-based (NOT JWT)**

- Cookie: `session_id`
- Session stored in **Redis DB 1**
- Middleware validates session → injects headers: `X-User-ID`, `X-User-Email`, `X-User-Role`, `X-User-Is-Staff`
- Public endpoints bypass auth (login, register, health, OAuth callbacks)
- Login/Logout handled by `auth.go` handler
- OAuth support: Google, Facebook

### 6.4 Rate Limiting

- Redis-based sliding window counter
- Lua script for atomic increment + expire

### 6.5 Proxy

- Single catch-all route: `r.Any("/*path", ...)`
- Routes config determines target service based on URL prefix
- Headers: `X-Gateway-Secret` for internal service auth

---

## 7. Realtime Service — `realtime-service-go/`

### 7.1 Tech Stack

| Attribute | Value                   |
| --------- | ----------------------- |
| Language  | **Go 1.22**             |
| Framework | Gin 1.10.0              |
| WebSocket | gorilla/websocket 1.5.3 |
| Port      | 8006                    |

### 7.2 Architecture

| Package       | Files                                        | Purpose                                  |
| ------------- | -------------------------------------------- | ---------------------------------------- |
| `hub/`        | `hub.go`, `hub_test.go`                      | Connection hub, group-based broadcasting |
| `handler/`    | `ws_handler.go`, `broadcast.go`, `*_test.go` | WebSocket upgrade + REST broadcast API   |
| `config/`     | Config loading                               |
| `middleware/` | Middleware                                   |

### 7.3 WebSocket Hub

- **Group-based pub/sub**: Connections subscribe to groups (e.g., `parking_updates`, `user_{userId}`)
- **Channels**: buffered (256 capacity) for register, unregister, broadcast, addConn, removeConn
- **WebSocket upgrader**: gorilla/websocket with `ReadBufferSize: 1024`, `WriteBufferSize: 1024`

### 7.4 Broadcast Types (REST → WebSocket)

| Endpoint Handler            | Event Type                 | Group             |
| --------------------------- | -------------------------- | ----------------- |
| `BroadcastSlotStatus`       | `slot.status_update`       | `parking_updates` |
| `BroadcastZoneAvailability` | `zone.availability_update` | `parking_updates` |
| `BroadcastLotAvailability`  | `lot.availability_update`  | `parking_updates` |
| `BroadcastBookingUpdate`    | `booking.status_update`    | `user_{userId}`   |

---

## 8. IoT/Hardware — `hardware/`

### 8.1 ESP32 — `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino`

| Feature    | Detail                                                                                 |
| ---------- | -------------------------------------------------------------------------------------- |
| MCU        | ESP32                                                                                  |
| WiFi       | Built-in, connects to local network                                                    |
| Display    | OLED SSD1306 (I2C: GPIO21=SDA, GPIO22=SCL)                                             |
| Libraries  | WiFi, HTTPClient, ArduinoJson v7+, Adafruit_GFX, Adafruit_SSD1306                      |
| Buttons    | GPIO4=CHECK-IN, GPIO5=CHECK-OUT (active LOW, INPUT_PULLUP)                             |
| UART       | GPIO16=RX2, GPIO17=TX2 → Arduino (9600 baud)                                           |
| LED        | GPIO2 (built-in)                                                                       |
| Protocol   | HTTP POST to AI service: `/ai/parking/esp32/check-in/`, `/ai/parking/esp32/check-out/` |
| Auth       | `X-Gateway-Secret` header + Device Token                                               |
| Firmware   | v1.0.0-parksmart                                                                       |
| Auto-close | Sends CLOSE_1/CLOSE_2 after configurable seconds                                       |

### 8.2 Arduino — `hardware/arduino/barrier_control/barrier_control.ino`

| Feature    | Detail                                                          |
| ---------- | --------------------------------------------------------------- |
| MCU        | Arduino (Uno/Nano)                                              |
| Library    | Servo.h                                                         |
| Servo IN   | Pin 10 (entry gate) — OPEN: 3000μs, CLOSE: 1500μs               |
| Servo OUT  | Pin 9 (exit gate) — OPEN: 3000μs, CLOSE: 1500μs                 |
| LED        | Pin 13                                                          |
| UART       | 9600 baud, newline-terminated                                   |
| Commands   | `OPEN_1\n`, `CLOSE_1\n` (entry), `OPEN_2\n`, `CLOSE_2\n` (exit) |
| Auto-close | 5000ms (AUTO_CLOSE_MS)                                          |
| Startup    | Sends "ARDUINO_READY" on Serial                                 |

### 8.3 Communication Flow

```
ESP32 (WiFi+HTTP) ──── POST /ai/parking/esp32/check-{in|out}/ ────→ AI Service
     ↑ response (barrier_action: "open")
     │
     └──── UART 9600 ──── OPEN_1/OPEN_2 ────→ Arduino ──→ Servo barrier
                          CLOSE_1/CLOSE_2 (after 5s)
```

---

## 9. Infrastructure — `infra/`

### 9.1 Nginx — `infra/nginx/nginx.conf`

| Feature          | Detail                                                                                                          |
| ---------------- | --------------------------------------------------------------------------------------------------------------- |
| Purpose          | Production reverse proxy + static file serving                                                                  |
| Domain           | `app.ghepdoicaulong.shop`, `api.ghepdoicaulong.shop`, `ws.ghepdoicaulong.shop`, `parksmart.ghepdoicaulong.shop` |
| Static root      | `/usr/share/nginx/html` (FE build `spotlove-ai/dist/`)                                                          |
| Upstreams        | `api_backend` (localhost:8000), `ws_backend` (localhost:8006), `ai_backend` (localhost:8009)                    |
| Gzip             | ON — js, css, json, xml, svg, fonts                                                                             |
| Security headers | X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, HSTS, CSP, Permissions-Policy       |
| Caching          | Static assets: 1 year, immutable                                                                                |
| Worker           | auto (auto-detect CPU cores), 1024 connections                                                                  |

### 9.2 Cloudflare Tunnel — `infra/cloudflare/cloudflared/`

| File                   | Purpose                                                                        |
| ---------------------- | ------------------------------------------------------------------------------ |
| `config-parksmart.yml` | Tunnel config: `parksmart.ghepdoicaulong.shop` → `http://localhost:80` (Nginx) |
| `config.yml`           | Generic tunnel config                                                          |
| `config.example.yml`   | Example template                                                               |

- Tunnel ID: `5d3c98ed-b629-48a3-9377-4163315c91da`
- Connect timeout: 30s

### 9.3 Cloudflare Additional

| Folder               | Files                           |
| -------------------- | ------------------------------- |
| `reverse-proxy/`     | `api.conf.example`              |
| `security-controls/` | `rate-limit-rules.example.json` |

---

## 10. Unity Digital Twin — `ParkingSimulatorUnity/`

### 10.1 Engine & Render Pipeline

| Attribute | Value                                  |
| --------- | -------------------------------------- |
| Engine    | Unity 2022.3.62f3 LTS                  |
| Render    | URP (Universal Render Pipeline) + DX11 |
| Solution  | `ParkingSimulatorUnity.sln`            |

### 10.2 Scripts — 8 namespaces under `Assets/Scripts/`

| Namespace       | Files     | Purpose                                             |
| --------------- | --------- | --------------------------------------------------- |
| **Camera/**     | 7 scripts | Virtual camera system                               |
| **Core/**       | 2 scripts | ParkingManager, FloorVisibilityManager              |
| **API/**        | 7 scripts | REST API integration, auth, mock data               |
| **Vehicle/**    | 4 scripts | Vehicle controller, queue, license plate, visual    |
| **Parking/**    | 3 scripts | ParkingLotGenerator, ParkingSlot, BarrierController |
| **Navigation/** | 2 scripts | WaypointGraph, WaypointNode (pathfinding)           |
| **IoT/**        | 2 scripts | ESP32Simulator, FlowLogger                          |
| **UI/**         | 3 scripts | BookingTestPanel, CameraMonitorUI, DashboardUI      |

**Total: 30 C# scripts**

### 10.3 Camera System Detail (from `Camera/`)

| Script                       | Purpose                                            |
| ---------------------------- | -------------------------------------------------- |
| `VirtualCameraManager.cs`    | Manages 6 virtual cameras                          |
| `VirtualCameraStreamer.cs`   | Captures render + HTTP POST to `/ai/cameras/frame` |
| `GateCameraSimulator.cs`     | Entry/exit gate camera simulation                  |
| `ParkingCameraController.cs` | Parking lot camera control                         |
| `SlotOccupancyDetector.cs`   | Unity-side slot occupancy detection                |
| `VehicleTrackingCamera.cs`   | Vehicle tracking camera                            |
| `IVirtualCamera.cs`          | Interface for virtual cameras                      |

- **6 virtual cameras:** f1-overview, f2-overview, gate-in, gate-out, zone-south, zone-north
- **Resolution:** 640×480 @ 5fps, JPEG quality 75%
- **Streaming:** POST to AI service with `X-Camera-ID` header

### 10.4 API Integration (from `API/`)

| Script                  | Purpose                               |
| ----------------------- | ------------------------------------- |
| `ApiConfig.cs`          | API endpoint configuration            |
| `ApiService.cs`         | HTTP client for backend communication |
| `AuthManager.cs`        | Authentication manager                |
| `DataModels.cs`         | Data model classes                    |
| `SharedBookingState.cs` | Shared booking state                  |
| `MockDataProvider.cs`   | Mock data for testing                 |
| `MockIds.cs`            | Mock IDs for testing                  |

### 10.5 Parking Lot Specs

- **2 floors**, **158 total slots**
- Floor 0: 72 car slots (4 rows × 18) + 20 moto + 5 garage = 97 slots
- Floor 1: 36 car slots (2 rows × 18) + 20 moto + 5 garage = 61 slots
- Slot dimensions: 2.5m × 5m

---

## 11. Database — MySQL 8.0

### 11.1 Tables from `init-mysql.sql` (Chatbot-specific, 8 tables)

Django services (auth, booking, parking, vehicle) manage their own migrations via `manage.py migrate`.

| #   | Table                              | Key Columns                                                                                                    | Purpose                  |
| --- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 1   | `chatbot_conversation`             | id (CHAR36), user_id, current_state, context (JSON), total_turns                                               | Conversation sessions    |
| 2   | `chatbot_chatmessage`              | id, conversation_id, role, content, intent, entities (JSON), confidence, action_taken                          | Chat messages            |
| 3   | `chatbot_user_preferences`         | user_id (UNIQUE), favorite_lot/zone/slot, default_vehicle_id, booking_history_summary (JSON)                   | User preferences memory  |
| 4   | `chatbot_user_behavior`            | user_id (UNIQUE), typical_arrival/departure_time, prefers_near_exit/shade/same_zone, cancel_rate, no_show_rate | User behavior patterns   |
| 5   | `chatbot_user_communication_style` | user_id (UNIQUE), prefers_short, emoji_level, formality, primary_language, frustration_score                   | Communication style      |
| 6   | `chatbot_conversation_summary`     | conversation_id, user_id, summary, key_decisions (JSON), sentiment                                             | Conversation summaries   |
| 7   | `chatbot_proactive_notification`   | user_id, event_type, status, title, message, suggested_actions (JSON), trigger_at, expires_at                  | Proactive notifications  |
| 8   | `chatbot_action_log`               | user_id, action_type, action_data (JSON), is_undoable, is_undone                                               | Action audit log         |
| 9   | `chatbot_ai_metric_log`            | metric_type, user_id, intent, confidence, extra_data (JSON)                                                    | AI observability metrics |

**Note:** Django-managed tables (auth*user, bookings*_, parking\__, vehicles\_\*) are created by Django migrations, not in init-mysql.sql.

### 11.2 Database Configuration

| Parameter    | Value                                            |
| ------------ | ------------------------------------------------ |
| Engine       | InnoDB                                           |
| Charset      | utf8mb4                                          |
| Collation    | utf8mb4_unicode_ci                               |
| JSON columns | Extensive (context, entities, action_data, etc.) |
| Primary keys | CHAR(36) UUIDs                                   |

---

## 12. Complete Port Map

| Port  | Service                        | Protocol         |
| ----- | ------------------------------ | ---------------- |
| 3307  | MySQL 8.0                      | TCP/MySQL        |
| 5672  | RabbitMQ (AMQP)                | AMQP             |
| 6379  | Redis 7                        | TCP/Redis        |
| 8000  | Gateway (Go)                   | HTTP             |
| 8001  | Auth Service (Django)          | HTTP             |
| 8002  | Booking Service (Django)       | HTTP             |
| 8003  | Parking Service (Django)       | HTTP             |
| 8005  | Notification Service (FastAPI) | HTTP (internal)  |
| 8006  | Realtime Service (Go)          | HTTP + WebSocket |
| 8007  | Payment Service (FastAPI)      | HTTP (internal)  |
| 8008  | Chatbot Service (FastAPI)      | HTTP (internal)  |
| 8009  | AI Service (FastAPI)           | HTTP             |
| 8080  | Frontend Dev Server (Vite)     | HTTP             |
| 15672 | RabbitMQ Management UI         | HTTP             |
| 80    | Nginx (Production)             | HTTP             |

---

## 13. Technology Summary

### Languages

| Language                  | Usage                | Services                                                            |
| ------------------------- | -------------------- | ------------------------------------------------------------------- |
| **TypeScript/JavaScript** | Frontend SPA         | spotlove-ai                                                         |
| **Python**                | Backend services (7) | auth, booking, parking, vehicle, notification, payment, chatbot, ai |
| **Go**                    | Gateway + Realtime   | gateway-service-go, realtime-service-go                             |
| **C#**                    | Unity Digital Twin   | ParkingSimulatorUnity (30 scripts)                                  |
| **C/C++**                 | IoT Firmware         | ESP32 + Arduino (2 .ino files)                                      |
| **SQL**                   | Database schema      | init-mysql.sql + Django migrations                                  |

### Frameworks

| Framework             | Version         | Usage                  |
| --------------------- | --------------- | ---------------------- |
| React                 | 18.3            | Frontend UI            |
| Vite                  | 5.4.19          | Build tool             |
| Redux Toolkit         | 2.11.2          | State management       |
| TanStack React Query  | 5.83.0          | Server state           |
| Tailwind CSS          | 3.4.17          | Styling                |
| shadcn/ui             | 51 components   | UI component library   |
| Django                | 5.2.12          | 4 backend services     |
| Django REST Framework | 3.15.2          | REST APIs              |
| FastAPI               | 0.134.0         | 4 backend services     |
| SQLAlchemy            | 2.0.35–2.0.47   | ORM (FastAPI services) |
| Celery                | 5.4.0           | Task queue             |
| Gin                   | 1.10.0          | Go HTTP framework      |
| gorilla/websocket     | 1.5.3           | WebSocket (Go)         |
| Unity                 | 2022.3.62f3 LTS | 3D simulation          |
| URP                   | —               | Render pipeline        |
| Ultralytics           | 8.4.18          | YOLO object detection  |
| PyTorch               | ≥2.0            | Deep learning          |

---

## 14. Nguồn

| #   | File                                                                                    | Mô tả                           |
| --- | --------------------------------------------------------------------------------------- | ------------------------------- |
| 1   | `spotlove-ai/package.json`                                                              | Frontend dependencies           |
| 2   | `backend-microservices/docker-compose.yml`                                              | Service definitions (450 lines) |
| 3   | `backend-microservices/init-mysql.sql`                                                  | Database schema                 |
| 4   | `backend-microservices/ai-service-fastapi/requirements.txt`                             | AI ML dependencies              |
| 5   | `backend-microservices/chatbot-service-fastapi/requirements.txt`                        | Chatbot dependencies            |
| 6   | `backend-microservices/chatbot-service-fastapi/app/domain/value_objects/intent.py`      | 16 intents                      |
| 7   | `backend-microservices/chatbot-service-fastapi/app/domain/value_objects/confidence.py`  | Hybrid confidence formula       |
| 8   | `backend-microservices/chatbot-service-fastapi/app/engine/orchestrator.py`              | Pipeline architecture           |
| 9   | `backend-microservices/chatbot-service-fastapi/app/infrastructure/llm/gemini_client.py` | LLM config                      |
| 10  | `backend-microservices/chatbot-service-fastapi/app/config.py`                           | Chatbot settings                |
| 11  | `backend-microservices/gateway-service-go/go.mod`                                       | Go 1.22 + dependencies          |
| 12  | `backend-microservices/gateway-service-go/internal/middleware/auth.go`                  | Session-based auth              |
| 13  | `backend-microservices/gateway-service-go/internal/router/routes.go`                    | Route config                    |
| 14  | `backend-microservices/realtime-service-go/go.mod`                                      | Realtime dependencies           |
| 15  | `backend-microservices/realtime-service-go/internal/hub/hub.go`                         | WebSocket hub                   |
| 16  | `backend-microservices/realtime-service-go/internal/handler/broadcast.go`               | Broadcast types                 |
| 17  | `spotlove-ai/src/services/websocket.service.ts`                                         | Frontend WS client              |
| 18  | `spotlove-ai/src/store/index.ts`                                                        | Redux store config              |
| 19  | `spotlove-ai/src/services/api/endpoints.ts`                                             | API endpoint map                |
| 20  | `spotlove-ai/vite.config.ts`                                                            | Vite config + proxy             |
| 21  | `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino`                        | ESP32 firmware                  |
| 22  | `hardware/arduino/barrier_control/barrier_control.ino`                                  | Arduino firmware                |
| 23  | `infra/nginx/nginx.conf`                                                                | Nginx production config         |
| 24  | `infra/cloudflare/cloudflared/config-parksmart.yml`                                     | Cloudflare tunnel               |
| 25  | `ParkingSimulatorUnity/Assets/Scripts/`                                                 | Unity scripts directory         |
| 26  | All `requirements.txt` files per service                                                | Service dependencies            |
