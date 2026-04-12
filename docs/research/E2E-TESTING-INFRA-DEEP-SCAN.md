# Research Report: Deep Scan — Infrastructure, API, Unity State for E2E Testing

**Task:** E2E Testing Preparation | **Date:** 2026-04-09 | **Type:** Mixed (Codebase + Infrastructure)

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **13 Docker services** trên 1 mạng bridge, gateway port 8000, tất cả route qua `/api/{service}/`
> 2. **Cloudflare tunnel** đã config cho `app/api/ws.ghepdoicaulong.shop`, tunnel ID `57eb6de9-...`, command: `cloudflared tunnel --config infra/cloudflare/cloudflared/config.yml run`
> 3. **Full booking flow** đã có seed script (`seed_e2e_data.py`) với test accounts `e2e_playwright@parksmart.com / TestPass123!` và `admin@parksmart.com / admin1234@`
> 4. **AI service** có 3 route groups: `/ai/parking/esp32/*` (ESP32 gate), `/ai/parking/*` (HTTP check-in/out), `/ai/cameras/*` (virtual camera streaming)
> 5. **Unity** đã có full integration: `ApiConfig.cs` (ScriptableObject), `ESP32Simulator`, `GateCameraSimulator`, `VirtualCameraStreamer` — tất cả hoạt động qua gateway hoặc direct AI service

---

## 2. Docker Services & Ports

### 2.1 Complete Service Map

| #   | Service                          | Container Name               | Host Port                  | Internal Port | Health Check                                              |
| --- | -------------------------------- | ---------------------------- | -------------------------- | ------------- | --------------------------------------------------------- |
| 1   | MySQL 8.0                        | parksmartdb_mysql            | **3307**                   | 3306          | `mysqladmin ping`                                         |
| 2   | Redis 7                          | parksmartdb_redis            | **6379**                   | 6379          | `redis-cli ping`                                          |
| 3   | RabbitMQ 3                       | parksmartdb_rabbitmq         | **5672**, **15672** (mgmt) | 5672, 15672   | `rabbitmq-diagnostics ping`                               |
| 4   | Auth Service (Django)            | auth-service                 | **8001**                   | 8000          | —                                                         |
| 5   | Booking Service (Django)         | booking-service              | **8002**                   | 8000          | —                                                         |
| 6   | Parking Service (Django)         | parking-service              | **8003**                   | 8000          | —                                                         |
| 7   | Vehicle Service (Django)         | vehicle-service              | — (expose only)            | 8000          | —                                                         |
| 8   | Notification Service (FastAPI)   | notification-service-fastapi | — (expose only)            | 8005          | —                                                         |
| 9   | Realtime Service (Go, WebSocket) | realtime-service-go          | **8006**                   | 8006          | —                                                         |
| 10  | Payment Service (FastAPI)        | payment-service-fastapi      | — (expose only)            | 8007          | —                                                         |
| 11  | AI Service (FastAPI)             | ai-service-fastapi           | — (expose only)            | 8009          | `urllib.request.urlopen('http://localhost:8009/health/')` |
| 12  | Chatbot Service (FastAPI)        | chatbot-service-fastapi      | — (expose only)            | 8008          | —                                                         |
| 13  | **Gateway Service (Go)**         | gateway-service-go           | **8000**                   | 8000          | —                                                         |
| 14  | Booking Celery Worker            | booking-celery-worker        | —                          | —             | disabled                                                  |
| 15  | Booking Celery Beat              | booking-celery-beat          | —                          | —             | disabled                                                  |

**Production overlay** adds:
| 16 | Nginx | parksmart_nginx | **80** | 80 | `wget --spider http://127.0.0.1/nginx-health` |

### 2.2 Health Check Commands (local testing)

```bash
# All services through gateway
curl http://localhost:8000/health/
curl http://localhost:8000/health/services/   # all upstream services
curl http://localhost:8000/health/ready/
curl http://localhost:8000/health/live/

# Direct service health
curl http://localhost:8001/health/  # auth
curl http://localhost:8002/health/  # booking
curl http://localhost:8003/health/  # parking
curl http://localhost:8009/health/  # AI (only if port exposed or via task)
```

