# Research Report: Virtual Camera System — Existing Real-Time & Streaming Infrastructure

**Task:** Virtual Camera Streaming | **Date:** 2026-04-01 | **Type:** Mixed (Codebase + Architecture)

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Realtime service (Go/Gin/gorilla-websocket)** đã có hub group-based pub/sub, `parking_updates` channel hoạt động — chỉ cần thêm group mới cho camera feeds
> 2. **AI Service đã có MJPEG streaming** qua HTTP (`/ai/cameras/stream`) dùng cv2 — đây là pattern tham chiếu cho virtual camera
> 3. **Unity đã có RenderTexture→PNG capture** trong `GateCameraSimulator.cs` — chỉ cần mở rộng thành continuous streaming thay vì one-shot capture
> 4. **Frontend đã có CamerasPage + AdminCamerasPage** hiển thị stream qua `<img src=mjpeg>` — tái dụng pattern này cho virtual cameras
> 5. **Gateway KHÔNG proxy WebSocket** — frontend/Unity connect trực tiếp tới `:8006`. Camera binary data nên dùng kênh riêng (WS binary frames hoặc HTTP MJPEG)

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Realtime Service (Go + Gin + gorilla/websocket)

| File                                                                             | Mục đích                                                             | Relevance                                 |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------- |
| `backend-microservices/realtime-service-go/internal/hub/hub.go`                  | Hub pub/sub core: groups, broadcast, connection management           | **HIGH** — extend cho camera channels     |
| `backend-microservices/realtime-service-go/internal/handler/ws_handler.go`       | WS upgrade, readPump/writePump, subscribe/unsubscribe handling       | **HIGH** — cần thêm handler cho camera WS |
| `backend-microservices/realtime-service-go/internal/handler/broadcast.go`        | REST broadcast endpoints (slot, zone, booking) cho internal services | **HIGH** — thêm camera broadcast endpoint |
| `backend-microservices/realtime-service-go/cmd/server/main.go`                   | Server setup, routes, CORS                                           | **MEDIUM** — thêm route cho camera WS     |
| `backend-microservices/realtime-service-go/internal/middleware/internal_auth.go` | X-Gateway-Secret auth cho broadcast API                              | **LOW** — tái dụng cho camera broadcast   |
| `backend-microservices/realtime-service-go/internal/config/config.go`            | Port 8006, env vars                                                  | **LOW**                                   |

**Technology Stack:**

- **Framework:** Gin (HTTP) + gorilla/websocket (WS)
- **Port:** 8006
- **Go version:** 1.22
- **Message format:** JSON `{ "type": string, "data": object }`

**WebSocket URL Patterns:**

```
ws://localhost:8006/ws/parking          — Public: parking updates (auto-subscribe to "parking_updates" group)
ws://localhost:8006/ws/user/:userId     — Authenticated: user-specific + parking updates (auto-subscribe to "user_{userId}" + "parking_updates")
```

**Auth Mechanism:** NONE for WebSocket upgrade. WS endpoints are public (no auth middleware). Only broadcast REST API requires `X-Gateway-Secret` header.

**Existing Channels/Groups:**
| Group Pattern | Publisher | Subscribers | Message Types |
|---------------|-----------|-------------|---------------|
| `parking_updates` | Parking service (via broadcast API) | All WS clients | `slot.status_update`, `zone.availability_update`, `lot.availability_update` |
| `user_{userId}` | Booking/Notification services | Specific user's WS client | `booking.status_update`, `booking.created`, `notification` |
| `parking.lot.{lotId}` | (client-subscribed, not server-pushed yet) | Frontend clients that subscribe | — |
| `parking.zone.{zoneId}` | (client-subscribed, not server-pushed yet) | Frontend clients that subscribe | — |

**Message Format (broadcast):**

```json
{
  "type": "slot.status_update",
  "data": {
    "slotId": "uuid",
    "zoneId": "uuid",
    "status": "occupied",
    "vehicleType": "Car"
  }
}
```

**Key Observations:**

