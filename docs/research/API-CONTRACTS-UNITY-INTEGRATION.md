# Research Report: Backend Microservices API Contracts cho Unity Integration

**Date:** 2026-04-01 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **Gateway (:8000)** là single entry point — mọi request đi qua `/api/{service_prefix}/...`, gateway inject `X-Gateway-Secret`, `X-User-ID`, `X-User-Email`
> 2. **Auth**: Session cookie (`session_id`) validated bởi gateway qua Redis. Downstream services chỉ check `X-Gateway-Secret` header. Endpoints `auth/` là public, còn lại require auth.
> 3. **Response format**: Parking service dùng **CamelCaseJSONRenderer** (snake_case → camelCase auto). Booking service dùng explicit camelCase field mapping. AI service dùng Pydantic CamelModel.
> 4. **Realtime**: WebSocket tại `ws://host:8006/ws/parking` (public) hoặc `/ws/user/{userId}` (authenticated). Message format: `{ "type": "slot.status_update", "data": {...} }`

---

## 2. GATEWAY SERVICE (Go Gin — `:8000`)

### 2.1 Route Table

| URL Prefix | Target Service | Port | Auth Required |
|---|---|---|---|
| `auth/` | auth-service | 8001 | **NO** (public) |
| `auth/admin/` | auth-service | 8001 | YES |
| `auth/me` | auth-service | 8001 | YES |
| `parking/` | parking-service | 8003 | YES |
| `vehicles/` | vehicle-service | 8004 | YES |
| `bookings/` | booking-service | 8002 | YES |
| `incidents/` | booking-service | 8002 | YES |
| `notifications/` | notification-service | 8005 | YES |
| `realtime/` | realtime-service | 8006 | YES |
| `payments/` | payment-service | 8007 | YES |
| `ai/` | ai-service | 8009 | YES |
| `chatbot/` | chatbot-service | 8008 | YES |

> Path normalization: strips leading `/` and optional `api/` prefix. `/{service_prefix}/health` endpoints bypass auth.

### 2.2 Authentication Flow

```
Client → Cookie: session_id=<uuid>
Gateway → Redis: validate session
Gateway → Inject headers:
  X-User-ID: <uuid>
  X-User-Email: <email>
  X-User-Role: <role>
  X-User-Is-Staff: true|false
  X-Gateway-Secret: <secret>
Gateway → Strip client-supplied X-User-ID, X-Gateway-Secret (prevent injection)
Gateway → Proxy to target service
```

### 2.3 Internal Service Communication Headers

| Header | Description | Source |
|---|---|---|
| `X-Gateway-Secret` | Inter-service auth secret | Gateway injects, env `GATEWAY_SECRET` |
| `X-User-ID` | UUID of authenticated user | Gateway from Redis session |
| `X-User-Email` | Email of authenticated user | Gateway from Redis session |
| `X-User-Role` | User role: `user` / `admin` | Gateway from Redis session |
| `X-User-Is-Staff` | `true` / `false` | Gateway from Redis session |

### 2.4 Downstream Service Auth Check

Django services dùng `IsGatewayAuthenticated` permission class:
```python
# shared/gateway_permissions.py
class IsGatewayAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, 'user_id', None))
```

FastAPI service dùng `GatewayAuthMiddleware` — checks `X-Gateway-Secret` header.

Realtime service internal broadcast endpoints dùng `InternalAuthMiddleware` — checks `X-Gateway-Secret`.

---

## 3. PARKING SERVICE (Django DRF — `:8003`)

> **CamelCase auto-conversion**: Dùng `djangorestframework-camel-case`. Response output: snake_case → camelCase. Request input: camelCase → snake_case.

### 3.1 Models (Hierarchy)

```
ParkingLot (UUID)
  └── Floor (UUID, FK→ParkingLot)
        └── Zone (UUID, FK→Floor, vehicle_type: Car|Motorbike)
              └── CarSlot (UUID, FK→Zone, status: available|occupied|reserved|maintenance)
                    └── Camera (UUID, FK→Zone, optional FK from CarSlot)
```

