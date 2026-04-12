# Research Report: Unity Code Deep Dive — 5 Specific Questions

**Task:** Full Parking Flow | **Date:** 2026-04-05 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **SharedBookingState** là pure in-memory store — KHÔNG tự fetch. Data đến từ 2 nguồn: `AddBooking()` (khi tạo booking trong Unity) và `SyncFromApi()` (gọi bởi ESP32Simulator auto-poll mỗi 10s). Không có nút Manual Refresh.
> 2. **ESP32Simulator.DoCheckIn()** gọi `POST {aiServiceUrl}/ai/parking/esp32/check-in/` với QR data, rồi spawn vehicle pre-checked-in nếu thành công.
> 3. **Vehicle biết slot nào** qua chain: `slotCode` → `generator.GetSlotByCode(slotCode)` → `ParkingSlot` object → `vehicle.Initialize(graph, slot, ...)` → `waypointGraph.GetSlotEntrance(slot.slotCode)` → A* pathfinding.

---

## 2. Question 1: SharedBookingState — Loading & Sync

**File:** [SharedBookingState.cs](../ParkingSimulatorUnity/Assets/Scripts/API/SharedBookingState.cs) (148 lines)

### Kiến trúc: Pure In-Memory Store (Singleton)

SharedBookingState **KHÔNG tự fetch từ backend**. Nó là passive data store với 2 entry points:

#### Entry Point 1: `AddBooking(BookingCreateResponse response)` (Line 31–48)

```csharp
public void AddBooking(BookingCreateResponse response)
{
    if (response?.Booking == null) return;
    var existing = activeBookings.Find(b => b.BookingId == response.Booking.Id);
    if (existing != null) return;

    var booking = new ActiveBooking
    {
        BookingId = response.Booking.Id,
        QrCodeData = response.QrCode,
        LicensePlate = response.Booking.Vehicle?.LicensePlate,
        SlotCode = response.Booking.CarSlot?.Code,
        VehicleType = response.Booking.Vehicle?.VehicleType,
        CheckInStatus = "not_checked_in"
    };
    activeBookings.Add(booking);
    OnBookingAdded?.Invoke(booking);
}
```

- Được gọi khi Unity UI tạo booking mới (thông qua API response).
- Dedup bằng bookingId.

#### Entry Point 2: `SyncFromApi(List<BookingData> apiBookings)` (Line 114–139)

```csharp
public int SyncFromApi(List<BookingData> apiBookings)
{
    int added = 0;
    foreach (var b in apiBookings)
    {
        if (b == null || string.IsNullOrEmpty(b.Id)) continue;
        if (b.CheckInStatus == "checked_in" || b.CheckInStatus == "checked_out") continue;
        if (activeBookings.Exists(x => x.BookingId == b.Id)) continue;

        var active = new ActiveBooking { ... };
        activeBookings.Add(active);
        OnBookingAdded?.Invoke(active);
        added++;
    }
    return added;
}
```

- Skips `checked_in` và `checked_out` — chỉ import pending bookings.
- Dedup: skip nếu bookingId đã tồn tại.
- **Caller chính:** `ESP32Simulator.DoSyncBookings()` (ESP32Simulator.cs Line 200–215).

### Ai gọi SyncFromApi?

**ESP32Simulator** auto-polls mỗi **10 giây** (ESP32Simulator.cs Line 56–64):

```csharp
private float syncTimer = 0f;
private const float SYNC_INTERVAL = 10f;

private void Update()
{
    syncTimer += Time.deltaTime;
    if (syncTimer >= SYNC_INTERVAL && !isSyncing && !isProcessing)
    {
        syncTimer = 0f;
        StartCoroutine(DoSyncBookings());
    }
}
```

`DoSyncBookings()` calls `GET {gatewayBaseUrl}/api/bookings/` → feeds results to `SharedBookingState.SyncFromApi()`.

### Có nút Manual Refresh không?

**KHÔNG** — hiện tại chỉ auto-poll mỗi 10s. Không có nút "Refresh" trên UI.

### Lookup Methods (dùng cho các flow khác)

