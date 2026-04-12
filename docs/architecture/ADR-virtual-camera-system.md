# ADR-006: Virtual Camera System for Parking Digital Twin

## Trạng thái: Accepted

## Bối cảnh

ParkSmart cần hệ thống virtual camera trong Unity Digital Twin để:

1. Giám sát bãi đỗ xe theo thời gian thực từ web
2. Cho phép user xem xe đã đỗ qua camera feed
3. Phát hiện slot occupied/empty bằng physics detection
4. Hiển thị camera như đối tượng 3D trong scene (có đánh dấu slot màu cam)
5. **Mọi giao tiếp là real-time, bidirectional giữa web và Unity**

### Existing Infrastructure (đã có sẵn):

- Realtime service (Go/gorilla-websocket): hub pub/sub, `parking_updates` channel
- AI service: MJPEG streaming pattern tại `/ai/cameras/stream`
- Frontend: `CamerasPage` hiển thị MJPEG streams qua `<img src=mjpeg>`
- Unity: NativeWebSocket, `GateCameraSimulator.cs` với RenderTexture→PNG capture
- Database: `infrastructure_camera` table + `car_slot.camera` FK
- Gateway: KHÔNG proxy WebSocket (direct connections tới :8006)

### Constraints:

- NativeWebSocket hỗ trợ `Send(byte[])` cho binary frames
- WS ReadLimit hiện tại = 4096 — quá nhỏ cho camera frames
- Frontend CamerasPage chỉ handle JSON messages — không có binary WS handler

---

## Phương Án Xem Xét

### Option A: Unity → HTTP POST → AI MJPEG (Reuse existing pattern)

```
Unity RenderTexture → EncodeToJPG → HTTP POST /ai/cameras/virtual/frame
AI service buffers latest frame per camera_id in memory
Web viewer: <img src="/ai/cameras/stream?camera_id=virtual-f1-overview&fps=3">
```

- **Ưu**: Tái dụng 100% MJPEG infrastructure (AI service + Frontend). Zero WS changes. Zero frontend changes. Simple HTTP POST from Unity.
- **Nhược**: Thêm hop qua AI service. Latency ~10-50ms (chấp nhận được cho monitoring).
- **Trade-off**: Coupling vào AI service cho streaming, nhưng AI service đã là streaming hub.

### Option B: Unity → WS Binary → Realtime Service → WS Binary → Web

- **Ưu**: Lower latency, native pub/sub.
- **Nhược**: Cần sửa realtime-service (buffer sizes 1024→128KB, binary writePump, new WS endpoint). Cần frontend binary handler (Blob→ObjectURL). Cần Unity WS binary support (chưa dùng). **3 hệ thống phải thay đổi lớn.**
- **Trade-off**: Performance tốt hơn nhưng complexity cao gấp 3x.

### Option C: Unity → HTTP MJPEG Server

- **Ưu**: Direct stream, lowest latency.
- **Nhược**: Unity không designed cho HTTP server. Rất phức tạp, không có library hỗ trợ.

## Quyết Định

**Option A** vì:

1. **Zero frontend changes** — `CamerasPage` đã handle MJPEG via `<img>` tag
2. **Zero realtime-service changes** — không đụng WS infrastructure đang ổn định
3. **Minimal AI service change** — chỉ thêm 1 POST endpoint + in-memory buffer (~20 dòng code)
4. **Proven pattern** — exact same pattern đang chạy cho physical cameras
5. **Latency 10-50ms** — chấp nhận được cho parking monitoring (không phải gaming/real-time control)
6. **Bandwidth**: 4 cameras × 5 fps × 40KB = 800KB/s HTTP traffic — trivial

## Hệ Quả

- **Tích cực**: Đơn giản, tái dụng maximum, triển khai nhanh, ít risk
- **Trade-offs**: AI service trở thành single point cho streaming (đã là vậy với physical cameras)
- **Rủi ro**: AI service crash → mất camera feeds → **Mitigation**: health check, auto-restart (Docker)

---

