# 🏗️ REVIEW REPORT: Unity Digital Twin Implementation Plan v2

**Reviewer:** Architect Agent  
**Date:** 2026-04-01  
**Source:** `implementation_plan.md` cross-referenced with `docs/research/API-CONTRACTS-UNITY-INTEGRATION.md`  
**Status:** Review Complete — Significant Issues Found

---

## 1. Tổng Điểm Đánh Giá

| Tiêu chí | Điểm | Ghi chú |
|-----------|-------|---------|
| Architecture & Structure | 8/10 | Tốt: layered, mock mode, connection state machine |
| API Accuracy | 3/10 | Port sai, booking params sai, thiếu vehicle service, thiếu DTOs |
| Data Flow Completeness | 5/10 | ESP32 flow thiếu verify-slot, cash-payment; WS events thiếu |
| Auth Strategy | 2/10 | Không giải thích flow, không rõ direct vs gateway |
| Code Completeness | 5/10 | Thiếu DTOs, ApiConfig, WaypointNode/Graph scripts |
| Error Handling | 6/10 | Có state machine tốt, nhưng thiếu xử lý error format khác nhau giữa services |
| Testing Strategy | 7/10 | Phase-by-phase OK, integration test rõ ràng |
| Feasibility | 7/10 | Khả thi nhưng cần sửa nhiều chi tiết |

### **Tổng: 43/100** — Cần sửa đáng kể trước khi implement

> Plan có kiến trúc tổng thể tốt (mock mode, state machine, waypoint graph, multi-floor) nhưng **chi tiết API integration sai lệch nghiêm trọng** so với backend thật. Implement theo plan hiện tại sẽ fail ngay khi gọi API.

---

## 2. Danh Sách Bugs / Sai Lệch

### BUG-01: Port Parking Service Sai ❌ CRITICAL

| | Plan | Thực Tế |
|---|---|---|
| Parking Service | `parkingServicePort = 8001` | **Port 8003** |
| Auth Service | Không mention | **Port 8001** |

**Impact:** Mọi API call tới parking service sẽ fail hoặc gọi nhầm auth service.

**Fix:** Cập nhật `ApiService.cs` config:
```
parkingServicePort = 8003
authServicePort = 8001
vehicleServicePort = 8004
```

---

### BUG-02: Booking API Parameters Hoàn Toàn Sai ❌ CRITICAL

**Plan ghi:**
```
CreateBooking(plate, vehicleType, slotCode, duration) → BookingData
```

**API thật (POST `/bookings/`):**
```json
{
  "vehicleId": "uuid",          // ← UUID, KHÔNG phải plate string
  "slotId": "uuid | null",      // ← UUID, KHÔNG phải slotCode string
  "zoneId": "uuid",             // ← THIẾU trong plan
  "parkingLotId": "uuid",       // ← THIẾU trong plan
  "startTime": "ISO-8601",      // ← THIẾU, plan dùng "duration"
  "endTime": "ISO-8601",        // ← THIẾU
  "packageType": "hourly",      // ← THIẾU
  "paymentMethod": "on_exit"    // ← THIẾU
}
```

**Impact:** BookingTestPanel không thể tạo booking. Toàn bộ booking flow fail.

**Fix:** 
1. Cần vehicle-service (port 8004) để lấy `vehicleId` từ license plate
2. Cần parking-service data để resolve `slotId`, `zoneId`, `parkingLotId` từ UI selection
3. Cần thêm time picker cho `startTime`/`endTime`
4. Cần dropdown cho `packageType` và `paymentMethod`

---

### BUG-03: Booking Request Case Convention ⚠️ MEDIUM

**API Contracts ghi rõ:**
> Booking service create request expects **snake_case** (`vehicle_id`, `slot_id`, `zone_id`...).  
> CamelCase parser **may** also accept camelCase — chưa kiểm chứng 100%.

**Plan:** Không đề cập convention nào.

**Fix:** Unity nên gửi **camelCase** (vì CamelCase parser có), nhưng cần fallback test với snake_case nếu fail. Ghi rõ trong implementation guide.

---

### BUG-04: ESP32 Check-In Request Body Thiếu Fields ⚠️ MEDIUM

**Plan:**
```json
{ "gate_id": "GATE-IN-01" }
```

**API thật (tất cả optional nhưng nên gửi):**
```json
{
  "gate_id": "GATE-IN-01",
  "qr_data": "{\"booking_id\":\"uuid\"}",      // ← optional
  "qr_camera_url": "http://...",                // ← optional  
  "plate_camera_url": "rtsp://...",             // ← optional
  "request_id": "uuid"                          // ← optional, for idempotency
}
```

