# Research Report: Camera Slot View After Verify Slot

**Task:** Camera Slot View Feature | **Date:** 2026-04-11 | **Type:** Mixed (Codebase + Architecture)

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. Camera snapshot API (`GET /ai/cameras/snapshot?camera_id=xxx`) trả về **raw JPEG binary** (image/jpeg), stream API trả MJPEG multipart — CamerasPage dùng `<img src={streamUrl}>` trực tiếp.
> 2. **Không có Zone→Virtual Camera mapping** ở backend. Virtual cameras chỉ cấu hình vị trí vật lý trong Unity. Slot model (parking-service) có FK `camera` nhưng hiện tại chưa được populate cho virtual cameras.
> 3. **Verify-slot endpoint KHÔNG broadcast WebSocket** — chỉ trả ESP32Response. Cần thêm broadcast `booking.status_update` hoặc event mới sau verify thành công.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File                                                                  | Mục đích                               | Relevance | Có thể tái dụng?                                         |
| --------------------------------------------------------------------- | -------------------------------------- | --------- | -------------------------------------------------------- |
| `ai-service-fastapi/app/routers/camera.py`                            | Camera snapshot/stream/frame endpoints | **High**  | Yes — snapshot/stream endpoints đã hoạt động             |
| `ai-service-fastapi/app/routers/esp32.py` L1276-1420                  | Verify-slot endpoint                   | **High**  | Yes — cần thêm broadcast sau khi verify thành công       |
| `ai-service-fastapi/app/engine/camera_monitor.py`                     | AI slot detection → realtime broadcast | **Med**   | Yes — pattern broadcast slot_status qua realtime-service |
| `spotlove-ai/src/pages/CamerasPage.tsx`                               | Camera feed display (MJPEG stream)     | **High**  | Yes — đã có logic user parking camera                    |
| `spotlove-ai/src/pages/UserDashboard.tsx` L155-165                    | "Xem camera" button                    | **High**  | Yes — cần thay đổi navigate behavior                     |
| `spotlove-ai/src/services/websocket.service.ts`                       | WS message handling                    | **High**  | Yes — đã có `booking.status_update` handler              |
| `spotlove-ai/src/hooks/useWebSocketConnection.ts`                     | WS connection hook                     | **Med**   | Yes — có `subscribeToBooking()`                          |
| `realtime-service-go/internal/handler/broadcast.go`                   | REST→WS broadcast endpoints            | **Med**   | Yes — có `BroadcastBookingUpdate`                        |
| `parking-service/infrastructure/models.py` L101                       | Slot model có FK `camera`              | **Med**   | Yes — slot.camera mapping sẵn có                         |
| `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraManager.cs` | Virtual camera configs (8 cameras)     | **Low**   | No — chỉ tham khảo                                       |

### 2.2 Camera Snapshot/Stream API

**File:** `ai-service-fastapi/app/routers/camera.py`

```
GET /ai/cameras/snapshot?camera_id={id}
  → Response: image/jpeg (raw binary)
  → Virtual cameras: trả từ in-memory buffer (_virtual_frame_buffer)
  → Physical cameras: capture từ RTSP/HTTP stream
  → Stale threshold: 30 giây — trả 503 nếu frame quá cũ

GET /ai/cameras/stream?camera_id={id}&fps={1-30}
  → Response: multipart/x-mixed-replace (MJPEG stream)
  → Browser <img src="..."> tự render liên tục
  → Virtual cameras: poll buffer at fps interval
  → Default fps: 5

GET /ai/cameras/list
  → Response: JSON array of all cameras (physical + virtual)
  → Mỗi camera có: id, name, zone, floor, type, description, snapshotUrl, streamUrl

POST /ai/cameras/frame (Unity → AI service)
  → Header: X-Camera-ID, X-Gateway-Secret
  → Body: raw JPEG bytes
  → Dùng bởi VirtualCameraStreamer từ Unity
```

### 2.3 Virtual Camera IDs và Zone Mapping

**8 virtual cameras** (defined in `camera.py` VIRTUAL_CAMERAS + `VirtualCameraManager.cs` BuildCameraConfigs):

