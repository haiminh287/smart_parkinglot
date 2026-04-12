# Code Review Report — Virtual Camera System

**Score: 5.5/10** | **Verdict: Request Changes**
**Date:** 2026-04-01 | Files reviewed: 11

---

## Summary

|               | Count        |
| ------------- | ------------ |
| 🚨 Critical   | 1            |
| ⚠️ Major      | 1            |
| 💡 Minor      | 5            |
| 🗑️ Dead Code  | 3 items      |
| 🏗️ Arch Drift | 0 violations |

---

## 🚨 Critical Issues (PHẢI fix trước merge)

### [CRIT-1] PostSlotDetection missing X-Gateway-Secret header → always 403

- **File:** `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs:425-444`
- **Category:** Security / Auth
- **Problem:** `PostSlotDetection` gọi đến realtime-service-go endpoint `/api/broadcast/camera-status/` mà KHÔNG set `X-Gateway-Secret` header. Endpoint này được bảo vệ bởi `InternalAuthMiddleware` (xem `realtime-service-go/internal/middleware/internal_auth.go`) → mọi request đều bị 403 Forbidden.
- **Impact:** Toàn bộ tính năng slot occupancy broadcast (SlotOccupancyDetector → realtime → frontend) hoàn toàn không hoạt động. Frontend sẽ không bao giờ nhận được camera detection events.
- **Fix:**

  ```csharp
  // Thay (line 435-436):
  req.SetRequestHeader("Content-Type", "application/json");

  // Bằng:
  req.SetRequestHeader("Content-Type", "application/json");
  req.SetRequestHeader("X-Gateway-Secret", config.gatewaySecret);
  ```

---

## ⚠️ Major Issues

### [MAJ-1] PostSlotDetection URL missing `/api/` prefix → always 404

- **File:** `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs:427`
- **Problem:** URL construction tạo path `http://localhost:8006/broadcast/camera-status/` nhưng Go route nằm dưới group `/api/broadcast` → đúng phải là `http://localhost:8006/api/broadcast/camera-status/`.

  Current code:

  ```csharp
  string url = $"{config.realtimeWsUrl.Replace("ws://", "http://").Replace("/ws/parking", "")}/broadcast/camera-status/";
  ```

  `realtimeWsUrl = "ws://localhost:8006/ws/parking"` → after replace → `http://localhost:8006` → append → `http://localhost:8006/broadcast/camera-status/`

  But Go route (main.go:65): `broadcast := r.Group("/api/broadcast")` → actual path = `/api/broadcast/camera-status/`

- **Impact:** Kể cả nếu fix CRIT-1, request vẫn 404 vì sai path. Slot detection broadcast hoàn toàn bất khả dụng.
- **Fix:**

  ```csharp
  // Thay:
  string url = $"{config.realtimeWsUrl.Replace("ws://", "http://").Replace("/ws/parking", "")}/broadcast/camera-status/";

  // Bằng:
  string url = $"{config.realtimeWsUrl.Replace("ws://", "http://").Replace("/ws/parking", "")}/api/broadcast/camera-status/";
  ```

---

## 💡 Minor Issues

- **[MIN-1]** `VirtualCameraStreamer.cs:155` — `framesSent++` trước khi SendFrame xác nhận thành công → metric không chính xác. Nên move vào SendFrame callback khi `success == true`.

- **[MIN-2]** `VirtualCameraManager.cs:140-175` (BuildCameraMesh) — Tạo 4 `new Material(shader)` per camera (x4 cameras = 16 materials). Các materials không được Destroy trong `ShutdownCameras()`. Unity sẽ không auto-gc materials → memory leak nhỏ qua nhiều init/shutdown cycles.
  - **Fix:** Track materials trong list, Destroy trong ShutdownCameras.

- **[MIN-3]** `VirtualCameraStreamer.cs:200-204` — `MAX_CONSECUTIVE_ERRORS` chỉ log warning mà không thực hiện backoff hay stop streaming. Camera tiếp tục gửi frame vào endpoint chết, lãng phí bandwidth/CPU.
  - **Suggestion:** Sau MAX_CONSECUTIVE_ERRORS, tăng interval (exponential backoff) hoặc pause + retry sau 30s.

- **[MIN-4]** `ApiService.cs:427` — URL construction dùng string `.Replace("ws://", "http://")` nhưng không handle trường hợp `wss://` (production sẽ dùng TLS). Nếu `realtimeWsUrl = "wss://..."` → URL thành `wss://` không bị replace → sai protocol.
  - **Fix:** Thêm `.Replace("wss://", "https://")`.

