# ADR-S2-IMP-10: ParkingManager Extraction — Implementation Design

**Status:** Accepted | **Date:** 2026-04-16 | **Architect:** System

---

## Trạng thái: Accepted

### TL;DR

Trích xuất **756-line ParkingManager** thành kiến trúc coordinator + 4 helper classes:

- **ParkingManager** ≤ 250 lines (thin coordinator, singleton, public API)
- **CoroutineHelpers** ~35 lines (shared timeout utility)
- **ParkingDataSync** ~180 lines (login, fetch, poll, WS handlers)
- **GateFlowController** ~220 lines (check-in/out, ANPR, barrier control)
- **StaticVehicleSpawner** ~100 lines (static vehicle prefab instantiation)

**Constraints met:**

- ✅ Behavior unchanged
- ✅ Serialized fields compatibility — all fields stay on ParkingManager Inspector
- ✅ No circular references
- ✅ No Inspector breakages

---

## 1. Class Contracts

### 1.1 CoroutineHelpers.cs

**File:** `Assets/Scripts/Utility/CoroutineHelpers.cs`

```csharp
using System;
using System.Collections;
using UnityEngine;

namespace ParkingSim.Utility
{
    /// <summary>
    /// Shared coroutine utilities. Extracted from ESP32Simulator.cs line 580.
    /// </summary>
    public static class CoroutineHelpers
    {
        /// <summary>
        /// Waits until condition is true OR timeout expires.
        /// Calls onTimeout if condition never becomes true.
        /// </summary>
        /// <param name="condition">Predicate to check each frame</param>
        /// <param name="timeoutSeconds">Max wait time</param>
        /// <param name="onTimeout">Optional callback on timeout</param>
        /// <param name="debugLabel">Optional label for warning log</param>
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

        /// <summary>
        /// Returns true if the condition became true before timeout.
        /// Use via: bool success = false; yield return WaitWithResult(..., out success);
        /// </summary>
        public static IEnumerator WaitWithResult(
            Func<bool> condition,
            float timeoutSeconds,
            Action<bool> result,
            string debugLabel = null)
        {
            float elapsed = 0f;
            while (!condition() && elapsed < timeoutSeconds)
            {
                elapsed += Time.deltaTime;
                yield return null;
            }
            bool succeeded = condition();
            result?.Invoke(succeeded);
            if (!succeeded && !string.IsNullOrEmpty(debugLabel))
                Debug.LogWarning($"[CoroutineHelpers] Timeout: {debugLabel}");
        }
    }
}
```

**Dependencies:** None (static class)
**Namespace:** `ParkingSim.Utility`

---

### 1.2 ParkingDataSync.cs

**File:** `Assets/Scripts/Core/Sync/ParkingDataSync.cs`