| Camera ID             | Zone (backend) | Unity Position            | Monitors                                   |
| --------------------- | -------------- | ------------------------- | ------------------------------------------ |
| `virtual-f1-overview` | Floor 1        | (0,22,0) top-down 75° FOV | Tổng quan tầng 1 — tất cả ô đỗ             |
| `virtual-f2-overview` | Floor 2        | N/A trong Unity configs   | Tổng quan tầng 2                           |
| `virtual-gate-in`     | Cổng vào       | (36,3.5,-4)               | Cổng vào — xe check-in                     |
| `virtual-gate-out`    | Cổng ra        | (-36,3.5,-4)              | Cổng ra — xe check-out                     |
| `virtual-zone-south`  | South          | (0,12,-20) 40° tilt       | South car rows: V1-01..V1-18, V1-37..V1-54 |
| `virtual-zone-north`  | North          | (0,12,20) 40° down 180°   | North car rows: V1-19..V1-36, V1-55..V1-72 |
| `virtual-anpr-entry`  | Cổng vào       | (43.5,1,0) 35° FOV        | ANPR cổng vào — đọc biển số                |
| `virtual-anpr-exit`   | Cổng ra        | (-42,0.4,0) 25° FOV       | ANPR cổng ra — đọc biển số                 |

**⚠️ QUAN TRỌNG:** `VirtualCameraConfig.monitoredSlotCodes` luôn là `new string[0]` — **KHÔNG có slot-level camera mapping** trong Unity. Tất cả cameras đều là zone-level overview.

**2 physical cameras** (from env):

| Camera ID            | Zone     | Type         |
| -------------------- | -------- | ------------ |
| `plate-camera-ezviz` | Cổng vào | plate (RTSP) |
| `qr-camera-droidcam` | Cổng vào | qr (HTTP)    |

### 2.4 Parking-Service Slot → Camera FK

```python
# parking-service/infrastructure/models.py L101
camera = models.ForeignKey('Camera', on_delete=models.SET_NULL, null=True, blank=True, related_name='monitored_slots')
```

- Mỗi `Slot` có thể trỏ đến 1 `Camera` object
- Hiện tại **chưa rõ** Camera table có chứa virtual camera IDs không (cần verify DB)
- Frontend `ParkingSlot` interface đã có `cameraId?: string` field

### 2.5 CamerasPage — User Parking Camera Logic

```typescript
// CamerasPage.tsx L230-265: Regular user flow
const parking = await bookingApi.getCurrentParking();
const mapped = mapBookingResponse(parking.booking);
const slotId = mapped.slotId;

// Try to get camera from slot
if (slotId) {
  const slotData = await parkingApi.getSlot(slotId);
  if (slotData.cameraId) {
    cameraId = slotData.cameraId; // ← use slot's FK camera
  }
}

// Fallback: generate fake camera ID from zone
if (!cameraId) {
  cameraId = `camera-zone-${mapped.zoneId || "unknown"}`;
}
```

**Vấn đề:** Nếu `slotData.cameraId` không khớp với bất kỳ virtual camera ID nào trong `MONITORING_CAMERAS`, camera card sẽ **không có streamUrl** → hiển thị placeholder.

### 2.6 "Xem camera" Button — UserDashboard

```typescript
// UserDashboard.tsx L155-160
<Button
  variant="outline"
  className="flex-1"
  size="sm"
  onClick={() => navigate("/cameras")}
>
  Xem camera
</Button>
```

**Hiện tại chỉ navigate sang `/cameras`** — không truyền context nào (booking ID, slot code, zone, camera ID). CamerasPage phải tự fetch lại từ `getCurrentParking()`.

---

## 3. WebSocket Events — Realtime Service

### 3.1 Architecture

```
Backend service → POST /api/broadcast/* → realtime-service-go → WebSocket → Frontend
```

**Groups:**

- `parking_updates` — tất cả clients (parking ws + user ws đều join)
- `user_{userId}` — per-user channel

### 3.2 Available Broadcast Endpoints

| Endpoint                                 | WS Event Type                          | Group           | Used By                          |
| ---------------------------------------- | -------------------------------------- | --------------- | -------------------------------- |
| `POST /api/broadcast/slot-status/`       | `slot.status_update`                   | parking_updates | camera_monitor.py (AI detection) |
| `POST /api/broadcast/zone-availability/` | `zone.availability_update`             | parking_updates | parking-service                  |
| `POST /api/broadcast/lot-availability/`  | `lot.availability_update`              | parking_updates | parking-service                  |
| `POST /api/broadcast/booking-update/`    | `booking.status_update` (configurable) | user\_{userId}  | booking-service                  |
| `POST /api/broadcast/notification/`      | `notification`                         | user\_{userId}  | notification-service             |
| `POST /api/broadcast/camera-status/`     | `camera.slot_detection`                | parking_updates | AI camera monitor                |
| `POST /api/broadcast/unity-command/`     | `unity.command`                        | parking_updates | check-in flow                    |

### 3.3 Frontend WS Message Handlers

```typescript
// websocket.service.ts — processMessage()
case "slot.status_update":     → updateSlotStatus(data)
case "zone.availability_update": → updateZoneAvailability(data)
case "booking.status_update":  → updateBookingStatus(data)
case "booking.created":        → addNewBooking(data)
case "notification":           → addNotification(data)
// ❌ Không có handler cho "slot.verified" hoặc "verify_slot"
```