**Impact:** Simulator không thể test QR scan flow trực tiếp. Thiếu `request_id` cho idempotency.

---

### BUG-05: Slot API Field Name Mismatch ⚠️ MEDIUM

**API response trả:** `"code": "A-01"` (field tên `code`)  
**Plan dùng khắp nơi:** `slotCode`

**Fix:** DTO cần `[JsonProperty("code")] public string SlotCode;` hoặc thống nhất dùng `code`.

---

### BUG-06: BookingTestPanel UI Fields Sai ❌ HIGH

**Plan:**
```
InputField: licensePlate
Dropdown: slotCode (string)
Dropdown: duration (1h/2h/4h/daily)
```

**Cần:**
```
InputField: licensePlate → resolve to vehicleId via vehicle-service
Dropdown: parkingLot → resolve to parkingLotId
Dropdown: floor → filter zones
Dropdown: zone → resolve to zoneId  
Dropdown: slot → resolve to slotId (UUID)
DateTimePicker: startTime, endTime
Dropdown: packageType (hourly/daily/weekly/monthly)
Dropdown: paymentMethod (online/on_exit)
```

---

## 3. Danh Sách Gaps (Thiếu so với Backend)

### GAP-01: Vehicle Service Hoàn Toàn Không Được Mention ❌ CRITICAL

**Backend có:** Vehicle service tại port 8004  
**Gateway route:** `vehicles/` → vehicle-service:8004  
**Cần cho:** Booking flow (phải có `vehicleId`)

**Required endpoints:**
```
GET  /vehicles/          → List user's vehicles
POST /vehicles/          → Create vehicle { licensePlate, vehicleType, name }
GET  /vehicles/{id}/     → Get vehicle detail
```

**Fix:** Thêm `vehicleServicePort = 8004` vào ApiService config. Thêm vehicle CRUD wrappers. BookingTestPanel cần vehicle selector hoặc auto-create vehicle.

---

### GAP-02: Auth Flow Không Được Giải Thích ❌ CRITICAL

Plan mention `gatewaySecret = "gateway-internal-secret-key"` nhưng **không giải thích Unity dùng nó thế nào**.

**Backend auth flow:**
```
Normal client: Cookie session_id → Gateway validates via Redis → injects X-User-ID etc.
Internal service: X-Gateway-Secret header → services trust it
```

**Câu hỏi chưa trả lời:**
1. Unity đi qua Gateway hay gọi trực tiếp services?
2. Nếu qua Gateway → cần login flow (POST /auth/login → session cookie)
3. Nếu trực tiếp → cần inject `X-Gateway-Secret` + `X-User-ID` headers

**Đề xuất Architecture Decision:**

| Strategy | Pros | Cons |
|----------|------|------|
| **A: Qua Gateway (Recommended)** | Đúng flow, security nhất quán | Cần implement login, manage cookie |
| **B: Direct với X-Gateway-Secret** | Đơn giản hơn, skip auth | Bypass security, Unity becomes trusted service |
| **C: Hybrid** | Gateway cho booking/vehicle, direct cho ESP32/AI | Phức tạp nhưng linh hoạt |

**Recommendation: Strategy C — Hybrid:**
- **Qua Gateway (:8000):** Booking, Vehicle, Parking (cần user context)
- **Direct tới AI (:8009):** ESP32 check-in/check-out (ESP32 thật cũng gọi trực tiếp)
- **Direct tới Realtime (:8006):** WebSocket (WS không qua gateway theo design)

**Unity Auth Flow cần implement:**
```
1. Login: POST http://localhost:8000/auth/login/ { email, password }
   → Response sets session_id cookie
2. Store cookie, attach to all Gateway requests
3. ESP32 calls: attach X-Gateway-Secret header (direct to AI service)
4. WS: connect directly to ws://localhost:8006/ws/parking (public, no auth)
```

---

### GAP-03: WebSocket Events Thiếu Nhiều ⚠️ HIGH

**Plan chỉ handle:**
- `slot.status_update`
- `zone.availability_update`

**Backend broadcast đầy đủ:**

| Event | Importance cho Unity | Plan có? |
|-------|---------------------|----------|
| `slot.status_update` | ★★★ Core | ✅ |
| `zone.availability_update` | ★★★ Dashboard stats | ✅ |
| `lot.availability_update` | ★★☆ Dashboard | ❌ |
| `slots.batch_update` | ★★★ Multiple slot changes | ❌ |
| `booking.created` | ★★☆ Visual feedback | ❌ |
| `booking.cancelled` | ★★☆ Slot revert | ❌ |
| `booking.status_update` | ★★☆ Status tracking | ❌ |
| `parking.cost_update` | ★☆☆ Nice-to-have | ❌ |
| `notification` | ★☆☆ Optional | ❌ |

