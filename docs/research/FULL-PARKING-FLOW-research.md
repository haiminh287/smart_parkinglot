# Research Report: Full Parking Flow (Booking → Gate → Check-in → Checkout)

**Task:** Full Parking Flow | **Date:** 2026-04-05 | **Type:** Mixed (Codebase + Architecture)

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Full flow đã hoàn chỉnh** ở mức logic: Booking → ESP32 Check-in (QR + plate) → Gate Open → Vehicle Navigate → Park → Departure → ESP32 Check-out → Gate Open → Exit. Cả Unity frontend + AI backend + booking/parking microservices đã có code cho mỗi bước.
> 2. **ESP32Simulator (IMGUI panel)** trong Unity là điểm điều khiển chính — có nút Check-In (manual/QR scan), Check-Out, Verify Slot, Cash Payment. VehicleQueue panel có "+" Spawn buttons nhưng spawn xe không có booking thật.
> 3. **Gotcha lớn nhất:** Check-out ESP32 endpoint luôn cố capture QR từ **camera thật** (DroidCam) trước khi parse — nếu không có DroidCam, sẽ fail timeout sau 30s. Check-in đã hỗ trợ fallback `qr_data` trực tiếp. Check-out cần implement cùng fallback.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan — Unity

| File | Mục đích | Relevance | Tái dụng? |
|------|---------|-----------|----------|
| `ParkingSimulatorUnity/Assets/Scripts/Core/ParkingManager.cs` | Central manager — spawn, gate flow, check-in/out orchestration | **Critical** | Yes — đây là orchestrator |
| `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs` | HTTP client + WebSocket — mọi API call | **Critical** | Yes — mọi endpoint đã có |
| `ParkingSimulatorUnity/Assets/Scripts/API/DataModels.cs` | Request/Response DTOs cho mọi API | **Critical** | Yes |
| `ParkingSimulatorUnity/Assets/Scripts/API/SharedBookingState.cs` | In-memory booking cache, synced from API | **High** | Yes — core data store |
| `ParkingSimulatorUnity/Assets/Scripts/Vehicle/VehicleController.cs` | Vehicle FSM (states + navigation) | **High** | Yes — state machine hoàn chỉnh |
| `ParkingSimulatorUnity/Assets/Scripts/Vehicle/VehicleQueue.cs` | Spawn queue + IMGUI panel ("+Spawn Car") | **Med** | Yes — nhưng spawn không có booking |
| `ParkingSimulatorUnity/Assets/Scripts/IoT/ESP32Simulator.cs` | **ESP32 simulation panel** — QR scan, Check-in, Check-out, Cash, Verify | **Critical** | Yes — đây là control panel chính |
| `ParkingSimulatorUnity/Assets/Scripts/UI/DashboardUI.cs` | Stats dashboard (slot counts, events, WS status) | **Med** | Yes — display only |
| `ParkingSimulatorUnity/Assets/Scripts/UI/CameraMonitorUI.cs` | Camera feed grid viewer | **Med** | Yes |
| `ParkingSimulatorUnity/Assets/Scripts/UI/BookingTestPanel.cs` | **STUB — empty class** | **Low** | No — cần implement từ đầu |

### 2.2 Files/Modules Liên Quan — Backend

| File | Mục đích | Relevance | Tái dụng? |
|------|---------|-----------|----------|
| `ai-service-fastapi/app/routers/esp32.py` | ESP32 check-in/check-out/verify-slot/cash-payment endpoints | **Critical** | Yes |
| `ai-service-fastapi/app/routers/camera.py` | Virtual camera frame receive, plate OCR, QR scan, MJPEG stream | **Critical** | Yes |
| `ai-service-fastapi/app/routers/parking.py` | Standalone plate scan + check-in/check-out (non-ESP32 path) | **High** | Yes |
| `ai-service-fastapi/app/engine/qr_reader.py` | QR decode from image bytes | **High** | Yes |
| `booking-service/bookings/views.py` | CRUD + checkin/checkout/cancel actions | **Critical** | Yes |
| `booking-service/bookings/services.py` | Price calc, checkout logic, late fees | **High** | Yes |
| `booking-service/bookings/models.py` | Booking model (all status fields) | **High** | Yes |
| `parking-service/infrastructure/views.py` | Slot status update, availability check | **High** | Yes |
| `gateway-service-go/internal/config/config.go` | Route mapping (prefix→service) | **Med** | Yes |

### 2.3 Unity Vehicle State Machine

```
VehicleState enum (VehicleController.cs:14-25):
  Idle → ApproachingGate → WaitingAtGate → Entering → Navigating → Parking → Parked
  Parked → Departing → WaitingAtExit → Exiting → Gone
```

