using System;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.Core;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;

namespace ParkingSim.UI
{
    public class DashboardUI : MonoBehaviour
    {
        [SerializeField] private ParkingManager parkingManager;
        [SerializeField] private FloorVisibilityManager floorManager;
        [SerializeField] private ApiService apiService;
        [SerializeField] private AuthManager authManager;
        [SerializeField] private ApiConfig config;

        private VehicleQueue vehicleQueue;
        private CameraMonitorUI cameraMonitorUI;

        private List<EventEntry> eventLog = new List<EventEntry>();
        private int maxLogEntries = 50;
        private int maxVisibleEntries = 20;
        private Vector2 logScrollPos;
        private Rect windowRect;
        private bool showDashboard = true;

        private float statsRefreshTimer;
        private const float STATS_REFRESH_INTERVAL = 0.5f;
        private int statTotal, statAvailable, statOccupied, statReserved, statMaintenance;

        // Animated display values
        private float displayAvailable, displayOccupied, displayReserved;
        private float targetAvailable, targetOccupied, targetReserved;
        private const float LERP_SPEED = 4f;

        // FPS
        private int currentFps;
        private float fpsTimer;
        private int fpsFrameCount;

        // Custom styles
        private GUIStyle headerStyle, statLabelStyle, eventStyle, sectionStyle;
        private GUIStyle bgBoxStyle, eventGreenStyle, eventRedStyle, eventYellowStyle;
        private bool stylesCreated;
        private Texture2D darkBgTex;

        private struct EventEntry
        {
            public string timestamp;
            public string message;
            public EventType type;
        }

        private enum EventType
        {
            Info, Success, Warning, Error, Connection
        }

        private void Start()
        {
            float w = 700f, h = 350f;
            windowRect = new Rect((Screen.width - w) / 2f, Screen.height - h - 10f, w, h);

            vehicleQueue = FindObjectOfType<VehicleQueue>();
            cameraMonitorUI = FindObjectOfType<CameraMonitorUI>();

            if (parkingManager != null)
            {
                parkingManager.OnStatusMessage += msg => AddEvent(msg, EventType.Info);
                parkingManager.OnInitComplete += () => AddEvent("Parking system initialized", EventType.Success);
            }

            if (apiService != null)
            {
                apiService.OnWsConnected += () => AddEvent("WebSocket connected", EventType.Connection);
                apiService.OnWsDisconnected += () => AddEvent("WebSocket disconnected", EventType.Warning);
                apiService.OnWsError += err => AddEvent($"WS error: {err}", EventType.Error);
                apiService.OnSlotStatusUpdate += update =>
                    AddEvent($"Slot {update.SlotId} → {update.Status}", EventType.Info);
            }

            AddEvent("Dashboard started", EventType.Success);
        }

        private void Update()
        {
            statsRefreshTimer += Time.deltaTime;
            if (statsRefreshTimer >= STATS_REFRESH_INTERVAL)
            {
                statsRefreshTimer = 0f;
                RefreshStats();
            }

            // Animate stat display values
            displayAvailable = Mathf.Lerp(displayAvailable, targetAvailable, LERP_SPEED * Time.deltaTime);
            displayOccupied = Mathf.Lerp(displayOccupied, targetOccupied, LERP_SPEED * Time.deltaTime);
            displayReserved = Mathf.Lerp(displayReserved, targetReserved, LERP_SPEED * Time.deltaTime);

            // FPS counter
            fpsFrameCount++;
            fpsTimer += Time.unscaledDeltaTime;
            if (fpsTimer >= 0.5f)
            {
                currentFps = Mathf.RoundToInt(fpsFrameCount / fpsTimer);
                fpsFrameCount = 0;
                fpsTimer = 0f;
            }
        }

        private void RefreshStats()
        {
            if (parkingManager == null) return;
            var stats = parkingManager.GetSlotStats();
            statTotal = stats.total;
            statAvailable = stats.available;
            statOccupied = stats.occupied;
            statReserved = stats.reserved;
            statMaintenance = stats.maintenance;

            targetAvailable = statAvailable;
            targetOccupied = statOccupied;
            targetReserved = statReserved;
        }

        private void AddEvent(string message, EventType type = EventType.Info)
        {
            string emoji = type switch
            {
                EventType.Success => "[OK]",
                EventType.Warning => "[!]",
                EventType.Error => "[ERR]",
                EventType.Connection => "[WS]",
                _ => "[i]"
            };

            eventLog.Add(new EventEntry
            {
                timestamp = DateTime.Now.ToString("HH:mm:ss"),
                message = $"{emoji} {message}",
                type = type
            });

            if (eventLog.Count > maxLogEntries)
                eventLog.RemoveAt(0);

            // Auto-scroll to bottom
            logScrollPos.y = float.MaxValue;
        }

