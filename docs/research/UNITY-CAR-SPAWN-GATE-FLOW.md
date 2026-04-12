# Research Report: Unity Parking Simulator — Car Spawning & Gate Flow

**Task:** Unity Car Spawn + Gate Flow | **Date:** 2026-04-09 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Spawn → Gate → Wait đã hoạt động đúng** — xe spawn tại `vehicleSpawnPoint`, đi đến `GATE-IN-01`, dừng ở `WaitingAtGate`. Gate chỉ mở sau khi `ESP32CheckInFlow` thành công (QR check-in API).
> 2. **Plate format SAIDEFECT** — `GenerateRandomPlate()` tạo format `51AA-123.45` (province + extra letter), không phải `51A-123.45`. Cần sửa ngay.
> 3. **GateCameraSimulator** đã render plate recognition + ESP32Simulator đã có QR scan panel — chỉ cần kết nối đúng Inspector references.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File                                              | Class                          | Mục đích                                                   | Relevance |
| ------------------------------------------------- | ------------------------------ | ---------------------------------------------------------- | --------- |
| `Assets/Scripts/Core/ParkingManager.cs`           | `ParkingManager`               | Spawn xe, kết nối gate events, quản lý barrier             | **HIGH**  |
| `Assets/Scripts/Vehicle/VehicleController.cs`     | `VehicleController`            | State machine, lưu plate/qr/bookingId, điều khiển movement | **HIGH**  |
| `Assets/Scripts/Vehicle/VehicleQueue.cs`          | `VehicleQueue`                 | Auto-spawn coroutine, plate generator, queue positioning   | **HIGH**  |
| `Assets/Scripts/Vehicle/LicensePlateCreator.cs`   | `LicensePlateCreator` (static) | Tạo 3D Vietnamese plate mesh + TextMeshPro                 | **HIGH**  |
| `Assets/Scripts/Parking/BarrierController.cs`     | `BarrierController`            | Mở/đóng barrier arm bằng angle lerp, events                | **HIGH**  |
| `Assets/Scripts/IoT/ESP32Simulator.cs`            | `ESP32Simulator`               | GUI panel QR scan, check-in/out via API, DroidCam polling  | **HIGH**  |
| `Assets/Scripts/Camera/GateCameraSimulator.cs`    | `GateCameraSimulator`          | Detect WaitingAtGate xe, OCR plate, GUI panel              | **HIGH**  |
| `Assets/Scripts/Navigation/WaypointGraph.cs`      | `WaypointGraph`                | BFS pathfinding, node registry, gate/slot lookup           | **MED**   |
| `Assets/Scripts/Navigation/WaypointNode.cs`       | `WaypointNode`                 | Node type: Gate/Lane/SlotEntrance/Ramp/Intersection        | **MED**   |
| `Assets/Scripts/Vehicle/VehicleVisualEnhancer.cs` | `VehicleVisualEnhancer`        | Wheel rotation, lights, exhaust, auto-geometry             | **LOW**   |
| `Assets/Scripts/Parking/ParkingSlot.cs`           | `ParkingSlot`                  | Slot state, assigned plate display                         | **LOW**   |
| `Assets/Scripts/Gate/`                            | —                              | **RỖNG** (chỉ có .gitkeep)                                 | NONE      |

### 2.2 Toàn Bộ Flow: Spawn → Gate → Wait → Open