### 2.3 Docker Start Commands

```bash
# Development (no nginx)
cd backend-microservices
docker compose up -d

# Production (with nginx + prod env vars)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check status
docker compose ps
docker compose logs -f --tail=50
```

### 2.4 Environment Variables Required (.env)

```
DB_USER=root                # or parksmartuser
DB_PASSWORD=parksmartpass
SECRET_KEY=<django-secret>
GATEWAY_SECRET=gateway-internal-secret-key
RABBITMQ_USER=<rabbitmq-user>
RABBITMQ_PASS=<rabbitmq-pass>
DEBUG=True
GEMINI_API_KEY=<for-chatbot>
ESP32_DEVICE_TOKEN=<optional>
```

---

## 3. Cloudflare Tunnel Config

### 3.1 Config File

**Location:** `infra/cloudflare/cloudflared/config.yml`

```yaml
tunnel: 57eb6de9-3ffa-4fe8-bb64-0aa7150f2684
credentials-file: C:\Users\MINH\.cloudflared\57eb6de9-3ffa-4fe8-bb64-0aa7150f2684.json

ingress:
  - hostname: app.ghepdoicaulong.shop   → http://localhost:80  (Nginx → FE)
  - hostname: api.ghepdoicaulong.shop   → http://localhost:80  (Nginx → Gateway:8000)
  - hostname: ws.ghepdoicaulong.shop    → http://localhost:80  (Nginx → Realtime:8006)
  - service: http_status:404
```

### 3.2 Start Tunnel Command

```powershell
cloudflared tunnel --config "infra/cloudflare/cloudflared/config.yml" run
```

### 3.3 Nginx Routing (infra/nginx/nginx.conf)

```
upstream api_backend → host.docker.internal:8000 (Gateway)
upstream ws_backend  → host.docker.internal:8006 (WebSocket)

/api/*  → proxy_pass http://api_backend/api/
/ws/*   → proxy_pass http://ws_backend/ws/ (WebSocket upgrade)
/*      → serve /usr/share/nginx/html (FE dist/)
```

---

## 4. API Gateway Routing

Gateway at `localhost:8000` strips `/api/` prefix and routes by first path segment:

| Gateway Path           | Target Service       | Auth Required        |
| ---------------------- | -------------------- | -------------------- |
| `/api/auth/register/`  | auth-service         | No (public)          |
| `/api/auth/login/`     | auth-service         | No (public)          |
| `/api/auth/logout/`    | auth-service         | No (special handler) |
| `/api/auth/me/`        | auth-service         | **Yes**              |
| `/api/auth/admin/*`    | auth-service         | **Yes**              |
| `/api/parking/*`       | parking-service      | **Yes**              |
| `/api/vehicles/*`      | vehicle-service      | **Yes**              |
| `/api/bookings/*`      | booking-service      | **Yes**              |
| `/api/incidents/*`     | booking-service      | **Yes**              |
| `/api/notifications/*` | notification-service | **Yes**              |
| `/api/realtime/*`      | realtime-service     | **Yes**              |
| `/api/payments/*`      | payment-service      | **Yes**              |
| `/api/ai/*`            | ai-service           | **Yes**              |
| `/api/chatbot/*`       | chatbot-service      | **Yes**              |

**Auth mechanism:** Session cookie (`sessionid`). Gateway reads session from Redis, extracts `user_id`/`email`, injects `X-Gateway-Secret + X-User-ID + X-User-Email` headers to backend.

---

## 5. Complete Booking Flow (Step-by-Step)

### 5.1 Register

```http
POST /api/auth/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "testuser",
  "password": "TestPass123!",
  "phone": "0912345678"   // optional
}
```

Response: `201` with `{ "user": { "id": "...", "email": "...", ... }, "message": "User registered successfully" }`

### 5.2 Login

```http
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "TestPass123!"
}
```

Response: `200` with `{ "user": {...}, "message": "Login successful" }` + `Set-Cookie: sessionid=...`

### 5.3 Register Vehicle