**Events fired:**
- `OnReachedGate` → triggers `HandleVehicleAtEntry()` in ParkingManager
- `OnParked` → triggers `HandleVehicleParked()` → starts random DepartureTimer
- `OnReachedExit` → triggers `HandleVehicleAtExit()` → ESP32CheckOutFlow
- `OnGone` → cleanup

### 2.4 Existing Full Flow (When NOT Mock)

#### Entry Flow (ParkingManager.cs:300-412)

```
1. SpawnVehicle(plate, bookingId, qrData, slotCode, vType)     [L:260]
   → Instantiate prefab, Initialize VehicleController
   → vehicle.StartEntry() → drives to GATE-IN-01
   
2. HandleVehicleAtEntry(vehicle)                                [L:300-313]
   → IF useMockData || alreadyCheckedIn → open barrier, proceed
   → ELSE → ESP32CheckInFlow(vehicle)
   
3. ESP32CheckInFlow(vehicle)                                    [L:391-413]
   → POST /ai/parking/esp32/check-in/ with gate_id + qr_data
   → IF success → open entry barrier → vehicle.ProceedFromGate()
   → ALSO → RecognizePlateAtGate(vehicle)                      [L:315-342]
     → snapshot from virtual-gate-in camera → POST /ai/cameras/read-plate
     → Log match/mismatch (informational only, doesn't block entry)
```

#### SpawnVehiclePreCheckedIn (ParkingManager.cs:345-378)
```
Used by ESP32Simulator after successful check-in API call
→ Sets vehicle.alreadyCheckedIn = true
→ Vehicle enters gate without re-calling ESP32 check-in
→ Barrier opens automatically via HandleVehicleAtEntry (alreadyCheckedIn path)
```

#### Parking + Departure (ParkingManager.cs:415-444)
```
4. HandleVehicleParked(vehicle)                                 [L:415-419]
   → Random departure timer (10-30s)
   
5. DepartureTimer expires → vehicle.StartDeparture()            [L:421-428]
   → Navigates from slot to GATE-OUT-01
```

#### Exit Flow (ParkingManager.cs:430-455)
```
6. HandleVehicleAtExit(vehicle)                                 [L:430-440]
   → IF useMockData → open exit barrier, proceed
   → ELSE → ESP32CheckOutFlow(vehicle)
   
7. ESP32CheckOutFlow(vehicle)                                   [L:442-462]
   → POST /ai/parking/esp32/check-out/ with gate_id + qr_data
   → IF success → open exit barrier → vehicle.ProceedFromExit()
   
8. HandleVehicleGone(vehicle)                                   [L:464-471]
   → Cleanup event handlers
   → vehicleQueue.NotifyDeparture() for stats
```

---

## 3. ESP32 Check-In Backend Flow (esp32.py:700-975)

```
POST /ai/parking/esp32/check-in/
├── Step 1: Get QR data
│   ├── IF payload.qr_data provided → parse directly (FAST PATH)
│   └── ELSE → open QR camera, scan loop (30s timeout)
├── Step 2: Fetch booking from booking-service
│   ├── Validate status == "not_checked_in"
│   ├── Validate time window (≤15min early)
│   └── Check payment (online bookings must be paid)
├── Step 3: Capture plate image
│   └── ⚠️ Currently HARDCODED to static test image (51A-224.56.jpg)
├── Step 4: OCR plate + compare
│   └── Only enforced when using REAL camera (skipped for test images)
├── Step 5: Call booking-service /bookings/{id}/checkin/
│   ├── Sets check_in_status = 'checked_in'
│   ├── Updates slot → 'occupied' in parking-service
│   └── Broadcasts slot status via realtime-service
├── Step 6: Update slot status → "occupied"
├── Step 7: Broadcast events
│   ├── gate.check_in notification
│   └── unity.spawn_vehicle command (→ WebSocket → Unity)
└── Return ESP32Response(barrier_action="open")
```

## 4. ESP32 Check-Out Backend Flow (esp32.py:1050-1300)

