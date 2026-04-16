# Research Report: Unity Parking Simulator — Comprehensive Analysis

**Task:** Unity Simulator Deep-Dive | **Date:** 2026-04-14 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. Unity project có **30 C# scripts** hoàn chỉnh, chia 7 namespaces — hệ thống FULLY FUNCTIONAL, không phải skeleton
> 2. Backend connection qua **3 channels**: HTTP Gateway (Cookie auth), Direct AI (X-Gateway-Secret), WebSocket (:8006) — tất cả đều implemented
> 3. **Motorcycle parking ĐÃ CÓ** — 20 slots/floor (V2-01..V2-20 trên F0, C-01..C-20 trên F1), mock data + zones đều có, motorbikePrefab được reference nhưng cần verify prefab asset tồn tại
> 4. **Gotcha lớn nhất**: `ApiConfig.gatewaySecret` default = `"gateway-internal-secret-key"` — phải đổi sang Docker's GATEWAY_SECRET nếu chạy với Docker backend

---

## 2. File Map — ALL Scripts

### 2.1 Scripts/API/ (7 files) — Backend Communication Layer

| File                    | Lines | Mục đích                                                                              | Relevance                                     |
| ----------------------- | ----- | ------------------------------------------------------------------------------------- | --------------------------------------------- |
| `ApiConfig.cs`          | 42    | ScriptableObject cấu hình API URLs, auth, polling, camera settings                    | **CRITICAL** — entry point cho mọi URL/secret |
| `ApiService.cs`         | ~500  | Singleton HTTP client — Gateway (cookie) + AI (secret) + WebSocket + Camera streaming | **CRITICAL** — toàn bộ API calls              |
| `AuthManager.cs`        | 115   | Login via Gateway → lưu session cookie, ApplyAuth cho requests                        | HIGH                                          |
| `DataModels.cs`         | 460   | ALL data models: Lot/Floor/Zone/Slot/Vehicle/Booking/ESP32/WS/Error/Pagination        | HIGH                                          |
| `SharedBookingState.cs` | 145   | In-memory booking store — bridge ESP32↔VehicleSpawner, SyncFromApi()                  | HIGH                                          |
| `MockDataProvider.cs`   | ~200  | Mock slots (V1, V2, A, B, C, G), mock floors/zones/bookings, mock vehicles            | MED                                           |
| `MockIds.cs`            | 80    | UUID constants cho mock data — LOT, FLOORS, ZONES, VEHICLES, BOOKINGS, SLOTS          | MED                                           |

### 2.2 Scripts/Core/ (2 files) — System Orchestration

| File                        | Lines | Mục đích                                                                                                                                                      |
| --------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ParkingManager.cs`         | ~700  | **MAIN ENTRY POINT** — Start() triggers: Generate → Login → FetchData → MapSlots → WS → Cameras → SlotDetection. Vehicle spawn/checkin/checkout orchestration |
| `FloorVisibilityManager.cs` | 70    | Show/hide floor GameObjects, transparency toggle                                                                                                              |

### 2.3 Scripts/Vehicle/ (4 files) — Vehicle System

| File                       | Lines | Mục đích                                                                                                                                                            |
| -------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VehicleController.cs`     | ~300  | FSM: Idle→ApproachingGate→WaitingAtGate→Entering→Navigating→Parking→Parked→Departing→Exiting→Gone. Path following via WaypointGraph                                 |
| `VehicleQueue.cs`          | ~350  | Entry/exit queues + **Vehicle Spawner UI** (+Spawn Car, +Spawn Motorbike buttons). Auto-spawn (Normal/Wave mode). Prioritizes real bookings from SharedBookingState |
| `LicensePlateCreator.cs`   | 150   | 3D Vietnamese license plate — 2-line format, TMP text, URP materials                                                                                                |
| `VehicleVisualEnhancer.cs` | ~200  | Wheel rotation, headlights, brake lights, exhaust particles, auto-create geometry, URP material fix                                                                 |