```http
POST /api/vehicles/
Cookie: sessionid=...

{
  "license_plate": "51A-999.88",
  "vehicle_type": "Car",
  "brand": "Toyota",
  "model": "Camry",
  "color": "White",
  "is_default": true
}
```

### 5.4 Get Parking Lots & Slots

```http
GET /api/parking/lots/
GET /api/parking/floors/?lot_id={lot_id}
GET /api/parking/zones/?floor_id={floor_id}
GET /api/parking/slots/?lot_id={lot_id}&page_size=200
```

### 5.5 Get Package Pricing

```http
GET /api/bookings/packagepricings/
```

### 5.6 Create Booking

```http
POST /api/bookings/
Cookie: sessionid=...

{
  "vehicle_id": "<uuid>",
  "parking_lot_id": "<uuid>",
  "zone_id": "<uuid>",
  "slot_id": "<uuid>",          // optional
  "package_type": "hourly",      // hourly | daily | weekly | monthly
  "start_time": "2026-04-09T10:00:00Z",
  "end_time": "2026-04-09T12:00:00Z",    // for hourly
  "payment_method": "online"     // online | on_exit
}
```

Response includes `qr_code_data` (JSON string with `booking_id` + `user_id`).

### 5.7 Check-In (ESP32 Path)

```http
POST /api/ai/parking/esp32/check-in/
X-Device-Token: <optional>

{
  "gate_id": "GATE-IN-01",
  "qr_data": "{\"booking_id\":\"...\",\"user_id\":\"...\"}",
  "qr_camera_url": null,
  "plate_camera_url": null
}
```

Response: `{ "success": true, "event": "check_in_success", "barrier_action": "open", ... }`

### 5.8 Check-In (HTTP Path — with image upload)

```http
POST /api/ai/parking/check-in/
Content-Type: multipart/form-data

image=<file>
qr_data={"booking_id":"...","user_id":"..."}
```

### 5.9 Check-Out (ESP32 Path)

```http
POST /api/ai/parking/esp32/check-out/
{
  "gate_id": "GATE-OUT-01",
  "qr_data": "{\"booking_id\":\"...\",\"user_id\":\"...\"}"
}
```

### 5.10 Check-Out (HTTP Path)

```http
POST /api/ai/parking/check-out/
Content-Type: multipart/form-data

image=<file>
booking_id=<uuid>
user_id=<uuid>
```

### 5.11 Direct Booking Check-In/Out (service-to-service)

```http
POST /api/bookings/{booking_id}/checkin/
POST /api/bookings/{booking_id}/checkout/
POST /api/bookings/{booking_id}/cancel/
GET  /api/bookings/{booking_id}/qr-code/
```

---

## 6. Seed Data & Test Accounts

### 6.1 Available Seed Scripts

| Script                    | Purpose                                             | Test Accounts                                                                      |
| ------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `seed_e2e_data.py`        | Full E2E data (users, vehicles, bookings, payments) | `e2e_playwright@parksmart.com / TestPass123!` + `admin@parksmart.com / admin1234@` |
| `seed_admin_test_data.py` | Admin-specific data (profile, vehicles, 6 bookings) | `admin@example.com` (ID: `64ed02950d1842c19e52dd787b8bd847`)                       |
| `seed_user_test_data.py`  | Additional user test data                           | (similar pattern)                                                                  |

### 6.2 E2E Test Accounts (from seed_e2e_data.py)

| Email                          | Password       | Role  | Vehicles                                     |
| ------------------------------ | -------------- | ----- | -------------------------------------------- |
| `e2e_playwright@parksmart.com` | `TestPass123!` | user  | `51A-999.88` (Car), `59C-123.45` (Motorbike) |
| `admin@parksmart.com`          | `admin1234@`   | admin | —                                            |

### 6.3 Running Seed Scripts

```bash
cd backend-microservices
python seed_e2e_data.py     # requires MySQL on localhost:3307
```

### 6.4 Existing E2E Test Script

`test_e2e_full_flow.py` — Tests full flow but uses **direct service ports** (not gateway):

