# Research Report: Unity Parking Simulator — Complete Check-In Flow

**Date:** 2026-04-10 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **Check-in chạy từ ESP32Simulator** — user chọn booking → nhấn "📥 Check-In (Manual)" hoặc QR scan → gọi API `ESP32CheckIn` → nếu thành công, `ParkingManager.CheckInWaitingVehicle()` mở barrier + cho xe qua.
> 2. **Không có slot-level check-in** — ESP32 gọi `esp32/check-in/` (gate-level). Slot verify là endpoint riêng biệt, hoàn toàn tách rời flow check-in.
> 3. **QR data = JSON `{"booking_id":"..."}` stored in `ActiveBooking.QrCodeData`** — được lấy từ API khi tạo/sync booking.

---

## 2. GUI Buttons Trên Màn Hình (Tất cả OnGUI windows)

### 2.1 ESP32 Simulator Window (ESP32Simulator.cs)

| Button                           | Section      | File:Line | Action                                                               |
| -------------------------------- | ------------ | --------- | -------------------------------------------------------------------- |
| `Hide` / `Show ESP32`            | Header       | L73-76    | Toggle window visibility                                             |
| **Booking SelectionGrid**        | CHECK-IN     | L98-107   | Chọn booking từ dropdown → auto-fill `checkInPlate` + `manualQrData` |
| `🔍 Start QR Scan (DroidCam)`    | CHECK-IN     | L113-119  | Mở URL DroidCam + bắt đầu poll QR API                                |
| `✕ Cancel Scan`                  | CHECK-IN     | L123-126  | Hủy QR polling                                                       |
| `📥 Check-In (Manual)`           | CHECK-IN     | L139-140  | Thực hiện check-in bằng plate + QR data                              |
| `📤 Check-Out`                   | CHECK-OUT    | L274      | Gọi ESP32CheckOut API                                                |
| `🔍 Verify Slot`                 | VERIFY SLOT  | L344-345  | Gọi ESP32VerifySlot API                                              |
| `💲 Cash Payment`                | CASH PAYMENT | L381      | Gọi ESP32CashPayment API                                             |
| `Register` / `Heartbeat` / `Log` | DEVICE       | L428-432  | Device management APIs                                               |

### 2.2 Gate Camera Window (GateCameraSimulator.cs)

| Button                   | File:Line | Action                                          |
| ------------------------ | --------- | ----------------------------------------------- |
| `Hide` / `Show Gate Cam` | L76-78    | Toggle window                                   |
| `📸 Manual Capture`      | L117-120  | Tìm xe gần capturePoint → chụp ảnh → gọi AI OCR |

**Displays:** Status (idle/capturing/spinner), Plate text (color-coded by confidence), Confidence %, Queue count.

### 2.3 Vehicle Spawner Window (VehicleQueue.cs)

| Button                      | File:Line | Action                                       |
| --------------------------- | --------- | -------------------------------------------- |
| `Auto Spawn: ON/OFF` toggle | L220-233  | Toggle auto-spawn coroutine                  |
| `+Spawn Car`                | L238      | Manual spawn car (uses booking if available) |
| `+Spawn Motorbike`          | L239      | Manual spawn motorbike                       |
| `Normal`/`Wave` toggle      | L244      | Switch spawn mode                            |

---

## 3. Complete Check-In Flow (Step by Step)

### Flow A: Manual Check-In via ESP32 GUI