### 3.2 Endpoints

#### ParkingLot — `/parking/lots/`

| Method | Path | Description | Query Params |
|---|---|---|---|
| GET | `/parking/lots/` | List all lots | `is_open`, `vehicle_type`, `lat`, `lng` |
| POST | `/parking/lots/` | Create lot | — |
| GET | `/parking/lots/{id}/` | Get lot detail | — |
| PUT | `/parking/lots/{id}/` | Update lot | — |
| PATCH | `/parking/lots/{id}/` | Partial update | — |
| DELETE | `/parking/lots/{id}/` | Delete lot | — |
| GET | `/parking/lots/nearest/` | Find nearest lot | `lat` (required), `lng` (required), `vehicle_type` (default: Car), `limit` (default: 5) |
| GET | `/parking/lots/{id}/availability/` | Get real-time availability | — |

**GET `/parking/lots/` Response (camelCase):**
```json
[
  {
    "id": "uuid",
    "name": "string",
    "address": "string",
    "latitude": "10.762622",
    "longitude": "106.660172",
    "totalSlots": 100,
    "availableSlots": 42,
    "pricePerHour": "10000.00",
    "isOpen": true,
    "createdAt": "2026-04-01T00:00:00Z",
    "updatedAt": "2026-04-01T00:00:00Z"
  }
]
```

**GET `/parking/lots/nearest/` Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "name": "string",
      "address": "string",
      "latitude": "10.762622",
      "longitude": "106.660172",
      "totalSlots": 100,
      "availableSlots": 42,
      "pricePerHour": "10000.00",
      "isOpen": true,
      "distance": 0.52,
      "createdAt": "...",
      "updatedAt": "..."
    }
  ],
  "count": 1
}
```

**GET `/parking/lots/{id}/availability/` Response:**
```json
{
  "lotId": "uuid",
  "lotName": "string",
  "total": 100,
  "available": 42,
  "occupied": 50,
  "reserved": 5,
  "maintenance": 3,
  "occupancyRate": 50.0,
  "byVehicleType": {
    "car": {
      "total": 60,
      "available": 25,
      "occupancyRate": 58.3
    },
    "motorbike": {
      "total": 40,
      "available": 17,
      "occupancyRate": 57.5
    }
  }
}
```

#### Floor — `/parking/floors/`

| Method | Path | Description | Query Params |
|---|---|---|---|
| GET | `/parking/floors/` | List floors | `lot_id` |
| POST | `/parking/floors/` | Create floor | — |
| GET | `/parking/floors/{id}/` | Get floor detail (includes nested zones) | — |
| PUT/PATCH | `/parking/floors/{id}/` | Update floor | — |
| DELETE | `/parking/floors/{id}/` | Delete floor | — |

**GET `/parking/floors/` Response (camelCase):**
```json
[
  {
    "id": "uuid",
    "parkingLot": "uuid",
    "level": 1,
    "name": "Floor 1",
    "zones": [
      {
        "id": "uuid",
        "floor": "uuid",
        "floorLevel": 1,
        "name": "Zone A",
        "vehicleType": "Car",
        "capacity": 20,
        "availableSlots": 12,
        "createdAt": "...",
        "updatedAt": "..."
      }
    ],
    "createdAt": "...",
    "updatedAt": "..."
  }
]
```

#### Zone — `/parking/zones/`

| Method | Path | Description | Query Params |
|---|---|---|---|
| GET | `/parking/zones/` | List zones | `lot_id`, `floor_id`, `vehicle_type` |
| POST | `/parking/zones/` | Create zone | — |
| GET | `/parking/zones/{id}/` | Get zone detail | — |
| PUT/PATCH | `/parking/zones/{id}/` | Update zone | — |
| DELETE | `/parking/zones/{id}/` | Delete zone | — |

**Zone Response (camelCase):**
```json
{
  "id": "uuid",
  "floor": "uuid",
  "floorLevel": 1,
  "name": "Zone A",
  "vehicleType": "Car",
  "capacity": 20,
  "availableSlots": 12,
  "createdAt": "...",
  "updatedAt": "..."
}
```

#### CarSlot — `/parking/slots/`

| Method | Path | Description | Query Params |
|---|---|---|---|
| GET | `/parking/slots/` | List slots | `zone_id`, `status`, `vehicle_type` |
| POST | `/parking/slots/` | Create slot | — |
| GET | `/parking/slots/{id}/` | Get slot detail | — |
| PUT/PATCH | `/parking/slots/{id}/` | Update slot | — |
| DELETE | `/parking/slots/{id}/` | Delete slot | — |
| POST | `/parking/slots/check-slots-availability/` | Bulk check slot availability | Body: `{ zone_id, start_time, end_time }` |
| POST | `/parking/slots/{id}/check-availability/` | Single slot availability | Body: `{ start_time, end_time? }` |
| PATCH | `/parking/slots/{id}/update-status/` | Update slot status (internal) | Body: `{ status }` |

**CarSlot Response (camelCase):**
```json
{
  "id": "uuid",
  "zone": "uuid",
  "code": "A-01",
  "status": "available",
  "isAvailable": true,
  "camera": "uuid | null",
  "x1": 100,
  "y1": 200,
  "x2": 300,
  "y2": 400,
  "createdAt": "...",
  "updatedAt": "..."
}
```

**CarSlot status values:** `available`, `occupied`, `reserved`, `maintenance`

**PATCH `/parking/slots/{id}/update-status/` Request:**
```json
{ "status": "occupied" }
```
**Response:**
```json
{
  "slotId": "uuid",
  "oldStatus": "available",
  "newStatus": "occupied",
  "zoneAvailable": 11,
  "lotAvailable": 41,
  "message": "Slot A-01 updated to occupied"
}
```

**POST `/parking/slots/check-slots-availability/` Request:**
```json
{
  "zoneId": "uuid",
  "startTime": "2026-04-01T10:00:00Z",
  "endTime": "2026-04-01T12:00:00Z"
}
```
**Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "zone": "uuid",
      "code": "A-01",
      "status": "available",
      "isAvailable": true,
      "camera": null,
      "x1": 100, "y1": 200, "x2": 300, "y2": 400,
      "createdAt": "...", "updatedAt": "..."
    }
  ],
  "count": 15
}
```

