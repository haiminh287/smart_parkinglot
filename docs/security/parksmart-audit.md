# Security Audit — parksmart.ghepdoicaulong.shop

**Date:** 2026-03-24
**Auditor:** AppSec Agent (Security Mode)
**Scope:** Gateway service, Auth service, Nginx, Cloudflare config, all `.env` files, Go/Python dependencies
**Verdict: ❌ FAIL — Deploy blocked**

| Severity | Count |
|---|---|
| 🔴 Critical | 1 |
| 🟠 High | 5 |
| 🟡 Medium | 5 |
| 🟢 Low | 4 |

---

## Verdict Summary

**FAIL.** Critical: hardcoded default `GATEWAY_SECRET` is the same string in source code AND all 7 deployed services. Multiple High findings including header injection bypass and broken OAuth CSRF defense make this deployment not production-ready. Specific required fixes listed in **Sign-off Conditions**.

---

## 🔴 Critical Vulnerabilities

### [VULN-001] Hardcoded Default GATEWAY_SECRET Across All Services

- **OWASP:** A02 — Cryptographic Failures / A05 — Security Misconfiguration
- **Locations:**
  - [backend-microservices/gateway-service-go/internal/config/config.go](../backend-microservices/gateway-service-go/internal/config/config.go) — line 44 (Go default)
  - [backend-microservices/auth-service/auth_service/settings.py](../backend-microservices/auth-service/auth_service/settings.py) — last line (Python default)
  - `gateway-service-go/.env`, `auth-service/.env`, `booking-service/.env`, `parking-service/.env`, `vehicle-service/.env`, `ai-service-fastapi/.env`, `payment-service-fastapi/.env`, root `.env` — all use `GATEWAY_SECRET=gateway-internal-secret-key`
- **Problem:** `GATEWAY_SECRET` is hardcoded as the fallback/default value in both Go and Python source code. Every service `.env` file uses the same trivial string. `GatewayAuthMiddleware` (shared across all Python services) uses this secret to authorize ALL protected inter-service requests. The secret is committed to the repository.
- **Attack scenario:** An attacker with repository read access (or who simply tries the obvious default) sends `X-Gateway-Secret: gateway-internal-secret-key` directly to any backend service Docker port if exposed, OR exploits any SSRF to reach internal services. They can then forge `X-User-ID`/`X-User-Role` headers and access any user's data or perform admin operations.
- **Impact:** Full authentication bypass on all microservices. Privilege escalation to admin.
- **Vulnerable code:**
  ```go
  // config.go:44
  GatewaySecret: strings.TrimSpace(getEnv("GATEWAY_SECRET", "gateway-internal-secret-key")),
  ```
  ```python
  # settings.py (auth-service)
  GATEWAY_SECRET = config('GATEWAY_SECRET', default='gateway-internal-secret-key')
  ```
  ```
  # ALL .env files
  GATEWAY_SECRET=gateway-internal-secret-key
  ```
- **Fix:**
  1. Remove hardcoded defaults from both source files — use `config('GATEWAY_SECRET')` (no default), fail on missing value.
  2. Rotate to a cryptographically random value: `python -c "import secrets; print(secrets.token_hex(32))"`.
  3. Set the generated value in all service `.env`/Docker secrets — never commit it.
  4. Add a startup check that rejects the known weak default string.

---

## 🟠 High Vulnerabilities

### [VULN-002] X-User-* Headers Not Stripped for Public Routes (Header Injection)

- **OWASP:** A01 — Broken Access Control
- **Locations:**
  - [backend-microservices/gateway-service-go/internal/handler/proxy.go](../backend-microservices/gateway-service-go/internal/handler/proxy.go) — `Director` function
  - [backend-microservices/shared/gateway_middleware.py](../backend-microservices/shared/gateway_middleware.py) — `__call__` method
