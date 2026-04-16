# Research Report: License Plate Rendering, Vehicle Navigation After Check-In, Verify-Slot Bug

**Task:** Unity Simulation Bugs | **Date:** 2026-04-15 | **Type:** Codebase Analysis (3 Areas)

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **License plates** dùng `TextMeshPro` 3D text qua `LicensePlateCreator.CreateRearPlate()` — 2-row Vietnamese format, split tại dấu `-` đầu tiên. Format phụ thuộc vào plate string truyền vào (từ booking hoặc `MOCK-{slotCode}`).
> 2. **Navigation sau check-in** hoạt động đúng logic: `ProceedFromGate()` tìm path từ `GATE-IN-01` → slot entrance. Nếu ANPR fail (no plate detected), vehicle vẫn được cho qua (simulation fallback) VÀ vẫn navigate đúng slot.
> 3. **Verify-slot bug** root cause: `spawned_slot_code` trong `esp32.py` check-in handler lấy từ `checkin_resp.data.carSlot.code` — nếu booking-service trả `carSlot` rỗng/khác slot thực tế, nó fallback sang hardcoded `"A-01"`. Dẫn đến WS spawn event gửi sai slot code. Verify-slot endpoint đọc `booking.slotCode` / `booking.slot_code` — nếu booking-service không trả field này → empty string.

---

## 2. AREA 1: License Plate Rendering on Vehicles

### 2.1 LicensePlateCreator.cs — Full plate rendering code

**File:** `ParkingSimulatorUnity/Assets/Scripts/Vehicle/LicensePlateCreator.cs` (Lines 1–161)

```csharp
// Static helper — creates 3D Vietnamese license plate (rear only)
// 2-line format: Line1 = province+series, Line2 = numbers
// White background, black border, black bold text
// Modeled after real VN 2-row plate (20.5cm × 17.5cm) scaled ×3.5 for visibility

public static class LicensePlateCreator
{
    private const float PlateWidth = 0.72f;
    private const float PlateHeight = 0.46f;
    private const float PlateDepth = 0.015f;
    private const float BorderThickness = 0.012f;
```

**Key method — `CreateRearPlate()` (Lines 28–113):**
- Position: `localPosition = new Vector3(0f, 0.38f, -2.3f)` (rear of vehicle, -Z)
- Container rotated 180° Y so plate faces backward
- Components:
  1. White background cube (`PlateBG`)
  2. Black border frame (4 strips + horizontal divider)
  3. **TextMeshPro** `line1Tmp` — top line (province+series, e.g. "51A")
  4. **TextMeshPro** `line2Tmp` — bottom line (numbers, e.g. "999.88")

**Text splitting logic (Lines 76–82):**
```csharp
string line1Text = plateText;
string line2Text = "";
int dashIndex = plateText.IndexOf('-');
if (dashIndex >= 0)
{
    line1Text = plateText.Substring(0, dashIndex);  // before first dash
    line2Text = plateText.Substring(dashIndex + 1);  // after first dash
}
```

**Important:** The plate splits at the FIRST `-` only. So:
- `"51G-888.88"` → Line1: `"51G"`, Line2: `"888.88"` ✅ 
- `"MOCK-V1-12"` → Line1: `"MOCK"`, Line2: `"V1-12"` (not ideal)
- `"51A-224.56"` → Line1: `"51A"`, Line2: `"224.56"` ✅ 

**`UpdatePlateText()` (Lines 115–135):** Updates existing plate — same split logic, finds child `PlateTextLine1` / `PlateTextLine2` by name.

### 2.2 Where plates get attached

**ParkingManager.cs — `AttachPlateText()` (Line 247):**
```csharp
private void AttachPlateText(GameObject vehicle, string plateText)
{
    LicensePlateCreator.CreateRearPlate(vehicle.transform, plateText);
}
```

Called from 3 places:

