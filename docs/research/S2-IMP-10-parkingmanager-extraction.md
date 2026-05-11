# Research Report: S2-IMP-10 — ParkingManager.cs Extraction Analysis

**Task:** S2-IMP-10 | **Date:** 2026-04-16 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Line count:** ParkingManager.cs = **756 dòng** (lines 1-756), vượt limit 300 theo coding standards
> 2. **Reflection hack tồn tại:** Lines 122-132 dùng `GetField` để set private `barrierArm` — cần public property
> 3. **7 coroutine dùng `while(!done)`:** Lines 156, 167, 177, 522, 596, 644 + 4 `WaitUntil` không có timeout
> 4. **Existing helper:** `WaitWithTimeout` đã có trong `ESP32Simulator.cs:580-588` — extract sang `CoroutineHelpers` chung
> 5. **Safe extraction order:** BarrierController fix → CoroutineHelpers → ParkingDataSync → GateFlowController → StaticVehicleSpawner

---

## 2. Current ParkingManager Structure Map

### 2.1 Line Count Breakdown

| Range   | Lines | Concern                                                | Candidate for Extraction             |
| ------- | ----- | ------------------------------------------------------ | ------------------------------------ |
| 1-14    | 14    | Using statements + namespace                           | Stay                                 |
| 15-42   | 28    | Class declaration + SerializedFields                   | Stay (Singleton core)                |
| 43-51   | 9     | Fields: events, cached data                            | Stay                                 |
| 52-67   | 16    | **Awake()** — DI/Find logic                            | → `ParkingManagerBootstrap`          |
| 68-111  | 44    | **Start()** coroutine — bootstrap                      | → `ParkingDataSync`                  |
| 112-137 | 26    | **AutoLinkBarrierArms()** — REFLECTION HACK            | → Fix in `BarrierController`         |
| 138-145 | 8     | OnDestroy()                                            | Stay                                 |
| 146-162 | 17    | **Login()** coroutine                                  | → `ParkingDataSync`                  |
| 163-182 | 20    | **FetchParkingData()** coroutine                       | → `ParkingDataSync`                  |
| 183-220 | 38    | **MapApiDataToSlots()**                                | → `ParkingDataSync` (mapping)        |
| 221-268 | 48    | **SpawnStaticParkedVehicle()** + **AttachPlateText()** | → `StaticVehicleSpawner`             |
| 269-284 | 16    | HandleSlotStatusUpdate()                               | → `ParkingDataSync` (WS handler)     |
| 285-335 | 51    | **PollSlotsCoroutine()**                               | → `ParkingDataSync`                  |
| 336-386 | 51    | **SpawnVehicle()**                                     | Stay (public API for ESP32Simulator) |
| 387-397 | 11    | HandleVehicleAtEntry()                                 | → `GateFlowController`               |
| 398-423 | 26    | **CheckInWaitingVehicle()**                            | → `GateFlowController`               |
| 424-483 | 60    | **CheckInWithANPR()** coroutine                        | → `GateFlowController`               |
| 484-526 | 43    | SpawnVehiclePreCheckedIn()                             | Stay (public API)                    |
| 527-558 | 32    | **ESP32CheckInFlow()** coroutine                       | → `GateFlowController`               |
| 559-592 | 34    | HandleVehicleParked() + VerifySlotFlow()               | → `GateFlowController`               |
| 593-612 | 20    | VerifySlotFlow() continuation                          | → `GateFlowController`               |
| 613-620 | 8     | DepartureTimer()                                       | Stay                                 |
| 621-662 | 42    | HandleVehicleAtExit() + **ESP32CheckOutFlow()**        | → `GateFlowController`               |
| 663-680 | 18    | HandleVehicleGone()                                    | Stay                                 |
| 681-705 | 25    | ApplyMockStatuses()                                    | → `StaticVehicleSpawner`             |
| 706-720 | 15    | GetSlotStats()                                         | Stay (utility)                       |
| 721-740 | 20    | HandleCheckinSuccess() (WS)                            | → `GateFlowController`               |
| 741-756 | 16    | OpenSlotBarrier() + AnimateSlotBarrier()               | Stay (slot barrier animation)        |

### 2.2 Method List Grouped by Concern

