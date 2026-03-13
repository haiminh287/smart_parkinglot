# Research: Snapshot issue/blocker trước fix-all + push + deploy Cloudflare

**Task:** ISSUE-SECURITY-BLOCKERS-2026-03-13  
**Ngày:** 2026-03-13  
**Researcher:** AI Research Agent  
**Loại research:** Release Readiness / Deployment Readiness / Blocker Consolidation

---

## 1. Tóm tắt (TL;DR)

> Trạng thái hiện tại chưa release-ready cho mục tiêu `fix-all + push + deploy Cloudflare`.  
> FE sanity mới nhất pass (65/65 tests + build pass), nhưng backend test vẫn có DB env blocker, dependency audit JS còn 15 vulnerabilities (7 high), và pipeline CI hiện trỏ sai project path (`dailytracking-*`).  
> Repo chưa có cấu hình Cloudflare thực thi (không có `wrangler.toml`, không thấy `cloudflared`, chưa có workflow deploy), nên deploy Cloudflare đang blocked ở mức hạ tầng/config.

---

## 2. Bối cảnh và Yêu cầu

- Yêu cầu từ Orchestrator: thu thập toàn bộ issue/blocker còn mở trước khi fix-all + push + deploy Cloudflare.
- Stack hiện tại (theo status + research trước):
  - FE: React + Vite (`spotlove-ai`)
  - BE: microservices Python (Django/FastAPI) + Go gateway/realtime (`backend-microservices`)
  - Runtime local phụ thuộc MySQL/Redis/RabbitMQ + gateway secret.
- Tiêu chí release-ready dùng trong report này:
  1. Không còn blocker test critical path (FE + BE integration cơ bản)
  2. Không còn security/dependency risk mức High chưa có mitigation
  3. Push/deploy pipeline khớp đúng repo hiện tại
  4. Cloudflare target architecture và config phải rõ + có secrets/env đầy đủ

---

## 3. Snapshot state hiện tại (resume context)

### 3.1 Trạng thái pipeline

- `docs/status.yaml` cho thấy task gần nhất đã đi qua implementer/tester/devops và có sanity FE pass sau cleanup.
- `blocked_reason` hiện ghi rõ: backend DB env blocker cũ vẫn còn ngoài scope sanity FE.
- Handoff mới nhất có artifact `docs/notes/devops-cleanup-git-snapshot.txt`.

### 3.2 Testing / QC snapshot

- FE:
  - `qc-fe-sanity.txt`: `npm run test` pass 65/65, `npm run build` pass.
- BE:
  - `docs/testing/bug-report.md` + `docs/testing/coverage-report.md`: chatbot/payment pytest fail vì DB access (`OperationalError 1045/2003`, Access denied/connection refused) sau khi gateway secret đã sync đúng.
- Coverage:
  - Không có coverage report cuối cùng cho run fail trước đó; chưa có bằng chứng đạt ngưỡng policy 80% unit / 60% integration.

### 3.3 Security / Dependency snapshot

- `npm-audit.json`:
  - Tổng: 15 vulnerabilities (7 high, 5 moderate, 3 low, 0 critical).
  - High nổi bật: `axios`, `@remix-run/router`/`react-router(-dom)`, `rollup`, `glob`/`minimatch`.
- `pip-audit.json`:
  - Từ sample hiện có: nhiều dependency với `"vulns": []`; chưa thấy evidence có lỗ hổng Python high trong snapshot hiện tại.

### 3.4 DevOps / Git snapshot

- `docs/notes/devops-cleanup-git-snapshot.txt` cho thấy working tree rất nhiễu (nhiều delete/modify/untracked cùng lúc).
- `docs/notes/devops-git-summary.txt`: entries lớn, deleted nhiều.
- `docs/notes/devops-status-focus.txt`: có file docs status/notes vẫn untracked.
- `docs/notes/devops-push-check.txt`: có log `main -> main`, nhưng snapshot khác vẫn cho thấy upstream chưa ổn định (`upstream=NONE` tại thời điểm chụp khác).

---

## 4. Danh sách Open Issues (actionable checklist)

### 4.1 Code bug

- [ ] **BUG-BE-ENV-DB-002**: chatbot/payment tests fail vì DB auth/connectivity (`Access denied` / `Can't connect to MySQL`) → chưa pass regression backend.
- [ ] **Config drift docs/runtime**: tài liệu cũ lệch runtime thực tế (đã nêu ở dead-code audit) làm tăng rủi ro vận hành sai.
- [ ] **Potential prod env gap FE**: `VITE_GATEWAY_SECRET` bắt buộc ngoài development; chưa có bằng chứng env production đã được set cho Cloudflare.

### 4.2 Test failure

- [ ] Backend regression suite cho `chatbot-service-fastapi` và `payment-service-fastapi` chưa green trong môi trường test chuẩn.
- [ ] Chưa có report coverage hợp lệ chứng minh đạt enterprise thresholds.

### 4.3 Security

