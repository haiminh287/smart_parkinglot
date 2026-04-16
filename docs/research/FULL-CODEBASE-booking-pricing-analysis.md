# Research Report: ParkSmart Booking & Pricing Logic — Full Codebase Analysis

**Task:** Full Codebase Analysis | **Date:** 2026-04-13 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **Pricing model** có 8 gói (hourly/daily/weekly/monthly × Car/Motorbike), đơn giá từ `package_pricing` table. Hourly: 15K VND/h (car), 5K VND/h (moto). Overtime tính phí 1.5× hourly rate.
> 2. **Extend booking feature**: Model có field `extended_until`, nhưng **KHÔNG CÓ endpoint** implement — chỉ có notification gợi ý `/bookings/{id}/extend` (404).
> 3. **Frontend PriceSummary có fallback prices hardcoded** khác với DB seed (FE car hourly = 20K, DB = 15K). FE cũng apply discount 20% monthly, 10% weekly mà backend **KHÔNG apply** → giá frontend hiển thị ≠ giá backend tính.

---

## 2. Service Topology

### 2.1 All Services & Ports

| Service                   | Tech                 | Internal Port | External Port | Container Name               |
| ------------------------- | -------------------- | ------------- | ------------- | ---------------------------- |
| **MySQL**                 | MySQL 8.0            | 3306          | 3307          | parksmartdb_mysql            |
| **Redis**                 | Redis 7 Alpine       | 6379          | 6379          | parksmartdb_redis            |
| **RabbitMQ**              | 3-management-alpine  | 5672/15672    | 5672/15672    | parksmartdb_rabbitmq         |
| **Auth Service**          | Django               | 8000          | 8001          | auth-service                 |
| **Booking Service**       | Django + Celery      | 8000          | 8002          | booking-service              |
| **Parking Service**       | Django               | 8000          | 8003          | parking-service              |
| **Vehicle Service**       | Django               | 8000          | (expose only) | vehicle-service              |
| **Notification Service**  | FastAPI              | 8005          | (expose only) | notification-service-fastapi |
| **Realtime Service**      | Go (WebSocket)       | 8006          | 8006          | realtime-service-go          |
| **Payment Service**       | FastAPI (SQLAlchemy) | 8007          | (expose only) | payment-service-fastapi      |
| **Chatbot Service**       | FastAPI              | 8008          | (expose only) | chatbot-service-fastapi      |
| **AI Service**            | FastAPI (PyTorch)    | 8009          | 8009          | ai-service-fastapi           |
| **Gateway**               | Go (Gin)             | 8000          | 8000          | gateway-service-go           |
| **Booking Celery Worker** | Celery               | —             | —             | booking-celery-worker        |
| **Booking Celery Beat**   | Celery Beat          | —             | —             | booking-celery-beat          |

### 2.2 Redis DB Allocation

| DB  | Service                        |
| --- | ------------------------------ |
| 0   | Celery broker + result backend |
| 1   | Auth service + Gateway         |
| 2   | Booking service                |
| 3   | Parking service                |
| 4   | Vehicle service                |
| 5   | Realtime service               |
| 6   | Chatbot service                |

### 2.3 Gateway Routing (Go — catch-all proxy)

Gateway at `:8000` removes `/api/` prefix, then routes by path prefix:

| Path Prefix                 | Service              | Auth Required                   |
| --------------------------- | -------------------- | ------------------------------- |
| `auth/login`, `auth/logout` | auth-service         | No (handled directly)           |
| `auth/` (others)            | auth-service         | Varies (admin=yes, register=no) |
| `parking/`                  | parking-service      | Yes                             |
| `vehicles/`                 | vehicle-service      | Yes                             |
| `bookings/`                 | booking-service      | Yes                             |
| `incidents/`                | booking-service      | Yes                             |
| `notifications/`            | notification-service | Yes                             |
| `realtime/`                 | realtime-service     | Yes                             |
| `payments/`                 | payment-service      | Yes                             |
| `ai/`                       | ai-service           | Yes                             |
| `chatbot/`                  | chatbot-service      | Yes                             |