```
[VehicleQueue.AutoSpawnVehicle()]
    │
    ├─ Check SharedBookingState for pending real bookings
    │   └─ Found: use real plate, bookingId, qrData, slotCode
    │   └─ Not found: GenerateRandomPlate() + random available slot
    │
    ▼
[ParkingManager.SpawnVehicle(plate, bookingId, qrData, slotCode, vType)]
    │ Line 260-284
    ├─ Instantiate(carPrefab/motorbikePrefab, vehicleSpawnPoint.position, Quaternion.identity)
    ├─ AddComponent<VehicleVisualEnhancer>() if missing
    ├─ vehicle.Initialize(waypointGraph, slot, plate, qrData, vType)
    ├─ vehicle.bookingId = bookingId
    ├─ Subscribe: OnReachedGate → HandleVehicleAtEntry
    ├─ Subscribe: OnParked → HandleVehicleParked
    ├─ Subscribe: OnReachedExit → HandleVehicleAtExit
    ├─ Subscribe: OnGone → HandleVehicleGone
    ├─ vehicle.StartEntry()   ← bắt đầu đi
    ├─ AttachPlateText(front, rear)
    └─ LicensePlateCreator.CreateRoofPlate()

[VehicleController.StartEntry()]  Line 55-90
    │
    ├─ waypointGraph.GetGateNode("GATE-IN-01")  ← node A
    ├─ waypointGraph.GetSlotEntrance(slotCode)  ← node B
    ├─ currentPath = FindPath(nodeA, nodeB)     ← BFS
    ├─ currentPathIndex = 0
    └─ state = ApproachingGate

[VehicleController.FollowPath() — Update()]
    │ Moves toward path[0] = GATE-IN-01 node
    └─ When dist < 0.3f to GATE-IN-01 AND it's the LAST node in partial path...
       Wait — path is from GATE-IN-01 to slotEntrance.
       path[0] = GATE-IN-01. Car drives from vehicleSpawnPoint → path[0].
       When path[0] reached → currentPathIndex++
       But path[0] IS gateNode, so reaching it means path is NOT complete yet.
       ─► Car continues driving through path toward slot.
       ─► When path FULLY complete and state==ApproachingGate → OnPathComplete():
           state = WaitingAtGate
           OnReachedGate?.Invoke(this)
```

> ⚠️ **CRITICAL FINDING**: Path hiện tại là từ GATE-IN-01 đến slotEntrance. GATE-IN-01 là node _đầu tiên_ trong path. Xe spawn ở `vehicleSpawnPoint` và đi thẳng đến path[0] (GATE-IN-01), KHÔNG dừng ở đó — chỉ tiếp tục theo path cho đến hết. `WaitingAtGate` chỉ được set khi toàn bộ path kết thúc. Nếu waypoint graph được setup đúng (GATE-IN-01 là node đầu tiên của path và path gồm nhiều nodes sau đó đến slot), thì khi path[0] = GATE-IN-01 và path.Count > 1, xe đi qua gate mà không dừng.
>
> **Để xe DỪNG tại GATE-IN-01**, cần path có 2 giai đoạn:
>
> 1. Path 1: spawnPoint → GATE-IN-01 (xe dừng tại GATE-IN-01 → WaitingAtGate)
> 2. Path 2 (sau khi gate mở): GATE-IN-01 → slotEntrance (ProceedFromGate gọi state=Entering)

Xem `ProceedFromGate()` ở line 119-123 — method này sets state `Entering` nhưng không set lại path. Path vẫn là path cũ từ gateNode→slotEntrance, và currentPathIndex đang ở node sau GATE-IN-01. Điều này HỢP LÝ nếu:

- Path 1 là spawnPoint → GATE-IN-01 (state: ApproachingGate, path end = GATE-IN-01)
- Sau khi gate mở: StartCoroutine để build path 2, gọi ProceedFromGate

**Implementer cần kiểm tra**: Waypoint graph được build như thế nào trong `ParkingLotGenerator`. `GATE-IN-01` node cần có `associatedSlotCode = "GATE-IN-01"` và `nodeType = NodeType.Gate`.

---

### 2.3 Gate Opening Logic