#### Camera — `/parking/cameras/`

| Method | Path | Description | Query Params |
|---|---|---|---|
| GET | `/parking/cameras/` | List cameras | `zone_id`, `floor`, `status` (online/offline) |
| POST | `/parking/cameras/` | Create camera | — |
| GET | `/parking/cameras/{id}/` | Get camera | — |
| GET | `/parking/cameras/{id}/stream/` | Get stream URL | — |

**Camera Response (camelCase):**
```json
{
  "id": "uuid",
  "name": "Camera 1",
  "ipAddress": "192.168.1.100",
  "port": 8080,
  "zone": "uuid | null",
  "streamUrl": "rtsp://...",
  "isActive": true,
  "createdAt": "...",
  "updatedAt": "..."
}
```

---

## 4. BOOKING SERVICE (Django DRF — `:8002`)

> **CamelCase**: Explicit field mapping trong serializers (source='snake_case').

### 4.1 Models

**Booking** — Denormalized (copies data from parking/vehicle/auth services):
```
id: UUID (PK)
user_id: UUID, user_email: string
vehicle_id: UUID, vehicle_license_plate: string, vehicle_type: string
parking_lot_id: UUID, parking_lot_name: string
floor_id: UUID?, floor_level: int?
zone_id: UUID, zone_name: string
slot_id: UUID?, slot_code: string
package_type: hourly|daily|weekly|monthly
start_time: datetime, end_time: datetime?
payment_method: online|on_exit
payment_status: pending|processing|completed|failed|refunded
price: decimal
check_in_status: not_checked_in|checked_in|checked_out|no_show|cancelled
checked_in_at: datetime?, checked_out_at: datetime?
qr_code_data: string (JSON)
hourly_start/hourly_end/extended_until: datetime?
late_fee_applied: bool
```