Auth: JWT token in cookie (session-based via Go gateway) → decoded → `X-User-ID`, `X-User-Email`, `X-Gateway-Secret` headers injected into proxied requests.

---

## 3. Booking Flow — Step by Step

### 3.1 Online Booking Creation

**Frontend:** `BookingPage.tsx` — 5-step wizard:

1. **Step 1**: Select parking lot → loads floors
2. **Step 2**: Select vehicle (from saved vehicles or enter plate) + vehicle type (Car/Motorbike)
3. **Step 3**: Select floor → zone → slot (car must pick slot, motorbike only needs zone)
4. **Step 4**: Select time package (hourly/daily/weekly/monthly/custom)
5. **Step 5**: Payment method (online/on_exit) → Submit

**API Call:** `POST /api/bookings/`

```json
{
  "vehicleId": "uuid-or-license-plate",
  "slotId": "uuid (optional for motorbike)",
  "zoneId": "uuid",
  "parkingLotId": "uuid",
  "startTime": "ISO-8601",
  "endTime": "ISO-8601 (optional)",
  "packageType": "hourly|daily|weekly|monthly",
  "paymentMethod": "online|on_exit"
}
```

**Backend Processing (CreateBookingSerializer.create):**

1. Fetch vehicle info from vehicle-service (or auto-register if license plate provided)
2. Fetch parking lot name from parking-service
3. Fetch zone info (name, floor_id, vehicle_type, capacity)
4. Fetch floor info (level)
5. Fetch slot info (code) if slot_id provided
6. **Calculate price** from `PackagePricing` table:
   - Hourly: `ceil(hours) × hourly_price`
   - Other packages: flat `price` from table
7. Generate QR code data (JSON with booking_id, user_id, timestamp)
8. Check slot conflict (atomic SELECT FOR UPDATE)
9. Create Booking record
10. Mark slot as "reserved" in parking-service
11. Broadcast "reserved" status via realtime-service WebSocket
12. **Auto-create payment** record in payment-service (best-effort)

**Response includes:** `booking` object + `qrCode` + `message`

### 3.2 Status Flow

```
not_checked_in ──────┬──→ checked_in ──→ checked_out
                     │
                     ├──→ cancelled (user cancel or auto-cancel)
                     │
                     └──→ no_show (Celery task after 30min)
```

### 3.3 Check-in

**Sources:**

- Web UI: `CheckInOutPage.tsx` — upload plate image or show QR
- ESP32 gate: `POST /ai/parking/esp32/check-in/` — QR scan + plate OCR
- Web API: `POST /ai/parking/check-in/` — QR data + plate image

**Process:**

1. ESP32/web sends QR data (booking_id + user_id) + plate image
2. AI service: OCR plate → compare with booking.vehicle_license_plate
3. Validate time: allow 30 min early (booking-service) or 15 min early (ESP32)
4. Call `POST /bookings/{id}/checkin/` on booking-service
5. Booking: set `check_in_status='checked_in'`, `checked_in_at=now()`
6. Update slot to "occupied" in parking-service
7. Broadcast "occupied" via WebSocket
8. ESP32 response: `barrier_action: "open"` → opens gate

### 3.4 Check-out

**Process:**

1. ESP32/web sends QR data + plate image
2. AI service: OCR plate → verify match
3. Call `POST /bookings/{id}/checkout/` on booking-service
4. **Calculate checkout price** (see Section 4 below)
5. Set `check_in_status='checked_out'`, `checked_out_at=now()`
6. Update slot to "available" in parking-service
7. Broadcast "available" via WebSocket
8. ESP32: check if payment completed → open barrier or await cash payment

---

## 4. Pricing Model — Complete Details

### 4.1 Package Pricing Table (seed_pricing.py)

