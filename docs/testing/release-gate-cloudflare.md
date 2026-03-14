# Release Gate Checklist — Cloudflare Cutover

Ngày: 2026-03-13  
Scope: FIX-ALL + Cloudflare release readiness

## 1) Implementer gate

- [x] CI path mismatch đã fix (`backend-microservices`, `spotlove-ai`).
- [x] Đã thêm workflow deploy FE Cloudflare Pages.
- [x] Đã thêm skeleton tunnel config + reverse proxy config.
- [x] Đã thêm `.env.example` cho FE với `VITE_API_URL`, `VITE_WS_URL`, `VITE_GATEWAY_SECRET`.
- [x] Đã cập nhật backend `.env.example` cho proxy/tunnel production-facing.

## 2) Tester gate

- [ ] FE `npm run test` pass (đính kèm log/evidence).
- [ ] FE `npm run build` pass (đính kèm log/evidence).
- [ ] API health check `GET /api/health` pass qua public domain.
- [ ] WS handshake `wss://api.<domain>/ws/...` pass.

## 3) Security gate

- [ ] `npm audit --audit-level=high` không còn High/Critical chưa được duyệt exception.
- [ ] Không có secret hardcoded mới trong diff.
- [ ] Cloudflare TLS mode `Full (strict)` đã bật.
- [ ] WAF managed rules + baseline rate limits đã áp dụng.
- [ ] Evidence đã điền tại `docs/notes/cloudflare-security-controls-evidence.md`.

## 4) DevOps gate

- [ ] GitHub Secrets tồn tại: `CF_API_TOKEN`, `CF_ACCOUNT_ID`, `CF_PAGES_PROJECT`.
- [ ] Workflow deploy FE chạy xanh từ `main`.
- [ ] Tunnel route `api.<domain>` hoạt động ổn định.
- [ ] Rollback drill staging đã thực hiện và có log.

## 5) QC sign-off

- [ ] Đủ evidence cho tester/security/devops gates.
- [ ] CI main branch xanh.
- [ ] Không còn blocker P0/P1 mở trong phạm vi FIX-ALL.
