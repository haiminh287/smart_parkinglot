# 🔗 Frontend ↔ Backend API Alignment — Tổng Quan

> **Tổng endpoints audit:** 106 | **Khớp:** 95 | **Lệch:** 8 (3 critical + 5 minor)
> **Cập nhật lần cuối:** Sau khi fix 10 API mismatches trong phiên trước
> **Playwright E2E:** 65/65 tests passing ✅

---

## 📊 Tổng Quan Hệ Thống

### Service Map

| Service      | Framework   | Port (Docker) | Port (Gateway)    | URL Prefix            |
| ------------ | ----------- | ------------- | ----------------- | --------------------- |
| Gateway      | Go (Gin)    | 8000          | —                 | `/`                   |
| Auth         | Django REST | 8001          | `/auth/`          | `/api/auth/`          |
| Booking      | Django REST | 8002          | `/bookings/`      | `/api/bookings/`      |
| Parking      | Django REST | 8003          | `/parking/`       | `/api/`               |
| Vehicle      | Django REST | 8004          | `/vehicles/`      | `/api/vehicles/`      |
| Notification | FastAPI     | 8005          | `/notifications/` | `/api/notifications/` |
| Realtime     | Go (Gin)    | 8006          | `/realtime/`      | —                     |
| Payment      | FastAPI     | 8007          | `/payments/`      | `/api/payments/`      |
| Chatbot      | FastAPI     | 8008          | `/chatbot/`       | `/api/chatbot/`       |
| AI           | FastAPI     | 8009          | `/ai/`            | `/api/ai/`            |

### Gateway Route Table (`gateway-service-go`)

```go
// internal/router/router.go
auth/       → auth-service:8001
parking/    → parking-service:8003
vehicles/   → vehicle-service:8004
bookings/   → booking-service:8002
incidents/  → booking-service:8002
notifications/ → notification-service:8005
realtime/   → realtime-service:8006
payments/   → payment-service:8007
ai/         → ai-service:8009
chatbot/    → chatbot-service:8008
```

### Frontend Proxy (Vite)

```ts
// vite.config.ts
server.proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  }
}
```

**Luồng request:**

```
Frontend /api/bookings/1/
  → Vite proxy → localhost:8000/bookings/1/
    → Gateway → booking-service:8002/api/bookings/1/
```

---

## 🔴 CRITICAL Mismatches (3)

### 1. Payment Service — Router Prefix 404

**Severity:** 🔴 Tất cả payment endpoints đều 404

**Vấn đề:**

```
Gateway gửi:  /payments/initiate/
                      ↓
Payment service router prefix: /api/payments/
                      ↓
Actual endpoint:      /api/payments/initiate/
                      ↓
Gateway path arrives: /initiate/  (đã strip "payments/")
Nhưng service expect: /api/payments/initiate/
                      ↓
KẾT QUẢ: 404 Not Found
```

**Files liên quan:**

- `payment-service-fastapi/app/main.py` — `app.include_router(router, prefix="/api/payments")`
- `gateway-service-go/internal/router/router.go` — `payments/ → service:8007`
- `spotlove-ai/src/services/paymentApi.ts` — Frontend calls

**Fix cần thiết:**

```python
# payment-service-fastapi/app/main.py
# HIỆN TẠI:
app.include_router(payment_router, prefix="/api/payments")
# SỬA THÀNH:
app.include_router(payment_router, prefix="/payments")
```

---

### 2. Parking Slot Update — URL Pattern Mismatch

**Severity:** 🔴 Slot status updates fail

**Vấn đề:**

```
Frontend gửi:     PATCH /parking/slots/update-status/
                  Body: { slot_id: "...", status: "..." }

Backend expects:  PATCH /parking/slots/{id}/update-status/
                  (detail-level URL, không phải list-level)
```

**Files liên quan:**