```
ParkingManager.cs (756 lines)
│
├── 🔧 BOOTSTRAP & DI (~42 lines) ─────────────────────────────────
│   ├── Awake() [52-67]           → ParkingManagerBootstrap.cs
│   └── AutoLinkBarrierArms() [112-137] → FIX BarrierController
│
├── 📡 DATA SYNC / LOGIN / FETCH / POLL / WS (~176 lines) ─────────
│   ├── Start() [68-111]          → Orchestrate via ParkingDataSync
│   ├── Login() [146-162]         → ParkingDataSync.LoginCoroutine()
│   ├── FetchParkingData() [163-182] → ParkingDataSync.FetchDataCoroutine()
│   ├── MapApiDataToSlots() [183-220] → ParkingDataSync.ApplySlotMapping()
│   ├── HandleSlotStatusUpdate() [269-284] → ParkingDataSync (event handler)
│   └── PollSlotsCoroutine() [285-335] → ParkingDataSync.StartPolling()
│
├── 🚗 GATE FLOW (CHECK-IN/OUT/ANPR) (~230 lines) ─────────────────
│   ├── HandleVehicleAtEntry() [387-397] → GateFlowController
│   ├── CheckInWaitingVehicle() [398-423] → GateFlowController
│   ├── CheckInWithANPR() [424-483] → GateFlowController
│   ├── ESP32CheckInFlow() [527-558] → GateFlowController
│   ├── HandleVehicleParked() [559-592] → GateFlowController
│   ├── VerifySlotFlow() [593-612] → GateFlowController
│   ├── HandleVehicleAtExit() [621-634] → GateFlowController
│   ├── ESP32CheckOutFlow() [635-662] → GateFlowController
│   └── HandleCheckinSuccess() [721-740] → GateFlowController
│
├── 🚙 STATIC VEHICLE SPAWNING (~73 lines) ────────────────────────
│   ├── SpawnStaticParkedVehicle() [221-262] → StaticVehicleSpawner
│   ├── AttachPlateText() [263-268] → StaticVehicleSpawner
│   └── ApplyMockStatuses() [681-705] → StaticVehicleSpawner
│
└── 📌 KEEP IN PARKINGMANAGER (~235 lines) ────────────────────────
    ├── Singleton + SerializedFields [15-51]
    ├── OnDestroy() [138-145]
    ├── SpawnVehicle() [336-386]      ← Public API (keep)
    ├── SpawnVehiclePreCheckedIn() [484-526] ← Public API (keep)
    ├── DepartureTimer() [613-620]
    ├── HandleVehicleGone() [663-680]
    ├── GetSlotStats() [706-720]
    └── OpenSlotBarrier() + AnimateSlotBarrier() [741-756]
```

---

## 3. Risk Hotspots

### 3.1 Reflection Hack (MUST FIX FIRST)