## 1. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         UNITY DIGITAL TWIN                          │
│                                                                     │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐  │
│  │ VirtualCamera     │   │  SlotOccupancy   │   │  ParkingManager│  │
│  │ Manager           │   │  Detector        │   │  (existing)    │  │
│  │                   │   │                  │   │                │  │
│  │ ┌──────────────┐ │   │ Physics.Overlap  │   │ WS: slot.status│  │
│  │ │ CameraStreamer│ │   │ Box per slot     │   │ _update recv   │  │
│  │ │ ×4 cameras   │ │   │ every 1-2s       │   │                │  │
│  │ └──────┬───────┘ │   └────────┬─────────┘   └────────────────┘  │
│  └────────┼─────────┘            │                                  │
└───────────┼──────────────────────┼──────────────────────────────────┘
            │ HTTP POST            │ HTTP POST
            │ JPEG frames          │ slot detection
            │ (5 fps/camera)       │ results
            ▼                      ▼
┌──────────────────────┐   ┌──────────────────────┐
│   AI SERVICE :8009   │   │ REALTIME SERVICE:8006 │
│                      │   │                       │
│ POST /ai/cameras/    │   │ POST /api/broadcast/  │
│   virtual/frame      │   │   slot-status/        │
│     ↓                │   │     ↓                 │
│ frame_buffer{        │   │ Hub.Broadcast(         │
│   cam_id: jpeg_bytes │   │  "parking_updates",   │
│ }                    │   │  "slot.status_update") │
│     ↓                │   │     ↓                 │
│ GET /ai/cameras/     │   │ WS → all subscribers  │
│   stream?camera_id=  │   │                       │
│   virtual-f1-overview│   └───────────────────────┘
│     ↓                │             │
│ MJPEG multipart      │             │ WS
│ stream response      │             │
└──────────┬───────────┘             │
           │ HTTP MJPEG              │
           ▼                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                     WEB FRONTEND :5173                           │
│                                                                  │
│  ┌───────────────────────┐   ┌────────────────────────────────┐  │
│  │ CamerasPage           │   │ WebSocket Service              │  │
│  │                       │   │ (existing)                     │  │
│  │ <img src="/ai/cameras │   │                                │  │
│  │  /stream?camera_id=   │   │ slot.status_update →           │  │
│  │  virtual-f1-overview  │   │   parkingSlice update          │  │
│  │  &fps=3" />           │   │                                │  │
│  │                       │   │ booking.status_update →        │  │
│  │ Zero code change!     │   │   bookingSlice update          │  │
│  └───────────────────────┘   └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Streaming Pipeline Design

### Frame Flow: Unity Render → Web Viewer

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│ Unity Camera │    │ RenderTexture│    │  Texture2D   │    │  JPEG    │
│ .Render()    │───→│  640×480     │───→│ .ReadPixels()│───→│EncodeToJPG
│              │    │  24-bit      │    │  RGB24       │    │ quality=75│
└─────────────┘    └──────────────┘    └──────────────┘    └────┬─────┘
                                                                │
                                                          ~30-50KB JPEG
                                                                │
                    ┌───────────────────────────────────────────┘
                    ▼
┌──────────────────────────────────────────┐
│ HTTP POST /ai/cameras/virtual/frame      │
│ Headers:                                 │
│   Content-Type: image/jpeg               │
│   X-Camera-ID: virtual-f1-overview       │
│   X-Gateway-Secret: {secret}             │
│ Body: raw JPEG bytes                     │
└────────────────────┬─────────────────────┘
                     ▼
┌──────────────────────────────────────────┐
│ AI Service: frame_buffer dict            │
│                                          │
│ frame_buffer = {                         │
│   "virtual-f1-overview": {               │
│     "jpeg": b'\xff\xd8...',             │
│     "timestamp": 1711929600.123,         │
│     "width": 640, "height": 480          │
│   },                                     │
│   "virtual-f2-overview": {...},          │
│   ...                                    │
│ }                                        │
└────────────────────┬─────────────────────┘
                     ▼
┌──────────────────────────────────────────┐
│ GET /ai/cameras/stream                   │
│   ?camera_id=virtual-f1-overview&fps=3   │
│                                          │
│ Response: multipart/x-mixed-replace      │
│                                          │
│ async def generate():                    │
│   while True:                            │
│     frame = frame_buffer.get(camera_id)  │
│     if frame:                            │
│       yield MJPEG_FRAME(frame["jpeg"])   │
│     await asyncio.sleep(1/fps)           │
└────────────────────┬─────────────────────┘
                     ▼