| Method | Line | Lookup by |
|--------|------|-----------|
| `GetBookingById(string)` | 73 | Booking ID |
| `GetBookingByPlate(string)` | 78 | License plate (case-insensitive) |
| `GetBookingByQr(string)` | 84 | QR data (case-insensitive) |
| `GetBookingBySlotCode(string)` | 90 | Slot code (case-insensitive) |
| `GetNotCheckedIn()` | 100 | Filter: status == "not_checked_in" |
| `GetActiveBookingsForDropdown()` | 103 | All bookings, formatted as labels |

---

## 3. Question 2: ESP32Simulator — DoCheckIn() Complete Flow

**File:** [ESP32Simulator.cs](../ParkingSimulatorUnity/Assets/Scripts/IoT/ESP32Simulator.cs)

### 3.1 QR Scanning — DroidCam vs Manual

**"Start QR Scan" Button Code (Line 128–138):**

```csharp
if (!isDroidCamScanning)
{
    if (GUILayout.Button("🔍 Start QR Scan (DroidCam)"))
    {
        isDroidCamScanning = true;
        qrScanStatus = "🔍 Scanning... (point QR at DroidCam)";
        Application.OpenURL(DROIDCAM_VIEW_URL);  // http://192.168.100.130:4747/
        StartCoroutine(QrPollCoroutine());
    }
}
else
{
    GUILayout.Label(qrScanStatus);
    if (GUILayout.Button("✕ Cancel Scan"))
    {
        isDroidCamScanning = false;
        qrScanStatus = "";
    }
}
```

**QR Poll Coroutine (Line 152–185):**

```csharp
private IEnumerator QrPollCoroutine()
{
    while (isDroidCamScanning)
    {
        // Call AI service to scan QR from DroidCam feed
        StartCoroutine(apiService.ScanQr(QR_CAMERA_ID, r => { scanResult = r; done = true; }));
        yield return new WaitUntil(() => done);

        if (scanResult?.IsSuccess == true && scanResult.Data?.Found == true)
        {
            isDroidCamScanning = false;
            manualQrData = scanResult.Data.QrData ?? "";
            qrScanStatus = $"✅ QR Found: {scanResult.Data.BookingId ?? manualQrData}";

            // Auto-lookup booking by QR and fill plate
            var bk = SharedBookingState.Instance?.GetBookingByQr(manualQrData)
                  ?? SharedBookingState.Instance?.GetBookingById(scanResult.Data.BookingId);
            if (bk != null) checkInPlate = bk.LicensePlate;

            StartCoroutine(DoCheckIn());  // ← AUTO check-in after QR found
            yield break;
        }
        yield return new WaitForSeconds(1.5f);  // ← poll every 1.5s
    }
}
```

- API called: `GET {aiServiceUrl}/ai/cameras/scan-qr?camera_id=qr-camera-droidcam`
- Camera ID constant: `QR_CAMERA_ID = "qr-camera-droidcam"`
- Auto-triggers check-in once QR detected — no user confirmation needed

**Manual Fallback UI (Line ~143–157):**
- Text field "Plate:" → `checkInPlate`
- Text field "QR:" → `manualQrData`
- Button **"📥 Check-In (Manual)"** → `StartCoroutine(DoCheckIn())`

**Booking Selection UI (Line 100–114):**
- `SelectionGrid` lists active bookings from `SharedBookingState.GetActiveBookingsForDropdown()`
- Format: `"{plate} → {slotCode} ({shortId})"`
- Selecting a booking auto-fills `checkInPlate` and `manualQrData`

### 3.2 DoCheckIn() Complete Method (Line 221–267)