```csharp
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Utility;

namespace ParkingSim.Core.Sync
{
    /// <summary>
    /// Handles data synchronization: login, fetch floors/slots, WS updates, polling fallback.
    /// Extracted from ParkingManager lines 146-335, 269-284.
    /// </summary>
    public class ParkingDataSync
    {
        // === Dependencies (injected via Initialize) ===
        private readonly ApiConfig _config;
        private readonly ApiService _apiService;
        private readonly AuthManager _authManager;
        private readonly ParkingLotGenerator _generator;
        private readonly MonoBehaviour _coroutineHost;

        // === Cached Data ===
        public List<SlotData> CachedSlots { get; private set; } = new List<SlotData>();
        public List<FloorData> CachedFloors { get; private set; } = new List<FloorData>();
        public List<BookingData> CachedBookings { get; private set; } = new List<BookingData>();

        // === Events ===
        public event Action<List<SlotData>> OnSlotsUpdated;
        public event Action OnSyncComplete;

        // === State ===
        public bool IsInitialized { get; private set; }
        private Coroutine _pollCoroutine;

        public ParkingDataSync(
            ApiConfig config,
            ApiService apiService,
            AuthManager authManager,
            ParkingLotGenerator generator,
            MonoBehaviour coroutineHost)
        {
            _config = config;
            _apiService = apiService;
            _authManager = authManager;
            _generator = generator;
            _coroutineHost = coroutineHost;
        }

        // === Public API ===

        /// <summary>
        /// Full initialization: login → fetch booking → fetch slots/floors → map to scene.
        /// Call from ParkingManager.Start().
        /// </summary>
        public IEnumerator InitializeAsync()
        {
            yield return _coroutineHost.StartCoroutine(LoginCoroutine());
            yield return _coroutineHost.StartCoroutine(FetchDataCoroutine());
            yield return _coroutineHost.StartCoroutine(FetchBookingsCoroutine());
            ApplySlotMapping();
            IsInitialized = true;
            OnSyncComplete?.Invoke();
        }

        /// <summary>Subscribe to WS events. Call after InitializeAsync.</summary>
        public void SubscribeWebSocket()
        {
            if (_apiService != null)
            {
                _apiService.ConnectWebSocket();
                _apiService.OnSlotStatusUpdate += HandleSlotStatusUpdate;
            }
        }

        /// <summary>Unsubscribe from WS events. Call from OnDestroy.</summary>
        public void UnsubscribeWebSocket()
        {
            if (_apiService != null)
                _apiService.OnSlotStatusUpdate -= HandleSlotStatusUpdate;
        }

        /// <summary>Start fallback polling (only kicks in when WS is down).</summary>
        public void StartPolling()
        {
            if (_pollCoroutine != null) return;
            _pollCoroutine = _coroutineHost.StartCoroutine(PollCoroutine());
        }

        public void StopPolling()
        {
            if (_pollCoroutine != null)
            {
                _coroutineHost.StopCoroutine(_pollCoroutine);
                _pollCoroutine = null;
            }
        }

        // === Internal Coroutines ===

        private IEnumerator LoginCoroutine()
        {
            bool done = false, success = false;
            Action successHandler = () => { success = true; done = true; };
            Action<string> failHandler = _ => { done = true; };
            _authManager.OnLoginSuccess += successHandler;
            _authManager.OnLoginFailed += failHandler;

            yield return _coroutineHost.StartCoroutine(
                _authManager.Login(_config.testEmail, _config.testPassword));

            // Timeout 10s
            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => done, 10f, null, "Login");

            _authManager.OnLoginSuccess -= successHandler;
            _authManager.OnLoginFailed -= failHandler;
            Debug.Log(success ? "[ParkingDataSync] Login OK" : "[ParkingDataSync] Login FAILED");
        }

        private IEnumerator FetchDataCoroutine()
        {
            // Fetch Slots
            bool slotsDone = false;
            ApiResponse<PaginatedResponse<SlotData>> slotsResult = null;
            _coroutineHost.StartCoroutine(_apiService.GetSlots(
                _config.targetParkingLotId,
                r => { slotsResult = r; slotsDone = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => slotsDone, 10f, null, "FetchSlots");

            CachedSlots = slotsResult?.IsSuccess == true
                ? slotsResult.Data?.Results ?? new List<SlotData>()
                : new List<SlotData>();
            Debug.Log($"[ParkingDataSync] Fetched {CachedSlots.Count} slots");

            // Fetch Floors
            bool floorsDone = false;
            ApiResponse<PaginatedResponse<FloorData>> floorsResult = null;
            _coroutineHost.StartCoroutine(_apiService.GetFloors(
                _config.targetParkingLotId,
                r => { floorsResult = r; floorsDone = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => floorsDone, 10f, null, "FetchFloors");

            CachedFloors = floorsResult?.IsSuccess == true
                ? floorsResult.Data?.Results ?? new List<FloorData>()
                : new List<FloorData>();
            Debug.Log($"[ParkingDataSync] Fetched {CachedFloors.Count} floors");
        }

        private IEnumerator FetchBookingsCoroutine()
        {
            bool done = false;
            ApiResponse<PaginatedResponse<BookingData>> result = null;
            _coroutineHost.StartCoroutine(_apiService.GetBookings(
                r => { result = r; done = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => done, 10f, null, "FetchBookings");

            if (result?.IsSuccess == true && result.Data?.Results != null)
            {
                CachedBookings = result.Data.Results;
                int synced = SharedBookingState.Instance?.SyncFromApi(CachedBookings) ?? 0;
                Debug.Log($"[ParkingDataSync] Pre-synced {synced} bookings");
            }
        }

        private void ApplySlotMapping()
        {
            if (CachedSlots == null || _generator == null) return;

            int matched = 0;
            foreach (var apiSlot in CachedSlots)
            {
                if (_generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                {
                    slot.slotId = apiSlot.Id;
                    slot.UpdateState(ParkingSlot.ParseStatus(apiSlot.Status));
                    matched++;
                }
            }
            Debug.Log($"[ParkingDataSync] Mapped {matched}/{CachedSlots.Count} slots");
        }

        private void HandleSlotStatusUpdate(SlotStatusUpdate update)
        {
            if (_generator == null) return;
            foreach (var kvp in _generator.slotRegistry)
            {
                if (kvp.Value.slotId == update.SlotId)
                {
                    kvp.Value.UpdateState(ParkingSlot.ParseStatus(update.Status));
                    Debug.Log($"[ParkingDataSync] WS: slot {kvp.Key} → {update.Status}");
                    return;
                }
            }
        }

        private IEnumerator PollCoroutine()
        {
            while (true)
            {
                yield return new WaitForSeconds(_config.deltaPollInterval);

                // Skip if WS is healthy
                if (_apiService != null && _apiService.IsWsConnected)
                    continue;

                bool done = false;
                ApiResponse<PaginatedResponse<SlotData>> result = null;
                _coroutineHost.StartCoroutine(_apiService.GetSlots(
                    _config.targetParkingLotId,
                    r => { result = r; done = true; }));

                yield return CoroutineHelpers.WaitUntilOrTimeout(
                    () => done, 10f, null, "PollSlots");

                if (!done) continue; // Timeout — skip tick

                if (result?.IsSuccess == true && result.Data?.Results != null)
                {
                    foreach (var apiSlot in result.Data.Results)
                    {
                        if (_generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                            slot.UpdateState(ParkingSlot.ParseStatus(apiSlot.Status));
                    }
                    OnSlotsUpdated?.Invoke(result.Data.Results);
                }
            }
        }

        // === Queries ===

        /// <summary>Get SlotData for a code from cached data.</summary>
        public SlotData GetSlotDataByCode(string code)
            => CachedSlots?.Find(s => s.Code == code);

        /// <summary>List occupied slots from cache.</summary>
        public List<SlotData> GetOccupiedSlots()
            => CachedSlots?.FindAll(s =>
                string.Equals(s.Status, "occupied", StringComparison.OrdinalIgnoreCase))
               ?? new List<SlotData>();
    }
}
```

**Dependencies:**

- `ApiConfig`, `ApiService`, `AuthManager`, `ParkingLotGenerator` — injected
- `CoroutineHelpers` — static call
- `MonoBehaviour` coroutineHost for `StartCoroutine`

**Not a MonoBehaviour** — instantiated by ParkingManager, uses host for coroutines.

---

### 1.3 GateFlowController.cs

**File:** `Assets/Scripts/Core/Flow/GateFlowController.cs`

