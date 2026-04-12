// SceneBootstrapper.cs — Unity Editor script
// Menu: ParkingSim > Setup Full Simulation Scene
// Tự động tạo toàn bộ GameObjects + wire references + cấu hình camera
// Sau khi chạy: nhấn ▶ Play để xem mô phỏng bãi đỗ xe Digital Twin

using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using ParkingSim.API;
using ParkingSim.Core;
using ParkingSim.Parking;
using ParkingSim.Vehicle;
using ParkingSim.IoT;
using ParkingSim.UI;
using ParkingSim.Navigation;
using ParkingSim.Camera;

namespace ParkingSim.Editor
{
    public static class SceneBootstrapper
    {
        // ─────────────────────────────────────────────
        // MENU ENTRIES
        // ─────────────────────────────────────────────

        [MenuItem("ParkingSim/\ud83c\udfd7\ufe0f Setup Full Simulation Scene", priority = 1)]
        public static void SetupScene()
        {
            if (!ConfirmSetup()) return;

            ClearExistingSimulation();

            var config = EnsureApiConfig();
            var simRoot = BuildSceneHierarchy(config);

            PositionCamera();
            if (!Application.isPlaying)
                EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            Selection.activeGameObject = simRoot;
            SceneView.FrameLastActiveSceneView();

            Debug.Log("[SceneBootstrapper] Scene setup complete. Press Play to run the simulation.");
            EditorUtility.DisplayDialog(
                "Setup Complete!",
                "Scene setup xong!\n\n" +
                "• useMockData = true (chạy offline không cần backend)\n" +
                "• Nhấn ▶ Play để xem mô phỏng\n\n" +
                "Controls (khi Play):\n" +
                "  Chuột phải + kéo: Xoay camera\n" +
                "  Scroll: Zoom in/out\n" +
                "  Giữa chuột + kéo: Pan\n" +
                "  F: Focus về trung tâm\n\n" +
                "Camera Monitor:\n" +
                "  📹 Show Cameras (top-right) → Xem feed 4 camera\n" +
                "  🚗 Run Full Demo → Chạy toàn bộ quy trình tự động\n\n" +
                "Tip: Kéo window ESP32 Simulator để test check-in/out",
                "▶ Play Now!"
            );

            // Auto-play
            EditorApplication.isPlaying = true;
        }

        [MenuItem("ParkingSim/\u25b6 Quick Play (Mock Mode)", priority = 2)]
        public static void QuickPlay()
        {
            var config = FindApiConfig();
            if (config != null)
            {
                config.useMockData = true;
                EditorUtility.SetDirty(config);
                AssetDatabase.SaveAssets();
                Debug.Log("[SceneBootstrapper] useMockData=true → starting Play.");
            }
            else
            {
                Debug.LogWarning("[SceneBootstrapper] ApiConfig not found. Run Setup Scene first.");
            }
            EditorApplication.isPlaying = true;
        }

        [MenuItem("ParkingSim/\u25b6 Live Play (Backend DB)", priority = 3)]
        public static void LivePlay()
        {
            var config = FindApiConfig();
            if (config != null)
            {
                config.useMockData = false;
                if (string.IsNullOrEmpty(config.targetParkingLotId))
                    config.targetParkingLotId = "3f54a675e64f4ea9a295ae8b068cc278";
                EditorUtility.SetDirty(config);
                AssetDatabase.SaveAssets();
                Debug.Log("[SceneBootstrapper] useMockData=false, backend mode → starting Play.");
            }
            else
            {
                Debug.LogWarning("[SceneBootstrapper] ApiConfig not found. Run Setup Scene first.");
            }
            EditorApplication.isPlaying = true;
        }

        [MenuItem("ParkingSim/\u23f9 Stop", priority = 3)]
        public static void StopPlay()
        {
            EditorApplication.isPlaying = false;
        }

        [MenuItem("ParkingSim/\ud83d\uddd1\ufe0f Clear Simulation Objects", priority = 10)]
        public static void ClearScene()
        {
            if (EditorUtility.DisplayDialog("Clear Scene", "Remove all ParkingSimulation objects?", "Yes", "Cancel"))
                ClearExistingSimulation();
        }