**Fix:** Thêm event handlers cho ít nhất: `lot.availability_update`, `slots.batch_update`, `booking.created`, `booking.cancelled`.

---

### GAP-04: ESP32 Flows Thiếu ⚠️ HIGH

**Plan có:** check-in, check-out  
**Backend có thêm:**

| Endpoint | Mô tả | Importance |
|----------|--------|-----------|
| `POST /esp32/verify-slot/` | Xác minh xe đúng slot (QR scan tại slot) | ★★☆ |
| `POST /esp32/cash-payment/` | Trả tiền mặt (AI nhận diện tiền) | ★★★ |
| `POST /esp32/register` | Đăng ký ESP32 device | ★☆☆ |
| `POST /esp32/heartbeat` | ESP32 heartbeat | ★★☆ |
| `POST /esp32/log` | Log từ ESP32 | ★☆☆ |
| `GET /esp32/devices` | List devices | ★★☆ |
| `GET /esp32/status/` | Health check | ★★☆ |

**Đặc biệt:** `cash-payment` flow quan trọng vì là flow xuất xe khi chưa thanh toán online:
```
check-out → barrierAction: "close", event: "check_out_awaiting_payment"
  → cash-payment (multiple times until amountPaid >= amountDue)
  → barrier opens
```

---

### GAP-05: C# DTOs Hoàn Toàn Thiếu ❌ HIGH

Plan mô tả data flow bằng text nhưng **không có 1 dòng C# DTO** nào. Implementer sẽ phải tự đoán field names.

**Cần tối thiểu:**

```
DataModels.cs (hoặc tách file):
├── LotData                 ← GET /parking/lots/
├── LotAvailability         ← GET /parking/lots/{id}/availability/
├── FloorData               ← GET /parking/floors/ (with nested zones)
├── ZoneData                ← Zone object in floor response
├── SlotData                ← GET /parking/slots/
├── CameraData              ← GET /parking/cameras/
├── BookingData             ← BookingSerializer response
├── BookingCreateRequest    ← POST /bookings/ request
├── BookingCreateResponse   ← POST /bookings/ response (booking + message + qrCode)
├── CheckInResponse         ← POST /bookings/{id}/checkin/
├── CheckOutResponse        ← POST /bookings/{id}/checkout/
├── VehicleData             ← Vehicle from vehicle-service
├── ESP32Request            ← POST /esp32/check-in/ request
├── ESP32Response           ← All ESP32 responses
├── CashPaymentRequest      ← POST /esp32/cash-payment/
├── WsMessage               ← WebSocket message { type, data }
├── SlotStatusUpdate        ← WS slot.status_update data
├── ZoneAvailabilityUpdate  ← WS zone.availability_update data
├── LotAvailabilityUpdate   ← WS lot.availability_update data
├── SlotsStatusBatchUpdate  ← WS slots.batch_update data
├── PackagePricing          ← GET /bookings/packagepricings/
├── PlateScanResult         ← POST /ai/parking/scan-plate/
├── SlotUpdateStatusResponse ← PATCH /parking/slots/{id}/update-status/
└── ErrorResponse           ← Error format per service
```

---

### GAP-06: Scripts Thiếu Trong File List ⚠️ HIGH

Plan liệt kê 13/14 scripts nhưng **thiếu các scripts quan trọng:**

| Script cần thêm | Lý do |
|------------------|-------|
| `DataModels.cs` | DTOs cho toàn bộ API responses |
| `ApiConfig.cs` | Centralized port/URL/header config (thay vì hardcode trong ApiService) |
| `WaypointNode.cs` | MonoBehaviour cho waypoint node (plan mô tả nhưng không list) |
| `WaypointGraph.cs` | ScriptableObject cho adjacency list (plan mô tả nhưng không list) |
| `AuthManager.cs` | Login flow, cookie management, header injection |
| `VehicleService.cs` hoặc integrate vào `ApiService.cs` | Vehicle CRUD wrappers |

---

### GAP-07: Unity Package Install Steps Thiếu ⚠️ MEDIUM

Plan mention trong bảng nhưng **Phase 1 (Project Setup) không có install commands:**

| Package | Registry | Cách install |
|---------|----------|-------------|
| `com.unity.nuget.newtonsoft-json` | Unity Registry | Package Manager |
| NativeWebSocket | GitHub | manifest.json scopedRegistry hoặc .unitypackage |
| `com.unity.inputsystem` | Unity Registry | Package Manager (nếu dùng new Input System) |
| `com.unity.textmeshpro` | Unity Registry | Thường có sẵn, cần import TMP Essentials |

