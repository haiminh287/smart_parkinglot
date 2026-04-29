using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;
using ParkingSim.Core;

namespace ParkingSim.Camera
{
    public class SlotOccupancyDetector : MonoBehaviour, ISlotOccupancyDetector
    {
        [SerializeField] private float detectionInterval = 2f;

        [Header("AI Hybrid Detection")]
        [SerializeField] private float aiDetectionInterval = 5f;
        [SerializeField] private bool enableAiDetection = true;

        [Header("Debug")]
        [SerializeField] private bool showDetectionLog = true;

        private bool isDetecting;
        private Coroutine detectionCoroutine;
        private Coroutine aiDetectionCoroutine;
        private List<ParkingSlot> monitoredSlots = new List<ParkingSlot>();
        private Dictionary<string, bool> previousOccupancy = new Dictionary<string, bool>();
        private Dictionary<string, string> slotCameraMap = new Dictionary<string, string>();
        private int occupiedCount;

        // Statistics
        public event Action<int, int, int> OnStatsChanged;
        public int TotalAvailable { get; private set; }
        public int TotalOccupied { get; private set; }
        public int TotalReserved { get; private set; }

        // Detection log entries
        private readonly List<DetectionLogEntry> detectionLog = new List<DetectionLogEntry>();
        private const int MAX_LOG_ENTRIES = 5;
        private const float LOG_FADE_DURATION = 5f;
        private GUIStyle logStyle;
        private GUIStyle logBgStyle;

        private struct DetectionLogEntry
        {
            public string message;
            public float timestamp;
        }

        public float DetectionInterval
        {
            get => detectionInterval;
            set => detectionInterval = Mathf.Max(0.1f, value);
        }

        public int TotalSlotsMonitored => monitoredSlots.Count;
        public int OccupiedSlotsDetected => occupiedCount;

        public void StartDetection()
        {
            if (isDetecting) return;

            DiscoverSlots();

            if (monitoredSlots.Count == 0)
            {
                Debug.LogWarning("[SlotDetector] No slots found to monitor");
                return;
            }

            if (slotCameraMap.Count == 0)
            {
                AutoAssignCameras();
            }

            isDetecting = true;
            detectionCoroutine = StartCoroutine(DetectionLoop());
            aiDetectionCoroutine = StartCoroutine(AIDetectionLoop());
            Debug.Log($"[SlotDetector] Started — monitoring {monitoredSlots.Count} slots, interval {detectionInterval}s, AI={enableAiDetection}");
        }

        public void StopDetection()
        {
            if (!isDetecting) return;

            isDetecting = false;
            if (detectionCoroutine != null)
            {
                StopCoroutine(detectionCoroutine);
                detectionCoroutine = null;
            }
            if (aiDetectionCoroutine != null)
            {
                StopCoroutine(aiDetectionCoroutine);
                aiDetectionCoroutine = null;
            }

            Debug.Log("[SlotDetector] Stopped");
        }

        public void AssignSlotsToCamera(string cameraId, string[] slotCodes)
        {
            if (slotCodes == null) return;

            foreach (var code in slotCodes)
            {
                slotCameraMap[code] = cameraId;
            }

            Debug.Log($"[SlotDetector] Assigned {slotCodes.Length} slots to camera {cameraId}");
        }

        private void DiscoverSlots()
        {
            monitoredSlots.Clear();
            previousOccupancy.Clear();

            var generator = FindObjectOfType<ParkingLotGenerator>();
            if (generator == null || generator.slotRegistry == null)
            {
                Debug.LogError("[SlotDetector] ParkingLotGenerator not found or slotRegistry is null");
                return;
            }

            foreach (var kvp in generator.slotRegistry)
            {
                if (kvp.Value != null)
                {
                    monitoredSlots.Add(kvp.Value);
                    previousOccupancy[kvp.Value.slotCode] = false;
                }
            }

            Debug.Log($"[SlotDetector] Discovered {monitoredSlots.Count} slots from registry");
        }

