using UnityEngine;

namespace ParkingSim.Camera
{
    public class ParkingCameraController : MonoBehaviour
    {
        public enum CameraMode { Overview, FloorB1, GateEntry, GateExit }

        [SerializeField] private float orbitSpeed = 5f;
        [SerializeField] private float zoomSpeed = 10f;
        [SerializeField] private float panSpeed = 0.5f;
        [SerializeField] private float minDistance = 5f;
        [SerializeField] private float maxDistance = 100f;
        [SerializeField] private float minVerticalAngle = 10f;
        [SerializeField] private float maxVerticalAngle = 80f;

        private Vector3 targetPosition = Vector3.zero;
        private float distance = 40f;
        private float horizontalAngle = 45f;
        private float verticalAngle = 45f;

        private Vector3 currentPosition;
        private Vector3 smoothVelocity;
        private bool isFocusing;
        private Vector3 focusTarget;
        private float focusSpeed = 5f;

        private CameraMode currentMode = CameraMode.Overview;

        private void Start()
        {
            currentPosition = CalculatePosition();
            transform.position = currentPosition;
            transform.LookAt(targetPosition);
        }

        private void LateUpdate()
        {
            if (isFocusing)
            {
                targetPosition = Vector3.Lerp(targetPosition, focusTarget,
                    Time.deltaTime * focusSpeed);
                if (Vector3.Distance(targetPosition, focusTarget) < 0.1f)
                    isFocusing = false;
            }

            if (!IsMouseOverGUI())
                ProcessMouseInput();

            ProcessKeyboardInput();

            Vector3 desiredPos = CalculatePosition();
            currentPosition = Vector3.SmoothDamp(currentPosition, desiredPos,
                ref smoothVelocity, 0.1f);
            transform.position = currentPosition;
            transform.LookAt(targetPosition);
        }

        private void ProcessMouseInput()
        {
            // Right-click + drag: orbit
            if (Input.GetMouseButton(1))
            {
                horizontalAngle += Input.GetAxis("Mouse X") * orbitSpeed;
                verticalAngle -= Input.GetAxis("Mouse Y") * orbitSpeed;
                verticalAngle = Mathf.Clamp(verticalAngle, minVerticalAngle, maxVerticalAngle);
            }

            // Middle-click + drag: pan
            if (Input.GetMouseButton(2))
            {
                Vector3 right = transform.right;
                Vector3 forward = Vector3.Cross(right, Vector3.up).normalized;
                targetPosition -= right * Input.GetAxis("Mouse X") * panSpeed;
                targetPosition -= forward * Input.GetAxis("Mouse Y") * panSpeed;
            }

            // Scroll wheel: zoom
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(scroll) > 0.01f)
            {
                distance -= scroll * zoomSpeed;
                distance = Mathf.Clamp(distance, minDistance, maxDistance);
            }
        }

        private void ProcessKeyboardInput()
        {
            // WASD: pan
            Vector3 right = transform.right;
            Vector3 forward = Vector3.Cross(right, Vector3.up).normalized;
            float panAmount = panSpeed * 2f * Time.deltaTime * distance * 0.1f;

            if (Input.GetKey(KeyCode.W)) targetPosition += forward * panAmount;
            if (Input.GetKey(KeyCode.S)) targetPosition -= forward * panAmount;
            if (Input.GetKey(KeyCode.A)) targetPosition -= right * panAmount;
            if (Input.GetKey(KeyCode.D)) targetPosition += right * panAmount;

            // QE: rotate
            float rotAmount = orbitSpeed * 10f * Time.deltaTime;
            if (Input.GetKey(KeyCode.Q)) horizontalAngle -= rotAmount;
            if (Input.GetKey(KeyCode.E)) horizontalAngle += rotAmount;

            // ZX: zoom
            float zoomAmount = zoomSpeed * Time.deltaTime;
            if (Input.GetKey(KeyCode.Z))
                distance = Mathf.Clamp(distance - zoomAmount, minDistance, maxDistance);
            if (Input.GetKey(KeyCode.X))
                distance = Mathf.Clamp(distance + zoomAmount, minDistance, maxDistance);

            // F: focus on selected (placeholder — caller should invoke FocusOn)
            if (Input.GetKeyDown(KeyCode.F))
                SetOverviewPosition();

            // Mode shortcuts
            if (Input.GetKeyDown(KeyCode.Alpha1)) SetMode(CameraMode.Overview);
            if (Input.GetKeyDown(KeyCode.Alpha2)) SetMode(CameraMode.FloorB1);
            if (Input.GetKeyDown(KeyCode.G)) SetMode(CameraMode.GateEntry);
            if (Input.GetKeyDown(KeyCode.R)) SetMode(CameraMode.Overview);
            if (Input.GetKeyDown(KeyCode.Tab)) CycleMode();
        }

