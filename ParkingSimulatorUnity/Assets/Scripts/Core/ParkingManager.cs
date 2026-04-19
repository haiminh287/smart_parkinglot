using System;
using System.Collections;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;
using ParkingSim.Navigation;
using ParkingSim.Camera;
using ParkingSim.Core.Sync;
using ParkingSim.Core.Flow;
using ParkingSim.Core.Spawn;

namespace ParkingSim.Core
{
    /// <summary>
    /// Thin coordinator — orchestrates helpers and exposes public API.
    /// Refactored from 756 lines → ~250 lines.
    /// </summary>
    public class ParkingManager : MonoBehaviour
    {
        public static ParkingManager Instance { get; private set; }

        // === SerializedFields (unchanged for Inspector compatibility) ===
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

        // === Helpers (created in Awake) ===
        private ParkingDataSync _dataSync;
        private GateFlowController _gateFlow;
        private StaticVehicleSpawner _staticSpawner;

        private void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            if (transform.parent == null)
                DontDestroyOnLoad(gameObject);

            // DI fallbacks
            if (config == null) config = Resources.Load<ApiConfig>("ApiConfig");
            if (apiService == null) apiService = ApiService.Instance ?? FindObjectOfType<ApiService>();
            if (authManager == null) authManager = AuthManager.Instance ?? FindObjectOfType<AuthManager>();
            if (generator == null) generator = FindObjectOfType<ParkingLotGenerator>();
            if (waypointGraph == null) waypointGraph = FindObjectOfType<WaypointGraph>();
            if (vehicleQueue == null) vehicleQueue = FindObjectOfType<VehicleQueue>();
            if (virtualCameraManager == null) virtualCameraManager = VirtualCameraManager.Instance ?? FindObjectOfType<VirtualCameraManager>();
            if (slotOccupancyDetector == null) slotOccupancyDetector = FindObjectOfType<SlotOccupancyDetector>();

            // Create helpers
            _dataSync = new ParkingDataSync(config, apiService, authManager, generator, this);
            _gateFlow = new GateFlowController(config, apiService, virtualCameraManager, entryBarrier, exitBarrier, this);
            _staticSpawner = new StaticVehicleSpawner(generator, carPrefab, motorbikePrefab);

            // Wire helper events
            _gateFlow.OnStatusMessage += msg => OnStatusMessage?.Invoke(msg);
        }

        private IEnumerator Start()
        {
            Debug.Log("[ParkingManager] Initializing...");
            if (generator == null)
            {
                Debug.LogError("[ParkingManager] ParkingLotGenerator not found! Cannot initialize.");
                yield break;
            }
            generator.Generate();
            AutoLinkBarrierArms();

            if (!config.useMockData)
            {
                yield return StartCoroutine(_dataSync.InitializeAsync());
                _staticSpawner.SpawnOccupiedVehicles(_dataSync.CachedSlots);
                _dataSync.SubscribeWebSocket();
                _gateFlow.SubscribeWebSocket();
                apiService.OnCheckinSuccess += HandleCheckinSuccess;
                apiService.OnDepartVehicle += HandleDepartVehicle;
                _dataSync.StartPolling();
            }
            else
            {
                _staticSpawner.ApplyMockStatuses();
            }

            // Initialize camera/detection
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
            // Wire barrier arms via public property (no reflection)
            var entryPivot = GameObject.Find("BarrierArmPivot_GATE-IN-01");
            var exitPivot = GameObject.Find("BarrierArmPivot_GATE-OUT-01");

            if (entryBarrier != null && entryPivot != null)
            {
                entryBarrier.Arm = entryPivot.transform;
                Debug.Log("[ParkingManager] Linked entry barrier arm");
            }
            if (exitBarrier != null && exitPivot != null)
            {
                exitBarrier.Arm = exitPivot.transform;
                Debug.Log("[ParkingManager] Linked exit barrier arm");
            }
        }

        private void OnDestroy()
        {
            _dataSync?.UnsubscribeWebSocket();
            _dataSync?.StopPolling();
            _gateFlow?.UnsubscribeWebSocket();
            if (apiService != null)
            {
                apiService.OnCheckinSuccess -= HandleCheckinSuccess;
                apiService.OnDepartVehicle -= HandleDepartVehicle;
            }
        }

        // === Public API ===