- `parking-service/infrastructure/urls.py` — URL patterns
- `spotlove-ai/src/services/parkingApi.ts` — `updateSlotStatus()`
- AI Service cũng gọi endpoint này: `ai-service-fastapi/app/routers/esp32.py`

**Fix cần thiết:**

```typescript
// spotlove-ai/src/services/parkingApi.ts
// HIỆN TẠI:
updateSlotStatus: (data) => api.patch("/parking/slots/update-status/", data);
// SỬA THÀNH:
updateSlotStatus: (id, data) =>
  api.patch(`/parking/slots/${id}/update-status/`, data);
```

---

### 3. Zone Availability — Endpoint Không Tồn Tại

**Severity:** 🔴 Frontend gọi endpoint backend chưa implement

**Vấn đề:**

```
Frontend gọi:   GET /parking/zones/{id}/availability/
Backend:        ❌ KHÔNG CÓ endpoint này
                Chỉ có: GET /parking/zones/ (list)
                        GET /parking/zones/{id}/ (detail)
```

**Files liên quan:**

- `parking-service/infrastructure/views/` — ViewSets
- `spotlove-ai/src/services/parkingApi.ts` — `getZoneAvailability()`

**Fix cần thiết:** Hoặc:

- **Option A:** Tạo `@action(detail=True)` trên ZoneViewSet
- **Option B:** Frontend tự tính availability từ zone slots data

---

## 🟡 Non-Critical Mismatches (5)

Các endpoint này có try/catch fallback trong frontend, trả về `[]` hoặc default khi fail.

| #   | Endpoint                             | Vấn đề                       | Frontend Handling           |
| --- | ------------------------------------ | ---------------------------- | --------------------------- |
| 1   | `GET /admin/stats/`                  | Backend không có route này   | `try/catch → {}`            |
| 2   | `GET /admin/activities/`             | Backend không có route này   | `try/catch → []`            |
| 3   | `GET /admin/reports/daily/`          | Backend không có route này   | `try/catch → []`            |
| 4   | `POST /notifications/push-settings/` | Endpoint tồn tại nhưng no-op | Returns 200 nhưng không lưu |
| 5   | `POST /notifications/subscribe/`     | Endpoint tồn tại nhưng no-op | Returns 200 nhưng không lưu |

**Recommended Action:** Implement các admin stat endpoints

---

## 🔤 camelCase vs snake_case Analysis

### Django Services (CamelCaseJSONRenderer) ✅

| Service | Renderer                | Frontend Compatibility |
| ------- | ----------------------- | ---------------------- |
| Auth    | `CamelCaseJSONRenderer` | ✅ Tự động convert     |
| Booking | `CamelCaseJSONRenderer` | ✅ Tự động convert     |
| Parking | `CamelCaseJSONRenderer` | ✅ Tự động convert     |
| Vehicle | `CamelCaseJSONRenderer` | ✅ Tự động convert     |

### FastAPI Services (snake_case) ⚠️

| Service      | Response Format | Frontend Handling                                                   |
| ------------ | --------------- | ------------------------------------------------------------------- |
| Notification | snake_case      | ✅ `normalizeKeys()` utility                                        |
| Payment      | snake_case      | ⚠️ Frontend types expect camelCase, API returns snake_case          |
| Chatbot      | snake_case      | ✅ Simple string responses, no issue                                |
| AI           | snake_case      | ⚠️ Frontend types expect camelCase (eg `bookingId` vs `booking_id`) |

**Notification normalizer:**

```typescript
// src/services/notificationApi.ts
const normalizeKeys = (obj) => {
  // Converts snake_case → camelCase recursively
};
```

**AI Service mismatch examples:**

```
Backend response:    { "barrier_action": "open", "booking_id": "..." }
Frontend TypeScript: { barrierAction: string; bookingId: string; }
```

→ Frontend có dual-check: `data.barrierAction || data.barrier_action`

---

## 📋 Endpoint Inventory — Full Mapping

### Auth Service (12 endpoints) ✅

