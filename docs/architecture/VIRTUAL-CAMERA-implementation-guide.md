# Implementation Guide — Virtual Camera System

## Dependency Order (implement theo thứ tự này)

### Phase 1: Backend Frame Buffer

1. `backend-microservices/ai-service-fastapi/app/routers/camera.py` — Add frame_buffer + POST endpoint + modify stream/list
2. `backend-microservices/parking-service/infrastructure/models.py` — Add camera_type, floor FK
3. `backend-microservices/parking-service/infrastructure/migrations/` — Django migration
4. `backend-microservices/parking-service/infrastructure/serializers.py` — Add new fields
5. `backend-microservices/realtime-service-go/internal/handler/broadcast.go` — Add BroadcastCameraStatus
6. `backend-microservices/realtime-service-go/cmd/server/main.go` — Register route

### Phase 2: Unity Camera Capture

7. `Assets/Scripts/API/ApiConfig.cs` — Add AI service URL + camera config fields
8. `Assets/Scripts/API/ApiService.cs` — Add PostCameraFrame coroutine
9. `Assets/Scripts/API/DataModels.cs` — Add camera DTOs
10. `Assets/Scripts/Camera/VirtualCameraStreamer.cs` — Core streaming component
11. `Assets/Scripts/Camera/VirtualCameraManager.cs` — Camera spawning + lifecycle

### Phase 3: Slot Detection

12. `Assets/Scripts/Camera/SlotOccupancyDetector.cs` — Physics.OverlapBox detection
13. `Assets/Scripts/Core/ParkingManager.cs` — Wire up VirtualCameraManager + detector

### Phase 4: Integration

14. `backend-microservices/seed_virtual_cameras.py` — Seed 4 virtual cameras in DB
15. `spotlove-ai/src/types/parking.ts` — Add cameraType to Camera interface (optional)

---

## Interfaces to Implement

| File                     | Interface              | Key Methods                                      |
| ------------------------ | ---------------------- | ------------------------------------------------ |
| VirtualCameraStreamer.cs | IVirtualCameraStreamer | StartStreaming, StopStreaming, capture coroutine |
| VirtualCameraManager.cs  | IVirtualCameraManager  | InitializeCameras, ShutdownCameras, spawn logic  |
| SlotOccupancyDetector.cs | ISlotOccupancyDetector | StartDetection, StopDetection, OverlapBox scan   |

Interface definitions: `Assets/Scripts/Camera/IVirtualCamera.cs`

---

## Business Rules (implement exactly as specified)

1. **Frame capture**: EncodeToJPG(75) NOT EncodeToPNG — PNG is 3-5x larger
2. **Capture rate**: 5 fps per camera (200ms interval between captures)
3. **Resolution**: 640×480 per camera (matches existing gate camera)
4. **HTTP POST**: Body = raw JPEG bytes, headers = X-Camera-ID + X-Gateway-Secret + Content-Type: image/jpeg
5. **Stale detection**: AI service marks camera "stale" if no frame for 5s, "offline" if 30s
6. **Camera pause**: Stop streaming when `Application.isFocused == false`
7. **Orange markings**: Slots monitored by camera get orange border (Color: 1f, 0.5f, 0f)
8. **4 cameras total**: virtual-f1-overview, virtual-f2-overview, virtual-gate-in, virtual-gate-out
9. **Slot detection interval**: Every 2 seconds per slot
10. **Detection**: Only count vehicles in VehicleState.Parked — ignore moving vehicles

---

## Error Scenarios (phải handle đủ)

| Scenario                         | Error Type        | HTTP Status | Handling                                            |
| -------------------------------- | ----------------- | ----------- | --------------------------------------------------- |
| AI service unreachable           | Network error     | —           | Unity: log warning, skip frame, retry next interval |
| Invalid JPEG data                | ValidationError   | 400         | AI: reject, Unity: regenerate frame                 |
| Missing X-Camera-ID              | ValidationError   | 400         | AI: reject with error message                       |
| Invalid gateway secret           | UnauthorizedError | 401         | AI: reject                                          |
| Frame too large (>500KB)         | ValidationError   | 413         | AI: reject, Unity: lower quality                    |
| Camera buffer full (>20 cameras) | ConflictError     | 409         | AI: reject new camera registration                  |
| No active viewers                | —                 | —           | Unity: still posts frames (AI buffers latest only)  |
| WebSocket disconnect             | —                 | —           | Existing reconnect logic handles this               |

---

## Observability Requirements

- **Log**: Frame POST success/failure with camera_id, frame_size, latency
- **Log**: Camera stale/offline transitions
- **Metric**: `virtual_camera_frames_received_total{camera_id}` counter
- **Metric**: `virtual_camera_frame_size_bytes{camera_id}` histogram
- **Health**: Include virtual_cameras status in `/health` endpoint

---

## Pattern Reference

### RenderTexture Capture (from GateCameraSimulator.cs)

```csharp
var rt = new RenderTexture(640, 480, 24);
camera.targetTexture = rt;
camera.Render();
RenderTexture.active = rt;
var tex = new Texture2D(640, 480, TextureFormat.RGB24, false);
tex.ReadPixels(new Rect(0, 0, 640, 480), 0, 0);
tex.Apply();
byte[] jpeg = tex.EncodeToJPG(75);  // NOT EncodeToPNG!
// cleanup: camera.targetTexture = null; RenderTexture.active = null; Destroy(rt); Destroy(tex);
```

### MJPEG Serving (from camera.py)

```python
async def generate():
    while True:
        jpeg_bytes = frame_buffer.get(camera_id)
        if jpeg_bytes:
            yield b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
        await asyncio.sleep(1/fps)
return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")
```

### Broadcast API Call (from existing Unity ApiService pattern)

```csharp
// Use UnityWebRequest.Post with raw body
var request = new UnityWebRequest(url, "POST");
request.uploadHandler = new UploadHandlerRaw(jpegBytes);
request.SetRequestHeader("Content-Type", "image/jpeg");
request.SetRequestHeader("X-Camera-ID", cameraId);
request.SetRequestHeader("X-Gateway-Secret", gatewaySecret);
```

---

## Camera Position Quick-Reference

| Camera ID           | Position (x,y,z) | Rotation (x,y,z) | FOV | Coverage                |
| ------------------- | ---------------- | ---------------- | --- | ----------------------- |
| virtual-f1-overview | (0, 30, 0)       | (90, 0, 0)       | 90° | Entire Floor 1 (60×40m) |
| virtual-f2-overview | (0, 33.5, 0)     | (90, 0, 0)       | 90° | Entire Floor 2          |
| virtual-gate-in     | (28, 3, 2)       | (15, -90, 0)     | 60° | Entry gate area         |
| virtual-gate-out    | (-28, 3, 2)      | (15, 90, 0)      | 60° | Exit gate area          |
