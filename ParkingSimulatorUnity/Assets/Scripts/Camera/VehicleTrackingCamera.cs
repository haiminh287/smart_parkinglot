using System.Collections;
using UnityEngine;
using ParkingSim.Vehicle;

namespace ParkingSim.Camera
{
    public class VehicleTrackingCamera : MonoBehaviour
    {
        public static VehicleTrackingCamera Instance { get; private set; }

        [SerializeField] private Vector3 followOffset = new Vector3(0f, 8f, -15f);
        [SerializeField] private float smoothTime = 0.3f;
        [SerializeField] private float lookAheadDistance = 5f;
        [SerializeField] private float autoReturnDelay = 5f;

        private VehicleController target;
        private UnityEngine.Camera cam;
        private Vector3 velocity = Vector3.zero;
        private bool isTracking;
        private Vector3 overviewPosition;
        private Quaternion overviewRotation;
        private float overviewFov;
        private Coroutine autoReturnCoroutine;
        private Coroutine fovCoroutine;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(this);
                return;
            }
            Instance = this;

            cam = GetComponent<UnityEngine.Camera>();
            if (cam == null)
                cam = UnityEngine.Camera.main;
        }

        /// <summary>
        /// Start tracking a specific vehicle. Saves current camera state for return.
        /// </summary>
        public void TrackVehicle(VehicleController vehicle)
        {
            if (vehicle == null) return;

            // Save overview state
            overviewPosition = transform.position;
            overviewRotation = transform.rotation;
            if (cam != null) overviewFov = cam.fieldOfView;

            target = vehicle;
            isTracking = true;

            if (autoReturnCoroutine != null)
            {
                StopCoroutine(autoReturnCoroutine);
                autoReturnCoroutine = null;
            }

            Debug.Log($"[VehicleTrackingCamera] Tracking: {vehicle.plateNumber}");
        }

        /// <summary>
        /// Stop tracking and restore camera to overview position.
        /// </summary>
        public void StopTracking()
        {
            if (!isTracking) return;

            isTracking = false;
            target = null;

            transform.position = overviewPosition;
            transform.rotation = overviewRotation;
            if (cam != null) cam.fieldOfView = overviewFov;

            if (autoReturnCoroutine != null)
            {
                StopCoroutine(autoReturnCoroutine);
                autoReturnCoroutine = null;
            }

            if (fovCoroutine != null)
            {
                StopCoroutine(fovCoroutine);
                fovCoroutine = null;
            }

            Debug.Log("[VehicleTrackingCamera] Stopped tracking, returned to overview.");
        }

        private void LateUpdate()
        {
            if (!isTracking || target == null) return;

            // Desired position in target's local offset space
            Vector3 desiredPos = target.transform.position
                + target.transform.right * followOffset.x
                + Vector3.up * followOffset.y
                + target.transform.forward * followOffset.z;

            transform.position = Vector3.SmoothDamp(transform.position, desiredPos, ref velocity, smoothTime);

            // Look ahead of vehicle
            Vector3 lookTarget = target.transform.position + target.transform.forward * lookAheadDistance;
            transform.LookAt(lookTarget);

            // Auto-return when vehicle parks
            if (target.state == VehicleController.VehicleState.Parked && autoReturnCoroutine == null)
            {
                autoReturnCoroutine = StartCoroutine(AutoReturnCoroutine());
            }
        }

        private IEnumerator AutoReturnCoroutine()
        {
            yield return new WaitForSeconds(autoReturnDelay);
            StopTracking();
            autoReturnCoroutine = null;
        }

        /// <summary>
        /// Zoom FOV from current to 40 over 1 second (gate zoom effect).
        /// </summary>
        public void ZoomToGate()
        {
            if (cam == null) return;
            if (fovCoroutine != null) StopCoroutine(fovCoroutine);
            fovCoroutine = StartCoroutine(FovZoomCoroutine(cam.fieldOfView, 40f, 1f));
        }

        private IEnumerator FovZoomCoroutine(float from, float to, float duration)
        {
            float elapsed = 0f;
            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float t = Mathf.Clamp01(elapsed / duration);
                if (cam != null) cam.fieldOfView = Mathf.Lerp(from, to, t);
                yield return null;
            }
            if (cam != null) cam.fieldOfView = to;
            fovCoroutine = null;
        }

        /// <summary>
        /// Camera shake effect.
        /// </summary>
        public void CameraShake(float duration = 0.3f, float magnitude = 0.1f)
        {
            StartCoroutine(ShakeCoroutine(duration, magnitude));
        }

        private IEnumerator ShakeCoroutine(float duration, float magnitude)
        {
            Vector3 originalPos = transform.localPosition;
            float elapsed = 0f;

            while (elapsed < duration)
            {
                Vector3 offset = Random.insideUnitSphere * magnitude;
                transform.localPosition = originalPos + offset;
                elapsed += Time.deltaTime;
                yield return null;
            }

            transform.localPosition = originalPos;
        }

        private void OnGUI()
        {
            if (!isTracking || target == null) return;

            float boxWidth = 260f;
            float boxHeight = 60f;
            float margin = 10f;
            Rect rect = new Rect(Screen.width - boxWidth - margin, margin, boxWidth, boxHeight);

            GUI.Box(rect, "");

            // Tracking label
            string label = $"\ud83c\udfa5 TRACKING: {target.plateNumber}";
            GUI.Label(new Rect(rect.x + 8, rect.y + 4, boxWidth - 16, 24), $"<b>{label}</b>", TrackingLabelStyle());

            // Vehicle state with color
            string stateText = target.state.ToString();
            Color stateColor = GetStateColor(target.state);
            string hex = ColorUtility.ToHtmlStringRGB(stateColor);
            GUI.Label(new Rect(rect.x + 8, rect.y + 28, boxWidth - 16, 24),
                $"State: <color=#{hex}><b>{stateText}</b></color>", RichLabelStyle());
        }

        private static GUIStyle TrackingLabelStyle()
        {
            var style = new GUIStyle(GUI.skin.label)
            {
                fontSize = 14,
                richText = true
            };
            style.normal.textColor = Color.white;
            return style;
        }

        private static GUIStyle RichLabelStyle()
        {
            var style = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                richText = true
            };
            style.normal.textColor = Color.white;
            return style;
        }

        private static Color GetStateColor(VehicleController.VehicleState state)
        {
            switch (state)
            {
                case VehicleController.VehicleState.Idle: return Color.gray;
                case VehicleController.VehicleState.ApproachingGate: return Color.yellow;
                case VehicleController.VehicleState.WaitingAtGate: return new Color(1f, 0.5f, 0f);
                case VehicleController.VehicleState.Entering: return Color.cyan;
                case VehicleController.VehicleState.Navigating: return Color.blue;
                case VehicleController.VehicleState.Parking: return new Color(0.5f, 0f, 1f);
                case VehicleController.VehicleState.Parked: return Color.green;
                case VehicleController.VehicleState.Departing: return Color.yellow;
                case VehicleController.VehicleState.WaitingAtExit: return new Color(1f, 0.5f, 0f);
                case VehicleController.VehicleState.Exiting: return Color.cyan;
                case VehicleController.VehicleState.Gone: return Color.gray;
                default: return Color.white;
            }
        }
    }
}