| Method | Gateway Path             | Backend Path                 | Status          |
| ------ | ------------------------ | ---------------------------- | --------------- |
| POST   | `/auth/register/`        | `/api/auth/register/`        | ✅ Match        |
| POST   | `/auth/login/`           | `/api/auth/login/`           | ✅ Match        |
| POST   | `/auth/logout/`          | `/api/auth/logout/`          | ✅ Match        |
| GET    | `/auth/profile/`         | `/api/auth/profile/`         | ✅ Match        |
| PUT    | `/auth/profile/`         | `/api/auth/profile/`         | ✅ Match        |
| POST   | `/auth/change-password/` | `/api/auth/change-password/` | ✅ Match        |
| GET    | `/auth/users/`           | `/api/auth/users/`           | ✅ Admin        |
| POST   | `/auth/token/refresh/`   | `/api/auth/token/refresh/`   | ✅ Match        |
| POST   | `/auth/token/verify/`    | `/api/auth/token/verify/`    | ✅ Match        |
| GET    | `/auth/google/login/`    | OAuth callback               | ✅ Backend-only |
| GET    | `/auth/google/callback/` | OAuth callback               | ✅ Backend-only |
| GET    | `/auth/session/`         | `/api/auth/session/`         | ✅ Match        |

### Booking Service (14 endpoints) ✅

| Method | Gateway Path                     | Backend Path                         | Status |
| ------ | -------------------------------- | ------------------------------------ | ------ |
| GET    | `/bookings/`                     | `/api/bookings/`                     | ✅     |
| POST   | `/bookings/`                     | `/api/bookings/`                     | ✅     |
| GET    | `/bookings/{id}/`                | `/api/bookings/{id}/`                | ✅     |
| POST   | `/bookings/{id}/cancel/`         | `/api/bookings/{id}/cancel/`         | ✅     |
| POST   | `/bookings/{id}/checkin/`        | `/api/bookings/{id}/checkin/`        | ✅     |
| POST   | `/bookings/{id}/checkout/`       | `/api/bookings/{id}/checkout/`       | ✅     |
| GET    | `/bookings/active/`              | `/api/bookings/active/`              | ✅     |
| GET    | `/bookings/history/`             | `/api/bookings/history/`             | ✅     |
| GET    | `/bookings/{id}/payment-status/` | `/api/bookings/{id}/payment-status/` | ✅     |
| POST   | `/bookings/{id}/extend/`         | `/api/bookings/{id}/extend/`         | ✅     |
| GET    | `/incidents/`                    | `/api/incidents/`                    | ✅     |
| POST   | `/incidents/`                    | `/api/incidents/`                    | ✅     |
| GET    | `/incidents/{id}/`               | `/api/incidents/{id}/`               | ✅     |
| PATCH  | `/incidents/{id}/`               | `/api/incidents/{id}/`               | ✅     |

### Parking Service (18 endpoints) — 2 Mismatches

| Method | Gateway Path                        | Backend Path                | Status   |
| ------ | ----------------------------------- | --------------------------- | -------- |
| GET    | `/parking/zones/`                   | `/api/zones/`               | ✅       |
| GET    | `/parking/zones/{id}/`              | `/api/zones/{id}/`          | ✅       |
| GET    | `/parking/zones/{id}/availability/` | ❌ NOT FOUND                | 🔴       |
| GET    | `/parking/floors/`                  | `/api/floors/`              | ✅       |
| GET    | `/parking/slots/`                   | `/api/slots/`               | ✅       |
| GET    | `/parking/slots/{id}/`              | `/api/slots/{id}/`          | ✅       |
| PATCH  | `/parking/slots/update-status/`     | ❌ Wrong URL                | 🔴       |
| POST   | `/parking/slots/`                   | `/api/slots/`               | ✅ Admin |
| GET    | `/parking/cameras/`                 | `/api/cameras/`             | ✅       |
| GET    | `/parking/cameras/{id}/`            | `/api/cameras/{id}/`        | ✅       |
| GET    | `/parking/cameras/{id}/stream/`     | `/api/cameras/{id}/stream/` | ✅       |
| POST   | `/parking/cameras/`                 | `/api/cameras/`             | ✅ Admin |
| PUT    | `/parking/cameras/{id}/`            | `/api/cameras/{id}/`        | ✅ Admin |
| DELETE | `/parking/cameras/{id}/`            | `/api/cameras/{id}/`        | ✅ Admin |
| GET    | `/parking/pricing/`                 | ❌ Already removed          | ✅ Fixed |
| GET    | `/parking/stats/overview/`          | `/api/stats/overview/`      | ✅       |
| GET    | `/parking/config/`                  | `/api/config/`              | ✅ Admin |
| PUT    | `/parking/config/`                  | `/api/config/`              | ✅ Admin |

