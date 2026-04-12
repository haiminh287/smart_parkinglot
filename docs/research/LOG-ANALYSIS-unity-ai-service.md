# Research Report: Comprehensive Log Analysis — Unity Editor + AI Service

**Task:** Log Analysis | **Date:** 2026-04-05 | **Type:** Mixed (Codebase + Runtime)

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Camera streaming 100% failed khi AI service không chạy** — 3,743 PostCameraFrame failures (HTTP 0) + 706 Curl errors to port 8009. Khi AI service chạy → tất cả 200 OK.
> 2. **Slot detection broadcast 100% failed (404)** — Unity gọi realtime-service-go tại `/api/broadcast/camera-status/` nhưng service trả 404 → realtime-service-go chưa chạy hoặc route bị sai.
> 3. **Navigation graph bị đứt** — Node 16 không có path đến 15 target nodes (54,58,62,68,92-94,117,120,122,126,145,150,153,154) → vehicles bị kẹt.

---

## 2. Log Overview

| Metric                     | Value                                     |
| -------------------------- | ----------------------------------------- |
| Unity Editor log           | 105,337 lines (~6.3 MB)                   |
| Log session start          | 2026-04-05T01:15:03Z                      |
| Log last modified          | 2026-04-05 10:37:22                       |
| AI service err log         | 20 lines (Pydantic warnings only)         |
| AI service out log         | 3 lines (health check + detect-occupancy) |
| AI service (live terminal) | Running, all requests 200 OK              |

---

## 3. Critical Issues (Blocking Functionality)

### CRIT-1: PostCameraFrame fails when AI service is down (3,743 failures)

| Detail        | Value                                                             |
| ------------- | ----------------------------------------------------------------- |
| Error message | `[ApiService] PostCameraFrame {cameraId} failed: 0`               |
| HTTP status   | 0 (connection refused)                                            |
| Count         | 3,743 total across 6 cameras                                      |
| Root cause    | AI service (port 8009) was not running during Unity play sessions |
| First failure | Line 3057                                                         |
| Last failure  | Line 101584                                                       |
| Curl errors   | 706 "Curl error 7: Failed to connect to localhost port 8009"      |

**Cross-correlation:** Khi AI service đang chạy (terminal output), tất cả requests đều 200 OK:

```
POST /ai/cameras/frame → 200 OK (tất cả 6 cameras)
GET /ai/cameras/snapshot → 200 OK
POST /ai/parking/detect-occupancy/ → 200 OK
```

**Impact:** Camera frames không được gửi → frontend camera viewer không hiển thị gì → slot AI detection không hoạt động.

**Recommendation:**

- Unity đã có backoff logic (30s sau 5 failures) → ✅ tốt
- Cần đảm bảo AI service luôn chạy trước khi start Unity Play mode
- Có thể thêm health check indicator trong Unity UI

---

### CRIT-2: PostSlotDetection → 404 (Realtime service issue)

| Detail           | Value                                                              |
| ---------------- | ------------------------------------------------------------------ |
| Error message    | `[ApiService] PostSlotDetection {cameraId} failed: 404`            |
| Target URL       | `http://localhost:8006/api/broadcast/camera-status/`               |
| Affected cameras | virtual-f2-overview, virtual-zone-north, virtual-zone-south        |
| Count            | 6 failures                                                         |
| Follow-up        | `[SlotDetector] Broadcast failed for camera {cameraId}` (6 events) |

**Root cause:** Unity gọi **realtime-service-go** (port 8006) tại endpoint `/api/broadcast/camera-status/`. Service trả 404 → hoặc:

1. realtime-service-go không chạy
2. Route `/api/broadcast/camera-status/` chưa được register đúng

**Code trace (Unity):**

```csharp
// ApiService.cs:451
string url = $"{config.realtimeWsUrl.Replace("ws://", "http://").Replace("/ws/parking", "")}/api/broadcast/camera-status/";
// realtimeWsUrl = "ws://localhost:8006/ws/parking"
// → URL = "http://localhost:8006/api/broadcast/camera-status/"
```

**Impact:** Slot occupancy changes không broadcast real-time → frontend dashboard không cập nhật live.

---

### CRIT-3: Gate plate scan always fails (HTTP 0)

| Detail          | Value                                                |
| --------------- | ---------------------------------------------------- |
| Error message   | `[ParkingManager] ℹ️ Gate plate scan failed: HTTP 0` |
| Count           | 15 failures                                          |
| Line range      | L89810 – L93279                                      |
| Target endpoint | `ai/parking/scan-plate/` on AI service               |

**Root cause:** HTTP 0 = connection refused. AI service không chạy tại thời điểm gate scan. Nghĩa là khi vehicles đến gate, AI không available để recognize plate → gate không mở.

**Impact:** Check-in/check-out flow bị block hoàn toàn khi AI service down.

---

### CRIT-4: WaypointGraph disconnected — Node 16 unreachable to 15 targets