- AUTH_URL: `localhost:8001`
- PARKING_URL: `localhost:8002` (⚠️ should be 8003)
- VEHICLE_URL: `localhost:8003` (⚠️ should be exposed vehicle port)
- BOOKING_URL: `localhost:8004` (⚠️ no service on 8004 — booking is 8002)
- AI_URL: `localhost:8009`

**⚠️ BLOCKER: Port mapping in `test_e2e_full_flow.py` is WRONG:**

- `PARKING_URL` should be `localhost:8003` (correct)
- `BOOKING_URL` should be `localhost:8002` (currently `8004`)
- `VEHICLE_URL` — vehicle-service only has `expose: 8000` (no host port), not reachable directly

---

## 7. AI Service Endpoints (Complete)

### 7.1 Router Structure

| Router         | Prefix               | Purpose                                                    |
| -------------- | -------------------- | ---------------------------------------------------------- |
| `esp32.py`     | `/ai/parking/esp32/` | ESP32 gate check-in/out/verify-slot/cash-payment           |
| `parking.py`   | `/ai/parking/`       | HTTP check-in/out with image upload                        |
| `camera.py`    | `/ai/cameras/`       | Virtual camera frame receive, snapshot, stream, plate read |
| `detection.py` | `/ai/detect/`        | License plate OCR, banknote recognition                    |
| `training.py`  | `/ai/training/`      | Model training endpoints                                   |
| `metrics.py`   | `/ai/metrics/`       | AI metrics/stats                                           |

### 7.2 ESP32 Endpoints (gate hardware/simulator)

```
POST /ai/parking/esp32/check-in/      — gate-in with QR + plate
POST /ai/parking/esp32/check-out/     — gate-out with QR + plate + payment check
POST /ai/parking/esp32/verify-slot/   — slot-level QR scan
POST /ai/parking/esp32/cash-payment/  — cash detection at exit
GET  /ai/parking/esp32/status/        — health + camera status
```

**Request format (check-in):**

```json
{
  "gate_id": "GATE-IN-01",
  "qr_data": "{\"booking_id\":\"...\",\"user_id\":\"...\"}",
  "qr_camera_url": null,
  "plate_camera_url": null,
  "request_id": null
}
```

**Response format:**

```json
{
  "success": true,
  "event": "check_in_success",
  "barrierAction": "open",
  "message": "Check-in successful",
  "gateId": "GATE-IN-01",
  "bookingId": "...",
  "plateText": "51A99988",
  "amountDue": null,
  "amountPaid": null,
  "processingTimeMs": 1234.5,
  "details": {}
}
```

### 7.3 HTTP Parking Endpoints (image upload)

```
POST /ai/parking/scan-plate/          — OCR only (no booking check)
POST /ai/parking/check-in/            — multipart: image + qr_data
POST /ai/parking/check-out/           — multipart: image + booking_id + user_id
POST /ai/parking/detect-occupancy/    — camera image + slot bboxes → occupancy
```

### 7.4 Camera Endpoints

```
GET  /ai/cameras/list                 — list all cameras (physical + virtual)
POST /ai/cameras/frame                — receive JPEG from Unity (X-Camera-ID header)
GET  /ai/cameras/snapshot?camera_id=  — get single JPEG frame
GET  /ai/cameras/stream?camera_id=    — MJPEG multipart stream
GET  /ai/cameras/read-plate?camera_id= — OCR on latest virtual camera frame
```

**Virtual Camera IDs:**

- `virtual-f1-overview` — Floor 1 overview
- `virtual-f2-overview` — Floor 2 overview
- `virtual-gate-in` — Entry gate
- `virtual-gate-out` — Exit gate
- `virtual-zone-south` — Zone South
- `virtual-zone-north` — Zone North

**Frame receive format:**

```http
POST /ai/cameras/frame
X-Camera-ID: virtual-gate-in
X-Gateway-Secret: gateway-internal-secret-key
Content-Type: application/octet-stream

<raw JPEG bytes, max 500KB>
```

### 7.5 Detection Endpoints

```
POST /ai/detect/license-plate/       — Upload image → plate OCR
```

### 7.6 ESP32 Device Management