- **Problem:** For public routes (`route.Public == true`, e.g. all `/auth/*`), `AuthMiddleware` does not set `session_data` in the Gin context. The `proxy.go` Director's user-header injection block is therefore skipped. However, `httputil.ReverseProxy` copies all original client request headers by default — client-supplied `X-User-ID`, `X-User-Role`, `X-User-Is-Staff` are forwarded unchanged to the backend. On the backend, `GatewayAuthMiddleware` skips the gateway-secret check for public paths but **still reads and trusts** `X-User-ID` from headers, setting `request.user_id = <attacker-controlled-value>`.
- **Attack scenario:** Attacker sends `POST /api/auth/login/` with header `X-User-ID: <any-uuid>`. The gateway forwards this to auth-service. `GatewayAuthMiddleware` sets `request.user_id` to the attacker's value. If any public endpoint logic ever reads `request.user_id` (e.g. a newly added endpoint), it would process it as a legitimate authenticated user ID without any session.
- **Impact:** Currently limited by the specific permissions used on public endpoints. However, this is a persistent architecture vulnerability: any future public endpoint that checks `request.user_id` is trivially bypassable.
- **Vulnerable code:**
  ```go
  // proxy.go — Director
  // For public routes, session_data is not in context:
  if sd, ok := c.Get("session_data"); ok {  // NOT executed for public routes
      // headers only set here
  }
  // Client headers cloned by httputil.ReverseProxy are forwarded as-is
  ```
- **Fix:** Add explicit header stripping in the Director **before** the session check, regardless of route visibility:
  ```go
  // proxy.go — at start of Director, before session check
  req.Header.Del("X-User-ID")
  req.Header.Del("X-User-Email")
  req.Header.Del("X-User-Role")
  req.Header.Del("X-User-Is-Staff")
  req.Header.Del("X-Gateway-Secret")
  // Then conditionally re-set from session:
  if sd, ok := c.Get("session_data"); ok { ... }
  ```

---

### [VULN-003] OAuth State Nonce Validation Non-Functional (Broken Anti-CSRF)

- **OWASP:** A07 — Identification and Authentication Failures
- **Locations:**
  - [backend-microservices/gateway-service-go/internal/handler/auth.go](../backend-microservices/gateway-service-go/internal/handler/auth.go) — `HandleOAuthCallback`
  - [backend-microservices/auth-service/users/views.py](../backend-microservices/auth-service/users/views.py) — `_consume_oauth_state_nonce`, `validate_oauth_state`
- **Problem:** The OAuth flow stores a nonce in the **browser's Django session** during `/api/auth/google/` (state generation). On callback, `HandleOAuthCallback` makes a **server-side HTTP request** to auth-service without forwarding the browser's `sessionid` cookie. `validate_oauth_state` calls `_consume_oauth_state_nonce(request, ...)` — but `request.session` is the gateway's new anonymous session, not the browser's. `_consume_oauth_state_nonce` returns `False` because the session store is empty, causing state validation to always fail (returns `OAUTH_ERROR_INVALID_STATE`).
- **Consequence:** Either (a) OAuth is completely non-functional (redirect always fails) or (b) the nonce-based CSRF protection is silently never checked in the real flow. If (b), OAuth CSRF attacks using an attacker-crafted `state` parameter signed with the `OAUTH_STATE_SECRET` (which defaults to `SECRET_KEY`, which has a weak default) are possible.
- **Impact:** Broken CSRF protection for OAuth login. Functional OAuth may be entirely unavailable.
- **Fix:** The gateway's `HandleOAuthCallback` must forward the browser's `sessionid` cookie in its server-side request to auth-service:
  ```go
  // In HandleOAuthCallback, after creating httpReq:
  if browserSessionCookie, err := c.Cookie("sessionid"); err == nil {
      httpReq.Header.Set("Cookie", "sessionid="+browserSessionCookie)
  }
  ```

---

### [VULN-004] No Auth-Specific Rate Limiting (Brute Force / Credential Stuffing)

