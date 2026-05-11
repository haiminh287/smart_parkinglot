using UnityEngine;

namespace ParkingSim.API
{
    [CreateAssetMenu(fileName = "ApiConfig", menuName = "ParkingSim/API Config")]
    public class ApiConfig : ScriptableObject
    {
        [Header("Gateway (Session Auth)")]
        public string gatewayBaseUrl = "http://localhost:8000";

        [Header("Direct Services (bypass gateway)")]
        public string aiServiceUrl = "http://localhost:8009";
        public string realtimeWsUrl = "ws://localhost:8006/ws/parking";

        [Header("Internal Auth")]
        public string gatewaySecret = "gateway-internal-secret-key";

        [Header("ESP32 Device Auth")]
        public string esp32DeviceToken = "";

        [Header("Test Credentials")]
        public string testEmail = "test@example.com";
        public string testPassword = "password";

        [Header("Polling Intervals")]
        public float lightPollInterval = 2f;
        public float deltaPollInterval = 5f;
        public float heartbeatInterval = 30f;

        [Header("Target")]
        public string targetParkingLotId = "";

        [Header("Behavior")]
        public bool useMockData = false;
        public int maxRetries = 3;
        public float maxBackoffSeconds = 30f;

        [Header("Virtual Camera")]
        public float cameraFps = 5f;
        public int cameraResWidth = 640;
        public int cameraResHeight = 480;
        public int cameraJpegQuality = 75;
    }
}
