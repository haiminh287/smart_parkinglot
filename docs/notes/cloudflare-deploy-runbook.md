# Cloudflare Deploy Runbook (Pages + Tunnel)

## 1) Mục tiêu

- Deploy frontend qua Cloudflare Pages.
- Public backend qua Cloudflare Tunnel + reverse proxy origin.
- Giữ contract public: `/api/*` và `/ws/*`.

## 2) Prerequisites

- Đã tạo Cloudflare Pages project cho frontend.
- Đã tạo Cloudflare Tunnel cho `api.<domain>`.
- VPS/origin chạy Docker Compose backend + reverse proxy.
- GitHub Secrets có sẵn:
  - `CF_API_TOKEN`
  - `CF_ACCOUNT_ID`
  - `CF_PAGES_PROJECT`
   - `VITE_API_URL`
   - `VITE_WS_URL`
   - `VITE_GATEWAY_SECRET`

## 3) Deploy frontend (Pages)

1. Cập nhật env Pages:
   - `VITE_API_URL=https://api.<domain>/api`
   - `VITE_WS_URL=wss://api.<domain>/ws`
   - `VITE_GATEWAY_SECRET=<placeholder/secret thật trên dashboard>`
2. Push `main` để chạy workflow `.github/workflows/deploy-cloudflare-pages.yml`.
   - Workflow sẽ fail-fast nếu thiếu bất kỳ secret bắt buộc nào ở trên.
3. Verify deployment success trong GitHub Actions + Cloudflare Pages.

## 4) Deploy backend public route (Tunnel + reverse proxy)

1. Copy `infra/cloudflare/reverse-proxy/api.conf.example` vào config thật của Nginx/Caddy.
2. Copy `infra/cloudflare/cloudflared/config.example.yml` thành config runtime và điền tunnel ID + hostname.
3. Khởi động lại dịch vụ:
   - reverse proxy
   - cloudflared
4. Verify:
   - `https://api.<domain>/api/health`
   - WebSocket handshake qua `wss://api.<domain>/ws/...`

## 5) Rollback nhanh

### FE rollback

1. Trong Cloudflare Pages, promote deployment trước đó.
2. Nếu lỗi env, restore env snapshot trước deploy và redeploy.

### API rollback

1. Revert config reverse proxy.
2. Revert config cloudflared/tunnel route.
3. Restart reverse proxy + cloudflared.
4. Re-check `GET /api/health` và WS handshake.

## 6) Lưu ý an toàn

- Không commit secret thật vào repo.
- TLS mode ở Cloudflare: `Full (strict)`.
- Bật WAF managed rules và rate limit auth/chatbot endpoints theo baseline kiến trúc.

## 7) Security evidence artifacts

- Mẫu evidence controls: `docs/notes/cloudflare-security-controls-evidence.md`.
- Mẫu rate-limit rules: `infra/cloudflare/security-controls/rate-limit-rules.example.json`.