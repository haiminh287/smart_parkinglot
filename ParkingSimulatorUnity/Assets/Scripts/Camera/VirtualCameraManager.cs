using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using TMPro;
using ParkingSim.API;

namespace ParkingSim.Camera
{
    public class VirtualCameraManager : MonoBehaviour, IVirtualCameraManager
    {
        public static VirtualCameraManager Instance { get; private set; }

        [SerializeField] private ApiConfig config;

        private VirtualCameraConfig[] cameraConfigs;
        private readonly List<VirtualCameraStreamer> streamers = new List<VirtualCameraStreamer>();

        public int ActiveCameraCount => streamers.Count(s => s != null && s.IsStreaming);

        private void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;

            if (config == null)
                config = Resources.Load<ApiConfig>("ApiConfig");
        }

        public VirtualCameraConfig[] GetCameraConfigs()
        {
            if (cameraConfigs == null) cameraConfigs = BuildCameraConfigs();
            return cameraConfigs;
        }

        public void InitializeCameras()
        {
            if (config == null)
            {
                Debug.LogError("[VirtualCameraManager] ApiConfig not assigned!");
                return;
            }

            cameraConfigs = BuildCameraConfigs();

            foreach (var cfg in cameraConfigs)
            {
                SpawnCamera(cfg);
            }

            Debug.Log($"[VirtualCameraManager] Initialized {cameraConfigs.Length} cameras");
        }

        public void ShutdownCameras()
        {
            foreach (var streamer in streamers)
            {
                if (streamer == null) continue;
                streamer.StopStreaming();
                Destroy(streamer.gameObject);
            }
            streamers.Clear();

            Debug.Log("[VirtualCameraManager] All cameras shut down");
        }

        public VirtualCameraStreamer GetStreamer(string cameraId)
        {
            return streamers.FirstOrDefault(s => s != null && s.CameraId == cameraId);
        }