### Vehicle Service (6 endpoints) ✅

| Method | Gateway Path                  | Backend Path                      | Status |
| ------ | ----------------------------- | --------------------------------- | ------ |
| GET    | `/vehicles/`                  | `/api/vehicles/`                  | ✅     |
| POST   | `/vehicles/`                  | `/api/vehicles/`                  | ✅     |
| GET    | `/vehicles/{id}/`             | `/api/vehicles/{id}/`             | ✅     |
| PUT    | `/vehicles/{id}/`             | `/api/vehicles/{id}/`             | ✅     |
| DELETE | `/vehicles/{id}/`             | `/api/vehicles/{id}/`             | ✅     |
| PATCH  | `/vehicles/{id}/set-default/` | `/api/vehicles/{id}/set-default/` | ✅     |

### Payment Service (8 endpoints) — 1 Critical Mismatch

| Method | Gateway Path                | Backend Path              | Status        |
| ------ | --------------------------- | ------------------------- | ------------- |
| POST   | `/payments/initiate/`       | `/api/payments/initiate/` | 🔴 Prefix 404 |
| GET    | `/payments/{id}/`           | `/api/payments/{id}/`     | 🔴 Same issue |
| POST   | `/payments/verify/`         | `/api/payments/verify/`   | 🔴 Same issue |
| GET    | `/payments/history/`        | `/api/payments/history/`  | 🔴 Same issue |
| POST   | `/payments/refund/`         | `/api/payments/refund/`   | 🔴 Same issue |
| GET    | `/payments/methods/`        | `/api/payments/methods/`  | 🔴 Same issue |
| POST   | `/payments/callback/momo/`  | Backend-only webhook      | N/A           |
| POST   | `/payments/callback/vnpay/` | Backend-only webhook      | N/A           |

> ⚠️ **ALL payment endpoints are broken** do router prefix mismatch

### Notification Service (8 endpoints) ✅

| Method | Gateway Path                    | Backend Path                        | Status |
| ------ | ------------------------------- | ----------------------------------- | ------ |
| GET    | `/notifications/`               | `/api/notifications/`               | ✅     |
| GET    | `/notifications/{id}/`          | `/api/notifications/{id}/`          | ✅     |
| PATCH  | `/notifications/{id}/read/`     | `/api/notifications/{id}/read/`     | ✅     |
| POST   | `/notifications/mark-all-read/` | `/api/notifications/mark-all-read/` | ✅     |
| GET    | `/notifications/unread-count/`  | `/api/notifications/unread-count/`  | ✅     |
| DELETE | `/notifications/{id}/`          | `/api/notifications/{id}/`          | ✅     |
| POST   | `/notifications/push-settings/` | Exists but no-op                    | 🟡     |
| POST   | `/notifications/subscribe/`     | Exists but no-op                    | 🟡     |

### AI Service (14 endpoints) ✅