```
POST /ai/parking/esp32/register       — register device
POST /ai/parking/esp32/heartbeat      — device heartbeat
POST /ai/parking/esp32/log            — device logs
GET  /ai/parking/esp32/devices        — list all devices
GET  /ai/parking/esp32/devices/{id}   — device detail + logs
```

Pre-seeded devices at startup: `GATE-IN-01`, `GATE-OUT-01`

### 7.7 Auth: ESP32 device endpoints use `X-Device-Token` header (optional, controlled by `ESP32_DEVICE_TOKEN` env var)

---

## 8. Unity Configuration

### 8.1 ApiConfig.cs (ScriptableObject)

**File:** `ParkingSimulatorUnity/Assets/Scripts/API/ApiConfig.cs`

| Field                   | Default                          | Purpose                              |
| ----------------------- | -------------------------------- | ------------------------------------ |
| `gatewayBaseUrl`        | `http://localhost:8000`          | Gateway API base                     |
| `aiServiceUrl`          | `http://localhost:8009`          | Direct AI service (for camera/ESP32) |
| `realtimeWsUrl`         | `ws://localhost:8006/ws/parking` | WebSocket                            |
| `gatewaySecret`         | `gateway-internal-secret-key`    | Internal auth                        |
| `testEmail`             | `test@example.com`               | Auto-login                           |
| `testPassword`          | `password`                       | Auto-login                           |
| `cameraFps`             | `5`                              | Virtual camera FPS                   |
| `cameraResWidth/Height` | `640x480`                        | Camera resolution                    |
| `cameraJpegQuality`     | `75`                             | JPEG quality                         |
| `useMockData`           | `false`                          | Mock mode flag                       |

### 8.2 Key Unity Scripts

| Script                     | Purpose                                      | API Used                                    |
| -------------------------- | -------------------------------------------- | ------------------------------------------- |
| `ApiService.cs`            | Central API client (HTTP + WebSocket)        | Gateway `/api/*` + AI direct                |
| `ESP32Simulator.cs`        | ESP32 gate check-in/out simulator with IMGUI | `/ai/parking/esp32/check-in/check-out/`     |
| `GateCameraSimulator.cs`   | Gate camera → capture frame → AI OCR         | `/ai/detect/license-plate/`                 |
| `VirtualCameraStreamer.cs` | Stream rendertexture JPEG frames to AI       | `POST /ai/cameras/frame` with `X-Camera-ID` |

### 8.3 Unity API Endpoints Used

```
GET  /api/parking/lots/
GET  /api/parking/slots/?lot_id={id}&page_size=200
GET  /api/parking/floors/?lot_id={id}
POST /api/bookings/
POST /ai/parking/esp32/check-in/
POST /ai/parking/esp32/check-out/
POST /ai/cameras/frame           (direct to AI service)
POST /ai/detect/license-plate/   (direct to AI service)
GET  /ai/cameras/read-plate?camera_id=...
ws://localhost:8006/ws/parking    (realtime slot updates)
```

### 8.4 Unity Configuration for E2E Testing

To connect Unity to the backend:

1. Select `ApiConfig` ScriptableObject in Unity
2. Set `Gateway Base URL` = `http://localhost:8000`
3. Set `AI Service URL` = `http://localhost:8009`
4. Set `Realtime WS URL` = `ws://localhost:8006/ws/parking`
5. Set `Gateway Secret` = `gateway-internal-secret-key`
6. Set `Test Email` = `e2e_playwright@parksmart.com`
7. Set `Test Password` = `TestPass123!`
8. Set `Use Mock Data` = `false`
9. Set `Target Parking Lot ID` = (get from `/api/parking/lots/` response)

---

## 9. Chatbot Service Endpoints

### 9.1 Routes

| Method  | Path                                        | Purpose                        |
| ------- | ------------------------------------------- | ------------------------------ |
| POST    | `/api/chatbot/chat/`                        | Send message, get AI response  |
| GET     | `/api/chatbot/conversations/`               | List conversations             |
| POST    | `/api/chatbot/conversations/`               | Create conversation            |
| GET     | `/api/chatbot/conversations/active/`        | Get/create active conversation |
| GET     | `/api/chatbot/conversations/{id}/`          | Get conversation detail        |
| GET     | `/api/chatbot/conversations/{id}/messages/` | Get messages                   |
| GET     | `/api/chatbot/actions/`                     | Recent actions (undo support)  |
| GET     | `/api/chatbot/notifications/`               | Chatbot notifications          |
| GET/PUT | `/api/chatbot/preferences/`                 | User preferences               |