**Location:** [ParkingManager.cs](ParkingSimulatorUnity/Assets/Scripts/Core/ParkingManager.cs#L112-L137)

```csharp
// Lines 122-132 — REFLECTION accessing private field
var field = typeof(BarrierController).GetField("barrierArm",
    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
if (field == null) return;

if (entryBarrier != null && entryPivot != null)
{
    field.SetValue(entryBarrier, entryPivot.transform);  // ❌ Bypasses encapsulation
    Debug.Log("[ParkingManager] Linked entry barrier arm");
}
```

**Why risky:**

- Stripping/obfuscation breaks reflection
- No compile-time check if field name changes
- Unity serialization of private field is unreliable across builds

**Fix required in BarrierController.cs:**

```csharp
// Assets/Scripts/Parking/BarrierController.cs — add property
public Transform Arm
{
    get => barrierArm;
    set => barrierArm = value;
}
```

### 3.2 SerializedFields (Dependencies to Wire)

**All dependencies in ParkingManager must stay wired in Inspector:**

| Field                   | Type                  | Used By                        | Risk if Moved                                    |
| ----------------------- | --------------------- | ------------------------------ | ------------------------------------------------ |
| `config`                | ApiConfig             | All sync + spawn               | Must pass to extracted classes                   |
| `apiService`            | ApiService            | Every API call                 | Must pass to ParkingDataSync, GateFlowController |
| `authManager`           | AuthManager           | Login()                        | Must pass to ParkingDataSync                     |
| `generator`             | ParkingLotGenerator   | MapApiDataToSlots, SpawnStatic | Must pass to StaticVehicleSpawner                |
| `waypointGraph`         | WaypointGraph         | SpawnVehicle                   | Keep in ParkingManager                           |
| `entryBarrier`          | BarrierController     | Check-in flow                  | Must pass to GateFlowController                  |
| `exitBarrier`           | BarrierController     | Check-out flow                 | Must pass to GateFlowController                  |
| `vehicleQueue`          | VehicleQueue          | HandleVehicleGone              | Keep in ParkingManager                           |
| `carPrefab`             | GameObject            | SpawnVehicle, SpawnStatic      | Must pass to StaticVehicleSpawner                |
| `motorbikePrefab`       | GameObject            | SpawnVehicle, SpawnStatic      | Must pass to StaticVehicleSpawner                |
| `vehicleSpawnPoint`     | Transform             | SpawnVehicle                   | Keep in ParkingManager                           |
| `virtualCameraManager`  | VirtualCameraManager  | ANPR flow                      | Must pass to GateFlowController                  |
| `slotOccupancyDetector` | SlotOccupancyDetector | Start()                        | Keep in ParkingManager                           |

### 3.3 Events (External Subscribers)

| Event                           | Publisher      | Subscribers    | Risk                               |
| ------------------------------- | -------------- | -------------- | ---------------------------------- |
| `OnInitComplete`                | ParkingManager | External (UI?) | Keep in ParkingManager             |
| `OnStatusMessage`               | ParkingManager | External (UI?) | Keep in ParkingManager             |
| `apiService.OnSlotStatusUpdate` | ApiService     | ParkingManager | Move handler to ParkingDataSync    |
| `apiService.OnCheckinSuccess`   | ApiService     | ParkingManager | Move handler to GateFlowController |

### 3.4 `while(!done) yield return null` Loops Without Timeout

| Line | Method                      | Duration Risk                        |
| ---- | --------------------------- | ------------------------------------ |
| 156  | Login()                     | Auth service down → infinite hang    |
| 167  | FetchParkingData() (slots)  | Parking service down → hang Start()  |
| 177  | FetchParkingData() (floors) | Parking service down → hang Start()  |
| 522  | ESP32CheckInFlow()          | AI service down → hang at gate       |
| 596  | VerifySlotFlow()            | `WaitUntil(() => done)` — no timeout |
| 644  | ESP32CheckOutFlow()         | AI service down → hang at exit       |

**Existing helper in ESP32Simulator.cs:580-588:**

```csharp
private IEnumerator WaitWithTimeout(Func<bool> condition, float timeoutSec, Action onTimeout)
{
    float elapsed = 0f;
    while (!condition() && elapsed < timeoutSec)
    {
        elapsed += Time.deltaTime;
        yield return null;
    }
    if (!condition()) onTimeout?.Invoke();
}
```

**Action:** Extract to `CoroutineHelpers.cs` và reuse ở cả ESP32Simulator + ParkingManager.

---

## 4. Exact Candidates for Extraction

### 4.1 New File: `Assets/Scripts/Core/Bootstrap/ParkingManagerBootstrap.cs`

**Từ ParkingManager.cs:**

- Lines 52-67 (`Awake()` dependency resolution logic)
- Create `DependencyResolver` helper with `FindOrLoad<T>()` pattern

**Expected size:** ~60 lines

### 4.2 New File: `Assets/Scripts/Core/Sync/ParkingDataSync.cs`

**Từ ParkingManager.cs:**

- Lines 146-162 (`Login()`)
- Lines 163-182 (`FetchParkingData()`)
- Lines 183-220 (`MapApiDataToSlots()`)
- Lines 269-284 (`HandleSlotStatusUpdate()`)
- Lines 285-335 (`PollSlotsCoroutine()`)

**Expected size:** ~180 lines

**Interface:**

```csharp
public class ParkingDataSync : MonoBehaviour
{
    public List<SlotData> CachedSlots { get; }
    public List<FloorData> CachedFloors { get; }
    public event Action<List<SlotData>> OnSlotsUpdated;

    public IEnumerator Initialize(ApiConfig config, AuthManager auth, ApiService api);
    public void StartPolling();
    public void StopPolling();
}
```

### 4.3 New File: `Assets/Scripts/Core/Flow/GateFlowController.cs`

**Từ ParkingManager.cs:**

- Lines 387-397 (`HandleVehicleAtEntry()`)
- Lines 398-423 (`CheckInWaitingVehicle()`)
- Lines 424-483 (`CheckInWithANPR()`)
- Lines 527-558 (`ESP32CheckInFlow()`)
- Lines 559-612 (`HandleVehicleParked()` + `VerifySlotFlow()`)
- Lines 621-662 (`HandleVehicleAtExit()` + `ESP32CheckOutFlow()`)
- Lines 721-740 (`HandleCheckinSuccess()`)

**Expected size:** ~220 lines

**Interface:**

```csharp
public class GateFlowController : MonoBehaviour
{
    public void Initialize(ApiConfig config, ApiService api, VirtualCameraManager cams,
                          BarrierController entry, BarrierController exit);
    public void HandleVehicleAtGate(VehicleController vehicle);
    public bool CheckInWaitingVehicle(string plate);
    public void OnCheckinSuccess(CheckinSuccessData data);
}
```

### 4.4 New File: `Assets/Scripts/Core/Spawn/StaticVehicleSpawner.cs`

**Từ ParkingManager.cs:**

- Lines 221-268 (`SpawnStaticParkedVehicle()` + `AttachPlateText()`)
- Lines 681-705 (`ApplyMockStatuses()`)

**Expected size:** ~100 lines

**Interface:**

```csharp
public class StaticVehicleSpawner : MonoBehaviour
{
    public void Initialize(ParkingLotGenerator gen, GameObject carPrefab, GameObject motoPrefab);
    public void SpawnForOccupiedSlot(ParkingSlot slot, string plateNumber);
    public void ApplyMockStatuses();
}
```

### 4.5 New File: `Assets/Scripts/Utility/CoroutineHelpers.cs`

**Extract từ ESP32Simulator.cs:580-588 và generalize:**

```csharp
using System;
using System.Collections;
using UnityEngine;

namespace ParkingSim.Utility
{
    public static class CoroutineHelpers
    {
        public static IEnumerator WaitUntilOrTimeout(
            Func<bool> condition,
            float timeoutSeconds,
            Action onTimeout = null,
            string debugLabel = null)
        {
            float elapsed = 0f;
            while (!condition() && elapsed < timeoutSeconds)
            {
                elapsed += Time.deltaTime;
                yield return null;
            }
            if (!condition())
            {
                onTimeout?.Invoke();
                if (!string.IsNullOrEmpty(debugLabel))
                    Debug.LogWarning($"[CoroutineHelpers] Timeout after {timeoutSeconds}s: {debugLabel}");
            }
        }
    }
}
```

**Usage refactor:**

```csharp
// Before:
bool done = false;
StartCoroutine(apiService.GetSlots(..., r => { result = r; done = true; }));
while (!done) yield return null;

// After:
bool done = false;
StartCoroutine(apiService.GetSlots(..., r => { result = r; done = true; }));
yield return CoroutineHelpers.WaitUntilOrTimeout(
    () => done, 10f, () => Debug.LogError("GetSlots timeout"), "GetSlots"
);
if (!done) yield break;
```

---

## 5. Step-by-Step Implementation Sequence

**Estimated time:** 2 ngày (như plan gốc)

### Day 1 Morning: Fix Foundation

| Step | Task                                                                    | Lines Affected                | Test                            |
| ---- | ----------------------------------------------------------------------- | ----------------------------- | ------------------------------- |
| 1    | **Fix BarrierController.cs** — add `public Transform Arm { get; set; }` | +4 lines                      | Unit test barrier linking       |
| 2    | **Fix AutoLinkBarrierArms()** — replace reflection with property        | -10 lines (delete reflection) | Play mode test gates open/close |

### Day 1 Afternoon: Extract Utilities

| Step | Task                                                        | Files               | Test                       |
| ---- | ----------------------------------------------------------- | ------------------- | -------------------------- |
| 3    | Create `Assets/Scripts/Utility/` folder                     | New folder          | —                          |
| 4    | Create `CoroutineHelpers.cs` with `WaitUntilOrTimeout()`    | New file ~30 lines  | Unit test timeout behavior |
| 5    | Update `ESP32Simulator.cs` to use shared helper             | -8 lines, add using | E2E check-in test          |
| 6    | Update ParkingManager `while(!done)` → `WaitUntilOrTimeout` | ~6 replacements     | Play mode full flow        |

### Day 2 Morning: Extract Data Sync

| Step | Task                                                | Files               | Test                       |
| ---- | --------------------------------------------------- | ------------------- | -------------------------- |
| 7    | Create `Assets/Scripts/Core/Sync/` folder           | New folder          | —                          |
| 8    | Create `ParkingDataSync.cs`                         | New file ~180 lines | Unit test Login, FetchData |
| 9    | Move methods from ParkingManager to ParkingDataSync | Edit ParkingManager | Integration test data flow |
| 10   | Wire ParkingDataSync in ParkingManager.Start()      | Edit ParkingManager | Play mode: slots load      |

### Day 2 Afternoon: Extract Flows

| Step | Task                                       | Files               | Test                                |
| ---- | ------------------------------------------ | ------------------- | ----------------------------------- |
| 11   | Create `Assets/Scripts/Core/Flow/` folder  | New folder          | —                                   |
| 12   | Create `GateFlowController.cs`             | New file ~220 lines | Unit test ANPR flow                 |
| 13   | Move gate methods from ParkingManager      | Edit ParkingManager | Play mode: gate open/close          |
| 14   | Create `Assets/Scripts/Core/Spawn/` folder | New folder          | —                                   |
| 15   | Create `StaticVehicleSpawner.cs`           | New file ~100 lines | Unit test static spawn              |
| 16   | Move spawn methods from ParkingManager     | Edit ParkingManager | Play mode: occupied slots have cars |

### Final: Verification

| Step | Task                               | Expected Result                                          |
| ---- | ---------------------------------- | -------------------------------------------------------- |
| 17   | Run `wc -l` on all extracted files | Each < 300 lines                                         |
| 18   | Run `wc -l` on ParkingManager.cs   | ≤ 250 lines                                              |
| 19   | Run full E2E flow in Unity         | Login → Slots → SpawnVehicle → CheckIn → Park → CheckOut |
| 20   | Run EditMode tests                 | All pass                                                 |

---

## 6. Final File Structure After Extraction

```
Assets/Scripts/
├── Core/
│   ├── ParkingManager.cs           # ≤ 250 lines (Singleton + public API)
│   ├── FloorVisibilityManager.cs   # Unchanged
│   ├── Bootstrap/
│   │   └── ParkingManagerBootstrap.cs  # (optional, can inline in Awake)
│   ├── Sync/
│   │   └── ParkingDataSync.cs      # ~180 lines
│   ├── Flow/
│   │   └── GateFlowController.cs   # ~220 lines
│   └── Spawn/
│       └── StaticVehicleSpawner.cs # ~100 lines
├── Parking/
│   └── BarrierController.cs        # +4 lines (Arm property)
└── Utility/
    └── CoroutineHelpers.cs         # ~30 lines (shared timeout helper)
```

---

## 7. Checklist cho Implementer

- [ ] FIX `BarrierController.cs`: add `public Transform Arm { get; set; }`
- [ ] DELETE reflection code in ParkingManager lines 122-132
- [ ] CREATE `Assets/Scripts/Utility/CoroutineHelpers.cs`
- [ ] REPLACE 7x `while(!done)` / `WaitUntil` with `WaitUntilOrTimeout`
- [ ] CREATE `Assets/Scripts/Core/Sync/ParkingDataSync.cs`
- [ ] MOVE Login, FetchParkingData, MapApiDataToSlots, HandleSlotStatusUpdate, PollSlotsCoroutine
- [ ] CREATE `Assets/Scripts/Core/Flow/GateFlowController.cs`
- [ ] MOVE HandleVehicleAtEntry, CheckInWaitingVehicle, CheckInWithANPR, ESP32CheckInFlow, HandleVehicleParked, VerifySlotFlow, HandleVehicleAtExit, ESP32CheckOutFlow, HandleCheckinSuccess
- [ ] CREATE `Assets/Scripts/Core/Spawn/StaticVehicleSpawner.cs`
- [ ] MOVE SpawnStaticParkedVehicle, AttachPlateText, ApplyMockStatuses
- [ ] VERIFY ParkingManager.cs ≤ 250 lines
- [ ] RUN Unity Play mode full E2E
- [ ] RUN EditMode tests

---

## 8. Nguồn

| #   | File                                                                                      | Mô tả                                      |
| --- | ----------------------------------------------------------------------------------------- | ------------------------------------------ |
| 1   | [ParkingManager.cs](ParkingSimulatorUnity/Assets/Scripts/Core/ParkingManager.cs)          | Main analysis target — 756 lines           |
| 2   | [BarrierController.cs](ParkingSimulatorUnity/Assets/Scripts/Parking/BarrierController.cs) | Reflection target — 90 lines               |
| 3   | [ESP32Simulator.cs](ParkingSimulatorUnity/Assets/Scripts/IoT/ESP32Simulator.cs)           | Existing WaitWithTimeout helper — line 580 |
| 4   | [FULL-REVIEW-FIX-PLAN-2026-04-15.md](docs/plans/FULL-REVIEW-FIX-PLAN-2026-04-15.md#L2621) | Original plan for S2-IMP-10                |
| 5   | [parking-simulator-context.md](/memories/repo/parking-simulator-context.md)               | Project context from memory                |