- [ ] NPM dependency audit còn 7 High (release blocker cho production internet-facing).
- [ ] Một số cảnh báo build/toolchain (Vite/esbuild/router chain) liên quan security advisory chưa được khóa fix version.

### 4.4 Dependency

- [ ] Chưa có lock kế hoạch nâng phiên bản an toàn cho: `axios`, `react-router-dom`, `vite`, nhóm transitives (`minimatch`, `rollup`, `glob`, `lodash`, `js-yaml`).
- [ ] Chưa có artifact chứng minh re-run `npm audit` sau upgrade đạt mức chấp nhận.

### 4.5 Deployment / Cloudflare

- [ ] Không tìm thấy cấu hình Cloudflare hiện hữu: `wrangler.toml`, `_routes.json`, `cloudflared` config, Workers/Pages config file.
- [ ] Chưa có workflow deploy cho Cloudflare trong `.github/workflows`.
- [ ] CI hiện tại `.github/workflows/ci.yml` tham chiếu `dailytracking-backend` / `dailytracking-frontend` (không khớp repo hiện tại) → pipeline unreliable.

### 4.6 Git / Push

- [ ] Working tree có quá nhiều thay đổi hỗn hợp, thiếu baseline sạch để release tag.
- [ ] Trạng thái upstream/push không nhất quán giữa các snapshot, cần xác nhận remote tracking trước release.

---

## 5. Priority P0/P1/P2 (theo tiêu chí release-ready)

### P0 — Must fix trước deploy

1. Backend test blocker DB cho chatbot/payment (không green backend).
2. Cloudflare deployment config chưa tồn tại (không thể deploy có kiểm soát).
3. CI path mismatch (`dailytracking-*`) làm mất giá trị gate trước release.
4. NPM audit còn High vulnerabilities chưa mitigation/upgrade.
5. Git release hygiene chưa sạch (khó xác thực phạm vi thay đổi trước push/deploy).

### P1 — Nên hoàn tất ngay sau P0 (trước production cutover)

1. Chuẩn hóa env docs cho production (`.env.example` FE/BE + secret inventory).
2. Bổ sung coverage artifacts và tiêu chí pass/fail rõ ràng trong QC gate.
3. Chốt docs lệch runtime (README/overview) để tránh sai thao tác vận hành.

### P2 — Theo dõi sau khi go-live ổn định

1. Giảm cảnh báo bundle/chunk (không block deploy, nhưng ảnh hưởng maintainability/perf).
2. Dọn artifact/log retention policy triệt để (nếu Orchestrator muốn giảm noise lâu dài).

---

## 6. Cloudflare deployment readiness matrix

| Hạng mục | Mức sẵn sàng hiện tại | Evidence trong repo | Blocker chính | Cần làm cụ thể |
|---|---|---|---|---|
| **Cloudflare Pages (FE static từ `spotlove-ai`)** | **Partial** | FE build pass; Vite app có thể xuất static | Không có Pages project config, env prod chưa định nghĩa, chưa có pipeline deploy | Tạo Pages project; map build command/output; set env vars (`VITE_*`); cấu hình domain + DNS |
| **Cloudflare Workers (API edge)** | **Not Ready** | Không có `wrangler.toml`, không có worker source/deploy script | Backend hiện là microservices Python/Go + DB stateful, không tương thích lift-and-shift lên Workers ngay | Nếu muốn Workers chỉ làm edge gateway: cần thiết kế mới route/auth/cache + service bindings |
| **Cloudflare Tunnel (đưa origin hiện tại ra internet an toàn)** | **Not Ready** | Không thấy `cloudflared` config/credentials | Chưa có tunnel ID/token, ingress rules, origin host mapping | Tạo tunnel, config ingress cho FE/API/WS, chạy cloudflared tại host origin |
| **Cloudflare Zero Trust (Access/WAF policy tầng org)** | **Not Ready** | Không có policy config/tài liệu | Chưa define app access policy, identity provider, service tokens | Thiết lập Access policy cho admin routes/API nội bộ; cấp service tokens cho CI |
| **WebSocket qua Cloudflare** | **Risk** | FE dùng `VITE_WS_URL` hoặc fallback endpoint runtime | Chưa có endpoint `wss://` production chuẩn + route qua gateway/realtime xác thực | Chốt public WS URL, TLS termination, auth header/token strategy |
| **CI/CD deploy Cloudflare** | **Not Ready** | Chỉ có `ci.yml` và đang mismatch project path | Không có deploy workflow + thiếu secrets (`CF_API_TOKEN`, `CF_ACCOUNT_ID`, project names) | Tạo workflow deploy riêng cho Pages/Tunnel; chuẩn hóa branch/tag gating |

---

## 7. Checklist thực thi cực cụ thể theo vai trò

### 7.1 Implementer

