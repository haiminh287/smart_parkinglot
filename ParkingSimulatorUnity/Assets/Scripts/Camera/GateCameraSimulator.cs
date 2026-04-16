using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.IoT;
using ParkingSim.Vehicle;

namespace ParkingSim.Camera
{
    public class GateCameraSimulator : MonoBehaviour
    {
        [SerializeField] private ApiService apiService;
        [SerializeField] private ESP32Simulator esp32Simulator;
        [SerializeField] private UnityEngine.Camera gateCamera;
        [SerializeField] private Transform capturePoint;
        [SerializeField] private float captureRadius = 3f;
        [SerializeField] private AudioClip beepClip;

        private AudioSource audioSource;
        private readonly Queue<VehicleController> pendingDetections = new Queue<VehicleController>();
        private readonly HashSet<VehicleController> queuedVehicles = new HashSet<VehicleController>();
        private bool isCapturing;
        private string lastRecognizedPlate = "";
        private string lastCaptureStatus = "Idle";
        private float lastConfidence;

        private bool showWindow = true;
        private Rect windowRect = new Rect(Screen.width - 320, 220, 300, 200);

        private void Start()
        {
            if (apiService == null)
                apiService = ApiService.Instance ?? FindObjectOfType<ApiService>();
            audioSource = gameObject.AddComponent<AudioSource>();
            audioSource.playOnAwake = false;
        }

        private void Update()
        {
            if (capturePoint == null) return;

            // Scan for vehicles waiting at gate and enqueue
            var colliders = Physics.OverlapSphere(capturePoint.position, captureRadius);
            foreach (var col in colliders)
            {
                var vehicle = col.GetComponent<VehicleController>();
                if (vehicle != null &&
                    vehicle.state == VehicleController.VehicleState.WaitingAtGate &&
                    !queuedVehicles.Contains(vehicle))
                {
                    pendingDetections.Enqueue(vehicle);
                    queuedVehicles.Add(vehicle);
                }
            }

            // Process queue sequentially
            if (!isCapturing && pendingDetections.Count > 0)
            {
                var next = pendingDetections.Dequeue();
                queuedVehicles.Remove(next);
                if (next != null)
                {
                    isCapturing = true;
                    StartCoroutine(CaptureAndRecognize(next));
                }
            }
        }

        private void OnGUI()
        {
            if (!showWindow)
            {
                if (GUI.Button(new Rect(Screen.width - 160, 220, 150, 30), "Show Gate Cam"))
                    showWindow = true;
                return;
            }

            windowRect = GUILayout.Window(104, windowRect, DrawWindow, "\ud83d\udcf7 Gate Camera");
        }

        private static readonly string[] spinnerFrames = { "\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f" };

        private void DrawWindow(int id)
        {
            if (GUILayout.Button("Hide", GUILayout.Width(50)))
            { showWindow = false; }

            if (isCapturing)
            {
                int frame = (int)(Time.time * 10f) % spinnerFrames.Length;
                GUILayout.Label($"Status: {spinnerFrames[frame]} {lastCaptureStatus}");
            }
            else
            {
                GUILayout.Label($"Status: {lastCaptureStatus}");
            }

            var prevColor = GUI.contentColor;
            if (!string.IsNullOrEmpty(lastRecognizedPlate))
            {
                if (lastConfidence > 0.85f)
                    GUI.contentColor = Color.green;
                else if (lastConfidence > 0.5f)
                    GUI.contentColor = Color.yellow;
                else
                    GUI.contentColor = Color.red;

                GUILayout.Label($"Plate: {lastRecognizedPlate}");
                GUI.contentColor = prevColor;
                GUILayout.Label($"Confidence: {lastConfidence:P0}");
            }
            else
            {
                GUILayout.Label("Plate: —");
            }

            GUILayout.Label($"Queue: {pendingDetections.Count} vehicle(s)");

            GUI.enabled = !isCapturing;
            if (GUILayout.Button("\ud83d\udcf8 Manual Capture"))
            {
                StartCoroutine(ManualCapture());
            }
            GUI.enabled = true;

            GUI.DragWindow();
        }