1. **`SpawnStaticParkedVehicle()` (Lines 214–246):**
   ```csharp
   // Line 237
   vc.plateNumber = plateNumber ?? $"MOCK-{slot.slotCode}";
   // Line 245
   string plate = vc?.plateNumber ?? "UNKNOWN";
   AttachPlateText(go, plate);
   ```
   - `plateNumber` comes from `SharedBookingState.Instance?.GetBookingBySlotCode(apiSlot.Code)?.LicensePlate`
   - If no booking found → fallback `MOCK-{slotCode}` (e.g. "MOCK-V1-12")

2. **`SpawnVehicle()` (Lines 305–340):**
   ```csharp
   // Line 338
   AttachPlateText(go, plate);
   ```
   - `plate` is the parameter passed in (from WebSocket `HandleCheckinSuccess` or other callers)

3. **`SpawnVehiclePreCheckedIn()` (Lines 460–490):**
   ```csharp
   // Line 488
   AttachPlateText(go, plate);
   ```

### 2.3 Plate format observed

| Source | Format | Example |
|--------|--------|---------|
| Static vehicles (no booking) | `MOCK-{slotCode}` | `MOCK-V1-12` |
| Static vehicles (with booking) | From `booking.LicensePlate` | `51G-888.88` |
| WS spawned vehicles | From `checkin_resp` OCR or booking plate | `51A-224.56` |

### 2.4 VehicleVisualEnhancer.cs — NO plate code

**File:** `ParkingSimulatorUnity/Assets/Scripts/Vehicle/VehicleVisualEnhancer.cs` (Lines 1–396)

This file handles ONLY visual effects: wheels, body sway, lights, exhaust, suspension, URP material fixes, auto-creating basic car geometry. **No plate rendering code** — plates are entirely in `LicensePlateCreator.cs`.

Notable: `FixUrpMaterials()` (Line 322) explicitly **skips TextMeshPro renderers** to avoid breaking plate text:
```csharp
// Line 342 — Skip TextMeshPro renderers — they use SDF shader, not URP/Lit
if (r.GetComponent<TMPro.TMP_Text>() != null) continue;
```

---

## 3. AREA 2: Vehicle Navigation After Check-In

### 3.1 ParkingManager.cs — Check-in flow (Lines 340–458)

**`HandleVehicleAtEntry()` (Lines 340–350):**
```csharp
private void HandleVehicleAtEntry(VehicleController vehicle)
{
    if (vehicle.alreadyCheckedIn)
    {
        // Vehicle was spawned after QR check-in — skip wait, run ANPR directly
        StartCoroutine(CheckInWithANPR(vehicle));
        return;
    }
    vehiclesWaitingAtGate.Add(vehicle);
    Debug.Log($"[ParkingManager] {vehicle.plateNumber} waiting at gate for QR scan");
}
```

**`CheckInWaitingVehicle()` (Lines 353–368):**
```csharp
public bool CheckInWaitingVehicle(string plate)
{
    var vehicle = vehiclesWaitingAtGate.Find(v =>
        string.Equals(v.plateNumber, plate, StringComparison.OrdinalIgnoreCase));

    if (vehicle == null) { /* warning */ return false; }

    vehiclesWaitingAtGate.Remove(vehicle);
    StartCoroutine(CheckInWithANPR(vehicle));
    return true;
}
```

**`CheckInWithANPR()` (Lines 370–458) — THE KEY METHOD:**

Step 1: Capture plate via virtual ANPR camera (Lines 376–400)
Step 2: Compare detected plate with `vehicle.plateNumber` (Lines 402–425)
Step 3: Decision logic (Lines 427–458):

