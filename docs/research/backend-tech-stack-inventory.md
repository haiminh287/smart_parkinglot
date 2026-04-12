# Research Report: Backend Microservices — Technical Stack Inventory

**Task:** General Inventory | **Date:** 2026-04-06 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **10 microservices**: 4× Django REST (auth, booking, parking, vehicle), 4× FastAPI (AI, chatbot, payment, notification), 2× Go/Gin (gateway, realtime)
> 2. **Single MySQL 8.0 database** (`parksmartdb`) shared by all services, differentiated by table prefix. Django services use `mysqlclient`, FastAPI services use `PyMySQL + SQLAlchemy`.
> 3. **Redis 7** used for: sessions (DB1), Celery broker (DB0), caching (DB2-6). **RabbitMQ 3** for async events (booking→chatbot proactive). **Gorilla WebSocket** for realtime push.
> 4. **Gateway-centric auth**: Go gateway manages sessions (Redis-backed), authenticates via cookie/JWT, injects `X-User-ID`/`X-Gateway-Secret` headers. Backend services verify `X-Gateway-Secret` — no direct public access.
> 5. **AI stack**: PyTorch <2.6, Ultralytics YOLOv8/YOLO11, TrOCR (HuggingFace), EasyOCR, OpenCV — license plate recognition + parking slot detection.

---

## 2. Architecture Overview

```
                         ┌──────────────────┐
                         │   MySQL 8.0      │
                         │  parksmartdb     │
                         │  (port 3307→3306)│
                         └────────┬─────────┘
                                  │
┌─────────┐   ┌─────────┐   ┌────┴─────┐   ┌──────────┐   ┌───────────┐
│ Redis 7 │   │RabbitMQ │   │          │   │          │   │           │
│ (6379)  │   │ (5672)  │   │ Gateway  │   │ Realtime │   │ AI Svc    │
│ DB 0-6  │   │  AMQP   │   │  Go/Gin  │   │  Go/Gin  │   │  FastAPI  │
└────┬────┘   └────┬────┘   │  :8000   │   │  :8006   │   │  :8009    │
     │              │        └────┬─────┘   └──────────┘   └───────────┘
     │              │             │
     │              │    ┌────────┼────────────────────────┐
     │              │    │        │        │        │      │
     │              │  Auth    Booking  Parking  Vehicle   │
     │              │  Django  Django   Django   Django    │
     │              │  :8001   :8002    :8003    (8000)    │
     │              │                                      │
     │              │    ┌─────────┬──────────┬────────┐   │
     │              │  Chatbot  Payment  Notification  │   │
     │              │  FastAPI  FastAPI  FastAPI        │   │
     │              │  :8008    :8007    :8005          │   │
     │              └──────────────────────────────────┘   │
     └─────────────────────────────────────────────────────┘
```

---

## 3. Service-by-Service Inventory

### 3.1 auth-service (Django)

| Attribute            | Value                                                                                                                         |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Framework**        | Django 5.2.12 + DRF 3.15.2                                                                                                    |
| **Python**           | 3.11 (Dockerfile)                                                                                                             |
| **WSGI Server**      | Gunicorn 22.0.0                                                                                                               |
| **Port**             | 8001 (host) → 8000 (container)                                                                                                |
| **DB**               | MySQL via `mysqlclient==2.2.4`, database `parksmartdb`                                                                        |
| **Cache**            | Redis DB 1                                                                                                                    |
| **Auth Mechanism**   | Session-based (Django sessions) + OAuth2 (Google, Facebook). Gateway manages session cookie. UUID primary keys on User model. |
| **User Model**       | Custom `AbstractUser` with UUID PK, email as `USERNAME_FIELD`, roles (user/admin), `no_show_count`, `force_online_payment`    |
| **Password Hashing** | Django default (PBKDF2/argon2 via `AUTH_PASSWORD_VALIDATORS`)                                                                 |

**Key Dependencies:**

- `djangorestframework-camel-case==1.4.2` (CamelCase JSON for frontend)
- `django-cors-headers==4.6.0`
- `redis==5.2.1`
- `python-decouple==3.8`
- `requests==2.32.4`