        private VirtualCameraConfig[] BuildCameraConfigs()
        {
            return new[]
            {
                new VirtualCameraConfig
                {
                    cameraId = "virtual-f1-overview",
                    displayName = "Floor 1 Overview",
                    // Góc nhìn perspective từ trên-trước (thay vì top-down thẳng
                    // đứng): tilt 32° + height 18 từ z=-38 → nhìn chéo 4 hàng slots,
                    // orange border thấy rõ từng ô, ít bóng đổ che khuất.
                    position = new Vector3(0, 18, -38),
                    rotation = new Vector3(32, 0, 0),
                    fieldOfView = 75f,
                    renderWidth = config.cameraResWidth,
                    renderHeight = config.cameraResHeight,
                    jpegQuality = config.cameraJpegQuality,
                    captureFps = config.cameraFps,
                    monitoredSlotCodes = new string[0]
                },
                // Entry gate overview (wide angle, shows whole gate area)
                new VirtualCameraConfig
                {
                    cameraId = "virtual-gate-in",
                    displayName = "Entry Gate",
                    position = new Vector3(36, 3.5f, -4),
                    rotation = new Vector3(20, 60, 0),
                    fieldOfView = 55f,
                    renderWidth = config.cameraResWidth,
                    renderHeight = config.cameraResHeight,
                    jpegQuality = config.cameraJpegQuality,
                    captureFps = config.cameraFps,
                    monitoredSlotCodes = new string[0]
                },
                // ANPR camera: behind stopping bay, angled down to frame rear plate
                // Vehicle stops at x≈38.5, facing -X. Rear plate at world x≈40.8, y≈0.48.
                // Camera at x=43.5 (2.7m behind plate), y=1.0 (above plate), tilted 5° down.
                // FOV 35° → view width ≈ 1.7m at 2.7m distance → plate (0.72m) fills ~42% of frame.
                new VirtualCameraConfig
                {
                    cameraId = "virtual-anpr-entry",
                    displayName = "ANPR Entry Plate",
                    position = new Vector3(43.5f, 1.0f, 0f),
                    rotation = new Vector3(8f, -90f, 0f),
                    fieldOfView = 35f,
                    renderWidth = config.cameraResWidth,
                    renderHeight = config.cameraResHeight,
                    jpegQuality = config.cameraJpegQuality,
                    captureFps = config.cameraFps,
                    monitoredSlotCodes = new string[0]
                },
                new VirtualCameraConfig
                {
                    cameraId = "virtual-gate-out",
                    displayName = "Exit Gate",
                    position = new Vector3(-36, 3.5f, -4),
                    rotation = new Vector3(20, 120, 0),
                    fieldOfView = 55f,
                    renderWidth = config.cameraResWidth,
                    renderHeight = config.cameraResHeight,
                    jpegQuality = config.cameraJpegQuality,
                    captureFps = config.cameraFps,
                    monitoredSlotCodes = new string[0]
                },
                // ANPR camera exit: vehicle exits facing +X, front plate at x≈-40.8
                new VirtualCameraConfig
                {
                    cameraId = "virtual-anpr-exit",
                    displayName = "ANPR Exit Plate",
                    position = new Vector3(-42f, 0.4f, 0f),
                    rotation = new Vector3(0f, 90f, 0f),
                    fieldOfView = 25f,
                    renderWidth = config.cameraResWidth,
                    renderHeight = config.cameraResHeight,
                    jpegQuality = config.cameraJpegQuality,
                    captureFps = config.cameraFps,
                    monitoredSlotCodes = new string[0]
                },
                // Garage row G-01..G-05 opens NORTH (aisle at Z≈-22); camera stands
                // at the aisle side looking south toward the open entrances so parked
                // cars' fronts face the camera.
                new VirtualCameraConfig
                {
                    cameraId = "virtual-zone-garage",
                    displayName = "Garage Zone Monitor",
                    // Garage row: X=12..27 (rộng 15m), Z≈-22..-28.
                    // Camera xa hơn (Z=-10) + cao hơn (Y=5) + FOV 75° để đủ 5 slots
                    // (trước đây FOV 55° + Z=-14 chỉ thấy 4 ô, G-01 ở X=13.5 bị clip).
                    position = new Vector3(19.5f, 5f, -10f),
                    rotation = new Vector3(22f, 180f, 0f),
                    fieldOfView = 75f,
                    renderWidth = config.cameraResWidth,
                    renderHeight = config.cameraResHeight,
                    jpegQuality = config.cameraJpegQuality,
                    captureFps = config.cameraFps,
                    monitoredSlotCodes = new string[0]
                },
                // Angled camera watching south car rows (V1-01..V1-18, V1-37..V1-54)
                new VirtualCameraConfig
                {
                    cameraId = "virtual-zone-south",
                    displayName = "South Zone Monitor",
                    position = new Vector3(0, 12, -20),
                    rotation = new Vector3(40, 0, 0),
                    fieldOfView = 65f,
                    renderWidth = config.cameraResWidth,
                    renderHeight = config.cameraResHeight,
                    jpegQuality = config.cameraJpegQuality,
                    captureFps = config.cameraFps,
                    monitoredSlotCodes = new string[0]
                },
                // Angled camera watching north car rows (V1-19..V1-36, V1-55..V1-72)
                new VirtualCameraConfig
                {
                    cameraId = "virtual-zone-north",
                    displayName = "North Zone Monitor",
                    position = new Vector3(0, 12, 20),
                    rotation = new Vector3(40, 180, 0),
                    fieldOfView = 65f,
                    renderWidth = config.cameraResWidth,
                    renderHeight = config.cameraResHeight,
                    jpegQuality = config.cameraJpegQuality,
                    captureFps = config.cameraFps,
                    monitoredSlotCodes = new string[0]
                }
            };
        }

        private const int CAMERA_MESH_LAYER = 31; // unused layer for camera housings

        private void SpawnCamera(VirtualCameraConfig cfg)
        {
            // Camera object — renders scene but excludes its own housing mesh
            var cameraObj = new GameObject($"VirtualCamera_{cfg.cameraId}");
            cameraObj.transform.SetParent(transform);
            cameraObj.transform.position = cfg.position;
            cameraObj.transform.eulerAngles = cfg.rotation;

            var cam = cameraObj.AddComponent<UnityEngine.Camera>();
            cam.cullingMask &= ~(1 << CAMERA_MESH_LAYER); // exclude housing mesh layer

            var streamer = cameraObj.AddComponent<VirtualCameraStreamer>();
            streamer.Initialize(cfg);

            // Visual model — sibling object on excluded layer so camera can't see it
            var modelObj = new GameObject($"CameraModel_{cfg.cameraId}");
            modelObj.transform.SetParent(transform);
            bool isOverview = cfg.cameraId.Contains("overview");
            if (isOverview)
            {
                modelObj.transform.position = cfg.position;
                modelObj.transform.eulerAngles = cfg.rotation;
            }
            else
            {
                // Place model BEHIND camera: offset backward along camera's forward direction
                var camRotation = Quaternion.Euler(cfg.rotation);
                modelObj.transform.position = cfg.position - camRotation * Vector3.forward * 1.5f;
                modelObj.transform.eulerAngles = cfg.rotation;
            }

            BuildCameraMesh(modelObj, cfg);
            SetLayerRecursive(modelObj, CAMERA_MESH_LAYER);

            streamers.Add(streamer);
        }