### 2.4 Scripts/Parking/ (3 files) — Parking Infrastructure

| File                     | Lines | Mục đích                                                                                                                         |
| ------------------------ | ----- | -------------------------------------------------------------------------------------------------------------------------------- |
| `ParkingLotGenerator.cs` | ~600  | Procedural generation: floors, painted slots, garage slots, **motorbike slots**, gates, ramps, waypoints, pillars, lane markings |
| `ParkingSlot.cs`         | 120   | MonoBehaviour on each slot — status color animation (green/yellow/red/grey), label TMP                                           |
| `BarrierController.cs`   | 100   | Animated barrier arm — Open/Close/OpenThenClose, entry/exit type                                                                 |

### 2.5 Scripts/Camera/ (7 files) — Camera System

| File                         | Lines | Mục đích                                                                                                                                                                                                             |
| ---------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VirtualCameraManager.cs`    | ~250  | Spawns 7 cameras, builds configs, manages streamers. Camera IDs: `virtual-f1-overview`, `virtual-gate-in`, `virtual-anpr-entry`, `virtual-gate-out`, `virtual-anpr-exit`, `virtual-zone-south`, `virtual-zone-north` |
| `VirtualCameraStreamer.cs`   | 210   | RenderTexture capture → JPEG → HTTP POST to AI `/ai/cameras/frame` with X-Camera-ID header. Backoff on consecutive errors                                                                                            |
| `GateCameraSimulator.cs`     | ~200  | Physics.OverlapSphere detects vehicles at gate → captures camera frame → AI OCR plate recognition. Manual capture button                                                                                             |
| `SlotOccupancyDetector.cs`   | ~200  | Position-based vehicle detection per slot (no colliders). Reports changes to realtime service                                                                                                                        |
| `ParkingCameraController.cs` | 230   | User camera: orbit/pan/zoom (WASD+mouse), preset modes (Overview/B1/GateEntry/GateExit), keyboard shortcuts                                                                                                          |
| `VehicleTrackingCamera.cs`   | 180   | Follow-cam for vehicles — smooth tracking, auto-return when parked, zoom effect                                                                                                                                      |
| `IVirtualCamera.cs`          | 90    | Interfaces: IVirtualCameraStreamer, IVirtualCameraManager, ISlotOccupancyDetector + VirtualCameraConfig class                                                                                                        |

### 2.6 Scripts/Navigation/ (2 files) — Pathfinding

| File               | Lines | Mục đích                                                                             |
| ------------------ | ----- | ------------------------------------------------------------------------------------ |
| `WaypointGraph.cs` | 160   | BFS pathfinding graph. RegisterNode, Connect, FindPath, GetGateNode, GetSlotEntrance |
| `WaypointNode.cs`  | 60    | Node types: Gate, Lane, SlotEntrance, Ramp, Intersection. Gizmo visualization        |

### 2.7 Scripts/IoT/ (2 files) — ESP32 Simulator

| File                | Lines | Mục đích                                                                                                                 |
| ------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------ |
| `ESP32Simulator.cs` | ~500  | **ESP32 Dashboard UI** — CHECK-IN, CHECK-OUT, VERIFY SLOT, CASH PAYMENT, DEVICE management. Auto-poll bookings every 10s |
| `FlowLogger.cs`     | ~180  | Auto-bootstrap logger — captures ALL Debug.Log to `logs/unity/parksmart_unity.log`, overlay with highlighted tags        |

### 2.8 Scripts/UI/ (3 files) — Dashboard

| File                  | Lines | Mục đích                                                                                    |
| --------------------- | ----- | ------------------------------------------------------------------------------------------- |
| `DashboardUI.cs`      | ~400  | Main dashboard — slot stats, vehicle activity, connection status, floor controls, event log |
| `CameraMonitorUI.cs`  | ~200  | Camera feed grid/fullscreen viewer, demo button                                             |
| `BookingTestPanel.cs` | 6     | **EMPTY STUB** — DisallowMultipleComponent only                                             |

### 2.9 Editor + Tests

| File                                        | Mục đích                |
| ------------------------------------------- | ----------------------- |
| `Editor/SceneBootstrapper.cs`               | Editor-time scene setup |
| `Editor/PrefabBuilder.cs`                   | Build prefabs           |
| `Editor/AutoTestRunner.cs`                  | Auto-run tests          |
| `Tests/EditMode/SharedBookingStateTests.cs` | Unit tests              |
| `Tests/EditMode/MockDataProviderTests.cs`   | Unit tests              |
| `Tests/EditMode/DataModelsTests.cs`         | Unit tests              |
| `Tests/PlayMode/WaypointGraphTests.cs`      | Play mode tests         |
| `Tests/PlayMode/ParkingSlotTests.cs`        | Play mode tests         |
| `Tests/PlayMode/BarrierControllerTests.cs`  | Play mode tests         |

---

## 3. API Connection Config

### 3.1 Configuration (ApiConfig.cs — ScriptableObject)

```csharp
// Source: Assets/Scripts/API/ApiConfig.cs
[Header("Gateway (Session Auth)")]
public string gatewayBaseUrl = "http://localhost:8000";