- **OWASP:** A07 — Identification and Authentication Failures
- **Location:** [backend-microservices/gateway-service-go/internal/middleware/ratelimit.go](../backend-microservices/gateway-service-go/internal/middleware/ratelimit.go)
- **Problem:** The only rate limiter is a global 100 req/min per IP applied at the gateway level. There is no endpoint-specific limit for `/auth/login/`, `/auth/register/`, or `/auth/forgot-password/`. 100 password attempts per minute from a single IP is feasible for targeted brute force. No account lockout mechanism is visible in the auth service. No CAPTCHA or exponential backoff.
- **Attack scenario:** Attacker performs credential stuffing: 100 login attempts/minute per IP, ~6,000/hour. With IP rotation, this is effectively uncapped.
- **Impact:** Account compromise via brute force / credential stuffing.
- **Fix:**
  - Add auth-specific middleware with ≤5 req/min for `/api/auth/login/`, `/api/auth/forgot-password/`
  - Implement temporary account lockout after 10 failed attempts (store in Redis: already available)
  - Consider CAPTCHA after 3 failed attempts from the same IP

---

### [VULN-005] Credentials Hardcoded as Fallback Defaults in Source Code

- **OWASP:** A02 — Cryptographic Failures
- **Locations:**
  - [backend-microservices/auth-service/auth_service/settings.py](../backend-microservices/auth-service/auth_service/settings.py) — lines `os.environ.get('DB_USER', 'parksmartuser')` / `os.environ.get('DB_PASSWORD', 'parksmartpass')`
  - Root `.env`: `RABBITMQ_USER=admin`, `RABBITMQ_PASS=admin`
  - `booking-service/.env`: `RABBITMQ_USER=admin`, `RABBITMQ_PASSWORD=admin`
- **Problem:** Database password `parksmartpass` and RabbitMQ credentials `admin/admin` are used uniformly across all services. The DB credentials are hardcoded as Python source-code fallbacks — they appear in git history permanently. RabbitMQ default admin credentials are trivially guessable.
- **Attack scenario:** (1) Git history leaks DB password. (2) If RabbitMQ management port (15672) is accidentally exposed via Docker port binding, trivial full queue access. (3) If single service is compromised, attacker has credentials for all other services' DBs and message broker.
- **Impact:** Full database compromise, message queue manipulation.
- **Fix:**
  - Remove hardcoded fallback defaults in `settings.py` for DB credentials
  - Rotate to unique strong passwords per service
  - Use Docker secrets or a secrets manager
  - Ensure RabbitMQ management port 15672 is never exposed outside Docker network

---

### [VULN-006] OAuth Access Tokens Stored in Database Plain Text

- **OWASP:** A02 — Cryptographic Failures
- **Location:** [backend-microservices/auth-service/users/oauth/google.py](../backend-microservices/auth-service/users/oauth/google.py) — `exchange_google_code()`
- **Problem:** Google OAuth access tokens are stored in the `OAuthAccount` model as plain text (`access_token=access_token, refresh_token=token_data.get('refresh_token')`). If the database is compromised, all active Google OAuth tokens are directly usable to access users' Google accounts.
- **Attack scenario:** SQL injection or DB backup leak exposes all access tokens → attacker accesses all users' Google account data.
- **Impact:** Mass user Google account privacy breach.
- **Fix:**
  - If access tokens are not needed for ongoing API calls (i.e., used only for initial login), do not store them.
  - If stored for API use, encrypt with `django.core.signing` or AES-256-GCM using a deployment key.
  - Refresh tokens specifically should be encrypted at rest.

---

## 🟡 Medium Vulnerabilities

### [VULN-007] CSP Allows `unsafe-inline` for Scripts and Styles

- **OWASP:** A05 — Security Misconfiguration
- **Location:** [infra/nginx/nginx.conf](../infra/nginx/nginx.conf) — `add_header Content-Security-Policy`
- **Problem:** `script-src 'self' 'unsafe-inline'` and `style-src 'self' 'unsafe-inline'` allow inline JavaScript and CSS. This neutralizes most XSS defenses — if an XSS injection is found anywhere, the attacker can execute arbitrary JavaScript.
- **Fix:** Use a build-step nonce strategy or hash-based CSP. For Vue/React SPAs, vite-plugin-csp can inject `nonces`. Fallback: `'unsafe-inline'` can be kept short-term, but track as technical debt.

---

### [VULN-008] In-Memory Rate Limiter — Lost on Restart, Not Distributed