        public void SpawnVehicle(string plate, string bookingId, string qrData,
            string targetSlotCode, string vType = "Car")
        {
            var prefab = vType == "Motorbike" ? motorbikePrefab : carPrefab;
            var spawnPos = new Vector3(generator.platformWidth / 2f + 12f, 0.1f, 0f);
            var spawnRot = Quaternion.Euler(0f, -90f, 0f);
            var go = Instantiate(prefab, spawnPos, spawnRot);

            if (go.GetComponent<VehicleVisualEnhancer>() == null)
                go.AddComponent<VehicleVisualEnhancer>();

            var vehicle = go.GetComponent<VehicleController>();
            if (vehicle == null) vehicle = go.AddComponent<VehicleController>();

            var slot = generator.GetSlotByCode(targetSlotCode);
            if (slot == null)
            {
                Debug.LogWarning($"[ParkingManager] Slot '{targetSlotCode}' not found, skipping spawn for {plate}");
                Destroy(go);
                return;
            }
            vehicle.Initialize(waypointGraph, slot, plate, qrData, vType);
            vehicle.bookingId = bookingId;

            vehicle.OnReachedGate += HandleVehicleAtEntry;
            vehicle.OnParked += HandleVehicleParked;
            vehicle.OnReachedExit += HandleVehicleAtExit;
            vehicle.OnGone += HandleVehicleGone;

            vehicle.StartEntry();
            LicensePlateCreator.CreateRearPlate(go.transform, plate);
            Debug.Log($"[ParkingManager] Spawned {plate} outside gate, heading to GATE-IN-01");
        }

        public VehicleController SpawnVehiclePreCheckedIn(string plate, string bookingId, string qrData,
            string targetSlotCode, string vType = "Car")
        {
            var prefab = vType == "Motorbike" ? motorbikePrefab : carPrefab;
            var spawnPos = new Vector3(generator.platformWidth / 2f + 12f, 0.1f, 0f);
            var spawnRot = Quaternion.Euler(0f, -90f, 0f);
            var go = Instantiate(prefab, spawnPos, spawnRot);

            if (go.GetComponent<VehicleVisualEnhancer>() == null)
                go.AddComponent<VehicleVisualEnhancer>();

            var vehicle = go.GetComponent<VehicleController>();
            if (vehicle == null) vehicle = go.AddComponent<VehicleController>();

            var slot = generator.GetSlotByCode(targetSlotCode);
            if (slot == null)
            {
                Debug.LogWarning($"[ParkingManager] Slot '{targetSlotCode}' not found, skipping spawn for {plate}");
                Destroy(go);
                return null;
            }
            vehicle.Initialize(waypointGraph, slot, plate, qrData, vType);
            vehicle.bookingId = bookingId;
            vehicle.alreadyCheckedIn = true;

            vehicle.OnReachedGate += HandleVehicleAtEntry;
            vehicle.OnParked += HandleVehicleParked;
            vehicle.OnReachedExit += HandleVehicleAtExit;
            vehicle.OnGone += HandleVehicleGone;

            vehicle.StartEntry();
            LicensePlateCreator.CreateRearPlate(go.transform, plate);
            Debug.Log($"[ParkingManager] Spawned pre-checked-in {plate} heading to {targetSlotCode}");
            return vehicle;
        }

        public bool CheckInWaitingVehicle(string plate) => _gateFlow.CheckInWaitingVehicle(plate);

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

        public void OpenSlotBarrier(string slotCode)
        {
            if (string.IsNullOrEmpty(slotCode)) return;
            if (generator == null || !generator.slotRegistry.TryGetValue(slotCode, out var slot))
            {
                Debug.LogWarning($"[ParkingManager] OpenSlotBarrier: slot {slotCode} chưa đăng ký — skip");
                return;
            }

            // Animate barrier if arm exists (optional visual — không block car movement)
            var arm = slot.transform.Find("SlotBarrierArm");
            if (arm != null)
                StartCoroutine(AnimateSlotBarrier(arm, slotCode));
            else
                Debug.LogWarning($"[ParkingManager] Slot {slotCode} thiếu SlotBarrierArm — cần Stop+Play lại để regen");

            // Drive the waiting vehicle into slot regardless of barrier visual state
            bool found = false;
            foreach (var v in FindObjectsOfType<VehicleController>())
            {
                if (v == null || !v.IsAtSlotEntrance) continue;
                if (string.Equals(v.TargetSlot?.slotCode, slotCode, StringComparison.OrdinalIgnoreCase))
                {
                    v.ProceedIntoSlot();
                    found = true;
                    break;
                }
            }
            if (!found)
                Debug.LogWarning($"[ParkingManager] OpenSlotBarrier({slotCode}): không thấy xe nào đang IsAtSlotEntrance ở slot này");
        }