        // ─────────────────────────────────────────────
        // BUILD HIERARCHY
        // ─────────────────────────────────────────────

        private static GameObject BuildSceneHierarchy(ApiConfig config)
        {
            // Root
            var root = new GameObject("ParkingSimulation");

            // ── Navigation ──────────────────────────────
            var waypointGraphGO = CreateChild(root, "WaypointGraph");
            var waypointGraph   = waypointGraphGO.AddComponent<WaypointGraph>();

            // ── Parking Lot Generator ───────────────────
            var generatorGO = CreateChild(root, "ParkingLotGenerator");
            var generator   = generatorGO.AddComponent<ParkingLotGenerator>();
            SetField(generator, "waypointGraph", waypointGraph);

            // ── Entry Barrier ───────────────────────────
            var entryBarrierGO  = CreateChild(root, "EntryBarrier");
            entryBarrierGO.transform.position = new Vector3(35f, 0f, 0f);
            var entryPost = BuildBarrierPost(entryBarrierGO, new Color(1f, 0.3f, 0.1f));   // red-orange
            var entryBarrier = entryBarrierGO.AddComponent<BarrierController>();
            SetField(entryBarrier, "barrierArm", entryPost.transform);
            var entryBarrierSO = new SerializedObject(entryBarrier);
            entryBarrierSO.FindProperty("isEntry").boolValue = true;
            entryBarrierSO.ApplyModifiedPropertiesWithoutUndo();

            // ── Exit Barrier ────────────────────────────
            var exitBarrierGO = CreateChild(root, "ExitBarrier");
            exitBarrierGO.transform.position = new Vector3(-35f, 0f, 0f);
            var exitPost = BuildBarrierPost(exitBarrierGO, new Color(0.1f, 0.8f, 0.25f));  // green
            var exitBarrier = exitBarrierGO.AddComponent<BarrierController>();
            SetField(exitBarrier, "barrierArm", exitPost.transform);
            var exitBarrierSO = new SerializedObject(exitBarrier);
            exitBarrierSO.FindProperty("isEntry").boolValue = false;
            exitBarrierSO.ApplyModifiedPropertiesWithoutUndo();

            // ── Gate markers (visual cubes) ──────────────
            BuildGateMarker(root, "GateIN_Marker",  new Vector3(35f, 0.1f, 0f), new Color(1f, 0.3f, 0f));
            BuildGateMarker(root, "GateOUT_Marker", new Vector3(-35f, 0.1f, 0f), new Color(0f, 0.8f, 0.2f));

            // ── Vehicle Spawn + Queue Points ─────────────
            var spawnGO = CreateChild(root, "VehicleSpawnPoint");
            spawnGO.transform.position = new Vector3(47f, 0.1f, 0f);
            spawnGO.transform.rotation = Quaternion.Euler(0, -90, 0);
            AddEmptyMarker(spawnGO, Color.cyan);

            var entryQueueStartGO = CreateChild(root, "EntryQueueStart");
            entryQueueStartGO.transform.position = new Vector3(42f, 0.1f, 0f);
            entryQueueStartGO.transform.rotation = Quaternion.Euler(0, -90, 0);

            var exitQueueStartGO = CreateChild(root, "ExitQueueStart");
            exitQueueStartGO.transform.position = new Vector3(-42f, 0.1f, 0f);
            exitQueueStartGO.transform.rotation = Quaternion.Euler(0, 90, 0);

            // ── VehicleQueue ─────────────────────────────
            var vehicleQueueGO = CreateChild(root, "VehicleQueue");
            var vehicleQueue = vehicleQueueGO.AddComponent<VehicleQueue>();
            SetField(vehicleQueue, "entryQueueStart", entryQueueStartGO.transform);
            SetField(vehicleQueue, "exitQueueStart",  exitQueueStartGO.transform);
            SetField(vehicleQueue, "config", config);

            // ── API Layer ────────────────────────────────
            var authManagerGO = CreateChild(root, "AuthManager");
            var authManager   = authManagerGO.AddComponent<AuthManager>();

            var apiServiceGO = CreateChild(root, "ApiService");
            var apiService   = apiServiceGO.AddComponent<ApiService>();
            SetField(apiService, "config",      config);
            SetField(apiService, "authManager", authManager);

            var sbsGO = CreateChild(root, "SharedBookingState");
            sbsGO.AddComponent<SharedBookingState>();

            // ── ParkingManager ───────────────────────────
            var pmGO = CreateChild(root, "ParkingManager");
            var parkingManager = pmGO.AddComponent<ParkingManager>();
            SetField(parkingManager, "config",          config);
            SetField(parkingManager, "apiService",      apiService);
            SetField(parkingManager, "authManager",     authManager);
            SetField(parkingManager, "generator",       generator);
            SetField(parkingManager, "waypointGraph",   waypointGraph);
            SetField(parkingManager, "entryBarrier",    entryBarrier);
            SetField(parkingManager, "exitBarrier",     exitBarrier);
            SetField(parkingManager, "vehicleQueue",    vehicleQueue);
            SetField(parkingManager, "vehicleSpawnPoint", spawnGO.transform);

            // Wire vehicle prefabs
            EnsureVehiclePrefabs(parkingManager);

            // ── Virtual Camera System ────────────────────
            var vcmGO = CreateChild(pmGO, "VirtualCameraManager");
            var vcm   = vcmGO.AddComponent<VirtualCameraManager>();
            SetField(vcm, "config", config);
            SetField(parkingManager, "virtualCameraManager", vcm);

            var sodGO = CreateChild(pmGO, "SlotOccupancyDetector");
            sodGO.AddComponent<SlotOccupancyDetector>();
            SetField(parkingManager, "slotOccupancyDetector", sodGO.GetComponent<SlotOccupancyDetector>());

            // ── FloorVisibilityManager ───────────────────
            var fvmGO      = CreateChild(root, "FloorVisibilityManager");
            var floorMgr   = fvmGO.AddComponent<FloorVisibilityManager>();
            SetField(floorMgr, "generator", generator);

            // ── ESP32 Simulator ──────────────────────────
            var esp32GO = CreateChild(root, "ESP32Simulator");
            var esp32   = esp32GO.AddComponent<ESP32Simulator>();
            SetField(esp32, "apiService", apiService);
            SetField(esp32, "config",     config);

            // ── Gate Camera Simulator ────────────────────
            var gateCamGO = CreateChild(root, "GateCameraSimulator");
            var gateCamSim = gateCamGO.AddComponent<GateCameraSimulator>();
            SetField(gateCamSim, "apiService", apiService);
            SetField(gateCamSim, "esp32Simulator", esp32);

            // ── Dashboard UI ─────────────────────────────
            var dashGO  = CreateChild(root, "DashboardUI");
            var dashUI  = dashGO.AddComponent<DashboardUI>();
            SetField(dashUI, "parkingManager", parkingManager);
            SetField(dashUI, "floorManager",   floorMgr);
            SetField(dashUI, "apiService",     apiService);
            SetField(dashUI, "authManager",    authManager);
            SetField(dashUI, "config",         config);

            // ── BookingTestPanel ─────────────────────────
            var bookingGO = CreateChild(root, "BookingTestPanel");
            var bookPanel = bookingGO.AddComponent<BookingTestPanel>();
            SetField(bookPanel, "apiService", apiService);
            SetField(bookPanel, "config",     config);
            SetField(bookPanel, "generator",  generator);

            // ── Camera Monitor UI ────────────────────────
            var camMonGO = CreateChild(root, "CameraMonitorUI");
            camMonGO.AddComponent<CameraMonitorUI>();

            Debug.Log($"[SceneBootstrapper] Created {root.transform.childCount} children under '{root.name}'");
            return root;
        }