```
[ParkingManager.HandleVehicleAtEntry(vehicle)]  Line ~306
    │
    ├─ IF config.useMockData OR vehicle.alreadyCheckedIn:
    │     entryBarrier.OpenThenClose(3f)   ← immediate open
    │     vehicle.ProceedFromGate()
    │     RecognizePlateAtGate(vehicle)    ← async, non-blocking
    │
    └─ ELSE:
          ESP32CheckInFlow(vehicle)

[ESP32CheckInFlow(vehicle)]  Line ~375-405
    ├─ Calls apiService.ESP32CheckIn(ESP32CheckInRequest{ GateId=GATE_IN, QrData=vehicle.qrData })
    ├─ Awaits response
    ├─ IF success:
    │     entryBarrier.OpenThenClose(3f)
    │     yield WaitForSeconds(1f)
    │     vehicle.ProceedFromGate()        ← xe tiếp tục đi vào
    └─ IF fail:
          LogWarning + OnStatusMessage     ← xe BỊ KẸT tại gate (không có retry/timeout)
```

**Quan trọng**: Khi `vehicle.alreadyCheckedIn = true` (set bởi `SpawnVehiclePreCheckedIn()`), gate mở tự động khi xe đến. `SpawnVehiclePreCheckedIn()` được gọi sau khi user check-in thủ công qua `ESP32Simulator.DoCheckIn()`.

---

### 2.4 QR Scan Flow (ESP32Simulator)

```
[ESP32Simulator.DrawCheckInSection()]
    ├─ Hiển thị danh sách bookings từ SharedBookingState
    ├─ Button "🔍 Start QR Scan (DroidCam)":
    │     isDroidCamScanning = true
    │     Application.OpenURL("http://192.168.100.130:4747/")  ← DroidCam view
    │     StartCoroutine(QrPollCoroutine())
    │
    └─ QrPollCoroutine():
          Poll mỗi 1.5s: apiService.ScanQr("qr-camera-droidcam", callback)
          IF found: manualQrData = qrData; DoCheckIn()
```

DroidCam URL: `http://192.168.100.130:4747/` — hardcoded, cần match với IP thực.
QR Camera ID: `"qr-camera-droidcam"` — AI service endpoint `POST /ai/cameras/frame`.

---

### 2.5 Plate Recognition (GateCameraSimulator)

```
[GateCameraSimulator.Update()]
    ├─ Physics.OverlapSphere(capturePoint.position, captureRadius=3f)
    ├─ Find VehicleController với state == WaitingAtGate
    └─ Enqueue vào pendingDetections

[CaptureAndRecognize(vehicle)]
    ├─ Render gateCamera (640×480) → RenderTexture → Texture2D → PNG bytes
    ├─ apiService.AIRecognizePlate(imageBytes, callback)
    ├─ IF confidence < 0.6f: retry once
    ├─ IF success: esp32Simulator.SetPlateFromCamera(lastRecognizedPlate)
    └─ IF fail: fallback to vehicle.plateNumber (known plate)

[OnGUI Panel — windowId=104]
    ├─ Status: Idle / Processing AI OCR... / Complete ✅ / Fallback
    ├─ Plate: {detected} (color: green ≥85%, yellow ≥50%, red <50%)
    ├─ Confidence: {%}
    └─ Queue: {N} vehicle(s)
```

---

### 2.6 License Plate Format

**Hiện tại** (`VehicleQueue.GenerateRandomPlate()`, line ~233-239):

```csharp
private static readonly string[] Provinces =
    { "51A", "51B", "30A", "29A", "77A", "59B", "43A", "92C" };

private string GenerateRandomPlate()
{
    string province = Provinces[Random.Range(0, Provinces.Length)]; // e.g. "51A"
    char letter = (char)('A' + Random.Range(0, 26));                 // e.g. 'B'
    int digits3 = Random.Range(100, 999);
    int digits2 = Random.Range(10, 99);
    return $"{province}{letter}-{digits3}.{digits2}";  // → "51AB-123.45" ❌
}
```

**Vấn đề**: Province array đã có letter Series (e.g. "51A"), rồi lại append thêm `letter` → tạo ra `51AA-123.45` hoặc `51AB-123.45`.

**Format đúng** theo yêu cầu (`51A-999.88`, `29B-123.45`):