| Package Type | Vehicle Type | Price (VND) | Duration |
| ------------ | ------------ | ----------- | -------- |
| **Hourly**   | Car          | 15,000      | per hour |
| **Hourly**   | Motorbike    | 5,000       | per hour |
| **Daily**    | Car          | 80,000      | 1 day    |
| **Daily**    | Motorbike    | 20,000      | 1 day    |
| **Weekly**   | Car          | 400,000     | 7 days   |
| **Weekly**   | Motorbike    | 100,000     | 7 days   |
| **Monthly**  | Car          | 1,200,000   | 30 days  |
| **Monthly**  | Motorbike    | 300,000     | 30 days  |

DB table: `package_pricing` (unique constraint on `package_type + vehicle_type`)

### 4.2 Price Calculation at Booking Time

**Source:** `CreateBookingSerializer.create()` in `serializers.py:246-255`

```python
pricing = PackagePricing.objects.get(package_type=package_type, vehicle_type=vehicle_type)
if package_type == 'hourly' and start_time and end_time:
    hours = (end_time - start_time).total_seconds() / 3600
    price = math.ceil(hours) * float(pricing.price)
else:
    price = float(pricing.price)  # Flat rate for daily/weekly/monthly
```

**Key:** Hourly = ceil(hours) × rate. Other packages = flat price.

### 4.3 Price Calculation at Checkout Time

**Source:** `services.calculate_checkout_price()` in `services.py:42-83`

**Hourly with scheduled end time (`hourly_end` set):**

```
If now > hourly_end (overtime):
  overtime_hours = ceil((now - hourly_end) in hours)
  scheduled_hours = ceil((hourly_end - hourly_start) in hours)
  base_amount = scheduled_hours × hourly_price
  late_fee = overtime_hours × (hourly_price × 1.5)   ← 50% SURCHARGE
  total = base_amount + late_fee
  late_fee_applied = True

If now <= hourly_end (on time):
  scheduled_hours = ceil((hourly_end - hourly_start) in hours)
  total = scheduled_hours × hourly_price
```

**Non-hourly or no scheduled end:**

```
billable_hours = ceil(actual_hours) or 1 minimum
total = billable_hours × hourly_price
```

**Key insight:** At checkout, ALL packages fall back to hourly billing based on actual time parked. Daily/weekly/monthly bookings are still charged by the hour at checkout. This may be intentional (pay-per-use) or a bug.

### 4.4 Fallback Prices (when PackagePricing table empty)

```python
# In services.py and views.py
Car:       15,000 VND/hour
Motorbike:  5,000 VND/hour
```

### 4.5 Frontend Pricing (PriceSummary.tsx)

**Fallback prices (different from backend!):**

```typescript
const FALLBACK_PRICES = {
  Car: { monthly: 2000000, weekly: 600000, daily: 100000, hourly: 20000 },
  Motorbike: { monthly: 500000, weekly: 150000, daily: 25000, hourly: 5000 },
};
```

**Discounts applied on frontend only:**

```typescript
const DISCOUNTS = {
  monthly: 0.2, // 20% off
  weekly: 0.1, // 10% off
  custom: 0,
  hourly: 0,
};
```

**Important:** Frontend fetches pricing from `GET /api/bookings/packagepricings/` and overlays fallbacks. But discounts are frontend-only — backend does NOT apply discounts.

---

## 5. Payment Flow

### 5.1 Payment Methods

| Method  | Code      | Behavior                                  |
| ------- | --------- | ----------------------------------------- |
| Cash    | `cash`    | Auto-completed immediately                |
| Momo    | `momo`    | Status = "processing", mock URL generated |
| VNPay   | `vnpay`   | Status = "processing", mock URL generated |
| ZaloPay | `zalopay` | Status = "processing", mock URL generated |

**Note:** Momo/VNPay/ZaloPay are currently **MOCKED** — no real gateway integration. They generate fake payment URLs like `https://payment-gateway.example.com/pay/...`

### 5.2 Payment Flow