[Header("Direct Services (bypass gateway)")]
public string aiServiceUrl = "http://localhost:8009";
public string realtimeWsUrl = "ws://localhost:8006/ws/parking";

[Header("Internal Auth")]
public string gatewaySecret = "gateway-internal-secret-key";

[Header("Test Credentials")]
public string testEmail = "test@example.com";
public string testPassword = "password";
```

**How to change**: Edit the ScriptableObject asset in Unity Inspector, or change defaults in code.

### 3.2 Three Communication Channels

| Channel        | Protocol                  | Auth                             | Used For                                                  |
| -------------- | ------------------------- | -------------------------------- | --------------------------------------------------------- |
| Gateway HTTP   | HTTP REST via `:8000`     | Cookie `session_id` (from login) | Parking lots, floors, slots, bookings, vehicles           |
| AI Direct HTTP | HTTP REST via `:8009`     | Header `X-Gateway-Secret`        | ESP32 check-in/out/verify/cash, plate scan, camera frames |
| WebSocket      | WS via `:8006/ws/parking` | None (direct)                    | Real-time slot status updates, check-in success events    |

### 3.3 Auth Flow (AuthManager.cs)

1. `ParkingManager.Start()` calls `Login(config.testEmail, config.testPassword)`
2. POST `{gatewayBaseUrl}/api/auth/login/` with email+password JSON
3. Response `Set-Cookie` header → stored as `sessionCookie`
4. All subsequent Gateway requests: `Cookie: {sessionCookie}` header
5. All AI requests: `X-Gateway-Secret: {gatewaySecret}` header

### 3.4 API Endpoints Used

**Gateway (Cookie Auth):**
| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/api/parking/lots/` | List parking lots |
| GET | `/api/parking/slots/?lot_id={id}&page_size=200` | All slots for a lot |
| GET | `/api/parking/floors/?lot_id={id}` | Floors with zones |
| GET | `/api/bookings/` | Active bookings |
| POST | `/api/bookings/` | Create booking |
| POST | `/api/bookings/{id}/cancel/` | Cancel booking |
| GET | `/api/vehicles/` | User's vehicles |

**AI Service (X-Gateway-Secret):**
| Method | URL | Purpose |
|--------|-----|---------|
| POST | `/ai/parking/esp32/check-in/` | QR-based check-in |
| POST | `/ai/parking/esp32/check-out/` | QR-based check-out |
| POST | `/ai/parking/esp32/verify-slot/` | Verify vehicle at slot |
| POST | `/ai/parking/esp32/cash-payment/` | Process cash payment |
| POST | `/ai/parking/esp32/register` | Register ESP32 device |
| POST | `/ai/parking/esp32/heartbeat` | Device heartbeat |
| POST | `/ai/parking/esp32/log` | Device log |
| POST | `/ai/parking/scan-plate/` | ANPR plate recognition (multipart image) |
| GET | `/ai/cameras/scan-qr?camera_id={id}` | QR scan from camera frame |
| POST | `/ai/cameras/frame` | Stream camera JPEG (X-Camera-ID header) |