### 3.4 ⚠️ Verify-Slot KHÔNG Broadcast

```python
# esp32.py L1279-1420: esp32_verify_slot()
# Chỉ return ESP32Response — KHÔNG gọi realtime-service broadcast
return ESP32Response(
    success=True,
    event=GateEvent.VERIFY_SLOT_SUCCESS,
    ...
)
# ← THIẾU: broadcast booking.status_update hoặc event mới
```

**So sánh với check-in flow:**

- Check-in endpoint **CÓ** broadcast `unity.spawn_vehicle` command
- Verify-slot **KHÔNG** broadcast bất kỳ WS event nào

---

## 4. CamerasPage Display Pattern

### 4.1 Stream Display

CamerasPage dùng **MJPEG streaming** (KHÔNG phải polling snapshot):

```tsx
// CamerasPage.tsx L579-585
<img
  src={displayUrl} // e.g. "/ai/cameras/stream?camera_id=virtual-zone-south&fps=5"
  alt={`Live feed: ${camera.name}`}
  className="absolute inset-0 w-full h-full object-cover"
  onError={() => handleStreamError(camera.id)}
/>
```

### 4.2 Stream URL Resolution

```typescript
// getDisplayStreamUrl():
// Already proxied (/ai/cameras/...): use as-is
// RTSP: proxy through /ai/cameras/stream?url=...&fps=3
// HTTP: use directly
```

### 4.3 Fullscreen Modal

CamerasPage có Dialog fullscreen khi click camera card:

- Zoom in/out controls
- Vehicle tracking info (if user vehicle)
- Request fullscreen browser API

### 4.4 Hardcoded MONITORING_CAMERAS

```typescript
const MONITORING_CAMERAS: CameraFeed[] = [
  {
    id: "plate-camera-ezviz",
    streamUrl: "/ai/cameras/stream?camera_id=plate-camera-ezviz&fps=3",
  },
  {
    id: "qr-camera-droidcam",
    streamUrl: "/ai/cameras/stream?camera_id=qr-camera-droidcam&fps=3",
  },
  {
    id: "virtual-gate-in",
    streamUrl: "/ai/cameras/stream?camera_id=virtual-gate-in&fps=5",
  },
  {
    id: "virtual-gate-out",
    streamUrl: "/ai/cameras/stream?camera_id=virtual-gate-out&fps=5",
  },
  {
    id: "virtual-f1-overview",
    streamUrl: "/ai/cameras/stream?camera_id=virtual-f1-overview&fps=5",
  },
  {
    id: "virtual-f2-overview",
    streamUrl: "/ai/cameras/stream?camera_id=virtual-f2-overview&fps=5",
  },
];
// ❌ THIẾU: virtual-zone-south và virtual-zone-north
```

---

## 5. ⚠️ Gotchas & Known Issues

- [ ] **[GAP]** Verify-slot endpoint **KHÔNG** broadcast WS event → frontend không biết slot đã verified
- [ ] **[GAP]** Không có Zone/Slot → Virtual Camera mapping ở backend. Slot model có FK `camera` nhưng virtual cameras (Unity) không nằm trong parking-service Camera table
- [ ] **[GAP]** `MONITORING_CAMERAS` hardcoded thiếu `virtual-zone-south` và `virtual-zone-north` — 2 camera quan trọng nhất cho giám sát slot
- [ ] **[GAP]** "Xem camera" button chỉ navigate `/cameras` — không truyền context để auto-select đúng camera/slot
- [ ] **[GAP]** CamerasPage user flow: Nếu `slotData.cameraId` trả về string không khớp MONITORING_CAMERAS, camera card hiển thị **không có stream** (streamUrl undefined)
- [ ] **[NOTE]** Virtual camera frames stale sau 30s nếu Unity không chạy → stream trả 503

---

## 6. So Sánh Phương Án: Show Slot Camera After Verify

| Tiêu chí        | Option A: Zone Camera Mapping                                           | Option B: Slot-specific Camera                           | Option C: Camera List + Auto-select  |
| --------------- | ----------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------ |
| Approach        | Map zone name → virtual camera ID (e.g. "South" → "virtual-zone-south") | Slot.camera FK → virtual camera ID                       | Fetch `/ai/cameras/list`, match zone |
| Backend change  | None — mapping in frontend                                              | Need: populate Slot.camera FK hoặc thêm API              | None — dùng existing API             |
| Frontend change | Thêm ZONE_CAMERA_MAP, "Xem camera" truyền camera_id                     | Dùng slotData.cameraId nếu populated                     | Fetch camera list, filter by zone    |
| Accuracy        | Zone-level (nhiều slot share 1 camera)                                  | Slot-level (ideal, nhưng virtual cameras chỉ zone-level) | Zone-level                           |
| Complexity      | **Low**                                                                 | **Med-High**                                             | **Med**                              |
| Slot-level view | ❌ Không — virtual cameras chỉ zone overview                            | ❌ Giống A do virtual cameras không per-slot             | ❌ Giống A                           |