```
1. [Pre-condition] SharedBookingState đã có bookings qua:
   - Auto-sync mỗi 10s (ESP32Simulator.Update → DoSyncBookings)
   - Hoặc ParkingManager.Start() pre-syncs bookings on init

2. User chọn booking từ SelectionGrid (ESP32Simulator L98-107)
   → auto-fills checkInPlate = selected.LicensePlate
   → auto-fills manualQrData = selected.QrCodeData

3. User nhấn "📥 Check-In (Manual)" (L139-140)
   → Calls DoCheckIn() coroutine (L223)

4. DoCheckIn() (ESP32Simulator L223-274):
   a. Validates: plate non-empty
   b. Looks up ActiveBooking by plate via SharedBookingState.GetBookingByPlate()
   c. Gets QR data (from manualQrData or activeBooking.QrCodeData)
   d. Sends API: POST /ai/parking/esp32/check-in/
      Body: { gate_id: "GATE-IN-01", qr_data: "..." }
   e. On success:
      - Extracts slot code from response.Details["carSlot"]["code"]
      - Updates SharedBookingState status → "checked_in"
      - Calls ParkingManager.CheckInWaitingVehicle(plate)
        → If vehicle found at gate: open barrier + proceed
        → If no vehicle at gate: calls SpawnVehiclePreCheckedIn()

5. ParkingManager.CheckInWaitingVehicle(plate) (ParkingManager L330-347):
   a. Finds vehicle in vehiclesWaitingAtGate list by plate
   b. Removes from waiting list
   c. entryBarrier.OpenThenClose(3f) — opens barrier arm 90°, closes after 3s
   d. vehicle.ProceedFromGate() — vehicle continues to slot
   e. Starts RecognizePlateAtGate() coroutine (ANPR verification, doesn't block)

6. RecognizePlateAtGate() (ParkingManager L349-376):
   a. Gets ANPR camera streamer ("virtual-anpr-entry" or "virtual-gate-in")
   b. Waits 2 frames
   c. Takes JPEG snapshot
   d. POST /ai/parking/scan-plate/ (multipart image upload)
   e. Logs match/mismatch — does NOT block gate entry
```

### Flow B: QR Scan via DroidCam

```
1. User nhấn "🔍 Start QR Scan (DroidCam)" (ESP32Simulator L113)
   → Opens browser: http://192.168.100.130:4747/ (DroidCam view)
   → Starts QrPollCoroutine()

2. QrPollCoroutine() (L156-190):
   a. Every 1.5s: calls GET /ai/cameras/scan-qr?camera_id=qr-camera-droidcam
   b. If QR found:
      - Sets manualQrData = scanResult.QrData
      - Looks up booking by QR or BookingId
      - Sets checkInPlate = booking.LicensePlate
      - Auto-calls DoCheckIn() → same flow as Manual above
```

### Flow C: Vehicle Spawn → Gate → ESP32 Check-In

```
1. User clicks "+Spawn Car" in Vehicle Spawner (VehicleQueue)
   → AutoSpawnVehicle("Car") (VehicleQueue L156-190)
   → Checks SharedBookingState.GetNotCheckedIn() for pending bookings
   → If found: ParkingManager.SpawnVehicle(plate, bookingId, qr, slotCode)
   → If not: generates random plate → SpawnVehicle anyway

2. Vehicle drives to gate → VehicleController fires OnReachedGate
   → ParkingManager.HandleVehicleAtEntry() (L321-325)
   → Vehicle added to vehiclesWaitingAtGate list
   → Vehicle STOPS at gate (waits for ESP32 check-in)

3. GateCameraSimulator detects waiting vehicle via Physics.OverlapSphere
   → CaptureAndRecognize() → AIRecognizePlate → OCR result
   → esp32Simulator.SetPlateFromCamera(plate)
   → ESP32 GUI plate field auto-fills

4. User must manually click "📥 Check-In (Manual)" in ESP32 GUI
   → DoCheckIn() → CheckInWaitingVehicle() → gate opens
```

### Flow D: WebSocket Triggered Spawn

```
1. WebSocket receives type="unity.spawn_vehicle"
   → ApiService.ParseWsMessage → OnCheckinSuccess event

2. ParkingManager.HandleCheckinSuccess() (L563-573):
   → Extracts plate, bookingId, qrData, slotCode, vehicleType
   → Calls SpawnVehicle() — vehicle drives in with full booking data
```

---

## 4. SharedBookingState Data Structure