```csharp
// Line 442
bool shouldOpen = plateMatch || string.IsNullOrEmpty(detectedPlate);
if (shouldOpen)
{
    StartCoroutine(entryBarrier.OpenThenClose(3f));
    vehicle.ProceedFromGate();  // ← THIS is the navigation trigger
    Debug.Log($"[ParkingManager] ✅ Gate opened for {vehicle.plateNumber}" +
              (plateMatch ? " (ANPR verified ✅)" : " (ANPR unverified ⚠️)"));
}
else
{
    Debug.LogWarning($"[ParkingManager] 🚫 Gate BLOCKED for {vehicle.plateNumber} " +
                   $"— plate mismatch: detected={detectedPlate}");
}
```

**Key finding:** When ANPR fails (no plate detected), `string.IsNullOrEmpty(detectedPlate)` is `true` → `shouldOpen = true` → vehicle STILL proceeds. The "ANPR unverified ⚠️" log is just a warning, **not a blocker**.

### 3.2 VehicleController.cs — `ProceedFromGate()` (Lines 147–166)

```csharp
public void ProceedFromGate()
{
    // Phase 2: build path from gate to slot entrance and drive in
    var gateNode = waypointGraph.GetGateNode("GATE-IN-01");
    var slotEntrance = waypointGraph.GetSlotEntrance(targetSlot.slotCode);

    if (gateNode == null || slotEntrance == null)
    {
        Debug.LogError($"[VehicleController] ProceedFromGate: cannot resolve path for {plateNumber}");
        state = VehicleState.Gone;
        return;
    }

    currentPath = waypointGraph.FindPath(gateNode, slotEntrance);
    if (currentPath == null || currentPath.Count == 0)
    {
        Debug.LogError($"[VehicleController] ProceedFromGate: no path found for {plateNumber}");
        state = VehicleState.Gone;
        return;
    }

    currentPathIndex = 0;
    state = VehicleState.Entering;
    Debug.Log($"[VehicleController] {plateNumber} proceeding from gate → slot");
}
```

**Navigation uses `targetSlot`** which was set during `Initialize()` — which uses the `slotCode` passed to `SpawnVehicle()`. The slot is resolved at spawn time via `generator.GetSlotByCode(targetSlotCode)`.

### 3.3 State machine flow

```
SpawnVehicle(plate, bookingId, qr, slotCode)
  └→ vehicle.Initialize(graph, slot, plate, qr, type)  // targetSlot = slot
  └→ vehicle.StartEntry()
       └→ state = ApproachingGate
       └→ path = [GATE-IN-01]
       └→ FollowPath() until reach gate
            └→ OnPathComplete() → state = WaitingAtGate
            └→ OnReachedGate → HandleVehicleAtEntry()
                 └→ CheckInWithANPR() → ProceedFromGate()
                      └→ path = FindPath(GATE-IN-01 → slot entrance)
                      └→ state = Entering
                      └→ FollowPath() until slot entrance
                           └→ OnPathComplete() → state = Navigating
                           └→ (waits for ProceedIntoSlot — verify-slot barrier)
                           └→ OR OnPathComplete() → state = Parking
```

**Important:** After `Entering` state completes (path done), `OnPathComplete()` sets `state = Navigating`. The vehicle stops at slot entrance. Then `ProceedIntoSlot()` or another path completion drives it into the slot.

### 3.4 HandleCheckinSuccess — WebSocket spawn (Lines 686–700)

```csharp
private void HandleCheckinSuccess(CheckinSuccessData data)
{
    if (data == null) return;
    string plate = data.Plate ?? "UNKNOWN";
    string bookingId = data.BookingId ?? System.Guid.NewGuid().ToString();
    string qrData = data.QrData ?? $"{{\"booking_id\":\"{bookingId}\"}}";
    string slotCode = data.SlotCode ?? "A-01";  // ← FALLBACK "A-01" !!!
    string vehicleType = data.VehicleType ?? "Car";

    Debug.Log($"[ParkingManager] 🚗 WebSocket check-in: plate={plate} slot={slotCode}");
    SpawnVehicle(plate, bookingId, qrData, slotCode, vehicleType);
}
```

