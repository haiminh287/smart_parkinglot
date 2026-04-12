# QA Deployment Report — parksmart.ghepdoicaulong.shop
**Date:** 2026-03-24  
**Target:** https://parksmart.ghepdoicaulong.shop (Cloudflare Tunnel → local Docker)  
**Tester:** 🧪 TESTER Agent  
**Overall Verdict: ❌ FAIL** — 1 High, 2 Medium, 3 Low bugs found

---

## Endpoint Matrix

| # | Method | Endpoint | Expected | Actual Status | CT | Result |
|---|--------|----------|----------|---------------|----|--------|
| **GROUP 1 — Infrastructure Smoke** |
| 1 | GET | `/` | 200 HTML | 200 | text/html | ✅ PASS |
| 2 | GET | `/nginx-health` | 200 | 200 | text/plain | ✅ PASS |
| 3 | GET | `/api/health` | 200 JSON | 200 | application/json | ✅ PASS |
| 4 | GET | `/api/chatbot/health` | 200 JSON | 200 | application/json | ✅ PASS |
| 5 | GET | `/api/chatbot/health/` | 200 JSON (no 307) | 200 | application/json | ✅ PASS |
| 6 | GET | `/api/parking/health/` | 200 JSON | 200 | application/json | ✅ PASS |
| **GROUP 2 — Auth API Contract** |
| 7 | POST | `/api/auth/login/` (invalid creds) | 400/401 JSON | 400 | application/json | ✅ PASS |
| 8 | GET | `/api/auth/me/` (no auth) | 401/403 JSON | 403 | application/json | ✅ PASS¹ |
| 9 | POST | `/api/auth/logout/` | 200/204 (idempotent) | 200 | application/json | ✅ PASS |
| 10 | POST | `/api/auth/refresh/` | 404 JSON ERR_NOT_FOUND | 404 | application/json | ✅ PASS |
| 11 | OPTIONS | `/api/auth/login/` (CORS preflight) | 200/204 + ACAO header | 200 / **no ACAO** | application/json | ❌ FAIL |
| **GROUP 3 — Domain Endpoints (unauthorized)** |
| 12 | GET | `/api/bookings/` | 401 JSON | 401 | application/json | ✅ PASS |
| 13 | GET | `/api/vehicles/` | 401 JSON | 401 | application/json | ✅ PASS |
| 14 | GET | `/api/parking/` | 200/401 JSON (not HTML) | 401 | application/json | ✅ PASS |
| 15 | GET | `/api/notifications/` | 401 JSON | 401 | application/json | ✅ PASS |
| **GROUP 4 — Guard Test** |
| 16 | GET | `/auth/me` | 404 JSON (no SPA fallback) | 404 | application/json | ✅ PASS |
| 17 | GET | `/bookings/` | 404 JSON (no SPA fallback) | 404 | application/json | ✅ PASS |
| **GROUP 5 — FE Render Check** |
| 18 | GET | `/` (valid SPA HTML) | `<div id="root">` + scripts | 200, has root div + Vite assets | text/html | ✅ PASS |
| **GROUP 6 — WebSocket** |
| 19 | WS | `/ws/parking` | 101 Switching Protocols | 101 | — | ✅ PASS |
| 20 | WS | `/ws/parking/` | 101 Switching Protocols | 101 | — | ✅ PASS |

¹ Passes acceptance criteria (401 or 403), but has semantic issue — see BUG-4.

**Summary: 19 PASS / 1 FAIL (20 checks total)**

---

## Bug List

### [BUG-1] HIGH — CORS: Preflight returns no `Access-Control-Allow-Origin` header

**Root Cause:** No CORS middleware configured in API gateway.

**Steps to Reproduce:**
1. Setup: No authentication
2. Action: `OPTIONS https://parksmart.ghepdoicaulong.shop/api/auth/login/` with headers `Origin: https://parksmart.ghepdoicaulong.shop`, `Access-Control-Request-Method: POST`
3. Expected: `Access-Control-Allow-Origin: *` (or specific origin), `Access-Control-Allow-Methods: POST, OPTIONS`
4. Actual: Response has **zero** `Access-Control-Allow-*` headers; `OPTIONS` from a **different** Origin returns `403 Forbidden`