        // === Event Handlers (thin delegation) ===

        private void HandleVehicleAtEntry(VehicleController v) => _gateFlow.HandleVehicleAtEntry(v);
        private void HandleVehicleParked(VehicleController v) => _gateFlow.HandleVehicleParked(v, AutoDepart);
        private void HandleVehicleAtExit(VehicleController v) => _gateFlow.HandleVehicleAtExit(v);

        private void HandleVehicleGone(VehicleController vehicle)
        {
            Debug.Log($"[ParkingManager] {vehicle.plateNumber} left the lot");
            if (vehicleQueue != null) vehicleQueue.NotifyDeparture();
            vehicle.OnReachedGate -= HandleVehicleAtEntry;
            vehicle.OnParked -= HandleVehicleParked;
            vehicle.OnReachedExit -= HandleVehicleAtExit;
            vehicle.OnGone -= HandleVehicleGone;
        }

        private void HandleCheckinSuccess(CheckinSuccessData data)
        {
            if (data == null) return;
            var (plate, bookingId, qrData, slotCode, vehicleType) = _gateFlow.ParseCheckinSuccess(data);
            Debug.Log($"[ParkingManager] 🚗 WebSocket check-in: plate={plate} slot={slotCode} booking={bookingId}");

            // Update local SharedBookingState để Verify Slot / Check-Out dropdown thấy
            // booking này đã checked_in (giống logic trong ESP32Simulator.DoCheckIn).
            if (!string.IsNullOrEmpty(bookingId))
            {
                SharedBookingState.Instance?.UpdateStatus(bookingId, "checked_in");
                SharedBookingState.Instance?.UpdateSlotCode(bookingId, slotCode);
            }

            // Ưu tiên: nếu đã có xe cùng biển số đang waiting tại gate (user spawn
            // thủ công trước, rồi ấn GPIO4 ESP32 vật lý) → release nó thay vì spawn mới.
            if (_gateFlow.CheckInWaitingVehicle(plate))
            {
                Debug.Log($"[ParkingManager] Released waiting vehicle {plate} via WS (physical ESP32 button)");
                return;
            }

            // Fallback: không có xe ở gate → spawn pre-checked-in mới.
            SpawnVehiclePreCheckedIn(plate, bookingId, qrData, slotCode, vehicleType);
        }

        /// <summary>
        /// WS unity.depart_vehicle → tìm xe parked với plate này → StartDeparture.
        /// Kích hoạt khi ESP32 vật lý ấn check-out button.
        /// </summary>
        private void HandleDepartVehicle(string plate)
        {
            if (string.IsNullOrEmpty(plate)) return;
            Debug.Log($"[ParkingManager] 🚗 WS depart signal for plate {plate}");

            // Remove booking khỏi dropdown local (tương đương DoCheckOut success flow)
            var booking = SharedBookingState.Instance?.GetBookingByPlate(plate);
            if (booking != null)
                SharedBookingState.Instance?.RemoveBooking(booking.BookingId);

            foreach (var v in FindObjectsOfType<VehicleController>())
            {
                if (v == null) continue;
                if (string.Equals(v.plateNumber, plate, StringComparison.OrdinalIgnoreCase))
                {
                    v.StartDeparture();
                    Debug.Log($"[ParkingManager] Departing {plate} via WS (physical ESP32 button)");
                    return;
                }
            }
            Debug.LogWarning($"[ParkingManager] WS depart: no vehicle found with plate {plate}");
        }

        private void AutoDepart(VehicleController v, float sec) => StartCoroutine(DepartureTimer(v, sec));

        private IEnumerator DepartureTimer(VehicleController vehicle, float duration)
        {
            yield return new WaitForSeconds(duration);
            if (vehicle == null) yield break;
            Debug.Log($"[ParkingManager] {vehicle.plateNumber} departing after {duration:F0}s");
            vehicle.StartDeparture();
        }

        private IEnumerator AnimateSlotBarrier(Transform arm, string slotCode)
        {
            Debug.Log($"[ParkingManager] 🟢 Slot barrier OPEN → {slotCode}");
            float elapsed = 0f;
            Quaternion closed = arm.localRotation;
            Quaternion open = closed * Quaternion.Euler(0f, -90f, 0f);

            while (elapsed < 0.5f)
            {
                elapsed += Time.deltaTime;
                arm.localRotation = Quaternion.Slerp(closed, open, elapsed / 0.5f);
                yield return null;
            }
            arm.localRotation = open;
            yield return new WaitForSeconds(4f);

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
