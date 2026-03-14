# Code Review Report — ISSUE-BATCH-P0-OAUTH-2026-03-14 (Re-review)

**Score: 8.5/10** | **Verdict: Approve**
**Date:** 2026-03-14 | Files reviewed: 9

---

## Summary

|               | Count |
| ------------- | ----- |
| 🚨 Critical   | 0     |
| ⚠️ Major      | 0     |
| 💡 Minor      | 2     |
| 🗑️ Dead Code  | 4     |
| 🏗️ Arch Drift | 0     |

---

## Re-check 3 OAuth Security Blockers

### [BLOCKER-1] OAuth state browser/session binding + one-time use

- **Status:** ✅ Closed
- **Evidence:** `users/views.py` đã thêm nonce one-time lưu vào session (`_store_oauth_state_nonce`) và consume khi callback (`_consume_oauth_state_nonce`), đồng thời verify chữ ký + TTL + provider + nonce.
- **File:** `backend-microservices/auth-service/users/views.py`

### [BLOCKER-2] Callback không còn trả raw exception message ra client

- **Status:** ✅ Closed
- **Evidence:** `google_callback_view` và `facebook_callback_view` chuyển sang `logger.exception(...)` và trả error code chuẩn hóa `provider_error`; không còn `str(e)` leak.
- **File:** `backend-microservices/auth-service/users/views.py`

### [BLOCKER-3] Production fail-fast guard cho cookie/CORS/OAuth callback URL

- **Status:** ✅ Closed
- **Evidence:** `Config.Validate()` đã enforce khi `ENV=production`: bắt buộc `SESSION_COOKIE_DOMAIN`, `SESSION_COOKIE_SECURE=true`, `SESSION_COOKIE_SAMESITE` hợp lệ, `CORS_ALLOWED_ORIGINS` là HTTPS/non-localhost, `FE_AUTH_CALLBACK_URL` là HTTPS.
- **Files:** `backend-microservices/gateway-service-go/internal/config/config.go`, `backend-microservices/gateway-service-go/internal/config/config_test.go`

---

## 💡 Minor Issues (non-blocking)

- [MIN-1] `spotlove-ai/src/pages/AuthCallbackPage.tsx` — vẫn render một phần `state` lên UI callback; nên bỏ để giảm lộ telemetry OAuth.
- [MIN-2] `spotlove-ai/src/store/slices/authSlice.ts` — còn `console.error` trong flow parse cookie; nên thay bằng logger chuẩn hoặc xử lý im lặng.

---

## 🗑️ Dead Code Found

| File | Location | Type | Action |
| ---- | -------- | ---- | ------ |
| `.tmp_django_smoke.py` | entire file | Temporary script artifact | Delete file |
| `.tmp_fe_build_with_env.ps1` | entire file | Temporary script artifact | Delete file |
| `.tmp_retest_smoke.ps1` | entire file | Temporary script artifact | Delete file |
| `.tmp_retest_smoke.py` | entire file | Temporary script artifact | Delete file |

**Total: 4 items → Cleanup task needed: yes**

---

## 🏗️ Architecture Compliance

- ✅ Context conventions: phù hợp baseline hiện có.
- ⚠️ API contract: chưa có `docs/api/openapi.yaml` để cross-check callback contract.
- ✅ Layer separation: gateway điều phối OAuth callback, auth-service xử lý OAuth state/identity.
- ✅ Naming conventions: nhất quán.

---

## ✨ Positive Highlights

- OAuth state protection đã chuyển từ signed-only sang signed + browser/session-bound one-time nonce.
- Gateway đã fail-fast validation rõ cho production security posture.
- Có test cho production config validation trong `config_test.go`.

---

## 📋 Action Items trước deploy

1. **[Cleanup bắt buộc]** Xóa 4 file `.tmp*` nêu trên theo dead-code policy.
2. (Khuyến nghị) Bỏ hiển thị `state` trên UI callback.
3. (Khuyến nghị) Thay `console.error` bằng logging policy chuẩn.