**Actual response headers (OPTIONS):**
```
cross-origin-opener-policy: same-origin   ← COOP, not CORS
vary: Accept, Cookie
(no Access-Control-Allow-Origin)
(no Access-Control-Allow-Methods)
(no Access-Control-Allow-Headers)
```

**Impact:**
- All cross-origin API consumers (mobile WebViews, Swagger UI, monitoring tools, CI integration tests hitting the live API from a different origin) are silently blocked by browsers
- Severely limits API usability for any client not served from the exact same domain

**Likely source:** `nginx.conf` CORS config block missing, or `CORS_ALLOW_ALL_ORIGINS`/`CORS_ALLOWED_ORIGINS` not set in Django `settings.py` (django-cors-headers not applied or not registered)

---

### [BUG-2] MEDIUM — Duplicate conflicting security headers

**Root Cause:** Application sets one value, Cloudflare proxy sets another, resulting in two headers sent to the client.

```
x-frame-options: DENY          ← from application
x-frame-options: SAMEORIGIN    ← from Cloudflare
referrer-policy: same-origin         ← from application
referrer-policy: strict-origin-when-cross-origin  ← from Cloudflare
```

**Expected:** Single authoritative value per header.  
**Actual:** Two conflicting values. Browser behavior is implementation-defined; Chrome typically uses the first occurrence, but this is not guaranteed. `DENY` vs `SAMEORIGIN` directly affects iframing security policy.

**Impact:** Inconsistent security policy enforcement across browser engines. Effective `x-frame-options` is ambiguous.

**Likely source:** Cloudflare "Security Headers" managed transform is enabled AND the origin server also sets the same headers. Fix: disable Cloudflare's managed transform or remove the application-level header.

---

### [BUG-3] MEDIUM — `GET /api/parking/health` (no trailing slash) returns 301

**Steps to Reproduce:**
1. `GET https://parksmart.ghepdoicaulong.shop/api/parking/health` (no trailing slash)
2. Expected: 200 JSON (consistent with `/api/chatbot/health` which returns 200 directly)
3. Actual: `301 Moved Permanently → /api/parking/health/`

```
GET /api/parking/health   → 301 Location:/api/parking/health/
GET /api/chatbot/health   → 200 OK (no redirect)
```

**Impact:** Inconsistency causes extra RTT for monitoring/uptime checkers configured without trailing slash. Misleads automated health-check tools (some register 3xx as failure). Inconsistent API design.

**Likely source:** Django `APPEND_SLASH = True` (default) on parking service, but chatbot service has it disabled or handles both. Fix: either set `APPEND_SLASH = False` and update URLs, or document that all parking endpoints require trailing slash.

---

### [BUG-4] LOW — `GET /api/auth/me/` returns 403 for unauthenticated (should be 401)

**Root Cause:** Django REST Framework default behavior — returns 403 Forbidden when no credentials provided instead of 401 Unauthorized.

**Actual body:**
```json
{"detail": "Authentication credentials were not provided."}
```

**Expected:** `401 Unauthorized` per RFC 7235 (unauthenticated = missing credentials).  
**Actual:** `403 Forbidden` (semantically: authenticated but insufficient permissions).

**Impact:** Client SDKs that distinguish 401 (redirect to login) from 403 (show "access denied") will show users the wrong UX. The message says "not provided" but the status says "forbidden".

**Likely source:** Missing `WWW-Authenticate` header in response and DRF not setting `DEFAULT_AUTHENTICATION_CLASSES` to distinguish unauthenticated vs unauthorized. Fix: add `authentication_classes` to the view or configure DRF to return 401 via a custom `DEFAULT_AUTHENTICATION_CLASSES` or exception handler.

---

### [BUG-5] LOW — CSP `connect-src` references stale/mismatched domains

**Root Cause:** CSP header references domains from a different deployment topology.

**Actual CSP:**
```
content-security-policy: default-src 'self';
  connect-src 'self' https://api.ghepdoicaulong.shop wss://ws.ghepdoicaulong.shop;
  ...
```

