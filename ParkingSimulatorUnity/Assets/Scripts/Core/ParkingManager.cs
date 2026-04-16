using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;
using ParkingSim.Navigation;
using ParkingSim.Camera;
using TMPro;

namespace ParkingSim.Core
{
    public class ParkingManager : MonoBehaviour
    {
        public static ParkingManager Instance { get; private set; }

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

        private readonly List<VehicleController> vehiclesWaitingAtGate = new List<VehicleController>();
        [SerializeField] private SlotOccupancyDetector slotOccupancyDetector;

        private List<SlotData> cachedSlots;
        private List<FloorData> cachedFloors;

        public event Action OnInitComplete;
        public event Action<string> OnStatusMessage;

        private void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            if (transform.parent == null)
                DontDestroyOnLoad(gameObject);

            if (config == null)
                config = Resources.Load<ApiConfig>("ApiConfig");
            if (apiService == null)
                apiService = ApiService.Instance ?? FindObjectOfType<ApiService>();
            if (authManager == null)
                authManager = AuthManager.Instance ?? FindObjectOfType<AuthManager>();
            if (generator == null)
                generator = FindObjectOfType<ParkingLotGenerator>();
            if (waypointGraph == null)
                waypointGraph = FindObjectOfType<WaypointGraph>();
            if (vehicleQueue == null)
                vehicleQueue = FindObjectOfType<VehicleQueue>();
            if (virtualCameraManager == null)
                virtualCameraManager = VirtualCameraManager.Instance ?? FindObjectOfType<VirtualCameraManager>();
            if (slotOccupancyDetector == null)
                slotOccupancyDetector = FindObjectOfType<SlotOccupancyDetector>();
        }

        private IEnumerator Start()
        {
            Debug.Log("[ParkingManager] Initializing...");
            generator.Generate();

            // Auto-link barrier arms from generated gates
            AutoLinkBarrierArms();

            if (!config.useMockData)
            {
                yield return StartCoroutine(Login());
                yield return StartCoroutine(FetchParkingData());

                // Sync bookings first so static vehicles can get plate numbers
                bool bookingsDone = false;
                ApiResponse<PaginatedResponse<BookingData>> bookingsResult = null;
                StartCoroutine(apiService.GetBookings(r => { bookingsResult = r; bookingsDone = true; }));
                yield return new WaitUntil(() => bookingsDone);
                if (bookingsResult?.IsSuccess == true && bookingsResult.Data?.Results != null)
                {
                    int synced = SharedBookingState.Instance?.SyncFromApi(bookingsResult.Data.Results) ?? 0;
                    Debug.Log($"[ParkingManager] Pre-synced {synced} bookings for plate matching");
                }

                MapApiDataToSlots();
                apiService.ConnectWebSocket();
                apiService.OnSlotStatusUpdate += HandleSlotStatusUpdate;
                apiService.OnCheckinSuccess += HandleCheckinSuccess;
                StartCoroutine(PollSlotsCoroutine());
            }
            else
            {
                ApplyMockStatuses();
            }

            // Initialize virtual camera system
            if (virtualCameraManager != null)
            {
                virtualCameraManager.InitializeCameras();
                Debug.Log("[ParkingManager] Virtual cameras initialized");
            }
            if (slotOccupancyDetector != null)
            {
                slotOccupancyDetector.StartDetection();
                Debug.Log("[ParkingManager] Slot detection started");
            }

            Debug.Log("[ParkingManager] Ready");
            OnInitComplete?.Invoke();
        }