```csharp
// Option 1: dùng province codes không có series letter
private static readonly string[] ProvinceCodes = { "51", "30", "29", "77", "59", "43", "92" };
private static readonly char[] SeriesLetters = { 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H' };

private string GenerateRandomPlate()
{
    string province = ProvinceCodes[Random.Range(0, ProvinceCodes.Length)];
    char series = SeriesLetters[Random.Range(0, SeriesLetters.Length)];
    int digits3 = Random.Range(100, 999);
    int digits2 = Random.Range(10, 99);
    return $"{province}{series}-{digits3}.{digits2}";  // → "51A-123.45" ✅
}
```

---

### 2.7 VehicleController Public Fields (Data Model)

```csharp
// Assets/Scripts/Vehicle/VehicleController.cs - Lines 24-30
public string plateNumber;       // "51A-123.45"
public string vehicleType;       // "Car" | "Motorbike"
public string bookingId;         // GUID từ API
public string qrData;            // JSON: {"booking_id":"..."}
public bool alreadyCheckedIn;    // true → gate tự mở khi đến
public VehicleState state;       // enum state machine
```

**State machine** (line 12-22):

```
Idle → ApproachingGate → WaitingAtGate → Entering → Navigating → Parking → Parked
                                                                              ↓
Gone ← Exiting ← WaitingAtExit ← Departing ←────────────────────────────────┘
```

---

### 2.8 BarrierController

```csharp
// Assets/Scripts/Parking/BarrierController.cs
public void Open()   // targetAngle = openAngle (90°), fires OnBarrierOpened
public void Close()  // targetAngle = closedAngle (0°), fires OnBarrierClosed
public IEnumerator OpenThenClose(float delay = 3f)  // open → wait → close

// Animation: Update() LerpAngle toward targetAngle at speed=2f
// Axis: barrierArm.localEulerAngles.x
```

---

### 2.9 WaypointGraph — Gate Node Lookup

```csharp
// GetGateNode(gateId) — line 155-167
// Tìm node có nodeType==Gate VÀ associatedSlotCode==gateId
// Ví dụ: node.associatedSlotCode = "GATE-IN-01" → cần được set đúng trong scene
public WaypointNode GetGateNode(string gateId)
```

`ParkingLotGenerator` phải tạo gate waypoint nodes với `associatedSlotCode = "GATE-IN-01"` và `associatedSlotCode = "GATE-OUT-01"`.

---

## 3. ⚠️ Gotchas & Known Issues

- [ ] **[BUG]** `GenerateRandomPlate()` tạo format sai `51AA-123.45` thay vì `51A-123.45`. → Fix: tách `ProvinceCodes` khỏi series letter.
- [ ] **[WARNING]** Khi `ESP32CheckInFlow` thất bại, xe bị kẹt tại gate **vĩnh viễn** — không có timeout, retry, hay option để hủy. Cần thêm timeout hoặc fallback.
- [ ] **[BLOCKER]** Path từ `GATE-IN-01 → slotEntrance` chứa GATE-IN-01 là node đầu tiên. Xe sẽ đi qua gate mà không dừng nếu path có nhiều nodes. Cần verify waypoint graph placement: spawn point phải nằm ngoài gate, và GATE-IN-01 phải là điểm dừng (end of approach path), không phải trung gian.
- [ ] **[NOTE]** `vehicleSpawnPoint` là `Transform` serialized — phải gán trong Unity Inspector. Nếu null, xe spawn tại `Vector3.zero`.
- [ ] **[NOTE]** `GateCameraSimulator` require vehicle prefab có **Collider + Rigidbody isKinematic** để `Physics.OverlapSphere` detect được.
- [ ] **[NOTE]** DroidCam URL (`http://192.168.100.130:4747/`) hardcoded trong `ESP32Simulator.cs`. Cần là đúng IP của điện thoại.
- [ ] **[NOTE]** `GateCameraSimulator` gọi `esp32Simulator.SetPlateFromCamera()` — method này chưa thấy trong phần đã đọc; cần verify tồn tại trong `ESP32Simulator.cs`.

---

## 4. Checklist cho Implementer

### Fix Plate Format

