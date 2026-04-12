# ParkSmart — Comprehensive Technical Audit Report

**Date:** 2026-03-27 | **Type:** Full System Audit | **Scope:** All services, infra, frontend, AI, hardware

---

## 1. TL;DR

> 1. **10 microservices** (4 Django, 4 FastAPI, 2 Go) + 3 infra containers (MySQL, Redis, RabbitMQ) — well-structured, single shared DB `parksmartdb`
> 2. **AI models are NOT trained** — 0/6 ML model files exist; banknote detection runs on stubs/fallbacks
> 3. **Security is solid** at gateway level (session-based auth, gateway secret, header injection protection) but has gaps (ESP32 endpoints bypass auth, hardcoded defaults in config)
> 4. **Frontend is mature** — 18+ pages, Redux + React Query, Playwright E2E + Vitest unit tests
> 5. **Known vulnerability** — `PyJWT CVE-2026-32597` in base requirements; `torch==1.13.1` cannot be audited

---

## 2. Project Structure

```
Project_Main/
├── .github/                          # CI/CD, agent configs, hooks
│   ├── workflows/ci.yml              # Lint → Test → Build pipeline
│   └── workflows/deploy-cloudflare-pages.yml
├── backend-microservices/            # All backend services
│   ├── auth-service/                 # Django REST — User auth
│   ├── booking-service/              # Django REST — Bookings + Celery
│   ├── parking-service/              # Django REST — Infrastructure
│   ├── vehicle-service/              # Django REST — Vehicles
│   ├── ai-service-fastapi/           # FastAPI — AI/ML (YOLO, OCR, banknote)
│   ├── chatbot-service-fastapi/      # FastAPI — Gemini-powered chatbot
│   ├── notification-service-fastapi/ # FastAPI — Notifications
│   ├── payment-service-fastapi/      # FastAPI — Payments
│   ├── gateway-service-go/           # Go Gin — API Gateway + Auth
│   ├── realtime-service-go/          # Go Gin — WebSocket service
│   ├── shared/                       # Shared middleware (Python)
│   ├── docker-compose.yml            # Dev compose (15 containers)
│   └── docker-compose.prod.yml       # Production override
├── spotlove-ai/                      # React frontend (Vite + TS)
├── hardware/
│   ├── arduino/barrier_control/      # Arduino servo barrier control
│   └── esp32/esp32_gate_controller/  # ESP32 WiFi gate controller
├── infra/
│   ├── nginx/nginx.conf              # Reverse proxy config
│   └── cloudflare/                   # Cloudflare tunnel + security rules
├── scripts/deploy-local.ps1          # Local deployment script
└── docs/                             # Architecture, research, security docs
```

---

## 3. Microservice Registry

### 3.1 Service Port Map

| Service | External Port | Internal Port | Framework | Language | Docker Container |
|---------|:------------:|:-------------:|-----------|----------|-----------------|
| **Gateway** | 8000 | 8000 | Gin | Go 1.24 | gateway-service-go |
| **Auth** | 8001 | 8000 | Django REST | Python 3.11 | auth-service |
| **Booking** | 8002 | 8000 | Django REST | Python 3.11 | booking-service |
| **Parking** | 8003 | 8000 | Django REST | Python 3.11 | parking-service |
| **Vehicle** | — (expose) | 8000 | Django REST | Python 3.11 | vehicle-service |
| **Notification** | — (expose) | 8005 | FastAPI | Python 3.11 | notification-service-fastapi |
| **Realtime** | 8006 | 8006 | Gin | Go 1.24 | realtime-service-go |
| **Payment** | — (expose) | 8007 | FastAPI | Python 3.11 | payment-service-fastapi |
| **Chatbot** | — (expose) | 8008 | FastAPI | Python 3.11 | chatbot-service-fastapi |
| **AI** | — (expose) | 8009 | FastAPI | Python 3.10 | ai-service-fastapi |
| **MySQL** | 3307 | 3306 | MySQL 8.0 | — | parksmartdb_mysql |
| **Redis** | 6379 | 6379 | Redis 7 Alpine | — | parksmartdb_redis |
| **RabbitMQ** | 5672/15672 | 5672 | RabbitMQ 3 Mgmt | — | parksmartdb_rabbitmq |
| Booking Celery Worker | — | — | Celery | Python 3.11 | booking-celery-worker |
| Booking Celery Beat | — | — | Celery Beat | Python 3.11 | booking-celery-beat |
| Nginx (prod only) | 80 | 80 | Nginx Alpine | — | parksmart_nginx |

### 3.2 Redis DB Allocation

| DB # | Service | Purpose |
|------|---------|---------|
| 0 | Celery | Broker + Result backend |
| 1 | Gateway + Auth | Session store |
| 2 | Booking | Cache |
| 3 | Parking | Cache |
| 4 | Vehicle | Cache |
| 5 | Realtime | WebSocket state |
| 6 | Chatbot | Conversation cache |

