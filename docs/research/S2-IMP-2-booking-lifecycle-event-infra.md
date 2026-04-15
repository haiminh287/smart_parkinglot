# Research Report: Booking Lifecycle + Event Infrastructure

**Task:** S2-IMP-2 | **Date:** 2026-04-15 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Tất cả inter-service communication hiện tại là synchronous HTTP** — booking-service `requests.post/patch` trực tiếp tới realtime-service và parking-service trong request path
> 2. **RabbitMQ đã configured trong docker-compose + env vars cho booking-service, NHƯNG không có code nào publish/consume** — pika **không có** trong booking-service requirements.txt (chỉ có ở root `requirements.txt` và `chatbot-service-fastapi`)
> 3. **realtime-service-go không có RabbitMQ consumer code** — 100% REST-based broadcast API, không có AMQP dependency trong go.mod
> 4. **cancel action thiếu slot release + broadcast** — là bug/gap hiện tại

---

## A. Current Lifecycle Flow

### Checkin (`views.py:113-180`)

```
1. Validate check_in_status == "not_checked_in"
2. Validate time (not more than 30min before start_time)
3. booking.check_in_status = "checked_in", booking.checked_in_at = now()
4. booking.save()
5. [HTTP POST sync] → realtime-service /api/broadcast/slot-status/  (status="occupied")
6. [HTTP PATCH sync] → parking-service /parking/slots/{slot_id}/update-status/  (status="occupied")
7. Return response
```

### Checkout (`views.py:182-246`)

```
1. Validate check_in_status == "checked_in"
2. services.validate_checkout(booking)
3. pricing = services.calculate_checkout_price(booking)
4. services.perform_checkout(booking)
5. [HTTP PATCH sync] → parking-service /parking/slots/{slot_id}/update-status/  (status="available")
6. [HTTP POST sync] → realtime-service /api/broadcast/slot-status/  (status="available")
7. Return response with pricing details
```

### Cancel (`views.py:316-333`)

```
1. Validate check_in_status not in ["checked_in", "checked_out"]
2. booking.check_in_status = "cancelled"
3. booking.save()
4. Return response
⚠️ GAP: NO slot release to parking-service
⚠️ GAP: NO broadcast to realtime-service
⚠️ GAP: NO refund processing (TODO comment only)
```

### Create (`views.py:82-111`)

```
1. Validate + save booking
2. [HTTP POST sync] → realtime-service /api/broadcast/slot-status/  (status="reserved")
3. services.create_payment_for_booking(booking)
4. Return response
⚠️ NO parking-service slot status update on create (slot reservation done in serializer)
```

---

## B. All Inter-Service HTTP Calls in views.py

| Line | Method | Target Service | Endpoint | When | Blocking? |
|------|--------|----------------|----------|------|-----------|
| 37 | POST | realtime-service:8006 | `/api/broadcast/slot-status/` | `broadcast_slot_status()` helper | Yes (timeout=2s) |
| 92 | — | (via helper above) | — | `create` action | Yes |
| 147 | — | (via helper above) | — | `checkin` action | Yes |
| 155-166 | PATCH | parking-service:8000 | `/parking/slots/{id}/update-status/` | `checkin` action | Yes (timeout=3s) |
| 215-226 | PATCH | parking-service:8000 | `/parking/slots/{id}/update-status/` | `checkout` action | Yes (timeout=3s) |
| 229 | — | (via helper above) | — | `checkout` action | Yes |

**Also in `services.py`** (called from views):
- `create_payment_for_booking()` → payment-service
- `initiate_payment()` → payment-service
- `get_booking_payments()` → payment-service

**Also in `serializers.py`** (called during create):
- Lines 65, 84, 107, 128, 335 → parking-service GET calls to validate lot/zone/floor/slot

**Also in `tasks.py`** (Celery async, NOT in request path):

| Line | Method | Target Service | Endpoint | Task |
|------|--------|----------------|----------|------|
| 49 | POST | realtime-service | `/api/broadcast/slot-status/` | auto_cancel_unpaid_bookings |
| 66 | PATCH | parking-service | `/parking/slots/{id}/update-status/` | auto_cancel_unpaid_bookings |
| 79-87 | POST | notification-service | `/notifications/` | auto_cancel_unpaid_bookings |
| 118 | POST | auth-service | `/users/{id}/increment-no-show/` | check_no_show_bookings |
| 126-136 | POST | notification-service | `/notifications/` | check_no_show_bookings |

