# Runtime Smoke Report — Cloudflare + Docker

- Date: 2026-03-14
- Scope: FE runtime, API runtime, WebSocket reachability, quick automation subset

## Runtime checks (real endpoints)

1. FE homepage
   - PASS: `https://app.ghepdoicaulong.shop` → HTTP 200
   - FAIL (secondary domain): `https://ghepdoicaulong.shop` → HTTP 530

2. FE auth page
   - PASS: `https://app.ghepdoicaulong.shop/login` → HTTP 200
   - FAIL (secondary domain): `https://ghepdoicaulong.shop/login` → HTTP 530

3. FE static assets
   - PASS: `https://app.ghepdoicaulong.shop/assets/index-agrOZQzs.js` → HTTP 200
   - PASS: `https://app.ghepdoicaulong.shop/assets/index-Dalyn510.css` → HTTP 200

4. API health + core endpoints
   - PASS: `https://api.ghepdoicaulong.shop/api/health` → HTTP 200
   - PASS: `https://api.ghepdoicaulong.shop/api/auth/me/` (unauth expected) → HTTP 401
   - PASS: `https://api.ghepdoicaulong.shop/api/bookings/` (unauth expected) → HTTP 401
   - FAIL: `https://api.ghepdoicaulong.shop/api/parking/health/` → HTTP 404 (`{"error":"Service not found","path":"api/parking/health/"}`)

5. WebSocket
   - PASS: `wss://ws.ghepdoicaulong.shop/ws/parking/` → CONNECTED (state: Open)

## Automation subset

1. Vitest smoke
   - Command: `npm run test -- src/test/smoke.test.tsx`
   - Result: PASS (1 test)

2. Playwright public-pages subset
   - Command: `npx playwright test e2e/public-pages.spec.ts --project=chromium --no-deps`
   - Result: PASS (6 tests)

## Failure analysis

- Bug: `/api/parking/health/` returns 404 at gateway layer.
- Root cause: gateway router computes `normalizedPath` without `api/`, but proxy call still forwards original `c.Param("path")` including `api/`, so route lookup fails (`Service not found`).
- Related source locations:
  - `backend-microservices/gateway-service-go/internal/router/routes.go` (normalization + direct `HandleProxy` call on service-health path)
  - `backend-microservices/gateway-service-go/internal/handler/proxy.go` (uses raw path from `c.Param("path")` for `GetServiceRoute`)
  - `backend-microservices/gateway-service-go/internal/config/config.go` (`GetServiceRoute` only matches prefixes like `parking/`, not `api/parking/`)