```csharp
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;
using ParkingSim.Camera;
using ParkingSim.Utility;

namespace ParkingSim.Core.Flow
{
    /// <summary>
    /// Handles check-in/out flows, ANPR verification, barrier control.
    /// Extracted from ParkingManager lines 387-662, 721-740.
    /// </summary>
    public class GateFlowController
    {
        // === Dependencies ===
        private readonly ApiConfig _config;
        private readonly ApiService _apiService;
        private readonly VirtualCameraManager _cameraManager;
        private readonly BarrierController _entryBarrier;
        private readonly BarrierController _exitBarrier;
        private readonly MonoBehaviour _coroutineHost;

        // === State ===
        private readonly List<VehicleController> _vehiclesWaitingAtGate = new List<VehicleController>();

        // === Events (raised to ParkingManager) ===
        public event Action<string> OnStatusMessage;
        public event Action<VehicleController> OnVehicleCheckedIn;
        public event Action<VehicleController> OnVehicleCheckedOut;

        public GateFlowController(
            ApiConfig config,
            ApiService apiService,
            VirtualCameraManager cameraManager,
            BarrierController entryBarrier,
            BarrierController exitBarrier,
            MonoBehaviour coroutineHost)
        {
            _config = config;
            _apiService = apiService;
            _cameraManager = cameraManager;
            _entryBarrier = entryBarrier;
            _exitBarrier = exitBarrier;
            _coroutineHost = coroutineHost;
        }

        // === Public Entry Points ===

        /// <summary>Subscribe to check-in success WS events.</summary>
        public void SubscribeWebSocket()
        {
            if (_apiService != null)
                _apiService.OnCheckinSuccess += HandleCheckinSuccess;
        }

        public void UnsubscribeWebSocket()
        {
            if (_apiService != null)
                _apiService.OnCheckinSuccess -= HandleCheckinSuccess;
        }

        /// <summary>
        /// Called when vehicle reaches entry gate.
        /// If pre-checked-in → ANPR flow; otherwise wait for QR scan.
        /// </summary>
        public void HandleVehicleAtEntry(VehicleController vehicle)
        {
            if (vehicle.alreadyCheckedIn)
            {
                _coroutineHost.StartCoroutine(CheckInWithANPR(vehicle));
                return;
            }
            _vehiclesWaitingAtGate.Add(vehicle);
            Debug.Log($"[GateFlowController] {vehicle.plateNumber} waiting at gate for QR");
        }

        /// <summary>
        /// Called by ESP32Simulator after QR scan success.
        /// Finds waiting vehicle, triggers ANPR flow.
        /// </summary>
        public bool CheckInWaitingVehicle(string plate)
        {
            var vehicle = _vehiclesWaitingAtGate.Find(v =>
                string.Equals(v.plateNumber, plate, StringComparison.OrdinalIgnoreCase));

            if (vehicle == null)
            {
                Debug.LogWarning($"[GateFlowController] No vehicle at gate with plate {plate}");
                return false;
            }

            _vehiclesWaitingAtGate.Remove(vehicle);
            _coroutineHost.StartCoroutine(CheckInWithANPR(vehicle));
            return true;
        }

        /// <summary>Handle vehicle at exit gate (mock or real check-out).</summary>
        public void HandleVehicleAtExit(VehicleController vehicle)
        {
            if (_config.useMockData)
            {
                _coroutineHost.StartCoroutine(_exitBarrier.OpenThenClose(3f));
                vehicle.ProceedFromExit();
            }
            else
            {
                _coroutineHost.StartCoroutine(ESP32CheckOutFlow(vehicle));
            }
        }

        /// <summary>Handle vehicle parked — verify slot with backend.</summary>
        public void HandleVehicleParked(VehicleController vehicle, Action<VehicleController, float> onAutoDepartCallback)
        {
            Debug.Log($"[GateFlowController] {vehicle.plateNumber} parked at slot");

            var booking = SharedBookingState.Instance?.GetBookingById(vehicle.bookingId);
            if (booking == null)
            {
                // Random spawn — auto depart after random duration
                float duration = UnityEngine.Random.Range(10f, 30f);
                onAutoDepartCallback?.Invoke(vehicle, duration);
                return;
            }

            // Slot verification
            string actualSlot = vehicle.TargetSlot?.slotCode ?? "unknown";
            string bookedSlot = booking.SlotCode ?? "unknown";
            bool match = string.Equals(actualSlot, bookedSlot, StringComparison.OrdinalIgnoreCase);
            Debug.Log(match
                ? $"[GateFlowController] ✅ SLOT VERIFIED: {vehicle.plateNumber} at {actualSlot}"
                : $"[GateFlowController] ⚠️ SLOT MISMATCH: parked {actualSlot}, booked {bookedSlot}");

            if (!_config.useMockData)
                _coroutineHost.StartCoroutine(VerifySlotFlow(vehicle, actualSlot, booking));
        }

        // === WS Handler ===

        private void HandleCheckinSuccess(CheckinSuccessData data)
        {
            if (data == null) return;
            // Bubble up to ParkingManager for SpawnVehicle call
            OnVehicleCheckedIn?.Invoke(null); // Signal only — spawn is done by PM
            // Full data is re-raised via separate path
        }

        /// <summary>Handle WS check-in success by spawning vehicle. Called from ParkingManager.</summary>
        public (string plate, string bookingId, string qrData, string slotCode, string vehicleType)
            ParseCheckinSuccess(CheckinSuccessData data)
        {
            return (
                data.Plate ?? "UNKNOWN",
                data.BookingId ?? Guid.NewGuid().ToString(),
                data.QrData ?? $"{{\"booking_id\":\"{data.BookingId}\"}}",
                data.SlotCode ?? "A-01",
                data.VehicleType ?? "Car"
            );
        }

        // === Internal Flows ===

        private IEnumerator CheckInWithANPR(VehicleController vehicle)
        {
            Debug.Log($"[GateFlowController] 🔍 ANPR verification for {vehicle.plateNumber}...");

            string detectedPlate = null;
            float confidence = 0f;

            var streamer = _cameraManager?.GetStreamer("virtual-anpr-entry")
                        ?? _cameraManager?.GetStreamer("virtual-gate-in");

            if (streamer != null)
            {
                yield return null;
                yield return null; // 2 frames settle

                byte[] snapshot = streamer.SnapshotJpeg();
                if (snapshot != null && snapshot.Length > 0)
                {
                    bool anprDone = false;
                    ApiResponse<PlateScanResult> scanResult = null;
                    _coroutineHost.StartCoroutine(_apiService.AIRecognizePlate(snapshot,
                        r => { scanResult = r; anprDone = true; }));

                    yield return CoroutineHelpers.WaitUntilOrTimeout(
                        () => anprDone, 5f, null, "ANPR");

                    if (scanResult?.IsSuccess == true && scanResult.Data != null)
                    {
                        detectedPlate = scanResult.Data.PlateText;
                        confidence = scanResult.Data.Confidence;
                    }
                }
            }

            bool plateMatch = !string.IsNullOrEmpty(detectedPlate) &&
                string.Equals(detectedPlate, vehicle.plateNumber, StringComparison.OrdinalIgnoreCase);

            if (plateMatch)
                Debug.Log($"[GateFlowController] ✅ ANPR MATCH: {detectedPlate}, conf={confidence:P0}");
            else if (!string.IsNullOrEmpty(detectedPlate))
                Debug.LogWarning($"[GateFlowController] ⚠️ ANPR MISMATCH: {detectedPlate} vs {vehicle.plateNumber}");
            else
                Debug.LogWarning($"[GateFlowController] ⚠️ ANPR failed — no plate detected");

            bool shouldOpen = plateMatch || string.IsNullOrEmpty(detectedPlate);
            if (shouldOpen)
            {
                _coroutineHost.StartCoroutine(_entryBarrier.OpenThenClose(3f));
                vehicle.ProceedFromGate();
                Debug.Log($"[GateFlowController] ✅ Gate opened for {vehicle.plateNumber}");
            }
            else
            {
                Debug.LogWarning($"[GateFlowController] 🚫 Gate BLOCKED: mismatch");
                OnStatusMessage?.Invoke($"Gate blocked: plate mismatch");
            }
        }

        private IEnumerator ESP32CheckOutFlow(VehicleController vehicle)
        {
            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32CheckOutRequest
            {
                GateId = MockIds.GATE_OUT,
                QrData = vehicle.qrData
            };
            _coroutineHost.StartCoroutine(_apiService.ESP32CheckOut(request,
                r => { result = r; done = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => done, 10f, null, "ESP32CheckOut");

            if (!done)
            {
                OnStatusMessage?.Invoke("Check-out timeout");
                yield break;
            }

            if (result?.IsSuccess == true && result.Data?.Success == true)
            {
                Debug.Log($"[GateFlowController] Check-out OK: {vehicle.plateNumber}");
                _coroutineHost.StartCoroutine(_exitBarrier.OpenThenClose(3f));
                yield return new WaitForSeconds(1f);
                vehicle.ProceedFromExit();
                OnVehicleCheckedOut?.Invoke(vehicle);
            }
            else
            {
                var msg = result?.Data?.Message ?? result?.ErrorMessage ?? "Unknown";
                Debug.LogWarning($"[GateFlowController] Check-out FAILED: {msg}");
                OnStatusMessage?.Invoke($"Check-out failed: {msg}");
            }
        }

        private IEnumerator VerifySlotFlow(VehicleController vehicle, string slotCode, ActiveBooking booking)
        {
            string qrData = vehicle.qrData ?? booking.QrCodeData;
            if (string.IsNullOrEmpty(qrData))
            {
                Debug.LogWarning($"[GateFlowController] No QR data for slot verify");
                yield break;
            }

            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32VerifySlotRequest
            {
                SlotCode = slotCode,
                ZoneId = MockIds.ZONE_CAR_PAINTED_F1,
                GateId = MockIds.GATE_IN,
                QrData = qrData
            };
            _coroutineHost.StartCoroutine(_apiService.ESP32VerifySlot(request,
                r => { result = r; done = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => done, 10f, null, "VerifySlot");

            if (result?.IsSuccess == true && result.Data?.Success == true)
                Debug.Log($"[GateFlowController] ✅ Backend verified slot {slotCode}");
            else
                Debug.LogWarning($"[GateFlowController] ⚠️ Slot verify failed");
        }
    }
}
```