**PackagePricing:**
```
id: UUID, package_type: hourly|daily|weekly|monthly
vehicle_type: Car|Motorbike, price: decimal, duration_days: int?
```

### 4.2 Endpoints

#### PackagePricing — `/bookings/packagepricings/`

| Method | Path | Description |
|---|---|---|
| GET | `/bookings/packagepricings/` | List all pricing packages |
| POST | `/bookings/packagepricings/` | Create pricing |
| GET | `/bookings/packagepricings/{id}/` | Get pricing detail |
| PUT/PATCH | `/bookings/packagepricings/{id}/` | Update pricing |
| DELETE | `/bookings/packagepricings/{id}/` | Delete pricing |

#### Booking CRUD — `/bookings/`

| Method | Path | Description |
|---|---|---|
| GET | `/bookings/` | List user's bookings |
| POST | `/bookings/` | **Create booking** |
| GET | `/bookings/{id}/` | Get booking detail |
| PUT/PATCH | `/bookings/{id}/` | Update booking |
| DELETE | `/bookings/{id}/` | Delete booking |

#### Booking Actions

| Method | Path | Description |
|---|---|---|
| POST | `/bookings/{id}/checkin/` | **Check-in** (scan QR at entry gate) |
| POST | `/bookings/{id}/checkout/` | **Check-out** (scan QR at exit gate) |
| POST | `/bookings/{id}/cancel/` | **Cancel** booking |
| GET | `/bookings/{id}/qr-code/` | Get QR code |
| GET | `/bookings/current-parking/` | Get current active parking session |
| GET | `/bookings/upcoming/` | Get upcoming bookings |
| GET | `/bookings/stats/` | Get user booking statistics |
| POST | `/bookings/payment/` | Initiate payment (body: `booking_id`) |
| POST | `/bookings/payment/verify/` | Verify payment callback |
| POST | `/bookings/check-slot-bookings/` | Check slot booking conflicts (internal) |

#### Incident Endpoints — `/incidents/`

| Method | Path | Description |
|---|---|---|
| GET | `/incidents/` | List incidents |
| POST | `/incidents/` | Create incident |
| GET | `/incidents/my/` | Get user's incidents |
| GET | `/incidents/nearby-camera/` | Find nearby camera |
| GET | `/incidents/{id}/` | Get incident detail |
| PUT/PATCH | `/incidents/{id}/` | Update incident |
| DELETE | `/incidents/{id}/` | Delete incident |
| POST | `/incidents/{id}/resolve/` | Resolve incident |
| POST | `/incidents/{id}/cancel/` | Cancel incident |
| POST | `/incidents/{id}/request-security/` | Request security |

### 4.3 Request/Response Schemas

**POST `/bookings/` — Create Booking Request (camelCase accepted):**
```json
{
  "vehicleId": "uuid-string",
  "slotId": "uuid | null",
  "zoneId": "uuid",
  "parkingLotId": "uuid",
  "startTime": "2026-04-01T10:00:00Z",
  "endTime": "2026-04-01T12:00:00Z",
  "packageType": "hourly",
  "paymentMethod": "on_exit"
}
```

**POST `/bookings/` — Create Booking Response (201):**
```json
{
  "booking": { /* BookingSerializer output — see below */ },
  "message": "Booking created successfully",
  "qrCode": "{\"booking_id\":\"...\",\"user_id\":\"...\",\"timestamp\":\"...\"}"
}
```