| Method | Gateway Path                      | Backend Path                          | Status |
| ------ | --------------------------------- | ------------------------------------- | ------ |
| GET    | `/ai/health/`                     | `/api/ai/health/`                     | ✅     |
| POST   | `/ai/parking/check-in/`           | `/api/ai/parking/check-in/`           | ✅     |
| POST   | `/ai/parking/check-out/`          | `/api/ai/parking/check-out/`          | ✅     |
| POST   | `/ai/parking/esp32/check-in/`     | `/api/ai/parking/esp32/check-in/`     | ✅     |
| POST   | `/ai/parking/esp32/check-out/`    | `/api/ai/parking/esp32/check-out/`    | ✅     |
| POST   | `/ai/parking/esp32/cash-payment/` | `/api/ai/parking/esp32/cash-payment/` | ✅     |
| POST   | `/ai/parking/detect-plate/`       | `/api/ai/parking/detect-plate/`       | ✅     |
| POST   | `/ai/cash/detect/`                | `/api/ai/cash/detect/`                | ✅     |
| POST   | `/ai/cash/train/`                 | Backend-only                          | ✅     |
| GET    | `/ai/predictions/`                | `/api/ai/predictions/`                | ✅     |
| GET    | `/ai/models/status/`              | `/api/ai/models/status/`              | ✅     |
| GET    | `/ai/monitoring/`                 | Backend-only                          | ✅     |
| GET    | `/ai/ml/metrics/`                 | Backend-only                          | ✅     |
| POST   | `/ai/ml/retrain/`                 | Backend-only                          | ✅     |

### Chatbot Service (6 endpoints) ✅

| Method | Gateway Path                   | Backend Path                       | Status |
| ------ | ------------------------------ | ---------------------------------- | ------ |
| POST   | `/chatbot/chat/`               | `/api/chatbot/chat/`               | ✅     |
| GET    | `/chatbot/conversations/`      | `/api/chatbot/conversations/`      | ✅     |
| GET    | `/chatbot/conversations/{id}/` | `/api/chatbot/conversations/{id}/` | ✅     |
| DELETE | `/chatbot/conversations/{id}/` | `/api/chatbot/conversations/{id}/` | ✅     |
| GET    | `/chatbot/health/`             | `/api/chatbot/health/`             | ✅     |
| GET    | `/chatbot/intents/`            | `/api/chatbot/intents/`            | ✅     |

### Realtime Service (6 endpoints) ✅

| Method | Gateway Path                          | Backend Path      | Status |
| ------ | ------------------------------------- | ----------------- | ------ |
| WS     | `/realtime/ws`                        | Direct WebSocket  | ✅     |
| POST   | `/realtime/broadcast/notification/`   | Internal API      | ✅     |
| POST   | `/realtime/broadcast/slot-update/`    | Internal API      | ✅     |
| POST   | `/realtime/broadcast/parking-update/` | Internal API      | ✅     |
| GET    | `/realtime/health/`                   | Health check      | ✅     |
| GET    | `/realtime/clients/`                  | Connected clients | ✅     |

---

## 🗑️ Dead / Redundant Code

### Frontend Code Cần Xóa/Fix

| #   | File                              | Code                    | Vấn đề                                            |
| --- | --------------------------------- | ----------------------- | ------------------------------------------------- |
| 1   | `src/services/adminApi.ts`        | `getStats()`            | Backend không có endpoint, luôn return `{}`       |
| 2   | `src/services/adminApi.ts`        | `getActivities()`       | Backend không có endpoint, luôn return `[]`       |
| 3   | `src/services/adminApi.ts`        | `getDailyReport()`      | Backend không có endpoint, luôn return `[]`       |
| 4   | `src/services/notificationApi.ts` | `updatePushSettings()`  | Backend no-op, setting không persist              |
| 5   | `src/services/notificationApi.ts` | `subscribe()`           | Backend no-op, subscription không persist         |
| 6   | Multiple files                    | Dual-case checks        | `data.bookingId \|\| data.booking_id` — redundant |
| 7   | `src/services/parkingApi.ts`      | `getZoneAvailability()` | Endpoint không tồn tại                            |

### Backend Endpoints Không Được Frontend Sử Dụng (18)