**File:** `Scripts/API/SharedBookingState.cs` (singleton MonoBehaviour)

### ActiveBooking Fields (DataModels.cs L414-421):

| Field           | Type   | Description                                           |
| --------------- | ------ | ----------------------------------------------------- |
| `BookingId`     | string | UUID from backend                                     |
| `QrCodeData`    | string | JSON string: `{"booking_id":"uuid","user_id":"uuid"}` |
| `LicensePlate`  | string | e.g. `"51A-123.45"`                                   |
| `SlotCode`      | string | e.g. `"A-01"`, `"V1-03"`                              |
| `VehicleType`   | string | `"Car"` or `"Motorbike"`                              |
| `CheckInStatus` | string | `"not_checked_in"` / `"checked_in"` / `"checked_out"` |

### Key Methods:

| Method                              | Line | Returns                | Description                                                         |
| ----------------------------------- | ---- | ---------------------- | ------------------------------------------------------------------- |
| `AddBooking(BookingCreateResponse)` | L33  | void                   | Creates ActiveBooking from booking response                         |
| `RemoveBooking(bookingId)`          | L53  | void                   | Removes by ID, fires OnBookingRemoved                               |
| `UpdateStatus(bookingId, status)`   | L62  | void                   | Changes CheckInStatus                                               |
| `GetBookingById(id)`                | L69  | ActiveBooking          | Find by BookingId                                                   |
| `GetBookingByPlate(plate)`          | L74  | ActiveBooking          | Case-insensitive plate match                                        |
| `GetBookingByQr(qrData)`            | L80  | ActiveBooking          | Case-insensitive QR match                                           |
| `GetBookingBySlotCode(slotCode)`    | L86  | ActiveBooking          | Find by slot code                                                   |
| `GetNotCheckedIn()`                 | L97  | List<ActiveBooking>    | Filter `CheckInStatus == "not_checked_in"`                          |
| `GetActiveBookingsForDropdown()`    | L102 | List<(label, booking)> | For ESP32 GUI SelectionGrid                                         |
| `SyncFromApi(List<BookingData>)`    | L115 | int (count added)      | Imports API bookings, skips checked_in/checked_out + already-stored |
| `Clear()`                           | L137 | void                   | Removes all bookings                                                |

### Storage: `List<ActiveBooking> activeBookings` — serialized in Inspector, singleton pattern.

---

## 5. DroidCam / QR Code Integration

**File:** ESP32Simulator.cs

| Detail            | Value                                                  | Line                     |
| ----------------- | ------------------------------------------------------ | ------------------------ |
| DroidCam URL      | `http://192.168.100.130:4747/`                         | L25                      |
| Camera ID for QR  | `"qr-camera-droidcam"`                                 | L26                      |
| Start button      | `"🔍 Start QR Scan (DroidCam)"`                        | L113                     |
| API endpoint      | `GET /ai/cameras/scan-qr?camera_id=qr-camera-droidcam` | ApiService.ScanQr() L417 |
| Poll interval     | 1.5 seconds                                            | L188                     |
| QR data stored in | `manualQrData` field + `ActiveBooking.QrCodeData`      | L176                     |
| Auto-triggers     | `DoCheckIn()` immediately after QR found               | L185                     |

**How "Start DroidCam" works:**

1. Opens `http://192.168.100.130:4747/` in browser (DroidCam IP camera view)
2. Starts `QrPollCoroutine()` — polls AI service every 1.5s
3. AI service examines DroidCam feed, returns QR data if found
4. QR data = booking JSON → auto-lookup booking → auto-fill plate → auto-check-in

---

## 6. QR Data Storage & Usage

QR data is a **JSON string** like: `{"booking_id":"uuid","user_id":"uuid"}`

| Where Stored                         | Purpose                                       |
| ------------------------------------ | --------------------------------------------- |
| `ActiveBooking.QrCodeData`           | Principal storage in SharedBookingState       |
| `manualQrData` (ESP32Simulator)      | Editable text field for manual override       |
| `vehicle.qrData` (VehicleController) | Passed to vehicle on spawn for exit check-out |
| `BookingCreateResponse.QrCode`       | Returned by API on booking creation           |
| `BookingData.QrCodeData`             | Returned by GET /api/bookings/                |