**BookingSerializer Response (camelCase):**
```json
{
  "id": "uuid",
  "userId": "uuid",
  "vehicle": {
    "id": "uuid",
    "licensePlate": "51A-224.56",
    "vehicleType": "Car",
    "name": "51A-224.56"
  },
  "packageType": "hourly",
  "startTime": "2026-04-01T10:00:00Z",
  "endTime": "2026-04-01T12:00:00Z",
  "floor": {
    "id": "uuid",
    "name": "Floor 1",
    "level": 1,
    "parkingLotId": "uuid"
  },
  "zone": {
    "id": "uuid",
    "floorId": "uuid",
    "name": "Zone A",
    "vehicleType": "Car",
    "capacity": 20,
    "availableSlots": 12
  },
  "carSlot": {
    "id": "uuid",
    "zoneId": "uuid",
    "code": "A-01",
    "isAvailable": false
  },
  "parkingLot": {
    "id": "uuid",
    "name": "Bãi xe Trung tâm",
    "address": "123 Nguyễn Huệ",
    "latitude": "10.762622",
    "longitude": "106.660172"
  },
  "paymentType": "on_exit",
  "paymentStatus": "pending",
  "checkInStatus": "not_checked_in",
  "price": "20000.00",
  "checkedInAt": null,
  "checkedOutAt": null,
  "qrCodeData": "{...}",
  "createdAt": "2026-04-01T09:00:00Z",
  "hourlyStart": "2026-04-01T10:00:00Z",
  "hourlyEnd": "2026-04-01T12:00:00Z",
  "extendedUntil": null,
  "lateFeeApplied": false
}
```

**POST `/bookings/{id}/checkin/` — Check-in Response (200):**
```json
{
  "booking": { /* BookingSerializer */ },
  "message": "Check-in successful",
  "checkedInAt": "2026-04-01T10:05:00Z"
}
```

**POST `/bookings/{id}/checkout/` — Check-out Response (200):**
```json
{
  "booking": { /* BookingSerializer */ },
  "message": "Check-out successful",
  "durationHours": 2.08,
  "totalAmount": 30000.00,
  "pricePerHour": 10000.00,
  "lateFee": 0.0,
  "lateFeeApplied": false
}
```

**POST `/bookings/{id}/cancel/` — Cancel Response (200):**
```json
{
  "booking": { /* BookingSerializer */ },
  "message": "Booking cancelled successfully"
}
```

**GET `/bookings/current-parking/` Response (200):**
```json
{
  "booking": { /* BookingSerializer */ },
  "duration": 125,
  "currentCost": 30000.00,
  "hoursParked": 2.08,
  "billableHours": 3,
  "pricePerHour": 10000.00,
  "message": "Current parking session"
}
```

**GET `/bookings/upcoming/` Response:**
```json
{
  "results": [ /* BookingSerializer[] */ ],
  "count": 3,
  "message": "Upcoming bookings"
}
```

**POST `/bookings/check-slot-bookings/` Request (internal service call):**
```json
{
  "slotIds": ["uuid", "uuid"],
  "startTime": "2026-04-01T10:00:00Z",
  "endTime": "2026-04-01T12:00:00Z"
}
```
**Response:**
```json
{
  "bookedSlotIds": ["uuid"],
  "count": 1
}
```

---

## 5. AI SERVICE (FastAPI — `:8009`)

### 5.1 Router: Detection (`/ai/detect/`)

| Method | Path | Description | Content-Type |
|---|---|---|---|
| POST | `/ai/detect/license-plate/` | Detect & OCR license plate | `multipart/form-data` |
| POST | `/ai/detect/cash/` | Recognize cash denomination | `multipart/form-data` |
| POST | `/ai/detect/banknote/` | Classify banknote denomination | `multipart/form-data` |

### 5.2 Router: Parking (`/ai/parking/`)

| Method | Path | Description | Content-Type |
|---|---|---|---|
| POST | `/ai/parking/scan-plate/` | Scan plate only (no booking) | `multipart/form-data` |
| POST | `/ai/parking/check-in/` | QR + plate check-in | `multipart/form-data` |
| POST | `/ai/parking/check-out/` | QR + plate check-out | `multipart/form-data` |
| POST | `/ai/parking/detect-occupancy/` | Camera slot occupancy detection | `multipart/form-data` |