**BUG HERE:** If `data.SlotCode` is null/empty, it defaults to `"A-01"`. The slot code comes from the WebSocket event, which comes from `_broadcast_unity_spawn` in esp32.py.

---

## 4. AREA 3: Verify-Slot Bug — Root Cause Analysis

### 4.1 esp32.py check-in handler — slot_code determination (Lines 968–983)

```python
# Broadcast Unity vehicle spawn command
checkin_data = (
    checkin_resp.get("data", {}) if isinstance(checkin_resp, dict) else {}
)
car_slot_info = checkin_data.get("carSlot") or checkin_data.get("car_slot") or {}
spawned_slot_code = (
    car_slot_info.get("code") if isinstance(car_slot_info, dict) else None
) or "A-01"  # ← HARDCODED FALLBACK "A-01" !!!
```

**ROOT CAUSE #1:** The `spawned_slot_code` is extracted from `checkin_resp["data"]["carSlot"]["code"]` — this is the booking-service's checkin response. If the booking-service doesn't return `carSlot.code` (or the data structure is different), it **falls back to hardcoded `"A-01"`**.

The booking-service response structure from `_call_booking_checkin()` (Line 359):
```python
async def _call_booking_checkin(booking_id: str, user_id: str) -> dict:
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/checkin/"
    resp = await client.post(url, headers=headers)
    return {"status_code": resp.status_code, "data": resp.json()}
```

The `data` is whatever booking-service returns. If it doesn't have `carSlot.code`, the Unity spawn gets `"A-01"`.

**However:** The booking itself has `slotCode`/`slot_code` and `slotId`/`slot_id` (used at Line 943-945). These fields are NOT used for the spawn broadcast — only the checkin response's `carSlot.code` is used.

### 4.2 _broadcast_unity_spawn (Lines 437–471)

```python
async def _broadcast_unity_spawn(
    booking_id: str, plate: str, slot_code: str,
    vehicle_type: str, qr_data: str,
) -> None:
    await client.post(url, headers=headers, json={
        "type": "unity.spawn_vehicle",
        "data": {
            "booking_id": booking_id,
            "plate": plate,
            "slot_code": slot_code,      # ← This is spawned_slot_code (possibly "A-01")
            "vehicle_type": vehicle_type,
            "qr_data": qr_data,
        },
    })
```

### 4.3 verify-slot endpoint — booking_slot empty (Lines 1383–1387)

```python
# Line 1384
booking_slot = booking.get("slotCode", booking.get("slot_code", ""))
booking_zone = booking.get("zoneId", booking.get("zone_id", ""))

slot_match = booking_slot.upper().strip() == slot_code.upper().strip()
```

**ROOT CAUSE #2:** The booking is fetched from booking-service via `_get_booking()`:
```python
async def _get_booking(booking_id: str, user_id: str) -> dict:
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/"
    resp = await client.get(url, headers=headers)
    return resp.json()
```

If the booking-service GET response doesn't include `slotCode` or `slot_code` fields (or they're empty/null), then `booking_slot` = `""`.

This means the booking-service API response for a booking might:
1. Not include `slotCode` at all (field missing)
2. Include it as `null` or empty string
3. Use a different field name (e.g. `car_slot.code` like the checkin response)

### 4.4 Data flow diagram — where slot_code gets lost

```
booking-service DB
  └→ booking has slot assigned (e.g. V1-12)
  └→ GET /bookings/{id}/ → response JSON
       ├─ "slotCode": ???      ← might be empty/missing
       ├─ "slot_code": ???     ← might be empty/missing  
       └─ "carSlot": {"code": ???}  ← might be present here instead

  └→ POST /bookings/{id}/checkin/ → checkin response JSON
       └─ "carSlot": {"code": ???}  ← esp32.py reads this for spawn
            └─ If missing → fallback "A-01"

esp32.py check-in handler:
  1. slot_id for _update_slot_status: booking.get("slotId") — works if field present
  2. spawned_slot_code for Unity: checkin_resp.data.carSlot.code — DIFFERENT SOURCE
  3. verify-slot: booking.get("slotCode") — yet ANOTHER source

→ Three different ways to get slot code, potentially inconsistent
```