```csharp
private IEnumerator DoCheckIn()
{
    // 1. VALIDATE: plate required
    if (string.IsNullOrEmpty(checkInPlate))
    { SetResult(false, "Plate number required"); yield break; }

    // 2. LOOKUP: booking by plate to get QR if needed
    var activeBooking = SharedBookingState.Instance?.GetBookingByPlate(checkInPlate);
    string qr = manualQrData;
    if (string.IsNullOrEmpty(qr))
    {
        if (activeBooking == null)
        { SetResult(false, $"No active booking for plate {checkInPlate}"); yield break; }
        qr = activeBooking.QrCodeData;
    }

    // 3. API CALL
    isProcessing = true;
    SetResult(false, $"Checking in {checkInPlate}...");
    var request = new ESP32CheckInRequest
    {
        GateId = MockIds.GATE_IN,
        QrData = qr
    };
    StartCoroutine(apiService.ESP32CheckIn(request, r => { result = r; done = true; }));
    yield return new WaitUntil(() => done);
    isProcessing = false;

    // 4. HANDLE RESPONSE
    if (result != null && result.IsSuccess && result.Data != null && result.Data.Success)
    {
        // Extract slot from response JSON details
        string slot = result.Data.Details?["carSlot"]?["code"]?.ToString()
            ?? activeBooking?.SlotCode ?? "unknown";

        SetResult(true, $"{result.Data.Message}\nAction: {result.Data.BarrierAction}\nSlot: {slot}");

        // Update shared state
        SharedBookingState.Instance?.UpdateStatus(result.Data.BookingId, "checked_in");

        // SPAWN pre-checked-in vehicle → skips gate API call
        if (ParkingManager.Instance != null)
        {
            ParkingManager.Instance.SpawnVehiclePreCheckedIn(
                checkInPlate,
                result.Data.BookingId ?? activeBooking?.BookingId ?? "",
                qr, slot,
                activeBooking?.VehicleType ?? "Car");
        }
    }
    else
    {
        SetResult(false, result?.ErrorMessage ?? result?.Data?.Message ?? "Check-in failed");
    }
}
```

### 3.3 API Endpoint Details

| Property | Value |
|----------|-------|
| **Method** | POST |
| **URL** | `{config.aiServiceUrl}/ai/parking/esp32/check-in/` |
| **URL builder** | `AiUrl(path) => $"{config.aiServiceUrl}/{path}"` (ApiService.cs:48) |
| **Auth** | `X-Gateway-Secret` header (auto-added by `SendRequest(..., true)`) |
| **Body** | `{ gateId: "GATE-IN-01", qrData: "..." }` |
| **Response** | `ESP32Response { Success, Event, BarrierAction, Message, BookingId, Details }` |

### 3.4 Gate Response Handling Summary

**On success:**
1. Extracts slot code from `result.Data.Details["carSlot"]["code"]`
2. Updates SharedBookingState status to `"checked_in"`
3. Spawns vehicle via `SpawnVehiclePreCheckedIn()` — has `alreadyCheckedIn = true`
4. When vehicle reaches gate → `HandleVehicleAtEntry()` sees `alreadyCheckedIn` → opens barrier immediately, no second API call

**On failure:** Shows error message in result area (red text).

---

## 4. Question 3: ESP32Simulator — Verify Slot

**File:** ESP32Simulator.cs, `DrawVerifySlotSection()` (Line 325–342) + `DoVerifySlot()` (Line 344–363)

### UI Layout

```
── VERIFY SLOT ──
[Slot: ___________]   ← text field (verifySlotCode)
[Zone: ___________]   ← text field (verifyZoneId, optional)
[🔍 Verify Slot]      ← button
```

### User Interaction

1. User types **slot code** (e.g. `"A-01"`) in the Slot text field
2. Optionally types **zone ID** in the Zone text field
3. If Zone empty → defaults to `MockIds.ZONE_CAR_PAINTED_F1`
4. Clicks **"🔍 Verify Slot"** button

### DoVerifySlot() Code

```csharp
private IEnumerator DoVerifySlot()
{
    if (string.IsNullOrEmpty(verifySlotCode))
    { SetResult(false, "Slot code required"); yield break; }

    isProcessing = true;
    var request = new ESP32VerifySlotRequest
    {
        SlotCode = verifySlotCode,
        ZoneId = string.IsNullOrEmpty(verifyZoneId)
            ? MockIds.ZONE_CAR_PAINTED_F1 : verifyZoneId,
        GateId = MockIds.GATE_IN
    };
    StartCoroutine(apiService.ESP32VerifySlot(request, r => { result = r; done = true; }));
    yield return new WaitUntil(() => done);
    isProcessing = false;

    SetResult(result.IsSuccess && result.Data?.Success == true,
        result.Data?.Message ?? result.ErrorMessage ?? "Verify failed");
}
```

