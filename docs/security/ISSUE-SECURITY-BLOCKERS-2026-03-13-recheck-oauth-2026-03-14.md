# Security Re-check — OAuth blockers (2026-03-14)

**Scope:** social OAuth callback hardening re-check (CSRF/replay/mix-up), error info leakage, production config guard.

**Risk Level: High**  
**Deploy Ready: NO**

| Severity | Count |
| --- | --- |
| 🔴 Critical | 0 |
| 🟠 High | 1 |
| 🟡 Medium | 1 |
| 🟢 Low | 1 |

---

## Findings

### [VULN-001] Production cookie security guard chưa chặt ở auth-service (HIGH)
- **OWASP:** A05 Security Misconfiguration / A02 Cryptographic Failures
- **Location:**
  - `backend-microservices/auth-service/auth_service/settings.py` (production guard section)
  - `backend-microservices/auth-service/users/views.py` (`LoginView.post` set CSRF cookie)
- **Problem:**
  - Auth-service chưa fail-fast khi `ENV=production` nhưng `SESSION_COOKIE_SECURE=false`.
  - `csrftoken` đang được set `secure=False` hard-coded trong login response.
- **Exploitability:** Nếu deployment bị terminate TLS sai lớp hoặc có đường HTTP nội bộ/public, cookie có thể bị gửi qua channel không bảo mật.
- **Impact:** tăng nguy cơ lộ session/CSRF context trong môi trường production misconfigured.
- **Remediation:**
  1. Enforce `SESSION_COOKIE_SECURE=True` khi `ENV=production` (raise `ImproperlyConfigured` nếu false).
  2. Set CSRF cookie `secure=settings.SESSION_COOKIE_SECURE` thay vì hard-code.
  3. Bổ sung test cấu hình production cho auth-service tương tự gateway `TestValidate_*`.

### [VULN-002] OAuth state phản chiếu về FE callback query (MEDIUM)
- **OWASP:** A01 Broken Access Control (information minimization side-channel)
- **Location:**
  - `backend-microservices/gateway-service-go/internal/handler/auth.go` (`redirectOAuthCallback`)
  - `spotlove-ai/src/pages/AuthCallbackPage.tsx`
- **Problem:** Gateway append lại `state` vào redirect URL FE; FE còn render một phần `state` trên UI.
- **Exploitability:** không lộ secret trực tiếp (state đã ký + nonce), nhưng tăng footprint telemetry/log/referrer/history.
- **Impact:** information disclosure mức thấp-trung bình.
- **Remediation:** không phản chiếu `state` về FE; bỏ hiển thị `state` trên callback page.

### [OBS-001] CSRF/replay/mix-up controls đã được tăng cường (LOW residual risk)
- **Location:** `backend-microservices/auth-service/users/views.py`
- **Verified controls:**
  - state có chữ ký + TTL (`signing.loads(... max_age=...)`)
  - state bind provider (`payload.provider == provider`)
  - nonce one-time consume trong session (`_consume_oauth_state_nonce`)
  - callback return_to được sanitize.
- **Residual risk:** phụ thuộc session integrity và deployment boundary (auth-service không expose trực tiếp public internet).

---

## Targeted Verification Notes

- Gateway production guard có test pass (`go test ./internal/config -run TestValidate -v`):
  - `TestValidate_ProductionRequiresCookieDomain` PASS
  - `TestValidate_ProductionRejectsInsecureCORSOrigin` PASS
  - `TestValidate_ProductionValidConfig` PASS

---

## STRIDE Re-check (OAuth callback scope)

| Threat | Status | Notes |
| --- | --- | --- |
| Spoofing | ⚠️ | State/provider/nonce đã tốt hơn, nhưng cookie secure guard auth-service còn thiếu block fail-fast. |
| Tampering | ✅ | Signed state + provider check + one-time nonce reduce tampering/replay. |
| Repudiation | ✅ | Callback failures log server-side (`logger.exception`). |
| Info Disclosure | ⚠️ | Không còn trả raw exception từ callback; còn phản chiếu `state` lên FE. |
| DoS | ✅ | Không thấy regression mới trong callback path. |
| Elevation | ✅ | Mix-up giảm nhờ provider-bound validation và provider-specific callback route. |

---

## Deploy Gate Decision

**FAIL**

- Lý do block: còn **1 High** (`VULN-001`).
- Điều kiện để PASS: fix `VULN-001`, re-run security re-check cho auth-service cookie policy.