**Usage in check-in:** QR data is sent as `qr_data` field to `POST /ai/parking/esp32/check-in/`

---

## 7. Slot-Level Check-In — DOES NOT EXIST in check-in flow

The ESP32 GUI has a **separate** "VERIFY SLOT" section (L330-367) that:

- Takes `SlotCode` + `ZoneId` inputs
- Calls `POST /ai/parking/esp32/verify-slot/`
- This is **NOT part of the check-in flow** — it's a standalone operation
- No code connects verify-slot to the check-in process

`SlotOccupancyDetector.cs` has `CheckWrongSlotParking()` (L245) — but this is **post-parking detection**, not check-in.

---

## 8. API Endpoints Used

### Gateway API (Cookie Auth via AuthManager):

| Method | Endpoint                                     | ApiService Method | Purpose                |
| ------ | -------------------------------------------- | ----------------- | ---------------------- |
| GET    | `/api/bookings/`                             | `GetBookings()`   | Sync bookings from web |
| POST   | `/api/bookings/`                             | `CreateBooking()` | Create booking         |
| POST   | `/api/bookings/{id}/cancel/`                 | `CancelBooking()` | Cancel booking         |
| GET    | `/api/parking/slots/?lot_id=X&page_size=200` | `GetSlots()`      | Fetch all slots        |
| GET    | `/api/parking/floors/?lot_id=X`              | `GetFloors()`     | Fetch floors           |
| GET    | `/api/vehicles/`                             | `GetVehicles()`   | Fetch vehicles         |

### AI Service API (X-Gateway-Secret header):

| Method | Endpoint                                           | ApiService Method       | File:Line       | Purpose                              |
| ------ | -------------------------------------------------- | ----------------------- | --------------- | ------------------------------------ |
| POST   | `/ai/parking/esp32/check-in/`                      | `ESP32CheckIn()`        | ApiService L279 | **Main check-in**                    |
| POST   | `/ai/parking/esp32/check-out/`                     | `ESP32CheckOut()`       | ApiService L302 | Check-out                            |
| POST   | `/ai/parking/esp32/verify-slot/`                   | `ESP32VerifySlot()`     | ApiService L320 | Verify slot (standalone)             |
| POST   | `/ai/parking/esp32/cash-payment/`                  | `ESP32CashPayment()`    | ApiService L337 | Cash payment                         |
| POST   | `/ai/parking/esp32/register`                       | `ESP32RegisterDevice()` | ApiService L356 | Device registration                  |
| POST   | `/ai/parking/esp32/heartbeat`                      | `ESP32Heartbeat()`      | ApiService L363 | Device heartbeat                     |
| POST   | `/ai/parking/esp32/log`                            | `ESP32SendLog()`        | ApiService L370 | Device logging                       |
| POST   | `/ai/parking/scan-plate/`                          | `AIRecognizePlate()`    | ApiService L377 | **ANPR plate OCR** (multipart image) |
| GET    | `/ai/cameras/scan-qr?camera_id=X`                  | `ScanQr()`              | ApiService L405 | **QR scanning via camera**           |
| POST   | `/ai/cameras/frame`                                | `PostCameraFrame()`     | ApiService L425 | Virtual camera streaming             |
| POST   | (realtime-service) `/api/broadcast/camera-status/` | `PostSlotDetection()`   | ApiService L444 | Slot occupancy broadcast             |

### WebSocket:

| URL                    | Channel               | Events                                      |
| ---------------------- | --------------------- | ------------------------------------------- |
| `config.realtimeWsUrl` | `parking.lot.{lotId}` | `slot.status_update`, `unity.spawn_vehicle` |

---

## 9. BarrierController Usage

