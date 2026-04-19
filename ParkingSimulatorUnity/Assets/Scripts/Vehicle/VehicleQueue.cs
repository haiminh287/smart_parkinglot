using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using ParkingSim.Core;
using ParkingSim.Parking;
using ParkingSim.API;

namespace ParkingSim.Vehicle
{
    public class VehicleQueue : MonoBehaviour
    {
        private Queue<VehicleController> entryQueue = new Queue<VehicleController>();
        private Queue<VehicleController> exitQueue = new Queue<VehicleController>();

        public bool isEntryProcessing;
        public bool isExitProcessing;

        [SerializeField] private float queueSpacing = 4f;
        [SerializeField] private Transform entryQueueStart;
        [SerializeField] private Transform exitQueueStart;

        [Header("Auto Spawn")]
        [SerializeField] private bool autoSpawnEnabled = false;
        [SerializeField] private float spawnIntervalMin = 15f;
        [SerializeField] private float spawnIntervalMax = 45f;
        [SerializeField] private bool waveMode = false;
        [SerializeField] private int waveSize = 4;
        [SerializeField] private float waveInterval = 60f;
        [SerializeField] private int maxActiveVehicles = 15;
        [SerializeField] private ApiConfig config;

        // Stats
        public int TotalSpawned { get; private set; }
        public int TotalDeparted { get; private set; }
        public int ActiveVehicles => TotalSpawned - TotalDeparted;

        private ParkingLotGenerator generatorRef;
        private bool showSpawnerGUI = true;
        private Rect guiRect;

        private static readonly string[] ProvinceCodes =
            { "51", "30", "29", "77", "59", "43", "92", "48", "61", "15", "47" };
        private static readonly char[] PlateLetters =
            { 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'K', 'L', 'M', 'N' };

        private void Start()
        {
            if (config == null)
                config = Resources.Load<ApiConfig>("ApiConfig");

            generatorRef = FindObjectOfType<ParkingLotGenerator>();

            float w = 260f, h = 170f;
            guiRect = new Rect(10f, 10f, w, h);

            if (autoSpawnEnabled)
            {
                if (waveMode)
                    StartCoroutine(WaveSpawnCoroutine());
                else
                    StartCoroutine(AutoSpawnCoroutine());
            }
        }

        // ── Existing Queue Logic ─────────────────────────────

        public void EnqueueEntry(VehicleController vehicle)
        {
            if (vehicle == null) return;
            entryQueue.Enqueue(vehicle);
            PositionInQueue(vehicle, entryQueue, entryQueueStart);
            Debug.Log($"[VehicleQueue] {vehicle.plateNumber} queued at entry (pos: {entryQueue.Count})");
        }

        public void EnqueueExit(VehicleController vehicle)
        {
            if (vehicle == null) return;
            exitQueue.Enqueue(vehicle);
            PositionInQueue(vehicle, exitQueue, exitQueueStart);
            Debug.Log($"[VehicleQueue] {vehicle.plateNumber} queued at exit (pos: {exitQueue.Count})");
        }

        public VehicleController DequeueEntry()
        {
            if (entryQueue.Count == 0) return null;
            var vehicle = entryQueue.Dequeue();
            ShiftQueue(entryQueue, entryQueueStart);
            Debug.Log($"[VehicleQueue] {vehicle.plateNumber} dequeued from entry");
            return vehicle;
        }

        public VehicleController DequeueExit()
        {
            if (exitQueue.Count == 0) return null;
            var vehicle = exitQueue.Dequeue();
            ShiftQueue(exitQueue, exitQueueStart);
            Debug.Log($"[VehicleQueue] {vehicle.plateNumber} dequeued from exit");
            return vehicle;
        }

        public int GetEntryQueueSize() => entryQueue.Count;
        public int GetExitQueueSize() => exitQueue.Count;

        private void Update()
        {
            SmoothQueuePositions(entryQueue, entryQueueStart);
            SmoothQueuePositions(exitQueue, exitQueueStart);
        }

        private void PositionInQueue(VehicleController vehicle, Queue<VehicleController> queue, Transform queueStart)
        {
            if (queueStart == null) return;
            int index = queue.Count - 1;
            Vector3 offset = -queueStart.forward * (queueSpacing * index);
            vehicle.transform.position = queueStart.position + offset;
        }

        private void ShiftQueue(Queue<VehicleController> queue, Transform queueStart)
        {
            if (queueStart == null) return;
            int index = 0;
            foreach (var v in queue)
            {
                if (v == null) { index++; continue; }
                Vector3 targetPos = queueStart.position + (-queueStart.forward * (queueSpacing * index));
                v.transform.position = targetPos;
                index++;
            }
        }