**Note:** Đây là facts. Architect quyết định approach.

### Possible Zone → Camera Mapping (nếu chọn Option A):

```typescript
const ZONE_CAMERA_MAP: Record<string, string> = {
  // Zone name/ID patterns → virtual camera IDs
  South: "virtual-zone-south",
  North: "virtual-zone-north",
  "Floor 1": "virtual-f1-overview",
  "Floor 2": "virtual-f2-overview",
  // Gate cameras
  "Cổng vào": "virtual-gate-in",
  "Cổng ra": "virtual-gate-out",
};
```

---

## 7. Recommended Changes (Facts for Architect)

### Backend (ai-service-fastapi)

1. **Verify-slot endpoint cần broadcast WS event** sau khi verify thành công:
   ```python
   # Sau ESP32Response success → POST realtime-service
   POST /api/broadcast/booking-update/
   {
     "user_id": user_id,
     "type": "booking.slot_verified",
     "data": {
       "booking_id": booking_id,
       "slot_code": slot_code,
       "zone_id": zone_id,
       "camera_id": "virtual-zone-south"  // resolved from zone mapping
     }
   }
   ```

### Frontend (spotlove-ai)

2. **Thêm `virtual-zone-south` + `virtual-zone-north` vào MONITORING_CAMERAS** (hiện thiếu)
3. **"Xem camera" button**: navigate với query param `/cameras?camera_id=virtual-zone-south` hoặc dùng state
4. **WebSocket handler**: Thêm case `"booking.slot_verified"` → auto-navigate/show camera dialog
5. **Zone→Camera mapping**: frontend utility map zone name/ID → virtual camera ID

---

## 8. Checklist cho Implementer

- [ ] Backend: Thêm realtime broadcast trong `esp32_verify_slot()` sau success
- [ ] Backend: Cân nhắc thêm `virtual-zone-south` và `virtual-zone-north` vào response data
- [ ] Frontend: Thêm 2 missing cameras vào `MONITORING_CAMERAS` list
- [ ] Frontend: Tạo `ZONE_CAMERA_MAP` utility
- [ ] Frontend: Sửa "Xem camera" button truyền camera context
- [ ] Frontend: Thêm WS handler cho slot_verified event (nếu thêm event mới)
- [ ] Frontend: CamerasPage auto-select camera khi navigate với query param
- [ ] Không cần migration — Slot.camera FK đã có sẵn
- [ ] Không cần install thêm packages

---

## 9. Nguồn

| #   | File/Location                                                         | Mô tả                                       | Relevance |
| --- | --------------------------------------------------------------------- | ------------------------------------------- | --------- |
| 1   | `ai-service-fastapi/app/routers/camera.py`                            | Camera API (snapshot/stream/list/frame)     | Primary   |
| 2   | `ai-service-fastapi/app/routers/esp32.py` L1276-1420                  | Verify-slot endpoint                        | Primary   |
| 3   | `spotlove-ai/src/pages/CamerasPage.tsx`                               | Camera feed display page                    | Primary   |
| 4   | `spotlove-ai/src/pages/UserDashboard.tsx` L155-165                    | "Xem camera" button                         | Primary   |
| 5   | `spotlove-ai/src/services/websocket.service.ts`                       | WS message types & handlers                 | Primary   |
| 6   | `spotlove-ai/src/hooks/useWebSocketConnection.ts`                     | WS hook with subscription helpers           | Secondary |
| 7   | `realtime-service-go/internal/handler/broadcast.go`                   | Broadcast REST endpoints                    | Primary   |
| 8   | `realtime-service-go/internal/hub/hub.go`                             | Hub group/broadcast logic                   | Secondary |
| 9   | `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraManager.cs` | Virtual camera configs (8 cameras)          | Reference |
| 10  | `ParkingSimulatorUnity/Assets/Scripts/Camera/IVirtualCamera.cs`       | VirtualCameraConfig struct                  | Reference |
| 11  | `parking-service/infrastructure/models.py` L101                       | Slot.camera FK                              | Secondary |
| 12  | `spotlove-ai/src/store/slices/parkingSlice.ts` L10-35                 | ParkingSlot interface (has cameraId)        | Secondary |
| 13  | `ai-service-fastapi/app/engine/camera_monitor.py` L230-250            | Pattern: broadcast slot_status via realtime | Reference |