---

## C. Celery Config + Existing Tasks

### Celery Configuration (`booking_service/celery.py`)

```python
app = Celery('booking_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = 'Asia/Ho_Chi_Minh'

# Broker: redis://redis:6379/0 (from docker-compose env)
# Result backend: redis://redis:6379/0

beat_schedule = {
    'auto-cancel-unpaid-bookings-every-minute': {
        'task': 'bookings.tasks.auto_cancel_unpaid_bookings',
        'schedule': 60.0,  # Every 60 seconds
    },
    'check-no-show-bookings-every-5-minutes': {
        'task': 'bookings.tasks.check_no_show_bookings',
        'schedule': 300.0,  # Every 5 minutes
    },
}
```

### Existing Tasks (`bookings/tasks.py`)

| Task | Schedule | What it does |
|------|----------|--------------|
| `auto_cancel_unpaid_bookings` | Every 60s | Cancel online-payment bookings still pending after 15min. Releases slot (parking+realtime), sends notification |
| `check_no_show_bookings` | Every 5min | Mark hourly bookings as no_show if 30min past start with no checkin. Increments user no_show_count, sends notification |

---

## D. RabbitMQ Setup Status

### Docker-Compose: ✅ Configured

```yaml
rabbitmq:
  image: rabbitmq:3-management-alpine
  container_name: parksmartdb_rabbitmq
  environment:
    RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
    RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASS}
  ports: 5672:5672, 15672:15672
  healthcheck: rabbitmq-diagnostics ping
```

### Env Vars for booking-service: ✅ Configured

```
RABBITMQ_URL=amqp://${RABBITMQ_USER}:${RABBITMQ_PASS}@rabbitmq:5672/
RABBITMQ_USER=${RABBITMQ_USER}
RABBITMQ_PASSWORD=${RABBITMQ_PASS}
```

booking-service `depends_on: rabbitmq: condition: service_healthy` ✅

### Pika/AMQP Library: ❌ NOT in booking-service

| File | Has pika/amqp? |
|------|----------------|
| `booking-service/requirements.txt` | ❌ No |
| `chatbot-service-fastapi/requirements.txt` | ✅ `aio-pika==9.4.0` |
| `backend-microservices/requirements.txt` (root) | ✅ `pika==1.3.2` |

**Verdict:** RabbitMQ infrastructure is running, env vars are injected, but **booking-service has no client library and no publish/consume code**.

### Realtime-service-go RabbitMQ: ❌ NOT configured

- `go.mod`: No AMQP/RabbitMQ dependency
- `docker-compose.yml` realtime-service-go env: No `RABBITMQ_URL`
- `internal/`: No consumer code, no AMQP imports
- `cmd/server/main.go`: Pure HTTP + WebSocket, no RabbitMQ setup

---

## E. Realtime-Service Event Reception — How It Works Now

### Architecture: Pure REST → WebSocket Bridge

```
booking-service (or any service)
    │
    │  HTTP POST (sync, in request path)
    │  Headers: X-Gateway-Secret
    ▼
realtime-service-go /api/broadcast/*
    │
    │  hub.Broadcast(group, msgType, data)
    ▼
WebSocket clients (browser/Unity)
    connected to /ws/parking or /ws/user/:userId
```

### Available Broadcast Endpoints (all require X-Gateway-Secret)

| Endpoint | Group | Message Type | Used By |
|----------|-------|-------------|---------|
| `POST /api/broadcast/slot-status/` | `parking_updates` | `slot.status_update` | booking-service, ai-service |
| `POST /api/broadcast/zone-availability/` | `parking_updates` | `zone.availability_update` | parking-service |
| `POST /api/broadcast/lot-availability/` | `parking_updates` | `lot.availability_update` | parking-service |
| `POST /api/broadcast/booking/` | `user_{userId}` | `booking.status_update` | (available but unused) |
| `POST /api/broadcast/notification/` | `user_{userId}` | `notification` | notification-service |
| `POST /api/broadcast/camera-status/` | `parking_updates` | `camera.slot_detection` | ai-service |
| `POST /api/broadcast/unity-command/` | `parking_updates` | `unity.command` | ai-service |