        private void SmoothQueuePositions(Queue<VehicleController> queue, Transform queueStart)
        {
            if (queueStart == null || queue.Count == 0) return;
            int index = 0;
            foreach (var v in queue)
            {
                if (v == null) { index++; continue; }
                Vector3 targetPos = queueStart.position + (-queueStart.forward * (queueSpacing * index));
                v.transform.position = Vector3.MoveTowards(v.transform.position, targetPos, 3f * Time.deltaTime);
                index++;
            }
        }

        // ── Auto Spawn ──────────────────────────────────────

        private IEnumerator AutoSpawnCoroutine()
        {
            yield return new WaitForSeconds(3f); // initial delay for system init
            while (true)
            {
                float interval = Random.Range(spawnIntervalMin, spawnIntervalMax);
                yield return new WaitForSeconds(interval);

                if (!autoSpawnEnabled) continue;
                if (ActiveVehicles >= maxActiveVehicles) continue;

                AutoSpawnVehicle("Car");
            }
        }

        private IEnumerator WaveSpawnCoroutine()
        {
            yield return new WaitForSeconds(3f);
            while (true)
            {
                yield return new WaitForSeconds(waveInterval);

                if (!autoSpawnEnabled) continue;

                int toSpawn = Mathf.Min(waveSize, maxActiveVehicles - ActiveVehicles);
                for (int i = 0; i < toSpawn; i++)
                {
                    string vType = Random.value > 0.7f ? "Motorbike" : "Car";
                    AutoSpawnVehicle(vType);
                    yield return new WaitForSeconds(1.5f); // stagger within wave
                }
            }
        }

        private void AutoSpawnVehicle(string vehicleType = "Car")
        {
            if (ParkingManager.Instance == null || generatorRef == null) return;
            if (generatorRef.slotRegistry == null || generatorRef.slotRegistry.Count == 0) return;

            // Trigger sync trước khi spawn để lấy booking MỚI NHẤT từ web/API.
            // Sau đó delay 1 frame rồi spawn với booking mới.
            StartCoroutine(SyncAndSpawn(vehicleType));
        }

        private System.Collections.IEnumerator SyncAndSpawn(string vehicleType)
        {
            var apiService = ParkingSim.API.ApiService.Instance;
            if (apiService != null)
            {
                bool synced = false;
                ParkingSim.API.ApiResponse<ParkingSim.API.PaginatedResponse<ParkingSim.API.BookingData>> result = null;
                yield return apiService.GetBookings(r => { result = r; synced = true; });
                if (synced && result != null && result.IsSuccess && result.Data?.Results != null)
                {
                    int added = SharedBookingState.Instance?.SyncFromApi(result.Data.Results) ?? 0;
                    if (added > 0)
                        Debug.Log($"[VehicleQueue] Pre-spawn sync: loaded {added} booking(s)");
                }
            }

            // Ưu tiên booking ActiveCheckInBookingId (user đã chọn trong ESP32 dropdown).
            var pendingBookings = SharedBookingState.Instance?.GetNotCheckedIn();
            ActiveBooking pendingBooking = null;
            string activeId = ParkingSim.IoT.ESP32Simulator.ActiveCheckInBookingId;
            if (!string.IsNullOrEmpty(activeId) && pendingBookings != null)
            {
                pendingBooking = pendingBookings.Find(b =>
                    b != null && b.BookingId == activeId &&
                    (vehicleType == "Motorbike"
                        ? b.VehicleType == "Motorbike"
                        : b.VehicleType != "Motorbike"));
            }
            // Fallback: lấy booking mới nhất (sort theo BookingId reverse — UUID-ish ordering by creation time)
            if (pendingBooking == null && pendingBookings != null && pendingBookings.Count > 0)
            {
                var filtered = pendingBookings.FindAll(b =>
                    vehicleType == "Motorbike"
                        ? b.VehicleType == "Motorbike"
                        : b.VehicleType != "Motorbike");
                pendingBooking = filtered.Count > 0 ? filtered[filtered.Count - 1] : null;
            }

            if (pendingBooking != null)
            {
                string bkPlate = pendingBooking.LicensePlate ?? "UNKNOWN";
                string bkId = pendingBooking.BookingId;
                string bkQr = pendingBooking.QrCodeData
                              ?? $"{{\"booking_id\":\"{bkId}\"}}";
                string slotCode = pendingBooking.SlotCode;

                if (!string.IsNullOrEmpty(slotCode)
                    && generatorRef.slotRegistry.ContainsKey(slotCode))
                {
                    ParkingManager.Instance.SpawnVehicle(bkPlate, bkId, bkQr,
                        slotCode, pendingBooking.VehicleType ?? vehicleType);
                    TotalSpawned++;
                    Debug.Log($"[VehicleQueue] Spawned BOOKING vehicle plate={bkPlate} → {slotCode} (booking={bkId.Substring(0, 8)})");
                    yield break;
                }
            }

            // No real booking → KHÔNG spawn random (tránh biển số lạ).
            // User cần tạo booking qua web hoặc chạy create_unity_checkin_booking.py.
            Debug.LogWarning($"[VehicleQueue] No pending {vehicleType} booking — tạo booking qua web/script trước khi spawn");
        }