        private IEnumerator DetectionLoop()
        {
            // Wait for physics to register newly spawned colliders
            yield return new WaitForFixedUpdate();
            yield return new WaitForFixedUpdate();
            while (isDetecting)
            {
                RunDetectionPass();
                yield return new WaitForSeconds(detectionInterval);
            }
        }

        private void RunDetectionPass()
        {
            // Vehicle prefabs have no colliders (removed by design to avoid blocking navigation).
            // Use position-based detection instead of Physics.OverlapBox.
            var parkedVehicles = FindObjectsOfType<VehicleController>(true);

            int newOccupied = 0;
            var changedSlots = new List<(ParkingSlot slot, bool isOccupied, VehicleController vehicle)>();

            for (int i = 0; i < monitoredSlots.Count; i++)
            {
                var slot = monitoredSlots[i];
                if (slot == null) continue;

                float threshold = slot.slotType == ParkingSlot.SlotType.Motorbike ? 1.5f : 2.5f;
                Vector2 slotXZ = new Vector2(slot.transform.position.x, slot.transform.position.z);

                VehicleController parkedVehicle = null;
                foreach (var vc in parkedVehicles)
                {
                    if (vc == null || vc.state != VehicleController.VehicleState.Parked) continue;
                    Vector2 vcXZ = new Vector2(vc.transform.position.x, vc.transform.position.z);
                    if (Vector2.Distance(vcXZ, slotXZ) < threshold)
                    {
                        parkedVehicle = vc;
                        break;
                    }
                }

                bool isOccupied = parkedVehicle != null;
                if (isOccupied) newOccupied++;

                bool wasOccupied = previousOccupancy.TryGetValue(slot.slotCode, out var prev) && prev;
                if (isOccupied != wasOccupied)
                {
                    changedSlots.Add((slot, isOccupied, parkedVehicle));
                    previousOccupancy[slot.slotCode] = isOccupied;
                }
            }

            occupiedCount = newOccupied;

            Debug.Log($"[SlotDetector] Detection pass: {newOccupied}/{monitoredSlots.Count} occupied, {changedSlots.Count} changed");

            if (changedSlots.Count > 0)
            {
                ProcessChanges(changedSlots, "Physics");
            }

            RecalculateStats();
        }

        private void ProcessChanges(List<(ParkingSlot slot, bool isOccupied, VehicleController vehicle)> changes, string source = "Physics")
        {
            foreach (var (slot, isOccupied, vehicle) in changes)
            {
                ParkingSlot.SlotStatus oldStatus = slot.status;
                ParkingSlot.SlotStatus newStatus = slot.status;

                if (isOccupied && slot.status == ParkingSlot.SlotStatus.Available)
                {
                    newStatus = ParkingSlot.SlotStatus.Occupied;
                    slot.UpdateState(
                        ParkingSlot.SlotStatus.Occupied,
                        vehicle?.plateNumber,
                        vehicle?.bookingId
                    );
                    Debug.Log($"[SlotDetector] {slot.slotCode} → Occupied (plate: {vehicle?.plateNumber}) [{source}]");

                    bool isWrongSlot = CheckWrongSlotParking(slot, vehicle);
                    if (isWrongSlot)
                    {
                        AnimateSlotChange(slot, ParkingSlot.SlotStatus.Maintenance); // magenta strobe for wrong slot
                    }
                    else
                    {
                        AnimateSlotChange(slot, newStatus);
                    }

                    AddLogEntry($"\ud83d\udccd {slot.slotCode}: Available → Occupied [{vehicle?.plateNumber}] [{source}]");
                }
                else if (!isOccupied && slot.status == ParkingSlot.SlotStatus.Occupied)
                {
                    newStatus = ParkingSlot.SlotStatus.Available;
                    slot.UpdateState(ParkingSlot.SlotStatus.Available);
                    Debug.Log($"[SlotDetector] {slot.slotCode} → Available [{source}]");

                    AnimateSlotChange(slot, newStatus);
                    AddLogEntry($"\ud83d\udccd {slot.slotCode}: Occupied → Available [{source}]");
                }
            }

            BroadcastChanges(changes);
        }