**File:** `Scripts/Parking/BarrierController.cs` (98 lines)

| Property      | Value         |
| ------------- | ------------- |
| `openAngle`   | 90° (default) |
| `closedAngle` | 0° (default)  |
| `speed`       | 2f lerp speed |

**Where `OpenThenClose(3f)` is called:**

| Caller                         | File:Line           | Context                                                         |
| ------------------------------ | ------------------- | --------------------------------------------------------------- |
| `CheckInWaitingVehicle()`      | ParkingManager L339 | `entryBarrier.OpenThenClose(3f)` — after successful QR check-in |
| `ESP32CheckInFlow()`           | ParkingManager L434 | `entryBarrier.OpenThenClose(3f)` — legacy auto check-in path    |
| `HandleVehicleAtExit()` (mock) | ParkingManager L475 | `exitBarrier.OpenThenClose(3f)` — mock data exit                |
| `ESP32CheckOutFlow()`          | ParkingManager L503 | `exitBarrier.OpenThenClose(3f)` — real exit check-out           |

**Two barriers serialized in ParkingManager:**

- `entryBarrier` — auto-linked to `BarrierArmPivot_GATE-IN-01`
- `exitBarrier` — auto-linked to `BarrierArmPivot_GATE-OUT-01`
- Linking happens in `AutoLinkBarrierArms()` (ParkingManager L90-105) via reflection

---

## 10. Key File Paths Index

| File                     | Full Path                                 | Lines | Role                                                     |
| ------------------------ | ----------------------------------------- | ----- | -------------------------------------------------------- |
| ESP32Simulator.cs        | `Scripts/IoT/ESP32Simulator.cs`           | ~510  | ESP32 GUI + Check-in/out/verify/payment logic            |
| SharedBookingState.cs    | `Scripts/API/SharedBookingState.cs`       | ~140  | Booking state singleton                                  |
| ParkingManager.cs        | `Scripts/Core/ParkingManager.cs`          | ~580  | Central orchestrator                                     |
| GateCameraSimulator.cs   | `Scripts/Camera/GateCameraSimulator.cs`   | ~260  | Gate AI camera + OCR                                     |
| VehicleQueue.cs          | `Scripts/Vehicle/VehicleQueue.cs`         | ~260  | Spawner + queue management                               |
| ApiService.cs            | `Scripts/API/ApiService.cs`               | ~530  | All HTTP + WebSocket calls                               |
| BarrierController.cs     | `Scripts/Parking/BarrierController.cs`    | ~98   | Barrier arm animation                                    |
| DataModels.cs            | `Scripts/API/DataModels.cs`               | ~440+ | ActiveBooking, CheckinSuccessData, request/response DTOs |
| SlotOccupancyDetector.cs | `Scripts/Camera/SlotOccupancyDetector.cs` | —     | Post-parking wrong-slot detection                        |

---

## 11. ⚠️ Gotchas & Notable Design Decisions

- **[NOTE]** GateCameraSimulator auto-detects vehicles near gate via `Physics.OverlapSphere` and auto-sends to AI OCR — but the OCR result only **fills the ESP32 plate field** (`SetPlateFromCamera`), it does NOT auto-check-in. User must still click "Check-In" manually.
- **[NOTE]** `SpawnVehiclePreCheckedIn()` exists for the case where ESP32 checks in BEFORE a vehicle is at the gate — spawns vehicle that skips gate wait (`alreadyCheckedIn = true`).
- **[NOTE]** `ESP32CheckInFlow()` (ParkingManager L413-440) is a legacy auto-check-in path that calls the ESP32 API directly from ParkingManager — but currently the main flow uses `ESP32Simulator.DoCheckIn()` → `ParkingManager.CheckInWaitingVehicle()` instead.
- **[NOTE]** RecognizePlateAtGate is **verification-only** (log match/mismatch) — doesn't block or reject vehicles.
- **[NOTE]** QR poll for DroidCam fires every 1.5s until QR found or cancelled — no timeout.