- Hub send channel buffer: 256 messages per connection
- Read limit: **4096 bytes** — ⚠️ TOO SMALL for binary camera frames
- Write pump uses `websocket.TextMessage` only — no binary support yet
- Ping/pong: 30s interval, 60s read deadline

### 2.2 AI Service Camera Streaming (Existing Pattern)

| File                                                             | Mục đích                 | Relevance                    |
| ---------------------------------------------------------------- | ------------------------ | ---------------------------- |
| `backend-microservices/ai-service-fastapi/app/routers/camera.py` | MJPEG streaming via HTTP | **HIGH** — reference pattern |

**Existing Endpoints:**

```
GET /ai/cameras/list      — List configured cameras (JSON)
GET /ai/cameras/snapshot   — Single JPEG frame
GET /ai/cameras/stream     — MJPEG multipart stream (for <img> tag)
    ?camera_id=plate-camera-ezviz
    ?url=rtsp://...
    &fps=5 (1-30)
```

**MJPEG Streaming Pattern:**

```python
# multipart/x-mixed-replace; boundary=frame
# Each frame: --frame\r\nContent-Type: image/jpeg\r\n\r\n{jpeg_bytes}\r\n
async def generate():
    while True:
        jpeg_bytes = await capture.capture_frame_bytes(stream_url, retries=1)
        yield b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
        await asyncio.sleep(interval)
```

**Configured Cameras:**
| ID | Name | Type | URL Source |
|----|------|------|-----------|
| `plate-camera-ezviz` | Camera Biển Số (EZVIZ) | plate | `settings.CAMERA_RTSP_URL` |
| `qr-camera-droidcam` | Camera QR Code (DroidCam) | qr | `settings.CAMERA_DROIDCAM_URL/video` |

### 2.3 Frontend WebSocket & Camera UI

| File                                               | Mục đích                                                 | Relevance  | Tái dụng?                             |
| -------------------------------------------------- | -------------------------------------------------------- | ---------- | ------------------------------------- |
| `spotlove-ai/src/services/websocket.service.ts`    | WS client singleton, Redux dispatch, message routing     | **HIGH**   | Yes — extend processMessage()         |
| `spotlove-ai/src/hooks/useWebSocketConnection.ts`  | WS lifecycle hook, subscribe/unsubscribe helpers         | **HIGH**   | Yes — add camera subscription helpers |
| `spotlove-ai/src/store/slices/websocketSlice.ts`   | WS state (status, error, reconnect)                      | **MEDIUM** | Yes — as-is                           |
| `spotlove-ai/src/store/slices/parkingSlice.ts`     | Parking state with realtime updates                      | **MEDIUM** | Pattern reference                     |
| `spotlove-ai/src/pages/CamerasPage.tsx`            | Camera viewer: grid/single view, MJPEG stream display    | **HIGH**   | Yes — extend for virtual cameras      |
| `spotlove-ai/src/pages/admin/AdminCamerasPage.tsx` | Admin camera management CRUD                             | **MEDIUM** | Yes — add virtual camera section      |
| `spotlove-ai/src/types/parking.ts`                 | Camera, CarSlot, Booking types (already has camera FK)   | **HIGH**   | Yes — extend Camera type              |
| `spotlove-ai/src/components/layout/MainLayout.tsx` | WS auto-connect on auth                                  | **LOW**    | As-is                                 |
| `spotlove-ai/src/App.tsx`                          | Routes: `/cameras`, `/admin/cameras`, `/admin/dashboard` | **LOW**    | Add new routes if needed              |

**Frontend WS Connection:**

```typescript
// URL construction
const WS_BASE_URL =
  import.meta.env.VITE_WS_URL || `${protocol}://${hostname}:8006/ws`;