**Endpoints:** `/auth/register/`, `/auth/login/`, `/auth/logout/`, `/auth/me/`, `/auth/change-password/`, `/auth/forgot-password/`, `/auth/reset-password/`, `/auth/google/`, `/auth/facebook/`, `/auth/admin/*`

**Tables:** `users_user`, `users_oauth_account`, `users_password_reset`

---

### 3.2 booking-service (Django + Celery)

| Attribute       | Value                                                |
| --------------- | ---------------------------------------------------- |
| **Framework**   | Django 5.2.12 + DRF 3.15.2                           |
| **Python**      | 3.11                                                 |
| **WSGI Server** | Gunicorn 22.0.0                                      |
| **Port**        | 8002 (host) → 8000 (container)                       |
| **DB**          | MySQL via `mysqlclient==2.2.4`                       |
| **Cache**       | Redis DB 2                                           |
| **Task Queue**  | Celery 5.4.0, broker: Redis DB 0, result: Redis DB 0 |
| **Messaging**   | RabbitMQ (AMQP) for event publishing                 |

**Celery Beat Periodic Tasks:**

- `auto_cancel_unpaid_bookings` — every 60s
- `check_no_show_bookings` — every 5 min

**Key Dependencies:**

- `celery==5.4.0`
- `pytest-cov==5.0.0`

**Inter-service calls to:** payment-service, vehicle-service, parking-service, auth-service, notification-service, realtime-service

**Tables:** `booking`, `package_pricing`

**Data Pattern:** Denormalized — booking stores copies of user_email, vehicle_license_plate, parking_lot_name, zone_name, slot_code to avoid cross-service joins.

**Docker:** 3 containers — `booking-service` (API), `booking-celery-worker`, `booking-celery-beat`

---

### 3.3 parking-service (Django)

| Attribute       | Value                          |
| --------------- | ------------------------------ |
| **Framework**   | Django 5.2.12 + DRF 3.15.2     |
| **Python**      | 3.11                           |
| **WSGI Server** | Gunicorn 22.0.0                |
| **Port**        | 8003 (host) → 8000 (container) |
| **DB**          | MySQL via `mysqlclient==2.2.4` |
| **Cache**       | Redis DB 3                     |

**Tables:** `parking_lot`, `floor`, `zone`, `car_slot`, `infrastructure_camera`

**Domain Model Hierarchy:** ParkingLot → Floor → Zone → CarSlot (with Camera FK)

**CarSlot statuses:** `available`, `occupied`, `reserved`, `maintenance`

**AI Integration:** CarSlot has bounding box fields (`x1,y1,x2,y2`) for AI detection mapping.

---

### 3.4 vehicle-service (Django)

| Attribute       | Value                                        |
| --------------- | -------------------------------------------- |
| **Framework**   | Django 5.2.12 + DRF 3.15.2                   |
| **Python**      | 3.11                                         |
| **WSGI Server** | Gunicorn 22.0.0                              |
| **Port**        | Internal only (expose 8000, no host mapping) |
| **DB**          | MySQL via `mysqlclient==2.2.4`               |
| **Cache**       | Redis DB 4                                   |

**Tables:** `vehicle`

**Fields:** UUID PK, `user_id` (UUID ref to auth-service), `license_plate` (unique), `vehicle_type` (Car/Motorbike), `brand`, `model`, `color`, `is_default`

---

### 3.5 ai-service-fastapi

| Attribute       | Value                                             |
| --------------- | ------------------------------------------------- |
| **Framework**   | FastAPI 0.134.0 + Starlette 0.52.1                |
| **Python**      | 3.10 (Dockerfile)                                 |
| **ASGI Server** | Uvicorn 0.41.0                                    |
| **Port**        | Internal (expose 8009)                            |
| **DB**          | MySQL via `PyMySQL==1.1.2` + `SQLAlchemy==2.0.47` |
| **ORM**         | SQLAlchemy 2.0 (async-compatible)                 |

