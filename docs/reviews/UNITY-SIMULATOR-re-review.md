# Code Re-Review Report — Unity Digital Twin Parking Simulator

**Score: 7.5/10** | **Verdict: Approve**
**Date:** 2026-04-01 | Files re-reviewed: 6 (.cs) + 2 backend contracts
**Previous Score:** 6/10 (Request Changes)

---

## Summary

|               | Previous | Current      |
| ------------- | -------- | ------------ |
| 🚨 Critical   | 2        | **0** ✅     |
| ⚠️ Major      | 4        | **0** ✅     |
| 💡 Minor      | 8        | 6 (in-scope) |
| 🗑️ Dead Code  | 15 items | **8 items**  |
| 🏗️ Arch Drift | 1        | 0 (in-scope) |

Tất cả 2 Critical và 4 Major từ review trước đã được fix đúng. DTOs match chính xác backend contracts. Không có issues mới từ các fixes. Dead code giảm từ 15 xuống 8 items (7 items resolved do DTOs đã được sử dụng).

---

## CRIT/MAJ Fix Verification

### ✅ CRIT-1: ESP32 API request bodies now use proper DTOs

**FIXED** — All 4 methods in `ApiService.cs` now accept typed DTO parameters instead of anonymous objects:

| Method             | Before (anonymous)                             | After (DTO)                                                  | Backend Contract Match                     |
| ------------------ | ---------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------ |
| `ESP32CheckIn`     | `new { plate_number, qr_data }`                | `ESP32CheckInRequest` with `GateId`, `QrData`                | ✅ `gate_id` required, `qr_data` optional  |
| `ESP32CheckOut`    | `new { plate_number }`                         | `ESP32CheckOutRequest` with `GateId`, `QrData`               | ✅ matches                                 |
| `ESP32VerifySlot`  | `new { slot_code }`                            | `ESP32VerifySlotRequest` with `SlotCode`, `ZoneId`, `GateId` | ✅ all 3 required fields present           |
| `ESP32CashPayment` | `new { plate_number, amount, payment_method }` | `ESP32CashPaymentRequest` with `BookingId`, `GateId`         | ✅ matches `CashPaymentRequest` in backend |

Call sites verified in:

- `ParkingManager.cs:169-175` (ESP32CheckInFlow) — `GateId = MockIds.GATE_IN, QrData = vehicle.qrData` ✅
- `ParkingManager.cs:207-212` (ESP32CheckOutFlow) — `GateId = MockIds.GATE_OUT, QrData = vehicle.qrData` ✅
- `ESP32Simulator.cs:125-129` (DoCheckIn) — `GateId = MockIds.GATE_IN, QrData = qr` ✅
- `ESP32Simulator.cs:159-162` (DoCheckOut) — `GateId = MockIds.GATE_OUT` ✅
- `ESP32Simulator.cs:187-192` (DoVerifySlot) — all 3 required fields set ✅
- `ESP32Simulator.cs:213-217` (DoCashPayment) — `BookingId + GateId` set ✅

### ✅ CRIT-2: ManageDevice split into 3 separate endpoints

**FIXED** — `ESP32ManageDevice` removed, replaced with 3 separate methods in `ApiService.cs:210-228`:

| New Method            | URL                          | Backend Route                   | DTO                          |
| --------------------- | ---------------------------- | ------------------------------- | ---------------------------- |
| `ESP32RegisterDevice` | `ai/parking/esp32/register`  | `@router.post("/register")` ✅  | `ESP32DeviceRegisterRequest` |
| `ESP32Heartbeat`      | `ai/parking/esp32/heartbeat` | `@router.post("/heartbeat")` ✅ | `ESP32HeartbeatRequest`      |
| `ESP32SendLog`        | `ai/parking/esp32/log`       | `@router.post("/log")` ✅       | `ESP32LogRequest`            |

All 3 call sites in `ESP32Simulator.cs:322-368` properly construct DTOs with required fields.

### ✅ MAJ-1: WS subscribe message sent after connect

**FIXED** — `ApiService.cs:282-293`:

```csharp
webSocket.OnOpen += () => {
    var sub = new WsSubscribeMessage {
        Type = "subscribe",
        Data = new WsSubscribeData {
            Channel = $"parking.lot.{config.targetParkingLotId}"
        }
    };
    webSocket.SendText(JsonConvert.SerializeObject(sub));
};
```

Backend `ws_handler.go:107-112` handles `"subscribe"` message type, extracts `data.channel` field → `hub.Register(conn, channel)`. Message format matches. ✅

### ✅ MAJ-2: GetSlots includes lotId in URL

**FIXED** — `ApiService.cs:160`:

```csharp
GatewayUrl($"parking/slots/?lot_id={lotId}&page_size=200")
```

`lotId` parameter now correctly passed as query parameter. Previously hardcoded URL ignored the parameter entirely.

### ✅ MAJ-3: Login credentials from config

**FIXED** — `ParkingManager.cs:76`:

```csharp
authManager.Login(config.testEmail, config.testPassword)
```

`ApiConfig.cs:19-20` defines `testEmail` and `testPassword` as configurable ScriptableObject fields. No more hardcoded `"admin@test.com"`.

### ✅ MAJ-4: Named event handlers with proper unsubscribe

**FIXED** — `ParkingManager.cs:69-82`:

```csharp
Action successHandler = () => { success = true; done = true; };
Action<string> failHandler = _ => { done = true; };
authManager.OnLoginSuccess += successHandler;
authManager.OnLoginFailed += failHandler;
// ... login ...
authManager.OnLoginSuccess -= successHandler;
authManager.OnLoginFailed -= failHandler;
```