        private bool CheckWrongSlotParking(ParkingSlot slot, VehicleController vehicle)
        {
            if (vehicle == null || string.IsNullOrEmpty(vehicle.plateNumber)) return false;

            var bookingState = SharedBookingState.Instance;
            if (bookingState == null) return false;

            // Check if this slot has a booking
            var slotBooking = bookingState.GetBookingBySlotCode(slot.slotCode);

            if (slotBooking != null)
            {
                // Slot is booked — check if the parked vehicle matches
                string expectedPlate = slotBooking.LicensePlate?.Replace("-", "").Replace(".", "").ToUpper();
                string actualPlate = vehicle.plateNumber?.Replace("-", "").Replace(".", "").ToUpper();

                if (!string.IsNullOrEmpty(expectedPlate) && !string.IsNullOrEmpty(actualPlate)
                    && expectedPlate != actualPlate)
                {
                    Debug.LogWarning($"[SlotDetector] WRONG SLOT! {slot.slotCode}: expected plate={slotBooking.LicensePlate}, actual={vehicle.plateNumber}");
                    Debug.LogWarning($"[SlotDetector] Vehicle {vehicle.plateNumber} should NOT be in slot {slot.slotCode} (booked for {slotBooking.LicensePlate})");
                    AddLogEntry($"\u26a0\ufe0f WRONG SLOT: {slot.slotCode} plate={vehicle.plateNumber} (expected {slotBooking.LicensePlate})");
                    return true;
                }
                else
                {
                    Debug.Log($"[SlotDetector] Plate match: {slot.slotCode} → {vehicle.plateNumber}");
                }
            }
            else
            {
                // No booking for this slot — vehicle parked without reservation
                Debug.LogWarning($"[SlotDetector] UNAUTHORIZED: {vehicle.plateNumber} parked at {slot.slotCode} with no booking");
                AddLogEntry($"\u26a0\ufe0f UNAUTHORIZED: {vehicle.plateNumber} at {slot.slotCode}");
                return true;
            }

            return false;
        }

        private void BroadcastChanges(List<(ParkingSlot slot, bool isOccupied, VehicleController vehicle)> changes)
        {
            if (ApiService.Instance == null) return;

            var grouped = new Dictionary<string, List<object>>();

            foreach (var (slot, isOccupied, vehicle) in changes)
            {
                string cameraId = slotCameraMap.TryGetValue(slot.slotCode, out var cam)
                    ? cam
                    : "detector-default";

                if (!grouped.ContainsKey(cameraId))
                    grouped[cameraId] = new List<object>();

                grouped[cameraId].Add(new
                {
                    slot_code = slot.slotCode,
                    is_occupied = isOccupied,
                    plate = vehicle?.plateNumber,
                    booking_id = vehicle?.bookingId
                });
            }

            foreach (var kvp in grouped)
            {
                StartCoroutine(ApiService.Instance.PostSlotDetection(
                    kvp.Key,
                    kvp.Value.ToArray(),
                    ok =>
                    {
                        if (!ok) Debug.LogWarning($"[SlotDetector] Broadcast failed for camera {kvp.Key}");
                    }
                ));
            }
        }

        private static Vector3 GetHalfExtents(ParkingSlot.SlotType slotType)
        {
            switch (slotType)
            {
                case ParkingSlot.SlotType.Garage:
                    return new Vector3(1.5f, 1.25f, 3f);
                case ParkingSlot.SlotType.Motorbike:
                    return new Vector3(0.5f, 0.75f, 1f);
                case ParkingSlot.SlotType.Painted:
                default:
                    return new Vector3(1.25f, 1f, 2.5f);
            }
        }

        private void OnDisable()
        {
            StopDetection();
        }

        // ─── AI Hybrid Detection ────────────────────────

        private IEnumerator AIDetectionLoop()
        {
            while (true)
            {
                yield return new WaitForSeconds(aiDetectionInterval);
                if (!enableAiDetection) continue;
                yield return StartCoroutine(RunAIDetection());
            }
        }