- **[MIN-5]** `VirtualCameraConfig.monitoredSlotCodes` — field tồn tại trong config nhưng luôn set empty array `new string[0]`. `AssignSlotsToCamera` cho phép link slot→camera nhưng không bao giờ được gọi. Feature wired nhưng incomplete.

---

## 🗑️ Dead Code Found

| File                       | Location                                  | Type                                                  | Action                                     |
| -------------------------- | ----------------------------------------- | ----------------------------------------------------- | ------------------------------------------ |
| `SlotOccupancyDetector.cs` | `AssignSlotsToCamera()` (line 63)         | Public method never called                            | Keep (public API for future use) or remove |
| `VirtualCameraManager.cs`  | `GetStreamer()` (line 63)                 | Public method never called                            | Keep (public API) or remove                |
| `VirtualCameraManager.cs`  | `ShutdownCameras()`, `GetCameraConfigs()` | Implementation of IVirtualCameraManager, never called | Keep (interface contract)                  |

**Total: 3 items → Cleanup task needed: no** (all are public interface methods that may be called by future consumers; acceptable to keep)

---

## 🏗️ Architecture Compliance

- ✅ **ADR**: No violations — follows existing patterns (singleton MonoBehaviour, coroutine-based HTTP)
- ✅ **API contract**: PostCameraFrame correctly targets `/ai/cameras/frame` with proper headers
- ✅ **Naming conventions**: Consistent camelCase, clear prefixes for tags `[VirtualCamera]`, `[SlotDetector]`
- ✅ **Layer separation**: Camera module in own namespace, uses ApiService for HTTP, no direct backend access
- ✅ **Dependency direction**: Camera → API (correct), Core → Camera (via serialized references)
- ✅ **Interface compliance**: VirtualCameraStreamer implements IVirtualCameraStreamer, VirtualCameraManager implements IVirtualCameraManager, SlotOccupancyDetector implements ISlotOccupancyDetector
- ❌ **PostSlotDetection auth**: Missing X-Gateway-Secret violates auth strategy (Hybrid Auth → internal calls require X-Gateway-Secret)

---

## Checklist Verdict

| Checklist Item  | Verdict | Notes                                                                            |
| --------------- | ------- | -------------------------------------------------------------------------------- |
| Correctness     | ❌ FAIL | CRIT-1 + MAJ-1: slot broadcast completely broken                                 |
| Security        | ❌ FAIL | Missing auth header on internal service call                                     |
| Performance     | ✅ PASS | RenderTexture lifecycle managed; JPEG encoding correct; frame pacing appropriate |
| Maintainability | ✅ PASS | Clean structure, separated concerns, good naming                                 |
| Architecture    | ✅ PASS | Follows established patterns, no drift                                           |
| Dead code       | ✅ PASS | Only interface stubs remain; no approach-drift artifacts                         |
| Error handling  | ✅ PASS | Consecutive error tracking, null checks, graceful degradation                    |

---

## ✨ Positive Highlights

- **Well-structured Python endpoint**: camera.py has proper validation (body size limit, camera ID whitelist, stale frame threshold), thread-safe buffer with lock, clean async MJPEG generator
- **Clean Go handler**: BroadcastCameraStatus validates input, properly typed struct binding
- **Good Unity patterns**: RenderTexture properly released in OnDestroy; coroutines correctly stop on disable; VirtualCameraStreamer respects Application.isFocused to pause streaming
- **IVirtualCamera interfaces**: Clean separation of contract (architect phase) from implementation
- **SceneBootstrapper integration**: Camera system wired correctly as children of ParkingManager, proper serialized field injection

---

## 📋 Action Items (ordered)

1. **[CRIT-1]** Add `X-Gateway-Secret` header to `PostSlotDetection` (ApiService.cs:435)
2. **[MAJ-1]** Fix URL prefix: `/broadcast/` → `/api/broadcast/` in `PostSlotDetection` (ApiService.cs:427)
3. **[MIN-4]** Handle `wss://` → `https://` in URL construction (ApiService.cs:427)
4. (Optional) **[MIN-1]** Move `framesSent++` into success callback
5. (Optional) **[MIN-3]** Add backoff/pause after MAX_CONSECUTIVE_ERRORS
6. (Optional) **[MIN-2]** Track + destroy materials in ShutdownCameras

---

## Score Breakdown

```
Baseline:                 8.0
Critical × 1:           -2.0
Major × 1:              -1.0
Minor (5 items, 1 set): -0.5
Dead code (3, < 5):      0.0
Arch drift:               0.0
                         ────
Total:                    4.5 → clamped to 4.5

Bonus: Clean Python/Go code, good Unity patterns: +1.0
                         ────
Final:                    5.5/10
```
