# Code Review Report — Unity Digital Twin Parking Simulator

**Score: 6/10** | **Verdict: Request Changes**
**Date:** 2026-04-01 | Files reviewed: 21 (.cs) + 3 (.asmdef)

---

## Summary

|               | Count       |
| ------------- | ----------- |
| 🚨 Critical   | 2           |
| ⚠️ Major      | 4           |
| 💡 Minor      | 8           |
| 🗑️ Dead Code  | 15 items    |
| 🏗️ Arch Drift | 1 violation |

The codebase demonstrates strong architecture — clean layer separation, consistent singleton patterns, proper namespace organization, and correct auth strategy (cookie for Gateway, X-Gateway-Secret for AI, no auth for WS). However, **all 5 ESP32/AI direct API calls use completely wrong request bodies** (anonymous objects instead of defined DTOs, missing required fields, sending non-existent fields). This makes the entire ESP32 integration non-functional and blocks testing. Additionally, 15 DTO classes are defined but never used, and 2 files exceed the 300-line limit.

---

## 🚨 Critical Issues (PHẢI fix trước testing)

### [CRIT-1] ESP32 API request bodies completely wrong — 4 endpoints affected

- **Files:** `ApiService.cs:180-210`
- **Category:** API Contract Violation
- **Problem:** All 4 ESP32 methods create inline anonymous objects with **wrong fields** instead of using the defined DTOs. Every call will fail with 422 Unprocessable Entity.

| Method             | Code Sends                                 | API Expects (DTO)                                               |
| ------------------ | ------------------------------------------ | --------------------------------------------------------------- |
| `ESP32CheckIn`     | `{ plate_number, qr_data }`                | `{ gate_id (REQ), qr_data, plate_camera_url, request_id }`      |
| `ESP32CheckOut`    | `{ plate_number }`                         | `{ gate_id (REQ), qr_data, plate_camera_url, request_id }`      |
| `ESP32VerifySlot`  | `{ slot_code }`                            | `{ slot_code, zone_id (REQ), gate_id (REQ), qr_data }`          |
| `ESP32CashPayment` | `{ plate_number, amount, payment_method }` | `{ booking_id (REQ), gate_id (REQ), image_base64, camera_url }` |

- **Impact:** 100% of ESP32 integration is non-functional. Check-in, check-out, verify-slot, cash-payment all broken.
- **Fix:** Use the defined DTOs:
  ```csharp
  // REPLACE (ESP32CheckIn):
  // new { plate_number = plateNumber, qr_data = qrData }
  // WITH:
  new ESP32CheckInRequest
  {
      GateId = MockIds.GATE_IN,  // or pass as parameter
      QrData = qrData,
      PlateCameraUrl = null      // camera URL if available
  }
  // Apply same pattern for CheckOut, VerifySlot, CashPayment
  ```

### [CRIT-2] ESP32ManageDevice calls non-existent unified endpoint

- **File:** `ApiService.cs:215-220`
- **Category:** API Contract Violation
- **Problem:** Code calls `POST /ai/parking/esp32/manage-device/` which doesn't exist. The actual API has 3 separate endpoints:
  - `POST /ai/parking/esp32/device/register/`
  - `POST /ai/parking/esp32/device/heartbeat/`
  - `POST /ai/parking/esp32/device/log/`
- **Impact:** All device management operations fail.
- **Fix:** Split into 3 separate methods using the correct DTOs (`ESP32DeviceRegisterRequest`, `ESP32HeartbeatRequest`, `ESP32LogRequest`).

---

## ⚠️ Major Issues

### [MAJ-1] WebSocket doesn't subscribe to channel

- **File:** `ApiService.cs:235-250`
- **Problem:** `ConnectWebSocket()` connects to `ws://localhost:8006/ws/parking` but never sends a subscribe message. Plan requires: `Subscribe: parking.lot.{targetLotId}`. The `WsSubscribeMessage` DTO exists but is never used.
- **Fix:** After WS `OnOpen`, send:
  ```csharp
  var sub = new WsSubscribeMessage {
      Type = "subscribe",
      Data = new WsSubscribeData { Channel = $"parking.lot.{config.targetParkingLotId}" }
  };
  webSocket.SendText(JsonConvert.SerializeObject(sub));
  ```