---

### GAP-08: Error Response Format Khác Nhau Giữa Services ⚠️ MEDIUM

| Service | Error Format |
|---------|-------------|
| Django (Parking, Booking) | `{"error": "..."}` hoặc `{"detail": "..."}` |
| FastAPI (AI) | `{"detail": "..."}` |
| Gateway | `{"error": "...", "service": "...", "path": "..."}` |

**Plan:** Không đề cập. `ApiService.cs` cần unified error parser:
```csharp
string ParseErrorMessage(string responseBody, int statusCode) {
    // Try "error" field first, then "detail", then generic
}
```

---

### GAP-09: Pagination Không Được Handle ⚠️ MEDIUM

API list endpoints (slots, floors, bookings) likely return paginated responses. Plan mô tả `GET /parking/slots/` nhưng **không handle pagination**.

**Fix:** 
- Initial load: fetch all pages hoặc use `?limit=1000` nếu backend support
- Hoặc filter by lot_id/zone_id để limit response size

---

### GAP-10: Slot Availability Check Trước Booking ⚠️ MEDIUM

Backend có endpoint:
```
POST /parking/slots/check-slots-availability/
Body: { zoneId, startTime, endTime }
```

Plan không mention. BookingTestPanel nên dùng endpoint này để populate slot dropdown với chỉ available slots.

---

## 4. Danh Sách Improvements Cần Thiết

### IMP-01: Centralized API Config (Priority: HIGH)

**Hiện tại:** Hardcoded ports trong ApiService Inspector  
**Cần:** `ApiConfig.cs` (ScriptableObject) chứa toàn bộ config

```csharp
[CreateAssetMenu(fileName = "ApiConfig", menuName = "ParkingSim/API Config")]
public class ApiConfig : ScriptableObject {
    [Header("Gateway")]
    public string gatewayBaseUrl = "http://localhost:8000";
    public string gatewaySecret = "gateway-internal-secret-key";
    
    [Header("Direct Services (bypass gateway)")]
    public string aiServiceUrl = "http://localhost:8009";
    public string realtimeWsUrl = "ws://localhost:8006/ws/parking";
    
    [Header("Auth")]
    public string testEmail = "test@example.com";
    public string testPassword = "password";
    
    [Header("Polling")]
    public float lightPollInterval = 2f;
    public float deltaPollInterval = 5f;
    public float heartbeatInterval = 30f;
    
    [Header("Target Lot")]
    public string targetParkingLotId = "";  // UUID of lot to simulate
}
```

---

### IMP-02: Auth Manager Module (Priority: HIGH)

Cần `AuthManager.cs` riêng:

```
AuthManager.cs:
├── Login(email, password) → session cookie
├── IsAuthenticated → bool
├── GetAuthHeaders() → Dictionary<string, string>
│   ├── Nếu qua Gateway: { "Cookie": "session_id=..." }
│   └── Nếu direct: { "X-Gateway-Secret": "...", "X-User-ID": "..." }
├── Logout()
└── Auto-refresh session nếu expired
```

---

### IMP-03: API Request Routing (Priority: HIGH)

Thêm logic routing rõ ràng:

```
Through Gateway (:8000):          Direct:
├── /parking/*                     ├── /ai/parking/esp32/* → :8009
├── /bookings/*                    └── ws://...:8006/ws/parking
├── /vehicles/*
└── /auth/*
```

---

### IMP-04: ESP32 Simulator Mở Rộng (Priority: MEDIUM)

Thêm vào ESP32Simulator.cs:

```
├── VERIFY-SLOT Flow:
│   ├── InputField: slotCode + zoneId
│   ├── [VERIFY] → POST /ai/parking/esp32/verify-slot/
│   ├── Response: verify_slot_success / verify_slot_failed
│   └── Visual: slot flash green/red
│
├── CASH-PAYMENT Flow:
│   ├── Display: amountDue from check-out response
│   ├── [INSERT CASH] → POST /ai/parking/esp32/cash-payment/
│   ├── Response: accumulated amount, remaining
│   ├── Repeat until amountPaid >= amountDue
│   └── Barrier opens when paid
│
├── DEVICE MANAGEMENT:
│   ├── Auto-register on start: POST /esp32/register
│   ├── Heartbeat coroutine: POST /esp32/heartbeat every 30s
│   └── Log events: POST /esp32/log
│
├── STATUS DISPLAY:
│   └── GET /esp32/status/ → health + camera status
```

---

### IMP-05: Polling Filter by Lot (Priority: MEDIUM)

**Hiện tại:** `GET /parking/slots/` → ALL slots across ALL lots  
**Cần:** `GET /parking/slots/?zone_id={zoneId}` hoặc pre-filter