| Detail              | Value                                                              |
| ------------------- | ------------------------------------------------------------------ |
| Error message       | `[WaypointGraph] No path found from node 16 to {target}`           |
| Source node         | Always node 16                                                     |
| Unreachable targets | 54, 58, 62, 68, 92, 93, 94, 117, 120, 122, 126, 145, 150, 153, 154 |
| Total path failures | 30 (15 unique node pairs × ~2 attempts)                            |
| Follow-up           | `[VehicleController] No path found!`                               |

**Root cause:** WaypointGraph BFS từ node 16 không tìm được đường tới nhiều slot nodes. Có thể:

1. Node 16 bị thiếu edge connections (waypoint scene data bị đứt)
2. Floor 2 nodes chưa được link qua ramp/elevator node
3. Procedural generation tạo nodes nhưng chưa connect full graph

**Impact:** Vehicles được assign slot nhưng không di chuyển được → stuck forever.

---

## 4. Warnings (Non-blocking nhưng cần fix)

### WARN-1: AI endpoint not yet connected — 1,295 messages

```
[SlotDetector/AI] AI snapshots captured (e.g. virtual-f1-overview 31518 bytes) — AI endpoint not yet connected
```

SlotOccupancyDetector chụp AI snapshots mỗi cycle nhưng không gửi được vì AI service down. Snapshots bị discard.

**Recommendation:** Khi AI service offline, có thể giảm snapshot frequency hoặc cache snapshots.

---

### WARN-2: Pydantic protected namespace warnings (AI service)

```
Field "model_version" in LicensePlateResponse has conflict with protected namespace "model_".
Field "model_version" in CashRecognitionResponse has conflict with protected namespace "model_".
Field "model_version" in PredictionLogResponse has conflict with protected namespace "model_".
Field "model_type" in ModelVersionResponse has conflict with protected namespace "model_".
```

**Fix:** Thêm `model_config['protected_namespaces'] = ()` vào các Pydantic models hoặc rename fields.

---

### WARN-3: Backoff events — 282 across 6 cameras

```
[VirtualCamera] virtual-{id}: 5 consecutive send failures — backing off 30s
```

Backoff logic hoạt động đúng, nhưng 282 backoff events nghĩa là ~47 cycles mỗi camera bị skip 30s → khá nhiều downtime.

---

### WARN-4: Unauthorized parking detected

```
[SlotDetector] UNAUTHORIZED: SIM-C-12 parked at V2-11 with no booking
[SlotDetector] UNAUTHORIZED: SIM-C-12 parked at C-11 with no booking
```

Vehicle SIM-C-12 park tại 2 slots mà không có booking. Đây là static vehicles từ ParkingManager init (prefix `SIM-`). Có thể bỏ qua nếu intentional cho testing, nhưng sẽ trigger unnecessary alerts.

---

### WARN-5: Unity Licensing validation failed

```
[Licensing::Module] LicensingClient has failed validation; ignoring
```

Unity license client connect rồi fail validation. Non-blocking nhưng có thể affect Unity Hub integration.

---

## 5. Info (Cosmetic / Low-priority)

### INFO-1: Curl error to Unity cloud (port 443)

```
Curl error 7: Failed to connect to config.uca.cloud.unity3d.com port 443
```

1 error duy nhất. Đây là Unity Analytics/Cloud config check — fail khi offline. Không ảnh hưởng ParkSmart.

---

### INFO-2: Camera frame sizes stable

AI snapshot sizes tăng dần từ ~27KB → ~31KB khi vehicles fill parking lot. Kích thước ổn định, không có spike bất thường.

---

### INFO-3: Detection pass ổn định

```
[SlotDetector] Detection pass: 41/158 occupied, 41 changed  (first pass)
[SlotDetector] Detection pass: 41/158 occupied, 0 changed   (subsequent — stable)
```

Physics-based slot detection hoạt động đúng: 41/158 slots occupied, stabilize sau pass đầu.

---

## 6. Subsystem Status

| Subsystem                    | Status                   | Detail                                                                                                      |
| ---------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------- |
| **Camera Streaming**         | ⚠️ DEPENDS ON AI SERVICE | 6 cameras init OK, 640x480 @ 5fps. 440-443 frames sent per session khi AI chạy. 3,743 failures khi AI down. |
| **Slot Detection (Physics)** | ✅ WORKING               | 41/158 occupied detected correctly. OverlapBox detection stable.                                            |
| **Slot Detection (AI)**      | ❌ NOT CONNECTED         | 1,295 "AI endpoint not yet connected" — AI occupancy detection chưa bao giờ chạy thành công từ Unity side   |
| **Slot Broadcast**           | ❌ FAILED (404)          | realtime-service-go endpoint returns 404                                                                    |
| **Vehicle Movement**         | ⚠️ PARTIAL               | 30+ vehicles spawned successfully. 15 path failures từ node 16 → vehicles stuck                             |
| **License Plates**           | ✅ ASSIGNED              | Plates assigned correctly (VN format: "29AR-331.81", "51AA-291.76" etc.)                                    |
| **Gate Plate Scan**          | ❌ FAILED                | 15/15 gate scans failed (AI service down). Endpoint `/ai/parking/scan-plate/` correct.                      |
| **API Connectivity**         | ⚠️ AI-DEPENDENT          | 706 Curl errors to port 8009. When AI service running → all 200 OK                                          |
| **WebSocket**                | ❓ NO DATA               | No WS connect/disconnect logs found in this session                                                         |
| **Compile Status**           | ✅ CLEAN                 | 0 compile errors (CS errors)                                                                                |
| **Runtime Exceptions**       | ✅ CLEAN                 | 0 NullReferenceException, MissingReferenceException, etc.                                                   |