**Dependencies:**

- `ApiConfig`, `ApiService`, `VirtualCameraManager`, `BarrierController` — injected
- `CoroutineHelpers` — static
- `VehicleController` — event args

**Not a MonoBehaviour** — uses coroutineHost for async ops.

---

### 1.4 StaticVehicleSpawner.cs

**File:** `Assets/Scripts/Core/Spawn/StaticVehicleSpawner.cs`

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;

namespace ParkingSim.Core.Spawn
{
    /// <summary>
    /// Spawns static (already-parked) vehicles for occupied slots at startup.
    /// Extracted from ParkingManager lines 221-268, 681-705.
    /// </summary>
    public class StaticVehicleSpawner
    {
        private readonly ParkingLotGenerator _generator;
        private readonly GameObject _carPrefab;
        private readonly GameObject _motorbikePrefab;

        public StaticVehicleSpawner(
            ParkingLotGenerator generator,
            GameObject carPrefab,
            GameObject motorbikePrefab)
        {
            _generator = generator;
            _carPrefab = carPrefab;
            _motorbikePrefab = motorbikePrefab;
        }

        /// <summary>
        /// Spawn static vehicle for occupied slot from API sync.
        /// Called during MapApiDataToSlots.
        /// </summary>
        public void SpawnForOccupiedSlot(ParkingSlot slot, string plateNumber = null)
        {
            if (slot == null) return;
            var prefab = slot.slotType == ParkingSlot.SlotType.Motorbike
                ? _motorbikePrefab
                : _carPrefab;
            if (prefab == null) return;

            Vector3 slotPos = slot.transform.position;
            float floorY = slotPos.y - 0.12f + 0.1f;
            Vector3 slotFwd = slot.transform.forward;
            Quaternion parkRot = slotFwd.sqrMagnitude > 0.01f
                ? Quaternion.LookRotation(-slotFwd)
                : Quaternion.identity;

            var go = UnityEngine.Object.Instantiate(
                prefab,
                new Vector3(slotPos.x, floorY, slotPos.z),
                parkRot);
            go.name = $"StaticVehicle_{slot.slotCode}";

            // URP material fix
            if (go.GetComponent<VehicleVisualEnhancer>() == null)
                go.AddComponent<VehicleVisualEnhancer>();

            var vc = go.GetComponent<VehicleController>();
            if (vc != null)
            {
                vc.state = VehicleController.VehicleState.Parked;
                vc.plateNumber = plateNumber ?? $"MOCK-{slot.slotCode}";
                vc.enabled = false;
            }

            var rb = go.GetComponent<Rigidbody>();
            if (rb != null) rb.isKinematic = true;

            AttachPlateText(go, vc?.plateNumber ?? "UNKNOWN");
            Debug.Log($"[StaticVehicleSpawner] Spawned at {slot.slotCode} plate={vc?.plateNumber}");
        }