- **OWASP:** A04 — Insecure Design / DoS Risk
- **Location:** [backend-microservices/gateway-service-go/internal/middleware/ratelimit.go](../backend-microservices/gateway-service-go/internal/middleware/ratelimit.go) — `init()` / `RateLimiter`
- **Problem:** Rate limit state stored in process memory (`map[string]*visitor`). State is lost every container restart/crash. With horizontal scaling (multiple gateway instances), limits are per-instance, so an attacker gets N×100 req/min. Cleanup goroutine is not cancelable on shutdown.
- **Fix:** Replace with Redis-backed rate limiter (Redis is already in the stack). Use `github.com/go-redis/redis_rate` or implement sliding window counter in Redis.

---

### [VULN-009] Password Reset Tokens Stored Plain Text

- **OWASP:** A02 — Cryptographic Failures
- **Location:** [backend-microservices/auth-service/users/views.py](../backend-microservices/auth-service/users/views.py) — `ForgotPasswordView.post()` / `ResetPasswordView.post()`
- **Problem:** `secrets.token_urlsafe(32)` is generated and stored as `PasswordReset.token` without hashing. A DB leak exposes all active reset tokens (valid 1 hour) that allow password takeover.
- **Fix:** Store `hashlib.sha256(token.encode()).hexdigest()` in DB; compare hash on validation. Send raw token in email URL only.

---

### [VULN-010] `ENV=development` Mode Active on Production Deployment

- **OWASP:** A05 — Security Misconfiguration
- **Locations:**
  - [backend-microservices/gateway-service-go/.env](../backend-microservices/gateway-service-go/.env) — `ENV=development`, `DEBUG=true`
  - [backend-microservices/auth-service/.env](../backend-microservices/auth-service/.env) — `DEBUG=True`, `SESSION_COOKIE_SECURE=false`
- **Problem:** Gateway `.env` has `ENV=development` and `DEBUG=true`, while production-like values for cookie domain and CORS are configured in the same file (`.ghepdoicaulong.shop`). In development mode:
  - Go gateway runs in `gin.DebugMode` (verbose routing info exposed at startup, detailed error output)
  - Production security validations in `Config.Validate()` are skipped (HTTPS-only CORS, secure cookie required)
  - Auth service has `SESSION_COOKIE_SECURE=false` — Django's `sessionid` cookie (used to store OAuth nonces) is not flagged Secure; could be transmitted over HTTP
- **Fix:** Set `ENV=production` and `DEBUG=false` in both `.env` files used in the deployed environment. Verify auth service `SESSION_COOKIE_SECURE=true`.

---

### [VULN-011] Password Reset Email Not Implemented — Token Exposed in Response?

- **OWASP:** A09 — Security Logging and Monitoring Failures
- **Location:** [backend-microservices/auth-service/users/views.py](../backend-microservices/auth-service/users/views.py) — `ForgotPasswordView.post()`, line with `# TODO: Send email`
- **Problem:** `send_password_reset_email` is commented out with a `TODO`. The reset token is created in the DB but never sent to the user via email. This means either (a) the feature is non-functional, or (b) the token may be exposed via logs or side-channel.
- **Fix:** Implement email delivery before enabling this endpoint in production. If the endpoint is live and the `TODO` is still unresolved, disable the endpoint to prevent DB token accumulation.

---

## 🟢 Low Findings

### [VULN-012] Dead Code — `isPublicEndpoint()` Never Called

- **Location:** [backend-microservices/gateway-service-go/internal/middleware/auth.go](../backend-microservices/gateway-service-go/internal/middleware/auth.go)
- **Problem:** `isPublicEndpoint()` function is defined but never called. Actual public path determination uses `route.Public` from config. This dead code could mislead developers who add new paths to this function assuming it has effect.
- **Fix:** Remove the function.

---

### [VULN-013] Cloudflare Tunnel UUIDs in Committed Config

- **Locations:**
  - [infra/cloudflare/cloudflared/config.yml](../infra/cloudflare/cloudflared/config.yml) — `tunnel: 57eb6de9-...`
  - [infra/cloudflare/cloudflared/config-parksmart.yml](../infra/cloudflare/cloudflared/config-parksmart.yml) — `tunnel: 5d3c98ed-...`
