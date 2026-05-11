using UnityEngine;
using ParkingSim.Core;
using ParkingSim.API;
using ParkingSim.Vehicle;

namespace ParkingSim.UI.Dashboard
{
    public class StatsPanel
    {
        private const float STATS_REFRESH_INTERVAL = 0.5f;
        private const float LERP_SPEED = 4f;

        private float statsRefreshTimer;
        private int statTotal, statAvailable, statOccupied, statReserved, statMaintenance;
        private float displayAvailable, displayOccupied, displayReserved;
        private float targetAvailable, targetOccupied, targetReserved;

        private int currentFps;
        private float fpsTimer;
        private int fpsFrameCount;

        private GUIStyle statLabelStyle;
        private bool stylesCreated;

        public int CurrentFps => currentFps;

        public void Update(float deltaTime, float unscaledDeltaTime, ParkingManager parkingManager)
        {
            // Stats refresh
            statsRefreshTimer += deltaTime;
            if (statsRefreshTimer >= STATS_REFRESH_INTERVAL)
            {
                statsRefreshTimer = 0f;
                RefreshStats(parkingManager);
            }

            // Animate stat display values
            displayAvailable = Mathf.Lerp(displayAvailable, targetAvailable, LERP_SPEED * deltaTime);
            displayOccupied = Mathf.Lerp(displayOccupied, targetOccupied, LERP_SPEED * deltaTime);
            displayReserved = Mathf.Lerp(displayReserved, targetReserved, LERP_SPEED * deltaTime);

            // FPS counter
            fpsFrameCount++;
            fpsTimer += unscaledDeltaTime;
            if (fpsTimer >= 0.5f)
            {
                currentFps = Mathf.RoundToInt(fpsFrameCount / fpsTimer);
                fpsFrameCount = 0;
                fpsTimer = 0f;
            }
        }

        private void RefreshStats(ParkingManager parkingManager)
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

        public void EnsureStyles()
        {
            if (stylesCreated) return;
            stylesCreated = true;

            statLabelStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 13,
                fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleCenter
            };
        }

        public void DrawStats(GUIStyle sectionStyle)
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

            float occupancy = statTotal > 0 ? (1f - (float)statAvailable / statTotal) * 100f : 0f;
            if (occupancy >= 80f) GUI.contentColor = new Color(1f, 0.3f, 0.3f);
            else if (occupancy >= 50f) GUI.contentColor = Color.yellow;
            else GUI.contentColor = Color.green;
            GUILayout.Label($"{occupancy:F0}%", statLabelStyle, GUILayout.Width(45));

            GUI.contentColor = prev;
            GUILayout.EndHorizontal();
        }

        public void DrawVehicleActivity(GUIStyle sectionStyle, VehicleQueue vehicleQueue)
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

        public void DrawConnectionStatus(GUIStyle sectionStyle, AuthManager authManager,
            ApiService apiService, ApiConfig config)
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
    }
}