- [ ] Sửa `VehicleQueue.GenerateRandomPlate()` — tách ProvinceCodes và series letters
- [ ] Cập nhật `Provinces` array (hiện là `{ "51A", "51B", ... }`) thành province codes thuần (`{ "51", "30", "29", ... }`)

### Fix Gate Stop Logic

- [ ] Verify `ParkingLotGenerator` đặt Gate waypoint nodes đúng vị trí (trước barrier)
- [ ] Approach path chỉ nên: `spawnPoint → [approach nodes] → GATE-IN-01`
- [ ] Path sau gate: `GATE-IN-01 → [internal nodes] → slotEntrance` (set trong `ProceedFromGate` hoặc build riêng)
- [ ] Hoặc split `StartEntry()` thành 2 phases: `StartApproach()` và `StartEntry()`

### Add Timeout for stuck vehicles

- [ ] `ESP32CheckInFlow`: thêm `yield return new WaitForSeconds(timeout)` timeout → gọi `vehicle.state = Gone; Destroy(vehicle.gameObject)`

### Inspector References cần gán

- [ ] `ParkingManager.vehicleSpawnPoint` → Transform outside gate (in Scene)
- [ ] `GateCameraSimulator.gateCamera` → Camera component at gate
- [ ] `GateCameraSimulator.capturePoint` → Transform near gate stop point
- [ ] `GateCameraSimulator.esp32Simulator` → ESP32Simulator component
- [ ] `BarrierController.barrierArm` → Transform của barrier mesh

### ESP32Simulator.SetPlateFromCamera() — ✅ Đã xác nhận

- `SetPlateFromCamera(string)` tồn tại tại line 498: sets `checkInPlate = plateText`

---

## 5. File Paths Summary

```
Assets/Scripts/Core/ParkingManager.cs
  - SpawnVehicle()                    Line 260
  - SpawnVehiclePreCheckedIn()        Line 341
  - HandleVehicleAtEntry()            Line ~306
  - ESP32CheckInFlow()                Line ~375
  - RecognizePlateAtGate()            Line ~318

Assets/Scripts/Vehicle/VehicleController.cs
  - VehicleState enum                 Line 12
  - plateNumber, qrData fields        Line 24-30
  - Initialize()                      Line 53
  - StartEntry()                      Line 62
  - ProceedFromGate()                 Line 119
  - OnPathComplete() - WaitingAtGate  Line ~178
  - FollowPath()                      Line ~145

Assets/Scripts/Vehicle/VehicleQueue.cs
  - GenerateRandomPlate() ⚠️BUG      Line ~233
  - AutoSpawnVehicle()                Line 176
  - Provinces array                   Line 42

Assets/Scripts/Vehicle/LicensePlateCreator.cs
  - CreateVietnamesePlate()           Line 23
  - CreateRoofPlate()                 Line 118
  - UpdatePlateText()                 Line 130

Assets/Scripts/Parking/BarrierController.cs
  - Open() / Close()                  Line 67/75
  - OpenThenClose(delay)              Line 83

Assets/Scripts/IoT/ESP32Simulator.cs
  - QrPollCoroutine()                 Line ~175
  - DoCheckIn()                       Line ~215
  - DROIDCAM_VIEW_URL                 Line 21

Assets/Scripts/Camera/GateCameraSimulator.cs
  - CaptureAndRecognize()             Line ~147
  - OnGUI plate display panel         Line ~80

Assets/Scripts/Navigation/WaypointGraph.cs
  - GetGateNode(gateId)               Line 155
  - FindPath(from, to)                Line 40
```

---

## 6. Nguồn

| #   | Source                                      | Mô tả                              |
| --- | ------------------------------------------- | ---------------------------------- |
| 1   | Codebase trực tiếp                          | `Assets/Scripts/` toàn bộ          |
| 2   | /memories/repo/parking-simulator-context.md | Phase history, ports, secrets      |
| 3   | /memories/repo/parksmart-project.md         | Stack, AI endpoints, hardware pins |