**WebSocket (:8006):**

- Subscribe: `{"type":"subscribe","data":{"channel":"parking.lot.{lotId}"}}`
- Receive: `slot.status_update` → update slot colors
- Receive: `unity.spawn_vehicle` → auto-spawn vehicle on web check-in

---

## 4. Data Sync Flow

### 4.1 Startup Sequence (ParkingManager.Start())

```
1. generator.Generate()           → Procedural parking lot (slots, gates, ramps, waypoints)
2. Login(testEmail, testPassword) → Session cookie
3. FetchParkingData()             → GET /parking/slots/ + /parking/floors/
4. GetBookings()                  → Pre-sync active bookings into SharedBookingState
5. MapApiDataToSlots()            → Match API slot codes → generated ParkingSlot objects
                                    Spawn static vehicles for "occupied" slots
6. ConnectWebSocket()             → Subscribe to parking.lot.{lotId}
7. virtualCameraManager.Init()    → Spawn 7 cameras, start streaming
8. slotOccupancyDetector.Start()  → Begin slot detection loop
9. PollSlotsCoroutine()           → Poll slots every deltaPollInterval (5s)
```

### 4.2 "Sync Bookings" Button (ESP32Simulator)

1. User clicks "🔄 Sync Bookings" in ESP32 panel (or auto-trigger every 10s)
2. `apiService.GetBookings()` → GET `/api/bookings/`
3. Response: `PaginatedResponse<BookingData>` with all user bookings
4. `SharedBookingState.SyncFromApi()`:
   - Skips `checked_in` and `checked_out` bookings
   - Skips bookings already in local state
   - Creates `ActiveBooking` for each new booking with: BookingId, QrCodeData, LicensePlate, SlotCode, ZoneId, VehicleType
5. ESP32 panel dropdown shows: `"{plate} → {slotCode} ({bookingId shortId})"`

### 4.3 "+Spawn Car" / "+Spawn Motorbike" Flow (VehicleQueue.AutoSpawnVehicle)

1. **Check for real bookings first**: `SharedBookingState.GetNotCheckedIn()`
   - Filters by vehicle type (Motorbike vs Car)
   - If found: spawn with real plate/bookingId/qrData/slotCode
2. **Fallback**: Random vehicle to random available slot (generates random VN plate)
3. Vehicle spawns at `platformWidth/2 + 12` (outside entry gate)
4. VehicleController FSM: spawn → approach gate → wait → (check-in) → drive to slot → park

### 4.4 Full Check-In Flow

```
Web booking created
       ↓
ESP32 "Sync Bookings" (auto every 10s, or manual button)
       ↓
SharedBookingState stores ActiveBooking
       ↓
"+Spawn Car" → spawns vehicle with booking's plate/slot
       ↓
Vehicle drives to GATE-IN-01, stops (WaitingAtGate)
       ↓
ESP32 panel selects booking, clicks "📥 Check-In"
       ↓
POST /ai/parking/esp32/check-in/ (qr_data from booking)
       ↓
AI service processes: decode QR → find booking → validate → update DB
       ↓
Response: {success, event:"checkin_success", details:{carSlot:{code:"A-03"}}}
       ↓
SharedBookingState.UpdateStatus(bookingId, "checked_in")
       ↓
ParkingManager.CheckInWaitingVehicle(plate)
   → If vehicle at gate: CheckInWithANPR → ANPR camera verifies plate → open barrier
   → If no vehicle at gate: SpawnVehiclePreCheckedIn (drives straight through)
       ↓
Vehicle enters lot, follows waypoints to assigned slot
       ↓
On parked: ParkingManager calls verify-slot API
       ↓
Slot status updated in backend, reflected via WS or polling
```