// Connect: ws://localhost:8006/ws/user/{userId}/ (authenticated)
//          ws://localhost:8006/ws/parking/ (public)
```

**Frontend Camera Stream Display:**

```tsx
// CamerasPage uses <img> tag for MJPEG streams
const streamUrl = "/ai/cameras/stream?camera_id=plate-camera-ezviz&fps=3";
// Proxied to AI service via Vite dev server (or nginx in prod)
```

**Stream URL Resolution (CamerasPage.tsx):**

```typescript
// 3 stream types: "rtsp" | "http" | "proxy"
// RTSP → proxied via AI MJPEG: /ai/cameras/stream?url={encoded}&fps=3
// HTTP → direct (DroidCam MJPEG works in <img>)
// Proxy → already /ai/cameras/... path
```

**Frontend Routes:**
| Route | Page | Description |
|-------|------|-------------|
| `/cameras` | CamerasPage | User: parking cameras + their vehicle. Admin: all cameras grid |
| `/admin/cameras` | AdminCamerasPage | Camera CRUD management |
| `/admin/dashboard` | AdminDashboard | Stats overview |

### 2.4 Unity WebSocket

| File                                                                     | Mục đích                                                                    | Relevance  | Tái dụng?                                |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------- | ---------- | ---------------------------------------- |
| `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs`                 | HTTP + WS client. WS: connect, subscribe, parse slot updates                | **HIGH**   | Extend for camera publishing             |
| `ParkingSimulatorUnity/Assets/Scripts/API/ApiConfig.cs`                  | ScriptableObject config: `realtimeWsUrl = "ws://localhost:8006/ws/parking"` | **MEDIUM** | May need separate camera WS URL          |
| `ParkingSimulatorUnity/Assets/Scripts/API/DataModels.cs`                 | DTOs incl. WsSubscribeMessage, SlotStatusUpdate                             | **HIGH**   | Add camera frame models                  |
| `ParkingSimulatorUnity/Assets/Scripts/Camera/GateCameraSimulator.cs`     | Gate camera: RenderTexture→PNG→AI OCR (one-shot)                            | **HIGH**   | Pattern reference for continuous capture |
| `ParkingSimulatorUnity/Assets/Scripts/Camera/ParkingCameraController.cs` | Orbit camera controller (user camera, not streaming)                        | **LOW**    | —                                        |

**Unity WS Current Capabilities:**

- Library: **NativeWebSocket** (git#upm package)
- Connect to `ws://localhost:8006/ws/parking`
- Auto-subscribe to `parking.lot.{lotId}` on open
- Parse `slot.status_update` messages
- Events: `OnSlotStatusUpdate`, `OnWsConnected`, `OnWsDisconnected`, `OnWsError`
- **Text-only** messaging (JSON). No binary frame support currently.

**Unity RenderTexture Capture Pattern (GateCameraSimulator.cs:127-143):**

```csharp
var rt = new RenderTexture(640, 480, 24);
gateCamera.targetTexture = rt;
gateCamera.Render();
RenderTexture.active = rt;
var tex = new Texture2D(640, 480, TextureFormat.RGB24, false);
tex.ReadPixels(new Rect(0, 0, 640, 480), 0, 0);
tex.Apply();
byte[] imageBytes = tex.EncodeToPNG();
// ... cleanup rt, tex
```

### 2.5 Gateway Service (Go)

| File                                                                 | Mục đích                  | Relevance  |
| -------------------------------------------------------------------- | ------------------------- | ---------- |
| `backend-microservices/gateway-service-go/internal/config/config.go` | Route table, service URLs | **MEDIUM** |
| `backend-microservices/gateway-service-go/internal/handler/proxy.go` | Reverse proxy (HTTP only) | **LOW**    |
| `backend-microservices/gateway-service-go/internal/router/routes.go` | Single catch-all route    | **LOW**    |

**Gateway Route Table:**

```go
{"parking/",    ServiceRoute{"parking",    c.ParkingServiceURL,    false}},
{"realtime/",   ServiceRoute{"realtime",   c.RealtimeServiceURL,   false}},
{"ai/",         ServiceRoute{"ai",         c.AIServiceURL,         false}},
// ... others
```

**⚠️ CRITICAL: Gateway does NOT proxy WebSocket connections.** The proxy handler explicitly strips `Connection` and `Upgrade` headers:

```go
req.Header.Del("Connection")
req.Header.Del("Upgrade")
```

Frontend and Unity connect to realtime-service **directly** on port 8006, bypassing the gateway entirely.

For AI camera streams (`/ai/cameras/stream`), the frontend uses Vite proxy or nginx to route to AI service port 8009.