**API:** `POST {aiServiceUrl}/ai/parking/esp32/verify-slot/`
**Body:** `{ slotCode, zoneId, gateId }`
**Result:** Shows success/fail message in IMGUI result area

---

## 5. Question 4: VehicleQueue.AutoSpawnVehicle()

**File:** [VehicleQueue.cs](../ParkingSimulatorUnity/Assets/Scripts/Vehicle/VehicleQueue.cs) (Line 168–230)

### Complete Logic

```csharp
private void AutoSpawnVehicle(string vehicleType = "Car")
{
    if (ParkingManager.Instance == null || generatorRef == null) return;
    if (generatorRef.slotRegistry == null || generatorRef.slotRegistry.Count == 0) return;

    // ─── STEP 1: Check for pending REAL bookings first ───
    var pendingBookings = SharedBookingState.Instance?.GetNotCheckedIn();
    var pendingBooking = pendingBookings?.Find(b =>
        vehicleType == "Motorbike"
            ? b.VehicleType == "Motorbike"
            : b.VehicleType != "Motorbike");

    if (pendingBooking != null)
    {
        string bkPlate  = pendingBooking.LicensePlate ?? "UNKNOWN";
        string bkId     = pendingBooking.BookingId;
        string bkQr     = pendingBooking.QrCodeData
                          ?? $"{{\"booking_id\":\"{bkId}\"}}";
        string slotCode = pendingBooking.SlotCode;

        if (!string.IsNullOrEmpty(slotCode)
            && generatorRef.slotRegistry.ContainsKey(slotCode))
        {
            ParkingManager.Instance.SpawnVehicle(bkPlate, bkId, bkQr,
                slotCode, pendingBooking.VehicleType ?? vehicleType);
            TotalSpawned++;
            return;
        }
    }

    // ─── STEP 2: Fallback — random vehicle (no real booking) ───
    var availableSlots = generatorRef.slotRegistry.Values
        .Where(s => s.status == ParkingSlot.SlotStatus.Available)
        .Where(s => vehicleType == "Motorbike"
            ? s.slotType == ParkingSlot.SlotType.Motorbike
            : s.slotType != ParkingSlot.SlotType.Motorbike)
        .ToList();

    if (availableSlots.Count == 0) return;

    var targetSlot = availableSlots[Random.Range(0, availableSlots.Count)];
    string plate     = GenerateRandomPlate();
    string bookingId = System.Guid.NewGuid().ToString();
    string qrData    = $"{{\"booking_id\":\"{bookingId}\"}}";

    ParkingManager.Instance.SpawnVehicle(plate, bookingId, qrData,
        targetSlot.slotCode, vehicleType);
    TotalSpawned++;
}
```

### Key Logic Flow

| Step | What | Detail |
|------|------|--------|
| 1 | **Real bookings first** | Gets `GetNotCheckedIn()` from SharedBookingState |
| 2 | **Type matching** | Motorbike spawns → only picks Motorbike bookings. Else → non-Motorbike |
| 3 | **Validate slot** | slotCode must exist in `generatorRef.slotRegistry` |
| 4 | **Uses `SpawnVehicle()`** | NOT `SpawnVehiclePreCheckedIn` — vehicle will do check-in at gate |
| 5 | **Random fallback** | If no real bookings → random available slot, random plate, fake QR |

### Important: SpawnVehicle vs SpawnVehiclePreCheckedIn

- `AutoSpawnVehicle()` → `SpawnVehicle()` — vehicle reaches gate → `HandleVehicleAtEntry()` → calls `ESP32CheckInFlow()` API
- `ESP32Simulator.DoCheckIn()` → `SpawnVehiclePreCheckedIn()` — vehicle has `alreadyCheckedIn = true` → gate opens immediately

---

## 6. Question 5: How Vehicle Knows Which Slot to Navigate To

### Full Chain: slotCode → ParkingSlot → VehicleController → WaypointGraph → Path

#### Step 1: ParkingManager resolves slotCode → ParkingSlot object

**ParkingManager.cs Line 260–265:**