### 4.5 Full Check-Out Flow

```
ESP32 panel selects booking, clicks "📤 Check-Out"
       ↓
POST /ai/parking/esp32/check-out/ (qr_data)
       ↓
Response may include amountDue (if unpaid)
   → If amountDue > 0: user must use "💲 Cash Payment" first
   → If success + paid: barrier opens
       ↓
SharedBookingState.RemoveBooking(bookingId)
       ↓
Vehicle drives to GATE-OUT-01
       ↓
Exit barrier opens → vehicle drives out → Destroy
```

### 4.6 WebSocket Real-Time Updates

- `slot.status_update` → ParkingManager updates slot color in real-time
- `unity.spawn_vehicle` → Auto-spawns a vehicle (triggered when someone checks in via web/hardware)

---

## 5. Parking Lot Structure

### 5.1 Generated Layout (ParkingLotGenerator)

| Floor        | Zone                   | Slot Codes   | Type          | Count   |
| ------------ | ---------------------- | ------------ | ------------- | ------- |
| Floor 0 (B1) | V1 row 1 (south inner) | V1-01..V1-18 | Car           | 18      |
| Floor 0 (B1) | V1 row 2 (north inner) | V1-19..V1-36 | Car           | 18      |
| Floor 0 (B1) | V1 row 3 (south outer) | V1-37..V1-54 | Car           | 18      |
| Floor 0 (B1) | V1 row 4 (north outer) | V1-55..V1-72 | Car           | 18      |
| Floor 0 (B1) | V2 (motorbike)         | V2-01..V2-20 | **Motorbike** | 20      |
| Floor 0 (B1) | Garage                 | G-01..G-05   | Car           | 5       |
| Floor 1      | A (south)              | A-01..A-18   | Car           | 18      |
| Floor 1      | B (north)              | B-01..B-18   | Car           | 18      |
| Floor 1      | C (motorbike)          | C-01..C-20   | **Motorbike** | 20      |
| Floor 1      | Garage                 | G-06..G-10   | Car           | 5       |
| **Total**    |                        |              |               | **158** |

**Motorbike slots EXIST**: 20/floor × 2 floors = **40 motorbike slots** (V2-xx, C-xx)

### 5.2 Physical Dimensions

- Slot: 2.5m × 5m (car), 1m × 2m (motorbike), 3m × 6m (garage)
- Lane width: 6m
- Platform: 70m × 60m per floor
- Floor height: 3.5m
- Motorbike area: 10 columns × 2 rows, positioned at platform east edge, north side

### 5.3 Slot Status Visualization

| Status      | Color                 | Alpha |
| ----------- | --------------------- | ----- |
| Available   | Green (0.2, 0.8, 0.2) | 0.35  |
| Reserved    | Yellow (1, 0.85, 0)   | 0.35  |
| Occupied    | Red (0.9, 0.15, 0.15) | 0.35  |
| Maintenance | Grey (0.5, 0.5, 0.5)  | 0.35  |

Colors animate smoothly via `Color.Lerp`.

---

## 6. Camera System

### 6.1 Virtual Cameras (7 total)

| Camera ID             | Display Name       | Position       | FOV | Purpose                               |
| --------------------- | ------------------ | -------------- | --- | ------------------------------------- |
| `virtual-f1-overview` | Floor 1 Overview   | (0, 22, 0)     | 75° | Top-down view of entire floor         |
| `virtual-gate-in`     | Entry Gate         | (36, 3.5, -4)  | 55° | Wide-angle gate area                  |
| `virtual-anpr-entry`  | ANPR Entry Plate   | (43.5, 1.0, 0) | 35° | Narrow-angle plate capture for AI OCR |
| `virtual-gate-out`    | Exit Gate          | (-36, 3.5, -4) | 55° | Wide-angle exit gate                  |
| `virtual-anpr-exit`   | ANPR Exit Plate    | (-42, 0.4, 0)  | 25° | Narrow-angle exit plate               |
| `virtual-zone-south`  | South Zone Monitor | (0, 12, -20)   | 65° | Angled view of south car rows         |
| `virtual-zone-north`  | North Zone Monitor | (0, 12, 20)    | 65° | Angled view of north car rows         |