### [MAJ-2] GetSlots ignores lotId parameter

- **File:** `ApiService.cs:146`
- **Problem:** `GetSlots(string lotId, ...)` accepts `lotId` but the URL is hardcoded as `parking/slots/?page_size=200` — parameter completely ignored. All slots returned regardless of lot.
- **Fix:** `GatewayUrl($"parking/slots/?lot_id={lotId}&page_size=200")`

### [MAJ-3] ParkingManager uses hardcoded login credentials, ignoring config

- **File:** `ParkingManager.cs:70`
- **Problem:** `authManager.Login("admin@test.com", "admin123")` ignores `config.testEmail` / `config.testPassword`.
- **Fix:** `authManager.Login(config.testEmail, config.testPassword)`

### [MAJ-4] Login event handler leak — lambdas never unsubscribed

- **File:** `ParkingManager.cs:65-68`
- **Problem:** Subscribes lambda handlers to `OnLoginSuccess`/`OnLoginFailed` without unsubscribing. If `Login()` is called multiple times, handlers accumulate causing duplicate side effects.
- **Fix:** Store handler references and unsubscribe after login completes:
  ```csharp
  Action successHandler = () => { success = true; done = true; };
  Action<string> failHandler = _ => { done = true; };
  authManager.OnLoginSuccess += successHandler;
  authManager.OnLoginFailed += failHandler;
  yield return StartCoroutine(authManager.Login(...));
  while (!done) yield return null;
  authManager.OnLoginSuccess -= successHandler;
  authManager.OnLoginFailed -= failHandler;
  ```

---

## 💡 Minor Issues

- [MIN-1] `DataModels.cs` — **522 lines** exceeds 300-line limit. Split into separate files per service domain: `ParkingModels.cs`, `BookingModels.cs`, `ESP32Models.cs`, `WsModels.cs`.
- [MIN-2] `ParkingLotGenerator.cs` — **373 lines** exceeds 300-line limit. Extract geometry creation helpers into a separate `ParkingGeometry.cs`.
- [MIN-3] `BarrierController.cs` in `Parking/` but plan specifies `Gate/`. Namespace is `ParkingSim.Parking` instead of expected `ParkingSim.Gate`. `Gate/` directory only has `.gitkeep`.
- [MIN-4] `AuthManager.cs:64` — Cookie preview logged (`sessionCookie.Substring(0, 20)`). Minor sensitive data exposure in logs.
- [MIN-5] `BookingTestPanel.cs:170` — Default `paymentMethod = "e_wallet"` but plan lists valid values as `"online"` | `"on_exit"`. Verify `"e_wallet"` is accepted by backend.
- [MIN-6] `GateCameraSimulator.cs:100` — `Physics.OverlapSphere` detection requires Collider on vehicle prefab. No validation check if Collider exists — will silently fail to detect vehicles.
- [MIN-7] `ParkingManager.cs:65-68` — If `authManager` events never fire (e.g., network timeout), `while (!done) yield return null` loops forever. Add timeout.
- [MIN-8] `ParkingSim.API.asmdef` — `overrideReferences: true` but `NativeWebSocket` not listed in `precompiledReferences` or `references`. If NativeWebSocket uses autoReferenced=true it works, but this is fragile and may break if NativeWebSocket package changes.

---

## 🗑️ Dead Code Found

