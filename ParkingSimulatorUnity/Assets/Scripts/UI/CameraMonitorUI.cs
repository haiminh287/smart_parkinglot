using System.Collections;
using UnityEngine;
using ParkingSim.Camera;
using ParkingSim.Core;

namespace ParkingSim.UI
{
    public class CameraMonitorUI : MonoBehaviour
    {
        private bool showPanel = false;
        private Rect windowRect;
        private int selectedCameraIdx = -1; // -1 = grid view
        private bool isDemoRunning;
        private string demoStatus = "";
        private Vector2 scrollPos;

        private void Start()
        {
            float w = 480, h = 500;
            windowRect = new Rect(Screen.width - w - 10, 60, w, h);
        }

        private void OnGUI()
        {
            // Toggle button
            if (!showPanel)
            {
                if (GUI.Button(new Rect(Screen.width - 180, 60, 170, 30), "📹 Show Cameras"))
                    showPanel = true;
                return;
            }

            windowRect = GUILayout.Window(110, windowRect, DrawWindow, "📹 Camera Monitor");
        }

        private void DrawWindow(int id)
        {
            if (GUILayout.Button("Hide", GUILayout.Width(50)))
            { showPanel = false; }

            var vcm = VirtualCameraManager.Instance;
            if (vcm == null)
            {
                GUILayout.Label("Camera system not initialized");
                GUI.DragWindow();
                return;
            }

            var configs = vcm.GetCameraConfigs();
            if (configs == null || configs.Length == 0)
            {
                GUILayout.Label("No cameras configured");
                GUI.DragWindow();
                return;
            }

            // Stats bar
            GUILayout.Label($"Active: {vcm.ActiveCameraCount}/{configs.Length} cameras");

            scrollPos = GUILayout.BeginScrollView(scrollPos);

            if (selectedCameraIdx < 0)
            {
                DrawCameraGrid(configs, vcm);
            }
            else
            {
                DrawSingleCamera(configs, vcm);
            }

            GUILayout.EndScrollView();

            GUILayout.Space(5);
            DrawDemoSection();

            GUI.DragWindow();
        }

        private void DrawCameraGrid(VirtualCameraConfig[] configs, VirtualCameraManager vcm)
        {
            // 2x2 grid
            int cols = 2;
            float thumbW = 210, thumbH = 158;

            for (int i = 0; i < configs.Length; i++)
            {
                if (i % cols == 0) GUILayout.BeginHorizontal();

                GUILayout.BeginVertical(GUI.skin.box, GUILayout.Width(thumbW));

                var streamer = vcm.GetStreamer(configs[i].cameraId);

                // Draw camera feed
                Rect texRect = GUILayoutUtility.GetRect(thumbW - 10, thumbH);
                if (streamer != null && streamer.IsStreaming)
                {
                    var cam = streamer.GetComponent<UnityEngine.Camera>();
                    if (cam != null && cam.targetTexture != null)
                    {
                        GUI.DrawTexture(texRect, cam.targetTexture, ScaleMode.ScaleToFit);
                    }
                    else
                    {
                        GUI.Box(texRect, "No Feed");
                    }
                }
                else
                {
                    GUI.Box(texRect, "Offline");
                }

                // Info line
                string status = streamer != null && streamer.IsStreaming ? "🟢" : "🔴";
                float fps = streamer != null ? streamer.CurrentFps : 0;
                int frames = streamer != null ? streamer.FramesSent : 0;
                GUILayout.Label($"{status} {configs[i].displayName}");
                GUILayout.Label($"FPS: {fps:F1} | Frames: {frames}");

                if (GUILayout.Button("🔍 Fullscreen"))
                    selectedCameraIdx = i;

                GUILayout.EndVertical();

                if (i % cols == 1 || i == configs.Length - 1) GUILayout.EndHorizontal();
            }
        }