1. **At booking creation:** `services.create_payment_for_booking()` auto-creates a payment record → calls `POST /api/payments/initiate/` on payment-service
2. **Payment mapping:** Booking `on_exit` → payment method `cash` (auto-completed). Booking `online` → also maps to `cash` by default (user can initiate specific method later)
3. **Manual payment initiation:** `POST /api/bookings/payment/` with `payment_method` → calls payment-service
4. **Cash payment**: Immediately completed with transaction_id = `CASH-{random12}`
5. **Online payment**: Status = `processing` → generate mock URL → user "pays" → verify callback → status = `completed`
6. **Payment verification**: `POST /api/payments/verify/{payment_id}/` → marks completed → notifies booking-service → broadcasts via realtime
7. **Frontend polling**: PaymentPage.tsx polls payment status every 10s (3s after user clicks confirm)

### 5.3 Auto-Cancel Unpaid (Celery Beat)

- Bookings with `payment_method='online'` + `payment_status='pending'` + `check_in_status='not_checked_in'` + older than 15 minutes → auto-cancelled
- Releases slot, broadcasts update, sends notification

### 5.4 No-Show Detection (Celery Beat)

- Hourly bookings + `not_checked_in` + `hourly_start + 30 min < now` → marked `no_show`
- Increments user's no_show count in auth-service
- Sends warning notification with suggestion to extend

### 5.5 No-Show Penalty

- Frontend: `noShowCount >= 2` → forces online payment (`forceOnlinePayment`)
- User sees warning banner on BookingPage

### 5.6 VietQR (PaymentPage.tsx)

Frontend generates VietQR code for bank transfer:

```
https://img.vietqr.io/image/{bankCode}-{accountNumber}-compact.png?amount={amount}&addInfo={bookingId}
```

Bank info configurable via env vars (`VITE_BANK_CODE`, etc.) with Vietcombank defaults.

---

## 6. AI Integration

### 6.1 Plate Detection

**Pipeline:** YOLOv8 finetune (license-plate-finetune-v1m.pt) → crop → TrOCR OCR

**Endpoints:**

- `POST /ai/detect/license-plate/` — standalone detection
- `POST /ai/parking/scan-plate/` — scan only (preview)
- `POST /ai/parking/check-in/` — QR + plate for web check-in
- `POST /ai/parking/check-out/` — QR + plate for web check-out
- `POST /ai/parking/esp32/check-in/` — ESP32 gate-in flow
- `POST /ai/parking/esp32/check-out/` — ESP32 gate-out flow

**Plate matching:** Normalize (uppercase, alphanumeric only), exact match for parking.py, fuzzy match (70% SequenceMatcher or ≤3 char diff) for esp32.py.

### 6.2 Image Saving

**Location:** `ai-service-fastapi/app/images/` (local) or `/app/app/images/` (Docker)

**File naming:**

- Plate images: `plate_{action}_{booking_id_short}_{timestamp}.jpg`
- Annotated images: `annotated_{action}_{id_short}_{timestamp}.jpg`
- Debug images: `app/images/debug/debug_{action}_{decision}_{timestamp}.jpg`

**MEDIA_ROOT:** `/app/media` (Docker volume `parksmart_media`) — used by detection router for banknote/cash images.

### 6.3 Slot Detection

**Endpoint:** `POST /ai/parking/detect-occupancy/`

- Input: camera image + slot bounding boxes (JSON)
- Engine: YOLO11n (yolo11n.pt) — detects vehicles in defined bounding box regions
- Output: per-slot occupancy status (occupied/available)
- Feeds: web camera monitoring page (`CamerasPage.tsx`), can update parking-service slot status

### 6.4 ESP32 Cash Payment

**Endpoint:** `POST /ai/parking/esp32/cash-payment/`

- Input: booking_id + image (base64 or camera URL)
- AI detects banknote denomination via Hybrid pipeline (HSV + MobileNetV3)
- Accumulates cash amount for booking
- When amount_paid >= amount_due → opens barrier

---

## 7. Frontend Pages