┌──────────────────────────────────────────┐
│ Browser: <img src="...stream..." />      │
│ Native MJPEG rendering — zero JS needed  │
└──────────────────────────────────────────┘
```

### Performance Budget

| Metric             | Value           | Notes                                          |
| ------------------ | --------------- | ---------------------------------------------- |
| Resolution         | 640×480         | Sufficient for monitoring, matches gate camera |
| JPEG quality       | 75              | Good balance: ~30-50KB/frame                   |
| Capture FPS        | 5               | Unity → AI POST rate                           |
| Viewer FPS         | 3               | AI → Web MJPEG rate (configurable per viewer)  |
| Cameras            | 4               | 2 floor overview + 2 gate                      |
| Upload bandwidth   | ~800 KB/s       | 4 cams × 5fps × 40KB                           |
| GPU readback cost  | ~2ms per camera | ReadPixels on 640×480                          |
| Total GPU overhead | ~10ms/frame     | 4 cameras × 2.5ms (incl. encode)               |
| AI memory usage    | ~200 KB         | 4 buffers × 50KB                               |
| Viewer latency     | 50-200ms        | POST delay + MJPEG poll interval               |

---

## 3. Camera Placement Specification

### Parking Lot Layout (from ParkingLotGenerator)

```
Platform: 60m × 40m, 2 floors, floorHeight=3.5m

Floor Layout (top-down view):
                    X=-30                    X=0                     X=30
                      │                       │                       │
          Z=+20  ─────┼───────────────────────┼───────────────────────┼─────
                      │                       │     MOTORBIKE ZONE    │
                      │                       │     M-01..M-20        │
          Z=+5.5 ─────│  CAR ROW 2 (C-slots)  │     X[15..25]        │
                      │  C-01..C-10            │     Z[13..17]        │
          Z=+3   ─────│  X[-25..0]             │                      │
                      │═══════ LANE ═══════════│══════════════════════│
          Z=-3   ─────│                        │                      │
                      │  CAR ROW 1 (A/B-slots) │                      │
          Z=-5.5 ─────│  A-01..A-10            │                      │
                      │  X[-25..0]             │     GARAGE ZONE      │
          Z=-15  ─────│                        │     G-01..G-05       │
                      │                        │     X[10..25]        │
          Z=-20  ─────┼───────────────────────┼───────────────────────┼─────
                      │                       │                       │
                GATE-OUT-01              (center)              GATE-IN-01
                X=-30, Z=0                                     X=+30, Z=0
