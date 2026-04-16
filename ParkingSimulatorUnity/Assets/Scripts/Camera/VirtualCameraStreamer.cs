using System;
using System.Collections;
using UnityEngine;
using ParkingSim.API;

namespace ParkingSim.Camera
{
    [RequireComponent(typeof(UnityEngine.Camera))]
    public class VirtualCameraStreamer : MonoBehaviour, IVirtualCameraStreamer
    {
        private VirtualCameraConfig config;
        private UnityEngine.Camera cam;
        private RenderTexture renderTexture;
        private Texture2D readbackTexture;

        private bool isStreaming;
        private int framesSent;
        private float currentFps;
        private Coroutine captureCoroutine;

        private int consecutiveErrors;
        private const int MAX_CONSECUTIVE_ERRORS = 5;
        private const float BACKOFF_SECONDS = 30f;
        private bool backoffLogged;

        private int framesThisSecond;
        private float fpsTimer;

        public string CameraId => config?.cameraId ?? "";
        public bool IsStreaming => isStreaming;
        public float CurrentFps => currentFps;
        public int FramesSent => framesSent;

        public void Initialize(VirtualCameraConfig config)
        {
            this.config = config;
            cam = GetComponent<UnityEngine.Camera>();

            SetupCamera();
            CreateRenderTexture();

            Debug.Log($"[VirtualCamera] Initialized: {config.cameraId} " +
                      $"({config.renderWidth}x{config.renderHeight} @ {config.captureFps}fps)");

            StartStreaming();
        }

        private void SetupCamera()
        {
            cam.fieldOfView = config.fieldOfView;
            cam.farClipPlane = 200f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.1f, 0.1f, 0.1f);
            cam.cullingMask = ~0;
            cam.depth = -10;
            cam.enabled = true;
        }

        private void CreateRenderTexture()
        {
            DestroyRenderTexture();

            renderTexture = new RenderTexture(config.renderWidth, config.renderHeight, 24);
            renderTexture.Create();
            cam.targetTexture = renderTexture;

            readbackTexture = new Texture2D(
                config.renderWidth, config.renderHeight,
                TextureFormat.RGB24, false
            );
        }

        private void DestroyRenderTexture()
        {
            if (cam != null) cam.targetTexture = null;

            if (renderTexture != null)
            {
                renderTexture.Release();
                Destroy(renderTexture);
                renderTexture = null;
            }

            if (readbackTexture != null)
            {
                Destroy(readbackTexture);
                readbackTexture = null;
            }
        }

        public void StartStreaming()
        {
            if (isStreaming) return;

            isStreaming = true;
            consecutiveErrors = 0;
            backoffLogged = false;
            framesThisSecond = 0;
            fpsTimer = Time.time;
            captureCoroutine = StartCoroutine(CaptureLoop());

            Debug.Log($"[VirtualCamera] Streaming started: {CameraId}");
        }

        public void StopStreaming()
        {
            if (!isStreaming) return;

            isStreaming = false;
            if (captureCoroutine != null)
            {
                StopCoroutine(captureCoroutine);
                captureCoroutine = null;
            }

            Debug.Log($"[VirtualCamera] Streaming stopped: {CameraId} (sent {framesSent} frames)");
        }

        public void UpdateConfig(VirtualCameraConfig newConfig)
        {
            bool resolutionChanged = config.renderWidth != newConfig.renderWidth ||
                                     config.renderHeight != newConfig.renderHeight;

            bool wasStreaming = isStreaming;
            if (wasStreaming && resolutionChanged) StopStreaming();

            config = newConfig;
            SetupCamera();

            if (resolutionChanged) CreateRenderTexture();

            if (wasStreaming && !isStreaming) StartStreaming();

            Debug.Log($"[VirtualCamera] Config updated: {CameraId}");
        }