        // ─────────────────────────────────────────────
        // CAMERA SETUP
        // ─────────────────────────────────────────────

        private static void PositionCamera()
        {
            var mainCam = UnityEngine.Camera.main;
            if (mainCam == null) return;

            // Replace flat overhead with nice orbit view
            mainCam.transform.position = new Vector3(0f, 52f, -30f);
            mainCam.transform.rotation = Quaternion.Euler(65f, 0f, 0f);
            mainCam.backgroundColor = new Color(0.12f, 0.15f, 0.25f);
            mainCam.clearFlags = UnityEngine.CameraClearFlags.SolidColor;
            mainCam.fieldOfView = 60f;

            // Add orbit controller if not already there
            if (mainCam.GetComponent<ParkingSim.Camera.ParkingCameraController>() == null)
                mainCam.gameObject.AddComponent<ParkingSim.Camera.ParkingCameraController>();

            // Add vehicle tracking camera
            if (mainCam.GetComponent<ParkingSim.Camera.VehicleTrackingCamera>() == null)
                mainCam.gameObject.AddComponent<ParkingSim.Camera.VehicleTrackingCamera>();

            // Ensure proper directional light for professional look
            EnsureDirectionalLight();

            Debug.Log("[SceneBootstrapper] Camera positioned for overview.");
        }