### 6.2 Camera Streaming

- Resolution: `config.cameraResWidth` × `config.cameraResHeight` (default 640×480)
- FPS: `config.cameraFps` (default 5)
- JPEG quality: `config.cameraJpegQuality` (default 75)
- Endpoint: POST `/ai/cameras/frame` with:
  - `Content-Type: image/jpeg`
  - `X-Camera-ID: {cameraId}`
  - `X-Gateway-Secret: {secret}`
- Backoff: after 5 consecutive failures → pause 30s then retry

### 6.3 ANPR Flow (ParkingManager.CheckInWithANPR)

1. Get ANPR camera streamer (`virtual-anpr-entry`)
2. Wait 2 frames for camera to settle
3. `SnapshotJpeg()` → JPEG bytes
4. POST to `/ai/parking/scan-plate/` (multipart form)
5. Response: `PlateScanResult` { plateText, confidence }
6. Compare detected vs expected plate
7. Match → open barrier, Mismatch → block, No detection → open with warning (fallback)

---

## 7. ESP32 Simulator Dashboard

### 7.1 UI Sections

| Section      | Button/Control                                      | API Call                      | Notes                           |
| ------------ | --------------------------------------------------- | ----------------------------- | ------------------------------- |
| CHECK-IN     | Booking dropdown, "🔄 Sync Bookings", "📥 Check-In" | `ESP32CheckIn`                | Uses selected booking's QR data |
| CHECK-OUT    | Uses same selected booking, "📤 Check-Out"          | `ESP32CheckOut`               | Shows amountDue if unpaid       |
| VERIFY SLOT  | Uses selected booking's slot/zone, "🔍 Verify Slot" | `ESP32VerifySlot`             | Opens slot barrier on success   |
| CASH PAYMENT | Manual plate input, "💲 Cash Payment"               | `ESP32CashPayment`            | Finds booking by plate          |
| DEVICE       | Device ID input, Register/Heartbeat/Log             | `ESP32Register/Heartbeat/Log` | Device management               |

### 7.2 Auto-Sync

- `ESP32Simulator.Update()` triggers `DoSyncBookings()` every 10 seconds
- Calls `apiService.GetBookings()` → `SharedBookingState.SyncFromApi()`
- Only imports `not_checked_in` bookings (skips `checked_in`/`checked_out`)

---

## 8. ⚠️ Gotchas & Known Issues

- [x] **[CRITICAL]** `ApiConfig.gatewaySecret` default is `"gateway-internal-secret-key"` — Docker backend uses different secret `gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE`. Must match for AI calls to work.
- [ ] **[CRITICAL]** `ApiConfig.targetParkingLotId` is empty string — if backend requires a specific lot UUID, this must be set. Empty string may return all lots or no slots.
- [ ] **[WARNING]** `ApiConfig.testEmail` = `test@example.com` + password = `password` — must match a real user in backend DB for login to succeed.
- [ ] **[WARNING]** `BookingTestPanel.cs` is an **empty stub** — no booking creation UI in Unity. Bookings must come from web app or API.
- [ ] **[NOTE]** Mock mode (`useMockData = true`) bypasses ALL backend calls — useful for offline testing but no data flows.
- [ ] **[NOTE]** Camera IDs changed from memory: now `virtual-f1-overview` (was `f1-overview`), `virtual-gate-in` (was `gate-in`), etc. AI service must recognize these IDs.
- [ ] **[NOTE]** WebSocket channel subscribes to `parking.lot.{targetParkingLotId}` — empty lotId means subscription may fail.
- [ ] **[NOTE]** Vehicle prefabs (`carPrefab`, `motorbikePrefab`) are SerializeField references — need verification that actual prefab assets exist in Unity.
- [ ] **[NOTE]** `VehicleVisualEnhancer` auto-creates basic car geometry if no child Renderers found — prefab may look like a simple box if mesh is missing.