        private IEnumerator CaptureLoop()
        {
            float interval = 1f / config.captureFps;

            while (isStreaming)
            {
                if (!Application.isFocused)
                {
                    yield return new WaitForSeconds(interval);
                    continue;
                }

                if (ApiService.Instance == null)
                {
                    Debug.LogWarning($"[VirtualCamera] ApiService not ready, waiting...");
                    yield return new WaitForSeconds(1f);
                    continue;
                }

                // S2-IMP-12: Use AsyncGPUReadback to avoid blocking main thread
                // during ReadPixels (GPU→CPU stall of several ms per frame).
                byte[] jpegData = null;
                yield return StartCoroutine(CaptureFrameAsync(bytes => jpegData = bytes));

                if (jpegData != null)
                {
                    // Back off when endpoint is unreachable (MOCK mode or server down)
                    if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS)
                    {
                        yield return new WaitForSeconds(BACKOFF_SECONDS);
                        consecutiveErrors = 0; // retry after backoff
                        backoffLogged = false;
                        continue;
                    }

                    yield return StartCoroutine(SendFrame(jpegData));
                    TrackFps();
                }

                yield return new WaitForSeconds(interval);
            }
        }

        // Legacy synchronous snapshot — kept for external callers that cannot
        // yield. Uses ReadPixels which blocks main thread. Prefer the async
        // path in CaptureLoop for real-time streaming.
        public byte[] SnapshotJpeg() => CaptureFrame();

        private byte[] CaptureFrame()
        {
            if (renderTexture == null || readbackTexture == null) return null;

            RenderTexture prev = RenderTexture.active;
            RenderTexture.active = renderTexture;

            readbackTexture.ReadPixels(
                new Rect(0, 0, config.renderWidth, config.renderHeight), 0, 0
            );
            readbackTexture.Apply();

            RenderTexture.active = prev;

            return readbackTexture.EncodeToJPG(config.jpegQuality);
        }

        // S2-IMP-12: Async GPU readback variant used by CaptureLoop.
        // Uses UnityEngine.Rendering.AsyncGPUReadback.Request to move the
        // GPU→CPU copy off the main thread. Adds ~1 frame latency but frees
        // the main thread for physics/AI.
        private IEnumerator CaptureFrameAsync(System.Action<byte[]> onComplete)
        {
            if (renderTexture == null || readbackTexture == null)
            {
                onComplete(null);
                yield break;
            }

            var request = UnityEngine.Rendering.AsyncGPUReadback.Request(
                renderTexture,
                0,
                UnityEngine.Experimental.Rendering.GraphicsFormat.R8G8B8A8_UNorm
            );

            while (!request.done)
                yield return null;

            if (request.hasError)
            {
                onComplete(null);
                yield break;
            }

            var raw = request.GetData<byte>();
            readbackTexture.LoadRawTextureData(raw);
            readbackTexture.Apply();

            onComplete(readbackTexture.EncodeToJPG(config.jpegQuality));
        }

        private IEnumerator SendFrame(byte[] jpegData)
        {
            bool done = false;
            bool success = false;

            yield return ApiService.Instance.PostCameraFrame(CameraId, jpegData, ok =>
            {
                success = ok;
                done = true;
            });

            if (!done) yield return new WaitUntil(() => done);

            if (success)
            {
                consecutiveErrors = 0;
                backoffLogged = false;
                framesSent++;
            }
            else
            {
                consecutiveErrors++;
                if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS && !backoffLogged)
                {
                    backoffLogged = true;
                    Debug.LogWarning($"[VirtualCamera] {CameraId}: {consecutiveErrors} consecutive send failures — backing off {BACKOFF_SECONDS}s");
                }
            }
        }

        private void TrackFps()
        {
            framesThisSecond++;
            float elapsed = Time.time - fpsTimer;

            if (elapsed >= 1f)
            {
                currentFps = framesThisSecond / elapsed;
                framesThisSecond = 0;
                fpsTimer = Time.time;
            }
        }

        private void OnDestroy()
        {
            StopStreaming();
            DestroyRenderTexture();
        }
    }
}