**AI/ML Stack:**
| Library | Version | Purpose |
|---|---|---|
| `torch` | ≥2.0.0, <2.6.0 | Deep learning runtime |
| `torchvision` | ≥0.15.0, <0.21.0 | Image transforms/models |
| `ultralytics` | 8.4.18 | YOLO object detection (slot detection, license plate) |
| `easyocr` | 1.7.2 | OCR fallback |
| `timm` | 1.0.25 | TrOCR model backbone |
| `huggingface_hub` | 1.5.0 | Model downloading |
| `opencv-python-headless` | 4.10.0.84 | Image processing |
| `scikit-image` | 0.25.2 | Image analysis |
| `scipy` | 1.15.3 | Scientific computing |
| `numpy` | 1.26.4 | Array ops |
| `matplotlib` | 3.10.8 | Visualization/debug |
| `pillow` | 12.1.1 | Image I/O |
| `shapely` | 2.1.2 | Geometry (slot polygon ops) |
| `polars` | 1.38.1 | Fast dataframes |

**Routers:** `detection`, `training`, `metrics`, `parking`, `esp32`, `camera`

**Functionality:**

- Parking slot detection (YOLO11n)
- License plate recognition (YOLOv8 finetune + TrOCR pipeline)
- Camera frame ingestion (from Unity sim + ESP32 hardware)
- Camera health monitoring (background asyncio task)
- ESP32 IoT device management
- Training pipeline

**Inter-service calls to:** parking-service, booking-service, realtime-service

---

### 3.6 chatbot-service-fastapi

| Attribute       | Value                                                |
| --------------- | ---------------------------------------------------- |
| **Framework**   | FastAPI 0.134.0 + Starlette 0.49.1                   |
| **Python**      | 3.11                                                 |
| **ASGI Server** | Uvicorn 0.30.0                                       |
| **Port**        | Internal (expose 8008)                               |
| **DB**          | MySQL via `PyMySQL==1.1.1` + `SQLAlchemy==2.0.35`    |
| **Migration**   | Alembic 1.13.0                                       |
| **Cache**       | Redis DB 6                                           |
| **Messaging**   | RabbitMQ via `aio-pika==9.4.0` (async AMQP consumer) |

**LLM Provider:** Google Gemini (`google-generativeai==0.8.0`), model configurable (default: `gemini-2.0-flash` in compose, `gemini-3-flash-preview` in config.py)

**Architecture:** v3.0 — IntentService 3-step (classify → extract → build), Hybrid Confidence scoring, Safety system, Memory architecture with anti-noise, Proactive notifications via RabbitMQ, AI Observability metrics

**Routers:** `chat`, `conversation`, `preferences`, `notifications`, `actions`

**Tables (from init-mysql.sql):**

- `chatbot_conversation` — dialog state machine
- `chatbot_chatmessage` — messages with intent/entities/confidence
- `chatbot_user_preferences` — favorite lot/zone/slot/vehicle
- `chatbot_user_behavior` — behavioral patterns (arrival time, cancel rate)
- `chatbot_user_communication_style` — personalization
- `chatbot_conversation_summary` — conversation summaries
- `chatbot_proactive_notification` — proactive push events
- `chatbot_action_log` — undoable action history
- `chatbot_ai_metric_log` — AI observability

**Inter-service calls to:** booking-service, parking-service, vehicle-service, payment-service, realtime-service

---

### 3.7 payment-service-fastapi

| Attribute       | Value                                             |
| --------------- | ------------------------------------------------- |
| **Framework**   | FastAPI 0.134.0 + Starlette 0.49.1                |
| **Python**      | 3.11 (implied by base)                            |
| **ASGI Server** | Uvicorn 0.34.0                                    |
| **Port**        | Internal (expose 8007)                            |
| **DB**          | MySQL via `PyMySQL==1.1.1` + `SQLAlchemy==2.0.36` |
| **Migration**   | Alembic 1.14.0                                    |

**Inter-service calls to:** booking-service, notification-service, realtime-service

**Minimal deps — no external payment gateway libs** (likely simulated/mock payments)

---

### 3.8 notification-service-fastapi