**POST `/ai/parking/scan-plate/` Response:**
```json
{
  "plateText": "51A22456",
  "decision": "ok",
  "confidence": 0.923,
  "detectionConfidence": 0.95,
  "isBlurry": false,
  "blurScore": 12.5,
  "ocrMethod": "trocr",
  "rawCandidates": ["51A-224.56", "51A224.56"],
  "warning": null,
  "message": "Plate detected successfully",
  "processingTimeMs": 245.3
}
```

**POST `/ai/parking/detect-occupancy/` Request:**
```
Form fields:
  - image: File (camera frame)
  - camera_id: string
  - slots: JSON string array of slot bboxes
    [{"slot_id":"uuid","slot_code":"A-01","zone_id":"uuid","x1":0,"y1":0,"x2":100,"y2":100}]
```
**Response (OccupancyDetectionResponse — camelCase):**
```json
{
  "cameraId": "cam-01",
  "totalSlots": 20,
  "totalAvailable": 12,
  "totalOccupied": 8,
  "detectionMethod": "yolo11n",
  "processingTimeMs": 150.5,
  "slots": [
    {
      "slotId": "uuid",
      "slotCode": "A-01",
      "zoneId": "uuid",
      "status": "available",
      "confidence": 0.95,
      "method": "yolo11n_iou"
    }
  ]
}
```

### 5.3 Router: ESP32 (`/ai/parking/esp32/`)

| Method | Path | Description |
|---|---|---|
| POST | `/ai/parking/esp32/check-in/` | ESP32 gate-in: QR scan + plate OCR + barrier control |
| POST | `/ai/parking/esp32/check-out/` | ESP32 gate-out: QR + plate + payment check + barrier |
| POST | `/ai/parking/esp32/verify-slot/` | Slot-level: QR scan + booking→slot match |
| POST | `/ai/parking/esp32/cash-payment/` | Cash inserted → AI denomination detection → accumulate |
| GET | `/ai/parking/esp32/status/` | Health + camera status |
| POST | `/ai/parking/esp32/register` | ESP32 device registration |
| POST | `/ai/parking/esp32/heartbeat` | ESP32 heartbeat |
| POST | `/ai/parking/esp32/log` | ESP32 log entry |
| GET | `/ai/parking/esp32/devices` | List registered devices |
| GET | `/ai/parking/esp32/devices/{device_id}` | Get device detail |
| GET | `/ai/parking/esp32/devices/{device_id}/logs` | Get device logs |

#### ESP32 Check-In Request/Response

**POST `/ai/parking/esp32/check-in/` Request (JSON):**
```json
{
  "gate_id": "GATE-IN-01",
  "qr_data": "{\"booking_id\":\"uuid\",\"user_id\":\"uuid\"}",
  "qr_camera_url": "http://192.168.1.100:8080/video",
  "plate_camera_url": "rtsp://192.168.1.101:554/stream",
  "request_id": "uuid"
}
```
> `qr_data`, `qr_camera_url`, `plate_camera_url`, `request_id` are optional.
> If `qr_data` not provided, server opens QR camera to scan.

**ESP32Response (camelCase — all ESP32 endpoints):**
```json
{
  "success": true,
  "event": "check_in_success",
  "barrierAction": "open",
  "message": "✅ Check-in thành công! Biển số: 51A22456",
  "gateId": "GATE-IN-01",
  "bookingId": "uuid",
  "plateText": "51A22456",
  "amountDue": null,
  "amountPaid": null,
  "processingTimeMs": 3250.5,
  "details": { /* booking-service checkin response */ }
}
```

#### ESP32 Check-Out

**POST `/ai/parking/esp32/check-out/` Request (JSON):**
```json
{
  "gate_id": "GATE-OUT-01",
  "qr_data": null,
  "qr_camera_url": null,
  "plate_camera_url": null,
  "request_id": "uuid"
}
```

#### ESP32 Verify Slot