---

## 4. Per-Service Detail

### 4.1 Gateway Service (Go)

**Path:** `backend-microservices/gateway-service-go/`
**Framework:** Go 1.24 + Gin
**Modules:** `go.mod` — `github.com/gin-gonic/gin`, `github.com/go-redis/redis/v8`, `github.com/google/uuid`

**Key Files:**
| File | Purpose |
|------|---------|
| `cmd/main.go` | Entry point — loads config, creates Redis session store, registers handlers |
| `internal/config/config.go` | All env vars, service route mapping, production validation |
| `internal/router/routes.go` | Single catch-all route pattern: health → auth special → auth middleware → proxy |
| `internal/handler/proxy.go` | Reverse proxy to microservices — strips/injects headers |
| `internal/handler/auth.go` | Login (creates Redis session), Logout, OAuth callbacks |
| `internal/middleware/auth.go` | Session validation from Redis, user context injection |
| `internal/middleware/cors.go` | CORS configuration |
| `internal/middleware/rate_limit.go` | Rate limiting |
| `internal/middleware/logging.go` | Request logging |
| `internal/session/redis.go` | Redis session store |

**Route Mapping** (from `config.go:GetServiceRoute()`):
| Path Prefix | Target Service | Public? |
|-------------|---------------|---------|
| `auth/admin/` | auth-service | No |
| `auth/me` | auth-service | No |
| `auth/change-password/` | auth-service | No |
| `auth/` | auth-service | **Yes** |
| `parking/` | parking-service | No |
| `vehicles/` | vehicle-service | No |
| `bookings/` | booking-service | No |
| `incidents/` | booking-service | No |
| `notifications/` | notification-service | No |
| `realtime/` | realtime-service | No |
| `payments/` | payment-service | No |
| `ai/` | ai-service | No |
| `chatbot/` | chatbot-service | No |

**Auth Flow:**
1. Client sends `POST /api/auth/login/` with credentials
2. Gateway proxies to auth-service, gets user data
3. Gateway creates Redis session, sets `session_id` HttpOnly cookie
4. Subsequent requests: gateway reads `session_id` cookie → validates in Redis → injects `X-User-ID`, `X-User-Email`, `X-User-Role`, `X-User-Is-Staff`, `X-Gateway-Secret` headers → proxies
5. Downstream services validate `X-Gateway-Secret` and trust `X-User-*` headers

**Security:**
- Strips client-supplied `X-User-*` headers before proxying (prevents header injection)
- Production validation: requires HTTPS CORS origins, secure cookies, no localhost
- Tests: `proxy_test.go` (7 tests), `middleware_test.go` (4+ tests)

**Known Issues:**
- Default fallback URLs in `config.go` use generic ports (`:8000`) that don't match Docker compose for notification/payment/AI/chatbot — only works because Docker DNS names are used

---

### 4.2 Auth Service (Django)

**Path:** `backend-microservices/auth-service/`
**Port:** 8001:8000 | **DB:** `parksmartdb` (MySQL)

**Key Files:**
| File | Purpose |
|------|---------|
| `users/models.py` | `User` (AbstractUser + UUID PK), `OAuthAccount`, `PasswordReset` |
| `users/views.py` | Login/Register/Logout/Me/ChangePassword/ForgotPassword/ResetPassword/Admin views |
| `users/urls.py` | URL routing |
| `auth_service/settings.py` | Django settings with decouple config |

**Database Models:**

**`User`** (table: `users_user`):
- `id` UUID PK, `email` unique, `username`, `phone`, `address`, `avatar`
- `role` (user/admin), `no_show_count`, `force_online_payment`
- Extends AbstractUser (has `is_staff`, `is_superuser`, etc.)

**`OAuthAccount`** (table: `users_oauth_account`):
- `user` FK → User, `provider` (google/facebook), `provider_user_id`
- `access_token`, `refresh_token`, `token_expires_at`

**`PasswordReset`** (table: `users_password_reset`):
- `user` FK → User, `token` unique, `expires_at`, `used`

**Tests:** `tests/` directory exists
**Known Issues:**
- OAuth tokens stored in plaintext in DB (access_token, refresh_token)

---

### 4.3 Booking Service (Django + Celery)

**Path:** `backend-microservices/booking-service/`
**Port:** 8002:8000 | **Celery:** Worker + Beat containers

**Database Models:**

**`PackagePricing`** (table: `package_pricing`):
- `package_type` (hourly/daily/weekly/monthly), `vehicle_type`, `price`, `duration_days`