| Attribute       | Value                                             |
| --------------- | ------------------------------------------------- |
| **Framework**   | FastAPI 0.134.0 + Starlette 0.49.1                |
| **Python**      | 3.11 (implied)                                    |
| **ASGI Server** | Uvicorn 0.34.0                                    |
| **Port**        | Internal (expose 8005)                            |
| **DB**          | MySQL via `PyMySQL==1.1.1` + `SQLAlchemy==2.0.36` |
| **Migration**   | Alembic 1.14.0                                    |

**Note:** `startup` event does NOT create tables — relies on existing schema. Minimal service.

---

### 3.9 gateway-service-go

| Attribute         | Value                                            |
| ----------------- | ------------------------------------------------ |
| **Language**      | Go 1.22                                          |
| **Framework**     | Gin 1.10.0                                       |
| **Port**          | 8000 (host & container) — **single entry point** |
| **Session Store** | Redis DB 1 (via `go-redis/v9 v9.7.0`)            |

**Key Dependencies:**

- `gin-contrib/cors v1.7.2`
- `google/uuid v1.6.0`
- `joho/godotenv v1.5.1`
- `redis/go-redis/v9 v9.7.0`

**Architecture:**

- **Reverse proxy** to all backend services
- **Session-based auth**: Login → creates Redis session → sets cookie → subsequent requests verify cookie → injects `X-User-ID`, `X-User-Email`, `X-User-Is-Staff`, `X-User-Role`, `X-Gateway-Secret` headers
- **OAuth callback handling**: Google/Facebook callbacks processed in gateway, redirects to frontend
- **Rate limiting** (configurable requests/window, Redis-backed)
- **Catch-all routing**: Single `r.Any("/*path")` that dispatches based on path prefix to upstream services

**Routing Map (from config):**
| Path prefix | Upstream |
|---|---|
| `/auth/*` | auth-service:8000 |
| `/parking/*` | parking-service:8000 |
| `/vehicles/*` | vehicle-service:8000 |
| `/bookings/*` | booking-service:8000 |
| `/notifications/*` | notification-service:8005 |
| `/ws/*` | realtime-service:8006 |
| `/payments/*` | payment-service:8007 |
| `/chatbot/*` | chatbot-service:8008 |
| `/ai/*` | ai-service:8009 |

**Production Validation:** Enforces HTTPS CORS origins, secure cookies, non-localhost domains

---

### 3.10 realtime-service-go

| Attribute     | Value                   |
| ------------- | ----------------------- |
| **Language**  | Go 1.22                 |
| **Framework** | Gin 1.10.0              |
| **WebSocket** | Gorilla WebSocket 1.5.3 |
| **Port**      | 8006 (host & container) |

**WebSocket Endpoints:**

- `GET /ws/parking` — Public: parking lot updates (slot status changes)
- `GET /ws/user/:userId` — Authenticated: user-specific notifications

**Internal Broadcast API** (requires `X-Gateway-Secret`):

- `POST /api/broadcast/slot-status/`
- `POST /api/broadcast/zone-availability/`
- `POST /api/broadcast/lot-availability/`
- `POST /api/broadcast/booking/`
- `POST /api/broadcast/notification/`
- `POST /api/broadcast/camera-status/`
- `POST /api/broadcast/unity-command/`

**Pattern:** Hub-and-spoke — central `Hub` goroutine manages connections, other services POST to broadcast API to push updates to connected clients.

---

## 4. Infrastructure Services

| Service      | Image                        | Port(s)     | Purpose                                   |
| ------------ | ---------------------------- | ----------- | ----------------------------------------- |
| **MySQL**    | mysql:8.0                    | 3307→3306   | Single shared database `parksmartdb`      |
| **Redis**    | redis:7-alpine               | 6379        | Sessions, Celery broker, caching (DB 0-6) |
| **RabbitMQ** | rabbitmq:3-management-alpine | 5672, 15672 | Async event messaging                     |

### Redis DB Allocation:

| DB  | Service                   | Purpose                        |
| --- | ------------------------- | ------------------------------ |
| 0   | booking-service           | Celery broker + result backend |
| 1   | auth-service / gateway    | Redis sessions + cache         |
| 2   | booking-service           | Django cache                   |
| 3   | parking-service / chatbot | Cache                          |
| 4   | vehicle-service           | Cache                          |
| 5   | realtime-service          | (configured but usage unclear) |
| 6   | chatbot-service           | Cache                          |