**POST `/ai/parking/esp32/verify-slot/` Request (JSON):**
```json
{
  "slot_code": "A-01",
  "zone_id": "uuid",
  "gate_id": "SLOT-GATE-01",
  "qr_data": null,
  "qr_camera_url": "http://192.168.1.100:8080/video",
  "request_id": "uuid"
}
```

#### ESP32 Cash Payment

**POST `/ai/parking/esp32/cash-payment/` Request (JSON):**
```json
{
  "booking_id": "uuid",
  "image_base64": "base64-encoded-cash-image",
  "camera_url": "http://192.168.1.102:8080/video",
  "gate_id": "GATE-OUT-01",
  "request_id": "uuid"
}
```

#### Enums

**BarrierAction:** `"open"`, `"close"`, `"no_action"`

**GateEvent:**
| Value | Meaning |
|---|---|
| `check_in_success` | Check-in successful, barrier opens |
| `check_in_failed` | Check-in failed, barrier stays closed |
| `check_out_success` | Check-out successful (paid), barrier opens |
| `check_out_awaiting_payment` | Must pay before exit |
| `check_out_failed` | Check-out failed |
| `verify_slot_success` | Vehicle in correct slot |
| `verify_slot_failed` | Vehicle in wrong slot |

#### ESP32 Device Management

**POST `/ai/parking/esp32/register` Request:**
```json
{
  "device_id": "gate-1",
  "ip": "192.168.1.50",
  "firmware": "1.0",
  "gpio_config": {
    "check_in_pin": 12,
    "check_out_pin": 14
  }
}
```

**POST `/ai/parking/esp32/heartbeat` Request:**
```json
{
  "device_id": "gate-1",
  "status": "ready",
  "wifi_rssi": -45
}
```

**POST `/ai/parking/esp32/log` Request:**
```json
{
  "device_id": "gate-1",
  "level": "info",
  "message": "Check-in button pressed"
}
```

---

## 6. REALTIME SERVICE (Go Gin — `:8006`)

### 6.1 WebSocket Endpoints

| Path | Auth | Auto-Subscribed Topics | Description |
|---|---|---|---|
| `ws://host:8006/ws/parking` | **NO** | `parking_updates` | Public parking lot/zone/slot updates |
| `ws://host:8006/ws/parking/` | **NO** | `parking_updates` | Same (trailing slash supported) |
| `ws://host:8006/ws/user/{userId}` | **YES** | `user_{userId}`, `parking_updates` | User-specific booking/notification updates |
| `ws://host:8006/ws/user/{userId}/` | **YES** | Same | Same (trailing slash supported) |

### 6.2 WebSocket Message Format

**Server → Client:**
```json
{
  "type": "slot.status_update",
  "data": {
    "slotId": "uuid",
    "zoneId": "uuid",
    "status": "occupied",
    "vehicleType": "Car"
  }
}
```

**Client → Server (subscribe/unsubscribe):**
```json
{
  "type": "subscribe",
  "data": { "channel": "parking.zone.{zoneId}" }
}
```
```json
{
  "type": "unsubscribe",
  "data": { "channel": "parking.zone.{zoneId}" }
}
```

### 6.3 Event Types (message `type` field)

| Event Type | Group | Description |
|---|---|---|
| `slot.status_update` | `parking_updates` | Single slot status changed |
| `zone.availability_update` | `parking_updates` | Zone available count changed |
| `lot.availability_update` | `parking_updates` | Lot available count changed |
| `slots.batch_update` | `parking_updates` | Multiple slots updated at once |
| `booking.status_update` | `user_{userId}` | Booking status changed |
| `booking.created` | `user_{userId}` | New booking created |
| `booking.cancelled` | `user_{userId}` | Booking cancelled |
| `parking.cost_update` | `user_{userId}` | Current parking cost updated |
| `notification` | `user_{userId}` | General notification |
| `incident.reported` | `user_{userId}` | Incident reported |
| `incident.resolved` | `user_{userId}` | Incident resolved |

### 6.4 Internal Broadcast API (service-to-service only)