Plan cần thêm `targetParkingLotId` concept — Unity chỉ simulate 1 lot, chỉ poll data cho lot đó.

---

### IMP-06: WebSocket Channel Subscription (Priority: MEDIUM)

Backend supports dynamic channel subscription:
```json
{ "type": "subscribe", "data": { "channel": "parking.lot.{lotId}" } }
```

Unity nên subscribe specific lot/zone channels thay vì nhận ALL updates:
```
On connect → subscribe("parking.lot.{targetLotId}")
Per zone   → subscribe("parking.zone.{zoneId}")
```

---

## 5. Updated Script List

```
ParkingSimulatorUnity/Assets/Scripts/
├── API/
│   ├── ApiConfig.cs              ← 🆕 ScriptableObject: URLs, ports, secrets, polling config
│   ├── ApiService.cs             ← HTTP + WS + retry (FIX: correct ports, routing)
│   ├── AuthManager.cs            ← 🆕 Login, cookie management, header injection
│   ├── MockDataProvider.cs       ← Offline mock data
│   └── DataModels.cs             ← 🆕 ALL C# DTOs with [JsonProperty] annotations
├── Parking/
│   ├── ParkingSlot.cs
│   ├── ParkingLotGenerator.cs    ← Multi-floor + waypoint graph
│   ├── ParkingManager.cs
│   └── FloorVisibilityManager.cs
├── Vehicle/
│   ├── VehicleController.cs      ← Waypoint navigation
│   └── VehicleQueue.cs           ← Spawn queue
├── Navigation/
│   ├── WaypointNode.cs           ← 🆕 MonoBehaviour: position + connections
│   └── WaypointGraph.cs          ← 🆕 ScriptableObject: adjacency list + BFS
├── Gate/
│   └── BarrierController.cs
├── IoT/
│   └── ESP32Simulator.cs         ← FIX: thêm verify-slot, cash-payment, device mgmt
├── Camera/
│   ├── ParkingCameraController.cs
│   └── GarageCameraSimulator.cs
└── UI/
    ├── DashboardUI.cs
    └── BookingTestPanel.cs       ← FIX: correct booking fields

Tổng: 18 scripts (tăng từ 13, thêm 5 scripts mới)
```

### Scripts mới chi tiết:

| Script | Type | Responsibility |
|--------|------|---------------|
| `ApiConfig.cs` | ScriptableObject | Centralized config: URLs, secrets, polling intervals, target lot ID |
| `AuthManager.cs` | MonoBehaviour | Login/logout, session cookie, auth headers, auto-refresh |
| `DataModels.cs` | Plain C# classes | 20+ DTO classes với `[JsonProperty]` annotations |
| `WaypointNode.cs` | MonoBehaviour | Node position, connections list, Gizmo drawing |
| `WaypointGraph.cs` | ScriptableObject | Adjacency list, BFS pathfinding, node registry |

---

## 6. Updated API Integration Strategy

### 6.1 Auth Flow (Mới)

```
┌─────────────────────────────────────────────────────┐
│                    UNITY STARTUP                     │
├─────────────────────────────────────────────────────┤
│ 1. Load ApiConfig (ScriptableObject)                │
│ 2. AuthManager.Login(email, password)               │
│    → POST http://localhost:8000/auth/login/          │
│    → Store session_id cookie                         │
│ 3. If login fail → switch to Mock Mode              │
│ 4. Connect WebSocket (direct, no auth needed):      │
│    → ws://localhost:8006/ws/parking                  │
│    → Subscribe: parking.lot.{targetLotId}            │
│ 5. Initial data load (through Gateway):             │
│    → GET /parking/lots/{id}/ → lot info              │
│    → GET /parking/floors/?lot_id={id} → floors+zones │
│    → GET /parking/slots/?zone_id={id} → per zone     │
│ 6. Start polling + listen WS events                 │
└─────────────────────────────────────────────────────┘
```

### 6.2 Request Routing Matrix

| Action | Route Through | URL Pattern | Auth Header |
|--------|--------------|-------------|-------------|
| Login | Gateway :8000 | `/auth/login/` | None (public) |
| Get lots/floors/zones/slots | Gateway :8000 | `/parking/*` | Cookie: session_id |
| Create/list vehicles | Gateway :8000 | `/vehicles/*` | Cookie: session_id |
| Create/manage bookings | Gateway :8000 | `/bookings/*` | Cookie: session_id |
| ESP32 check-in/check-out | Direct AI :8009 | `/ai/parking/esp32/*` | X-Gateway-Secret |
| ESP32 verify-slot/cash-payment | Direct AI :8009 | `/ai/parking/esp32/*` | X-Gateway-Secret |
| ESP32 device mgmt | Direct AI :8009 | `/ai/parking/esp32/*` | X-Gateway-Secret |
| WebSocket | Direct Realtime :8006 | `ws://.../ws/parking` | None (public) |
| Scan plate | Direct AI :8009 | `/ai/parking/scan-plate/` | X-Gateway-Secret |