---

## 5. Shared Utilities (`backend-microservices/shared/`)

Installed as pip package `parksmart-shared` (editable install via `setup.py`).

| File                     | Purpose                                                                                                                                                               |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `gateway_middleware.py`  | Django middleware: validates `X-Gateway-Secret`, extracts `X-User-ID`/`X-User-Email` from headers, sets `request.user_id`. Skips health checks and public auth paths. |
| `gateway_permissions.py` | DRF permissions: `IsGatewayAuthenticated` (checks `request.user_id`), `IsGatewayAdmin` (checks `X-User-Is-Staff`/`X-User-Role` headers)                               |
| `permissions.py`         | `IsInternalService` — allows only internal services with valid `X-Gateway-Secret`. Fail-closed design.                                                                |

**Note:** FastAPI services have their OWN `GatewayAuthMiddleware` (at `app/middleware/gateway_auth.py`), not using the shared Django middleware.

---

## 6. Inter-Service Communication Patterns

### 6.1 Synchronous (HTTP)

All inter-service calls use `httpx` (FastAPI) or `requests` (Django) with internal Docker network URLs. Gateway injects `X-Gateway-Secret` header for downstream auth.

### 6.2 Asynchronous (RabbitMQ)

- **booking-service** → publishes events (booking created, cancelled, etc.)
- **chatbot-service** → consumes events via `aio-pika` for proactive notifications

### 6.3 Real-time (WebSocket)

- Backend services → POST to `realtime-service /api/broadcast/*` → Hub pushes to connected WebSocket clients
- Frontend + Unity → connect to `ws://host:8006/ws/parking` or `/ws/user/:id`

### 6.4 Task Queue (Celery)

- `booking-service` uses Celery workers for: auto-cancel unpaid bookings, check no-shows
- Broker: Redis DB 0

---

## 7. Database Schema Summary

**Django-managed tables** (via migrations):

- `users_user`, `users_oauth_account`, `users_password_reset` (auth-service)
- `booking`, `package_pricing` (booking-service)
- `parking_lot`, `floor`, `zone`, `car_slot`, `infrastructure_camera` (parking-service)
- `vehicle` (vehicle-service)
- Standard Django tables: `django_migrations`, `django_session`, `django_content_type`, `auth_*`

**SQL-managed tables** (via `init-mysql.sql`):

- `chatbot_conversation`, `chatbot_chatmessage`
- `chatbot_user_preferences`, `chatbot_user_behavior`, `chatbot_user_communication_style`
- `chatbot_conversation_summary`
- `chatbot_proactive_notification`, `chatbot_action_log`
- `chatbot_ai_metric_log`

**FastAPI/Alembic-managed tables:**

- payment-service, notification-service — via Alembic migrations (tables not in init SQL)

**All UUIDs:** Every entity uses UUID (CHAR(36)) primary keys.

---

## 8. Port Map (External)

| Port      | Service             | Protocol                  |
| --------- | ------------------- | ------------------------- |
| **8000**  | gateway-service-go  | HTTP (single entry point) |
| **8001**  | auth-service        | HTTP                      |
| **8002**  | booking-service     | HTTP                      |
| **8003**  | parking-service     | HTTP                      |
| **8006**  | realtime-service-go | HTTP + WebSocket          |
| **3307**  | MySQL               | MySQL protocol            |
| **6379**  | Redis               | Redis protocol            |
| **5672**  | RabbitMQ            | AMQP                      |
| **15672** | RabbitMQ Management | HTTP                      |

**Internal-only (no host port):** vehicle-service, notification-service (8005), payment-service (8007), chatbot-service (8008), ai-service (8009)

---

## 9. Version Matrix

