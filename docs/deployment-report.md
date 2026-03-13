# Deployment Report — GitHub Push + Cloudflare Attempt

Ngày cập nhật: 2026-03-13  
Vai trò: DevOps

## 1) Phạm vi phiên deploy này

- Push toàn bộ thay đổi hợp lệ hiện tại lên GitHub theo commit plan atomic.
- Thử deploy frontend lên Cloudflare Pages bằng workflow/CLI nếu credential khả dụng.
- Thử xác nhận đường publish backend qua Cloudflare Tunnel theo skeleton hiện có.
- Thu evidence cho TLS/WAF/rate-limit/deploy status để phục vụ Security/QC.

## 2) Commit plan atomic

1. `feat: migrate smart parking workspace to current frontend and microservices layout`
   - Remove legacy monolith paths `smart_parking/`, `smart_parking_ui/`
   - Add current app workspaces như `backend-microservices/`, `spotlove-ai/`, `hardware/`
   - Include project docs/scripts cần thiết cho workspace hiện tại
2. `chore: add cloudflare deployment assets and release documentation`
   - `.github/workflows/*`
   - `infra/cloudflare/*`
   - `docs/architecture/*`, `docs/testing/*`, `docs/notes/*`
3. `chore: record deploy evidence and ignore local temp artifacts`
   - `.gitignore`
   - `docs/deployment-report.md`
   - `docs/notes/cloudflare-security-controls-evidence.md`
   - `docs/status.yaml`

## 3) Local preflight evidence

- Git remote: `origin -> https://github.com/haiminh287/smart_parkinglot.git`
- Branch hiện tại: `main`
- `wrangler whoami`: không authenticated
- Environment variables local cho Cloudflare: thiếu `CF_API_TOKEN`, `CF_ACCOUNT_ID`, `CF_PAGES_PROJECT`, `CF_TUNNEL_TOKEN`
- `cloudflared` có sẵn trên máy và đọc được tunnel list

## 4) Cloudflare Pages attempt status

- CLI direct deploy: **BLOCKED**
- Lý do cụ thể:
  - Không có local `wrangler` auth session
  - Không có local API token/account id/project name để gọi `wrangler pages deploy`
- Workflow path đã sẵn sàng: `.github/workflows/deploy-cloudflare-pages.yml`
- Cơ chế fallback khả dụng: push lên `main` để kích hoạt GitHub Actions nếu repository secrets đã được cấu hình trên GitHub

## 5) Cloudflare Tunnel attempt status

- `cloudflared tunnel list`: **PASS** ở mức local auth/tooling
- Local machine có tunnel credentials trong user profile
- Blocker để publish backend thật cho project hiện tại:
  - Chưa có hostname production được xác nhận cho dự án này
  - Chưa có bằng chứng Cloudflare zone nào thuộc project hiện tại
  - Chưa có origin reverse proxy/runtime host được xác nhận là target production thật
  - Local tunnel config hiện tại đang trỏ tới hostname khác, không đủ an toàn để tái sử dụng cho project này

## 6) Security evidence status

- TLS mode / SSL setting: **CHƯA VERIFY ĐƯỢC** bằng API/dashboard trong phiên này
- WAF managed rules: **CHƯA VERIFY ĐƯỢC** bằng API/dashboard trong phiên này
- Rate-limit rules: có baseline template tại `infra/cloudflare/security-controls/rate-limit-rules.example.json`
- Deploy URL / project name / environment status: **CHƯA CÓ** do chưa lấy được Pages project/zone production thực tế

## 7) Unblock checklist chính xác

### Để deploy frontend thật qua CLI hoặc workflow

1. Tạo GitHub repository secrets:
   - `CF_API_TOKEN`
   - `CF_ACCOUNT_ID`
   - `CF_PAGES_PROJECT`
   - `VITE_API_URL`
   - `VITE_WS_URL`
   - `VITE_GATEWAY_SECRET`
2. Xác nhận `CF_API_TOKEN` có quyền tối thiểu:
   - Cloudflare Pages Write
   - Account Read
3. Xác nhận Pages project name thực tế khớp với `CF_PAGES_PROJECT`
4. Push lại `main` hoặc chạy manual workflow dispatch

### Để publish backend thật qua Cloudflare Tunnel

1. Cung cấp production hostname chính xác, ví dụ `api.<domain>`
2. Cung cấp zone/domain ownership tương ứng trên Cloudflare
3. Cung cấp tunnel ID/token dành riêng cho project hoặc xác nhận tunnel hiện hữu được phép tái sử dụng
4. Cung cấp/verify origin reverse proxy endpoint thật, ví dụ `http://localhost:8088`
5. Sau đó chạy:
   - `cloudflared tunnel route dns <tunnel> <hostname>`
   - deploy runtime config từ `infra/cloudflare/cloudflared/config.example.yml`
   - smoke test `https://<hostname>/api/health` và `wss://<hostname>/ws/...`