### 6.3 Header Templates

**Gateway requests:**
```
GET http://localhost:8000/parking/lots/
Headers:
  Cookie: session_id=<uuid-from-login>
  Content-Type: application/json
```

**Direct AI requests:**
```
POST http://localhost:8009/ai/parking/esp32/check-in/
Headers:
  X-Gateway-Secret: gateway-internal-secret-key
  Content-Type: application/json
```

**Note:** Gateway strips client-supplied `X-User-ID` và `X-Gateway-Secret` headers để chống injection. Nên đi qua gateway cho booking/vehicle/parking requests.

---

## 7. Updated Data Flow Diagrams

### Flow 1: Full Booking Lifecycle (Corrected)

```
                        BookingTestPanel
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
    ▼                         ▼                         ▼
1. RESOLVE VEHICLE        2. SELECT SLOT            3. CREATE BOOKING
   GET /vehicles/            GET /parking/floors/       POST /bookings/
   → find by plate           ?lot_id={targetLotId}     { vehicleId, slotId,
   → if not found:           → show zones+slots          zoneId, parkingLotId,
     POST /vehicles/         POST /parking/slots/        startTime, endTime,
     { licensePlate,            /check-slots-             packageType,
       vehicleType,              availability/            paymentMethod }
       name }                → filter available        → Response:
   → vehicleId (UUID)        → user picks slot           { booking, qrCode }
                              → slotId (UUID)          → Slot turns YELLOW
                                                         (via WS event)
```

### Flow 2: ESP32 Check-In (Corrected & Complete)

```
Unity ESP32Simulator                    AI Service (:8009)              Backend
      │                                       │                          │
      │ POST /ai/parking/esp32/check-in/      │                          │
      │ { gate_id: "GATE-IN-01",              │                          │
      │   qr_data: "{...}" (optional),        │                          │
      │   plate_camera_url: (optional),       │                          │
      │   request_id: "uuid" }                │                          │
      │──────────────────────────────────────►│                          │
      │                                       │  If no qr_data:          │
      │                                       │  Open QR camera → scan   │
      │                                       │  Open plate camera → OCR │
      │                                       │                          │
      │                                       │  POST /bookings/{id}/    │
      │                                       │    checkin/              │
      │                                       │─────────────────────────►│
      │                                       │                          │
      │                                       │  ◄── { booking, message, │
      │                                       │       checkedInAt }      │
      │                                       │                          │
      │  ◄──── ESP32Response:                 │  Broadcast WS:          │
      │  { success: true,                     │  slot.status_update      │
      │    event: "check_in_success",         │  { slotId, status:       │
      │    barrierAction: "open",             │    "occupied" }          │
      │    bookingId, plateText,              │                          │
      │    message, details }                 │                          │
      │                                       │                          │
      ▼                                       │                          │
Unity Actions:                                │                          │
├── BarrierController.Open(GATE-IN-01)        │                          │
├── VehicleQueue.Enqueue({                    │                          │
│     plate, slot from details,               │                          │
│     vehicleType, bookingId })               │                          │
├── Vehicle spawns → waypoint path → park     │                          │
├── ParkingSlot → RED + plate label           │                          │
└── UART log: "OPEN_1" / "ACK:OPEN_1"        │                          │
```

### Flow 3: ESP32 Check-Out With Cash Payment (NEW — Not In Plan)

```
Unity ESP32Simulator                    AI Service (:8009)
      │                                       │
      │ POST /esp32/check-out/                │
      │ { gate_id: "GATE-OUT-01" }            │
      │──────────────────────────────────────►│
      │                                       │
      │  ◄── ESP32Response:                   │
      │  Case A: Payment completed (online)   │
      │  { event: "check_out_success",        │
      │    barrierAction: "open",             │
      │    amountDue: 30000, amountPaid: 30000│
      │    message: "Check-out OK" }          │
      │  → Barrier opens → vehicle exits      │
      │                                       │
      │  Case B: Payment pending              │
      │  { event: "check_out_awaiting_payment"│
      │    barrierAction: "close",            │
      │    amountDue: 30000, amountPaid: 0 }  │
      │  → Barrier stays CLOSED               │
      │  → Show "Insert Cash" UI              │
      │                                       │
      │ POST /esp32/cash-payment/             │
      │ { booking_id, image_base64 or         │
      │   camera_url, gate_id }               │
      │──────────────────────────────────────►│
      │  ◄── { success, amountPaid: 10000,    │
      │       amountDue: 30000,               │
      │       event: "check_out_awaiting..." }│
      │  → Update display: "10000/30000"      │
      │                                       │
      │  [Repeat cash-payment until paid]     │
      │                                       │
      │  ◄── { event: "check_out_success",    │
      │       barrierAction: "open" }         │
      │  → Barrier opens → vehicle exits      │
```