| Page                   | File                        | Purpose                                                   |
| ---------------------- | --------------------------- | --------------------------------------------------------- |
| **Booking**            | `BookingPage.tsx`           | 5-step booking wizard (lot → vehicle → slot → time → pay) |
| **Payment**            | `PaymentPage.tsx`           | VietQR display + 15min countdown + payment polling        |
| **Check-in/out**       | `CheckInOutPage.tsx`        | Show QR, upload plate image, manual check-in/out          |
| **Cameras**            | `CamerasPage.tsx`           | Live camera feeds, slot monitoring                        |
| **History**            | `HistoryPage.tsx`           | Past bookings                                             |
| **Dashboard**          | `UserDashboard.tsx`         | User overview                                             |
| **Admin Dashboard**    | `AdminDashboard.tsx`        | Admin panel                                               |
| **Kiosk**              | `KioskPage.tsx`             | Kiosk mode for gate                                       |
| **Map**                | `MapPage.tsx`               | Parking lot map                                           |
| **Detection History**  | `DetectionHistoryPage.tsx`  | AI detection logs                                         |
| **Banknote Detection** | `BanknoteDetectionPage.tsx` | Cash recognition test                                     |
| **Settings**           | `SettingsPage.tsx`          | User settings                                             |
| **Panic Button**       | `PanicButtonPage.tsx`       | Emergency/incident reporting                              |

**Booking modes (3 tabs):**

1. **Standard** — manual step-by-step booking
2. **Auto Guarantee** — automatic slot assignment ("Đi đâu cũng có chỗ")
3. **Calendar Auto-Hold** — calendar integration for recurring bookings

---

## 8. Cloudflared Config

### 8.1 Main Config (`config.yml`)

- **Tunnel ID:** `57eb6de9-3ffa-4fe8-bb64-0aa7150f2684`
- **Hostnames:**
  - `app.ghepdoicaulong.shop` → localhost:80 (Nginx → FE)
  - `api.ghepdoicaulong.shop` → localhost:80 (Nginx → API)
  - `ws.ghepdoicaulong.shop` → localhost:80 (Nginx → WS)
  - `parksmart.ghepdoicaulong.shop` → localhost:80 (all-in-one)
- All route through Nginx at port 80

### 8.2 ParkSmart Config (`config-parksmart.yml`)

- **Tunnel ID:** `5d3c98ed-b629-48a3-9377-4163315c91da` (separate tunnel)
- **Hostname:** `parksmart.ghepdoicaulong.shop` → localhost:80

### 8.3 Nginx Config (`infra/nginx/nginx.conf`)

- `/api/*` → `host.docker.internal:8000` (Gateway)
- `/ws/*` → `host.docker.internal:8006` (Realtime, WebSocket upgrade)
- `/ai/*` → `host.docker.internal:8009` (AI Service, direct — bypasses gateway)
- `/*` → SPA fallback (index.html)
- Security headers: X-Frame-Options, CSP, HSTS, etc.

---

## 9. Existing E2E Tests

### Frontend (`spotlove-ai/e2e/`)

| Test File                   | Description           |
| --------------------------- | --------------------- |
| `booking-full-flow.spec.ts` | Full booking flow E2E |
| `booking.spec.ts`           | Basic booking tests   |
| `checkin-flow.spec.ts`      | Check-in flow         |
| `full-flows.spec.ts`        | Combined flow tests   |
| `admin.management.spec.ts`  | Admin management      |
| `admin.pages.spec.ts`       | Admin pages           |
| `api-endpoints.spec.ts`     | API endpoint tests    |
| `dashboard.spec.ts`         | Dashboard tests       |
| `history.spec.ts`           | History page tests    |
| `public-pages.spec.ts`      | Public page tests     |
| `user-pages.spec.ts`        | User page tests       |
| `global-setup.ts`           | Auth setup            |

### Backend Tests

| Test File                         | Location                 |
| --------------------------------- | ------------------------ |
| `test_e2e_parksmart.py`           | `backend-microservices/` |
| `test_e2e_full_flow.py`           | `backend-microservices/` |
| `test_booking_plate_scenarios.py` | `backend-microservices/` |
| `test_ai_full.py`                 | `backend-microservices/` |
| `test_chatbot_e2e.py`             | `backend-microservices/` |
| `test_chatbot_lifecycle.py`       | `backend-microservices/` |
| `test_booking_comprehensive.py`   | `booking-service/tests/` |

---

## 10. ⚠️ Issues Found