        // ─────────────────────────────────────────────
        // API CONFIG
        // ─────────────────────────────────────────────

        private static ApiConfig EnsureApiConfig()
        {
            var existing = FindApiConfig();
            if (existing != null)
            {
                existing.useMockData = true;
                EditorUtility.SetDirty(existing);
                AssetDatabase.SaveAssets();
                return existing;
            }

            if (!AssetDatabase.IsValidFolder("Assets/Resources"))
                AssetDatabase.CreateFolder("Assets", "Resources");

            var cfg = ScriptableObject.CreateInstance<ApiConfig>();
            cfg.useMockData       = true;
            cfg.gatewayBaseUrl    = "http://localhost:8000";
            cfg.aiServiceUrl      = "http://localhost:8009";
            cfg.realtimeWsUrl     = "ws://localhost:8006/ws/parking";
            cfg.testEmail         = "test@example.com";
            cfg.testPassword      = "password";
            cfg.lightPollInterval = 2f;
            cfg.deltaPollInterval = 5f;
            cfg.heartbeatInterval = 30f;

            AssetDatabase.CreateAsset(cfg, "Assets/Resources/ApiConfig.asset");
            AssetDatabase.SaveAssets();
            Debug.Log("[SceneBootstrapper] Created ApiConfig asset at Assets/Resources/ApiConfig.asset");
            return cfg;
        }

        private static ApiConfig FindApiConfig()
        {
            var guids = AssetDatabase.FindAssets("t:ApiConfig");
            if (guids.Length > 0)
                return AssetDatabase.LoadAssetAtPath<ApiConfig>(AssetDatabase.GUIDToAssetPath(guids[0]));
            return null;
        }

        // ─────────────────────────────────────────────
        // LIGHTING
        // ─────────────────────────────────────────────

        private static void EnsureDirectionalLight()
        {
            var existing = Object.FindObjectOfType<Light>();
            if (existing != null && existing.type == LightType.Directional)
            {
                // Upgrade existing light settings
                existing.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
                existing.color = new Color(1f, 0.96f, 0.88f);
                existing.intensity = 1.2f;
                existing.shadows = LightShadows.Soft;
                return;
            }

            var lightGo = new GameObject("Directional Light");
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            light.color = new Color(1f, 0.96f, 0.88f);
            light.intensity = 1.2f;
            light.shadows = LightShadows.Soft;
            Debug.Log("[SceneBootstrapper] Added directional light for better visuals.");
        }

        // ─────────────────────────────────────────────
        // VEHICLE PREFABS
        // ─────────────────────────────────────────────

        private static void EnsureVehiclePrefabs(ParkingManager pm)
        {
            PrefabBuilder.BuildPrefabs(showDialog: false);
            PrefabBuilder.WireIntoParkingManager();
        }

        // ─────────────────────────────────────────────
        // HELPER BUILDERS
        // ─────────────────────────────────────────────