        private void DrawSingleCamera(VirtualCameraConfig[] configs, VirtualCameraManager vcm)
        {
            if (selectedCameraIdx >= configs.Length)
            {
                selectedCameraIdx = -1;
                return;
            }

            var cfg = configs[selectedCameraIdx];
            var streamer = vcm.GetStreamer(cfg.cameraId);

            if (GUILayout.Button("← Back to Grid"))
            {
                selectedCameraIdx = -1;
                return;
            }

            GUILayout.Label($"📷 {cfg.displayName}", GUI.skin.box);

            float viewW = 440, viewH = 330;
            Rect texRect = GUILayoutUtility.GetRect(viewW, viewH);
            if (streamer != null && streamer.IsStreaming)
            {
                var cam = streamer.GetComponent<UnityEngine.Camera>();
                if (cam != null && cam.targetTexture != null)
                    GUI.DrawTexture(texRect, cam.targetTexture, ScaleMode.ScaleToFit);
                else
                    GUI.Box(texRect, "No Feed");
            }
            else
            {
                GUI.Box(texRect, "Camera Offline");
            }

            string statusText = streamer != null && streamer.IsStreaming ? "🟢 Streaming" : "🔴 Offline";
            float currentFps = streamer != null ? streamer.CurrentFps : 0;
            int totalFrames = streamer != null ? streamer.FramesSent : 0;
            GUILayout.Label($"Status: {statusText} | FPS: {currentFps:F1} | Total Frames: {totalFrames}");
            GUILayout.Label($"Resolution: {cfg.renderWidth}x{cfg.renderHeight} | FOV: {cfg.fieldOfView}°");
        }

        private void DrawDemoSection()
        {
            GUILayout.Label("── Demo ──");

            if (!string.IsNullOrEmpty(demoStatus))
            {
                var prev = GUI.contentColor;
                GUI.contentColor = Color.yellow;
                GUILayout.Label(demoStatus);
                GUI.contentColor = prev;
            }

            GUI.enabled = !isDemoRunning && ParkingManager.Instance != null;
            if (GUILayout.Button("🚗 Run Full Demo"))
            {
                StartCoroutine(RunFullDemo());
            }
            GUI.enabled = true;
        }

        private IEnumerator RunFullDemo()
        {
            isDemoRunning = true;
            demoStatus = "Demo: Creating booking...";
            yield return new WaitForSeconds(1f);

            // Step 1: Spawn vehicle with booking
            demoStatus = "Demo: Spawning vehicle DEMO-001 → slot A-01...";
            string plate = "DEMO-001";
            string bookingId = System.Guid.NewGuid().ToString();
            string qrData = $"{{\"booking_id\":\"{bookingId}\",\"user_id\":\"demo-user\"}}";

            ParkingManager.Instance.SpawnVehicle(plate, bookingId, qrData, "A-01", "Car");
            yield return new WaitForSeconds(1f);

            // Step 2: Vehicle approaches gate
            demoStatus = "Demo: Vehicle approaching entry gate...";
            yield return new WaitForSeconds(4f);

            // Step 3: Gate processing
            demoStatus = "Demo: Gate camera scanning plate...";
            yield return new WaitForSeconds(3f);

            // Step 4: Vehicle entering
            demoStatus = "Demo: Gate opened — vehicle entering lot...";
            yield return new WaitForSeconds(5f);

            // Step 5: Vehicle navigating
            demoStatus = "Demo: Vehicle navigating to slot A-01...";
            yield return new WaitForSeconds(5f);

            // Step 6: Parked
            demoStatus = "Demo: Vehicle PARKED at A-01 ✅ Camera detecting occupancy...";
            yield return new WaitForSeconds(5f);

            // Step 7: Occupancy detected
            demoStatus = "Demo: Slot A-01 marked OCCUPIED. Streaming to web...";
            yield return new WaitForSeconds(10f);

            // Step 8: Departing
            demoStatus = "Demo: Vehicle departing...";
            yield return new WaitForSeconds(8f);

            // Step 9: Exit
            demoStatus = "Demo: Vehicle at exit gate → checking out...";
            yield return new WaitForSeconds(5f);

            demoStatus = "Demo: ✅ COMPLETE — Full flow demonstrated!";
            yield return new WaitForSeconds(3f);

            demoStatus = "";
            isDemoRunning = false;
        }
    }
}