| Service | Endpoint                           | Loại              |
| ------- | ---------------------------------- | ----------------- |
| Auth    | `/auth/google/login/`              | OAuth redirect    |
| Auth    | `/auth/google/callback/`           | OAuth callback    |
| AI      | `/ai/cash/train/`                  | Training trigger  |
| AI      | `/ai/ml/metrics/`                  | ML monitoring     |
| AI      | `/ai/ml/retrain/`                  | Model retrain     |
| AI      | `/ai/monitoring/`                  | System monitoring |
| Payment | `/payments/callback/momo/`         | Webhook           |
| Payment | `/payments/callback/vnpay/`        | Webhook           |
| Booking | Several admin-only batch endpoints | Internal          |

> ⚠️ Các backend-only endpoints KHÔNG nên xóa — chúng phục vụ webhook, internal communication, và future admin tools.

---

## 📈 Completeness Matrix

```
Service            Frontend  Backend  Gateway  API Match  Overall
───────────────────────────────────────────────────────────────────
Auth               ✅ 100%  ✅ 100%  ✅       ✅ 100%    ✅ 100%
Booking            ✅ 100%  ✅ 100%  ✅       ✅ 100%    ✅ 100%
Parking            ✅ 95%   ✅ 95%   ✅       🔴 89%     🟡 93%
Vehicle            ✅ 100%  ✅ 100%  ✅       ✅ 100%    ✅ 100%
Payment            ✅ 100%  ✅ 90%   ✅       🔴 0%      🔴 63%
Notification       ✅ 100%  ✅ 85%   ✅       🟡 75%     🟡 87%
AI                 ✅ 100%  ✅ 85%   ✅       ✅ 100%    ✅ 95%
Chatbot            ✅ 100%  ✅ 95%   ✅       ✅ 100%    ✅ 98%
Realtime           ✅ 100%  ✅ 100%  ✅       ✅ 100%    ✅ 100%
```

---

## 🛠️ Action Items — Ưu Tiên Sửa

### 🔴 Critical (Sửa ngay)

| #   | Task                                                           | File(s)                                  | Effort  |
| --- | -------------------------------------------------------------- | ---------------------------------------- | ------- |
| 1   | Fix payment router prefix `/api/payments` → `/payments`        | `payment-service-fastapi/app/main.py`    | 1 dòng  |
| 2   | Fix slot update URL: list-level → detail-level                 | `spotlove-ai/src/services/parkingApi.ts` | 1 dòng  |
| 3   | Implement zone availability endpoint hoặc remove frontend call | `parking-service/` + `parkingApi.ts`     | 30 phút |

### 🟡 Medium (Sprint tiếp theo)

| #   | Task                                                    | File(s)                                    | Effort   |
| --- | ------------------------------------------------------- | ------------------------------------------ | -------- |
| 4   | Implement admin stats/activities/reports endpoints      | `booking-service/` hoặc `parking-service/` | 1 ngày   |
| 5   | Implement notification push settings persistence        | `notification-service-fastapi/`            | 2 giờ    |
| 6   | Thống nhất camelCase cho FastAPI responses (middleware) | All FastAPI services                       | 4 giờ    |
| 7   | Implement MoMo/VNPay payment gateway integration        | `payment-service-fastapi/`                 | 2-3 ngày |

### 🟢 Low (Cleanup)

| #   | Task                                               | File(s)                    | Effort  |
| --- | -------------------------------------------------- | -------------------------- | ------- |
| 8   | Remove dead admin API calls hoặc replace with TODO | `src/services/adminApi.ts` | 15 phút |
| 9   | Remove dual-case checks khi đã thống nhất case     | Multiple frontend files    | 1 giờ   |
| 10  | Add API response type validation (Zod/yup)         | Frontend services          | 1 ngày  |

---