        private void AutoLinkBarrierArms()
        {
            var entryPivot = GameObject.Find("BarrierArmPivot_GATE-IN-01");
            var exitPivot = GameObject.Find("BarrierArmPivot_GATE-OUT-01");

            var field = typeof(BarrierController).GetField("barrierArm",
                System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            if (field == null) return;

            if (entryBarrier != null && entryPivot != null)
            {
                field.SetValue(entryBarrier, entryPivot.transform);
                Debug.Log("[ParkingManager] Linked entry barrier arm");
            }

            if (exitBarrier != null && exitPivot != null)
            {
                field.SetValue(exitBarrier, exitPivot.transform);
                Debug.Log("[ParkingManager] Linked exit barrier arm");
            }
        }

        private void OnDestroy()
        {
            if (apiService != null)
            {
                apiService.OnSlotStatusUpdate -= HandleSlotStatusUpdate;
                apiService.OnCheckinSuccess -= HandleCheckinSuccess;
            }
        }

        private IEnumerator Login()
        {
            bool done = false, success = false;
            Action successHandler = () => { success = true; done = true; };
            Action<string> failHandler = _ => { done = true; };
            authManager.OnLoginSuccess += successHandler;
            authManager.OnLoginFailed += failHandler;
            yield return StartCoroutine(authManager.Login(config.testEmail, config.testPassword));
            while (!done) yield return null;
            authManager.OnLoginSuccess -= successHandler;
            authManager.OnLoginFailed -= failHandler;
            Debug.Log(success ? "[ParkingManager] Login OK" : "[ParkingManager] Login FAILED");
        }

        private IEnumerator FetchParkingData()
        {
            bool slotsDone = false;
            ApiResponse<PaginatedResponse<SlotData>> slotsResult = null;
            StartCoroutine(apiService.GetSlots(config.targetParkingLotId, r => { slotsResult = r; slotsDone = true; }));
            while (!slotsDone) yield return null;

            cachedSlots = slotsResult?.IsSuccess == true ? slotsResult.Data?.Results ?? new List<SlotData>() : new List<SlotData>();
            Debug.Log(slotsResult?.IsSuccess == true
                ? $"[ParkingManager] Fetched {cachedSlots.Count} slots"
                : "[ParkingManager] Failed to fetch slots");

            bool floorsDone = false;
            ApiResponse<PaginatedResponse<FloorData>> floorsResult = null;
            StartCoroutine(apiService.GetFloors(config.targetParkingLotId, r => { floorsResult = r; floorsDone = true; }));
            while (!floorsDone) yield return null;

            cachedFloors = floorsResult?.IsSuccess == true ? floorsResult.Data?.Results ?? new List<FloorData>() : new List<FloorData>();
            Debug.Log(floorsResult?.IsSuccess == true
                ? $"[ParkingManager] Fetched {cachedFloors.Count} floors"
                : "[ParkingManager] Failed to fetch floors");
        }

        private void MapApiDataToSlots()
        {
            if (cachedSlots == null) return;

            int matched = 0;
            foreach (var apiSlot in cachedSlots)
            {
                if (generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                {
                    slot.slotId = apiSlot.Id;
                    slot.UpdateState(ParkingSlot.ParseStatus(apiSlot.Status));
                    matched++;

                    if (string.Equals(apiSlot.Status, "occupied", StringComparison.OrdinalIgnoreCase))
                    {
                        string plate = SharedBookingState.Instance?.GetBookingBySlotCode(apiSlot.Code)?.LicensePlate;
                        SpawnStaticParkedVehicle(slot, plate);
                    }
                }
                else
                {
                    Debug.LogWarning($"[ParkingManager] Slot {apiSlot.Code} from API not in generated lot");
                }
            }
            Debug.Log($"[ParkingManager] Mapped {matched}/{cachedSlots.Count} slots");
        }

        /// <summary>Spawn a static parked vehicle visually on a slot that is already occupied in the DB.</summary>
        private void SpawnStaticParkedVehicle(ParkingSlot slot, string plateNumber = null)
        {
            var prefab = slot.slotType == ParkingSlot.SlotType.Motorbike ? motorbikePrefab : carPrefab;
            if (prefab == null) return;

            // Place at slot centre at floor level (slot.y is 0.12 above the floor slab top ~0.10)
            Vector3 slotPos = slot.transform.position;
            float floorY = slotPos.y - 0.12f + 0.1f; // floor surface
            Vector3 slotFwd = slot.transform.forward;
            Quaternion parkRot = slotFwd.sqrMagnitude > 0.01f ? Quaternion.LookRotation(-slotFwd) : Quaternion.identity;
            var go = Instantiate(prefab, new Vector3(slotPos.x, floorY, slotPos.z), parkRot);
            go.name = $"StaticVehicle_{slot.slotCode}";

            // Ensure URP materials are fixed at runtime
            if (go.GetComponent<VehicleVisualEnhancer>() == null)
                go.AddComponent<VehicleVisualEnhancer>();

            // Set vehicle controller with plate for AI recognition
            var vc = go.GetComponent<VehicleController>();
            if (vc != null)
            {
                vc.state = VehicleController.VehicleState.Parked;
                vc.plateNumber = plateNumber ?? $"MOCK-{slot.slotCode}";
                vc.enabled = false;
            }

            // Kinematic so physics doesn't drop / move it
            var rb = go.GetComponent<Rigidbody>();
            if (rb != null) rb.isKinematic = true;

            // Attach visible license plate (rear only)
            string plate = vc?.plateNumber ?? "UNKNOWN";
            AttachPlateText(go, plate);

            Debug.Log($"[ParkingManager] Static vehicle placed at {slot.slotCode} plate={plate}");
        }

        private void AttachPlateText(GameObject vehicle, string plateText)
        {
            LicensePlateCreator.CreateRearPlate(vehicle.transform, plateText);
        }

        private void HandleSlotStatusUpdate(SlotStatusUpdate update)
        {
            ParkingSlot found = null;
            foreach (var kvp in generator.slotRegistry)
            {
                if (kvp.Value.slotId == update.SlotId)
                {
                    found = kvp.Value;
                    break;
                }
            }

            if (found != null)
            {
                found.UpdateState(ParkingSlot.ParseStatus(update.Status));
                Debug.Log($"[ParkingManager] WS update: slot {found.slotCode} → {update.Status}");
            }
        }

        private IEnumerator PollSlotsCoroutine()
        {
            // S2-IMP-11: WebSocket is the primary source of slot updates.
            // Polling runs only as a FALLBACK when WS is disconnected — avoids
            // race where stale HTTP snapshot overwrites a fresh WS push.
            while (true)
            {
                yield return new WaitForSeconds(config.deltaPollInterval);

                // Skip poll if WebSocket is healthy — events flow through
                // apiService.OnSlotStatusUpdate → HandleSlotStatusUpdate.
                if (apiService != null && apiService.IsWsConnected)
                {
                    continue;
                }

                bool done = false;
                ApiResponse<PaginatedResponse<SlotData>> result = null;
                StartCoroutine(apiService.GetSlots(config.targetParkingLotId, r =>
                {
                    result = r;
                    done = true;
                }));

                // Fail-safe timeout — prevent infinite hang if HTTP stalls.
                float timeoutElapsed = 0f;
                const float pollTimeoutSeconds = 10f;
                while (!done && timeoutElapsed < pollTimeoutSeconds)
                {
                    timeoutElapsed += Time.deltaTime;
                    yield return null;
                }
                if (!done)
                {
                    Debug.LogWarning("[ParkingManager] Poll HTTP timeout — skipping tick");
                    continue;
                }

                if (result != null && result.IsSuccess && result.Data?.Results != null)
                {
                    foreach (var apiSlot in result.Data.Results)
                    {
                        if (generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                            slot.UpdateState(ParkingSlot.ParseStatus(apiSlot.Status));
                    }

                    var stats = GetSlotStats();
                    Debug.Log($"[ParkingManager] Poll (fallback): {stats.available}/{stats.total} slots available");
                }
            }
        }

        public void SpawnVehicle(string plate, string bookingId, string qrData,
            string targetSlotCode, string vType = "Car")
        {
            var prefab = vType == "Motorbike" ? motorbikePrefab : carPrefab;
            // Always compute spawn from generator geometry — entry road is on +X side.
            // vehicleSpawnPoint scene reference may be stale from old bootstrap, so ignore it.
            var spawnPos = new Vector3(generator.platformWidth / 2f + 12f, 0.1f, 0f);
            var spawnRot = Quaternion.Euler(0f, -90f, 0f); // face -X toward gate
            var go = Instantiate(prefab, spawnPos, spawnRot);

            // Ensure URP materials are fixed at runtime
            if (go.GetComponent<VehicleVisualEnhancer>() == null)
                go.AddComponent<VehicleVisualEnhancer>();

            var vehicle = go.GetComponent<VehicleController>();
            if (vehicle == null) vehicle = go.AddComponent<VehicleController>();

            var slot = generator.GetSlotByCode(targetSlotCode);
            vehicle.Initialize(waypointGraph, slot, plate, qrData, vType);
            vehicle.bookingId = bookingId;

            vehicle.OnReachedGate += HandleVehicleAtEntry;
            vehicle.OnParked += HandleVehicleParked;
            vehicle.OnReachedExit += HandleVehicleAtExit;
            vehicle.OnGone += HandleVehicleGone;

            vehicle.StartEntry();

            // Attach visible license plate (rear only)
            AttachPlateText(go, plate);

            Debug.Log($"[ParkingManager] Spawned {plate} outside gate, heading to GATE-IN-01");
        }

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

        /// <summary>Called by ESP32Simulator after a successful QR-based check-in.
        /// Finds the vehicle already stopped at the gate and lets it through.</summary>
        public bool CheckInWaitingVehicle(string plate)
        {
            var vehicle = vehiclesWaitingAtGate.Find(v =>
                string.Equals(v.plateNumber, plate, StringComparison.OrdinalIgnoreCase));

            if (vehicle == null)
            {
                Debug.LogWarning($"[ParkingManager] CheckIn: no vehicle waiting at gate with plate {plate}");
                return false;
            }

            vehiclesWaitingAtGate.Remove(vehicle);
            StartCoroutine(CheckInWithANPR(vehicle));
            return true;
        }

        private IEnumerator CheckInWithANPR(VehicleController vehicle)
        {
            Debug.Log($"[ParkingManager] \ud83d\udd0d Starting ANPR verification for {vehicle.plateNumber}...");

            // Step 1: Use ANPR camera to capture plate
            string detectedPlate = null;
            float confidence = 0f;

            var streamer = virtualCameraManager?.GetStreamer("virtual-anpr-entry")
                        ?? virtualCameraManager?.GetStreamer("virtual-gate-in");

            if (streamer != null)
            {
                // Wait 2 frames for camera to settle
                yield return null;
                yield return null;

                byte[] snapshot = streamer.SnapshotJpeg();
                if (snapshot != null && snapshot.Length > 0)
                {
                    bool anprDone = false;
                    float anprTimer = 0f;
                    ApiResponse<PlateScanResult> scanResult = null;
                    StartCoroutine(apiService.AIRecognizePlate(snapshot,
                        r => { scanResult = r; anprDone = true; }));

                    // 5s timeout — don’t block gate forever if AI service is slow
                    while (!anprDone && anprTimer < 5f)
                    {
                        anprTimer += Time.deltaTime;
                        yield return null;
                    }

                    if (scanResult?.IsSuccess == true && scanResult.Data != null)
                    {
                        detectedPlate = scanResult.Data.PlateText;
                        confidence = scanResult.Data.Confidence;
                    }
                }
            }

            // Step 2: Compare with booking plate
            bool plateMatch = false;
            if (!string.IsNullOrEmpty(detectedPlate))
            {
                plateMatch = string.Equals(detectedPlate, vehicle.plateNumber,
                    StringComparison.OrdinalIgnoreCase);

                if (plateMatch)
                {
                    Debug.Log($"[ParkingManager] ✅ ANPR MATCH: detected={detectedPlate}, " +
                              $"expected={vehicle.plateNumber}, confidence={confidence:P0}");
                }
                else
                {
                    Debug.LogWarning($"[ParkingManager] ⚠️ ANPR MISMATCH: detected={detectedPlate}, " +
                                   $"expected={vehicle.plateNumber}, confidence={confidence:P0}");
                }
            }
            else
            {
                Debug.LogWarning($"[ParkingManager] ⚠️ ANPR failed — no plate detected. " +
                               $"Proceeding with check-in for {vehicle.plateNumber}");
            }

            // Step 3: Open barrier.
            //   plateMatch=true  → ANPR verified ✔
            //   detectedPlate empty → model/camera issue, open with warning (simulation fallback)
            //   plateMatch=false but detectedPlate set → real mismatch → BLOCK
            bool shouldOpen = plateMatch || string.IsNullOrEmpty(detectedPlate);
            if (shouldOpen)
            {
                StartCoroutine(entryBarrier.OpenThenClose(3f));
                vehicle.ProceedFromGate();
                Debug.Log($"[ParkingManager] \u2705 Gate opened for {vehicle.plateNumber}" +
                          (plateMatch ? " (ANPR verified \u2705)" : " (ANPR unverified \u26a0\ufe0f)"));
            }
            else
            {
                Debug.LogWarning($"[ParkingManager] \ud83d\udeab Gate BLOCKED for {vehicle.plateNumber} " +
                               $"— plate mismatch: detected={detectedPlate}, expected={vehicle.plateNumber}");
            }
        }

        public VehicleController SpawnVehiclePreCheckedIn(string plate, string bookingId, string qrData,
            string targetSlotCode, string vType = "Car")
        {
            var prefab = vType == "Motorbike" ? motorbikePrefab : carPrefab;
            var spawnPos = new Vector3(generator.platformWidth / 2f + 12f, 0.1f, 0f);
            var spawnRot = Quaternion.Euler(0f, -90f, 0f);
            var go = Instantiate(prefab, spawnPos, spawnRot);

            // Ensure URP materials are fixed at runtime
            if (go.GetComponent<VehicleVisualEnhancer>() == null)
                go.AddComponent<VehicleVisualEnhancer>();

            var vehicle = go.GetComponent<VehicleController>();
            if (vehicle == null) vehicle = go.AddComponent<VehicleController>();

            var slot = generator.GetSlotByCode(targetSlotCode);
            vehicle.Initialize(waypointGraph, slot, plate, qrData, vType);
            vehicle.bookingId = bookingId;
            vehicle.alreadyCheckedIn = true;

            vehicle.OnReachedGate += HandleVehicleAtEntry;
            vehicle.OnParked += HandleVehicleParked;
            vehicle.OnReachedExit += HandleVehicleAtExit;
            vehicle.OnGone += HandleVehicleGone;

            vehicle.StartEntry();

            // Attach visible license plate (rear only)
            AttachPlateText(go, plate);

            Debug.Log($"[ParkingManager] Spawned pre-checked-in {plate} heading to {targetSlotCode}");
            return vehicle;
        }

        private IEnumerator ESP32CheckInFlow(VehicleController vehicle)
        {
            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32CheckInRequest
            {
                GateId = MockIds.GATE_IN,
                QrData = vehicle.qrData
            };
            StartCoroutine(apiService.ESP32CheckIn(request, r =>
            {
                result = r;
                done = true;
            }));
            while (!done) yield return null;

            if (result != null && result.IsSuccess && result.Data != null && result.Data.Success)
            {
                Debug.Log($"[ParkingManager] Check-in OK for {vehicle.plateNumber}");
                StartCoroutine(entryBarrier.OpenThenClose(3f));
                yield return new WaitForSeconds(1f);
                vehicle.ProceedFromGate();
            }
            else
            {
                string error = result?.ErrorMessage ?? result?.Data?.Message ?? "Unknown error";
                Debug.LogWarning($"[ParkingManager] Check-in FAILED for {vehicle.plateNumber}: {error}");
                OnStatusMessage?.Invoke("Check-in failed: " + error);
            }
        }

        private void HandleVehicleParked(VehicleController vehicle)
        {
            Debug.Log($"[ParkingManager] {vehicle.plateNumber} parked at slot");

            // Only auto-depart vehicles without real bookings (random/test spawns)
            var booking = SharedBookingState.Instance?.GetBookingById(vehicle.bookingId);
            if (booking == null)
            {
                float duration = UnityEngine.Random.Range(10f, 30f);
                StartCoroutine(DepartureTimer(vehicle, duration));
                return;
            }

            // Slot-level check-in: verify the vehicle parked at the correct slot
            string actualSlot = vehicle.TargetSlot?.slotCode ?? "unknown";
            string bookedSlot = booking.SlotCode ?? "unknown";
            bool slotMatch = string.Equals(actualSlot, bookedSlot, StringComparison.OrdinalIgnoreCase);

            if (slotMatch)
            {
                Debug.Log($"[ParkingManager] ✅ SLOT VERIFIED: {vehicle.plateNumber} parked at {actualSlot} " +
                          $"(matches booking {vehicle.bookingId.Substring(0, 8)})");
            }
            else
            {
                Debug.LogWarning($"[ParkingManager] ⚠️ SLOT MISMATCH: {vehicle.plateNumber} parked at {actualSlot} " +
                               $"but booking says {bookedSlot}");
            }

            // Call verify-slot API
            if (!config.useMockData)
            {
                StartCoroutine(VerifySlotFlow(vehicle, actualSlot, booking));
            }

            Debug.Log($"[ParkingManager] {vehicle.plateNumber} has real booking — waiting for manual checkout");
        }

        private IEnumerator VerifySlotFlow(VehicleController vehicle, string slotCode, ActiveBooking booking)
        {
            string qrData = vehicle.qrData ?? booking.QrCodeData;
            if (string.IsNullOrEmpty(qrData))
            {
                Debug.LogWarning($"[ParkingManager] Cannot verify slot — no QR data for {vehicle.plateNumber}");
                yield break;
            }

            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32VerifySlotRequest
            {
                SlotCode = slotCode,
                ZoneId = booking.SlotCode?.StartsWith("V") == true ? MockIds.ZONE_CAR_PAINTED_F1 : MockIds.ZONE_CAR_PAINTED_F1,
                GateId = MockIds.GATE_IN,
                QrData = qrData
            };
            StartCoroutine(apiService.ESP32VerifySlot(request, r => { result = r; done = true; }));
            yield return new WaitUntil(() => done);

            if (result?.IsSuccess == true && result.Data?.Success == true)
            {
                Debug.Log($"[ParkingManager] ✅ Backend verified slot {slotCode} for {vehicle.plateNumber}");
            }
            else
            {
                string msg = result?.Data?.Message ?? result?.ErrorMessage ?? "Unknown error";
                Debug.LogWarning($"[ParkingManager] ⚠️ Backend slot verification failed: {msg}");
            }
        }

        private IEnumerator DepartureTimer(VehicleController vehicle, float duration)
        {
            yield return new WaitForSeconds(duration);
            if (vehicle == null) yield break;
            Debug.Log($"[ParkingManager] {vehicle.plateNumber} departing after {duration:F0}s");
            vehicle.StartDeparture();
        }

        private void HandleVehicleAtExit(VehicleController vehicle)
        {
            if (config.useMockData)
            {
                StartCoroutine(exitBarrier.OpenThenClose(3f));
                vehicle.ProceedFromExit();
            }
            else
            {
                StartCoroutine(ESP32CheckOutFlow(vehicle));
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
            StartCoroutine(apiService.ESP32CheckOut(request, r =>
            {
                result = r;
                done = true;
            }));
            while (!done) yield return null;

            if (result != null && result.IsSuccess && result.Data != null && result.Data.Success)
            {
                Debug.Log($"[ParkingManager] Check-out OK for {vehicle.plateNumber}");
                StartCoroutine(exitBarrier.OpenThenClose(3f));
                yield return new WaitForSeconds(1f);
                vehicle.ProceedFromExit();
            }
            else
            {
                string error = result?.ErrorMessage ?? result?.Data?.Message ?? "Unknown error";
                Debug.LogWarning($"[ParkingManager] Check-out FAILED for {vehicle.plateNumber}: {error}");
                OnStatusMessage?.Invoke("Check-out failed: " + error);
            }
        }

        private void HandleVehicleGone(VehicleController vehicle)
        {
            Debug.Log($"[ParkingManager] {vehicle.plateNumber} left the lot");
            if (vehicleQueue != null) vehicleQueue.NotifyDeparture();
            vehicle.OnReachedGate -= HandleVehicleAtEntry;
            vehicle.OnParked -= HandleVehicleParked;
            vehicle.OnReachedExit -= HandleVehicleAtExit;
            vehicle.OnGone -= HandleVehicleGone;
        }

        private void ApplyMockStatuses()
        {
            // Use mock data that mirrors DB structure (V1-xx, A-xx, etc.)
            var mockSlots = MockDataProvider.GenerateMockSlots();
            int matched = 0;
            foreach (var apiSlot in mockSlots)
            {
                if (generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                {
                    var status = ParkingSlot.ParseStatus(apiSlot.Status);
                    slot.slotId = apiSlot.Id;
                    slot.UpdateState(status);
                    matched++;

                    if (status == ParkingSlot.SlotStatus.Occupied)
                        SpawnStaticParkedVehicle(slot, $"SIM-{apiSlot.Code}");
                }
            }
            Debug.Log($"[ParkingManager] Applied mock statuses: {matched}/{mockSlots.Count} slots matched, spawned vehicles for occupied");
        }

        public (int total, int available, int occupied, int reserved, int maintenance) GetSlotStats()
        {
            int total = 0, available = 0, occupied = 0, reserved = 0, maintenance = 0;
            foreach (var slot in generator.slotRegistry.Values)
            {
                total++;
                switch (slot.status)
                {
                    case ParkingSlot.SlotStatus.Available:   available++;   break;
                    case ParkingSlot.SlotStatus.Occupied:    occupied++;    break;
                    case ParkingSlot.SlotStatus.Reserved:    reserved++;    break;
                    case ParkingSlot.SlotStatus.Maintenance: maintenance++; break;
                }
            }
            return (total, available, occupied, reserved, maintenance);
        }

        private void HandleCheckinSuccess(CheckinSuccessData data)
        {
            if (data == null) return;
            string plate = data.Plate ?? "UNKNOWN";
            string bookingId = data.BookingId ?? System.Guid.NewGuid().ToString();
            string qrData = data.QrData ?? $"{{\"booking_id\":\"{bookingId}\"}}";
            string slotCode = data.SlotCode ?? "A-01";
            string vehicleType = data.VehicleType ?? "Car";

            Debug.Log($"[ParkingManager] 🚗 WebSocket check-in: plate={plate} slot={slotCode} booking={bookingId}");
            SpawnVehicle(plate, bookingId, qrData, slotCode, vehicleType);
        }

        /// <summary>Open the mini-barrier arm at the given slot for 3 seconds then close it.</summary>
        public void OpenSlotBarrier(string slotCode)
        {
            if (string.IsNullOrEmpty(slotCode)) return;
            if (generator == null || !generator.slotRegistry.TryGetValue(slotCode, out var slot)) return;

            var arm = slot.transform.Find("SlotBarrierArm");
            if (arm == null)
            {
                Debug.LogWarning($"[ParkingManager] SlotBarrierArm not found on slot {slotCode}");
                return;
            }

            StartCoroutine(AnimateSlotBarrier(arm, slotCode));

            // Release vehicle waiting at this slot entrance → drive into slot
            foreach (var v in FindObjectsOfType<VehicleController>())
            {
                if (v == null || !v.IsAtSlotEntrance) continue;
                if (string.Equals(v.TargetSlot?.slotCode, slotCode, StringComparison.OrdinalIgnoreCase))
                {
                    v.ProceedIntoSlot();
                    break;
                }
            }
        }

        private IEnumerator AnimateSlotBarrier(Transform arm, string slotCode)
        {
            Debug.Log($"[ParkingManager] 🟢 Slot barrier OPEN → {slotCode}");
            float elapsed = 0f;
            Quaternion closed = arm.localRotation;
            Quaternion open = closed * Quaternion.Euler(0f, -90f, 0f);

            // Open
            while (elapsed < 0.5f)
            {
                elapsed += Time.deltaTime;
                arm.localRotation = Quaternion.Slerp(closed, open, elapsed / 0.5f);
                yield return null;
            }
            arm.localRotation = open;

            yield return new WaitForSeconds(4f);

            // Close
            elapsed = 0f;
            while (elapsed < 0.5f)
            {
                elapsed += Time.deltaTime;
                arm.localRotation = Quaternion.Slerp(open, closed, elapsed / 0.5f);
                yield return null;
            }
            arm.localRotation = closed;
            Debug.Log($"[ParkingManager] 🔴 Slot barrier CLOSE → {slotCode}");
        }
    }
}