---

## 9. Does Motorcycle Parking Exist?

### **YES — Fully Implemented**

**In Generator:**

- `motorbikeSlotCount = 20` per floor
- `motorbikeWidth = 1m`, `motorbikeDepth = 2m`
- Floor 0: V2-01..V2-20 (`ZONE_MOTO_F1`)
- Floor 1: C-01..C-20 (`ZONE_MOTO_F2`)
- `CreateMotorbikeSlot()` called with correct codes

**In MockData:**

- `ZONE_MOTO_F1`, `ZONE_MOTO_F2` zones exist with `VehicleType = "Motorbike"`
- `SLOT_M01..SLOT_M20` IDs exist
- Mock bookings include motorbike: `59P1-123.45` / `Motorbike` / `M-01`
- `MockDataProvider.GenerateMockVehicles()` includes `VEHICLE_MOTO_1`

**In Vehicle Spawner:**

- "+Spawn Motorbike" button calls `AutoSpawnVehicle("Motorbike")`
- Filters for `SlotType.Motorbike` slots
- Uses `motorbikePrefab` (SerializeField reference)

**In ParkingManager:**

- `SpawnStaticParkedVehicle` checks `slotType == Motorbike` → uses `motorbikePrefab`
- `SpawnVehicle/SpawnVehiclePreCheckedIn` accept `vType = "Motorbike"`

**What might be missing:**

- ❓ Actual motorbike prefab asset in Assets/Prefabs/Vehicles/ — code references it but prefab file not verified
- ❓ Motorbike license plate positioning may differ from car (LicensePlateCreator uses fixed offsets designed for car dimensions)

---

## 10. What Could Cause "Unity Shows Empty"

### If slots appear but are all green (no data):

1. **Login failed**: `test@example.com` / `password` doesn't match backend user → no cookie → all API calls 401
2. **targetParkingLotId empty**: API returns empty results for `?lot_id=`
3. **Gateway secret mismatch**: AI calls fail silently (ESP32 operations)
4. **Backend services down**: Docker containers not running

### If nothing appears at all:

5. **ParkingManager not in scene**: Must be on a GameObject with all SerializeField references set
6. **Missing prefab references**: carPrefab/motorbikePrefab not assigned → no vehicles spawn
7. **Generator not assigned**: ParkingLotGenerator reference missing → no parking lot generated

### Diagnosis Sequence:

```
1. Check Unity Console → [ParkingManager] Login OK or FAILED?
2. Check Console → [ParkingManager] Fetched N slots — if 0, lotId issue
3. Check Console → [ParkingManager] Mapped N/M slots — if 0, code mismatch
4. Check Console → [ApiService] POST/GET → check HTTP status codes
5. Check useMockData toggle → if true, should show mock data at minimum
```

---

## 11. Step-by-Step: Get Data Flowing

### Prerequisites

1. Backend Docker services running (at least: auth, booking, parking, vehicle, ai, realtime, gateway)
2. A user exists in DB matching `testEmail`/`testPassword` in ApiConfig
3. A parking lot exists in DB — copy its UUID to `ApiConfig.targetParkingLotId`
4. `ApiConfig.gatewaySecret` matches Docker's GATEWAY_SECRET

### Flow

```
1. Open Unity, press Play
2. ParkingManager auto-starts → generates lot → logs in → fetches data
3. Console shows: "Fetched N slots", "Mapped M/N slots"
4. Dashboard shows slot stats: Total / Available / Occupied / Reserved
5. Create a booking on the web app (or via API)
6. In Unity ESP32 panel: click "🔄 Sync Bookings"
7. Booking appears in dropdown
8. Click "+Spawn Car" → vehicle drives to gate
9. Select booking in ESP32, click "📥 Check-In"
10. AI processes → barrier opens → vehicle drives to slot
11. When parked: verify-slot triggers automatically
12. For checkout: click "📤 Check-Out" → vehicle departs
```