---

## 7. Cross-Correlation: Unity ↔ AI Service

### Timeline Reconstruction

```
L1-377:     Unity starts, licensing check
L378:       First Curl error (cloud.unity3d.com:443 — unrelated)
L622:       ParkingManager init → 25 static vehicles placed
L1063-1225: 6 VirtualCameras initialized + streaming started
L3057+:     PostCameraFrame failures begin (AI service not running)
L3000+:     SlotDetector detects 41/158 occupied (physics works)
L3000+:     PostSlotDetection 404 (realtime-service-go not running)
L3000-77K:  Continuous PostCameraFrame failures + backoff cycles
L13917:     First "No path found" from node 16
L77587:     Camera streaming stopped (440-443 frames — from earlier OK session)
L78336:     Scene reload → cameras re-initialized, streaming restarted
L89810+:    Gate plate scan failures (15 total)
L101584:    Last PostCameraFrame failure
L104946:    VirtualCameraStreamer.cs reimported (code change mid-session)
```

### Key Insight

Có 2 play sessions trong log:

1. **Session 1 (L1-77K):** Cameras worked initially (440+ frames sent), then failures accumulated
2. **Session 2 (L78K-105K):** Cameras re-initialized, but AI service still down → all failures

AI service terminal shows: khi service chạy, Unity requests đều 200 OK. Vấn đề 100% do **startup ordering** — AI service phải chạy trước Unity Play.

---

## 8. Recommendations

### Immediate Fixes (Priority 1)

| #   | Issue                  | Fix                                                                                                             | Owner              |
| --- | ---------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------ |
| 1   | AI service not running | **Startup script** hoặc Unity UI indicator "AI Service: Connected/Disconnected"                                 | Implementer        |
| 2   | PostSlotDetection 404  | Verify realtime-service-go is running + route `/api/broadcast/camera-status/` exists                            | Implementer/DevOps |
| 3   | Node 16 disconnected   | Audit WaypointGraph — ensure node 16 has edges to reach all target zones. Check if Floor 2 ramp node connected. | Implementer        |

### Short-term Fixes (Priority 2)

| #   | Issue                                            | Fix                                                                      | Owner                 |
| --- | ------------------------------------------------ | ------------------------------------------------------------------------ | --------------------- |
| 4   | Pydantic warnings                                | Set `model_config['protected_namespaces'] = ()` trên 4 response models   | Implementer           |
| 5   | Unauthorized parking alerts from static vehicles | Exclude `SIM-*` plates from unauthorized check hoặc assign mock bookings | Implementer           |
| 6   | Gate scan offline resilience                     | Queue gate scan requests + retry khi AI service reconnects               | Architect/Implementer |

### Long-term (Priority 3)

| #   | Issue              | Fix                                                                                          | Owner       |
| --- | ------------------ | -------------------------------------------------------------------------------------------- | ----------- |
| 7   | Service dependency | Health check dashboard in Unity showing status of AI (8009), Realtime (8006), Gateway (8001) | Architect   |
| 8   | Camera frame waste | Cache last successful frame for snapshot API khi streaming fails                             | Implementer |

---

## 9. Nguồn

| #   | Source                                          | Mô tả                                                 | Date             |
| --- | ----------------------------------------------- | ----------------------------------------------------- | ---------------- |
| 1   | `$LOCALAPPDATA\Unity\Editor\Editor.log`         | Unity Editor log, 105K lines                          | 2026-04-05       |
| 2   | Terminal ID 5c95d0b6-... (AI Service)           | Live uvicorn output, all 200 OK                       | 2026-04-05       |
| 3   | `ai-service-fastapi/logs/uvicorn-local.err.log` | Pydantic warnings (20 lines)                          | Previous session |
| 4   | `ai-service-fastapi/logs/uvicorn-local.out.log` | 3 request logs                                        | Previous session |
| 5   | `ApiService.cs` (line 449-470)                  | PostSlotDetection → realtime-service URL construction | Codebase         |
| 6   | `ParkingManager.cs` (line 315-345)              | Gate plate scan flow → AIRecognizePlate               | Codebase         |