### Flow 4: WebSocket Event Handling (Complete)

```
ws://localhost:8006/ws/parking
      │
      │ On Connect:
      │ → Send: { "type": "subscribe", "data": { "channel": "parking.lot.{lotId}" } }
      │
      ├── slot.status_update
      │   { slotId, zoneId, status, vehicleType }
      │   → ParkingSlot.UpdateState(status)
      │   → If occupied: show plate label
      │   → If available: clear plate label
      │
      ├── zone.availability_update
      │   { zoneId, available, total, occupancyRate }
      │   → DashboardUI.UpdateZoneStats()
      │
      ├── lot.availability_update          ← NEW
      │   { lotId, available, total, occupancyRate }
      │   → DashboardUI.UpdateLotStats()
      │
      ├── slots.batch_update               ← NEW
      │   { slots: [{ slotId, status }...] }
      │   → ParkingManager.BatchUpdateSlots()
      │
      ├── booking.created                  ← NEW (if subscribed per user)
      │   { bookingData }
      │   → Slot turns YELLOW
      │
      └── booking.cancelled                ← NEW
          { bookingId, slotId }
          → Slot reverts to GREEN
```

---

## 8. Risk Assessment Per Phase

### Phase 1: Project Setup

| Risk | Level | Mitigation |
|------|-------|-----------|
| NativeWebSocket package install khó (not on Unity Registry) | MEDIUM | Dùng `endel/NativeWebSocket` via git URL trong manifest.json. Fallback: `UnityWebSocket` hoặc custom `ClientWebSocket` wrapper |
| Assembly definitions conflict | LOW | Tạo asmdef sớm, test compile ngay |

### Phase 2: Floor Generator + Waypoints

| Risk | Level | Mitigation |
|------|-------|-----------|
| Waypoint placement tại runtime → EditorOnly issues | LOW | Dùng Gizmos + `#if UNITY_EDITOR` |
| Performance với nhiều waypoint nodes | LOW | Giới hạn ~200 nodes cho 2 floors, BFS là O(V+E) |
| Geometry dimensions không khớp khi scale | MEDIUM | Test real measurements sớm, dùng constants |

### Phase 3: Slot Prefabs

| Risk | Level | Mitigation |
|------|-------|-----------|
| Slot visual khó phân biệt 3 loại | LOW | Dùng distinct colors + shape |
| TextMeshPro font atlas chưa generate | LOW | Import TMP Essentials trong Phase 1 |

### Phase 4: Mock Data

| Risk | Level | Mitigation |
|------|-------|-----------|
| Mock data format drift vs real API | MEDIUM | Mock DTOs phải dùng cùng `DataModels.cs` classes |

### Phase 5: API Connection ⚠️ HIGHEST RISK

| Risk | Level | Mitigation |
|------|-------|-----------|
| **Port sai → all calls fail** | **CRITICAL** | Fix ports trước khi code. Test với curl first |
| **Booking API params sai → 400 errors** | **CRITICAL** | Implement đúng DTOs từ API contracts |
| **Auth flow unclear → 401 everywhere** | **CRITICAL** | Implement AuthManager first, test login manually |
| **CORS blocking Unity → Gateway rejects** | **HIGH** | Gateway dev mode cho phép all origins. Test sớm |
| **Cookie handling trong UnityWebRequest** | **HIGH** | `CookieContainer` hoặc manual `Cookie` header |
| **WebSocket library compatibility** | **MEDIUM** | Test NativeWebSocket với Unity 2022.3 LTS early |
| Vehicle service cần cho booking | **HIGH** | Implement vehicle CRUD trong ApiService |

### Phase 6: Barrier

| Risk | Level | Mitigation |
|------|-------|-----------|
| Animation timing vs API response latency | LOW | Barrier opens on API success, not prediction |

### Phase 7: Vehicle + Queue

| Risk | Level | Mitigation |
|------|-------|-----------|
| Vehicles clip through geometry | MEDIUM | Raycast hoặc collider checks along waypoint path |
| Queue overflow khi many WS events | LOW | Max 10 active vehicles, queue the rest |