        private IEnumerator RunAIDetection()
        {
            var vcm = VirtualCameraManager.Instance;
            if (vcm == null) yield break;

            var configs = vcm.GetCameraConfigs();
            if (configs == null) yield break;

            if (ApiService.Instance == null) yield break;

            int sent = 0;
            int failed = 0;

            foreach (var cfg in configs)
            {
                if (cfg.cameraId.Contains("gate")) continue; // skip gate cameras

                var streamer = vcm.GetStreamer(cfg.cameraId);
                if (streamer == null || !streamer.IsStreaming) continue;

                byte[] snapshot = streamer.SnapshotJpeg();
                if (snapshot == null || snapshot.Length == 0) continue;

                yield return ApiService.Instance.PostCameraFrame(cfg.cameraId, snapshot, ok =>
                {
                    if (ok) sent++;
                    else failed++;
                });

                yield return null; // spread across frames
            }

            if (sent > 0 || failed > 0)
            {
                Debug.Log($"[SlotDetector/AI] Frames sent: {sent} OK, {failed} failed");
            }
        }

        // ─── Auto Camera Assignment ─────────────────────

        private void AutoAssignCameras()
        {
            int assigned = 0;

            foreach (var slot in monitoredSlots)
            {
                if (slot == null) continue;

                string code = slot.slotCode;
                string cameraId;

                if (code.StartsWith("V1"))
                {
                    cameraId = slot.transform.position.z < 0
                        ? "virtual-zone-south"
                        : "virtual-zone-north";
                }
                else if (code.StartsWith("A") || code.StartsWith("B"))
                {
                    cameraId = "virtual-f2-overview";
                }
                else if (code.StartsWith("V2"))
                {
                    cameraId = "virtual-zone-north";
                }
                else if (code.StartsWith("C"))
                {
                    cameraId = "virtual-zone-south";
                }
                else
                {
                    cameraId = "virtual-f1-overview";
                }

                slotCameraMap[code] = cameraId;
                assigned++;
            }

            Debug.Log($"[SlotDetector] Auto-assigned {assigned} slots to cameras");
        }

        // ─── Slot Visual Animation ──────────────────────

        private void AnimateSlotChange(ParkingSlot slot, ParkingSlot.SlotStatus newStatus)
        {
            StartCoroutine(SlotAnimateCoroutine(slot, newStatus));
        }

        private IEnumerator SlotAnimateCoroutine(ParkingSlot slot, ParkingSlot.SlotStatus newStatus)
        {
            var renderer = slot.GetComponentInChildren<Renderer>();
            if (renderer == null || renderer.material == null) yield break;

            var mat = renderer.material;
            Color settleColor = ParkingSlot.StatusToColor(newStatus);
            bool hasEmissive = mat.HasProperty("_EmissionColor");

            if (newStatus == ParkingSlot.SlotStatus.Maintenance)
            {
                // Wrong slot: strobe magenta rapidly for 3s
                Color magenta = new Color(1f, 0f, 0.7f);
                float endTime = Time.time + 3f;
                while (Time.time < endTime)
                {
                    if (hasEmissive) mat.SetColor("_EmissionColor", magenta * 2f);
                    yield return new WaitForSeconds(0.1f);
                    if (slot == null) yield break;
                    if (hasEmissive) mat.SetColor("_EmissionColor", Color.black);
                    yield return new WaitForSeconds(0.1f);
                    if (slot == null) yield break;
                }
                if (hasEmissive) mat.SetColor("_EmissionColor", Color.black);
            }
            else if (newStatus == ParkingSlot.SlotStatus.Occupied)
            {
                // Flash red 3 times over 1s
                Color flashColor = new Color(1f, 0.1f, 0.1f);
                for (int i = 0; i < 3; i++)
                {
                    if (hasEmissive) mat.SetColor("_EmissionColor", flashColor * 2f);
                    yield return new WaitForSeconds(0.1f);
                    if (slot == null) yield break;
                    if (hasEmissive) mat.SetColor("_EmissionColor", Color.black);
                    yield return new WaitForSeconds(0.23f);
                    if (slot == null) yield break;
                }
            }
            else if (newStatus == ParkingSlot.SlotStatus.Available)
            {
                // Flash green 3 times over 1s
                Color flashColor = new Color(0.1f, 1f, 0.2f);
                for (int i = 0; i < 3; i++)
                {
                    if (hasEmissive) mat.SetColor("_EmissionColor", flashColor * 2f);
                    yield return new WaitForSeconds(0.1f);
                    if (slot == null) yield break;
                    if (hasEmissive) mat.SetColor("_EmissionColor", Color.black);
                    yield return new WaitForSeconds(0.23f);
                    if (slot == null) yield break;
                }
            }

            if (hasEmissive) mat.SetColor("_EmissionColor", Color.black);
        }