**`Booking`** (table: `booking`):
- Denormalized: `user_id`, `user_email`, `vehicle_id`, `vehicle_license_plate`, `vehicle_type`
- Denormalized: `parking_lot_id`, `parking_lot_name`, `floor_id`, `zone_id`, `zone_name`, `slot_id`, `slot_code`
- `package_type`, `start_time`, `end_time`, `payment_method` (online/on_exit), `payment_status`, `price`
- `check_in_status` (not_checked_in/checked_in/checked_out/no_show/cancelled)
- `qr_code_data`, `hourly_start`, `hourly_end`, `extended_until`, `late_fee_applied`

**Celery Tasks:** Background jobs via Celery worker + beat (no-show detection, booking expiry)
**Dependencies:** RabbitMQ (AMQP), Redis (broker), inter-service calls to vehicle/parking/auth/notification/realtime services

---

### 4.4 Parking Service (Django)

**Path:** `backend-microservices/parking-service/`
**Port:** 8003:8000

**Database Models:**

**`ParkingLot`** (table: `parking_lot`):
- `name`, `address`, `latitude`/`longitude`, `total_slots`, `available_slots`, `price_per_hour`, `is_open`

**`Floor`** (table: `floor`):
- FK → ParkingLot, `level`, `name`

**`Zone`** (table: `zone`):
- FK → Floor, `name`, `vehicle_type` (Car/Motorbike), `capacity`, `available_slots`

**`CarSlot`** (table: — from migration):
- FK → Zone, `code`, `status` (available/occupied/reserved/maintenance), `x1/y1/x2/y2` (map coordinates)

**`Camera`** (table: `infrastructure_camera`):
- FK → Zone (nullable), `name`, `ip_address`, `port`, `stream_url`, `is_active`

---

### 4.5 Vehicle Service (Django)

**Path:** `backend-microservices/vehicle-service/`
**Port:** exposed only (8000 internal)

**Database Models:**

**`Vehicle`** (table: from model):
- `user_id` UUID (reference to auth-service), `license_plate` unique, `vehicle_type` (Car/Motorbike)
- `brand`, `model`, `color`, `is_default`

---

### 4.6 AI Service (FastAPI)

**Path:** `backend-microservices/ai-service-fastapi/`
**Port:** 8009 | **Python:** 3.10 (not 3.11 — Dockerfile uses `python:3.10-slim`)

**Key Files:**
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app with gateway middleware, CORS, routers |
| `app/config.py` | Settings (DB, model paths, service URLs) |
| `app/routers/detection.py` | `/ai/detect/license-plate/`, `/ai/detect/cash/`, `/ai/detect/banknote/` |
| `app/routers/camera.py` | `/ai/cameras/list` — hardcoded camera config |
| `app/routers/esp32.py` | ESP32 gate endpoints (check-in/out, verify-slot, cash-payment) |
| `app/engine/plate_detector.py` | YOLO v8 license plate detection |
| `app/engine/plate_ocr.py` | TrOCR → EasyOCR → Tesseract OCR chain |
| `app/engine/plate_pipeline.py` | Full plate recognition pipeline |
| `app/engine/detector.py` | YOLO v8 banknote detection (with fallback) |
| `app/engine/ai_classifier.py` | Neural network banknote classifier |
| `app/engine/color_classifier.py` | HSV histogram-based classification |
| `app/engine/pipeline.py` | Banknote recognition pipeline (detect → classify) |
| `app/ml/inference/cash_recognition.py` | ResNet50/EfficientNet-B3 inference |
| `app/ml/banknote/train_classifier.py` | EfficientNetV2-S training script |
| `train_and_evaluate.py` | ResNet50 training pipeline |
| `train_mobilenetv3.py` | MobileNetV3 training script |

**Database Models (SQLAlchemy):**

**`CameraFeed`** (table: `api_camerafeed`): camera_id, frame_url, detections (JSON)
**`PredictionLog`** (table: `api_predictionlog`): prediction_type, input_data, output_data, confidence, model_version, processing_time
**`ModelVersion`** (table: `api_modelversion`): model_type, version, file_path, status, accuracy/precision/recall/f1/mAP metrics

**AI/ML Models:**

| Model | Architecture | File Needed | Status |
|-------|-------------|-------------|--------|
| License Plate Detector | YOLO v8 (fine-tuned) | `license-plate-finetune-v1m.pt` | Configured in settings |
| Banknote Detector | YOLO v8n | `banknote_yolov8n.pt` | **NOT TRAINED** — uses full-image fallback |
| Banknote AI Classifier | MobileNetV3-Large | `banknote_mobilenetv3.pth` | **NOT TRAINED** — returns stub |
| Cash Recognition | ResNet50 / EfficientNet-B3 | `cash_recognition_best.pth` | **NOT TRAINED** |
| Parking Occupancy | YOLO 11n | `yolo11n.pt` | Configured but unverified |
| TrOCR | HuggingFace Transformers | Auto-downloaded | Available |
| EasyOCR | EasyOCR | Auto-downloaded | Available |