Named references stored, proper `+=` / `-=` lifecycle. No more handler leak on repeated calls.

---

## 🆕 New Issues Found

**No new Critical or Major issues introduced by the fixes.**

### 💡 Minor (pre-existing, in-scope)

- [MIN-1] `DataModels.cs` — 433 lines (exceeds 300 limit). Improved from 522 (dead DTOs removed), nhưng vẫn quá limit. Split recommended.
- [MIN-2] `ESP32Simulator.cs` — 344 lines (exceeds 300 limit). Pre-existing.
- [MIN-3] `ApiService.cs` — 312 lines (exceeds 300 limit, borderline). Pre-existing.
- [MIN-4] `ParkingManager.cs` — 308 lines (exceeds 300 limit, borderline). Pre-existing.
- [MIN-5] `ParkingManager.cs:77` — `while (!done) yield return null` in Login still has no timeout. Handler leak fixed, but infinite loop risk on network timeout remains.
- [MIN-6] `ApiService.cs:152-159` — `GetParkingLotDetail` and `GetParkingLotFullInfo` are **identical methods** (same URL, same return type). One is redundant.

---

## 🗑️ Dead Code Found

| File                  | Location                                  | Type                                        | Action                                              |
| --------------------- | ----------------------------------------- | ------------------------------------------- | --------------------------------------------------- |
| `DataModels.cs`       | `LotAvailability` class (line 29)         | Defined DTO, never used by any API call     | Remove                                              |
| `DataModels.cs`       | `VehicleTypeAvailability` class (line 43) | Only referenced by unused `LotAvailability` | Remove                                              |
| `DataModels.cs`       | `ZoneAvailabilityUpdate` class (line 381) | WS DTO defined but never deserialized       | Remove or implement in ParseWsMessage               |
| `DataModels.cs`       | `LotAvailabilityUpdate` class (line 390)  | WS DTO defined but never deserialized       | Remove or implement in ParseWsMessage               |
| `DataModels.cs`       | `SlotsBatchUpdate` class (line 399)       | WS DTO defined but never deserialized       | Remove or implement in ParseWsMessage               |
| `MockDataProvider.cs` | `GenerateMockESP32Devices()` (line 225)   | Method never called                         | Remove                                              |
| `ApiService.cs`       | `GetParkingLotDetail()` (line 152)        | Never called from any file                  | Remove (keep `GetParkingLotFullInfo` or vice versa) |
| `ApiService.cs`       | `GetParkingLotFullInfo()` (line 157)      | Never called, identical to above            | Remove one                                          |

**Total: 8 items** (down from 15 — 7 items resolved by CRIT/MAJ fixes)
**Cleanup task needed: yes** (non-blocking)

### Dead Code Resolved by Fixes ✅

| Item                                     | Status                                                    |
| ---------------------------------------- | --------------------------------------------------------- |
| `ESP32CheckInRequest`                    | ✅ Now used by ApiService, ESP32Simulator, ParkingManager |
| `ESP32CheckOutRequest`                   | ✅ Now used                                               |
| `ESP32VerifySlotRequest`                 | ✅ Now used                                               |
| `ESP32CashPaymentRequest`                | ✅ Now used                                               |
| `ESP32HeartbeatRequest`                  | ✅ Now used by ESP32Simulator.DoHeartbeat                 |
| `ESP32LogRequest`                        | ✅ Now used by ESP32Simulator.DoSendLog                   |
| `WsSubscribeMessage` + `WsSubscribeData` | ✅ Now used in ConnectWebSocket OnOpen                    |

---

## 🏗️ Architecture Compliance (in-scope files)

- ✅ ESP32 API contracts: Unity DTOs match backend Pydantic models exactly
- ✅ Device management endpoints: 3 separate routes matching backend router
- ✅ WS subscribe protocol: Message format matches Go handler expectations
- ✅ Auth strategy: Cookie for Gateway, X-Gateway-Secret for AI (unchanged, correct)
- ✅ Layer separation: Manager → Service → API flow maintained
- ✅ Named handlers: Proper event subscribe/unsubscribe lifecycle

---

## ✨ Positive Highlights

- **Clean DTO adoption**: All ESP32 call sites consistently construct proper requests with required fields
- **Correct trailing-slash handling**: check-in/check-out endpoints have `/` suffix matching backend, device endpoints don't — both correct
- **Vehicle event cleanup**: `HandleVehicleGone` properly unsubscribes all 4 vehicle events (pre-existing, well done)
- **Significant dead code reduction**: 15 → 8 items, all 7 DTO classes now actively used

---

## 📊 Score Breakdown

```
Baseline:                          8.0
Critical issues:                   0   (±0.0)
Major issues:                      0   (±0.0)
Minor issues (6):                  2 groups of 3  (-1.0)
Dead code (8 items):               >5 items (-0.5)
Bonus — clean CRIT/MAJ fixes:     +0.5
Bonus — significant cleanup:      +0.5
                                   ────
TOTAL:                             7.5/10  → Approve
```

---

## 📋 Action Items (non-blocking)

1. **[Dead code]** Remove unused DTOs: `LotAvailability`, `VehicleTypeAvailability`, 3 WS update classes
2. **[Dead code]** Remove `GenerateMockESP32Devices()` from MockDataProvider
3. **[Dead code]** Consolidate `GetParkingLotDetail`/`GetParkingLotFullInfo` into one method
4. **[MIN-5]** Add timeout to Login `while (!done)` loop (30s suggested)
5. (Optional) Split `DataModels.cs` to reduce below 300 lines
6. (Optional) Split `ESP32Simulator.cs` device section into separate class