        private void EnsureStyles()
        {
            if (stylesCreated) return;
            stylesCreated = true;

            darkBgTex = MakeTex(2, 2, new Color(0.1f, 0.1f, 0.13f, 0.93f));

            bgBoxStyle = new GUIStyle(GUI.skin.box);
            bgBoxStyle.normal.background = darkBgTex;
            bgBoxStyle.padding = new RectOffset(8, 8, 6, 6);

            headerStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 16,
                fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleLeft
            };
            headerStyle.normal.textColor = new Color(0.85f, 0.9f, 1f);

            statLabelStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 13,
                fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleCenter
            };

            sectionStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                fontStyle = FontStyle.Bold
            };
            sectionStyle.normal.textColor = new Color(0.6f, 0.7f, 0.85f);

            eventStyle = new GUIStyle(GUI.skin.label) { fontSize = 11, richText = true };
            eventStyle.normal.textColor = new Color(0.75f, 0.75f, 0.78f);

            eventGreenStyle = new GUIStyle(eventStyle);
            eventGreenStyle.normal.textColor = new Color(0.4f, 0.9f, 0.4f);

            eventRedStyle = new GUIStyle(eventStyle);
            eventRedStyle.normal.textColor = new Color(0.95f, 0.4f, 0.4f);

            eventYellowStyle = new GUIStyle(eventStyle);
            eventYellowStyle.normal.textColor = new Color(0.95f, 0.85f, 0.3f);
        }

        private void OnGUI()
        {
            EnsureStyles();

            // Always-visible toggle button at top-right corner (plain ASCII - IMGUI safe)
            var btnStyle = new GUIStyle(GUI.skin.button) { fontSize = 12, fontStyle = FontStyle.Bold };
            string btnLabel = showDashboard ? "[H] AN" : "[H] DASHBOARD";
            float btnW = showDashboard ? 70f : 130f;
            if (GUI.Button(new Rect(Screen.width - btnW - 8f, 8f, btnW, 26f), btnLabel, btnStyle))
                showDashboard = !showDashboard;

            // Keyboard toggle
            if (Event.current.type == UnityEngine.EventType.KeyDown && Event.current.keyCode == KeyCode.H)
                showDashboard = !showDashboard;

            if (!showDashboard) return;

            windowRect = GUILayout.Window(103, windowRect, DrawDashboard, "", bgBoxStyle);
        }

        private void DrawDashboard(int id)
        {
            DrawHeaderBar();
            GUILayout.Space(4);
            DrawStatsBar();
            GUILayout.Space(4);
            DrawVehicleActivity();
            GUILayout.Space(4);
            DrawConnectionStatus();
            GUILayout.Space(4);
            DrawFloorControls();
            GUILayout.Space(4);
            DrawEventLog();
            GUILayout.Space(4);
            DrawControlsRow();

            GUI.DragWindow();
        }

        private void DrawHeaderBar()
        {
            GUILayout.BeginHorizontal();

            GUILayout.Label("[P] ParkSmart Dashboard", headerStyle);

            GUILayout.FlexibleSpace();

            var clockStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                alignment = TextAnchor.MiddleRight
            };
            clockStyle.normal.textColor = new Color(0.7f, 0.8f, 0.9f);

            GUILayout.Label(DateTime.Now.ToString("HH:mm:ss"), clockStyle, GUILayout.Width(65));

            string fpsColor = currentFps >= 50 ? "lime" : currentFps >= 30 ? "yellow" : "red";
            var fpsStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                richText = true,
                alignment = TextAnchor.MiddleRight
            };
            GUILayout.Label($"<color={fpsColor}>{currentFps} FPS</color>", fpsStyle, GUILayout.Width(65));

            // Close button in header (plain ASCII)
            var closeStyle = new GUIStyle(GUI.skin.button) { fontSize = 13, fontStyle = FontStyle.Bold };
            closeStyle.normal.textColor = new Color(1f, 0.5f, 0.5f);
            if (GUILayout.Button("X", closeStyle, GUILayout.Width(28), GUILayout.Height(22)))
                showDashboard = false;

            GUILayout.EndHorizontal();
        }

        private void DrawStatsBar()
        {
            GUILayout.Label("── Statistics ──", sectionStyle);
            GUILayout.BeginHorizontal();

            var prev = GUI.contentColor;

            GUILayout.Label($"Total: {statTotal}", statLabelStyle, GUILayout.Width(70));

            GUI.contentColor = Color.green;
            GUILayout.Label($"[+] Available: {Mathf.RoundToInt(displayAvailable)}", statLabelStyle, GUILayout.Width(120));

            GUI.contentColor = new Color(1f, 0.35f, 0.35f);
            GUILayout.Label($"[x] Occupied: {Mathf.RoundToInt(displayOccupied)}", statLabelStyle, GUILayout.Width(115));

            GUI.contentColor = Color.yellow;
            GUILayout.Label($"[R] Reserved: {Mathf.RoundToInt(displayReserved)}", statLabelStyle, GUILayout.Width(115));

            GUI.contentColor = Color.grey;
            GUILayout.Label($"Maint: {statMaintenance}", statLabelStyle, GUILayout.Width(70));

            // Occupancy with color coding
            float occupancy = statTotal > 0 ? (1f - (float)statAvailable / statTotal) * 100f : 0f;
            if (occupancy >= 80f) GUI.contentColor = new Color(1f, 0.3f, 0.3f);
            else if (occupancy >= 50f) GUI.contentColor = Color.yellow;
            else GUI.contentColor = Color.green;
            GUILayout.Label($"{occupancy:F0}%", statLabelStyle, GUILayout.Width(45));

            GUI.contentColor = prev;
            GUILayout.EndHorizontal();
        }

        private void DrawVehicleActivity()
        {
            GUILayout.Label("── Vehicle Activity ──", sectionStyle);
            GUILayout.BeginHorizontal();

            if (vehicleQueue != null)
            {
                var prev = GUI.contentColor;

                GUI.contentColor = Color.cyan;
                GUILayout.Label($"[CAR] Active: {vehicleQueue.ActiveVehicles}", GUILayout.Width(100));

                GUI.contentColor = new Color(0.7f, 0.85f, 1f);
                GUILayout.Label($"Spawned: {vehicleQueue.TotalSpawned}", GUILayout.Width(100));

                GUI.contentColor = new Color(0.8f, 0.8f, 0.8f);
                GUILayout.Label($"Departed: {vehicleQueue.TotalDeparted}", GUILayout.Width(110));

                GUI.contentColor = prev;

                GUILayout.Label(
                    $"Entry Q: {vehicleQueue.GetEntryQueueSize()} | Exit Q: {vehicleQueue.GetExitQueueSize()}");
            }
            else
            {
                GUILayout.Label("VehicleQueue not found");
            }

            GUILayout.EndHorizontal();
        }

        private void DrawConnectionStatus()
        {
            GUILayout.Label("── Connection ──", sectionStyle);
            GUILayout.BeginHorizontal();

            bool apiOk = authManager != null && authManager.IsAuthenticated;
            GUILayout.Label($"API: {(apiOk ? "✅ Connected" : "❌ Disconnected")}");

            bool wsOk = apiService != null && apiService.IsWsConnected;
            GUILayout.Label($"WS: {(wsOk ? "✅ Connected" : "❌ Disconnected")}");

            bool isMock = config != null && config.useMockData;
            GUILayout.Label($"Mode: [{(isMock ? "MOCK" : "LIVE")}]");

            GUILayout.EndHorizontal();
        }

        private void DrawFloorControls()
        {
            if (floorManager == null) return;

            GUILayout.Label("── Floors ──", sectionStyle);
            GUILayout.BeginHorizontal();

            int totalFloors = parkingManager != null
                ? parkingManager.GetSlotStats().total > 0 ? GetFloorCount() : 2
                : 2;

            for (int i = 0; i < totalFloors; i++)
            {
                string label = $"F{i + 1}";
                if (floorManager.CurrentFloor == i)
                    label = $"[{label}]";

                if (GUILayout.Button(label, GUILayout.Width(40)))
                    floorManager.ShowFloor(i);
            }

            if (GUILayout.Button("All", GUILayout.Width(40)))
                floorManager.ShowAllFloors();

            GUILayout.EndHorizontal();
        }

        private int GetFloorCount()
        {
            var gen = floorManager.GetComponentInParent<ParkingLotGenerator>();
            if (gen == null) gen = FindObjectOfType<ParkingLotGenerator>();
            return gen != null ? gen.numberOfFloors : 2;
        }

        private void DrawEventLog()
        {
            GUILayout.Label("── Events ──", sectionStyle);
            logScrollPos = GUILayout.BeginScrollView(logScrollPos, GUILayout.Height(80));

            int start = Mathf.Max(0, eventLog.Count - maxVisibleEntries);
            for (int i = start; i < eventLog.Count; i++)
            {
                var entry = eventLog[i];
                GUIStyle style = entry.type switch
                {
                    EventType.Success => eventGreenStyle,
                    EventType.Error => eventRedStyle,
                    EventType.Warning => eventYellowStyle,
                    _ => eventStyle
                };
                GUILayout.Label($"[{entry.timestamp}] {entry.message}", style);
            }

            GUILayout.EndScrollView();
        }

        private void DrawControlsRow()
        {
            GUILayout.BeginHorizontal();

            var hintStyle = new GUIStyle(GUI.skin.label) { fontSize = 10 };
            hintStyle.normal.textColor = new Color(0.5f, 0.5f, 0.55f);
            GUILayout.Label("[H] = An/Hien  |  Keo tieu de de di chuyen", hintStyle);

            GUILayout.FlexibleSpace();

            if (GUILayout.Button("[CAM] Cameras", GUILayout.Width(100)))
            {
                if (cameraMonitorUI != null)
                    cameraMonitorUI.gameObject.SetActive(!cameraMonitorUI.gameObject.activeSelf);
            }

            GUILayout.EndHorizontal();
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