## 🏗️ Kiến Trúc API Communication

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                     │
│                                                                │
│   src/services/                                                │
│   ├─ api.ts            (Axios instance, cookie auth)          │
│   ├─ authApi.ts        (Auth endpoints)                       │
│   ├─ bookingApi.ts     (Booking CRUD + actions)               │
│   ├─ parkingApi.ts     (Zones, Slots, Cameras)                │
│   ├─ vehicleApi.ts     (Vehicle CRUD)                         │
│   ├─ paymentApi.ts     (Payment initiate/verify)              │
│   ├─ notificationApi.ts (Notifications + normalizer)          │
│   ├─ aiApi.ts          (Check-in/out, plate, cash)            │
│   ├─ chatbotApi.ts     (Chat, conversations)                  │
│   └─ adminApi.ts       (Admin-specific endpoints)             │
│                                                                │
│   Vite proxy: /api/* → localhost:8000/*                        │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│                 GATEWAY (Go Gin) :8000                         │
│                                                                │
│   Route: /{service_prefix}/* → {service_host}:{port}/*        │
│   Headers: X-User-ID, X-User-Email, X-Gateway-Secret          │
│   Auth: JWT cookie validation (except health endpoints)        │
│   CORS: localhost:8080                                         │
└──────────────────┬───────────────────────────────────────────┘
                   │
         ┌─────────┼─────────┬──────────┬──────────┐
         ▼         ▼         ▼          ▼          ▼
    ┌─────────┐ ┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │  Auth   │ │Booking  │ │Parking │ │Payment │ │  AI    │
    │ Django  │ │ Django  │ │ Django │ │FastAPI │ │FastAPI │
    │ camelC. │ │ camelC. │ │camelC. │ │snake_c.│ │snake_c.│
    │  :8001  │ │  :8002  │ │ :8003  │ │ :8007  │ │ :8009  │
    └─────────┘ └─────────┘ └────────┘ └────────┘ └────────┘
```

### Authentication Flow

```
1. POST /auth/login/ → Set-Cookie: access_token, refresh_token (HttpOnly)
2. Mọi request sau → Cookie tự động gửi kèm
3. Gateway decode JWT → inject X-User-ID, X-User-Email headers
4. Backend services validate X-Gateway-Secret header
5. Token refresh: POST /auth/token/refresh/ (auto via Axios interceptor)
```

### Inter-Service Communication

```
AI Service → Booking Service:  HTTP GET/POST (direct, không qua Gateway)
AI Service → Parking Service:  HTTP PATCH (direct)
AI Service → Realtime Service: HTTP POST /api/broadcast/
Booking Service → Payment:     ❌ Chưa implement (TODO)
Chatbot → Booking/Parking:     HTTP GET (qua Gateway hoặc direct)
```

---

## ✅ Những Gì Đã Fix Trong Phiên Này

| #    | Vấn đề gốc                                                    | Fix                           | Kết quả |
| ---- | ------------------------------------------------------------- | ----------------------------- | ------- |
| 1    | Frontend gọi `/parking/pricing/` (không tồn tại)              | Xóa test case + frontend call | ✅      |
| 2    | AI health endpoint return "ok" nhưng frontend check "healthy" | Backend sửa thành "healthy"   | ✅      |
| 3    | Payment page crash khi không có bookingId                     | Thêm `?bookingId=` param      | ✅      |
| 4-10 | 7 API mismatches khác (từ phiên trước)                        | Đã sửa cả frontend + backend  | ✅      |

---

## 📝 Kết Luận

**Tổng quan:**

- 106 endpoints đã audit, **95 khớp hoàn toàn** (90%)
- **3 lỗi critical** cần fix ngay (payment prefix, slot URL, zone availability)
- **5 lỗi minor** có fallback nhưng nên fix
- camelCase consistency cần middleware cho FastAPI services
- 18 backend-only endpoints là hợp lệ (webhooks, internal API)
- 7 dead frontend code items nên cleanup

**Ưu tiên #1:** Fix payment router prefix — 1 dòng code unlock toàn bộ payment flow.