| File                  | Location                                                                               | Type                                 | Action                                     |
| --------------------- | -------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------ |
| `DataModels.cs`       | `ESP32CheckInRequest` class                                                            | Defined DTO never used by ApiService | Use in CRIT-1 fix                          |
| `DataModels.cs`       | `ESP32CheckOutRequest` class                                                           | Defined DTO never used               | Use in CRIT-1 fix                          |
| `DataModels.cs`       | `ESP32VerifySlotRequest` class                                                         | Defined DTO never used               | Use in CRIT-1 fix                          |
| `DataModels.cs`       | `ESP32CashPaymentRequest` class                                                        | Defined DTO never used               | Use in CRIT-1 fix                          |
| `DataModels.cs`       | `ESP32HeartbeatRequest` class                                                          | Never used                           | Use in CRIT-2 fix or remove                |
| `DataModels.cs`       | `ESP32LogRequest` class                                                                | Never used                           | Use in CRIT-2 fix or remove                |
| `DataModels.cs`       | `WsSubscribeMessage` + `WsSubscribeData`                                               | Never used                           | Use in MAJ-1 fix                           |
| `DataModels.cs`       | `WsMessage` class                                                                      | Never used (WS parsing uses JObject) | Remove                                     |
| `DataModels.cs`       | `CheckSlotsAvailabilityRequest` + `Response`                                           | Never used                           | Remove or implement feature                |
| `DataModels.cs`       | `SlotUpdateStatusResponse` class                                                       | Never used                           | Remove                                     |
| `DataModels.cs`       | `CameraData` class                                                                     | Never used                           | Remove or implement camera CRUD            |
| `DataModels.cs`       | `PackagePricing` class                                                                 | Never used                           | Remove or implement pricing fetch          |
| `DataModels.cs`       | `CurrentParkingResponse` class                                                         | Never used                           | Remove or implement current-parking        |
| `DataModels.cs`       | `CheckInResponse`, `CheckOutResponse`, `CancelBookingResponse`, `CreateVehicleRequest` | Never used                           | Remove or implement corresponding features |
| `MockDataProvider.cs` | `GenerateMockLotAvailability()`                                                        | Never called                         | Remove                                     |

**Total: 15+ items → Cleanup task needed: YES** (but 8 items will be resolved by CRIT-1/CRIT-2/MAJ-1 fixes — they'll become used)

---

## 🏗️ Architecture Compliance

- ✅ Dependency flow: Manager → Service → API (correct)
- ✅ No circular dependencies between assemblies
- ✅ Singleton pattern: consistent with null check + DontDestroyOnLoad
- ✅ WaypointGraph: MonoBehaviour (FIX #7 ✓)
- ✅ SharedBookingState: Singleton bridge works (FIX #2 ✓)
- ✅ Cookie auth: explicit Set-Cookie parsing (FIX #1 ✓)
- ✅ ESP32Response.Details: JObject (FIX #3 ✓)
- ✅ WS: no booking.created/cancelled events (FIX #4 ✓)
- ✅ NullValueHandling.Ignore on ESP32 optional fields (FIX #9 ✓)
- ✅ MockIds: stable UUIDs (FIX #10 ✓)
- ✅ GateCameraSimulator: AI OCR flow present (FIX #11 ✓)
- ✅ Gateway URL: `/api/` prefix confirmed correct (verified against gateway-service-go)
- ❌ BarrierController in `Parking/` instead of `Gate/` per plan
- ❌ GarageCameraSimulator.cs missing (plan lists it as required script)
- ❌ Mode B (API-Driven generator) not implemented (only Mode A procedural)

---

## ✨ Positive Highlights

- **Clean architecture**: 3-assembly structure (API → Core → UI) with proper asmdef references and no circular dependencies
- **Robust error handling**: ApiService parses 3 different error formats (standard, Django, Gateway) with graceful fallbacks
- **Well-designed SharedBookingState**: Clean Booking→QR→ESP32 bridge with proper event system
- **Comprehensive mock mode**: Full offline capability with realistic mock data using stable UUIDs
- **GateCameraSimulator**: Elegant camera capture → AI OCR → ESP32 integration with fallback to known plate
- **Visual feedback**: Smooth color lerping on slot status changes, proper URP material handling
- **DashboardUI**: Real-time stats, connection status, event log — good observability

---

## 📋 Action Items (ordered)

1. **[CRIT-1]** Fix all 4 ESP32 API methods to use defined DTOs with correct fields (gate_id required)
2. **[CRIT-2]** Split ESP32ManageDevice into 3 separate endpoint methods matching backend API
3. **[MAJ-1]** Add WS channel subscribe after connection opens
4. **[MAJ-2]** Pass lotId to GetSlots URL query parameter
5. **[MAJ-3]** Use `config.testEmail`/`config.testPassword` in ParkingManager.Login
6. **[MAJ-4]** Unsubscribe login event handlers after completion
7. **[Dead code]** After CRIT/MAJ fixes, remove remaining 7 unused DTOs
8. **[MIN-3]** Move BarrierController.cs from Parking/ to Gate/, update namespace
9. (Optional) [MIN-1,2] Split DataModels.cs and ParkingLotGenerator.cs to meet 300-line limit
10. (Optional) Create GarageCameraSimulator.cs per plan