        private static GameObject CreateChild(GameObject parent, string name)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent.transform);
            go.transform.localPosition = Vector3.zero;
            return go;
        }

        // Builds a barrier arm: base post + arm pivot + horizontal arm cube
        private static GameObject BuildBarrierPost(GameObject parent, Color armColor)
        {
            // Base post (visual)
            var post = GameObject.CreatePrimitive(PrimitiveType.Cube);
            post.name = "Post";
            post.transform.SetParent(parent.transform);
            post.transform.localPosition = new Vector3(0, 0.9f, 0);
            post.transform.localScale    = new Vector3(0.25f, 1.8f, 0.25f);
            ApplyColor(post, new Color(0.5f, 0.5f, 0.55f));
            Object.DestroyImmediate(post.GetComponent<BoxCollider>());

            // Arm pivot (this is what BarrierController rotates)
            var armPivot = new GameObject("BarrierArm");
            armPivot.transform.SetParent(parent.transform);
            armPivot.transform.localPosition = new Vector3(0, 1.8f, 0);

            // Horizontal arm
            var arm = GameObject.CreatePrimitive(PrimitiveType.Cube);
            arm.name = "ArmBar";
            arm.transform.SetParent(armPivot.transform);
            arm.transform.localPosition = new Vector3(2f, 0, 0);
            arm.transform.localScale    = new Vector3(4f, 0.12f, 0.12f);
            ApplyColor(arm, armColor);
            Object.DestroyImmediate(arm.GetComponent<BoxCollider>());

            // Striped pattern cube (visual accent)
            var accent = GameObject.CreatePrimitive(PrimitiveType.Cube);
            accent.name = "ArmAccent";
            accent.transform.SetParent(armPivot.transform);
            accent.transform.localPosition = new Vector3(3.5f, 0, 0);
            accent.transform.localScale    = new Vector3(0.5f, 0.14f, 0.14f);
            ApplyColor(accent, Color.white);
            Object.DestroyImmediate(accent.GetComponent<BoxCollider>());

            return armPivot;
        }

        private static void BuildGateMarker(GameObject root, string name, Vector3 pos, Color color)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(root.transform);
            go.transform.position   = pos;
            go.transform.localScale = new Vector3(6f, 0.08f, 0.5f);
            ApplyColor(go, color);
            Object.DestroyImmediate(go.GetComponent<BoxCollider>());
        }

        private static void AddEmptyMarker(GameObject go, Color color)
        {
            var sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sphere.name = "SpawnMarker";
            sphere.transform.SetParent(go.transform);
            sphere.transform.localPosition = Vector3.zero;
            sphere.transform.localScale    = new Vector3(0.5f, 0.5f, 0.5f);
            ApplyColor(sphere, color);
            Object.DestroyImmediate(sphere.GetComponent<SphereCollider>());
        }

        private static void ApplyColor(GameObject go, Color color)
        {
            var rend = go.GetComponent<Renderer>();
            if (rend == null) return;
            // Try URP Lit first, fallback to Standard
            var shader = Shader.Find("Universal Render Pipeline/Lit")
                      ?? Shader.Find("Standard");
            if (shader == null) return;
            var mat = new Material(shader) { color = color };
            rend.sharedMaterial = mat;
        }

        // Sets a [SerializeField] private OR public field via SerializedObject
        private static void SetField(Object target, string fieldName, Object value)
        {
            var so = new SerializedObject(target);
            var prop = so.FindProperty(fieldName);
            if (prop != null)
            {
                prop.objectReferenceValue = value;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            else
            {
                Debug.LogWarning($"[SceneBootstrapper] Field '{fieldName}' not found on {target.GetType().Name}");
            }
        }

        private static void SetField(Object target, string fieldName, bool value)
        {
            var so = new SerializedObject(target);
            var prop = so.FindProperty(fieldName);
            if (prop != null)
            {
                prop.boolValue = value;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
        }

        // ─────────────────────────────────────────────
        // CLEANUP
        // ─────────────────────────────────────────────

        private static void ClearExistingSimulation()
        {
            var existing = GameObject.Find("ParkingSimulation");
            if (existing != null)
            {
                Object.DestroyImmediate(existing);
                Debug.Log("[SceneBootstrapper] Cleared existing ParkingSimulation.");
            }
        }

        private static bool ConfirmSetup()
        {
            var existing = GameObject.Find("ParkingSimulation");
            if (existing != null)
                return EditorUtility.DisplayDialog(
                    "Re-Setup Scene",
                    "ParkingSimulation object already exists.\nRemove it and rebuild?",
                    "Rebuild", "Cancel");
            return true;
        }
    }
}