```csharp
public void SpawnVehicle(string plate, string bookingId, string qrData,
    string targetSlotCode, string vType = "Car")
{
    // ...instantiate prefab...
    var slot = generator.GetSlotByCode(targetSlotCode);  // ← ParkingSlot object
    vehicle.Initialize(waypointGraph, slot, plate, qrData, vType);
    vehicle.bookingId = bookingId;
    vehicle.StartEntry();
}
```

Same in `SpawnVehiclePreCheckedIn()` (Line 341+), plus `vehicle.alreadyCheckedIn = true`.

#### Step 2: VehicleController stores the ParkingSlot

**VehicleController.cs Line 49–57:**

```csharp
public void Initialize(WaypointGraph graph, ParkingSlot slot, string plate, string qr, string vType)
{
    waypointGraph = graph;
    targetSlot = slot;           // ← stored as private ParkingSlot field
    plateNumber = plate;
    qrData = qr;
    vehicleType = vType;
}
```

#### Step 3: StartEntry() uses slot to pathfind

**VehicleController.cs Line 59–88:**

```csharp
public void StartEntry()
{
    var gateNode = waypointGraph.GetGateNode("GATE-IN-01");
    var slotEntrance = waypointGraph.GetSlotEntrance(targetSlot.slotCode);

    currentPath = waypointGraph.FindPath(gateNode, slotEntrance);  // A* pathfinding
    currentPathIndex = 0;
    state = VehicleState.ApproachingGate;
}
```

#### Step 4: Departure reverses the path

**VehicleController.cs Line 92+:**

```csharp
public void StartDeparture()
{
    var slotEntrance = waypointGraph.GetSlotEntrance(targetSlot.slotCode);
    var exitNode = waypointGraph.GetGateNode("GATE-OUT-01");
    currentPath = waypointGraph.FindPath(slotEntrance, exitNode);
}
```

### Complete Navigation Chain Diagram

```
Booking.SlotCode (string, e.g. "A-01")
  ↓ generator.GetSlotByCode(targetSlotCode)
ParkingSlot (MonoBehaviour on scene object, has transform.position)
  ↓ vehicle.Initialize(graph, slot, ...)
VehicleController.targetSlot (private ParkingSlot field)
  ↓ waypointGraph.GetSlotEntrance(targetSlot.slotCode)
WaypointNode (entrance node registered for that slot code)
  ↓ waypointGraph.FindPath(gateNode, slotEntrance)
List<WaypointNode> currentPath (A* pathfinding result)
  ↓ VehicleController.Update() — follows path nodes one by one
Vehicle arrives at slot → parks at targetSlot.transform.position
```

---

## 7. ⚠️ Gotchas & Notes

- [NOTE] SharedBookingState has **no manual refresh button** — only ESP32Simulator's 10s auto-poll brings web-created bookings in
- [NOTE] `AutoSpawnVehicle()` uses `SpawnVehicle()` (with gate check-in), while ESP32's manual check-in uses `SpawnVehiclePreCheckedIn()` (skips gate)
- [NOTE] If `slotCode` doesn't exist in `generatorRef.slotRegistry`, the real booking is **silently skipped** and falls through to random fallback
- [NOTE] QR polling to DroidCam runs every 1.5s and auto-triggers check-in when found — no user confirmation step
- [NOTE] `SyncFromApi()` only imports bookings with status NOT `checked_in`/`checked_out` — already-checked-in bookings from web are invisible to Unity

---

## 8. Nguồn

| # | File | Lines | Content |
|---|------|-------|---------|
| 1 | `Assets/Scripts/API/SharedBookingState.cs` | 1–148 | Full file — booking state store |
| 2 | `Assets/Scripts/IoT/ESP32Simulator.cs` | 1–513 | Full file — ESP32 UI + all flows |
| 3 | `Assets/Scripts/Vehicle/VehicleQueue.cs` | 168–230 | AutoSpawnVehicle method |
| 4 | `Assets/Scripts/Core/ParkingManager.cs` | 260–380 | SpawnVehicle + SpawnVehiclePreCheckedIn |
| 5 | `Assets/Scripts/Vehicle/VehicleController.cs` | 30–110 | Initialize + StartEntry + StartDeparture |
| 6 | `Assets/Scripts/API/ApiService.cs` | 47–48, 236–297, 406–430 | URL builders + ESP32 endpoints |
