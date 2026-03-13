# Spotlove AI Frontend

Frontend React + Vite cho hệ thống Smart Parking.

## Local development

Yêu cầu: Node.js 20+, npm.

```bash
npm ci
cp .env.example .env
npm run dev
```

## Build & test

```bash
npm run lint
npm run test
npm run build
```

## Environment variables

Khai báo trong `.env` (local) hoặc Cloudflare Pages (production):

- `VITE_API_URL`: public API base URL, ví dụ `https://api.example.com/api`
- `VITE_WS_URL`: public WebSocket URL, ví dụ `wss://api.example.com/ws`
- `VITE_GATEWAY_SECRET`: shared gateway secret (không commit secret thật)

## Deploy Cloudflare Pages

Workflow deploy: `.github/workflows/deploy-cloudflare-pages.yml`.

Cần cấu hình GitHub Secrets ở repository:

- `CF_API_TOKEN`
- `CF_ACCOUNT_ID`
- `CF_PAGES_PROJECT`
- `VITE_API_URL`
- `VITE_WS_URL`
- `VITE_GATEWAY_SECRET`

Workflow sẽ fail-fast nếu thiếu bất kỳ secret bắt buộc nào.

Build output dùng cho Pages là `dist/`.

## Routing contract production

- App: `https://app.<domain>` (Cloudflare Pages)
- API: `https://api.<domain>/api/*`
- WS: `wss://api.<domain>/ws/*`