### 10.1 [WARNING] Frontend-Backend Pricing Mismatch

**Frontend fallback prices ≠ Backend seed prices:**

- FE car hourly: **20,000** VND vs DB seed: **15,000** VND
- FE car daily: **100,000** VND vs DB seed: **80,000** VND
- FE car monthly: **2,000,000** VND vs DB seed: **1,200,000** VND
- FE moto daily: **25,000** VND vs DB seed: **20,000** VND

**Impact:** If API fetch fails, user sees wrong prices.

**Source:** `PriceSummary.tsx` FALLBACK_PRICES vs `seed_pricing.py` PRICING_DATA

### 10.2 [WARNING] Frontend Discounts Not Applied on Backend

Frontend applies 20% monthly discount and 10% weekly discount. Backend charges flat rate from `package_pricing` table — **no discount logic**.

**Impact:** User sees discounted price on booking form, but backend charges full price. The stored `booking.price` will differ from what user saw.

### 10.3 [WARNING] Checkout Price Recalculation Ignores Package Type

`calculate_checkout_price()` for non-hourly packages falls back to hourly billing:

```python
else:
    billable_hours = math.ceil(total_hours) if total_hours > 0 else 1
    total_amount = billable_hours * hourly_price
```

A monthly booking (1,200,000 VND) that lasts 720 hours would be charged `720 × 15,000 = 10,800,000 VND` at checkout.

**Impact:** Major billing discrepancy for daily/weekly/monthly packages.

### 10.4 [NOTE] Extend Booking Feature — Incomplete

- Model has `extended_until` field
- Celery no-show task sends notification with `actionUrl: /bookings/{id}/extend`
- **NO backend endpoint** implements extend functionality
- **NO frontend page** for extending a booking
- Frontend endpoints.ts has no extend endpoint

### 10.5 [NOTE] Payment Gateway is Mocked

All online payment methods (Momo, VNPay, ZaloPay) generate fake URLs. Cash is auto-completed. No real payment gateway integration exists.

### 10.6 [NOTE] AI Proxy Bypasses Gateway

Nginx routes `/ai/*` directly to `ai-service:8009`, bypassing the Go gateway. This means AI endpoints don't go through gateway auth. The AI service has its own `X-Gateway-Secret` check, but it's a different auth path than the JWT-based gateway auth.

### 10.7 [NOTE] ParkingLot.price_per_hour Not Used

`ParkingLot` model has a `price_per_hour` field (default 10,000) that is never referenced in pricing calculations. All pricing goes through `PackagePricing` table.

---

## 11. Key File Paths

### Booking Service

| File                                                                                 | Purpose                                                                 |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| `backend-microservices/booking-service/bookings/models.py`                           | Booking + PackagePricing models                                         |
| `backend-microservices/booking-service/bookings/serializers.py`                      | CreateBookingSerializer + BookingSerializer                             |
| `backend-microservices/booking-service/bookings/views.py`                            | All booking endpoints (CRUD, checkin, checkout, cancel, payment, stats) |
| `backend-microservices/booking-service/bookings/services.py`                         | Business logic: pricing, checkout calc, payment integration             |
| `backend-microservices/booking-service/bookings/tasks.py`                            | Celery tasks: auto-cancel, no-show detection                            |
| `backend-microservices/booking-service/bookings/urls.py`                             | URL routing                                                             |
| `backend-microservices/booking-service/bookings/management/commands/seed_pricing.py` | Seed pricing data                                                       |

### Payment Service

| File                                                                   | Purpose                                    |
| ---------------------------------------------------------------------- | ------------------------------------------ |
| `backend-microservices/payment-service-fastapi/app/models/payment.py`  | Payment SQLAlchemy model                   |
| `backend-microservices/payment-service-fastapi/app/routers/payment.py` | Payment endpoints (initiate, verify, list) |
| `backend-microservices/payment-service-fastapi/app/schemas/payment.py` | Pydantic schemas                           |

### Parking Service