### 2.6 Database Schema

**Camera Table (parking-service Django):**

```
Table: infrastructure_camera
├── id          UUID (PK)
├── name        VARCHAR(255)
├── ip_address  VARCHAR(45)
├── port        INT
├── zone        UUID (FK → zone.id, nullable)
├── stream_url  TEXT
├── is_active   BOOLEAN (default true)
├── created_at  DATETIME
└── updated_at  DATETIME
```

**CarSlot Table (parking-service Django):**

```
Table: car_slot
├── id      UUID (PK)
├── zone    UUID (FK → zone.id)
├── code    VARCHAR(20)
├── status  ENUM(available, occupied, reserved, maintenance)
├── camera  UUID (FK → infrastructure_camera.id, nullable)  ← slot ↔ camera link exists!
├── x1, y1, x2, y2  INT (bounding box for AI detection)
├── created_at, updated_at
```

**Booking Table (booking-service Django):**

```
Table: bookings_booking
├── id, user_id, user_email
├── vehicle_id, vehicle_license_plate, vehicle_type
├── parking_lot_id, floor_id, zone_id, slot_id, slot_code
├── check_in_status: not_checked_in | checked_in | checked_out | no_show | cancelled
├── checked_in_at, checked_out_at
├── qr_code_data
└── ... (payment, pricing fields)
```

**Key Schema Observations:**

- `CarSlot.camera` FK already exists — a slot can be linked to a physical camera
- No virtual camera table exists yet
- Camera model has `stream_url` (RTSP/HTTP) — virtual cameras could use a different scheme (e.g., `ws://` or identifier)
- Bounding box coords (x1,y1,x2,y2) on slots are for AI detection, could also be used to highlight slots in virtual camera view

---

## 3. Key File Paths for Modification

### Backend — Realtime Service

| File                                                                       | Change Needed                                                                          |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `backend-microservices/realtime-service-go/internal/hub/hub.go`            | Increase Send buffer, add binary message support option                                |
| `backend-microservices/realtime-service-go/internal/handler/ws_handler.go` | Add `HandleCameraWS` endpoint, binary write support in writePump                       |
| `backend-microservices/realtime-service-go/internal/handler/broadcast.go`  | Add `BroadcastCameraFrame` endpoint (receives frame from Unity, broadcasts to viewers) |
| `backend-microservices/realtime-service-go/cmd/server/main.go`             | Register new camera WS routes                                                          |

### Backend — Parking Service

| File                                                             | Change Needed                                                          |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `backend-microservices/parking-service/infrastructure/models.py` | Optionally: Add `camera_type` field (physical/virtual) to Camera model |

### Frontend

| File                                              | Change Needed                                 |
| ------------------------------------------------- | --------------------------------------------- |
| `spotlove-ai/src/services/websocket.service.ts`   | Add camera frame message type handling        |
| `spotlove-ai/src/hooks/useWebSocketConnection.ts` | Add `subscribeToCamera()` helper              |
| `spotlove-ai/src/pages/CamerasPage.tsx`           | Add virtual camera feeds section              |
| `spotlove-ai/src/types/parking.ts`                | Extend Camera type with virtual camera fields |

### Unity

| File                                                     | Change Needed                                                               |
| -------------------------------------------------------- | --------------------------------------------------------------------------- |
| `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs` | Add camera frame publishing (binary WS or HTTP POST)                        |
| `ParkingSimulatorUnity/Assets/Scripts/API/ApiConfig.cs`  | Add camera streaming config (fps, resolution, WS URL)                       |
| `ParkingSimulatorUnity/Assets/Scripts/API/DataModels.cs` | Add CameraFrame models                                                      |
| `ParkingSimulatorUnity/Assets/Scripts/Camera/`           | NEW: `VirtualCameraStreamer.cs` — continuous RenderTexture capture + stream |

---

## 4. So Sánh Phương Án: Camera Frame Streaming