---

## 5. ⚠️ Gotchas & Known Issues

- [x] **[BUG]** `esp32.py` Line 975: Hardcoded `or "A-01"` fallback for `spawned_slot_code` — if booking-service checkin response doesn't have `carSlot.code`, Unity gets wrong slot code `A-01` instead of the actual booked slot.
- [x] **[BUG]** `ParkingManager.cs` Line 695: `string slotCode = data.SlotCode ?? "A-01"` — double fallback to `A-01` on Unity side too.
- [x] **[BUG]** `esp32.py` verify-slot (Line 1384): `booking.get("slotCode", booking.get("slot_code", ""))` — if booking-service doesn't return these fields, `booking_slot` is empty string, causing verify to always fail.
- [ ] **[WARNING]** The slot code for Unity spawn comes from `checkin_resp.data.carSlot.code` but the slot code for `_update_slot_status` comes from `booking.slotId` — these could be out of sync.
- [ ] **[NOTE]** The check-in handler should use the booking's own slot code (from `booking.get("slotCode")`) for the Unity spawn instead of relying on the checkin response's nested `carSlot.code`.

---

## 6. Suggested Fix Approach (for Architect/Implementer)

### Fix 1: esp32.py check-in — use booking slot code as primary source

```python
# CURRENT (Line 968-975):
checkin_data = checkin_resp.get("data", {}) if isinstance(checkin_resp, dict) else {}
car_slot_info = checkin_data.get("carSlot") or checkin_data.get("car_slot") or {}
spawned_slot_code = (
    car_slot_info.get("code") if isinstance(car_slot_info, dict) else None
) or "A-01"

# SUGGESTED:
# Use booking's own slot code as primary, checkin response as fallback
booking_slot_code = booking.get("slotCode", booking.get("slot_code", ""))
checkin_data = checkin_resp.get("data", {}) if isinstance(checkin_resp, dict) else {}
car_slot_info = checkin_data.get("carSlot") or checkin_data.get("car_slot") or {}
checkin_slot_code = car_slot_info.get("code") if isinstance(car_slot_info, dict) else None
spawned_slot_code = booking_slot_code or checkin_slot_code or "UNKNOWN"
```

### Fix 2: Investigate booking-service response

Need to check what `GET /bookings/{id}/` and `POST /bookings/{id}/checkin/` actually return. The slot code field might be named differently (e.g. `car_slot`, `slot`, `parkingSlot.code`).

---

## 7. Files Referenced

| # | File | Lines | Purpose |
|---|------|-------|---------|
| 1 | `ParkingSimulatorUnity/Assets/Scripts/Vehicle/LicensePlateCreator.cs` | 1–161 | 3D plate creation with TextMeshPro |
| 2 | `ParkingSimulatorUnity/Assets/Scripts/Vehicle/VehicleVisualEnhancer.cs` | 1–396 | Visual effects only, no plate code |
| 3 | `ParkingSimulatorUnity/Assets/Scripts/Vehicle/VehicleController.cs` | 1–290 | Vehicle state machine, ProceedFromGate() |
| 4 | `ParkingSimulatorUnity/Assets/Scripts/Core/ParkingManager.cs` | 1–750+ | Spawn, check-in, ANPR, verify-slot flow |
| 5 | `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | 660–1000 | Check-in endpoint |
| 6 | `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | 1288–1435 | Verify-slot endpoint |
| 7 | `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | 340–400 | _get_booking, _call_booking_checkin |
| 8 | `backend-microservices/ai-service-fastapi/app/routers/esp32.py` | 437–471 | _broadcast_unity_spawn |