---

## 12. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        UNITY SCENE                            │
│                                                               │
│  ┌──────────┐   ┌─────────────┐   ┌──────────────────┐       │
│  │ ApiConfig │──→│ AuthManager │──→│ ApiService        │       │
│  │(SO Asset) │   │(Login+Cookie)│  │(HTTP+WS Client)  │       │
│  └──────────┘   └─────────────┘   └────┬────┬────┬───┘       │
│                                         │    │    │            │
│  ┌─────────────────┐  ┌────────────────┐│    │    │            │
│  │ ParkingManager   │←─│SharedBookingState│    │    │           │
│  │ (Orchestrator)   │  │(In-memory store)│←───┘    │           │
│  └───┬───┬───┬─────┘  └────────────────┘         │            │
│      │   │   │                                     │            │
│  ┌───┘   │   └──────────────┐                     │            │
│  ↓       ↓                  ↓                     │            │
│ Generator VehicleQueue   ESP32Simulator          WS            │
│ (Procedural            (+Spawn Car/Moto      (Check-in/      │
│  lot+slots)             Auto-spawn)            Check-out)     │
│  ↓                      ↓                                      │
│ ParkingSlot[]       VehicleController[]                        │
│ (color status)      (FSM + pathfinding)                        │
│                                                                │
│  ┌─────────────────────────────┐                               │
│  │ VirtualCameraManager        │                               │
│  │ → 7× VirtualCameraStreamer  │── POST /ai/cameras/frame ──→ │
│  │ → SlotOccupancyDetector     │                               │
│  │ → GateCameraSimulator       │── POST /ai/scan-plate/ ────→ │
│  └─────────────────────────────┘                               │
│                                                                │
│  ┌────────────┐ ┌──────────────┐ ┌────────────┐               │
│  │ DashboardUI │ │CameraMonitorUI│ │ FlowLogger │              │
│  │ (Stats+Log) │ │(Camera feeds) │ │(File+GUI)  │              │
│  └────────────┘ └──────────────┘ └────────────┘               │
└──────────────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ↓              ↓              ↓
    Gateway :8000    AI Service :8009  Realtime :8006
    (Cookie Auth)    (Secret Auth)    (WebSocket)
```

---

## 13. Nguồn

| #   | Location                                        | Mô tả                   | Lines |
| --- | ----------------------------------------------- | ----------------------- | ----- |
| 1   | `Assets/Scripts/API/ApiConfig.cs`               | API configuration       | 42    |
| 2   | `Assets/Scripts/API/ApiService.cs`              | All HTTP/WS calls       | ~500  |
| 3   | `Assets/Scripts/API/AuthManager.cs`             | Login + auth            | 115   |
| 4   | `Assets/Scripts/API/DataModels.cs`              | All data models         | 460   |
| 5   | `Assets/Scripts/Core/ParkingManager.cs`         | Main orchestrator       | ~700  |
| 6   | `Assets/Scripts/IoT/ESP32Simulator.cs`          | ESP32 dashboard         | ~500  |
| 7   | `Assets/Scripts/Vehicle/VehicleQueue.cs`        | Vehicle spawner         | ~350  |
| 8   | `Assets/Scripts/Vehicle/VehicleController.cs`   | Vehicle FSM             | ~300  |
| 9   | `Assets/Scripts/Parking/ParkingLotGenerator.cs` | Procedural generation   | ~600  |
| 10  | `Assets/Scripts/Camera/VirtualCameraManager.cs` | Camera system           | ~250  |
| 11  | `/memories/repo/parking-simulator-context.md`   | Previous research notes | —     |
| 12  | `/memories/repo/parksmart-project.md`           | Project facts           | —     |