- **Problem:** Tunnel UUIDs are publicly committable and alone carry low risk, but combined with leaked credentials, they identify targets. `credentials-file` paths reveal the developer's local machine username (`C:\Users\MINH\`).
- **Fix:** Replace absolute credential paths with relative or environment-variable paths. Tunnel UUIDs in config are acceptable.

---

### [VULN-014] `.env.production` Not in `.gitignore`

- **Location:** [spotlove-ai/.env.production](../spotlove-ai/.env.production), root [.gitignore](../.gitignore)
- **Problem:** `.gitignore` covers `.env`, `.env.local`, `.env.*.local` — but NOT `.env.production`. The `spotlove-ai/.env.production` file currently contains only public URLs (`VITE_API_URL`, `VITE_WS_URL`) and no secrets, so the current risk is low. However, the pattern is wrong — if someone adds a secret to this file, it would be committed.
- **Fix:** Add `.env.production` to `.gitignore`.

---

### [VULN-015] No Request Body Size Limit in Gateway

- **Location:** [backend-microservices/gateway-service-go/cmd/server/main.go](../backend-microservices/gateway-service-go/cmd/server/main.go)
- **Problem:** No global `http.MaxBytesReader` or gin `MaxMultipartMemory` override is set. Default gin multipart limit is 32 MiB. For non-multipart bodies, no limit is imposed. An attacker can send large payloads to memory-buffer the gateway.
- **Fix:** Add a global body limit middleware: `r.Use(func(c *gin.Context) { c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 10<<20); c.Next() })` (10 MiB example).

---

## STRIDE Assessment

| Threat | Status | Notes |
|---|---|---|
| Spoofing | ❌ FAIL | VULN-001: Gateway secret hardcoded; VULN-002: X-User headers injectable on public paths |
| Tampering | ⚠️ PARTIAL | SQL via ORM (safe); VULN-002 allows header injection; no body size limit |
| Repudiation | ❌ FAIL | VULN security events not logged — auth failures, session creation not in structured log |
| Info Disclosure | ⚠️ PARTIAL | VULN-005: DB password in source; VULN-006: OAuth tokens plain text; debug mode leaks |
| DoS | ⚠️ PARTIAL | Rate limiter present but in-memory and not auth-specific (VULN-004, VULN-008) |
| Elevation | ❌ FAIL | VULN-001 + VULN-002 together allow full privilege escalation if internal network reachable |

---

## Dependency Vulnerabilities

### Go (gateway-service-go)

| Package | Version | CVE | Status |
|---|---|---|---|
| `golang.org/x/net` | v0.33.0 | None known | ✅ Current |
| `golang.org/x/crypto` | v0.31.0 | None known | ✅ Current |
| `github.com/gin-gonic/gin` | v1.10.0 | None known | ✅ Current |
| `github.com/redis/go-redis/v9` | v9.7.0 | None known | ✅ Current |

**Note:** `govulncheck` not available in this environment. Manual review shows all Go dependencies are current versions with no known critical CVEs. Run `govulncheck ./...` to confirm.

### Python (auth-service / shared)

| Package | Version | Status |
|---|---|---|
| `Django` | 5.2.12 | ✅ Current (latest 5.x series with security patches) |
| `djangorestframework` | 3.15.2 | ✅ Current |
| `gunicorn` | 22.0.0 | ✅ Current |
| `requests` | 2.32.4 | ✅ Current |
| `redis` | 5.2.1 | ✅ Current |

No critical CVEs identified. Run `pip-audit` to confirm.

---

## OWASP Top 10 Status