```
POST /ai/parking/esp32/check-out/
├── Step 1: Get QR data
│   ├── ⚠️ IF payload.qr_data provided → CURRENTLY IGNORES IT
│   │   (always tries camera scan first — SEE GOTCHA #1)
│   └── Open QR camera, scan loop (30s timeout)
├── Step 2: Fetch booking, validate status == "checked_in"
├── Step 3: Capture plate → OCR → verify match
│   └── ⚠️ HARDCODED to static test image (same as check-in)
├── Step 4: PAYMENT ENFORCEMENT
│   ├── Check payment_status via _check_payment_status()
│   ├── on_exit payment → always True
│   ├── online payment → must be "completed"
│   └── If not paid → return AWAITING_PAYMENT (barrier stays closed)
├── Step 5: Call booking-service /bookings/{id}/checkout/
│   ├── calculate_checkout_price() — hourly + late fees
│   ├── perform_checkout() — sets check_in_status='checked_out'
│   └── Updates slot → 'available' in parking-service
├── Step 6: Release slot → "available"
├── Step 7: Broadcast gate.check_out notification
└── Return ESP32Response(barrier_action="open", amount_due, amount_paid)
```

---

## 5. Unity UI Status

### Existing IMGUI Panels (OnGUI-based):

| Panel | File | Location on Screen | Features |
|-------|------|--------------------|----------|
| **ESP32 Simulator** | `IoT/ESP32Simulator.cs` | Top-right (360×460) | Check-In (booking dropdown + QR scan + manual), Check-Out (plate), Verify Slot, Cash Payment, Device Mgmt |
| **Vehicle Spawner** | `Vehicle/VehicleQueue.cs` | Top-left (260×170) | Spawn/Active/Departed counts, Auto-spawn toggle, +Spawn Car, +Spawn Motorbike |
| **Dashboard** | `UI/DashboardUI.cs` | Bottom-center (700×350) | Slot stats, event log, WS status, FPS |
| **Camera Monitor** | `UI/CameraMonitorUI.cs` | Right side (480×500) | Virtual camera grid, live feed preview |
| **Booking Test Panel** | `UI/BookingTestPanel.cs` | — | **EMPTY STUB** — no functionality |

### What Buttons/UI Already Exist for Flow:

| Action | Where | Works? |
|--------|-------|--------|
| Spawn vehicle with booking | ESP32Simulator → Check-In | ✅ Yes — selects booking, calls ESP32 check-in, spawns pre-checked-in vehicle |
| QR scan via DroidCam | ESP32Simulator → "Start QR Scan (DroidCam)" | ✅ Yes — polls `/ai/cameras/scan-qr` endpoint |
| Manual check-in (plate+QR) | ESP32Simulator → "Check-In (Manual)" | ✅ Yes |
| Check-out | ESP32Simulator → "Check-Out" | ⚠️ Partial — only sends gate_id, no QR data passed |
| Cash payment | ESP32Simulator → "Cash Payment" | ✅ Yes — finds booking by plate |
| Random spawn (no booking) | VehicleQueue → "+Spawn Car" | ✅ Yes — but no real booking, uses random plate/UUID |
| Create booking from Unity | — | ❌ Missing — must create bookings via web or seed script |

---

## 6. API Endpoints Map

### AI Service (port 8009, direct access)

| Method | Endpoint | Purpose | Auth | Status |
|--------|----------|---------|------|--------|
| POST | `/ai/parking/esp32/check-in/` | Full check-in flow (QR+plate+booking) | X-Device-Token | ✅ Working |
| POST | `/ai/parking/esp32/check-out/` | Full check-out flow (QR+plate+payment) | X-Device-Token | ⚠️ QR fallback missing |
| POST | `/ai/parking/esp32/verify-slot/` | Verify booking→slot match | X-Device-Token | ✅ Working |
| POST | `/ai/parking/esp32/cash-payment/` | Cash inserted detection | X-Device-Token | ✅ Working |
| GET | `/ai/parking/esp32/status/` | Device health check | X-Device-Token | ✅ Working |
| POST | `/ai/parking/scan-plate/` | Standalone plate OCR | — | ✅ Working |
| POST | `/ai/parking/check-in/` | Alt check-in (image+QR form) | — | ✅ Working |
| POST | `/ai/cameras/frame` | Receive virtual camera frame | X-Gateway-Secret | ✅ Working |
| GET | `/ai/cameras/snapshot` | Get camera snapshot | — | ✅ Working |
| GET | `/ai/cameras/stream` | MJPEG stream | — | ✅ Working |
| GET | `/ai/cameras/read-plate` | OCR from virtual camera | — | ✅ Working |
| GET | `/ai/cameras/scan-qr` | QR decode from camera frame | — | ✅ Working |
| GET | `/ai/cameras/list` | List all cameras | — | ✅ Working |

### Booking Service (port 8002, via gateway at `/api/bookings/`)