```

### Virtual Camera Specifications

| Camera ID             | Name               | Position (x,y,z) | Rotation (x,y,z) | FOV | Resolution | Coverage                                                     |
| --------------------- | ------------------ | ---------------- | ---------------- | --- | ---------- | ------------------------------------------------------------ |
| `virtual-f1-overview` | Tầng 1 — Toàn cảnh | (0, 30, 0)       | (90, 0, 0)       | 90° | 640×480    | All F1 slots: A-01..A-10, C-01..C-10, G-01..G-05, M-01..M-20 |
| `virtual-f2-overview` | Tầng 2 — Toàn cảnh | (0, 33.5, 0)     | (90, 0, 0)       | 90° | 640×480    | All F2 slots: B-01..B-10, C-11..C-20, G-06..G-10, M-21..M-40 |
| `virtual-gate-in`     | Cổng vào           | (28, 3, 2)       | (15, -90, 0)     | 60° | 640×480    | Entry gate area, approaching vehicles                        |
| `virtual-gate-out`    | Cổng ra            | (-28, 3, 2)      | (15, 90, 0)      | 60° | 640×480    | Exit gate area, departing vehicles                           |

### Camera 3D Object Specification

Mỗi virtual camera là một visible GameObject trong scene:

```
GameObject: "VirtualCamera_{id}"
├── MeshFilter: Cube (scaled to camera housing shape)
│   Scale: (0.3, 0.2, 0.4) — small box
│   Material: Dark gray (#333333)
├── Camera component (for RenderTexture capture)
├── VirtualCameraStreamer component
├── Light (small spot, optional — visual indicator)
│   Color: Orange (#FF8800), Range: 2m, Intensity: 0.5
└── Children:
    └── "Lens" (Sphere, scale 0.1, material: glass/reflective)
```

### Slot Marking (Orange color for monitored slots)

Khi camera active, các slot nó giám sát có viền cam:

- Sử dụng `OrangeLineColor` đã có trong ParkingLotGenerator: `new Color(1f, 0.5f, 0f)`
- Thêm thin border quad (LineRenderer hoặc 4 quads) quanh slot khi camera monitoring
- Toggle on/off khi camera is_active changes

---

## 4. Slot Detection Algorithm

### Physics-Based Detection

```csharp
// SlotOccupancyDetector.cs — attached to ParkingManager or separate GO

// Runs every detectionInterval seconds (default: 2s)
// For each registered ParkingSlot:
//   1. Physics.OverlapBox at slot world position
//   2. Check for Collider on object with VehicleController component
//   3. Compare with current slot status
//   4. If changed → broadcast via API

private void DetectSlotOccupancy(ParkingSlot slot)
{
    Vector3 center = slot.transform.position + Vector3.up * 0.5f;
    Vector3 halfExtents = GetSlotHalfExtents(slot.slotType);

    Collider[] hits = Physics.OverlapBox(center, halfExtents, slot.transform.rotation);

    bool vehiclePresent = false;
    VehicleController detectedVehicle = null;

    foreach (var hit in hits)
    {
        var vc = hit.GetComponent<VehicleController>();
        if (vc != null && vc.state == VehicleController.VehicleState.Parked)
        {
            vehiclePresent = true;
            detectedVehicle = vc;
            break;
        }
    }

    // State transition logic:
    // reserved + vehicle with matching booking → occupied (arrival confirmed)
    // available + vehicle → occupied (unexpected, but handle)
    // occupied + no vehicle → available (departure confirmed)
}

private Vector3 GetSlotHalfExtents(ParkingSlot.SlotType type)
{
    return type switch
    {
        SlotType.Painted   => new Vector3(1.25f, 1f, 2.5f),  // slotWidth/2, height, slotDepth/2
        SlotType.Garage    => new Vector3(1.5f, 1.25f, 3f),   // garageWidth/2, garageHeight/2, garageDepth/2
        SlotType.Motorbike => new Vector3(0.5f, 0.75f, 1f),   // motorbikeWidth/2, height, motorbikeDepth/2
        _                  => new Vector3(1.25f, 1f, 2.5f)
    };
}
```

### Detection State Machine

```
                    ┌─────────────┐
                    │   AVAILABLE  │
                    │ (no vehicle) │
                    └──────┬──────┘
                           │ vehicle detected
                           ▼
                    ┌─────────────┐
                    │  OCCUPIED    │
                    │ (vehicle     │
                    │  parked)     │
                    └──────┬──────┘
                           │ vehicle leaves
                           ▼
                    ┌─────────────┐
                    │  AVAILABLE   │
                    └─────────────┘

For RESERVED slots:
                    ┌─────────────┐
                    │  RESERVED    │
                    │ (booking     │
                    │  active)     │
                    └──────┬──────┘
                           │ vehicle with matching
                           │ bookingId detected
                           ▼
                    ┌─────────────┐
                    │  OCCUPIED    │
                    │ (arrival     │
                    │  confirmed)  │──→ broadcast slot.status_update
                    └──────┬──────┘     + booking.arrival_confirmed
                           │
                           │ vehicle departs
                           ▼
                    ┌─────────────┐
                    │  AVAILABLE   │──→ broadcast slot.status_update
                    └─────────────┘
```

### Notification Flow

```
Unity detects state change
  → HTTP POST to realtime broadcast API:
      POST http://localhost:8006/api/broadcast/slot-status/
      {
        "slotId": "uuid",
        "zoneId": "uuid",
        "status": "occupied",
        "vehicleType": "Car",
        "detectedPlate": "51A-123.45",
        "detectionSource": "virtual_camera"
      }
  → Hub broadcasts to "parking_updates" group
  → All WS clients receive slot.status_update
  → Frontend parkingSlice updates
  → CamerasPage / ParkingMap re-renders
```

---

## 5. WebSocket Message Contracts

### Existing Messages (reused as-is)

| Type                       | Direction     | Group             | Data Schema                             |
| -------------------------- | ------------- | ----------------- | --------------------------------------- |
| `slot.status_update`       | Server→Client | `parking_updates` | `{slotId, zoneId, status, vehicleType}` |
| `zone.availability_update` | Server→Client | `parking_updates` | `{zoneId, availableCount}`              |
| `booking.status_update`    | Server→Client | `user_{userId}`   | `{bookingId, status, ...}`              |

### New Messages

#### `camera.status_update` — Camera online/offline notification

```json
{
  "type": "camera.status_update",
  "data": {
    "cameraId": "virtual-f1-overview",
    "cameraType": "virtual",
    "status": "online",
    "floor": 1,
    "streamUrl": "/ai/cameras/stream?camera_id=virtual-f1-overview&fps=3",
    "lastFrameAt": "2026-04-01T10:00:00Z"
  }
}
```

- **Group**: `parking_updates`
- **Publisher**: AI service (via broadcast API) when frame buffer updates/stales
- **Subscribers**: All WS clients
- **Use case**: Frontend shows camera online/offline indicator

#### `slot.detection_update` — Physics-based slot detection from Unity

```json
{
  "type": "slot.detection_update",
  "data": {
    "slotId": "uuid",
    "slotCode": "A-03",
    "zoneId": "uuid",
    "isOccupied": true,
    "vehiclePlate": "51A-123.45",
    "bookingId": "uuid-or-null",
    "detectionSource": "virtual_camera",
    "cameraId": "virtual-f1-overview",
    "timestamp": "2026-04-01T10:00:05Z"
  }
}
```

- **Group**: `parking_updates`
- **Publisher**: Unity (via realtime broadcast API)
- **Subscribers**: All WS clients
- **Use case**: More detailed than `slot.status_update` — includes detection metadata

### New Broadcast API Endpoint

```
POST /api/broadcast/camera-status/
Headers: X-Gateway-Secret: {secret}
Body: { camera_id, camera_type, status, floor, stream_url }
→ Broadcasts camera.status_update to parking_updates group
```

---

## 6. API Contracts

### AI Service — New Endpoints

#### POST `/ai/cameras/virtual/frame` — Receive frame from Unity

```yaml
/ai/cameras/virtual/frame:
  post:
    summary: Receive a JPEG frame from Unity virtual camera
    operationId: postVirtualFrame
    tags: [cameras]
    security:
      - GatewaySecret: []
    parameters:
      - name: X-Camera-ID
        in: header
        required: true
        schema: { type: string, example: "virtual-f1-overview" }
      - name: X-Gateway-Secret
        in: header
        required: true
        schema: { type: string }
    requestBody:
      required: true
      content:
        image/jpeg:
          schema:
            type: string
            format: binary
    responses:
      "200":
        description: Frame accepted
        content:
          application/json:
            schema:
              type: object
              properties:
                status: { type: string, example: "ok" }
                camera_id: { type: string }
                frame_size: { type: integer }
                buffer_count: { type: integer }
      "400":
        description: Missing camera ID or invalid JPEG
      "401":
        description: Invalid gateway secret
      "413":
        description: Frame too large (max 500KB)
```

#### GET `/ai/cameras/virtual/list` — List active virtual cameras

```yaml
/ai/cameras/virtual/list:
  get:
    summary: List virtual cameras with active frame buffers
    operationId: listVirtualCameras
    tags: [cameras]
    responses:
      "200":
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  id: { type: string }
                  lastFrameAt: { type: string, format: date-time }
                  frameSize: { type: integer }
                  streamUrl: { type: string }
                  status: { type: string, enum: [online, stale, offline] }
```

#### Modified: GET `/ai/cameras/stream` — Now serves virtual cameras too

No contract change. Behavior change:

1. If `camera_id` starts with `virtual-` → serve from frame_buffer
2. Else → serve from cv2 capture (existing behavior)

#### Modified: GET `/ai/cameras/list` — Include virtual cameras

Existing response format extended — virtual cameras appended to the list with `type: "virtual"`.

### Realtime Service — New Broadcast Endpoint

```yaml
/api/broadcast/camera-status/:
  post:
    summary: Broadcast camera status update
    security:
      - GatewaySecret: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [camera_id, status]
            properties:
              camera_id: { type: string }
              camera_type: { type: string, enum: [physical, virtual] }
              status: { type: string, enum: [online, offline, stale] }
              floor: { type: integer }
              stream_url: { type: string }
    responses:
      "200": { description: "Broadcast sent" }
```

### Parking Service — Modified Camera API

Existing CRUD endpoints at `/parking/cameras/` — no new endpoints needed.
Virtual cameras registered via existing API or seed script.

---

## 7. Database Changes

### Migration: Add `camera_type` and `floor` to Camera model

**File: `backend-microservices/parking-service/infrastructure/migrations/000X_add_camera_type_floor.py`**

```sql
-- Forward migration
ALTER TABLE infrastructure_camera
  ADD COLUMN camera_type VARCHAR(20) NOT NULL DEFAULT 'physical';

ALTER TABLE infrastructure_camera
  ADD COLUMN floor_id CHAR(32) NULL;

ALTER TABLE infrastructure_camera
  ADD CONSTRAINT fk_camera_floor
    FOREIGN KEY (floor_id) REFERENCES floor(id)
    ON DELETE SET NULL;

CREATE INDEX idx_camera_type ON infrastructure_camera(camera_type);
CREATE INDEX idx_camera_floor ON infrastructure_camera(floor_id);
```

```sql
-- Rollback
ALTER TABLE infrastructure_camera DROP FOREIGN KEY fk_camera_floor;
ALTER TABLE infrastructure_camera DROP INDEX idx_camera_floor;
ALTER TABLE infrastructure_camera DROP INDEX idx_camera_type;
ALTER TABLE infrastructure_camera DROP COLUMN floor_id;
ALTER TABLE infrastructure_camera DROP COLUMN camera_type;
```

### Updated Camera Model

```python
class Camera(models.Model):
    CAMERA_TYPE_CHOICES = [
        ('physical', 'Physical Camera'),
        ('virtual', 'Virtual Camera'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=45, blank=True, default='')
    port = models.IntegerField(default=0)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='cameras', null=True, blank=True)
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True, related_name='cameras')
    camera_type = models.CharField(max_length=20, choices=CAMERA_TYPE_CHOICES, default='physical')
    stream_url = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'infrastructure_camera'
        indexes = [
            models.Index(fields=['camera_type']),
        ]
```

### Seed Data: Virtual Cameras

```python
VIRTUAL_CAMERAS = [
    {
        "name": "Tầng 1 — Toàn cảnh",
        "camera_type": "virtual",
        "ip_address": "",
        "port": 0,
        "zone": None,  # covers entire floor
        "floor": 1,    # FK lookup by level
        "stream_url": "/ai/cameras/stream?camera_id=virtual-f1-overview&fps=3",
        "is_active": True,
    },
    {
        "name": "Tầng 2 — Toàn cảnh",
        "camera_type": "virtual",
        "floor": 2,
        "stream_url": "/ai/cameras/stream?camera_id=virtual-f2-overview&fps=3",
    },
    {
        "name": "Cổng vào — Virtual",
        "camera_type": "virtual",
        "floor": 1,
        "stream_url": "/ai/cameras/stream?camera_id=virtual-gate-in&fps=5",
    },
    {
        "name": "Cổng ra — Virtual",
        "camera_type": "virtual",
        "floor": 1,
        "stream_url": "/ai/cameras/stream?camera_id=virtual-gate-out&fps=5",
    },
]
```

### Migration Plan

1. Migration file: Django auto-generated via `makemigrations`
2. Rollback: `migrate infrastructure 000{N-1}`
3. Data migration needed: No — existing cameras get `camera_type='physical'` via default
4. Zero-downtime compatible: **YES** — additive columns only
5. Estimated migration time: < 1s (table has few rows)

---

## 8. Component List

### New Unity Scripts

| File                                             | Purpose                                               | Lines (est.) | Dependencies                               |
| ------------------------------------------------ | ----------------------------------------------------- | ------------ | ------------------------------------------ |
| `Assets/Scripts/Camera/VirtualCameraStreamer.cs` | RenderTexture→JPEG→HTTP POST to AI service per camera | ~120         | ApiService, ApiConfig                      |
| `Assets/Scripts/Camera/VirtualCameraManager.cs`  | Spawns/manages all virtual cameras, handles lifecycle | ~150         | ParkingLotGenerator, ParkingManager        |
| `Assets/Scripts/Camera/SlotOccupancyDetector.cs` | Physics.OverlapBox slot scanning + broadcast          | ~130         | ParkingSlot, VehicleController, ApiService |

### Modified Unity Scripts

| File                                    | Change                                                                       | Impact |
| --------------------------------------- | ---------------------------------------------------------------------------- | ------ |
| `Assets/Scripts/API/ApiConfig.cs`       | Add `aiServiceUrl`, `cameraFps`, `cameraJpegQuality`, `gatewaySecret` fields | Low    |
| `Assets/Scripts/API/ApiService.cs`      | Add `PostCameraFrame(string cameraId, byte[] jpeg)` method                   | Low    |
| `Assets/Scripts/API/DataModels.cs`      | Add `CameraFrameResponse`, `VirtualCameraConfig` DTOs                        | Low    |
| `Assets/Scripts/Core/ParkingManager.cs` | Initialize VirtualCameraManager after lot generation                         | Low    |

### Modified Backend — AI Service

| File                                       | Change                                                                                                                             | Impact |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ------ |
| `ai-service-fastapi/app/routers/camera.py` | Add `frame_buffer` dict, `POST /virtual/frame`, modify `stream` to serve virtual cameras, modify `list` to include virtual cameras | Medium |

### Modified Backend — Realtime Service

| File                                                | Change                                         | Impact |
| --------------------------------------------------- | ---------------------------------------------- | ------ |
| `realtime-service-go/internal/handler/broadcast.go` | Add `BroadcastCameraStatus` handler            | Low    |
| `realtime-service-go/cmd/server/main.go`            | Register `/api/broadcast/camera-status/` route | Low    |

### Modified Backend — Parking Service

| File                                            | Change                                            | Impact |
| ----------------------------------------------- | ------------------------------------------------- | ------ |
| `parking-service/infrastructure/models.py`      | Add `camera_type`, `floor` fields to Camera model | Low    |
| `parking-service/infrastructure/migrations/`    | New migration file                                | Low    |
| `parking-service/infrastructure/serializers.py` | Add new fields to CameraSerializer                | Low    |

### New Backend Scripts

| File                                            | Purpose                           |
| ----------------------------------------------- | --------------------------------- |
| `backend-microservices/seed_virtual_cameras.py` | Seed virtual camera records in DB |

### Frontend Changes (Minimal)

| File                                    | Change                                                                      | Impact |
| --------------------------------------- | --------------------------------------------------------------------------- | ------ |
| `spotlove-ai/src/types/parking.ts`      | Add `cameraType` to Camera interface                                        | Low    |
| `spotlove-ai/src/pages/CamerasPage.tsx` | Add "Virtual Cameras" section/tab (optional — existing code may work as-is) | Low    |

---

## 9. Implementation Order

### Phase 1: Backend Frame Buffer (Foundation)

```
Priority: HIGH — everything depends on this
Duration: Small

1. ai-service-fastapi/app/routers/camera.py
   - Add frame_buffer dict (thread-safe with asyncio.Lock)
   - Add POST /ai/cameras/virtual/frame endpoint
   - Modify stream() to check frame_buffer for virtual-* camera_ids
   - Modify list() to include virtual cameras from buffer
   - Add GET /ai/cameras/virtual/list endpoint

2. parking-service/infrastructure/models.py
   - Add camera_type, floor fields
   - makemigrations + migrate

3. parking-service/infrastructure/serializers.py
   - Add new fields to serializer

4. realtime-service-go/internal/handler/broadcast.go
   - Add BroadcastCameraStatus handler

5. realtime-service-go/cmd/server/main.go
   - Register camera-status broadcast route
```

### Phase 2: Unity Camera Capture (Core Feature)

```
Priority: HIGH
Duration: Medium
Depends on: Phase 1

6. Assets/Scripts/API/ApiConfig.cs
   - Add AI service URL, camera config fields

7. Assets/Scripts/API/ApiService.cs
   - Add PostCameraFrame(cameraId, jpeg) coroutine

8. Assets/Scripts/API/DataModels.cs
   - Add camera-related DTOs

9. Assets/Scripts/Camera/VirtualCameraStreamer.cs
   - RenderTexture capture coroutine
   - JPEG encoding + HTTP POST
   - Configurable fps, resolution, quality

10. Assets/Scripts/Camera/VirtualCameraManager.cs
    - Spawn camera GameObjects at specified positions
    - Create Camera components + RenderTextures
    - Attach VirtualCameraStreamer to each
    - Visual camera housing meshes (dark box + lens)
    - Orange slot marking for monitored slots
```

### Phase 3: Slot Detection (Enhancement)

```
Priority: MEDIUM
Duration: Small
Depends on: Phase 2

11. Assets/Scripts/Camera/SlotOccupancyDetector.cs
    - Physics.OverlapBox scan every 2 seconds
    - State change detection
    - Broadcast via realtime API

12. Assets/Scripts/Core/ParkingManager.cs (modify)
    - Initialize VirtualCameraManager + SlotOccupancyDetector
```

### Phase 4: Integration & Data

```
Priority: MEDIUM
Duration: Small
Depends on: Phase 1

13. backend-microservices/seed_virtual_cameras.py
    - Register 4 virtual cameras in DB with stream_urls

14. spotlove-ai/src/types/parking.ts (optional)
    - Add cameraType field to Camera interface

15. spotlove-ai/src/pages/CamerasPage.tsx (optional)
    - Add virtual camera filter/section
    - Should work without changes if stream_url is set
```

### Phase 5: E2E Validation

```
Priority: HIGH
Duration: Small
Depends on: All phases

16. Manual E2E test:
    - Start Unity → virtual cameras stream to AI service
    - Open CamerasPage → see live feed from virtual cameras
    - Create booking on web → slot turns reserved in Unity
    - Vehicle parks → camera shows parked vehicle
    - User opens camera feed → sees their car
```

---

## Implementation Notes

- **Pattern reference**: Use `GateCameraSimulator.cs` RenderTexture pattern but switch `EncodeToPNG()` → `EncodeToJPG(75)` for 3-5× smaller frames
- **GPU readback**: `ReadPixels` is a GPU→CPU sync point. At 5fps for 4 cameras (640×480) this is ~10ms total per frame cycle — acceptable
- **Thread safety**: AI service frame_buffer must use `asyncio.Lock` since FastAPI is async
- **Camera lifecycle**: VirtualCameraStreamer should stop posting when `Application.isFocused` is false (Unity minimized)
- **Stale detection**: AI service should mark cameras as `stale` if no frame received in 5+ seconds, `offline` if 30+ seconds
- **Memory cleanup**: Remove stale frame buffers after 60 seconds of no updates
- **Orange markings**: Use existing `OrangeLineColor` from ParkingLotGenerator; add thin quad borders around camera-monitored slots
- **Security**: `POST /ai/cameras/virtual/frame` must validate `X-Gateway-Secret` header to prevent unauthorized frame injection
- **No `git add .`**: Each change committed as separate logical unit per git workflow rules

---

## Security Considerations

| Threat                            | Mitigation                                                                        |
| --------------------------------- | --------------------------------------------------------------------------------- |
| Unauthorized frame injection      | `X-Gateway-Secret` on POST endpoint                                               |
| Frame buffer DoS (flooding)       | Rate limit: max 30 frames/sec per camera_id                                       |
| Large frame DoS                   | Max body size: 500KB per frame                                                    |
| Information disclosure via camera | Camera streams require auth in production (currently bypassed for `<img>` compat) |
| Buffer memory leak                | Auto-cleanup stale buffers after 60s; max 20 virtual cameras                      |

## Observability Requirements

### Metrics

- `virtual_camera_frames_received_total{camera_id}` — counter
- `virtual_camera_frame_size_bytes{camera_id}` — histogram
- `virtual_camera_buffer_age_seconds{camera_id}` — gauge (time since last frame)
- `virtual_camera_stream_viewers_active{camera_id}` — gauge

### Logs

- Frame received: `level=info, camera_id, frame_size, buffer_count`
- Camera stale: `level=warn, camera_id, last_frame_age`
- Camera offline: `level=error, camera_id, offline_duration`

### Health Check Extension

```json
GET /health → {
  "checks": {
    "virtual_cameras": {
      "status": "ok",
      "active": 4,
      "stale": 0,
      "offline": 0
    }
  }
}
```
