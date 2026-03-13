# ParkSmart — Comprehensive AI Coding System Prompt

> **Version**: 3.2 — Last Updated: 2025-07  
> **Project**: ParkSmart — Smart Parking Management Platform  
> **Stack**: Microservices (Django REST + FastAPI + Go Gin) + React/Vite Frontend + ESP32/Arduino Hardware + AI/ML (YOLO, TrOCR, EasyOCR)

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Infrastructure & DevOps](#3-infrastructure--devops)
4. [Backend Services — Django REST Framework](#4-backend-services--django-rest-framework)
5. [Backend Services — FastAPI](#5-backend-services--fastapi)
6. [Backend Services — Go (Gin)](#6-backend-services--go-gin)
7. [Shared Libraries](#7-shared-libraries)
8. [Frontend — React + Vite + TypeScript](#8-frontend--react--vite--typescript)
9. [AI/ML Engine](#9-aiml-engine)
10. [Hardware Integration](#10-hardware-integration)
11. [Authentication & Authorization Flow](#11-authentication--authorization-flow)
12. [Inter-Service Communication](#12-inter-service-communication)
13. [Database Schema Summary](#13-database-schema-summary)
14. [API Endpoint Reference](#14-api-endpoint-reference)
15. [Testing Strategy](#15-testing-strategy)
16. [Gaps, Redundancies & Improvement Areas](#16-gaps-redundancies--improvement-areas)
17. [Coding Conventions](#17-coding-conventions)
18. [Quick Reference: Ports & Credentials](#18-quick-reference-ports--credentials)

---

## 1. PROJECT OVERVIEW

**ParkSmart** is a full-stack smart parking management platform with:

- **12 microservices** across 3 languages (Python, Go, TypeScript)
- **AI-powered** license plate recognition, banknote detection, and chatbot
- **Real-time** WebSocket-based slot monitoring
- **Hardware integration** with ESP32 + Arduino barriers + RTSP cameras
- **Mobile-first** responsive React frontend with admin dashboard

### Core User Flows

1. **Booking Flow**: User registers → adds vehicle → browses parking lots/zones → books a slot → receives QR code
2. **Check-In Flow**: User arrives → scans QR at ESP32 kiosk → AI reads license plate via camera → validates booking → barrier opens
3. **Check-Out Flow**: User presses check-out button → AI scans plate → calculates fees (including hourly overstay) → cash payment via banknote detection OR online payment → barrier opens
4. **Admin Flow**: Admin dashboard → manages users/slots/zones/cameras → views revenue analytics → handles violations
5. **Chatbot Flow**: User asks questions about parking/bookings → AI chatbot with memory/context → can execute actions (book, cancel, check status)

---

## 2. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/Vite)                         │
│                     localhost:8080 / spotlove-ai/                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ /api/* proxy
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   GATEWAY (Go Gin) :8000                             │
│         Session Auth (Redis) → Proxy → Microservices                 │
│     Headers: X-User-ID, X-User-Email, X-Gateway-Secret              │
└──┬──────┬───────┬───────┬───────┬───────┬────────┬──────┬──────────┘
   │      │       │       │       │       │        │      │
   ▼      ▼       ▼       ▼       ▼       ▼        ▼      ▼
┌─────┐┌──────┐┌──────┐┌──────┐┌──────┐┌───────┐┌─────┐┌───────┐
│Auth ││Book- ││Park- ││Vehi- ││Noti- ││Pay-   ││Chat-││AI     │
│:8001││ing   ││ing   ││cle   ││fica- ││ment   ││bot  ││Svc   │
│     ││:8002 ││:8003 ││:8004 ││tion  ││:8007  ││:8008││:8009  │
│DRF  ││DRF   ││DRF   ││DRF   ││:8005 ││FastAPI││Fast ││Fast   │
│     ││+Celry││      ││      ││FastAPI││      ││API  ││API    │
└──┬──┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬──┘└──┬────┘
   │      │       │       │       │       │       │      │
   └──────┴───────┴───────┴───────┴───────┴───────┴──┬───┘
                                                      │
┌─────────────────────────────────────────────────────┴──────────────┐
│              INFRASTRUCTURE                                         │
│  MySQL 8.0 (:3307)  │  Redis 7 (:6379)  │  RabbitMQ 3 (:5672)     │
└─────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────────┐
│              REALTIME (Go Gin) :8006                                 │
│         WebSocket Hub — gorilla/websocket                            │
│    /ws/parking (public) │ /ws/user?userId=X (authenticated)         │
└─────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────────┐
│              HARDWARE LAYER                                          │
│  ESP32 (WiFi+OLED+GPIO) ←UART→ Arduino Uno (2x Servo Barriers)    │
│  DroidCam (MJPEG/QR) │ EZVIZ (RTSP/Plate)                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. INFRASTRUCTURE & DEVOPS

### Docker Compose (`backend-microservices/docker-compose.yml`)

| Service               | Image / Build                  | Port        | Depends On             |
| --------------------- | ------------------------------ | ----------- | ---------------------- |
| mysql                 | mysql:8.0                      | 3307:3306   | —                      |
| redis                 | redis:7-alpine                 | 6379:6379   | —                      |
| rabbitmq              | rabbitmq:3-management          | 5672, 15672 | —                      |
| auth-service          | ./auth-service                 | 8001        | mysql, redis           |
| booking-service       | ./booking-service              | 8002        | mysql, redis, rabbitmq |
| booking-celery-worker | ./booking-service              | —           | mysql, redis, rabbitmq |
| booking-celery-beat   | ./booking-service              | —           | mysql, redis, rabbitmq |
| parking-service       | ./parking-service              | 8003        | mysql                  |
| vehicle-service       | ./vehicle-service              | 8004        | mysql                  |
| notification-service  | ./notification-service-fastapi | 8005        | mysql, rabbitmq        |
| realtime-service      | ./realtime-service-go          | 8006        | redis                  |
| payment-service       | ./payment-service-fastapi      | 8007        | mysql, rabbitmq        |
| chatbot-service       | ./chatbot-service-fastapi      | 8008        | mysql, redis           |
| ai-service            | ./ai-service-fastapi           | 8009        | mysql                  |
| gateway-service       | ./gateway-service-go           | 8000        | redis, all services    |

### Docker Volumes

- `mysql_data` — persistent MySQL data
- `redis_data` — persistent Redis data
- `rabbitmq_data` — persistent RabbitMQ data
- `ai_models` — AI model weights (YOLO, TrOCR)
- `ai_datasets` — training dataset images
- `parksmart_media` — uploaded media files

### Environment Variables (Common)

```env
DB_HOST=mysql / localhost
DB_PORT=3306 / 3307
DB_NAME=parksmartdb
DB_USER=root / parksmartuser
DB_PASSWORD=parksmartpass
REDIS_HOST=redis / localhost
REDIS_PORT=6379
RABBITMQ_HOST=rabbitmq / localhost
GATEWAY_SECRET=gateway-internal-secret-key
```

---

## 4. BACKEND SERVICES — DJANGO REST FRAMEWORK

All Django services share:

- Python 3.11+, Django REST Framework
- MySQL 8.0 database (`parksmartdb`)
- Shared `GatewayAuthMiddleware` from `shared/gateway_middleware.py`
- UUID primary keys
- `pytest-django` for testing

### 4.1 Auth Service (`:8001`)

**Directory**: `backend-microservices/auth-service/`

**Models** (`users/models.py`):
| Model | Fields | Notes |
|-------|--------|-------|
| User | id (UUID), email (unique, USERNAME_FIELD), username, role (user/admin), phone, no_show_count, force_online_payment, is_active, date_joined | Extends AbstractUser |
| OAuthAccount | user (FK), provider (google/facebook), provider_id, email, access_token, refresh_token | Social login |
| PasswordReset | user (FK), token (UUID), is_used, expires_at | Password reset token |

**URL Endpoints** (`users/urls.py`):
| Method | Path | View | Description |
|--------|------|------|-------------|
| POST | /auth/register/ | register | User registration |
| POST | /auth/login/ | login | Email+password login |
| POST | /auth/logout/ | logout | Session logout |
| GET | /auth/me/ | profile | Current user profile |
| PUT/PATCH | /auth/me/ | update_profile | Update profile |
| POST | /auth/change-password/ | change_password | Change password |
| POST | /auth/forgot-password/ | forgot_password | Request reset |
| POST | /auth/reset-password/ | reset_password | Execute reset |
| POST | /auth/google/ | google_login | Google OAuth |
| POST | /auth/facebook/ | facebook_login | Facebook OAuth |
| GET | /auth/admin/dashboard/stats/ | admin_dashboard_stats | Admin overview |
| GET/PUT | /auth/admin/config/ | admin_config | System config |
| GET | /auth/admin/users/ | admin_users_list | List users |
| GET | /auth/admin/users/{id}/ | admin_users_detail | User detail |
| PUT | /auth/admin/users/{id}/ | admin_users_update | Update user |
| DELETE | /auth/admin/users/{id}/ | admin_users_delete | Delete user |

### 4.2 Booking Service (`:8002`)

**Directory**: `backend-microservices/booking-service/`

**Models** (`bookings/models.py`):
| Model | Key Fields | Notes |
|-------|------------|-------|
| PackagePricing | vehicle_type (Car/Motorbike), package_type (hourly/daily/weekly/monthly), price, is_active | Pricing config |
| Booking | id (UUID), user_id (UUID), vehicle_license_plate, vehicle_type, parking_lot_id/name, floor_name, zone_id/name, slot_id/code, package_type, start_time, end_time, total_amount, payment_status (unpaid/paid/refunded), payment_method (cash/online), check_in_status (not_checked_in/checked_in/checked_out/no_show/cancelled), checked_in_at, checked_out_at, hourly_start, hourly_end, extended_until, late_fee_applied, qr_code_data | Denormalized booking |

**URL Endpoints** (`bookings/urls.py`):
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | /bookings/ | List/Create bookings |
| GET/PUT/PATCH/DELETE | /bookings/{id}/ | Booking CRUD |
| GET/POST | /bookings/packagepricings/ | Package pricing CRUD |
| GET | /bookings/current-parking/ | Active check-in bookings |
| GET | /bookings/upcoming/ | Future bookings |
| GET | /bookings/stats/ | Booking statistics |
| POST | /bookings/payment/ | Initiate payment |
| POST | /bookings/payment/verify/ | Verify payment |
| POST | /bookings/check-slot-bookings/ | Check slot availability |
| POST | /bookings/{id}/checkin/ | Check-in action |
| POST | /bookings/{id}/checkout/ | Check-out action |
| POST | /bookings/{id}/cancel/ | Cancel booking |
| GET | /bookings/{id}/qr-code/ | Get QR code image |

**Background Tasks**: Celery worker + beat for:

- Booking expiration (no-show marking)
- Scheduled notifications

### 4.3 Parking Service (`:8003`)

**Directory**: `backend-microservices/parking-service/`

**Models** (`infrastructure/models.py`):
| Model | Key Fields | Notes |
|-------|------------|-------|
| ParkingLot | id (UUID), name, address, latitude, longitude, total_capacity, is_active | Top-level entity |
| Floor | id (UUID), parking_lot (FK), name, level_number | Building floor |
| Zone | id (UUID), floor (FK), name, vehicle_type (Car/Motorbike), capacity, description | Zone within floor |
| CarSlot | id (UUID), zone (FK), code (unique), status (available/occupied/reserved/maintenance), camera (FK to Camera, nullable), x1/y1/x2/y2 (float, bounding box for AI) | Individual slot |
| Camera | id (UUID), name, ip_address, port, zone (FK), stream_url, is_active | RTSP/MJPEG camera |

**URL Endpoints** (`infrastructure/urls.py`):
| Path Pattern | ViewSet | Methods |
|-------------|---------|---------|
| /parking/lots/ | ParkingLotViewSet | CRUD |
| /parking/lots/{id}/ | ParkingLotViewSet | Detail CRUD |
| /parking/floors/ | FloorViewSet | CRUD |
| /parking/zones/ | ZoneViewSet | CRUD |
| /parking/slots/ | CarSlotViewSet | CRUD |
| /parking/cameras/ | CameraViewSet | CRUD |

### 4.4 Vehicle Service (`:8004`)

**Directory**: `backend-microservices/vehicle-service/`

**Models** (`vehicles/models.py`):
| Model | Key Fields | Notes |
|-------|------------|-------|
| Vehicle | id (UUID), user_id (UUID), license_plate (unique), vehicle_type (Car/Motorbike), brand, model, color, is_default | User vehicle registration |

**URL Endpoints** (`vehicles/urls.py`):
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | /vehicles/ | List/Create |
| GET/PUT/PATCH/DELETE | /vehicles/{id}/ | Detail CRUD |
| POST | /vehicles/{id}/set-default/ | Set as default vehicle |

---

## 5. BACKEND SERVICES — FASTAPI

All FastAPI services share:

- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy
- MySQL 8.0 (`parksmartdb`)
- `pytest-asyncio` for testing
- Gateway auth middleware checking `X-Gateway-Secret`

### 5.1 Notification Service (`:8005`)

**Directory**: `backend-microservices/notification-service-fastapi/`

**Endpoints** (prefix: `/notifications`):
| Method | Path | Description |
|--------|------|-------------|
| GET | /notifications/ | List notifications (paginated) |
| GET | /notifications/unread-count/ | Unread notification count |
| POST | /notifications/ | Create notification |
| POST | /notifications/mark-read/ | Mark specific as read |
| POST | /notifications/mark-all-read/ | Mark all as read |
| GET | /notifications/preferences/ | Get notification preferences |
| PUT | /notifications/preferences/ | Update preferences |

### 5.2 Payment Service (`:8007`)

**Directory**: `backend-microservices/payment-service-fastapi/`

**Endpoints** (prefix: `/payments`):
| Method | Path | Description |
|--------|------|-------------|
| POST | /payments/initiate/ | Initiate payment |
| POST | /payments/verify/{id}/ | Verify payment |
| GET | /payments/ | List payments |
| GET | /payments/{id}/ | Get payment detail |
| GET | /payments/booking/{booking_id}/ | Get payments for booking |

### 5.3 Chatbot Service (`:8008`)

**Directory**: `backend-microservices/chatbot-service-fastapi/`

**Database Tables** (created via `init-mysql.sql`, not Django migrations):

- `chatbot_conversation` — conversation sessions with state machine
- `chatbot_chatmessage` — individual messages with intent/confidence/entities
- `chatbot_user_preferences` — learned user preferences (favorite lot/zone/slot)
- `chatbot_user_behavior` — behavioral patterns (typical times, cancel rates)
- `chatbot_user_communication_style` — response personalization
- `chatbot_conversation_summary` — conversation summaries for memory
- `chatbot_proactive_notification` — proactive notifications with suggested actions
- `chatbot_action_log` — undoable action tracking
- `chatbot_ai_metric_log` — AI observability metrics

**Endpoints**:
| Method | Path | Prefix | Description |
|--------|------|--------|-------------|
| POST | /chat/ | /chatbot | Send message + get AI response |
| GET | /quick-actions/ | /chatbot | Available quick actions |
| POST | /feedback/ | /chatbot | Rate AI response |
| GET | /conversations/ | /chatbot/conversations | List conversations |
| POST | /conversations/ | /chatbot/conversations | Create conversation |
| GET | /conversations/active/ | /chatbot/conversations | Get active conversation |
| GET | /conversations/{id}/ | /chatbot/conversations | Get conversation |
| GET | /conversations/{id}/messages/ | /chatbot/conversations | Get messages |
| GET | /conversations/history/latest/ | /chatbot/conversations | Latest history |
| GET | /actions/ | /chatbot/actions | List actions |
| GET | /preferences/ | /chatbot/preferences | Get preferences |
| PUT | /preferences/ | /chatbot/preferences | Update preferences |
| GET | /notifications/ | /chatbot/notifications | List chatbot notifications |
| POST | /notifications/{id}/ | /chatbot/notifications | Action on notification |

### 5.4 AI Service (`:8009`)

**Directory**: `backend-microservices/ai-service-fastapi/`

**Dependencies** (`requirements.txt`):

- FastAPI, Uvicorn, SQLAlchemy, PyMySQL
- OpenCV (headless), NumPy, Pillow
- Ultralytics (YOLO v8), EasyOCR, Transformers (TrOCR), PyTorch
- httpx (inter-service calls)

**Router: Detection** (prefix: `/ai/detect`):
| Method | Path | Description |
|--------|------|-------------|
| POST | /license-plate/ | Detect & OCR license plate from image |
| POST | /cash/ | Detect cash/banknotes from image |
| POST | /banknote/ | Classify individual banknote denomination |

**Router: Parking** (prefix: `/ai/parking`):
| Method | Path | Description |
|--------|------|-------------|
| POST | /scan-plate/ | Scan plate and match to booking |
| POST | /check-in/ | Full check-in flow (QR + plate + booking validation) |
| POST | /check-out/ | Full check-out flow (plate + fee calculation + booking update) |

**Router: ESP32** (prefix: `/ai/esp32`):
| Method | Path | Description |
|--------|------|-------------|
| POST | /check-in/ | ESP32-triggered check-in (QR scan → plate scan → validate → open barrier) |
| POST | /check-out/ | ESP32-triggered check-out |
| POST | /verify-slot/ | Verify vehicle is in correct slot via camera |
| POST | /cash-payment/ | Cash payment session with banknote detection |
| GET | /status/ | ESP32 device status |

**Router: Training** (prefix: `/ai/training`):
| Method | Path | Description |
|--------|------|-------------|
| POST | /cash/ | Upload cash training images |
| POST | /banknote/ | Upload banknote training images |

**Router: Metrics** (prefix: `/ai`):
| Method | Path | Description |
|--------|------|-------------|
| GET | /metrics/ | AI model performance metrics |
| GET | /predictions/ | Prediction log history |
| GET | /versions/ | Model version tracking |

**Router: Camera** (prefix: `/ai/cameras`):
| Method | Path | Description |
|--------|------|-------------|
| GET | /list | List available cameras |
| GET | /snapshot | Capture single frame from camera |
| GET | /stream | MJPEG video stream from camera |

---

## 6. BACKEND SERVICES — GO (GIN)

### 6.1 Gateway Service (`:8000`)

**Directory**: `backend-microservices/gateway-service-go/`

**Architecture**: Single reverse proxy that:

1. Accepts all HTTP requests
2. Checks session cookie in Redis for authentication
3. Injects `X-User-ID`, `X-User-Email`, `X-Gateway-Secret` headers
4. Routes to appropriate microservice

**Config** (`internal/config/config.go`):

```go
type Config struct {
    Port             string  // :8000
    RedisAddr        string  // redis:6379
    AuthServiceURL   string  // http://auth-service:8001
    ParkingServiceURL string // http://parking-service:8003
    VehicleServiceURL string // http://vehicle-service:8004
    BookingServiceURL string // http://booking-service:8002
    NotificationServiceURL string // http://notification-service-fastapi:8005
    RealtimeServiceURL string    // http://realtime-service-go:8006
    PaymentServiceURL  string    // http://payment-service-fastapi:8007
    ChatbotServiceURL  string    // http://chatbot-service-fastapi:8008
    AIServiceURL       string    // http://ai-service-fastapi:8009
    GatewaySecret      string   // gateway-internal-secret-key
    SessionSecret      string
}
```

**Route Mapping** (`internal/router/routes.go`):
| URL Prefix | Target Service | Auth Required |
|------------|---------------|---------------|
| /auth/ | auth-service:8001 | NO (public) |
| /parking/ | parking-service:8003 | YES |
| /vehicles/ | vehicle-service:8004 | YES |
| /bookings/ | booking-service:8002 | YES |
| /incidents/ | booking-service:8002 | YES |
| /notifications/ | notification-service:8005 | YES |
| /realtime/ | realtime-service:8006 | YES |
| /payments/ | payment-service:8007 | YES |
| /ai/ | ai-service:8009 | YES |
| /chatbot/ | chatbot-service:8008 | YES |

**Special Cases**:

- `/health` — bypasses auth, returns gateway health
- `/*service*/health/` — bypasses auth, proxies to service
- `/auth/login/` and `/auth/register/` — sets session cookie on success
- `/auth/logout/` — destroys session

### 6.2 Realtime Service (`:8006`)

**Directory**: `backend-microservices/realtime-service-go/`

**WebSocket Hub Pattern**:

- Central `Hub` struct with `clients`, `broadcast`, `register`, `unregister` channels
- Each `Client` subscribes to topic channels
- Read/write goroutine pumps per connection

**Endpoints**:
| Path | Auth | Topics | Description |
|------|------|--------|-------------|
| /ws/parking | NO | `parking_updates` | Public parking lot occupancy updates |
| /ws/user?userId=X | YES | `user_{userId}`, `parking_updates` | User-specific notifications + parking updates |

---

## 7. SHARED LIBRARIES

### Gateway Middleware (`shared/gateway_middleware.py`)

Used by all Django services. Validates incoming requests:

```python
class GatewayAuthMiddleware:
    # Validates X-Gateway-Secret header
    # Extracts X-User-ID, X-User-Email from gateway headers
    # Sets request.user_id, request.user_email

    PUBLIC_PATHS = ['/auth/login/', '/auth/register/', ...]
    EXEMPT_PATHS = ['/health/', '/_test/', '/admin/']
```

---

## 8. FRONTEND — REACT + VITE + TYPESCRIPT

### Tech Stack

| Technology             | Version | Purpose                        |
| ---------------------- | ------- | ------------------------------ |
| React                  | 18.3    | UI framework                   |
| Vite                   | 5.4     | Build tool, dev server (:8080) |
| TypeScript             | 5.8     | Type safety                    |
| React Router           | 6.30    | Client-side routing            |
| Redux Toolkit          | 2.11    | Global state management        |
| React Query (TanStack) | 5.83    | Server state management        |
| shadcn/ui + Radix      | Latest  | UI component library           |
| Tailwind CSS           | 3.4     | Utility-first styling          |
| Recharts               | 2.15    | Chart/graph components         |
| Zod                    | 3.25    | Schema validation              |
| React Hook Form        | 7.61    | Form management                |
| Axios                  | 1.13    | HTTP client                    |
| Playwright             | 1.58    | E2E testing                    |
| Vitest                 | 3.2     | Unit testing                   |
| lucide-react           | 0.462   | Icon library                   |
| qrcode.react           | 4.2     | QR code generation             |

### Directory Structure

```
spotlove-ai/
├── e2e/                    # Playwright E2E tests
│   ├── .auth/              # Stored auth states (user.json, admin.json)
│   ├── admin.pages.spec.ts
│   ├── api-endpoints.spec.ts
│   ├── booking.spec.ts
│   ├── dashboard.spec.ts
│   ├── history.spec.ts
│   ├── public-pages.spec.ts
│   └── user-pages.spec.ts
├── src/
│   ├── App.tsx             # Route definitions
│   ├── main.tsx            # Entry point
│   ├── components/         # Reusable UI components
│   │   ├── dashboard/      # StatsCard, SlotOverview, RecentBookings, QuickBooking
│   │   ├── ui/             # shadcn/ui primitives
│   │   └── ...
│   ├── pages/              # Route page components
│   │   ├── AdminDashboard.tsx
│   │   ├── UserDashboard.tsx
│   │   ├── BookingPage.tsx
│   │   ├── CamerasPage.tsx
│   │   ├── MapPage.tsx
│   │   ├── HistoryPage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── KioskPage.tsx
│   │   └── ...
│   ├── services/
│   │   ├── api/            # Pure HTTP layer (snake_case responses)
│   │   │   ├── auth.api.ts
│   │   │   ├── booking.api.ts
│   │   │   ├── parking.api.ts
│   │   │   ├── vehicle.api.ts
│   │   │   ├── notification.api.ts
│   │   │   ├── incident.api.ts
│   │   │   ├── admin.api.ts
│   │   │   ├── chatbot.api.ts
│   │   │   └── ai.api.ts
│   │   ├── business/       # Business logic layer (camelCase, Redux+WS)
│   │   └── index.ts        # Service barrel exports
│   ├── store/              # Redux store configuration
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utility functions
│   └── types/              # TypeScript type definitions
├── playwright.config.ts
├── vite.config.ts
├── vitest.config.ts
└── package.json
```

### Route Map (`App.tsx`)

**Public Routes** (no auth):
| Path | Component | Description |
|------|-----------|-------------|
| /login | LoginPage | User login |
| /register | RegisterPage | User registration |
| /kiosk | KioskPage | Public check-in kiosk |

**Protected User Routes** (requires auth):
| Path | Component | Description |
|------|-----------|-------------|
| / | Index (→ Dashboard) | Redirects based on role |
| /booking | BookingPage | Create/manage bookings |
| /history | HistoryPage | Booking history |
| /cameras | CamerasPage | Live camera feeds |
| /map | MapPage | Parking lot map |
| /support | SupportPage | Help/chatbot |
| /settings | SettingsPage | User settings |
| /payment | PaymentPage | Payment flow |
| /panic | PanicPage | Emergency alert |
| /banknote-detection | BanknoteDetectionPage | Cash detection UI |
| /check-in-out | CheckInOutPage | Manual check-in/out |

**Admin Routes** (requires admin role):
| Path | Component | Description |
|------|-----------|-------------|
| /admin/dashboard | AdminDashboard | Admin overview |
| /admin/users | AdminUsersPage | User management |
| /admin/zones | AdminZonesPage | Zone management |
| /admin/slots | AdminSlotsPage | Slot management |
| /admin/cameras | AdminCamerasPage | Camera management |
| /admin/config | AdminConfigPage | System configuration |
| /admin/violations | AdminViolationsPage | Violation management |
| /admin/esp32 | AdminESP32Page | ESP32 hardware management |
| /admin/revenue | AdminRevenuePage | Revenue analytics |

### Vite Proxy Configuration (`vite.config.ts`)

```typescript
server: {
  port: 8080,
  proxy: {
    '/api': { target: 'http://localhost:8000', rewrite: path => path.replace(/^\/api/, '') },
    '/ai-camera': { target: 'http://localhost:8009', rewrite: path => path.replace(/^\/ai-camera/, '') },
  }
}
```

### Services Architecture

**Two-layer design**:

1. **API Layer** (`services/api/`): Pure HTTP calls via Axios. Returns raw snake_case data from backend. No state mutations.
2. **Business Layer** (`services/business/`): Redux dispatches, WebSocket connections, data transformations to camelCase. Orchestrates API calls.

---

## 9. AI/ML ENGINE

### Directory: `ai-service-fastapi/app/engine/`

| Module                | Class/Function                | Purpose                                                                |
| --------------------- | ----------------------------- | ---------------------------------------------------------------------- |
| `plate_detector.py`   | `LicensePlateDetector`        | YOLO v8 model for detecting plate bounding boxes                       |
| `plate_ocr.py`        | Multi-engine OCR              | TrOCR (primary) + EasyOCR (fallback) + Tesseract (fallback)            |
| `plate_pipeline.py`   | `PlatePipeline`               | Orchestrates: detect plate → crop → OCR → clean text                   |
| `detector.py`         | `BanknoteDetector`            | YOLO v8 model for banknote detection                                   |
| `ai_classifier.py`    | `BanknoteAIClassifier`        | Neural network banknote denomination classifier                        |
| `color_classifier.py` | Color histogram               | HSV histogram-based banknote color classification                      |
| `pipeline.py`         | `BanknoteRecognitionPipeline` | Full: detect → classify → aggregate total amount                       |
| `camera_capture.py`   | `CameraCapture`               | RTSP/MJPEG frame capture with OpenCV (TCP transport)                   |
| `camera_monitor.py`   | Background monitoring         | Continuous slot occupancy detection via camera feeds                   |
| `cash_session.py`     | `CashPaymentSession/Manager`  | State machine for cash payment flow (insert → detect → total → change) |
| `qr_reader.py`        | QR decoder                    | Reads QR codes from camera frames                                      |

### AI Models

| Model                  | Framework                | Purpose                 | Location                                   |
| ---------------------- | ------------------------ | ----------------------- | ------------------------------------------ |
| License Plate Detector | YOLO v8 (fine-tuned)     | Detect plate regions    | `app/models/license-plate-finetune-v1m.pt` |
| Banknote Detector      | YOLO v8                  | Detect banknote regions | Loaded at startup                          |
| Banknote Classifier    | Custom CNN               | Classify denominations  | Loaded at startup                          |
| TrOCR                  | HuggingFace Transformers | Plate text recognition  | Downloaded at first run                    |
| EasyOCR                | EasyOCR                  | Fallback plate OCR      | Downloaded at first run                    |

### Vietnamese Banknote Denominations

Dataset organized in 54 folders for training:

- **Denominations**: 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000 VND
- **Types**: polymer, cotton (where applicable)
- **Sides**: front, back
- Format: `{denomination}_{type}_{side}/` (e.g., `500000_polymer_front/`)

### ESP32 Check-In Flow (Detailed)

```
1. ESP32 button press (GPIO4) → POST /ai/esp32/check-in/
2. AI Service:
   a. Start QR scan timeout (30s) via DroidCam
   b. Decode QR → extract booking_id
   c. GET /bookings/{id}/ from booking-service → validate status
   d. Capture frame from EZVIZ RTSP camera
   e. Run plate_pipeline: YOLO detect → crop → TrOCR OCR
   f. Compare detected plate with booking.vehicle_license_plate
   g. If match: POST /bookings/{id}/checkin/ → update booking
   h. Return success with barrier_action: "OPEN"
3. ESP32 sends UART "OPEN_1" → Arduino opens entry servo
4. After 5s delay: UART "CLOSE_1" → Arduino closes entry servo
```

### ESP32 Check-Out Flow

```
1. ESP32 button press (GPIO5) → POST /ai/esp32/check-out/
2. AI Service:
   a. Capture frame from EZVIZ RTSP camera
   b. Run plate_pipeline → detect license plate
   c. Find active booking by plate (check_in_status=checked_in)
   d. Calculate fees (including hourly overstay if applicable)
   e. If payment_method=cash → start cash session
   f. If payment_method=online → check payment_status
   g. POST /bookings/{id}/checkout/ → update booking
   h. Return barrier_action: "OPEN"
3. ESP32 sends UART "OPEN_2" → Arduino opens exit servo
```

---

## 10. HARDWARE INTEGRATION

### ESP32 (`hardware/esp32/esp32_gate_controller/`)

| Component     | Details                                                 |
| ------------- | ------------------------------------------------------- |
| MCU           | ESP32                                                   |
| Display       | SSD1306 OLED (128x64, I2C 0x3C)                         |
| Buttons       | GPIO4 (CHECK-IN), GPIO5 (CHECK-OUT)                     |
| LED           | GPIO2 (status indicator)                                |
| Communication | WiFi (HTTP to AI service), UART (to Arduino, 9600 baud) |
| WiFi SSID     | `FPT Telecom-755C-IOT`                                  |
| AI Server     | `http://192.168.100.x:8009`                             |
| HTTP Timeout  | 30 seconds                                              |

**Button Actions**:

- GPIO4 (CHECK-IN): `POST http://{AI_SERVER}/ai/esp32/check-in/`
- GPIO5 (CHECK-OUT): `POST http://{AI_SERVER}/ai/esp32/check-out/`

**OLED Display States**: IDLE → PROCESSING → SUCCESS/FAIL

### Arduino Uno (`hardware/arduino/barrier_control/`)

| Component     | Details                                      |
| ------------- | -------------------------------------------- |
| MCU           | Arduino Uno                                  |
| Servos        | Pin 10 (entry barrier), Pin 9 (exit barrier) |
| Communication | UART from ESP32 (9600 baud)                  |

**UART Commands**:
| Command | Action |
|---------|--------|
| `OPEN_1` | Open entry barrier (servo to 90°) |
| `CLOSE_1` | Close entry barrier (servo to 0°) |
| `OPEN_2` | Open exit barrier (servo to 90°) |
| `CLOSE_2` | Close exit barrier (servo to 0°) |

### Camera Setup

| Camera    | Type            | Purpose                   | URL                                               |
| --------- | --------------- | ------------------------- | ------------------------------------------------- |
| DroidCam  | MJPEG over HTTP | QR code scanning          | `http://192.168.x.x:4747/video`                   |
| EZVIZ C6N | RTSP (TCP)      | License plate recognition | `rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main` |

---

## 11. AUTHENTICATION & AUTHORIZATION FLOW

```
[Browser] → Cookie (session_id)
    │
    ▼
[Gateway :8000]
    │ 1. Read session_id from cookie
    │ 2. Lookup in Redis → get user_id, email, role
    │ 3. If not found → 401 (except public paths)
    │
    ▼ Inject headers:
    │ X-User-ID: <uuid>
    │ X-User-Email: <email>
    │ X-Gateway-Secret: gateway-internal-secret-key
    │
    ▼
[Microservice]
    │ 1. Validate X-Gateway-Secret
    │ 2. Extract X-User-ID, X-User-Email
    │ 3. Process request with user context
```

**Public Paths** (no auth required):

- `/auth/login/`, `/auth/register/`, `/auth/google/`, `/auth/facebook/`
- `/health/` endpoints on all services
- `/ws/parking` (public WebSocket)
- `/ai/cameras/` (browser img tag access)

**Admin Paths**: Gateway checks role from session. Admin routes in frontend also check role client-side.

---

## 12. INTER-SERVICE COMMUNICATION

### Synchronous (HTTP)

| From            | To                               | Purpose                                      |
| --------------- | -------------------------------- | -------------------------------------------- |
| AI Service      | Booking Service (:8002)          | Validate/update bookings during check-in/out |
| AI Service      | Parking Service (:8003)          | Get camera/slot info                         |
| AI Service      | Realtime Service (:8006)         | Push slot status updates                     |
| Chatbot Service | Booking/Parking/Vehicle Services | Execute user actions (book, cancel, check)   |
| Payment Service | Booking Service                  | Update payment status                        |

### Asynchronous (RabbitMQ)

| Event               | Publisher                | Consumer(s)                   |
| ------------------- | ------------------------ | ----------------------------- |
| booking.created     | Booking Service          | Notification Service          |
| booking.cancelled   | Booking Service          | Notification Service          |
| payment.completed   | Payment Service          | Booking Service, Notification |
| booking.checked_in  | AI Service (via Booking) | Realtime, Notification        |
| booking.checked_out | AI Service (via Booking) | Realtime, Notification        |

### WebSocket (Realtime)

| Channel           | Data                                    | Subscribers           |
| ----------------- | --------------------------------------- | --------------------- |
| `parking_updates` | Slot status changes, occupancy          | All connected clients |
| `user_{userId}`   | Personal notifications, booking updates | Specific user         |

---

## 13. DATABASE SCHEMA SUMMARY

**Single MySQL database**: `parksmartdb` (port 3307)

All services share the same database but use different tables:

| Service      | Tables                                                              | Migration         |
| ------------ | ------------------------------------------------------------------- | ----------------- |
| Auth         | `users_user`, `users_oauthaccount`, `users_passwordreset`           | Django migrations |
| Booking      | `booking`, `package_pricing`                                        | Django migrations |
| Parking      | `parking_lot`, `floor`, `zone`, `car_slot`, `infrastructure_camera` | Django migrations |
| Vehicle      | `vehicle`                                                           | Django migrations |
| Notification | FastAPI/SQLAlchemy tables                                           | Alembic           |
| Payment      | FastAPI/SQLAlchemy tables                                           | Alembic           |
| Chatbot      | 8 tables (see §5.3)                                                 | `init-mysql.sql`  |
| AI           | Metrics/prediction tables                                           | Alembic           |

---

## 14. API ENDPOINT REFERENCE (COMPLETE)

### Via Gateway (`:8000`)

All paths below are relative to `http://localhost:8000/`

#### Auth Service

```
POST   /auth/register/
POST   /auth/login/
POST   /auth/logout/
GET    /auth/me/
PUT    /auth/me/
POST   /auth/change-password/
POST   /auth/forgot-password/
POST   /auth/reset-password/
POST   /auth/google/
POST   /auth/facebook/
GET    /auth/admin/dashboard/stats/
GET    /auth/admin/config/
PUT    /auth/admin/config/
GET    /auth/admin/users/
GET    /auth/admin/users/{id}/
PUT    /auth/admin/users/{id}/
DELETE /auth/admin/users/{id}/
```

#### Booking Service

```
GET    /bookings/
POST   /bookings/
GET    /bookings/{id}/
PUT    /bookings/{id}/
PATCH  /bookings/{id}/
DELETE /bookings/{id}/
GET    /bookings/packagepricings/
POST   /bookings/packagepricings/
GET    /bookings/current-parking/
GET    /bookings/upcoming/
GET    /bookings/stats/
POST   /bookings/payment/
POST   /bookings/payment/verify/
POST   /bookings/check-slot-bookings/
POST   /bookings/{id}/checkin/
POST   /bookings/{id}/checkout/
POST   /bookings/{id}/cancel/
GET    /bookings/{id}/qr-code/
```

#### Parking Service

```
GET    /parking/lots/
POST   /parking/lots/
GET    /parking/lots/{id}/
PUT    /parking/lots/{id}/
PATCH  /parking/lots/{id}/
DELETE /parking/lots/{id}/
GET    /parking/floors/
POST   /parking/floors/
GET    /parking/floors/{id}/
PUT    /parking/floors/{id}/
GET    /parking/zones/
POST   /parking/zones/
GET    /parking/zones/{id}/
PUT    /parking/zones/{id}/
GET    /parking/slots/
POST   /parking/slots/
GET    /parking/slots/{id}/
PUT    /parking/slots/{id}/
GET    /parking/cameras/
POST   /parking/cameras/
GET    /parking/cameras/{id}/
PUT    /parking/cameras/{id}/
```

#### Vehicle Service

```
GET    /vehicles/
POST   /vehicles/
GET    /vehicles/{id}/
PUT    /vehicles/{id}/
PATCH  /vehicles/{id}/
DELETE /vehicles/{id}/
POST   /vehicles/{id}/set-default/
```

#### Notification Service

```
GET    /notifications/
POST   /notifications/
GET    /notifications/unread-count/
POST   /notifications/mark-read/
POST   /notifications/mark-all-read/
GET    /notifications/preferences/
PUT    /notifications/preferences/
```

#### Payment Service

```
POST   /payments/initiate/
POST   /payments/verify/{id}/
GET    /payments/
GET    /payments/{id}/
GET    /payments/booking/{booking_id}/
```

#### AI Service

```
POST   /ai/detect/license-plate/
POST   /ai/detect/cash/
POST   /ai/detect/banknote/
POST   /ai/parking/scan-plate/
POST   /ai/parking/check-in/
POST   /ai/parking/check-out/
POST   /ai/esp32/check-in/
POST   /ai/esp32/check-out/
POST   /ai/esp32/verify-slot/
POST   /ai/esp32/cash-payment/
GET    /ai/esp32/status/
POST   /ai/training/cash/
POST   /ai/training/banknote/
GET    /ai/metrics/
GET    /ai/predictions/
GET    /ai/versions/
GET    /ai/cameras/list
GET    /ai/cameras/snapshot
GET    /ai/cameras/stream
```

#### Chatbot Service

```
POST   /chatbot/chat/
GET    /chatbot/quick-actions/
POST   /chatbot/feedback/
GET    /chatbot/conversations/
POST   /chatbot/conversations/
GET    /chatbot/conversations/active/
GET    /chatbot/conversations/{id}/
GET    /chatbot/conversations/{id}/messages/
GET    /chatbot/conversations/history/latest/
GET    /chatbot/actions/
GET    /chatbot/preferences/
PUT    /chatbot/preferences/
GET    /chatbot/notifications/
POST   /chatbot/notifications/{id}/
```

#### Realtime Service (WebSocket)

```
WS     /realtime/ws/parking
WS     /realtime/ws/user?userId={uuid}
```

---

## 15. TESTING STRATEGY

### Current Test Inventory

| Service              | Framework      | Test Files                     | Coverage               |
| -------------------- | -------------- | ------------------------------ | ---------------------- |
| auth-service         | pytest-django  | test_health.py                 | Low — health only      |
| booking-service      | pytest-django  | test_health.py                 | Low — health only      |
| parking-service      | pytest-django  | test_health.py                 | Low — health only      |
| vehicle-service      | pytest-django  | test_health.py                 | Low — health only      |
| notification-service | pytest-asyncio | test_smoke.py                  | Low — smoke only       |
| payment-service      | pytest-asyncio | test_smoke.py                  | Low — smoke only       |
| ai-service           | pytest-asyncio | 7 test files                   | Medium — unit + API    |
| chatbot-service      | pytest-asyncio | 8 test files                   | Medium — comprehensive |
| gateway-service      | Go testing     | config_test.go, health_test.go | Low — config + health  |
| realtime-service     | Go testing     | None                           | None                   |
| Frontend E2E         | Playwright     | 7 spec files (65 tests)        | Good — all user flows  |
| Frontend Unit        | Vitest         | None                           | None                   |

### Recommended Test Coverage Goals

1. **Django Services**: Model validation, ViewSet CRUD, permission checks, serializer tests
2. **FastAPI Services**: Router endpoint tests, request/response validation, error handling
3. **Go Services**: Middleware tests, proxy routing, WebSocket hub, session management
4. **Frontend E2E**: Expanded admin flows, edge cases, error states
5. **Frontend Unit**: Component rendering, hook behavior, service layer mocking
6. **Integration**: Cross-service booking flow, check-in/out E2E with mocked AI

---

## 16. GAPS, REDUNDANCIES & IMPROVEMENT AREAS

### Critical Gaps ⚠️

1. **No Rate Limiting per User**: Gateway has global rate limit but no per-user throttling
2. **No API Versioning**: All endpoints are unversioned; breaking changes will affect all clients
3. **No Request Validation on Gateway**: Payload validation only happens at service level
4. **No Circuit Breaker**: If a downstream service is down, gateway will hang until timeout
5. **Missing Swagger/OpenAPI Aggregation**: Each FastAPI service has its own docs, no unified API docs
6. **No Monitoring/Alerting**: No Prometheus metrics, no Grafana dashboards, no health check alerting
7. **Single Database**: All services share `parksmartdb` — no database-per-service isolation
8. **No Database Migrations for Chatbot**: Tables created via raw SQL, not through migration tool
9. **No Automated Backup**: No MySQL backup strategy defined
10. **Hardcoded Camera IPs**: Camera URLs are hardcoded in frontend constants and ESP32 firmware

### Redundancies 🔄

1. **Dual Check-In Endpoints**: `/ai/parking/check-in/` AND `/ai/esp32/check-in/` — overlap in logic
2. **Booking Denormalization**: Booking model copies vehicle_license_plate, parking_lot_name, etc. — could lead to stale data
3. **QuickBooking Component**: Static form with no API integration (placeholder code)
4. **Multiple OCR Engines**: TrOCR + EasyOCR + Tesseract — could simplify to best-performing one
5. **Gateway auth middleware exists in both**: `shared/gateway_middleware.py` (Django) + `ai-service-fastapi/app/middleware/gateway_auth.py` (FastAPI separate implementation)

### Improvement Suggestions 📈

1. **Add Health Check Aggregator**: Gateway should aggregate health from all services
2. **Implement Event Sourcing**: Replace direct HTTP calls with event-driven patterns via RabbitMQ
3. **Add Caching Layer**: Redis caching for parking lot data, package pricing (frequently read, rarely written)
4. **Implement CQRS**: Separate read/write models for booking queries vs. commands
5. **Add Retry/Backoff**: Implement exponential backoff for inter-service HTTP calls
6. **Structured Logging**: Unified logging format with correlation IDs across services
7. **Database Per Service**: Migrate to separate databases (or at minimum separate schemas)
8. **Add OpenTelemetry**: Distributed tracing across the microservice mesh
9. **Secret Management**: Move credentials to vault (currently in env vars and docker-compose)
10. **Add WebSocket Authentication**: `/ws/parking` is currently unauthenticated
11. **Frontend State Normalization**: Use RTK Query instead of manual React Query + Redux mix
12. **Implement Graceful Shutdown**: All services should handle SIGTERM properly
13. **Add Input Sanitization**: SQL injection protection at gateway level
14. **Mobile-Responsive Admin**: Admin dashboard needs responsive design improvements
15. **Add Pagination to All Lists**: Some list endpoints don't support pagination

---

## 17. CODING CONVENTIONS

### Python (Django REST Framework)

```python
# Models: UUID PK, snake_case fields
class MyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# URLs: path with ViewSet.as_view() mapping
path('items/', MyViewSet.as_view({'get': 'list', 'post': 'create'}))

# Tests: pytest-django, no classes needed
def test_my_feature(client, db):
    response = client.get('/api/items/')
    assert response.status_code == 200
```

### Python (FastAPI)

```python
# Router with prefix and tags
router = APIRouter(prefix="/myservice", tags=["myservice"])

@router.get("/items/", response_model=list[ItemResponse])
async def list_items(db: Session = Depends(get_db)):
    ...

# Pydantic v2 schemas
class ItemResponse(BaseModel):
    id: str
    name: str
    model_config = ConfigDict(from_attributes=True)

# Tests: pytest-asyncio + httpx
@pytest.mark.asyncio
async def test_list_items(async_client):
    response = await async_client.get("/myservice/items/")
    assert response.status_code == 200
```

### Go (Gin)

```go
// Router setup
func SetupRouter(cfg *config.Config) *gin.Engine {
    r := gin.Default()
    r.GET("/health", healthHandler)
    r.Any("/*path", proxyHandler)
    return r
}

// Tests: standard testing package
func TestMyFunction(t *testing.T) {
    result := MyFunction(input)
    if result != expected {
        t.Errorf("expected %v, got %v", expected, result)
    }
}
```

### TypeScript (React)

```typescript
// Service API layer (snake_case from backend)
export const myApi = {
  getItems: () => api.get<{ results: Item[] }>('/items/'),
  createItem: (data: CreateItemDTO) => api.post('/items/', data),
};

// Component (functional, hooks)
const MyComponent: React.FC = () => {
  const { data } = useQuery({ queryKey: ['items'], queryFn: myApi.getItems });
  return <div>{/* JSX */}</div>;
};

// Playwright E2E
test('should display items', async ({ page }) => {
  await page.goto('/items');
  await expect(page.getByText('Item 1')).toBeVisible();
});
```

---

## 18. QUICK REFERENCE: PORTS & CREDENTIALS

### Service Ports

| Service              | Port                    | Framework   |
| -------------------- | ----------------------- | ----------- |
| Frontend (Vite)      | 8080                    | React+Vite  |
| Gateway              | 8000                    | Go Gin      |
| Auth Service         | 8001                    | Django REST |
| Booking Service      | 8002                    | Django REST |
| Parking Service      | 8003                    | Django REST |
| Vehicle Service      | 8004                    | Django REST |
| Notification Service | 8005                    | FastAPI     |
| Realtime Service     | 8006                    | Go Gin      |
| Payment Service      | 8007                    | FastAPI     |
| Chatbot Service      | 8008                    | FastAPI     |
| AI Service           | 8009                    | FastAPI     |
| MySQL                | 3307                    | MySQL 8.0   |
| Redis                | 6379                    | Redis 7     |
| RabbitMQ             | 5672 (AMQP), 15672 (UI) | RabbitMQ 3  |

### Credentials

| What           | Value                                           |
| -------------- | ----------------------------------------------- |
| Admin Account  | admin@parksmart.com / admin123                  |
| MySQL Root     | root / parksmartpass                            |
| MySQL User     | parksmartuser / parksmartpass                   |
| MySQL DB       | parksmartdb                                     |
| Gateway Secret | gateway-internal-secret-key                     |
| RabbitMQ       | guest / guest                                   |
| EZVIZ Camera   | rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main |
| WiFi (IoT)     | FPT Telecom-755C-IOT / 2462576d                 |

### Key File Paths

| Purpose           | Path                                                               |
| ----------------- | ------------------------------------------------------------------ |
| Docker Compose    | backend-microservices/docker-compose.yml                           |
| DB Init SQL       | backend-microservices/init-mysql.sql                               |
| Gateway Routes    | backend-microservices/gateway-service-go/internal/router/routes.go |
| Gateway Config    | backend-microservices/gateway-service-go/internal/config/config.go |
| Shared Middleware | backend-microservices/shared/gateway_middleware.py                 |
| AI Engine         | backend-microservices/ai-service-fastapi/app/engine/               |
| AI ESP32 Router   | backend-microservices/ai-service-fastapi/app/routers/esp32.py      |
| Frontend App      | spotlove-ai/src/App.tsx                                            |
| Frontend Services | spotlove-ai/src/services/                                          |
| Playwright Config | spotlove-ai/playwright.config.ts                                   |
| Vite Config       | spotlove-ai/vite.config.ts                                         |
| ESP32 Firmware    | hardware/esp32/esp32_gate_controller/                              |
| Arduino Firmware  | hardware/arduino/barrier_control/                                  |

---

## APPENDIX A: DOCKER COMPOSE QUICK START

```bash
# Start all services
cd backend-microservices
docker compose up -d

# Start only infrastructure
docker compose up -d mysql redis rabbitmq

# Run Django migrations (each service)
docker compose exec auth-service python manage.py migrate
docker compose exec booking-service python manage.py migrate
docker compose exec parking-service python manage.py migrate
docker compose exec vehicle-service python manage.py migrate

# Create admin user
docker compose exec auth-service python manage.py createsuperuser

# Start frontend
cd ../spotlove-ai
npm install
npm run dev
```

## APPENDIX B: LOCAL DEVELOPMENT (Without Docker)

```bash
# Prerequisites: MySQL on port 3307, Redis on 6379, RabbitMQ on 5672

# Auth Service
cd backend-microservices/auth-service
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8001

# AI Service
cd backend-microservices/ai-service-fastapi
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8009 --reload

# Gateway
cd backend-microservices/gateway-service-go
go run cmd/main.go

# Frontend
cd spotlove-ai
npm install
npm run dev
```

## APPENDIX C: RUNNING TESTS

```bash
# Django tests (each service)
cd backend-microservices/auth-service && pytest
cd backend-microservices/booking-service && pytest
cd backend-microservices/parking-service && pytest
cd backend-microservices/vehicle-service && pytest

# FastAPI tests
cd backend-microservices/ai-service-fastapi && pytest
cd backend-microservices/notification-service-fastapi && pytest
cd backend-microservices/payment-service-fastapi && pytest
cd backend-microservices/chatbot-service-fastapi && pytest

# Go tests
cd backend-microservices/gateway-service-go && go test ./...
cd backend-microservices/realtime-service-go && go test ./...

# Frontend E2E (Playwright)
cd spotlove-ai && npx playwright test

# Frontend Unit (Vitest)
cd spotlove-ai && npm run test
```

---

> **END OF SYSTEM PROMPT**  
> This document should be provided to any AI coding assistant to give it full context of the ParkSmart project.
