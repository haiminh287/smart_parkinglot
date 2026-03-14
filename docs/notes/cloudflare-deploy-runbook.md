# Cloudflare Deploy Runbook (Pages + Tunnel)

## 1) Mục tiêu

- Deploy frontend qua Cloudflare Pages.
- Public backend qua Cloudflare Tunnel + reverse proxy origin.
- Giữ contract public: `/api/*` và `/ws/*`.

---

## 2) Prerequisites

- Đã tạo Cloudflare Pages project cho frontend.
- Đã tạo Cloudflare Tunnel cho `ghepdoicaulong.shop`.
- `cloudflared` đã được cài trên máy Windows.
- Docker Desktop đang chạy với backend-microservices compose.
- Nginx serve FE dist/ tại port 80.
- GitHub Secrets có sẵn:
  - `CF_API_TOKEN`
  - `CF_ACCOUNT_ID`
  - `CF_PAGES_PROJECT`
  - `VITE_API_URL`
  - `VITE_WS_URL`
  - `VITE_GATEWAY_SECRET`

---

## 3) Tạo Cloudflare Tunnel (một lần)

```powershell
# 1. Cài cloudflared (nếu chưa có)
winget install --id Cloudflare.cloudflared

# 2. Đăng nhập Cloudflare
cloudflared tunnel login

# 3. Tạo tunnel
cloudflared tunnel create ghepdoicaulong

# Lệnh trên sẽ in ra:
#   Tunnel credentials written to C:\Users\MINH\.cloudflared\<TUNNEL_ID>.json
#   Created tunnel ghepdoicaulong with id <TUNNEL_ID>

# 4. Ghi nhớ TUNNEL_ID – dùng ở bước tiếp theo
```

---

## 4) DNS Records cần tạo trên Cloudflare Dashboard

> Vào **Cloudflare Dashboard → ghepdoicaulong.shop → DNS → Add record**

| Type  | Name                      | Target                               | Proxy |
|-------|---------------------------|--------------------------------------|-------|
| CNAME | `ghepdoicaulong.shop`     | `<TUNNEL_ID>.cfargotunnel.com`       | ✅ ON |
| CNAME | `api.ghepdoicaulong.shop` | `<TUNNEL_ID>.cfargotunnel.com`       | ✅ ON |
| CNAME | `ws.ghepdoicaulong.shop`  | `<TUNNEL_ID>.cfargotunnel.com`       | ✅ ON |

> Thay `<TUNNEL_ID>` bằng ID thật từ bước 3.

**Hoặc dùng CLI:**
```bash
cloudflared tunnel route dns ghepdoicaulong ghepdoicaulong.shop
cloudflared tunnel route dns ghepdoicaulong api.ghepdoicaulong.shop
cloudflared tunnel route dns ghepdoicaulong ws.ghepdoicaulong.shop
```

---

## 5) Điền Tunnel ID vào config

```powershell
# Cách 1: Auto-patch qua deploy script
.\scripts\deploy-local.ps1 -TunnelId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Cách 2: Sửa thủ công
# Mở: infra/cloudflare/cloudflared/config.yml
# Thay: <TUNNEL_ID_PLACEHOLDER> → tunnel ID thật
```

---

## 6) Deploy toàn bộ (một lệnh)

```powershell
# Từ thư mục gốc project
.\scripts\deploy-local.ps1 -TunnelId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

Script sẽ tự động:
1. Kiểm tra prerequisites (node, npm, docker, cloudflared)
2. Patch Tunnel ID vào config.yml
3. Build FE (`spotlove-ai/dist/`)
4. Start Docker Compose với prod override
5. Health check port 80 + 8000
6. Start cloudflared tunnel (background)

---

## 7) Deploy frontend qua Cloudflare Pages (CI)

1. Cập nhật env Pages:
   - `VITE_API_URL=https://api.ghepdoicaulong.shop`
   - `VITE_WS_URL=wss://ws.ghepdoicaulong.shop`
   - `VITE_GATEWAY_SECRET=<secret thật trên dashboard>`
2. Push `main` → workflow `deploy-cloudflare-pages.yml` tự chạy.
3. Verify trong GitHub Actions + Cloudflare Pages Dashboard.

### Option: Build dist/ và commit vào repo (cho local tunnel serve)

```powershell
# Push tag → CI build và commit dist/ vào main
git tag v1.0.0 && git push origin v1.0.0

# Hoặc trigger thủ công qua GitHub Actions
# → workflow_dispatch → build_and_commit_dist=true
```

---

## 8) Checklist deploy thủ công

- [ ] `cloudflared tunnel list` hiển thị tunnel `ghepdoicaulong`
- [ ] DNS records đã tạo đủ 3 CNAME trên Dashboard
- [ ] `infra/cloudflare/cloudflared/config.yml` đã điền Tunnel ID thật (không còn placeholder)
- [ ] `VITE_GATEWAY_SECRET` đã set trong env
- [ ] `spotlove-ai/dist/index.html` tồn tại
- [ ] Docker Compose đang chạy: `docker compose ps` → tất cả services Up
- [ ] `http://localhost/nginx-health` → 200 OK
- [ ] `http://localhost:8000/api/health` → 200 OK
- [ ] cloudflared process đang chạy (check `Get-Process cloudflared`)
- [ ] Truy cập `https://ghepdoicaulong.shop` → FE load thành công
- [ ] Truy cập `https://api.ghepdoicaulong.shop/api/health` → 200 OK

---

## 9) Rollback nhanh

### FE rollback
1. Trong Cloudflare Pages, promote deployment trước đó.
2. Nếu lỗi env, restore env snapshot trước deploy và redeploy.

### Tunnel rollback
```powershell
# Dừng tunnel
Stop-Process -Name cloudflared -Force

# Restart về config cũ
cloudflared tunnel --config infra/cloudflare/cloudflared/config.yml run
```

### API rollback
1. `docker compose -f docker-compose.yml -f docker-compose.prod.yml down`
2. Revert docker-compose.prod.yml về version trước.
3. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
4. Kiểm tra `GET /api/health` và WS handshake.

---

## 10) Lưu ý an toàn

- Không commit secret thật vào repo.
- TLS mode ở Cloudflare: `Full (strict)`.
- Bật WAF managed rules và rate limit auth/chatbot endpoints.
- Credentials file `.cloudflared/<TUNNEL_ID>.json` không commit vào repo.

---

## 11) Cấu trúc files đã tạo

```
infra/
  cloudflare/
    cloudflared/
      config.yml               ← Tunnel config (điền TUNNEL_ID)
      config.yml.example       ← Example cũ (tham khảo)
  nginx/
    nginx.conf                 ← Serve FE + proxy API/WS

backend-microservices/
  docker-compose.prod.yml      ← Override: nginx service + CORS headers

scripts/
  deploy-local.ps1             ← Script deploy một lệnh

spotlove-ai/
  .env.production              ← Env vars cho ghepdoicaulong.shop

.github/workflows/
  deploy-cloudflare-pages.yml  ← CI: Pages deploy + build-and-commit-dist (tag v*)
```

---

## 12) Security evidence artifacts

- Mẫu evidence controls: `docs/notes/cloudflare-security-controls-evidence.md`.
- Mẫu rate-limit rules: `infra/cloudflare/security-controls/rate-limit-rules.example.json`.