        private IEnumerator ManualCapture()
        {
            if (capturePoint == null) yield break;

            VehicleController nearest = null;
            float minDist = captureRadius * 2f;

            var colliders = Physics.OverlapSphere(capturePoint.position, captureRadius * 2f);
            foreach (var col in colliders)
            {
                var v = col.GetComponent<VehicleController>();
                if (v != null)
                {
                    float d = Vector3.Distance(capturePoint.position, v.transform.position);
                    if (d < minDist) { minDist = d; nearest = v; }
                }
            }

            if (nearest != null)
            {
                isCapturing = true;
                yield return StartCoroutine(CaptureAndRecognize(nearest));
            }
            else
            {
                lastCaptureStatus = "No vehicle nearby";
            }
        }

        // NOTE: VehicleController requires a Collider (+ Rigidbody with isKinematic)
        // on the vehicle prefab for Physics.OverlapSphere detection.
        private IEnumerator CaptureAndRecognize(VehicleController vehicle)
        {
            lastCaptureStatus = "Capturing...";
            Debug.Log($"[GateCamera] Vehicle detected at gate: {vehicle.plateNumber}");

            if (gateCamera != null)
            {
                // Render camera to texture and capture image bytes
                var rt = new RenderTexture(640, 480, 24);
                gateCamera.targetTexture = rt;
                gateCamera.Render();

                RenderTexture.active = rt;
                var tex = new Texture2D(640, 480, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, 640, 480), 0, 0);
                tex.Apply();
                byte[] imageBytes = tex.EncodeToPNG();

                gateCamera.targetTexture = null;
                RenderTexture.active = null;
                Destroy(rt);
                Destroy(tex);

                // Send to AI for OCR
                lastCaptureStatus = "Processing AI OCR...";
                bool done = false;
                ApiResponse<PlateScanResult> result = null;
                StartCoroutine(apiService.AIRecognizePlate(imageBytes, r =>
                {
                    result = r;
                    done = true;
                }));
                yield return new WaitUntil(() => done);

                if (result.IsSuccess && result.Data != null &&
                    !string.IsNullOrEmpty(result.Data.PlateText))
                {
                    lastRecognizedPlate = result.Data.PlateText;
                    lastConfidence = result.Data.Confidence;

                    // Retry once if low confidence
                    if (lastConfidence < 0.6f)
                    {
                        Debug.Log($"[GateCamera] Low confidence ({lastConfidence:P0}), retrying...");
                        lastCaptureStatus = "Retrying (low confidence)...";
                        done = false;
                        result = null;
                        StartCoroutine(apiService.AIRecognizePlate(imageBytes, r =>
                        {
                            result = r;
                            done = true;
                        }));
                        yield return new WaitUntil(() => done);

                        if (result.IsSuccess && result.Data != null &&
                            !string.IsNullOrEmpty(result.Data.PlateText))
                        {
                            lastRecognizedPlate = result.Data.PlateText;
                            lastConfidence = result.Data.Confidence;
                        }
                    }

                    Debug.Log($"[GateCamera] \u2705 AI OCR: {lastRecognizedPlate} " +
                              $"(confidence: {lastConfidence:P0})");
                    esp32Simulator.SetPlateFromCamera(lastRecognizedPlate);
                    lastCaptureStatus = "Complete \u2705";

                    if (beepClip != null && audioSource != null)
                        audioSource.PlayOneShot(beepClip);
                }
                else
                {
                    // Fallback: use vehicle's known plate (simulation mode)
                    lastRecognizedPlate = vehicle.plateNumber;
                    lastConfidence = 0f;
                    Debug.Log($"[GateCamera] \u26a0\ufe0f AI OCR failed, using known plate: " +
                              $"{lastRecognizedPlate}");
                    esp32Simulator.SetPlateFromCamera(lastRecognizedPlate);
                    lastCaptureStatus = "Fallback (known plate)";
                }
            }
            else
            {
                // No camera assigned — use known plate directly
                lastRecognizedPlate = vehicle.plateNumber;
                lastConfidence = 1f;
                Debug.Log($"[GateCamera] \ud83d\udcf7 Simulated capture: {lastRecognizedPlate}");
                esp32Simulator.SetPlateFromCamera(lastRecognizedPlate);
                lastCaptureStatus = "Simulated \u2705";

                if (beepClip != null && audioSource != null)
                    audioSource.PlayOneShot(beepClip);
            }

            yield return new WaitForSeconds(2f);
            isCapturing = false;
        }

        private void OnDrawGizmos()
        {
            if (capturePoint == null) return;
            Gizmos.color = Color.cyan;
            Gizmos.DrawWireSphere(capturePoint.position, captureRadius);
        }
    }
}