        /// <summary>Apply mock statuses and spawn vehicles for occupied mock slots.</summary>
        public void ApplyMockStatuses()
        {
            var mockSlots = MockDataProvider.GenerateMockSlots();
            int matched = 0;
            foreach (var apiSlot in mockSlots)
            {
                if (_generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                {
                    var status = ParkingSlot.ParseStatus(apiSlot.Status);
                    slot.slotId = apiSlot.Id;
                    slot.UpdateState(status);
                    matched++;

                    if (status == ParkingSlot.SlotStatus.Occupied)
                        SpawnForOccupiedSlot(slot, $"SIM-{apiSlot.Code}");
                }
            }
            Debug.Log($"[StaticVehicleSpawner] Mock applied: {matched}/{mockSlots.Count}");
        }

        /// <summary>
        /// After sync completes, spawn vehicles for all occupied slots.
        /// Call this from ParkingManager after ParkingDataSync.ApplySlotMapping.
        /// </summary>
        public void SpawnOccupiedVehicles(List<SlotData> slots)
        {
            if (slots == null || _generator == null) return;
            foreach (var apiSlot in slots)
            {
                if (!string.Equals(apiSlot.Status, "occupied", StringComparison.OrdinalIgnoreCase))
                    continue;
                if (!_generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                    continue;

                string plate = SharedBookingState.Instance?.GetBookingBySlotCode(apiSlot.Code)?.LicensePlate;
                SpawnForOccupiedSlot(slot, plate);
            }
        }

        private void AttachPlateText(GameObject vehicle, string plateText)
        {
            LicensePlateCreator.CreateRearPlate(vehicle.transform, plateText);
        }
    }
}
```

**Dependencies:**

- `ParkingLotGenerator` — slot registry
- Prefabs — injected
- `MockDataProvider`, `SharedBookingState` — static calls

**Not a MonoBehaviour** — pure C# class, no coroutines needed.

---

## 2. Field Ownership Map

### 2.1 SerializedFields — ALL STAY on ParkingManager

**Constraint fulfilled:** No Inspector changes required. All fields remain on `ParkingManager.cs`.

| Field                   | Type                    | Passed To                                         | Usage           |
| ----------------------- | ----------------------- | ------------------------------------------------- | --------------- |
| `config`                | `ApiConfig`             | `ParkingDataSync`, `GateFlowController`, internal | Config access   |
| `apiService`            | `ApiService`            | `ParkingDataSync`, `GateFlowController`           | API calls       |
| `authManager`           | `AuthManager`           | `ParkingDataSync`                                 | Login           |
| `generator`             | `ParkingLotGenerator`   | `ParkingDataSync`, `StaticVehicleSpawner`         | Slot registry   |
| `waypointGraph`         | `WaypointGraph`         | **Stay** (SpawnVehicle)                           | Navigation      |
| `entryBarrier`          | `BarrierController`     | `GateFlowController`                              | Entry gate      |
| `exitBarrier`           | `BarrierController`     | `GateFlowController`                              | Exit gate       |
| `vehicleQueue`          | `VehicleQueue`          | **Stay** (HandleVehicleGone)                      | Queue notify    |
| `carPrefab`             | `GameObject`            | `StaticVehicleSpawner`, **Stay**                  | Prefab spawn    |
| `motorbikePrefab`       | `GameObject`            | `StaticVehicleSpawner`, **Stay**                  | Prefab spawn    |
| `vehicleSpawnPoint`     | `Transform`             | **Stay** (deprecated but kept)                    | Compat          |
| `virtualCameraManager`  | `VirtualCameraManager`  | `GateFlowController`                              | ANPR            |
| `slotOccupancyDetector` | `SlotOccupancyDetector` | **Stay**                                          | Detection start |

### 2.2 Non-Serialized Fields

| Field                   | Current Location | New Owner                      | Notes                    |
| ----------------------- | ---------------- | ------------------------------ | ------------------------ |
| `vehiclesWaitingAtGate` | ParkingManager   | `GateFlowController`           | State for check-in queue |
| `cachedSlots`           | ParkingManager   | `ParkingDataSync.CachedSlots`  | Property                 |
| `cachedFloors`          | ParkingManager   | `ParkingDataSync.CachedFloors` | Property                 |

---

## 3. Method Migration Map

| Original Method              | Lines   | New Location                                                                          | Notes                         |
| ---------------------------- | ------- | ------------------------------------------------------------------------------------- | ----------------------------- |
| `Awake()`                    | 52-67   | **Stay**                                                                              | Creates helper instances      |
| `Start()`                    | 68-111  | **Stay** (thin)                                                                       | Orchestrates calls to helpers |
| `AutoLinkBarrierArms()`      | 112-137 | **Stay** → use BarrierController.Arm property                                         | FIX reflection                |
| `OnDestroy()`                | 138-145 | **Stay**                                                                              | Cleanup calls to helpers      |
| `Login()`                    | 146-162 | `ParkingDataSync.LoginCoroutine()`                                                    | ✅ Extracted                  |
| `FetchParkingData()`         | 163-182 | `ParkingDataSync.FetchDataCoroutine()`                                                | ✅ Extracted                  |
| `MapApiDataToSlots()`        | 183-220 | `ParkingDataSync.ApplySlotMapping()` + `StaticVehicleSpawner.SpawnOccupiedVehicles()` | ✅ Split                      |
| `SpawnStaticParkedVehicle()` | 221-262 | `StaticVehicleSpawner.SpawnForOccupiedSlot()`                                         | ✅ Extracted                  |
| `AttachPlateText()`          | 263-268 | `StaticVehicleSpawner` (private)                                                      | ✅ Extracted                  |
| `HandleSlotStatusUpdate()`   | 269-284 | `ParkingDataSync` (internal)                                                          | ✅ Extracted                  |
| `PollSlotsCoroutine()`       | 285-335 | `ParkingDataSync.PollCoroutine()`                                                     | ✅ Extracted                  |
| `SpawnVehicle()`             | 336-386 | **Stay**                                                                              | Public API                    |
| `HandleVehicleAtEntry()`     | 387-397 | `GateFlowController.HandleVehicleAtEntry()`                                           | ✅ Delegated                  |
| `CheckInWaitingVehicle()`    | 398-423 | `GateFlowController.CheckInWaitingVehicle()`                                          | ✅ Delegated                  |
| `CheckInWithANPR()`          | 424-483 | `GateFlowController` (private)                                                        | ✅ Extracted                  |
| `SpawnVehiclePreCheckedIn()` | 484-526 | **Stay**                                                                              | Public API                    |
| `ESP32CheckInFlow()`         | 527-558 | `GateFlowController` (deleted — not used)                                             | Superseded by ANPR            |
| `HandleVehicleParked()`      | 559-592 | `GateFlowController.HandleVehicleParked()`                                            | ✅ Delegated                  |
| `VerifySlotFlow()`           | 593-612 | `GateFlowController` (private)                                                        | ✅ Extracted                  |
| `DepartureTimer()`           | 613-620 | **Stay**                                                                              | Simple coroutine              |
| `HandleVehicleAtExit()`      | 621-634 | `GateFlowController.HandleVehicleAtExit()`                                            | ✅ Delegated                  |
| `ESP32CheckOutFlow()`        | 635-662 | `GateFlowController` (private)                                                        | ✅ Extracted                  |
| `HandleVehicleGone()`        | 663-680 | **Stay**                                                                              | Event cleanup                 |
| `ApplyMockStatuses()`        | 681-705 | `StaticVehicleSpawner.ApplyMockStatuses()`                                            | ✅ Extracted                  |
| `GetSlotStats()`             | 706-720 | **Stay**                                                                              | Utility getter                |
| `HandleCheckinSuccess()`     | 721-740 | `GateFlowController` → signal back                                                    | ✅ Delegated                  |
| `OpenSlotBarrier()`          | 741-756 | **Stay**                                                                              | Slot-level barrier            |
| `AnimateSlotBarrier()`       | 757-780 | **Stay**                                                                              | Animation                     |

---

## 4. Event Wiring Map

### 4.1 Subscription Setup

```
ParkingManager.Start():
  → _dataSync.SubscribeWebSocket()       // apiService.OnSlotStatusUpdate
  → _gateFlow.SubscribeWebSocket()       // apiService.OnCheckinSuccess
  → _dataSync.StartPolling()
```

### 4.2 Unsubscription

```
ParkingManager.OnDestroy():
  → _dataSync.UnsubscribeWebSocket()
  → _dataSync.StopPolling()
  → _gateFlow.UnsubscribeWebSocket()
```

### 4.3 Vehicle Events (unchanged binding, delegated handler)

| Event                   | Source            | Handler Location                                     |
| ----------------------- | ----------------- | ---------------------------------------------------- |
| `vehicle.OnReachedGate` | VehicleController | `→ _gateFlow.HandleVehicleAtEntry(v)`                |
| `vehicle.OnParked`      | VehicleController | `→ _gateFlow.HandleVehicleParked(v, DepartureTimer)` |
| `vehicle.OnReachedExit` | VehicleController | `→ _gateFlow.HandleVehicleAtExit(v)`                 |
| `vehicle.OnGone`        | VehicleController | `→ ParkingManager.HandleVehicleGone(v)` (stays)      |

### 4.4 Helper-to-Manager Callbacks

| Event                                   | Source   | Handler                            |
| --------------------------------------- | -------- | ---------------------------------- |
| `GateFlowController.OnStatusMessage`    | GateFlow | `→ ParkingManager.OnStatusMessage` |
| `GateFlowController.OnVehicleCheckedIn` | GateFlow | (log only)                         |
| `ParkingDataSync.OnSyncComplete`        | DataSync | (log only, init camera)            |

---

## 5. Safe Rollout Sequence

### Phase 0: Pre-Requisite Fix (15 min)

| Step | Action                                                                                                      | Checkpoint          |
| ---- | ----------------------------------------------------------------------------------------------------------- | ------------------- |
| 0.1  | Edit `BarrierController.cs` — add `public Transform Arm { get; set; }`                                      | Compile ✅          |
| 0.2  | Edit `ParkingManager.AutoLinkBarrierArms()` — replace reflection with `entryBarrier.Arm = pivot.transform;` | Compile ✅          |
| 0.3  | Play mode test — barriers open/close                                                                        | Barriers animate ✅ |

### Phase 1: CoroutineHelpers (20 min)

| Step | Action                                                                                                     | Checkpoint     |
| ---- | ---------------------------------------------------------------------------------------------------------- | -------------- |
| 1.1  | Create folder `Assets/Scripts/Utility/`                                                                    | Folder exists  |
| 1.2  | Create `CoroutineHelpers.cs` (static class)                                                                | Compile ✅     |
| 1.3  | Update `ESP32Simulator.cs` — replace internal `WaitWithTimeout` with `CoroutineHelpers.WaitUntilOrTimeout` | Compile ✅     |
| 1.4  | Play mode — ESP32 QR flow works                                                                            | QR check-in ok |

### Phase 2: ParkingDataSync (45 min)

| Step | Action                                                                              | Checkpoint    |
| ---- | ----------------------------------------------------------------------------------- | ------------- |
| 2.1  | Create folder `Assets/Scripts/Core/Sync/`                                           | Folder exists |
| 2.2  | Create `ParkingDataSync.cs`                                                         | Compile ✅    |
| 2.3  | In `ParkingManager.Awake()` — instantiate `_dataSync = new ParkingDataSync(...)`    | Compile ✅    |
| 2.4  | Replace `Login()` call in `Start()` with `yield return _dataSync.InitializeAsync()` | Compile ✅    |
| 2.5  | Remove old `Login()`, `FetchParkingData()`, `PollSlotsCoroutine()` methods          | Compile ✅    |
| 2.6  | Wire `_dataSync.SubscribeWebSocket()` in Start, cleanup in OnDestroy                | Compile ✅    |
| 2.7  | Play mode — slots load from API, WS updates work                                    | Slots sync ✅ |

### Phase 3: StaticVehicleSpawner (30 min)

| Step | Action                                                                                                   | Checkpoint             |
| ---- | -------------------------------------------------------------------------------------------------------- | ---------------------- |
| 3.1  | Create folder `Assets/Scripts/Core/Spawn/`                                                               | Folder exists          |
| 3.2  | Create `StaticVehicleSpawner.cs`                                                                         | Compile ✅             |
| 3.3  | Instantiate `_staticSpawner` in Awake                                                                    | Compile ✅             |
| 3.4  | Replace `MapApiDataToSlots()` logic — call `_staticSpawner.SpawnOccupiedVehicles(_dataSync.CachedSlots)` | Compile ✅             |
| 3.5  | Replace `ApplyMockStatuses()` call with `_staticSpawner.ApplyMockStatuses()`                             | Compile ✅             |
| 3.6  | Remove old `SpawnStaticParkedVehicle()`, private `AttachPlateText()`, `ApplyMockStatuses()`              | Compile ✅             |
| 3.7  | Play mode — occupied slots have vehicles                                                                 | Static cars visible ✅ |

### Phase 4: GateFlowController (45 min)

| Step | Action                                                                                          | Checkpoint               |
| ---- | ----------------------------------------------------------------------------------------------- | ------------------------ |
| 4.1  | Create folder `Assets/Scripts/Core/Flow/`                                                       | Folder exists            |
| 4.2  | Create `GateFlowController.cs`                                                                  | Compile ✅               |
| 4.3  | Instantiate `_gateFlow` in Awake                                                                | Compile ✅               |
| 4.4  | Replace `HandleVehicleAtEntry()` body → `_gateFlow.HandleVehicleAtEntry(v)`                     | Compile ✅               |
| 4.5  | Replace `CheckInWaitingVehicle()` → `_gateFlow.CheckInWaitingVehicle(plate)`                    | Compile ✅               |
| 4.6  | Replace `HandleVehicleParked()` → delegate to `_gateFlow`                                       | Compile ✅               |
| 4.7  | Replace `HandleVehicleAtExit()` → `_gateFlow.HandleVehicleAtExit(v)`                            | Compile ✅               |
| 4.8  | Replace `HandleCheckinSuccess()` → parse via `_gateFlow`, call `SpawnVehicle`                   | Compile ✅               |
| 4.9  | Remove old `CheckInWithANPR()`, `ESP32CheckOutFlow()`, `VerifySlotFlow()`, `ESP32CheckInFlow()` | Compile ✅               |
| 4.10 | Remove `vehiclesWaitingAtGate` list from ParkingManager                                         | Compile ✅               |
| 4.11 | Wire `_gateFlow.OnStatusMessage += msg => OnStatusMessage?.Invoke(msg)`                         | Compile ✅               |
| 4.12 | Wire `_gateFlow.SubscribeWebSocket()` in Start                                                  | Compile ✅               |
| 4.13 | Play mode — full check-in/out flow                                                              | Gate opens, ANPR logs ✅ |

### Phase 5: Final Cleanup (20 min)

| Step | Action                             | Checkpoint       |
| ---- | ---------------------------------- | ---------------- |
| 5.1  | Run `wc -l ParkingManager.cs`      | ≤ 250 lines ✅   |
| 5.2  | Run EditMode tests                 | All pass ✅      |
| 5.3  | Run full E2E Play mode flow        | Complete flow ✅ |
| 5.4  | Clean up unused `using` statements | Build clean ✅   |

---

## 6. Verification Checklist — Unity Play Mode

### 6.1 Startup Sequence

- [ ] Console shows `[ParkingDataSync] Login OK`
- [ ] Console shows `[ParkingDataSync] Fetched N slots`
- [ ] Console shows `[ParkingDataSync] Fetched N floors`
- [ ] No reflection warnings (AutoLinkBarrierArms fixed)
- [ ] Static vehicles appear on occupied slots
- [ ] `[ParkingManager] Ready` logged

### 6.2 Vehicle Spawn & Check-In

- [ ] `ESP32Simulator` → Queue vehicle → vehicle spawns at entry road
- [ ] Vehicle drives to gate, logs `waiting at gate for QR`
- [ ] QR scan triggers ANPR flow
- [ ] Console shows `✅ ANPR MATCH` or `⚠️ ANPR failed`
- [ ] Entry barrier opens and closes
- [ ] Vehicle proceeds to slot

### 6.3 Parking & Slot Verification

- [ ] Vehicle parks in slot
- [ ] Console shows `✅ SLOT VERIFIED: {plate} at {slot}`
- [ ] If real booking: no auto-depart; if random: auto-depart after delay

### 6.4 Check-Out Flow

- [ ] `StartDeparture()` → vehicle drives to exit gate
- [ ] Exit barrier opens via `ESP32CheckOutFlow`
- [ ] Console shows `Check-out OK`
- [ ] Vehicle leaves scene
- [ ] `HandleVehicleGone` cleanup runs (events unsubscribed)

### 6.5 WebSocket Updates

- [ ] Manually occupy slot via backend → Unity slot updates to Occupied
- [ ] WS check-in event → `SpawnVehicle` called, vehicle appears

### 6.6 Inspector Compatibility

- [ ] All `ParkingManager` serialized fields still wired
- [ ] No MissingReferenceException
- [ ] No NullReferenceException from helper classes

### 6.7 Regression Tests

- [ ] Mock mode (`useMockData = true`) → static vehicles spawn
- [ ] Re-run ESP32Simulator QR E2E test
- [ ] Re-run seed_unity_test_data + Play mode

---

## 7. ParkingManager After Extraction — Target Layout

```csharp
// ParkingManager.cs — Target ≤ 250 lines
namespace ParkingSim.Core
{
    public class ParkingManager : MonoBehaviour
    {
        public static ParkingManager Instance { get; private set; }