        private Vector3 CalculatePosition()
        {
            float hRad = horizontalAngle * Mathf.Deg2Rad;
            float vRad = verticalAngle * Mathf.Deg2Rad;

            float x = distance * Mathf.Cos(vRad) * Mathf.Sin(hRad);
            float y = distance * Mathf.Sin(vRad);
            float z = distance * Mathf.Cos(vRad) * Mathf.Cos(hRad);

            return targetPosition + new Vector3(x, y, z);
        }

        public void FocusOn(Vector3 position)
        {
            focusTarget = position;
            isFocusing = true;
            distance = Mathf.Clamp(15f, minDistance, maxDistance);
        }

        public void SetOverviewPosition()
        {
            targetPosition = Vector3.zero;
            horizontalAngle = 45f;
            verticalAngle = 60f;
            distance = 60f;
            isFocusing = false;
            currentMode = CameraMode.Overview;
        }

        private void SetMode(CameraMode mode)
        {
            currentMode = mode;
            isFocusing = false;
            switch (mode)
            {
                case CameraMode.Overview:
                    targetPosition = Vector3.zero;
                    distance = 45f;
                    verticalAngle = 55f;
                    horizontalAngle = 30f;
                    break;
                case CameraMode.FloorB1:
                    targetPosition = new Vector3(targetPosition.x, 0f, targetPosition.z);
                    distance = 30f;
                    verticalAngle = 50f;
                    break;
                case CameraMode.GateEntry:
                    targetPosition = new Vector3(-35f, 0f, 0f);
                    distance = 20f;
                    verticalAngle = 15f;
                    horizontalAngle = 0f;
                    break;
                case CameraMode.GateExit:
                    targetPosition = new Vector3(35f, 0f, 0f);
                    distance = 20f;
                    verticalAngle = 15f;
                    horizontalAngle = 180f;
                    break;
            }
        }

        private void CycleMode()
        {
            int count = System.Enum.GetValues(typeof(CameraMode)).Length;
            currentMode = (CameraMode)(((int)currentMode + 1) % count);
            SetMode(currentMode);
        }

        private void OnGUI()
        {
            string[] labels = { "1:Overview", "2:B1", "G:Gate", "TAB:Cycle" };
            CameraMode[] modes = { CameraMode.Overview, CameraMode.FloorB1,
                                   CameraMode.GateEntry, CameraMode.GateExit };

            string hud = "";
            for (int i = 0; i < labels.Length; i++)
            {
                if (i > 0) hud += "  ";
                hud += (i < modes.Length && currentMode == modes[i])
                    ? $"<b>[{labels[i]}]</b>" : $"[{labels[i]}]";
            }

            var style = new GUIStyle(GUI.skin.label)
            {
                fontSize = 14,
                richText = true,
                normal = { textColor = Color.white }
            };

            float boxWidth = 450f;
            float boxHeight = 28f;
            GUI.backgroundColor = new Color(0f, 0f, 0f, 0.6f);
            GUI.Box(new Rect(10, Screen.height - boxHeight - 10, boxWidth, boxHeight), "");
            GUI.Label(new Rect(15, Screen.height - boxHeight - 8, boxWidth, boxHeight), hud, style);
        }

        private bool IsMouseOverGUI()
        {
            return GUIUtility.hotControl != 0;
        }
    }
}