| Method | Endpoint | Purpose | Status |
|--------|----------|---------|--------|
| GET | `/bookings/` | List user's bookings | ✅ Working |
| POST | `/bookings/` | Create new booking | ✅ Working |
| GET | `/bookings/{id}/` | Get booking detail | ✅ Working |
| POST | `/bookings/{id}/checkin/` | Mark as checked_in | ✅ Working |
| POST | `/bookings/{id}/checkout/` | Mark as checked_out + pricing | ✅ Working |
| POST | `/bookings/{id}/cancel/` | Cancel booking | ✅ Working |
| GET | `/bookings/{id}/qr-code/` | Get QR code data | ✅ Working |
| GET | `/bookings/current-parking/` | Get currently parked | ✅ Working |
| GET | `/bookings/upcoming/` | Get upcoming bookings | ✅ Working |
| GET | `/bookings/stats/` | Booking statistics | ✅ Working |

### Parking Service (port 8003, via gateway at `/api/parking/`)

| Method | Endpoint | Purpose | Status |
|--------|----------|---------|--------|
| GET | `/parking/slots/?lot_id={id}&page_size=200` | List all slots | ✅ Working |
| GET | `/parking/floors/?lot_id={id}` | List floors | ✅ Working |
| PATCH | `/parking/slots/{id}/update-status/` | Update slot status (occupied/available) | ✅ Working |

### Gateway Routing (port 8080)

| Path Prefix | Upstream Service | Auth Required |
|-------------|-----------------|---------------|
| `auth/` | auth-service | Public (login/register), Protected (admin/me) |
| `parking/` | parking-service | Yes |
| `bookings/` | booking-service | Yes |
| `vehicles/` | vehicle-service | Yes |
| `ai/` | ai-service | Yes |
| `realtime/` | realtime-service | Yes |
| `payments/` | payment-service | Yes |
| `chatbot/` | chatbot-service | Yes |

**Note:** Unity bypasses gateway for AI service (direct to :8009) using `X-Gateway-Secret` header. API calls via gateway go through JWT auth (cookie-based session).

---

## 7. Booking Status Transitions

```
not_checked_in → checked_in    (via POST /checkin/)
checked_in     → checked_out   (via POST /checkout/)
not_checked_in → cancelled     (via POST /cancel/)
not_checked_in → no_show       (via admin)
```

**Slot status transitions:**
```
available → reserved   (booking created)
reserved  → occupied   (check-in)
occupied  → available  (check-out)
```

---

## 8. ⚠️ Gotchas & Known Issues