        // ─── Statistics ─────────────────────────────────

        private void RecalculateStats()
        {
            int available = 0, occupied = 0, reserved = 0;

            foreach (var slot in monitoredSlots)
            {
                if (slot == null) continue;
                switch (slot.status)
                {
                    case ParkingSlot.SlotStatus.Available: available++; break;
                    case ParkingSlot.SlotStatus.Occupied: occupied++; break;
                    case ParkingSlot.SlotStatus.Reserved: reserved++; break;
                }
            }

            bool changed = available != TotalAvailable || occupied != TotalOccupied || reserved != TotalReserved;
            TotalAvailable = available;
            TotalOccupied = occupied;
            TotalReserved = reserved;

            if (changed)
            {
                OnStatsChanged?.Invoke(TotalAvailable, TotalOccupied, TotalReserved);
            }
        }

        // ─── Detection Log ──────────────────────────────

        private void AddLogEntry(string message)
        {
            detectionLog.Add(new DetectionLogEntry
            {
                message = message,
                timestamp = Time.time
            });

            while (detectionLog.Count > MAX_LOG_ENTRIES)
            {
                detectionLog.RemoveAt(0);
            }
        }

        private void OnGUI()
        {
            if (!showDetectionLog || detectionLog.Count == 0) return;

            // Remove expired entries
            detectionLog.RemoveAll(e => Time.time - e.timestamp > LOG_FADE_DURATION);
            if (detectionLog.Count == 0) return;

            if (logStyle == null)
            {
                logStyle = new GUIStyle(GUI.skin.label)
                {
                    fontSize = 12,
                    alignment = TextAnchor.MiddleLeft,
                    wordWrap = false,
                    richText = true
                };
                logStyle.normal.textColor = Color.white;
                logStyle.padding = new RectOffset(6, 6, 2, 2);
            }

            if (logBgStyle == null)
            {
                logBgStyle = new GUIStyle(GUI.skin.box);
                var bgTex = new Texture2D(1, 1);
                bgTex.SetPixel(0, 0, new Color(0.1f, 0.1f, 0.15f, 0.85f));
                bgTex.Apply();
                logBgStyle.normal.background = bgTex;
            }

            float panelWidth = 420f;
            float lineHeight = 20f;
            float panelHeight = detectionLog.Count * lineHeight + 30f;
            float x = Screen.width - panelWidth - 20f;
            float y = Screen.height - panelHeight - 20f;

            GUI.Box(new Rect(x, y, panelWidth, panelHeight), "", logBgStyle);

            var titleStyle = new GUIStyle(logStyle) { fontStyle = FontStyle.Bold, fontSize = 13 };
            GUI.Label(new Rect(x + 6, y + 2, panelWidth - 12, 22f), "Detection Log", titleStyle);

            for (int i = 0; i < detectionLog.Count; i++)
            {
                var entry = detectionLog[i];
                float age = Time.time - entry.timestamp;
                float alpha = Mathf.Clamp01(1f - (age / LOG_FADE_DURATION));

                var fadeStyle = new GUIStyle(logStyle);
                fadeStyle.normal.textColor = new Color(1f, 1f, 1f, alpha);

                float entryY = y + 24f + i * lineHeight;
                GUI.Label(new Rect(x + 6, entryY, panelWidth - 12, lineHeight), entry.message, fadeStyle);
            }
        }
    }
}