### 9.2 Chat Request Format

```json
POST /api/chatbot/chat/
{
  "message": "Tôi muốn đặt chỗ đỗ xe",
  "conversation_id": "optional-uuid"
}
```

### 9.3 Dependencies

- **Gemini API** (`GEMINI_API_KEY`) for LLM intent classification
- **Redis DB 6** for conversation cache
- **RabbitMQ** for proactive event handling
- Calls booking/parking/vehicle/payment services internally

---

## 10. Frontend Pages (spotlove-ai)

### 10.1 Available Pages

| Page Component              | Route (likely)   | Purpose                                |
| --------------------------- | ---------------- | -------------------------------------- |
| `Index.tsx`                 | `/`              | Landing / home                         |
| `LoginPage.tsx`             | `/login`         | User login                             |
| `RegisterPage.tsx`          | `/register`      | User registration                      |
| `AuthCallbackPage.tsx`      | `/auth/callback` | OAuth callback                         |
| `BookingPage.tsx`           | `/booking`       | Create/manage bookings                 |
| `CamerasPage.tsx`           | `/cameras`       | Camera monitoring (virtual + physical) |
| `CheckInOutPage.tsx`        | `/check-in-out`  | Check-in/out kiosk                     |
| `MapPage.tsx`               | `/map`           | Parking lot map                        |
| `PaymentPage.tsx`           | `/payment`       | Payment processing                     |
| `HistoryPage.tsx`           | `/history`       | Booking history                        |
| `UserDashboard.tsx`         | `/dashboard`     | User dashboard                         |
| `KioskPage.tsx`             | `/kiosk`         | Kiosk mode                             |
| `SettingsPage.tsx`          | `/settings`      | User settings                          |
| `SupportPage.tsx`           | `/support`       | Support (chatbot)                      |
| `BanknoteDetectionPage.tsx` | `/banknote`      | Cash detection test                    |
| `PanicButtonPage.tsx`       | `/panic`         | Emergency button                       |
| `admin/AdminDashboard.tsx`  | `/admin`         | Admin panel                            |

### 10.2 Dev Server

```bash
cd spotlove-ai
bun install    # or npm install
bun dev        # Vite dev server at http://localhost:5173
bun run build  # Build to dist/
```

---

## 11. Parking Data Model (Important for Seed)

```
ParkingLot (id, name, address, lat, long, total_slots, available_slots, price_per_hour, is_open)
  └── Floor (id, parking_lot_id, level, name)
       └── Zone (id, floor_id, name, vehicle_type, capacity, available_slots)
            └── CarSlot (id, zone_id, code, status, camera_id, x1/y1/x2/y2)
            └── Camera (id, name, ip_address, port, zone_id, stream_url, is_active)
```

**Slot statuses:** available | occupied | reserved | maintenance
**Vehicle types:** Car | Motorbike
**Booking check_in_status:** not_checked_in | checked_in | checked_out | no_show | cancelled

---

## 12. ⚠️ Gotchas & Known Issues

- [x] **[BLOCKER]** `test_e2e_full_flow.py` has WRONG port mapping: `BOOKING_URL=localhost:8004` should be `8002`; `PARKING_URL=localhost:8002` should be `8003`
- [ ] **[WARNING]** `vehicle-service` has NO host port mapping (only `expose: 8000`), only reachable through gateway or Docker network
- [ ] **[WARNING]** `notification-service`, `payment-service`, `ai-service`, `chatbot-service` also have no host ports — only reachable through gateway or Docker network
- [ ] **[NOTE]** AI service task (`AI Service - Local`) runs AI on port 8009 locally (outside Docker) with direct MySQL 3307 — useful for E2E testing without full Docker
- [ ] **[NOTE]** ESP32 device token is optional (empty string means no auth required)
- [ ] **[NOTE]** Virtual camera frame buffer expires after 30 seconds (`_STALE_THRESHOLD`)
- [ ] **[NOTE]** Cloudflare tunnel config has real tunnel ID `57eb6de9-3ffa-4fe8-bb64-0aa7150f2684` (was previously a placeholder per status.yaml)
- [ ] **[NOTE]** Production domains: `app.ghepdoicaulong.shop` (FE), `api.ghepdoicaulong.shop` (API), `ws.ghepdoicaulong.shop` (WS)