| File                                                                  | Purpose                                            |
| --------------------------------------------------------------------- | -------------------------------------------------- |
| `backend-microservices/parking-service/infrastructure/models.py`      | ParkingLot, Floor, Zone, CarSlot, Camera models    |
| `backend-microservices/parking-service/infrastructure/views.py`       | Parking CRUD, availability, nearest, update-status |
| `backend-microservices/parking-service/infrastructure/serializers.py` | Parking serializers                                |
| `backend-microservices/parking-service/infrastructure/urls.py`        | DefaultRouter URLs                                 |

### AI Service

| File                                                                | Purpose                                          |
| ------------------------------------------------------------------- | ------------------------------------------------ |
| `backend-microservices/ai-service-fastapi/app/routers/esp32.py`     | ESP32 check-in/out/cash-payment endpoints        |
| `backend-microservices/ai-service-fastapi/app/routers/parking.py`   | Web check-in/out, scan-plate, detect-occupancy   |
| `backend-microservices/ai-service-fastapi/app/routers/detection.py` | License plate + banknote detection               |
| `backend-microservices/ai-service-fastapi/app/utils/image_utils.py` | Plate image saving utilities                     |
| `backend-microservices/ai-service-fastapi/app/config.py`            | Settings (MEDIA_ROOT, model paths, service URLs) |

### Gateway

| File                                                                 | Purpose                             |
| -------------------------------------------------------------------- | ----------------------------------- |
| `backend-microservices/gateway-service-go/internal/router/routes.go` | Route setup + auth middleware       |
| `backend-microservices/gateway-service-go/internal/config/config.go` | Service routing table + CORS config |

### Frontend

| File                                                  | Purpose                     |
| ----------------------------------------------------- | --------------------------- |
| `spotlove-ai/src/pages/BookingPage.tsx`               | 5-step booking wizard       |
| `spotlove-ai/src/pages/PaymentPage.tsx`               | Payment QR + countdown      |
| `spotlove-ai/src/pages/CheckInOutPage.tsx`            | User check-in/out           |
| `spotlove-ai/src/pages/CamerasPage.tsx`               | Camera monitoring           |
| `spotlove-ai/src/components/booking/PriceSummary.tsx` | Price calculation + display |
| `spotlove-ai/src/services/api/booking.api.ts`         | Booking API client          |
| `spotlove-ai/src/services/api/ai.api.ts`              | AI Service API client       |
| `spotlove-ai/src/services/api/endpoints.ts`           | All API endpoint constants  |

### Infrastructure

| File                                                | Purpose                                   |
| --------------------------------------------------- | ----------------------------------------- |
| `backend-microservices/docker-compose.yml`          | All services topology                     |
| `infra/cloudflare/cloudflared/config.yml`           | Main Cloudflare tunnel config             |
| `infra/cloudflare/cloudflared/config-parksmart.yml` | ParkSmart-specific tunnel                 |
| `infra/nginx/nginx.conf`                            | Nginx reverse proxy (API + WS + AI + SPA) |
| `infra/cloudflare/reverse-proxy/api.conf.example`   | Simple API proxy example                  |

---

## 12. Nguồn

| #   | File                                                  | Mô tả                                      |
| --- | ----------------------------------------------------- | ------------------------------------------ |
| 1   | `booking-service/bookings/models.py`                  | Booking + PackagePricing model definitions |
| 2   | `booking-service/bookings/services.py`                | Complete pricing calculation logic         |
| 3   | `booking-service/bookings/serializers.py`             | Booking creation + serialization           |
| 4   | `booking-service/bookings/views.py`                   | All booking endpoints                      |
| 5   | `payment-service-fastapi/app/routers/payment.py`      | Payment initiation + verification          |
| 6   | `docker-compose.yml`                                  | Service topology                           |
| 7   | `spotlove-ai/src/components/booking/PriceSummary.tsx` | Frontend pricing                           |
| 8   | `ai-service-fastapi/app/routers/esp32.py`             | ESP32 check-in/out flow                    |
| 9   | `gateway-service-go/internal/config/config.go`        | Gateway routing table                      |
| 10  | `infra/nginx/nginx.conf`                              | Production nginx config                    |