- [x] **[GOTCHA #1 — BLOCKER for checkout]** `esp32.py` check-out endpoint (L:1068-1092) **always opens QR camera first**, even when `payload.qr_data` is provided. Unlike check-in (which has a `if payload.qr_data:` fast path at L:700-720), check-out starts with `capture.scan_qr_loop()` unconditionally. **This means check-out will fail/timeout if no DroidCam is available.** Unity's `ESP32Simulator.DoCheckOut()` doesn't even pass `qr_data` (only `gate_id`).

- [x] **[GOTCHA #2]** Both check-in and check-out plate OCR are **hardcoded to a static test image** (`51A-224.56.jpg`) instead of using the virtual gate cameras. Comments in code say "TẠM THỜI" (temporary). The virtual cameras (`virtual-gate-in`, `virtual-gate-out`) are available and streaming, but esp32.py doesn't use them.

- [x] **[GOTCHA #3]** ESP32Simulator check-out only takes a `plate` input but **never sends QR data or booking_id** to the backend. The DoCheckOut() function (ESP32Simulator.cs:290-310) creates `ESP32CheckOutRequest` with only `GateId` set — no `QrData`.

- [x] **[GOTCHA #4]** VehicleQueue "+Spawn" creates vehicles with **random UUIDs as booking_id** and no real booking in the database. These vehicles will fail ESP32 check-in at the gate (since no booking exists). They only work in mock mode.

- [x] **[NOTE]** `BookingTestPanel.cs` is an empty stub — just `MonoBehaviour` with no methods. Was likely intended for a booking creation UI from Unity.

- [x] **[NOTE]** DepartureTimer in ParkingManager is random 10-30s, not driven by booking end_time. For demo purposes this is fine, but for realistic testing, vehicles depart before checkout is actually triggered.

- [x] **[NOTE]** The check-out flow for **auto-departed vehicles** (DepartureTimer) calls ESP32CheckOutFlow which tries to use `vehicle.qrData` — this should work if the vehicle was spawned with valid QR data from a real booking.

---

## 9. Gap Analysis: What's Missing for Full Simulated Flow

### Gap 1: Check-Out QR Data Passthrough
**Location:** `esp32.py` check-out endpoint
**What:** Check-out doesn't support `qr_data` direct passthrough like check-in does
**Impact:** Cannot check out without real DroidCam QR camera
**Fix:** Add `if payload.qr_data:` fast path at beginning of check-out (mirror check-in logic)

### Gap 2: ESP32Simulator Check-Out Sends No QR
**Location:** `ESP32Simulator.cs:290-310`
**What:** `DoCheckOut()` only sets `GateId`, never passes QR data or booking info
**Impact:** Even if backend supports QR passthrough, client doesn't send it
**Fix:** Look up active booking by plate in SharedBookingState, pass QR data

### Gap 3: Virtual Camera Plate OCR Not Used at Gates
**Location:** `esp32.py` check-in/check-out plate capture sections
**What:** Hardcoded to static file instead of reading from virtual-gate-in/gate-out cameras
**Impact:** Plate verification is always against a wrong test image
**Fix:** Use `/ai/cameras/snapshot?camera_id=virtual-gate-in` to get live frame from Unity

### Gap 4: No Booking Creation from Unity
**Location:** `BookingTestPanel.cs` (empty)
**What:** Cannot create bookings from within Unity. Must use web app or seed scripts.
**Impact:** For standalone Unity testing, need external tool
**Fix:** Either implement BookingTestPanel or continue using seed scripts (lower priority)

### Gap 5: Vehicle Departure Not Linked to Checkout
**What:** Vehicles auto-depart on random timer → drive to exit → ESP32 check-out fires → but if checkout fails (due to gaps 1-3), vehicle gets stuck at exit gate
**Fix:** After fixing gaps 1-3, this should self-resolve

---

## 10. Recommended Implementation Order

1. **Fix ESP32 check-out `qr_data` passthrough** (esp32.py) — 1 backend change, unblocks everything
2. **Fix Unity ESP32Simulator.DoCheckOut() to send QR data** — pass booking's QR from SharedBookingState
3. **Use virtual camera frames for plate OCR** at gates — replace static image with snapshot API call
4. **Integration test** — spawn vehicle with real booking → check-in → park → depart → check-out
5. (Optional) Implement BookingTestPanel for in-Unity booking creation

---

## 11. Checklist cho Implementer

- [ ] No new installs needed — all dependencies exist
- [ ] Edit `esp32.py`: add `qr_data` fast path to check-out endpoint (mirror check-in at L:700-720)
- [ ] Edit `ESP32Simulator.cs`: `DoCheckOut()` should lookup booking by plate, pass QR data
- [ ] Edit `esp32.py`: replace hardcoded static plate image with virtual camera snapshot
- [ ] Pattern reference: use check-in endpoint pattern for check-out fix
- [ ] Pattern reference: use `apiService.ScanQr()` pattern for QR scanning
- [ ] Test: `test_ai_detection_unity.py` already has test framework, add check-in/out test

---

## 12. Nguồn

| # | File | Mô tả | Key Lines |
|---|------|-------|-----------|
| 1 | `ParkingManager.cs` | Unity central flow | L:260 (SpawnVehicle), L:300 (HandleVehicleAtEntry), L:345 (SpawnPreCheckedIn), L:391 (ESP32CheckInFlow), L:430 (HandleVehicleAtExit), L:442 (ESP32CheckOutFlow), L:525 (HandleCheckinSuccess) |
| 2 | `ApiService.cs` | All API methods | L:267 (ESP32CheckIn), L:300 (ESP32CheckOut), L:388 (AIRecognizePlate), L:406 (ScanQr), L:510 (ParseWsMessage for unity.spawn_vehicle) |
| 3 | `VehicleController.cs` | Vehicle state machine | L:13 (VehicleState enum), L:56 (Initialize), L:68 (StartEntry), L:100 (StartDeparture), L:120 (ProceedFromGate), L:188 (OnPathComplete) |
| 4 | `VehicleQueue.cs` | Spawn panel | L:167 (AutoSpawnVehicle), L:246-278 (OnGUI panel with +Spawn buttons) |
| 5 | `ESP32Simulator.cs` | Check-in/out UI | L:95 (DrawCheckInSection), L:221 (DoCheckIn), L:275 (DrawCheckOutSection), L:290 (DoCheckOut) |
| 6 | `esp32.py` | Backend ESP32 flows | L:650 (check-in endpoint), L:1050 (check-out endpoint), L:850 (static plate HACK) |
| 7 | `camera.py` | Camera endpoints | L:170 (receive_frame), L:237 (read-plate), L:330 (scan-qr) |
| 8 | `views.py` (booking) | Booking actions | L:103 (checkin), L:161 (checkout), L:229 (cancel) |
| 9 | `views.py` (parking) | Slot management | L:388 (update-status) |
| 10 | `config.go` (gateway) | Route mapping | L:137 (GetServiceRoute), L:155 (route table) |
