# Code Review Report — 6 Production Readiness Improvements

**Score: 4.5/10** | **Verdict: Request Changes**
**Date:** 2026-03-27 | Files reviewed: 12

---

## Summary

|               | Count          |
| ------------- | -------------- |
| 🚨 Critical   | 1              |
| ⚠️ Major      | 1              |
| 💡 Minor      | 6              |
| 🗑️ Dead Code  | 6 items        |
| 🏗️ Arch Drift | 1 violation    |

---

## 🚨 Critical Issues (PHẢI fix trước merge)

### [CRIT-1] RTSP camera credentials hardcoded in source defaults

- **Files:**
  - `backend-microservices/ai-service-fastapi/app/config.py:27`
  - `backend-microservices/ai-service-fastapi/.env.example:42`
  - `backend-microservices/docker-compose.yml:337`
- **Category:** Security — Hardcoded Credentials
- **Problem:** RTSP URL default contains real camera credentials (`admin:XGIMBN`):
  ```python
  CAMERA_RTSP_URL: str = "rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main"
  ```
  This violates the explicit standard: *"KHÔNG hardcode secrets, keys, tokens — dùng env vars"*. The password is committed to git in three locations.
- **Impact:** Anyone with repo access obtains the camera password. If camera is internet-accessible or repo becomes public, credentials are exposed.
- **Fix:**
  ```python
  # config.py — Replace with:
  CAMERA_RTSP_URL: str = ""  # Set via env: rtsp://user:pass@host:554/path

  # .env.example — Replace with:
  CAMERA_RTSP_URL=rtsp://user:password@camera-ip:554/ch1/main

  # docker-compose.yml — Replace with:
  - CAMERA_RTSP_URL=${CAMERA_RTSP_URL:-}
  ```

---

## ⚠️ Major Issues

### [MAJ-1] Plate verification bypassed with "TẠM THỜI" static image — production readiness unclear

- **File:** `backend-microservices/ai-service-fastapi/app/routers/esp32.py` (check-in ~line 420, check-out ~line 570)
- **Category:** Architecture / Approach Drift
- **Problem:** Both `check-in` and `check-out` endpoints have their real plate camera capture logic commented out and replaced with a hardcoded static image (`51A-224.56.jpg`). This means:
  - Plate verification does **NOT** work in production
  - `_capture_plate_image()` and `_get_test_image_bytes()` are defined but never called (dead functions)
  - The commented-out blocks are 6+ lines each with no timeline for restoration
- **Impact:** Plate verification is effectively disabled. Any QR code bypasses plate matching.
- **Fix:** Either:
  1. Restore `_capture_plate_image()` calls and remove static image workaround, OR
  2. Add a feature flag (e.g. `PLATE_VERIFICATION_ENABLED=false`) to explicitly control this, and remove the dead commented-out code

---

## 💡 Minor Issues

- **[MIN-1]** `esp32.py:~line 330` — `_parse_qr_data()` function is defined but never called anywhere. Code uses `QRPayload.from_json()` instead. Remove dead function.
- **[MIN-2]** `ratelimit.go:77-79` — `CleanupRateLimiter()` is an exported no-op function. Either implement cleanup logic or remove.
- **[MIN-3]** `views.py:~line 186` — `_get_hourly_price()` method on `BookingViewSet` duplicates `services.get_hourly_price()`. Use service method instead.
- **[MIN-4]** `views.py` — `current()` and `current_parking()` are near-duplicate endpoints returning the same active booking data. Consolidate.
- **[MIN-5]** `gateway-service-go/.env.example` — Missing documentation for `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, `RATE_LIMIT_ENABLED` env vars.
- **[MIN-6]** `services.py:~line 160` — `_PAYMENT_METHOD_MAP` maps `'online'` to `'cash'`, which is semantically misleading. Consider mapping to `'online'` or a more descriptive default.

---

## 🗑️ Dead Code Found

| File | Location | Type | Action |
|------|----------|------|--------|
| `ai-service-fastapi/app/routers/esp32.py` | `_parse_qr_data()` | Unused function | Remove function |
| `ai-service-fastapi/app/routers/esp32.py` | `_capture_plate_image()` | Function — callers commented out | Restore callers or remove |
| `ai-service-fastapi/app/routers/esp32.py` | `_get_test_image_bytes()` | Function — only called by above | Same as above |
| `ai-service-fastapi/app/routers/esp32.py` | check-in TẠM THỜI block (~7 lines) | Commented-out code | Remove or restore |
| `ai-service-fastapi/app/routers/esp32.py` | check-out TẠM THỜI block (~7 lines) | Commented-out code | Remove or restore |
| `gateway-service-go/internal/middleware/ratelimit.go` | `CleanupRateLimiter()` | No-op exported function | Implement or remove |

**Total: 6 items → Cleanup task needed: yes**

---

## 🏗️ Architecture Compliance

- ✅ **ADR compliance**: Layer separation (services.py for business logic, views.py for HTTP) — booking-service follows pattern
- ✅ **API error format**: Rate limiter returns standard `{success, error: {code, message}}` format
- ✅ **Naming conventions**: camelCase in Go, snake_case in Python, PascalCase for classes
- ✅ **Dependency injection**: `verify_device_token` via FastAPI `Depends`, rate limiter via middleware
- ❌ **No hardcoded secrets**: RTSP credentials in source defaults (CRIT-1)
- ❌ **Dead code policy**: 6 dead code items violate "Không có commented-out code blocks > 10 dòng" rule

---

## ✨ Positive Highlights

- **Task 1 (Token Security)**: Excellent use of `hmac.compare_digest()` for constant-time comparison. Graceful dev-mode bypass when token is empty. Router-level dependency ensures all ESP32 endpoints are protected.
- **Task 2 (CI/CD)**: Clean workflow with path-filtered triggers, proper caching, and separate jobs per language.
- **Task 3 (Payment Integration)**: Best-effort pattern (`create_payment_for_booking` never raises) is the right approach for non-critical inter-service calls. 5s timeouts on all external calls.
- **Task 4 (Rate Limiting)**: Redis Lua script ensures atomic increment+expire. Fail-open on Redis unavailability is correct for availability. Standard `X-RateLimit-*` response headers. Configurable via env vars with sensible defaults (100 req/60s).
- **Task 5 (PyTorch)**: Clean version range that balances compatibility and freshness.
- **Task 6 (Camera Env Vars)**: Successfully externalized camera URLs into pydantic Settings. Both esp32.py and camera.py now read from centralized config.

---

## 📋 Action Items (ordered)

1. **[CRIT-1]** Remove RTSP credentials from source defaults in `config.py`, `.env.example`, and `docker-compose.yml`. Use empty default or placeholder.
2. **[MAJ-1]** Resolve plate camera approach: restore `_capture_plate_image()` usage or add explicit feature flag. Remove "TẠM THỜI" commented-out blocks.
3. **[Dead code]** Delete: `_parse_qr_data()`, `CleanupRateLimiter()` (or implement). Clean up unused `_capture_plate_image()` / `_get_test_image_bytes()` per MAJ-1 resolution.
4. **[MIN-5]** Add `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, `RATE_LIMIT_ENABLED` to `gateway-service-go/.env.example`
5. (Optional) [MIN-3] Replace `_get_hourly_price()` viewset method with `services.get_hourly_price()` call
6. (Optional) [MIN-4] Consolidate `current()` and `current_parking()` into one endpoint