**Major Dependencies:** `ultralytics==8.4.18`, `easyocr==1.7.2`, `torch==1.13.1`, `torchvision==0.14.1`, `opencv-python-headless==4.10.0.84`, `fastapi==0.134.0`, `SQLAlchemy==2.0.47`

**[CRITICAL] torch==1.13.1** — very old version (2022), cannot be pip-audited, incompatible with `+cu116` suffix in some references

---

### 4.7 Chatbot Service (FastAPI)

**Path:** `backend-microservices/chatbot-service-fastapi/`
**Port:** 8008 | **LLM:** Google Gemini (via `GEMINI_API_KEY`)

**Key Files:**
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, LLM client init, service client init |
| `app/routers/chat.py` | `POST /chatbot/chat/` — main chat endpoint |
| `app/routers/conversation.py` | Conversation CRUD |
| `app/engine/orchestrator.py` | 6-stage message processing pipeline |
| `app/infrastructure/llm/` | Gemini client + prompt templates |

**Database Models (9 tables, SQLAlchemy):**

| Model | Table | Purpose |
|-------|-------|---------|
| `Conversation` | `chatbot_conversation` | Session with state machine (`idle`, etc.) |
| `ChatMessage` | `chatbot_chatmessage` | Messages with intent, entities, confidence |
| `UserPreferences` | `chatbot_user_preferences` | Favorite lots/zones/vehicles |
| `UserBehavior` | `chatbot_user_behavior` | Usage patterns, arrival times, cancel rates |
| `UserCommunicationStyle` | `chatbot_user_communication_style` | Emoji/formality preferences |
| `ConversationSummary` | `chatbot_conversation_summary` | Memory summaries |
| `ProactiveNotification` | `chatbot_proactive_notification` | Proactive alerts |
| `ActionLog` | `chatbot_action_log` | Undoable action tracking |
| `AIMetricLog` | `chatbot_ai_metric_log` | Observability metrics |

**Dependencies:** Redis (DB 6), RabbitMQ, calls to booking/parking/vehicle/payment/realtime services

---

### 4.8 Notification Service (FastAPI)

**Path:** `backend-microservices/notification-service-fastapi/`
**Port:** 8005

**Database Models (SQLAlchemy):**

| Model | Table |
|-------|-------|
| `NotificationPreference` | `notifications_notificationpreference` |
| `Notification` | `notifications_notification` |

---

### 4.9 Payment Service (FastAPI)

**Path:** `backend-microservices/payment-service-fastapi/`
**Port:** 8007

**Database Models (SQLAlchemy):**

**`Payment`** (table: `payments_payment`):
- `booking_id`, `user_id`, `payment_method` (momo/vnpay/zalopay/cash)
- `amount`, `transaction_id`, `payment_url`, `qr_code_url`
- `status` (pending/processing/completed/failed/refunded/cancelled)
- `gateway_response` (JSON)

---

### 4.10 Realtime Service (Go)

**Path:** `backend-microservices/realtime-service-go/`
**Port:** 8006 | **Go:** 1.24 + Gin
**Purpose:** WebSocket connections for real-time updates (slot status, notifications)
**Dependencies:** Redis (DB 5)

---

## 5. Shared Infrastructure

### 5.1 Shared Python Package

**Path:** `backend-microservices/shared/`

| File | Purpose |
|------|---------|
| `gateway_middleware.py` | Django middleware: validates `X-Gateway-Secret`, extracts `X-User-*` headers |
| `gateway_permissions.py` | DRF permissions: `IsGatewayAuthenticated`, `IsGatewayAdmin` |
| `permissions.py` | Additional permission classes |
| `setup.py` | Installable package `parksmart-shared` v1.0.0 |
| `requirements-base.txt` | Base deps: Django>=4.2.29, DRF>=3.14, celery>=5.4, mysqlclient, etc. |

### 5.2 Database

