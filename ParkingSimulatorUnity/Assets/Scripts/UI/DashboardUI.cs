using System;
using UnityEngine;
using ParkingSim.Core;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;
using ParkingSim.UI.Dashboard;

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
        private ParkingLotGenerator cachedGenerator;

        private Rect windowRect;
        private bool showDashboard = true;

        // Sub-panels
        private EventLogPanel eventLogPanel;
        private StatsPanel statsPanel;

        // Shared styles
        private GUIStyle headerStyle, sectionStyle, bgBoxStyle;
        private bool stylesCreated;
        private Texture2D darkBgTex;

        private void Start()
        {
            if (config == null)
                config = Resources.Load<ApiConfig>("ApiConfig");
            if (apiService == null)
                apiService = ApiService.Instance ?? FindObjectOfType<ApiService>();
            if (authManager == null)
                authManager = AuthManager.Instance ?? FindObjectOfType<AuthManager>();

            float w = 700f, h = 350f;
            windowRect = new Rect((Screen.width - w) / 2f, Screen.height - h - 10f, w, h);

            vehicleQueue = FindObjectOfType<VehicleQueue>();
            cameraMonitorUI = FindObjectOfType<CameraMonitorUI>();
            cachedGenerator = FindObjectOfType<ParkingLotGenerator>();

            eventLogPanel = new EventLogPanel();
            statsPanel = new StatsPanel();

            if (parkingManager != null)
            {
                parkingManager.OnStatusMessage += msg => eventLogPanel.AddEvent(msg, Dashboard.EventType.Info);
                parkingManager.OnInitComplete += () => eventLogPanel.AddEvent("Parking system initialized", Dashboard.EventType.Success);
            }

            if (apiService != null)
            {
                apiService.OnWsConnected += () => eventLogPanel.AddEvent("WebSocket connected", Dashboard.EventType.Connection);
                apiService.OnWsDisconnected += () => eventLogPanel.AddEvent("WebSocket disconnected", Dashboard.EventType.Warning);
                apiService.OnWsError += err => eventLogPanel.AddEvent($"WS error: {err}", Dashboard.EventType.Error);
                apiService.OnSlotStatusUpdate += update =>
                    eventLogPanel.AddEvent($"Slot {update.SlotId} → {update.Status}", Dashboard.EventType.Info);
            }

            eventLogPanel.AddEvent("Dashboard started", Dashboard.EventType.Success);
        }

        private void Update()
        {
            if (statsPanel == null) return;
            statsPanel.Update(Time.deltaTime, Time.unscaledDeltaTime, parkingManager);
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

            sectionStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                fontStyle = FontStyle.Bold
            };
            sectionStyle.normal.textColor = new Color(0.6f, 0.7f, 0.85f);

            eventLogPanel?.EnsureStyles();
            statsPanel?.EnsureStyles();
        }

        private void OnGUI()
        {
            if (statsPanel == null || eventLogPanel == null) return;
            EnsureStyles();

            var btnStyle = new GUIStyle(GUI.skin.button) { fontSize = 12, fontStyle = FontStyle.Bold };
            string btnLabel = showDashboard ? "[H] AN" : "[H] DASHBOARD";
            float btnW = showDashboard ? 70f : 130f;
            if (GUI.Button(new Rect(Screen.width - btnW - 8f, 8f, btnW, 26f), btnLabel, btnStyle))
                showDashboard = !showDashboard;

            if (Event.current.type == UnityEngine.EventType.KeyDown && Event.current.keyCode == KeyCode.H)
                showDashboard = !showDashboard;

            if (!showDashboard) return;

            windowRect = GUILayout.Window(103, windowRect, DrawDashboard, "", bgBoxStyle);
        }

        private void DrawDashboard(int id)
        {
            DrawHeaderBar();
            GUILayout.Space(4);
            statsPanel.DrawStats(sectionStyle);
            GUILayout.Space(4);
            statsPanel.DrawVehicleActivity(sectionStyle, vehicleQueue);
            GUILayout.Space(4);
            statsPanel.DrawConnectionStatus(sectionStyle, authManager, apiService, config);
            GUILayout.Space(4);
            DrawFloorControls();
            GUILayout.Space(4);
            eventLogPanel.Draw(sectionStyle);
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

            int fps = statsPanel.CurrentFps;
            string fpsColor = fps >= 50 ? "lime" : fps >= 30 ? "yellow" : "red";
            var fpsStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                richText = true,
                alignment = TextAnchor.MiddleRight
            };
            GUILayout.Label($"<color={fpsColor}>{fps} FPS</color>", fpsStyle, GUILayout.Width(65));

            var closeStyle = new GUIStyle(GUI.skin.button) { fontSize = 13, fontStyle = FontStyle.Bold };
            closeStyle.normal.textColor = new Color(1f, 0.5f, 0.5f);
            if (GUILayout.Button("X", closeStyle, GUILayout.Width(28), GUILayout.Height(22)))
                showDashboard = false;

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
            if (cachedGenerator == null)
            {
                if (floorManager != null)
                    cachedGenerator = floorManager.GetComponentInParent<ParkingLotGenerator>();
                if (cachedGenerator == null)
                    cachedGenerator = FindObjectOfType<ParkingLotGenerator>();
            }
            return cachedGenerator != null ? cachedGenerator.numberOfFloors : 2;
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