| Tiêu chí                    | Option A: WS Binary Frames                    | Option B: WS Base64 JSON               | Option C: HTTP MJPEG (like AI service)           |
| --------------------------- | --------------------------------------------- | -------------------------------------- | ------------------------------------------------ |
| **Bandwidth**               | ~50KB/frame JPEG (optimal)                    | ~67KB/frame (+33% base64 overhead)     | ~50KB/frame JPEG                                 |
| **Latency**                 | Low (direct binary push)                      | Medium (encode/decode overhead)        | Low (HTTP chunked)                               |
| **Viewer scalability**      | Hub broadcasts to N viewers simultaneously    | Same but 33% more bandwidth per viewer | Each viewer = separate HTTP connection to origin |
| **Unity compat**            | NativeWebSocket supports `SendBinary(byte[])` | JSON via `SendText()` (already used)   | Requires separate HTTP POST per frame            |
| **Frontend compat**         | Need custom binary→blob→objectURL handler     | JSON.parse → base64→blob               | `<img src=mjpeg>` (already works in CamerasPage) |
| **Realtime service change** | Add binary write to writePump                 | Minimal (JSON already supported)       | Bypass realtime service entirely                 |
| **Multiple cameras**        | Group per camera: `camera_{cameraId}`         | Same                                   | Separate endpoint per camera                     |
| **Complexity**              | Medium                                        | Low                                    | Low (but scaling concern)                        |
| **Existing pattern match**  | None (new pattern)                            | Close to existing JSON messaging       | Exact match with AI camera streaming             |

**Note**: Đây là facts để Architect quyết định. Không phải khuyến nghị của Researcher.

**Additional considerations for Architect:**

1. **Hybrid approach possible**: Unity → HTTP POST frames to realtime service → WS binary broadcast to viewers. This avoids Unity needing WS binary support while still using WS pub/sub for distribution.

2. **MJPEG-over-WS**: Unity sends JPEG frames via WS binary, realtime service re-packages as MJPEG HTTP stream for `<img>` tag consumption. Best of both worlds.

3. **Current WS limitations**: Read buffer is 1024 bytes, read limit is 4096 bytes in gorilla/websocket config. For 640×480 JPEG frames (~30-80KB), these MUST be increased.

4. **NativeWebSocket binary support**: The library exposes `WebSocket.Send(byte[])` for binary frames. This is supported but not used anywhere in the current codebase.

---

## 5. ⚠️ Gotchas & Known Issues

- [ ] **[WARNING]** Realtime WS `ReadBufferSize: 1024` and `ReadLimit: 4096` — far too small for camera frames. Must increase to at least 128KB.
- [ ] **[WARNING]** `writePump` only sends `websocket.TextMessage` — binary frames require `websocket.BinaryMessage` support.
- [ ] **[WARNING]** Hub `Send` channel buffer is 256 — at 5fps this is ~51 seconds of backlog per camera. May need larger buffer or frame dropping strategy.
- [ ] **[NOTE]** Gateway strips WS upgrade headers — all WS connections are direct to `:8006`. Virtual camera WS will follow same pattern.
- [ ] **[NOTE]** Frontend WS currently only handles `JSON.parse(event.data)` — binary message handling needs to check `event.data instanceof Blob/ArrayBuffer`.
- [ ] **[NOTE]** Unity `RenderTexture.ReadPixels` is a GPU→CPU readback — expensive if done at high fps. `EncodeToJPG()` (not PNG) should be used for smaller frames. PNG is ~3-5x larger.
- [ ] **[NOTE]** CamerasPage already has `streamErrors` tracking and fallback UI — can reuse for virtual camera error states.
- [ ] **[NOTE]** `CarSlot.camera` FK exists — virtual cameras could be registered in the same Camera table with a `camera_type='virtual'` discriminator, linking them to zones/slots they monitor.

---

## 6. Code Examples từ Existing Codebase

### Unity RenderTexture Capture (GateCameraSimulator.cs:127-143)

```csharp
// Source: ParkingSimulatorUnity/Assets/Scripts/Camera/GateCameraSimulator.cs
var rt = new RenderTexture(640, 480, 24);
gateCamera.targetTexture = rt;
gateCamera.Render();
RenderTexture.active = rt;
var tex = new Texture2D(640, 480, TextureFormat.RGB24, false);
tex.ReadPixels(new Rect(0, 0, 640, 480), 0, 0);
tex.Apply();
byte[] imageBytes = tex.EncodeToPNG(); // ← Switch to EncodeToJPG(75) for streaming
```