- **Single database:** `parksmartdb` (MySQL 8.0)
- **All services share** the same database but own separate tables
- Initial schema: `init-mysql.sql` creates chatbot/notification tables (FastAPI services don't use Django migrations)
- Django services run `manage.py migrate` on startup

### 5.3 Message Queue

- **RabbitMQ** — used for async events between services (booking events → notifications)
- **Celery** — booking-service uses Celery worker + beat for background tasks (no-show detection, expiry)
- Broker: Redis DB 0

---

## 6. Frontend (spotlove-ai)

### 6.1 Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 18.3.1 | UI framework |
| TypeScript | 5.8.3 | Type safety |
| Vite | 5.4.19 | Build tool (port 8080 dev) |
| Redux Toolkit | 2.11.2 | Global state |
| React Query | 5.83.0 | Server state |
| React Router DOM | 6.30.1 | Routing |
| Tailwind CSS | 3.4.17 | Styling |
| shadcn/ui (Radix) | Various | Component library |
| Axios | 1.13.2 | HTTP client |
| Zod | 3.25.76 | Validation |
| Recharts | 2.15.4 | Charts |
| Vitest | 3.2.4 | Unit testing |
| Playwright | 1.58.2 | E2E testing |

### 6.2 Route Map

**Public Routes:**
| Path | Component |
|------|-----------|
| `/login` | LoginPage |
| `/register` | RegisterPage |
| `/auth/callback` | AuthCallbackPage (OAuth) |
| `/kiosk` | KioskPage (public check-in) |

**Protected User Routes:**
| Path | Component |
|------|-----------|
| `/` | Index → UserDashboard (or redirect admin) |
| `/booking` | BookingPage (standard, auto-guarantee, calendar-hold tabs) |
| `/history` | HistoryPage (with charts) |
| `/cameras` | CamerasPage (live feeds) |
| `/map` | MapPage (SVG parking map with Dijkstra pathfinding) |
| `/support` | SupportPage (chatbot) |
| `/settings` | SettingsPage |
| `/payment` | PaymentPage (QR code payment) |
| `/panic` | PanicButtonPage |
| `/banknote-detection` | BanknoteDetectionPage |
| `/check-in-out` | CheckInOutPage |

**Admin Routes** (requireAdmin):
| Path | Component |
|------|-----------|
| `/admin/dashboard` | AdminDashboard |
| `/admin/users` | AdminUsersPage |
| `/admin/zones` | AdminZonesPage |
| `/admin/slots` | AdminSlotsPage |
| `/admin/cameras` | AdminCamerasPage |
| `/admin/config` | AdminConfigPage |
| `/admin/violations` | AdminViolationsPage |
| `/admin/esp32` | AdminESP32Page |
| `/admin/revenue` | AdminRevenuePage |

### 6.3 State Management

- **Redux Toolkit** slices: `authSlice`, `bookingSlice`, `parkingSlice`, `notificationSlice`, `websocketSlice`
- **React Query** for server state cache
- **Context:** `AuthContext`, `ThemeContext`

### 6.4 API Layer

Central endpoint config: `src/services/api/endpoints.ts`
API clients: `auth.api.ts`, `booking.api.ts`, `parking.api.ts`, `vehicle.api.ts`, `ai.api.ts`, `chatbot.api.ts`, `notification.api.ts`, `incident.api.ts`, `admin.api.ts`
HTTP client: `axios.client.ts` (with interceptors)
WebSocket: `websocket.service.ts`

**Vite Proxy:** `/api/*` → `localhost:8000` (gateway)

### 6.5 Testing

**Unit Tests (Vitest):** `src/test/` — 11 test files
- `smoke.test.tsx`, `auth-api.test.ts`, `booking-api.test.ts`, `chatbot-api.test.ts`, `notification-api.test.ts`, `ai-api.test.ts`, `axios-client-utils.test.ts`, `banknote-detection-page.test.tsx`, `support-page.test.tsx`

**E2E Tests (Playwright):** `e2e/` — 10 spec files
- `public-pages.spec.ts`, `user-pages.spec.ts`, `admin.pages.spec.ts`, `admin.management.spec.ts`, `booking.spec.ts`, `dashboard.spec.ts`, `history.spec.ts`, `full-flows.spec.ts`, `api-endpoints.spec.ts`

**Known Issues:**
- `@supabase/supabase-js` in dependencies — appears unused (no Supabase integration found)
- `lovable-tagger` in devDependencies — unclear purpose
- PaymentPage has hardcoded bank info with TODO comment (line ~30): `// TODO: Move these values to environment variables`

---

## 7. Hardware Integration

### 7.1 ESP32 Gate Controller

**Path:** `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino`

- WiFi-connected ESP32 microcontroller
- Communicates with AI service via HTTP
- Endpoints used: `/ai/parking/esp32/check-in`, `/ai/parking/esp32/check-out`, `/ai/parking/esp32/verify-slot`, `/ai/parking/esp32/cash-payment`, `/ai/parking/esp32/register`, `/ai/parking/esp32/heartbeat`
- Controls physical gate barrier (servo)

### 7.2 Arduino Barrier Control

**Path:** `hardware/arduino/barrier_control/barrier_control.ino`

- Arduino-based servo barrier controller
- Simpler standalone barrier control

**[SECURITY NOTE]:** ESP32 endpoints are **exempted from gateway auth** in `ai-service-fastapi/app/middleware/gateway_auth.py` (lines 16-28). These endpoints have NO authentication — any device on the network can call them.

---

## 8. Infrastructure

### 8.1 Docker Compose

**Dev:** `backend-microservices/docker-compose.yml` — 15+ containers, bridge network `parksmart-network`
**Prod:** `docker-compose.prod.yml` — overlay with nginx, production CORS/ALLOWED_HOSTS

**Volumes:** `mysql_data`, `redis_data`, `rabbitmq_data`, `ai_models`, `ai_datasets`, `parksmart_media`

### 8.2 Nginx

**Path:** `infra/nginx/nginx.conf`

- Serves frontend static files from `spotlove-ai/dist/`
- Proxies `/api/*` → gateway (upstream `api_backend`)
- Proxies `/ws/` → realtime service (WebSocket upgrade)
- Security headers: HSTS, X-Content-Type-Options, X-Frame-Options
- Static asset caching: 1 year with `immutable`
- SPA fallback: `try_files $uri $uri/ /index.html`

### 8.3 Cloudflare

**Path:** `infra/cloudflare/`

- `cloudflared/` — Cloudflare Tunnel configuration
- `reverse-proxy/` — Reverse proxy rules
- `security-controls/` — Rate limit rules, WAF templates

**Production Domains:**
- Frontend: `app.ghepdoicaulong.shop` / `parksmart.ghepdoicaulong.shop`
- API: `api.ghepdoicaulong.shop`

---

## 9. CI/CD

### 9.1 GitHub Actions

**`.github/workflows/ci.yml`:**

| Job | Trigger | Steps |
|-----|---------|-------|
| `backend-structure-check` | push/PR to main/develop | Verify directory layout exists |
| `lint-frontend` | push/PR to main/develop | `npm ci` → `npm run lint` |
| `test-frontend` | after lint | `npm ci` → `npm run test` (Vitest) |
| `build-frontend` | after test | `npm ci` → `npm run build` → `npm audit --audit-level=high` |

**`.github/workflows/deploy-cloudflare-pages.yml`:** Cloudflare Pages deployment

**Missing CI:**
- No backend Python tests in CI pipeline
- No Go tests in CI pipeline
- No Docker build verification
- No integration tests
- No E2E (Playwright) tests in CI

### 9.2 Git Hooks

**Path:** `.github/hooks/` — exists but contents not verified

---

## 10. Security Analysis

### 10.1 Authentication

- **Session-based** (not JWT) — Redis session store with HttpOnly cookie
- Gateway validates session → injects user context headers
- OAuth: Google + Facebook (callback handling in gateway)
- Password hashing: Django's default (PBKDF2)

### 10.2 Authorization

- Gateway middleware: public endpoints don't require session
- Downstream services use `IsGatewayAuthenticated` / `IsGatewayAdmin` DRF permissions
- FastAPI services check `X-User-Role` and `X-User-Is-Staff` headers
- Admin routes: `requireAdmin` in frontend ProtectedRoute

### 10.3 Security Positives

- ✅ Gateway strips client-supplied `X-User-*` headers (prevents impersonation)
- ✅ Gateway secret required for all non-public microservice requests
- ✅ Production config validation (HTTPS-only CORS, secure cookies, no localhost)
- ✅ CORS properly configured per environment
- ✅ Health endpoints exempted from auth (proper pattern)
- ✅ Rate limiting middleware in gateway
- ✅ Nginx security headers (HSTS, X-Frame-Options, X-Content-Type-Options)
- ✅ Parameterized queries (Django ORM, SQLAlchemy)
- ✅ Input validation via Pydantic/DRF serializers

### 10.4 Security Concerns

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | **HIGH** | ESP32 endpoints completely bypass gateway auth | `ai-service-fastapi/app/middleware/gateway_auth.py` EXEMPT_PATHS |
| 2 | **HIGH** | `PyJWT CVE-2026-32597` — requires ≥2.12.0, have 2.10.1 | `backend-microservices/requirements.txt` |
| 3 | **MEDIUM** | Hardcoded default `GATEWAY_SECRET` in ai-service config | `ai-service-fastapi/app/config.py:15` (`"gateway-internal-secret-key"`) |
| 4 | **MEDIUM** | OAuth tokens stored in plaintext | `auth-service/users/models.py` — OAuthAccount.access_token/refresh_token |
| 5 | **MEDIUM** | `DB_PASSWORD` hardcoded default `"rootpassword"` in AI config | `ai-service-fastapi/app/config.py:12` |
| 6 | **LOW** | Camera IPs hardcoded in AI service | `ai-service-fastapi/app/routers/camera.py:29-31` |
| 7 | **LOW** | Bank account info hardcoded in PaymentPage | `spotlove-ai/src/pages/PaymentPage.tsx` |
| 8 | **LOW** | `.env` files present in multiple services (should be gitignored) | Multiple `.env` files exist |

---

## 11. Configuration

### 11.1 Environment Variables

**Backend `.env.example`:**
```
SECRET_KEY=your-django-secret-key-here
DEBUG=True
DB_USER=parksmart_user
DB_PASSWORD=your-db-password-here
RABBITMQ_USER=parksmart_rabbit
RABBITMQ_PASS=your-rabbitmq-password-here
GATEWAY_SECRET=your-gateway-secret-here
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.0-flash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
FACEBOOK_APP_ID=...
FACEBOOK_APP_SECRET=...
FE_AUTH_CALLBACK_URL=http://localhost:5173/auth/callback
```

**Frontend `.env.example`:**
```
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8006/ws
VITE_GATEWAY_SECRET=...
```

### 11.2 Production Environment

- `docker-compose.prod.yml` overrides: DEBUG=False, proper ALLOWED_HOSTS, CORS for production domains
- OAuth redirect URIs set to `api.ghepdoicaulong.shop`
- Session cookies: `SESSION_COOKIE_DOMAIN=.ghepdoicaulong.shop`, `SESSION_COOKIE_SECURE=true`

---

## 12. Database Schema Summary

### 12.1 All Tables

| Service | Table | ORM |
|---------|-------|-----|
| auth | `users_user` | Django |
| auth | `users_oauth_account` | Django |
| auth | `users_password_reset` | Django |
| parking | `parking_lot` | Django |
| parking | `floor` | Django |
| parking | `zone` | Django |
| parking | `car_slot` (from migration) | Django |
| parking | `infrastructure_camera` | Django |
| parking | `auth_user_proxy` | Django |
| vehicle | `vehicles_vehicle` | Django |
| booking | `booking` | Django |
| booking | `package_pricing` | Django |
| ai | `api_camerafeed` | SQLAlchemy |
| ai | `api_predictionlog` | SQLAlchemy |
| ai | `api_modelversion` | SQLAlchemy |
| chatbot | `chatbot_conversation` | SQLAlchemy |
| chatbot | `chatbot_chatmessage` | SQLAlchemy |
| chatbot | `chatbot_user_preferences` | SQLAlchemy |
| chatbot | `chatbot_user_behavior` | SQLAlchemy |
| chatbot | `chatbot_user_communication_style` | SQLAlchemy |
| chatbot | `chatbot_conversation_summary` | SQLAlchemy |
| chatbot | `chatbot_proactive_notification` | SQLAlchemy |
| chatbot | `chatbot_action_log` | SQLAlchemy |
| chatbot | `chatbot_ai_metric_log` | SQLAlchemy |
| notification | `notifications_notification` | SQLAlchemy |
| notification | `notifications_notificationpreference` | SQLAlchemy |
| payment | `payments_payment` | SQLAlchemy |

Total: **~26 tables** (+ Django system tables like auth_group, django_session, etc.)

---

## 13. Testing Coverage

### 13.1 Backend Tests

| Service | Test Dir | Test Files | Framework |
|---------|----------|------------|-----------|
| gateway-service-go | `internal/*/` | `proxy_test.go`, `middleware_test.go` | Go testing |
| auth-service | `tests/` | Present | pytest |
| booking-service | `tests/` | Present | pytest |
| parking-service | `tests/` | Present | pytest |
| vehicle-service | `tests/` | Present | pytest |
| ai-service-fastapi | `tests/` | Present | pytest |
| chatbot-service-fastapi | `tests/` | `test_smoke.py` | pytest (anyio) |
| notification-service-fastapi | `tests/` | Present | pytest |
| payment-service-fastapi | `tests/` | Present | pytest |

**Integration/E2E test scripts** (root of backend-microservices):
- `test_e2e_full_flow.py`
- `test_ai_full.py`
- `test_chatbot_e2e.py`
- `test_chatbot_lifecycle.py`
- `test_booking_plate_scenarios.py`

### 13.2 Frontend Tests

- **Unit:** 11 Vitest files in `src/test/`
- **E2E:** 10 Playwright specs in `e2e/`
- **Config:** `vitest.config.ts`, `playwright.config.ts`

### 13.3 What's NOT Tested

- No backend tests in CI pipeline
- No Go tests in CI
- No coverage reporting configured
- AI model accuracy not validated (models don't exist)
- ESP32/hardware integration untested
- Payment gateway integration likely mock-only

---

## 14. Known Issues & Technical Debt

### 14.1 BLOCKERS

| # | Issue | Impact |
|---|-------|--------|
| 1 | **0 trained AI models** — banknote detection, cash recognition, banknote classifier all use fallback/stub | Core AI features non-functional |
| 2 | **PyJWT CVE-2026-32597** — High severity vulnerability | Security blocker |
| 3 | **torch==1.13.1** — Cannot be pip-audited, very old (2022), potential CVEs | Security/compatibility risk |

### 14.2 WARNINGS

| # | Issue | Location |
|---|-------|----------|
| 1 | ESP32 endpoints have zero authentication | `ai-service-fastapi/app/middleware/gateway_auth.py` |
| 2 | Multiple `.env` files committed to repo (not just `.env.example`) | Various service dirs |
| 3 | `UserCommunicationStyle` model is never written to | `docs/02_AI_CHATBOT_OVERVIEW.md` confirms |
| 4 | Hardcoded camera URLs (192.168.x.x) | `ai-service-fastapi/app/routers/camera.py` |
| 5 | Hardcoded bank account info in PaymentPage | `spotlove-ai/src/pages/PaymentPage.tsx` |
| 6 | `@supabase/supabase-js` in FE deps — appears unused | `spotlove-ai/package.json` |
| 7 | Backend tests not in CI pipeline | `.github/workflows/ci.yml` |
| 8 | Default secret values in config files | `ai-service-fastapi/app/config.py` |

### 14.3 TODOs Found

- PaymentPage: `// TODO: Move these values to environment variables or a backend config endpoint`
- Multiple endpoint configs commented out as "Not yet implemented": MAP, SUPPORT, CALENDAR, USER profile in `endpoints.ts`

### 14.4 Dead Code / Unused

- `spotlove-ai/.tmp-runtime-check.cjs` — temp file
- `spotlove-ai/vitest.config.ts.timestamp-*` — temp Vite file
- Multiple `check-*-service.log` files in service directories
- `backend-microservices/visualize_parking.py` — utility script
- `backend-microservices/seed_*.py` — seed scripts (may be intentional)

---

## 15. Dependency Versions (Key)

### 15.1 Python (Backend)

| Package | Version | Notes |
|---------|---------|-------|
| Django | >=4.2.29 (resolves to 5.2.12) | OK |
| DRF | >=3.14.0 (resolves to 3.15.2) | OK |
| FastAPI | 0.134.0 | OK |
| Starlette | 0.49.1–0.52.1 | Varies by service |
| SQLAlchemy | 2.0.35–2.0.47 | Varies by service |
| Celery | >=5.4.0 | OK |
| PyJWT | 2.10.1 | **VULNERABLE — CVE-2026-32597** |
| torch | 1.13.1 | **Very old, cannot be audited** |
| ultralytics | 8.4.18 | OK for YOLO |
| Pillow | 12.1.1 | OK |
| requests | 2.32.4–2.32.5 | OK |
| cryptography | 46.0.5 | OK |

### 15.2 Go

| Package | Version |
|---------|---------|
| Go | 1.24.0 |
| gin-gonic/gin | v1.10.1 |
| go-redis/redis | v8.11.5 |
| google/uuid | v1.6.0 |

### 15.3 Frontend (Node)

| Package | Version |
|---------|---------|
| React | 18.3.1 |
| TypeScript | 5.8.3 |
| Vite | 5.4.19 |
| Redux Toolkit | 2.11.2 |
| Axios | 1.13.2 |
| Playwright | 1.58.2 |

---

## 16. Architecture Patterns

- **Gateway Pattern:** Single Go gateway handles auth + routing + CORS + rate limiting
- **Session Auth:** Redis-backed sessions (not JWT tokens)
- **Denormalized Data:** Booking service denormalizes user/vehicle/parking data for independence
- **Proxy User Models:** Non-auth Django services have minimal `User` proxy models for session compatibility
- **CamelCase API:** All responses use `camelCase` via DRF/Pydantic alias generators
- **Shared Middleware:** Python shared package for gateway auth validation
- **Event-Driven:** RabbitMQ for async inter-service events
- **Background Tasks:** Celery worker + beat for booking lifecycle management

---

## Sources

| # | Type | Path |
|---|------|------|
| 1 | Docker Compose | `backend-microservices/docker-compose.yml` |
| 2 | Docker Compose Prod | `backend-microservices/docker-compose.prod.yml` |
| 3 | Gateway Config | `backend-microservices/gateway-service-go/internal/config/config.go` |
| 4 | Gateway Routes | `backend-microservices/gateway-service-go/internal/router/routes.go` |
| 5 | Auth Models | `backend-microservices/auth-service/users/models.py` |
| 6 | Booking Models | `backend-microservices/booking-service/bookings/models.py` |
| 7 | Parking Models | `backend-microservices/parking-service/infrastructure/models.py` |
| 8 | Vehicle Models | `backend-microservices/vehicle-service/vehicles/models.py` |
| 9 | AI Models | `backend-microservices/ai-service-fastapi/app/models/ai.py` |
| 10 | Chatbot Models | `backend-microservices/chatbot-service-fastapi/app/models/chatbot.py` |
| 11 | Payment Models | `backend-microservices/payment-service-fastapi/app/models/payment.py` |
| 12 | Notification Models | `backend-microservices/notification-service-fastapi/app/models/notification.py` |
| 13 | Frontend Routes | `spotlove-ai/src/App.tsx` |
| 14 | API Endpoints | `spotlove-ai/src/services/api/endpoints.ts` |
| 15 | CI Pipeline | `.github/workflows/ci.yml` |
| 16 | Nginx Config | `infra/nginx/nginx.conf` |
| 17 | System Prompt Doc | `docs/PARKSMART_SYSTEM_PROMPT.md` |
| 18 | Security Recheck | `docs/security/ISSUE-SECURITY-BLOCKERS-2026-03-13-recheck-2026-03-14.md` |