### WebSocket Groups

- `parking_updates` — all connected clients (both `/ws/parking` and `/ws/user/:userId`)
- `user_{userId}` — only user-specific connections (`/ws/user/:userId`)

### Key Observation

**`/api/broadcast/booking/` endpoint EXISTS but is NEVER called from booking-service views.py.** Booking status changes (checkin/checkout/cancel) only broadcast slot status, not booking-level events to the specific user.

---

## F. Recommended Approach: What Needs to Change

### Gaps Identified

| # | Gap | Impact | Priority |
|---|-----|--------|----------|
| 1 | `cancel` action doesn't release slot (parking-service) or broadcast (realtime) | Slot stays "reserved" after cancel, UI shows stale data | **HIGH** |
| 2 | No booking-level event broadcast to user | User's app doesn't update in real-time when booking status changes | **MEDIUM** |
| 3 | All inter-service calls are sync HTTP in request path | If realtime-service or parking-service is slow/down, checkin/checkout latency increases or fails | **MEDIUM** |
| 4 | RabbitMQ infra exists but unused by booking-service | Wasted infrastructure, missed async opportunity | **LOW** (infra ready) |

### Phương án chuyển sang Event-Driven (facts cho Architect)

**Option A: Add RabbitMQ publish in booking-service (full event-driven)**

- Add `pika` to `booking-service/requirements.txt`
- Create publisher module: publish events like `booking.checked_in`, `booking.checked_out`, `booking.cancelled`, `booking.created`
- Add RabbitMQ consumer in realtime-service-go (requires `streadway/amqp` or `rabbitmq/amqp091-go` in go.mod)
- Add RabbitMQ consumer in parking-service for slot updates
- Pros: Decoupled, resilient, retryable
- Cons: Complexity increase, need consumer code in Go + Python, need dead letter queues

**Option B: Keep HTTP but fix gaps + add booking broadcast**

- Fix `cancel` to call parking-service PATCH + realtime broadcast (like checkin/checkout do)
- Add `broadcast_booking_update()` call to `realtime-service /api/broadcast/booking/` for user-level events
- Keep existing pattern consistent
- Pros: Minimal change, consistent with existing approach
- Cons: Still sync, still has timeout/failure coupling

**Option C: Hybrid — Celery tasks for non-critical side effects**

- Keep slot update (parking-service PATCH) synchronous (critical — must succeed)
- Move realtime broadcast + notification to Celery tasks (fire-and-forget)
- Fix cancel gap
- Pros: Uses existing Celery infra, no new deps, isolates non-critical work
- Cons: Celery uses Redis broker (not RabbitMQ), adds latency for WS broadcast

### Codebase Pattern Reference

Chatbot-service đã dùng `aio-pika` — xem `chatbot-service-fastapi/requirements.txt` line 18 cho pattern reference nếu chọn Option A.

---

## 8. Nguồn

| # | File | Mô tả |
|---|------|-------|
| 1 | `booking-service/bookings/views.py` (L1-716) | BookingViewSet — all lifecycle actions |
| 2 | `booking-service/bookings/tasks.py` (L1-140) | Celery tasks — auto-cancel + no-show |
| 3 | `booking-service/booking_service/celery.py` (L1-38) | Celery config + beat schedule |
| 4 | `booking-service/bookings/services.py` (L1-100) | Business logic layer |
| 5 | `booking-service/requirements.txt` | Dependencies — no pika |
| 6 | `realtime-service-go/internal/handler/broadcast.go` | REST broadcast handlers |
| 7 | `realtime-service-go/internal/hub/hub.go` | WebSocket hub — group-based broadcast |
| 8 | `realtime-service-go/internal/handler/ws_handler.go` | WS connection handlers |
| 9 | `realtime-service-go/cmd/server/main.go` | Server setup — routes, no RabbitMQ |
| 10 | `realtime-service-go/go.mod` | Dependencies — no AMQP |
| 11 | `docker-compose.yml` (L50-68, 154-192, 276-295) | RabbitMQ + booking-service + realtime-service config |