| # | Category | Status | Finding |
|---|---|---|---|
| A01 | Broken Access Control | ❌ FAIL | VULN-002: header injection on public routes |
| A02 | Cryptographic Failures | ❌ FAIL | VULN-001 (hardcoded secret), VULN-005 (DB creds in source), VULN-006 (OAuth tokens plain text), VULN-009 (reset tokens plain text) |
| A03 | Injection | ✅ PASS | ORM used throughout; parameterized queries; no raw SQL interpolation found |
| A04 | Insecure Design | ⚠️ PARTIAL | VULN-003: OAuth CSRF nonce architecture broken; VULN-004: no auth-specific rate limit |
| A05 | Security Misconfiguration | ❌ FAIL | VULN-001 (default secrets), VULN-007 (CSP unsafe-inline), VULN-010 (dev mode in prod) |
| A06 | Vulnerable Components | ✅ PASS | All deps current; no known critical CVEs |
| A07 | Auth Failures | ❌ FAIL | VULN-003 (broken OAuth nonce), VULN-004 (no brute-force protection), VULN-009 (plain text reset token) |
| A08 | Software/Data Integrity | ✅ PASS | go.sum and pip lockfiles present; CI not audited in scope |
| A09 | Logging Failures | ⚠️ PARTIAL | VULN-011 (security events not logged; no auth failure/session event logging) |
| A10 | SSRF | ✅ PASS | OAuth redirect URI sanitized (`sanitize_return_to`); no user-controlled URL fetch found |

**OWASP Score: 5/10 clean**

---

## Security Headers Assessment (nginx.conf)

| Header | Status | Value |
|---|---|---|
| `X-Frame-Options` | ✅ | `SAMEORIGIN` |
| `X-Content-Type-Options` | ✅ | `nosniff` |
| `X-XSS-Protection` | ✅ | `1; mode=block` |
| `Referrer-Policy` | ✅ | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | ✅ | `max-age=31536000; includeSubDomains` (served via Cloudflare → client) |
| `Permissions-Policy` | ✅ | Cameras, mic, geolocation disabled |
| `Content-Security-Policy` | ⚠️ | Has `unsafe-inline` for script/style (VULN-007) |

---

## Transport Security Assessment

- **TLS termination:** Cloudflare handles TLS 1.2/1.3 → **PASS**
- **Backend:** Cloudflare → Nginx on HTTP port 80 (internal Docker) → **Acceptable** (local tunnel, no internet exposure)
- **HSTS:** Present, `max-age=31536000`, forwarded by Cloudflare to client → **PASS**
- **noTLSVerify in config.yml:** `noTLSVerify: false` for WS (default) → **PASS**

---

## Sign-off Conditions (Required Before Production-Ready)

The following must be resolved before deployment can be considered production-safe. Items are ordered by priority:

### MUST FIX (blocking):

1. **[VULN-001]** Rotate `GATEWAY_SECRET` to a random 32-byte hex secret. Remove hardcoded defaults from `config.go` and `settings.py`. Fail startup if env var is missing.

2. **[VULN-002]** Strip `X-User-ID`, `X-User-Email`, `X-User-Role`, `X-User-Is-Staff`, `X-Gateway-Secret` from incoming client requests in `proxy.go` Director before the session re-injection block.

3. **[VULN-003]** Fix OAuth callback flow: forward browser `sessionid` cookie in gateway's server-side request to auth-service, OR refactor OAuth flow to pass state validation through the proxy (preserving session continuity).

4. **[VULN-005]** Rotate `DB_PASSWORD` to unique strong passwords per service. Remove `os.environ.get('DB_PASSWORD', 'parksmartpass')` fallback from `settings.py`.

5. **[VULN-010]** Set `ENV=production` and `DEBUG=false` in the deployed gateway config. Set `SESSION_COOKIE_SECURE=true` in auth-service deployed config.

### SHOULD FIX (high priority, not immediately blocking deploy if mitigated):

6. **[VULN-004]** Add login-specific rate limiter: ≤5 req/min per IP on `POST /api/auth/login/` and `POST /api/auth/forgot-password/`.

7. **[VULN-006]** Encrypt or remove OAuth access/refresh tokens from DB storage.

8. **[VULN-008]** Replace in-memory rate limiter with Redis-backed implementation.

### SHOULD FIX (medium priority):

9. **[VULN-007]** Remove `unsafe-inline` from CSP `script-src` and `style-src`.
10. **[VULN-009]** Hash password reset tokens before DB storage.
11. **[VULN-011]** Implement password reset email or disable the endpoint.

---

*Audit performed via static code analysis and configuration review. No live exploitation was performed.*