        private static void SetLayerRecursive(GameObject obj, int layer)
        {
            obj.layer = layer;
            foreach (Transform child in obj.transform)
                SetLayerRecursive(child.gameObject, layer);
        }

        private void BuildCameraMesh(GameObject cameraObj, VirtualCameraConfig cfg)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            bool isOverview = cfg.cameraId.Contains("overview");

            if (isOverview)
            {
                BuildOverviewCameraMesh(cameraObj, cfg, shader);
            }
            else
            {
                BuildGateCameraMesh(cameraObj, cfg, shader);
            }
        }

        private void BuildGateCameraMesh(GameObject cameraObj, VirtualCameraConfig cfg, Shader shader)
        {
            // Body — dark gray housing (large, visible)
            var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
            body.name = "CameraBody";
            body.transform.SetParent(cameraObj.transform, false);
            body.transform.localPosition = Vector3.zero;
            body.transform.localScale = new Vector3(1.2f, 0.8f, 1.5f);
            body.GetComponent<Renderer>().sharedMaterial = MakeMat(shader, new Color(0.15f, 0.15f, 0.18f));

            // Lens — black cylinder
            var lens = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            lens.name = "CameraLens";
            lens.transform.SetParent(cameraObj.transform, false);
            lens.transform.localPosition = new Vector3(0, 0, 0.85f);
            lens.transform.localRotation = Quaternion.Euler(90, 0, 0);
            lens.transform.localScale = new Vector3(0.5f, 0.15f, 0.5f);
            lens.GetComponent<Renderer>().sharedMaterial = MakeMat(shader, new Color(0.03f, 0.03f, 0.08f));

            // Bracket — tall mounting pole
            var bracket = GameObject.CreatePrimitive(PrimitiveType.Cube);
            bracket.name = "CameraBracket";
            bracket.transform.SetParent(cameraObj.transform, false);
            bracket.transform.localPosition = new Vector3(0, 1.5f, 0);
            bracket.transform.localScale = new Vector3(0.15f, 2.5f, 0.15f);
            bracket.GetComponent<Renderer>().sharedMaterial = MakeMat(shader, new Color(0.5f, 0.5f, 0.5f));

            // LED — red emissive
            var led = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            led.name = "CameraLED";
            led.transform.SetParent(cameraObj.transform, false);
            led.transform.localPosition = new Vector3(0, 0.45f, 0.6f);
            led.transform.localScale = new Vector3(0.18f, 0.18f, 0.18f);
            var ledMat = MakeMat(shader, Color.red);
            ledMat.EnableKeyword("_EMISSION");
            ledMat.SetColor("_EmissionColor", Color.red * 3f);
            led.GetComponent<Renderer>().sharedMaterial = ledMat;

            // Label
            var labelObj = new GameObject("CameraLabel");
            labelObj.transform.SetParent(cameraObj.transform, false);
            labelObj.transform.localPosition = new Vector3(0, -0.8f, 0);
            labelObj.transform.localRotation = Quaternion.Euler(0, 0, 0);
            var tmp = labelObj.AddComponent<TextMeshPro>();
            tmp.text = $"[CAM] {cfg.displayName}";
            tmp.fontSize = 4;
            tmp.color = Color.white;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.rectTransform.sizeDelta = new Vector2(5f, 1.5f);
        }

        private void BuildOverviewCameraMesh(GameObject cameraObj, VirtualCameraConfig cfg, Shader shader)
        {
            // Small camera body at ceiling
            var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
            body.name = "CameraBody";
            body.transform.SetParent(cameraObj.transform, false);
            body.transform.localPosition = Vector3.zero;
            body.transform.localScale = new Vector3(0.8f, 0.6f, 0.8f);
            body.GetComponent<Renderer>().sharedMaterial = MakeMat(shader, new Color(0.15f, 0.15f, 0.18f));

            // LED
            var led = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            led.name = "CameraLED";
            led.transform.SetParent(cameraObj.transform, false);
            led.transform.localPosition = new Vector3(0, 0.4f, 0);
            led.transform.localScale = new Vector3(0.2f, 0.2f, 0.2f);
            var ledMat = MakeMat(shader, Color.red);
            ledMat.EnableKeyword("_EMISSION");
            ledMat.SetColor("_EmissionColor", Color.red * 3f);
            led.GetComponent<Renderer>().sharedMaterial = ledMat;

            // Floor-level indicator frame — bright orange border showing camera coverage zone
            float floorY = cfg.cameraId.Contains("f1") ? 0.15f : 3.65f;
            float frameW = 66f;
            float frameD = 56f;
            float barThickness = 0.3f;
            float barHeight = 0.2f;

            Color orange = new Color(1f, 0.5f, 0f);
            var orangeMat = MakeMat(shader, orange);
            orangeMat.EnableKeyword("_EMISSION");
            orangeMat.SetColor("_EmissionColor", orange * 1.5f);

            // Create frame as a root-level object (not parented to rotated camera)
            var frameObj = new GameObject($"CameraFrame_{cfg.cameraId}");
            frameObj.transform.SetParent(transform); // parent to VirtualCameraManager, not the camera
            frameObj.transform.position = new Vector3(cfg.position.x, floorY, cfg.position.z);

            // North bar
            var nBar = GameObject.CreatePrimitive(PrimitiveType.Cube);
            nBar.name = "Frame_N";
            nBar.transform.SetParent(frameObj.transform);
            nBar.transform.localPosition = new Vector3(0, 0, frameD / 2f);
            nBar.transform.localScale = new Vector3(frameW, barHeight, barThickness);
            nBar.GetComponent<Renderer>().sharedMaterial = orangeMat;
            // South
            var sBar = GameObject.CreatePrimitive(PrimitiveType.Cube);
            sBar.name = "Frame_S";
            sBar.transform.SetParent(frameObj.transform);
            sBar.transform.localPosition = new Vector3(0, 0, -frameD / 2f);
            sBar.transform.localScale = new Vector3(frameW, barHeight, barThickness);
            sBar.GetComponent<Renderer>().sharedMaterial = orangeMat;
            // East
            var eBar = GameObject.CreatePrimitive(PrimitiveType.Cube);
            eBar.name = "Frame_E";
            eBar.transform.SetParent(frameObj.transform);
            eBar.transform.localPosition = new Vector3(frameW / 2f, 0, 0);
            eBar.transform.localScale = new Vector3(barThickness, barHeight, frameD);
            eBar.GetComponent<Renderer>().sharedMaterial = orangeMat;
            // West
            var wBar = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wBar.name = "Frame_W";
            wBar.transform.SetParent(frameObj.transform);
            wBar.transform.localPosition = new Vector3(-frameW / 2f, 0, 0);
            wBar.transform.localScale = new Vector3(barThickness, barHeight, frameD);
            wBar.GetComponent<Renderer>().sharedMaterial = orangeMat;

            // Corner marker cubes (4 corners, bright orange)
            float[][] corners = {
                new[]{-frameW/2f, -frameD/2f}, new[]{frameW/2f, -frameD/2f},
                new[]{-frameW/2f, frameD/2f}, new[]{frameW/2f, frameD/2f}
            };
            foreach (var c in corners)
            {
                var corner = GameObject.CreatePrimitive(PrimitiveType.Cube);
                corner.name = "CornerMarker";
                corner.transform.SetParent(frameObj.transform);
                corner.transform.localPosition = new Vector3(c[0], 0.25f, c[1]);
                corner.transform.localScale = new Vector3(1.5f, 0.8f, 1.5f);
                corner.GetComponent<Renderer>().sharedMaterial = orangeMat;
            }

            // Floor label — large visible text
            var labelObj = new GameObject("CameraFloorLabel");
            labelObj.transform.SetParent(frameObj.transform);
            labelObj.transform.localPosition = new Vector3(0, 0.4f, frameD / 2f - 2f);
            labelObj.transform.localRotation = Quaternion.Euler(90, 0, 0);
            var tmp = labelObj.AddComponent<TextMeshPro>();
            tmp.text = $"[CAM] {cfg.displayName}";
            tmp.fontSize = 8;
            tmp.color = orange;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.rectTransform.sizeDelta = new Vector2(20f, 3f);
        }

        private static Material MakeMat(Shader shader, Color color)
        {
            var mat = new Material(shader) { color = color };
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
            return mat;
        }
    }
}