> Requires header: `X-Gateway-Secret`

| Method | Path | Broadcasts To | Event Type |
|---|---|---|---|
| POST | `/api/broadcast/slot-status/` | `parking_updates` | `slot.status_update` |
| POST | `/api/broadcast/zone-availability/` | `parking_updates` | `zone.availability_update` |
| POST | `/api/broadcast/lot-availability/` | `parking_updates` | `lot.availability_update` |
| POST | `/api/broadcast/booking/` | `user_{userId}` | `booking.status_update` (default) |
| POST | `/api/broadcast/notification/` | `user_{userId}` | `notification` |

**POST `/api/broadcast/slot-status/` Request:**
```json
{
  "slotId": "uuid",
  "zoneId": "uuid",
  "status": "occupied",
  "vehicleType": "Car"
}
```

**POST `/api/broadcast/booking/` Request:**
```json
{
  "user_id": "uuid",
  "type": "booking.status_update",
  "data": { /* booking data */ }
}
```

**POST `/api/broadcast/notification/` Request:**
```json
{
  "user_id": "uuid",
  "data": {
    "title": "...",
    "message": "...",
    "type": "info"
  }
}
```

**All broadcast responses (200):**
```json
{ "status": "broadcast sent" }
```

### 6.5 WebSocket Client Subscription Channels

Frontend subscribes to these channels dynamically:
- `parking.lot.{lotId}` — Lot-level updates
- `parking.zone.{zoneId}` — Zone-level slot updates
- `booking.{bookingId}` — Specific booking updates

### 6.6 Connection Management

- Ping/pong: 60s read deadline, client must respond to pings
- Read limit: 4096 bytes per message
- Upgrader allows all origins (dev mode)

---

## 7. ERROR FORMAT

### Django Services (Parking, Booking)

**Validation Error (400):**
```json
{
  "error": "start_time is required"
}
```

**Auth Error (401):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Not Found (404):**
```json
{
  "detail": "Not found."
}
```

### FastAPI Service (AI)

**HTTP Exception:**
```json
{
  "detail": "Error message or object"
}
```

### Gateway

**Service Not Found (404):**
```json
{
  "error": "Service not found",
  "path": "unknown/path/"
}
```

**Service Down (502):**
```json
{
  "error": "Service unavailable",
  "service": "parking"
}
```

---

## 8. PORT SUMMARY

| Service | Port | Tech Stack |
|---|---|---|
| Gateway | 8000 | Go (Gin) |
| Auth | 8001 | Django |
| Booking | 8002 | Django DRF |
| Parking | 8003 | Django DRF |
| Vehicle | 8004 | Django DRF |
| Notification | 8005 | FastAPI |
| Realtime | 8006 | Go (Gin) + WebSocket |
| Payment | 8007 | FastAPI |
| Chatbot | 8008 | FastAPI |
| AI | 8009 | FastAPI |

---

## 9. ⚠️ Gotchas & Notes

- **[NOTE]** Parking service uses `djangorestframework-camel-case` — all responses are auto-converted to camelCase. Requests accept camelCase input.
- **[NOTE]** Booking service uses explicit field mapping (`source='snake_case'`) — response is camelCase, but create request expects **snake_case** (`vehicle_id`, `slot_id`, `zone_id`, `parking_lot_id`, `start_time`, `end_time`, `package_type`, `payment_method`). The CamelCase parser may also accept camelCase.
- **[NOTE]** AI service ESP32 endpoints use **snake_case** in requests (Pydantic BaseModel) but **camelCase** in responses (CamelModel).
- **[NOTE]** WebSocket connects directly to port 8006, NOT through gateway. Gateway does not proxy WebSocket upgrades for `/ws/` paths.
- **[NOTE]** `X-Gateway-Secret` is the universal inter-service auth mechanism. Default dev value: `gateway-internal-secret-key`.
- **[NOTE]** All IDs are UUID v4 format.
- **[NOTE]** DateTime format: ISO 8601 (`2026-04-01T10:00:00Z`).