---

## 13. For E2E Testing — Recommended Setup

### Minimum services needed:

1. **MySQL** (port 3307) — DB
2. **Redis** (port 6379) — sessions + cache
3. **Auth Service** (port 8001) — login/register
4. **Parking Service** (port 8003) — lots/slots
5. **Booking Service** (port 8002) — bookings + celery worker
6. **Gateway** (port 8000) — unified API entry
7. **AI Service** (port 8009, can run local via VS Code task) — check-in/out

### Optional for full flow:

- RabbitMQ (port 5672) — if testing chatbot proactive events
- Realtime Service (port 8006) — if testing WebSocket updates in Unity
- Payment Service — if testing payment flows
- Chatbot Service — if testing chatbot

### Quick Start for E2E:

```powershell
# 1. Start infrastructure
cd backend-microservices
docker compose up -d mysql redis rabbitmq

# 2. Wait for MySQL healthy (~60s)
docker compose exec mysql mysqladmin ping -h 127.0.0.1 -u root -pparksmartpass

# 3. Start Django services
docker compose up -d auth-service parking-service booking-service vehicle-service gateway-service-go

# 4. Seed test data
python seed_e2e_data.py

# 5. Start AI service locally (VS Code task "AI Service - Local")
# OR: docker compose up -d ai-service-fastapi

# 6. (Optional) Start Realtime + others
docker compose up -d realtime-service-go notification-service-fastapi payment-service-fastapi chatbot-service-fastapi
```

---

## 14. Nguồn

| #   | File/Source                                                  | Purpose                  |
| --- | ------------------------------------------------------------ | ------------------------ |
| 1   | `backend-microservices/docker-compose.yml`                   | All services config      |
| 2   | `backend-microservices/docker-compose.prod.yml`              | Production overlay       |
| 3   | `infra/cloudflare/cloudflared/config.yml`                    | Tunnel config            |
| 4   | `infra/nginx/nginx.conf`                                     | Nginx routing            |
| 5   | `gateway-service-go/internal/config/config.go`               | Gateway routing rules    |
| 6   | `auth-service/users/urls.py + views.py`                      | Auth endpoints           |
| 7   | `booking-service/bookings/models.py + urls.py`               | Booking model + routes   |
| 8   | `parking-service/infrastructure/models.py + urls.py`         | Parking model + routes   |
| 9   | `vehicle-service/vehicles/models.py + urls.py`               | Vehicle model + routes   |
| 10  | `ai-service-fastapi/app/routers/esp32.py`                    | ESP32 check-in/out       |
| 11  | `ai-service-fastapi/app/routers/camera.py`                   | Virtual camera endpoints |
| 12  | `ai-service-fastapi/app/routers/parking.py`                  | HTTP check-in/out        |
| 13  | `chatbot-service-fastapi/app/routers/chat.py`                | Chatbot main endpoint    |
| 14  | `ParkingSimulatorUnity/Assets/Scripts/API/ApiConfig.cs`      | Unity API config         |
| 15  | `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs`     | Unity API service        |
| 16  | `ParkingSimulatorUnity/Assets/Scripts/IoT/ESP32Simulator.cs` | Unity ESP32 sim          |
| 17  | `ParkingSimulatorUnity/Assets/Scripts/Camera/*.cs`           | Unity camera scripts     |
| 18  | `backend-microservices/seed_e2e_data.py`                     | E2E seed script          |
| 19  | `backend-microservices/test_e2e_full_flow.py`                | Existing E2E test        |
| 20  | `scripts/deploy-local.ps1`                                   | Deployment script        |