- [ ] Đồng bộ file CI sang đúng paths repo thật (`spotlove-ai`, `backend-microservices/*`) trước.
- [ ] Chốt chiến lược backend test DB: dùng test DB compose riêng hoặc fixtures/mock cho case không cần DB thật.
- [ ] Tạo `spotlove-ai/.env.example` (hiện chưa có) với biến tối thiểu cho production build.
- [ ] Bump dependencies JS có advisory High và cập nhật lockfile.
- [ ] Re-run build/test local sau upgrade để bắt breaking changes.

### 7.2 Tester

- [ ] Chạy lại FE regression + build trên clean env; lưu artifact pass.
- [ ] Chạy backend tests với DB test hợp lệ (không dùng dev DB), xác nhận hết lỗi 1045/2003.
- [ ] Xuất coverage report có số liệu rõ cho FE/BE.
- [ ] Gắn bug matrix: fixed / remaining / env-only.

### 7.3 Security

- [ ] Re-run `npm audit --json` sau dependency upgrades và xác nhận không còn High/Critical.
- [ ] Xác minh không hardcode secret trong repo theo scope thay đổi mới.
- [ ] Rà soát cấu hình CORS, gateway secret propagation, WS auth trước public exposure qua Cloudflare.
- [ ] Đánh giá risk acceptance cho vulnerabilities còn lại (nếu có).

### 7.4 DevOps

- [ ] Quyết định target deploy Cloudflare chính: Pages-only FE + origin backend qua Tunnel (khả thi nhất với repo hiện trạng).
- [ ] Tạo/điền GitHub secrets: `CF_API_TOKEN`, `CF_ACCOUNT_ID`, `CF_PAGES_PROJECT`, (nếu tunnel: `CF_TUNNEL_TOKEN`).
- [ ] Tạo workflow deploy Cloudflare riêng (staging/prod), có gate sau test + security pass.
- [ ] Thiết lập DNS routes: FE domain (Pages), API/WS subdomain trỏ tunnel/origin.
- [ ] Smoke test public endpoints HTTPS/WSS sau deploy, rollback plan sẵn.

---

## 8. Danh sách file likely cần sửa

### 8.1 Release gate / pipeline / deploy

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-cloudflare.yml` (mới)
- `docs/status.yaml`

### 8.2 Frontend deploy readiness

- `spotlove-ai/package.json`
- `spotlove-ai/vite.config.ts`
- `spotlove-ai/.env.example` (mới)
- `spotlove-ai/README.md`

### 8.3 Backend test/deploy readiness

- `backend-microservices/docker-compose.yml`
- `backend-microservices/.env.example`
- `backend-microservices/chatbot-service-fastapi/app/config.py`
- `backend-microservices/payment-service-fastapi/app/config.py`

### 8.4 Hygiene

- `.gitignore`
- `docs/testing/coverage-report.md`
- `docs/testing/bug-report.md`

---

## 9. Tool blocker & fallback

- **Tool limitation gặp phải:** một số file output lớn khi đọc trực tiếp trả về đường dẫn tạm ngoài allowed directories, không thể mở lại bằng filesystem tool.
- **Fallback đã áp dụng:**
  1. Đọc file theo phần (`head`/`tail`) để lấy metadata cần thiết.
  2. Dùng semantic search để trích đoạn có ngữ cảnh từ file lớn (status, audit, research cũ).
  3. Đối chiếu chéo nhiều artifact (`docs/testing/*`, `docs/notes/*`, `npm-audit.json`, `pip-audit.json`) để tránh kết luận dựa 1 nguồn.

---

## 10. Nguồn tham khảo

| # | URL/Path | Mô tả |
|---|---|---|
| 1 | `docs/status.yaml` | Snapshot trạng thái task/handoff/blocker hiện tại |
| 2 | `docs/testing/bug-report.md` | Danh sách bug testing gần nhất |
| 3 | `docs/testing/coverage-report.md` | Regression + coverage context |
| 4 | `qc-fe-sanity.txt` | FE sanity mới nhất PASS |
| 5 | `docs/notes/devops-cleanup-git-snapshot.txt` | Git working tree snapshot |
| 6 | `docs/notes/devops-git-summary.txt` | Tổng hợp số lượng thay đổi |
| 7 | `docs/notes/devops-push-check.txt` | Push check log |
| 8 | `.github/workflows/ci.yml` | CI pipeline hiện tại (mismatch paths) |
| 9 | `npm-audit.json` | Dependency vulnerabilities JS |
|10 | `pip-audit.json` | Dependency vulnerabilities Python |
|11 | `spotlove-ai/package.json` | Scripts/build hiện tại FE |
|12 | `spotlove-ai/.env` | Biến môi trường FE hiện dùng |
|13 | `docs/research/ISSUE-SECURITY-BLOCKERS-2026-03-13-dead-code-audit.md` | Baseline research trước đó |
|14 | `docs/research/ISSUE-SECURITY-BLOCKERS-2026-03-13-safe-remove-refresh.md` | Refresh cleanup scope |

---

_Research được thực hiện bởi AI Research Agent — facts-first, cần Architect/DevOps xác nhận quyết định kiến trúc deploy cuối cùng._