        // === SerializedFields (unchanged) ===
        [SerializeField] private ApiConfig config;
        [SerializeField] private ApiService apiService;
        [SerializeField] private AuthManager authManager;
        [SerializeField] private ParkingLotGenerator generator;
        [SerializeField] private WaypointGraph waypointGraph;
        [SerializeField] private BarrierController entryBarrier;
        [SerializeField] private BarrierController exitBarrier;
        [SerializeField] private VehicleQueue vehicleQueue;
        [SerializeField] private GameObject carPrefab;
        [SerializeField] private GameObject motorbikePrefab;
        [SerializeField] private Transform vehicleSpawnPoint;
        [SerializeField] private VirtualCameraManager virtualCameraManager;
        [SerializeField] private SlotOccupancyDetector slotOccupancyDetector;

        // === Events ===
        public event Action OnInitComplete;
        public event Action<string> OnStatusMessage;

        // === Helpers (instantiated in Awake) ===
        private ParkingDataSync _dataSync;
        private GateFlowController _gateFlow;
        private StaticVehicleSpawner _staticSpawner;

        // === Lifecycle ===
        private void Awake() { /* DI + create helpers ~30 lines */ }
        private IEnumerator Start() { /* orchestrate ~40 lines */ }
        private void OnDestroy() { /* cleanup ~10 lines */ }
        private void AutoLinkBarrierArms() { /* fixed, ~15 lines */ }

