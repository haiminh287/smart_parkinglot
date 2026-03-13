# Deployment Report — GitHub Push + Cloudflare Attempt

Ngày cập nhật: 2026-03-13  
Vai trò: DevOps

## 1) Phạm vi phiên deploy này

- Push toàn bộ thay đổi hợp lệ hiện tại lên GitHub theo commit plan atomic.
- Thử deploy frontend lên Cloudflare Pages bằng workflow/CLI nếu credential khả dụng.
- Thử xác nhận đường publish backend qua Cloudflare Tunnel theo skeleton hiện có.
- Thu evidence cho TLS/WAF/rate-limit/deploy status để phục vụ Security/QC.

## 2) Commit plan atomic

1. `feat: migrate smart parking workspace`
    - Commit: `1666ab1`
   - Remove legacy monolith paths `smart_parking/`, `smart_parking_ui/`
   - Add current app workspaces như `backend-microservices/`, `spotlove-ai/`, `hardware/`
   - Include project docs/scripts cần thiết cho workspace hiện tại
2. `chore: add cloudflare deployment assets and release docs`
    - Commit: `29952c1`
   - `.github/workflows/*`
   - `infra/cloudflare/*`
   - `docs/architecture/*`, `docs/testing/*`, `docs/notes/*`
3. `chore: record deploy evidence and ignore local temp artifacts`
    - Commit: `47522c5`
   - `.gitignore`
   - `docs/deployment-report.md`
   - `docs/notes/cloudflare-security-controls-evidence.md`
   - `docs/status.yaml`

## 3) Git push result

- Branch pushed: `main`
- Local HEAD: `47522c5d9608050995cbeb5d576d6813cabcdf9d`
- Remote `origin/main`: `47522c5d9608050995cbeb5d576d6813cabcdf9d`
- Push status: `PASS`
- Remote warnings:
   - `backend-microservices/ai-service-fastapi/ml/models/cash_recognition_best.pth` = `51.47 MB`, vượt mức khuyến nghị `50 MB` của GitHub nhưng push vẫn thành công

## 4) Local preflight evidence

- Git remote: `origin -> https://github.com/haiminh287/smart_parkinglot.git`
- Branch hiện tại: `main`
- `wrangler whoami`: không authenticated
- Environment variables local cho Cloudflare: thiếu `CF_API_TOKEN`, `CF_ACCOUNT_ID`, `CF_PAGES_PROJECT`, `CF_TUNNEL_TOKEN`
- `cloudflared` có sẵn trên máy và đọc được tunnel list

## 5) Cloudflare Pages attempt status

- CLI direct deploy: **BLOCKED**
- Lý do cụ thể:
  - Không có local `wrangler` auth session
  - Không có local API token/account id/project name để gọi `wrangler pages deploy`
- Workflow path đã sẵn sàng: `.github/workflows/deploy-cloudflare-pages.yml`
- Push lên `main` đã hoàn tất nên workflow *có thể* đã được kích hoạt theo path filter
- Kết quả workflow hiện **KHÔNG VERIFY ĐƯỢC** trong phiên này vì:
   - GitHub Actions page probe trả `404`
   - GitHub Actions REST API cho repo này trả `404`
   - Không có GitHub auth/session để xem run của repository private hoặc restricted
- Deploy URL / Pages project name: **CHƯA THU ĐƯỢC**

## 6) Cloudflare Tunnel attempt status

- `cloudflared tunnel list`: **PASS** ở mức local auth/tooling
- Local machine có tunnel credentials trong user profile
- Tunnel nhìn thấy được qua local auth: `fcba5010-2361-42db-8ba4-b150c36d866a` (`dailytracking`)
- Local runtime config hiện có:
   - Tunnel file: `6fb90bf1-7fe4-4855-9bdc-d6d882aab876.json`
   - Hostnames: `ghepdoicaulong.shop`, `www.ghepdoicaulong.shop`
- Blocker để publish backend thật cho project hiện tại:
  - Chưa có hostname production được xác nhận cho dự án này
  - Chưa có bằng chứng Cloudflare zone nào thuộc project hiện tại
  - Chưa có origin reverse proxy/runtime host được xác nhận là target production thật
  - Local tunnel config hiện tại đang trỏ tới hostname khác, không đủ an toàn để tái sử dụng cho project này

## 7) Security evidence status

- TLS mode / SSL setting: **CHƯA VERIFY ĐƯỢC** bằng API/dashboard trong phiên này
- WAF managed rules: **CHƯA VERIFY ĐƯỢC** bằng API/dashboard trong phiên này
- Rate-limit rules: có baseline template tại `infra/cloudflare/security-controls/rate-limit-rules.example.json`
- Deploy URL / project name / environment status: **CHƯA CÓ** do chưa lấy được Pages project/zone production thực tế

## 8) Unblock checklist chính xác

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