### Go Hub Broadcast (hub.go:133-144)

```go
// Source: backend-microservices/realtime-service-go/internal/hub/hub.go
func (h *Hub) Broadcast(group string, msgType string, data interface{}) {
    msg := Message{Type: msgType, Data: data}
    jsonData, err := json.Marshal(msg)
    // ... sends to h.broadcast channel → distributed to all group connections
}
```

### Frontend MJPEG Display (CamerasPage.tsx)

```tsx
// Source: spotlove-ai/src/pages/CamerasPage.tsx
// Cameras displayed via <img> tag pointing to MJPEG stream URL
const streamUrl = "/ai/cameras/stream?camera_id=plate-camera-ezviz&fps=3";
// <img src={streamUrl} /> — browser handles multipart/x-mixed-replace natively
```

### WS Message Processing (websocket.service.ts)

```typescript
// Source: spotlove-ai/src/services/websocket.service.ts
private handleMessage(event: MessageEvent): void {
    const message: WebSocketMessage = JSON.parse(event.data);
    // Currently only handles text (JSON) messages
    this.processMessage(message);
}
```

---

## 7. Checklist cho Implementer

- [ ] Increase realtime WS buffer sizes: `ReadBufferSize: 128*1024`, `WriteBufferSize: 128*1024`, `ReadLimit: 256*1024`
- [ ] Add binary message support to `writePump` (check message type, use `BinaryMessage` for camera frames)
- [ ] Add `HandleCameraWS` endpoint: `/ws/camera/:cameraId` — viewers subscribe to specific camera feed
- [ ] Add `BroadcastCameraFrame` REST or WS endpoint for Unity to push frames
- [ ] Unity: Create `VirtualCameraStreamer.cs` with configurable fps, resolution, JPEG quality
- [ ] Unity: Use `EncodeToJPG(quality)` NOT `EncodeToPNG()` for smaller frame size
- [ ] Frontend: Handle binary WS messages (Blob/ArrayBuffer → ObjectURL or base64 `<img>`)
- [ ] Frontend: Add virtual camera feed component to CamerasPage
- [ ] Pattern reference: Use `GateCameraSimulator.cs` RenderTexture pattern
- [ ] Pattern reference: Use `CamerasPage.tsx` stream display pattern
- [ ] No new env vars expected for basic implementation (uses existing WS infra)
- [ ] No DB migration required if using existing Camera table with virtual flag
- [ ] Breaking changes from existing code: NONE expected

---

## 8. Nguồn

| #   | Source                                                               | Mô tả                             | Version                          |
| --- | -------------------------------------------------------------------- | --------------------------------- | -------------------------------- |
| 1   | `backend-microservices/realtime-service-go/`                         | Full codebase analysis            | Go 1.22, gorilla/websocket 1.5.3 |
| 2   | `backend-microservices/ai-service-fastapi/app/routers/camera.py`     | Existing MJPEG streaming pattern  | FastAPI/Python                   |
| 3   | `spotlove-ai/src/services/websocket.service.ts`                      | Frontend WS client                | TypeScript/React                 |
| 4   | `spotlove-ai/src/pages/CamerasPage.tsx`                              | Existing camera viewer UI         | TypeScript/React                 |
| 5   | `ParkingSimulatorUnity/Assets/Scripts/Camera/GateCameraSimulator.cs` | Unity RenderTexture capture       | Unity/C#                         |
| 6   | `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs`             | Unity WS client (NativeWebSocket) | Unity/C#                         |
| 7   | `backend-microservices/parking-service/infrastructure/models.py`     | DB schema: Camera, CarSlot        | Django/Python                    |
| 8   | `backend-microservices/booking-service/bookings/models.py`           | DB schema: Booking                | Django/Python                    |
| 9   | `backend-microservices/gateway-service-go/internal/config/config.go` | Gateway routing (no WS proxy)     | Go                               |