### Phase 8: Manager (Integration)

| Risk | Level | Mitigation |
|------|-------|-----------|
| Race condition: poll + WS updating same slot | **HIGH** | WS data is newer → WS timestamp wins. Version/timestamp comparison |
| Event ordering: booking.created arrives before slot.status_update | MEDIUM | Buffer events 100ms, process in order |

### Phase 9: Floor Visibility

| Risk | Level | Mitigation |
|------|-------|-----------|
| Camera snap khi switching floors | LOW | Smooth transition Lerp |
| Vehicles on hidden floors still processing | LOW | Disable vehicle scripts on hidden floors |

### Phase 10: IoT + Booking Panel ⚠️ HIGH RISK

| Risk | Level | Mitigation |
|------|-------|-----------|
| **ESP32 check-in trả response → Unity không parse đúng** | **HIGH** | Test từng ESP32 endpoint bằng curl, validate DTO mapping |
| **Booking create needs vehicleId → need vehicle-service** | **HIGH** | Implement vehicle lookup/create flow |
| **Cash payment flow completely missing** | **HIGH** | Thêm vào ESP32Simulator UI |
| QR data encoding mismatch | MEDIUM | Check QR JSON format matches backend expectation |

### Phase 11: Dashboard + Camera + Polish

| Risk | Level | Mitigation |
|------|-------|-----------|
| Performance: 70 slots + vehicles + UI | MEDIUM | Profile early. Object pooling cho vehicles |
| GarageCameraSimulator RenderTexture cost | LOW | Disable when not viewed |

---

## 9. Tổng Kết — Action Items Theo Priority

### 🔴 MUST FIX (trước khi implement)

| # | Item | Affected Scripts |
|---|------|-----------------|
| 1 | Fix parking port 8001 → 8003 | ApiService, ApiConfig |
| 2 | Thêm vehicle service (port 8004) | ApiService, ApiConfig, BookingTestPanel |
| 3 | Fix booking API params (vehicleId, zoneId, etc.) | ApiService, BookingTestPanel, DataModels |
| 4 | Design auth flow (hybrid: gateway + direct) | AuthManager (new), ApiService |
| 5 | Tạo DataModels.cs với tất cả DTOs | DataModels (new) |
| 6 | Tạo ApiConfig.cs scriptable object | ApiConfig (new) |

### 🟡 SHOULD FIX (trong quá trình implement)

| # | Item | Affected Scripts |
|---|------|-----------------|
| 7 | Thêm WS events: lot.availability, slots.batch, booking.created/cancelled | ApiService |
| 8 | Thêm ESP32 flows: verify-slot, cash-payment, device mgmt | ESP32Simulator |
| 9 | Tạo WaypointNode.cs + WaypointGraph.cs riêng | Navigation/ |
| 10 | Handle error format khác nhau giữa services | ApiService |
| 11 | Polling filter by lot_id/zone_id | ApiService |
| 12 | WS channel subscription (specific lot) | ApiService |

### 🟢 NICE TO HAVE

| # | Item |
|---|------|
| 13 | ESP32 device auto-registration + heartbeat |
| 14 | Pagination handling cho list endpoints |
| 15 | Slot availability check trước booking |
| 16 | Cash denomination display từ AI response |

---

## Appendix A: Port Reference (Correct)

```
Gateway:      8000  (Go Gin)       ← Single entry point
Auth:         8001  (Django)       ← Session/login
Booking:      8002  (Django DRF)   ← Booking CRUD + check-in/out
Parking:      8003  (Django DRF)   ← Lots/Floors/Zones/Slots/Cameras
Vehicle:      8004  (Django DRF)   ← Vehicle CRUD
Notification: 8005  (FastAPI)      ← Push notifications
Realtime:     8006  (Go + WS)     ← WebSocket hub
Payment:      8007  (FastAPI)      ← Payment processing
Chatbot:      8008  (FastAPI)      ← AI chatbot
AI:           8009  (FastAPI)      ← Plate OCR, ESP32 integration
```

## Appendix B: ESP32 Event Types Reference

| Event | Barrier Action | Meaning |
|-------|---------------|---------|
| `check_in_success` | `open` | Check-in OK → barrier mở |
| `check_in_failed` | `close` | Check-in fail → barrier đóng |
| `check_out_success` | `open` | Check-out OK (đã thanh toán) → barrier mở |
| `check_out_awaiting_payment` | `close` | Chưa thanh toán → cần cash-payment |
| `check_out_failed` | `close` | Check-out fail |
| `verify_slot_success` | `no_action` | Xe đúng slot |
| `verify_slot_failed` | `no_action` | Xe sai slot |
