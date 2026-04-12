using UnityEngine;

namespace ParkingSim.Camera
{
    /// <summary>
    /// Configuration for a virtual camera instance.
    /// Populated by VirtualCameraManager during scene setup.
    /// </summary>
    [System.Serializable]
    public class VirtualCameraConfig
    {
        public string cameraId;
        public string displayName;
        public Vector3 position;
        public Vector3 rotation;
        public float fieldOfView = 90f;
        public int renderWidth = 640;
        public int renderHeight = 480;
        public int jpegQuality = 75;
        public float captureFps = 5f;
        public string[] monitoredSlotCodes;
    }

    /// <summary>
    /// Captures RenderTexture frames as JPEG and HTTP POSTs them to AI service.
    /// Attach to a GameObject with a Camera component.
    /// </summary>
    /// <remarks>
    /// Implementation should:
    /// - Create RenderTexture at configured resolution
    /// - Run capture coroutine at configured fps
    /// - Use EncodeToJPG(quality) NOT EncodeToPNG (3-5x smaller)
    /// - POST to: {aiServiceUrl}/ai/cameras/virtual/frame
    /// - Headers: X-Camera-ID, X-Gateway-Secret, Content-Type: image/jpeg
    /// - Stop posting when Application.isFocused == false
    /// - Pattern reference: GateCameraSimulator.cs RenderTexture capture
    /// </remarks>
    public interface IVirtualCameraStreamer
    {
        string CameraId { get; }
        bool IsStreaming { get; }
        float CurrentFps { get; }
        int FramesSent { get; }

        void StartStreaming();
        void StopStreaming();
        void UpdateConfig(VirtualCameraConfig config);
    }

    /// <summary>
    /// Manages lifecycle of all virtual cameras in the scene.
    /// Spawns camera GameObjects, attaches streamers, handles registration.
    /// </summary>
    /// <remarks>
    /// Implementation should:
    /// - Read camera configs (hardcoded or from API)
    /// - Spawn camera GameObjects with visible mesh (dark box + lens)
    /// - Position cameras per VirtualCameraConfig
    /// - Attach Camera + VirtualCameraStreamer components
    /// - Add orange border markings to monitored slots
    /// - Register cameras with backend on startup
    /// - Handle camera on/off toggling
    /// </remarks>
    public interface IVirtualCameraManager
    {
        int ActiveCameraCount { get; }
        VirtualCameraConfig[] GetCameraConfigs();
        void InitializeCameras();
        void ShutdownCameras();
    }

    /// <summary>
    /// Detects vehicle presence in parking slots using physics overlap.
    /// Reports state changes via realtime broadcast API.
    /// </summary>
    /// <remarks>
    /// Implementation should:
    /// - Run Physics.OverlapBox at each ParkingSlot position every N seconds
    /// - Detect VehicleController colliders in Parked state
    /// - Track current detected state per slot
    /// - On state change: POST to /api/broadcast/slot-status/ (realtime service)
    /// - Include detection metadata: plate, bookingId, cameraId
    /// - Use half-extents from slot type (Car: 1.25x1x2.5, Garage: 1.5x1.25x3, Moto: 0.5x0.75x1)
    /// </remarks>
    public interface ISlotOccupancyDetector
    {
        float DetectionInterval { get; set; }
        int TotalSlotsMonitored { get; }
        int OccupiedSlotsDetected { get; }

        void StartDetection();
        void StopDetection();
    }
}