| Component                | Version               |
| ------------------------ | --------------------- |
| Python (Django services) | 3.11                  |
| Python (AI service)      | 3.10                  |
| Go                       | 1.22                  |
| Django                   | 5.2.12                |
| DRF                      | 3.15.2                |
| FastAPI                  | 0.134.0               |
| Gin                      | 1.10.0                |
| Celery                   | 5.4.0                 |
| SQLAlchemy               | 2.0.35–2.0.47         |
| Pydantic                 | 2.9.0–2.12.5          |
| MySQL                    | 8.0                   |
| Redis                    | 7 (Alpine)            |
| RabbitMQ                 | 3 (Management Alpine) |
| PyTorch                  | ≥2.0, <2.6            |
| Ultralytics              | 8.4.18                |
| Gorilla WebSocket        | 1.5.3                 |

---

## 10. ⚠️ Gotchas & Notes

- [ ] **[NOTE]** AI service uses Python 3.10 while all other Python services use 3.11 — likely due to PyTorch compatibility.
- [ ] **[NOTE]** Chatbot config.py has a hardcoded Gemini API key (`AIzaSyC6NTI...`) — **security concern** per enterprise standards (should be env-only).
- [ ] **[NOTE]** Notification service config has hardcoded default password `parksmartpass` — acceptable for dev defaults only.
- [ ] **[NOTE]** Vehicle service has no exposed host port in docker-compose — only accessible via gateway or internal network.
- [ ] **[NOTE]** SQLAlchemy version varies across FastAPI services (2.0.35 chatbot, 2.0.36 payment/notification, 2.0.47 AI) — minor inconsistency.
- [ ] **[NOTE]** Starlette version mismatch: AI service uses 0.52.1, others use 0.49.1 — may cause subtle behavior differences.
- [ ] **[NOTE]** Django services all share a single `parksmartdb` database with no schema isolation — relies on unique table names per service.

---

## 11. Nguồn

| #   | File                                            | Mô tả                      |
| --- | ----------------------------------------------- | -------------------------- |
| 1   | `auth-service/requirements.txt`                 | Auth deps                  |
| 2   | `auth-service/auth_service/settings.py`         | Auth config (180 lines)    |
| 3   | `auth-service/users/models.py`                  | User model                 |
| 4   | `booking-service/requirements.txt`              | Booking deps (with Celery) |
| 5   | `booking-service/booking_service/settings.py`   | Booking config             |
| 6   | `booking-service/booking_service/celery.py`     | Celery beat schedule       |
| 7   | `booking-service/bookings/models.py`            | Booking data model         |
| 8   | `parking-service/infrastructure/models.py`      | Parking domain model       |
| 9   | `vehicle-service/vehicles/models.py`            | Vehicle model              |
| 10  | `ai-service-fastapi/requirements.txt`           | AI/ML full dep list        |
| 11  | `ai-service-fastapi/app/main.py`                | AI service entry           |
| 12  | `ai-service-fastapi/app/config.py`              | AI config                  |
| 13  | `chatbot-service-fastapi/requirements.txt`      | Chatbot deps               |
| 14  | `chatbot-service-fastapi/app/main.py`           | Chatbot v3.0 lifecycle     |
| 15  | `chatbot-service-fastapi/app/config.py`         | Chatbot config             |
| 16  | `payment-service-fastapi/requirements.txt`      | Payment deps               |
| 17  | `notification-service-fastapi/requirements.txt` | Notification deps          |
| 18  | `gateway-service-go/go.mod`                     | Go gateway deps            |
| 19  | `gateway-service-go/cmd/server/main.go`         | Gateway entry              |
| 20  | `gateway-service-go/internal/config/config.go`  | Gateway config             |
| 21  | `gateway-service-go/internal/router/routes.go`  | Gateway routing            |
| 22  | `realtime-service-go/go.mod`                    | Realtime deps              |
| 23  | `realtime-service-go/cmd/server/main.go`        | Realtime entry + WS        |
| 24  | `docker-compose.yml`                            | Full orchestration         |
| 25  | `init-mysql.sql`                                | Chatbot schema             |
| 26  | `shared/gateway_middleware.py`                  | Shared Django middleware   |
| 27  | `shared/gateway_permissions.py`                 | Shared DRF permissions     |
| 28  | `shared/permissions.py`                         | Internal service auth      |