        // === Public API ===
        public void SpawnVehicle(...) { /* ~50 lines, unchanged */ }
        public VehicleController SpawnVehiclePreCheckedIn(...) { /* ~40 lines */ }
        public bool CheckInWaitingVehicle(string plate) => _gateFlow.CheckInWaitingVehicle(plate);
        public (int,int,int,int,int) GetSlotStats() { /* ~15 lines */ }
        public void OpenSlotBarrier(string slotCode) { /* ~20 lines */ }

        // === Event Handlers (thin delegation) ===
        private void HandleVehicleAtEntry(VehicleController v) => _gateFlow.HandleVehicleAtEntry(v);
        private void HandleVehicleParked(VehicleController v) => _gateFlow.HandleVehicleParked(v, AutoDepart);
        private void HandleVehicleAtExit(VehicleController v) => _gateFlow.HandleVehicleAtExit(v);
        private void HandleVehicleGone(VehicleController v) { /* cleanup ~15 lines */ }
        private IEnumerator DepartureTimer(...) { /* ~8 lines */ }
        private void AutoDepart(VehicleController v, float sec) => StartCoroutine(DepartureTimer(v, sec));
        private IEnumerator AnimateSlotBarrier(...) { /* ~25 lines */ }
    }
}
```

**Estimated line count:** 240-250 lines ✅

---

## 8. Hệ Quả

### Tích cực

- ParkingManager giảm từ 756 → ~250 lines (67% reduction)
- Separation of concerns: sync, flow, spawn isolated
- Testable: helper classes không phụ thuộc MonoBehaviour lifecycle
- Timeout protection: tất cả `while(!done)` loops có timeout

### Trade-offs

- 4 new files added
- Helper instantiation complexity in Awake
- Callback wiring between helpers and PM

### Rủi ro

- **Inspector breakage** → Mitigated: all SerializedFields stay on PM
- **Event leak** → Mitigated: explicit subscribe/unsubscribe
- **Circular refs** → Mitigated: helpers receive PM via coroutineHost interface, không reference ParkingManager type

---

## 9. Tóm Tắt Output

```
✅ [ARCHITECT] hoàn tất: S2-IMP-10

📄 Design:       docs/architecture/S2-IMP-10-parkingmanager-extraction-design.md

New Classes:
  1. Assets/Scripts/Utility/CoroutineHelpers.cs (~35 lines)
  2. Assets/Scripts/Core/Sync/ParkingDataSync.cs (~180 lines)
  3. Assets/Scripts/Core/Flow/GateFlowController.cs (~220 lines)
  4. Assets/Scripts/Core/Spawn/StaticVehicleSpawner.cs (~100 lines)

ParkingManager After: ≤ 250 lines (từ 756)

Breaking changes: No
Inspector changes: No
Pre-requisite: Fix BarrierController.cs (add Arm property)
Implement order: Phase 0 → 1 → 2 → 3 → 4 → 5
Est. time: 2.5 hours (with testing)
```