**Issue:**
- `https://api.ghepdoicaulong.shop` — no DNS record verified; current API is at `parksmart.ghepdoicaulong.shop/api/`
- `wss://ws.ghepdoicaulong.shop` — WS endpoint is actually on `wss://parksmart.ghepdoicaulong.shop/ws/parking` (confirmed working), not this separate domain

**Impact:** If frontend JS ever resolves API base URL to `api.ghepdoicaulong.shop`, CSP permits that call but no listener exists → silent failures. The stated WS domain `ws.ghepdoicaulong.shop` is not the active endpoint, creating confusion in security review and hardening. Stale domains in CSP are dead entries that may expose unintended origins if those FQDNs are ever registered by a third party.

**Likely source:** CSP was written for a planned multi-subdomain topology (`api.`, `ws.`) but the deployment merged everything under one domain. The `nginx.conf` CSP header needs updating.

---

### [BUG-6] LOW — Frontend `<title>` is placeholder "Lovable App"

**Root Cause:** Scaffolding template title not replaced before production deployment.

**Actual HTML:**
```html
<title>Lovable App</title>
<!-- TODO: Set the document title to the name of your application -->
```

**Impact:** Tab title shows "Lovable App" to end users; `<meta name="author" content="Lovable" />`  is also public. Cosmetic but unprofessional; the TODO comment is visible in browser devtools.

---

## Coverage Summary

| Check Group | Total | Pass | Fail |
|-------------|-------|------|------|
| Infra Smoke | 6 | 6 | 0 |
| Auth Contract | 5 | 4 | 1 |
| Domain Endpoints | 4 | 4 | 0 |
| Guard Test | 2 | 2 | 0 |
| FE Render | 1 | 1 | 0 |
| WebSocket | 2 | 2 | 0 |
| **TOTAL** | **20** | **19** | **1** |

---

## Residual Risks

| Risk | Severity | Detail |
|------|----------|--------|
| CORS absent means API cannot be called from mobile clients or 3rd-party origins | HIGH | Browsers enforce this strictly; no workaround without server-side fix |
| Duplicate `x-frame-options` may cause SPA to be embeddable in iframes on some browsers | MEDIUM | Chrome generally takes first header (`DENY`), but not all clients agree |
| `wss://ws.ghepdoicaulong.shop` in CSP is a dead/unregistered domain — if a threat actor registers it, the CSP explicitly whitelists it for SPA fetch calls | LOW | Theoretical supply-chain risk; unlikely in short term but worth cleaning |
| `APPEND_SLASH` produces 301s before health checks — load balancer/uptime monitor configured for `/api/parking/health` will see 3xx and may mark service as degraded | LOW | Operational monitoring accuracy |

---

## Recommendations (Priority Order)

1. **[HIGH]** Add `django-cors-headers` to parking/auth services and configure `CORS_ALLOWED_ORIGINS` or `CORS_ALLOW_ALL_ORIGINS = True` (behind auth for private API). Alternatively, handle CORS at the nginx gateway level with `add_header Access-Control-Allow-Origin` for OPTIONS.
2. **[MEDIUM]** Remove duplicate headers: either disable Cloudflare's "Managed Security Headers" transform or strip `X-Frame-Options`/`Referrer-Policy` from the origin nginx/app before Cloudflare adds them.
3. **[MEDIUM]** Fix trailing-slash inconsistency: set `APPEND_SLASH = False` on parking service and register explicit URL patterns with trailing slash, OR configure nginx to proxy `/api/parking/health` → `/api/parking/health/` transparently (308 permanent redirect is less ideal than just handling both).
4. **[LOW]** Add a custom DRF exception handler that returns 401 with `WWW-Authenticate` header for unauthenticated requests instead of 403.
5. **[LOW]** Update `nginx.conf` CSP to match the actual deployment topology — replace stale `api.ghepdoicaulong.shop` and `wss://ws.ghepdoicaulong.shop` references with `'self'` since both API and WebSocket are co-hosted.
6. **[LOW]** Replace `<title>Lovable App</title>` with the actual application name and remove the TODO comment.