        // ── Plate Generator ─────────────────────────────────

        private string GenerateRandomPlate()
        {
            string province = ProvinceCodes[Random.Range(0, ProvinceCodes.Length)];
            char letter = PlateLetters[Random.Range(0, PlateLetters.Length)];
            int digits3 = Random.Range(100, 999);
            int digits2 = Random.Range(10, 99);
            return $"{province}{letter}-{digits3}.{digits2}";
        }

        // ── Departure Tracking ──────────────────────────────

        public void NotifyDeparture()
        {
            TotalDeparted++;
            Debug.Log($"[VehicleQueue] Departure tracked. Active={ActiveVehicles}");
        }

        // ── OnGUI Panel ─────────────────────────────────────

        private void OnGUI()
        {
            if (!showSpawnerGUI) return;
            guiRect = GUILayout.Window(200, guiRect, DrawSpawnerPanel, "");
        }

        private void DrawSpawnerPanel(int id)
        {
            var bgStyle = new GUIStyle(GUI.skin.box);
            bgStyle.normal.background = MakeTex(2, 2, new Color(0.12f, 0.12f, 0.15f, 0.92f));

            GUILayout.BeginVertical(bgStyle);

            // Header
            var headerStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 14,
                fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleCenter
            };
            headerStyle.normal.textColor = new Color(0.9f, 0.9f, 0.95f);
            GUILayout.Label("── Vehicle Spawner ──", headerStyle);

            GUILayout.Space(4);

            // Stats row
            GUILayout.BeginHorizontal();
            GUILayout.Label($"Spawned: {TotalSpawned}", GUILayout.Width(85));
            GUI.contentColor = Color.cyan;
            GUILayout.Label($"Active: {ActiveVehicles}", GUILayout.Width(75));
            GUI.contentColor = Color.gray;
            GUILayout.Label($"Departed: {TotalDeparted}");
            GUI.contentColor = Color.white;
            GUILayout.EndHorizontal();

            GUILayout.Space(4);

            // Toggle auto spawn
            bool newAutoSpawn = GUILayout.Toggle(autoSpawnEnabled,
                autoSpawnEnabled ? " Auto Spawn: ON" : " Auto Spawn: OFF");
            if (newAutoSpawn != autoSpawnEnabled)
            {
                autoSpawnEnabled = newAutoSpawn;
                if (autoSpawnEnabled)
                {
                    StopAllCoroutines();
                    if (waveMode)
                        StartCoroutine(WaveSpawnCoroutine());
                    else
                        StartCoroutine(AutoSpawnCoroutine());
                }
            }

            GUILayout.Space(2);

            // Manual spawn buttons
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("+Spawn Car"))
                AutoSpawnVehicle("Car");
            if (GUILayout.Button("+Spawn Motorbike"))
                AutoSpawnVehicle("Motorbike");
            GUILayout.EndHorizontal();

            GUILayout.Space(2);

            // Mode toggle
            GUILayout.BeginHorizontal();
            GUILayout.Label("Mode:", GUILayout.Width(40));
            if (GUILayout.Button(waveMode ? "Wave" : "Normal"))
            {
                waveMode = !waveMode;
                if (autoSpawnEnabled)
                {
                    StopAllCoroutines();
                    if (waveMode)
                        StartCoroutine(WaveSpawnCoroutine());
                    else
                        StartCoroutine(AutoSpawnCoroutine());
                }
            }
            GUILayout.Label($"Max: {maxActiveVehicles}", GUILayout.Width(60));
            GUILayout.EndHorizontal();

            GUILayout.EndVertical();

            GUI.DragWindow();
        }

        private static Texture2D MakeTex(int w, int h, Color col)
        {
            var pix = new Color[w * h];
            for (int i = 0; i < pix.Length; i++) pix[i] = col;
            var tex = new Texture2D(w, h);
            tex.SetPixels(pix);
            tex.Apply();
            return tex;
        }
    }
}
