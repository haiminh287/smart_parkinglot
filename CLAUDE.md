# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ParkSmart / smartparkinglot** — monorepo cho hệ thống bãi giữ xe thông minh (khóa luận). Gồm 4 "quốc gia":

- `backend-microservices/` — 10 microservices (Django REST + FastAPI + Go), deploy qua Docker Compose.
- `spotlove-ai/` — React 18 + Vite + Tailwind SPA (Redux Toolkit + React Query + shadcn/ui). Triển khai Cloudflare Pages.
- `ParkingSimulatorUnity/` — Unity 2022.3.62f3 LTS Digital Twin simulator (6 virtual cameras, 158 procedural slots) gọi backend thật qua HTTP/WS để E2E test không cần phần cứng.
- `hardware/`, `infra/` (Cloudflare tunnel + nginx), `scripts/deploy-local.ps1`.

Source of truth thiết kế: `docs/architecture/context.md` + các file `docs/architecture/adr-*.md` và `docs/architecture/fix-all-cloudflare-release-plan-2026-03-13.md`. Khi có conflict giữa file này và `docs/architecture/context.md`, **context.md thắng**.

## Common commands

All commands assume the working directory in the header of each section.

### Full stack (Docker) — `backend-microservices/`

```bash
# Bring everything up (mysql, redis, rabbitmq + 10 services + gateway)
docker compose up -d --build

# Tail one service
docker compose logs -f booking-service

# Rebuild one service after code change
docker compose up -d --build booking-service

# Stop + wipe volumes (destructive — confirm before running)
docker compose down -v
```

Required env vars (fail-fast in compose): `DB_USER`, `DB_PASSWORD`, `SECRET_KEY`, `RABBITMQ_USER`, `RABBITMQ_PASS`, `GATEWAY_SECRET`. Template in `backend-microservices/.env.example`.

Host ports exposed: gateway `8000`, auth `8001`, booking `8002`, parking `8003`, realtime WS `8006`, ai `8009`, mysql `3307`, redis `6379`, rabbitmq `5672/15672`. `vehicle-service`, `notification-service-fastapi`, `payment-service-fastapi`, `chatbot-service-fastapi` **chỉ `expose`** internal — phải đi qua gateway.

### Django services (auth, parking, booking, vehicle)

Cùng pattern cho cả 4 service. Chạy trực tiếp ngoài Docker:

```bash
cd backend-microservices/<service>
pip install -r requirements.txt
export PYTHONPATH="$(pwd)/..:$(pwd)/../shared"   # Windows: set PYTHONPATH=..;..\shared
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

# Tests (pytest-django, config via pytest.ini)
pytest
pytest tests/path/to/test_file.py::TestClass::test_case
python manage.py check        # smoke check — used in CI
```

`booking-service` còn có Celery worker + beat (broker `redis://redis:6379/0`):

```bash
celery -A booking_service worker --loglevel=info
celery -A booking_service beat --loglevel=info
```

### FastAPI services (ai, chatbot, notification, payment)

```bash
cd backend-microservices/<service>
pip install -r requirements.txt
uvicorn app.main:app --reload --port <port>   # ports: ai 8009, chatbot 8008, notification 8005, payment 8007

pytest                                         # asyncio_mode=auto trong pytest.ini
pytest tests/test_foo.py -k test_bar -v
```

AI service đặc biệt: pre-warm YOLO model trong `lifespan()`; weights ở `app/ml/models/` (gitignored — `*.pt` trong `.gitignore`). Serving saved plate crops qua mount `/ai/images/` → `app/images/`.

### Go services (gateway, realtime)

```bash
cd backend-microservices/gateway-service-go     # hoặc realtime-service-go
go run ./cmd/server
go test ./...
go test ./internal/handler -run TestProxy
```

Go modules: `gateway-service` / `realtime-service` (go 1.22, gin + go-redis + godotenv).

### Frontend — `spotlove-ai/`

```bash
npm ci
cp .env.example .env                # phải set VITE_GATEWAY_SECRET, VITE_API_URL, VITE_WS_URL
npm run dev                         # Vite dev server at :8080, proxies /api→gateway, /ws→realtime, /ai/cameras→ai
npm run lint
npm run test                        # vitest run
npm run test:watch
npm run build
npm run e2e                         # Playwright; spec ở spotlove-ai/e2e/
npx playwright test e2e/booking-full-flow.spec.ts -g "full booking"
```

Build fails hard ngoài `mode=development` nếu thiếu `VITE_GATEWAY_SECRET` — xem `spotlove-ai/vite.config.ts`.

### Unity simulator — `ParkingSimulatorUnity/`

Mở bằng Unity Hub với editor **2022.3.62f3**. Chạy scene Play mode để simulator gọi vào backend qua `ApiService` (`Assets/Scripts/API/ApiService.cs`) + `AuthManager`. Trước khi Play, seed dữ liệu Unity tương thích:

```bash
cd backend-microservices
python seed_unity_test_data.py
python seed_unity_slots.py
```

Không có "unity build from CLI" workflow. Tests Unity ở `ParkingSim.Tests.EditMode` / `ParkingSim.Tests.PlayMode` (`.csproj` tương ứng).

### Top-level E2E / seed scripts — `backend-microservices/`

```bash
python seed_e2e_data.py                  # setup fixtures cho Playwright
python seed_admin_test_data.py
python test_e2e_full_flow.py             # standalone HTTP E2E (không phải pytest)
python test_ai_full.py
python test_chatbot_e2e.py
```

Các file `test_*.py` ở **root `backend-microservices/`** là **script E2E standalone** (chạy bằng `python`), **không phải** pytest suite — đừng nhầm với tests trong từng service.

## Architecture — the load-bearing parts

### 1. Gateway-based trust model (đọc cái này trước tiên)

Không service nào trong `backend-microservices/` tự xác thực user. Luồng:

1. Client (FE hoặc Unity) gửi request tới gateway `:8000`.
2. `gateway-service-go` (một file `internal/router/routes.go` với **một catch-all `r.Any("/*path")`**) xử lý session, auth login/logout/OAuth callback và rate limiting.
3. Gateway proxy request đến service đích, thêm headers:
   - `X-Gateway-Secret: <GATEWAY_SECRET>`
   - `X-User-ID`, `X-User-Email`
4. Mọi Django service phải có `shared.gateway_middleware.GatewayAuthMiddleware` (xem `backend-microservices/shared/gateway_middleware.py`) — nó **reject 403** nếu `X-Gateway-Secret` không khớp, **ngoại trừ** các path public:
   - `/auth/login/`, `/auth/register/`, `/auth/logout/`, `/auth/forgot-password/`, `/auth/reset-password/`, `/auth/password-reset/`, `/auth/google/`, `/auth/facebook/`, `/health/`, `/admin/`, `/_test/`.
5. FastAPI services có middleware tương đương: `app/middleware/gateway_auth.py` (ví dụ `ai-service-fastapi/app/middleware/gateway_auth.py`).
6. **`request.user` không tồn tại** — Django middleware set `request.user_id` (UUID string) và `request.user_email` từ headers. Không dùng `django.contrib.auth.User`.

**Auth contract notes** (xem `backend-microservices/auth-service/README.md`):

- Session-cookie based, **không có refresh token endpoint**. Route `/auth/refresh/` và `/auth/token/refresh/` bị gateway reject cố ý (`HandleUnsupportedRefresh`).
- Django admin bị **disable** trong các service (`# 'django.contrib.admin'` bị comment trong `INSTALLED_APPS` của `parking_service/settings.py`, `booking_service/settings.py`, …). Không thêm lại.

### 2. Inter-service communication

Services gọi nhau qua internal Docker DNS (xem env vars trong `backend-microservices/docker-compose.yml`):

- `BOOKING_SERVICE_URL=http://booking-service:8000`
- `PARKING_SERVICE_URL=http://parking-service:8000`
- `VEHICLE_SERVICE_URL=http://vehicle-service:8000`
- `AUTH_SERVICE_URL=http://auth-service:8000`
- `NOTIFICATION_SERVICE_URL=http://notification-service-fastapi:8005`
- `PAYMENT_SERVICE_URL=http://payment-service-fastapi:8007`
- `REALTIME_SERVICE_URL=http://realtime-service-go:8006`
- `AI_SERVICE_URL=http://ai-service-fastapi:8009`
- `CHATBOT_SERVICE_URL=http://chatbot-service-fastapi:8008`

Service-to-service HTTP request phải tự gửi `X-Gateway-Secret` (GATEWAY_SECRET shared env) — nếu không sẽ bị middleware 403. Event-driven async (booking confirmation → notification, etc.) đi qua **RabbitMQ** (`amqp://` từ env `RABBITMQ_URL`). Realtime push về browser đi qua **WebSocket** của `realtime-service-go` ở `:8006` (FE connect trực tiếp, **không** proxy qua gateway).

### 3. Redis DB allocation (cố định — đừng va chạm)

| DB  | Dùng cho                              |
| --- | ------------------------------------- |
| 0   | Celery broker + result backend        |
| 1   | `auth-service` + gateway session      |
| 2   | `booking-service`                     |
| 3   | `parking-service`                     |
| 4   | `vehicle-service`                     |
| 5   | `realtime-service-go`                 |
| 6   | `chatbot-service-fastapi`             |

### 4. Shared Python package — `backend-microservices/shared/`

Là **installable package** (`setup.py`, `parksmart_shared.egg-info`). Được mount vào mỗi container qua `volumes: - ./shared:/app/shared` và exposed qua `PYTHONPATH=/app:/app/shared`. Chạy Django service ngoài Docker phải set `PYTHONPATH` tương đương. Nội dung chính: `gateway_middleware.py`, `gateway_permissions.py`, `permissions.py`, `requirements-base.txt` (nguồn chung cho Django + Starlette pin fixes).

### 5. Frontend architecture — `spotlove-ai/src/`

- Layer rõ ràng:
  - `services/api/*.api.ts` — axios clients + endpoint constants (`endpoints.ts`, `axios.client.ts`).
  - `services/business/*.service.ts` — orchestration + mapping, **FE code chỉ được import từ tầng này**, không import trực tiếp `api/`.
  - `store/slices/*Slice.ts` — Redux Toolkit slices (auth, booking, parking, notification, websocket).
  - `services/websocket.service.ts` — kết nối `VITE_WS_URL` (`wss://.../ws/*` production, `ws://localhost:8006` dev qua proxy).
- Router: React Router v6, pages ở `src/pages/` (user pages root + `src/pages/admin/`). **React.lazy code splitting** được áp dụng cho tất cả page routes (S2-IMP-8).
- UI: shadcn/ui + Radix primitives trong `src/components/ui/` — khi thêm component mới ưu tiên compose các primitive này.
- Dev proxy: `/api` → gateway, `/ws` → realtime, `/ai/cameras` → ai service trực tiếp (camera streams bypass gateway auth vì `<img>` tags không gửi header).
- **FE layering enforced (S2-IMP-9):** pages/components/store chỉ được import từ `services/business/*` — KHÔNG import trực tiếp `services/api/*`. ESLint `no-restricted-imports` rule enforce convention này.

### 6. AI service pipeline

`ai-service-fastapi` đóng vai license plate OCR (YOLO + EasyOCR/TrOCR fallback), parking slot occupancy (YOLO11n, xem `docs/architecture/adr-004-yolo11n-parking-occupancy.md`), banknote classifier (MobileNetV3, ADR-005). Routers ở `app/routers/`: `detection`, `training`, `metrics`, `parking`, `esp32`, `camera`. Lifespan khởi động pre-warm slot detector + `camera_monitor` background worker — **không gọi trực tiếp** `get_slot_detector()` trong request path trước khi lifespan chạy. Virtual camera streaming contract mô tả ở `docs/architecture/ADR-virtual-camera-system.md` và `docs/architecture/VIRTUAL-CAMERA-implementation-guide.md`.

### 7. Unity simulator integration

Scripts quan trọng (`ParkingSimulatorUnity/Assets/Scripts/`):

- `Core/ParkingManager.cs` — Singleton + MonoBehaviour orchestrator, lifecycle + gate/queue/camera wiring.
- `API/ApiService.cs`, `API/AuthManager.cs`, `API/DataModels.cs` — REST client tương đương FE, dùng cùng gateway.
- `Camera/GateCameraSimulator.cs`, `Camera/VirtualCameraManager.cs` — stream frames lên `ai-service-fastapi`.
- `IoT/ESP32Simulator.cs` — giả lập IoT barrier device, gọi routes `/ai/esp32/*`.
- `Vehicle/LicensePlateCreator.cs`, `Vehicle/VehicleQueue.cs` — spawn xe với biển số Việt Nam thật.

Unity simulator **cần seed dữ liệu tương thích** (xem `seed_unity_test_data.py` + `seed_unity_slots.py`) trước khi Play — slot codes phải match với `cached floors/slots` mà `ParkingManager` fetch lúc khởi động.

## Conventions ngầm định (quan trọng để khỏi review bị bật ngược)

Nguồn: `.github/copilot-instructions.md` (Enterprise Coding Standards v10) + patterns đã áp dụng trong repo.

- **Ngôn ngữ:** docs / commit body / comment giải thích **tiếng Việt**; tên biến / hàm / class / commit type prefix / log message **tiếng Anh**. Đừng dịch code sang tiếng Việt.
- **Commit format:** Conventional commits `{type}({scope}): {desc}` — types đang dùng: `feat fix refactor test docs chore ci perf style build`. Không `git add .` — add theo file. Không force push `main`.
- **Error handling:** API response lỗi theo shape `{ success: false, error: { code, message, details } }`. Log structured JSON không chứa PII/token/password.
- **Naming:** Python `snake_case`, TS/JS `camelCase`/`PascalCase`, Go theo gofmt. Boolean phải có prefix `is_`/`has_`/`can_`.
- **Function ≤ 50 lines, file ≤ 300 lines, nesting ≤ 4, params ≤ 4** — nếu vượt, DTO hoá.
- **Dead code policy:** sau mỗi task, xoá approach-drift file, không để lại `.old`/`.bak`/`_backup` trong `src/`, không để commented-out block > 10 dòng, không `console.log`/`print` debug.
- **FastAPI `.env` fail-fast:** `chatbot-service-fastapi/app/config.py`, `payment-service-fastapi/app/config.py` fail-fast nếu thiếu biến bắt buộc. Đừng thêm fallback "default safe value" — pattern này có lịch sử (ref `docs/notes/cloudflare-security-controls-evidence.md`).
- **Image/model weights gitignored:** `*.pt *.pth *.onnx *.h5 *.tflite *.pb`, `backend-microservices/ai-service-fastapi/app/images/`, `booking-*.png`, `booking_qr_*.svg`. Đừng commit.
- **Public routing contract (production Cloudflare):** app ở `https://app.<domain>`, API ở `https://api.<domain>/api/*`, WS ở `wss://api.<domain>/ws/*`. Workflow deploy Cloudflare Pages ở `.github/workflows/deploy-cloudflare-pages.yml` — required GitHub secrets: `CF_API_TOKEN`, `CF_ACCOUNT_ID`, `CF_PAGES_PROJECT`, `VITE_API_URL`, `VITE_WS_URL`, `VITE_GATEWAY_SECRET`.

## Debugging guideposts

- Reference status history trong `docs/status.yaml` (phiên làm việc gần nhất, blocker).
- Full E2E kết quả & screenshots: `docs/report.md`.
- Audit/pipaudit artifacts theo service: `docs/notes/*-pipaudit.json`.
- Test reports Playwright: `spotlove-ai/test-results/` (gitignored).
- Deploy runbook Cloudflare: `docs/notes/cloudflare-deploy-runbook.md`; placeholder `<TUNNEL_ID_PLACEHOLDER>` trong `infra/cloudflare/cloudflared/config.yml` phải được thay trước khi `scripts/deploy-local.ps1` chạy được.

## Code graph hotspots (từ gitnexus index)

Đã index bằng GitNexus (`Project_Main` — 993 files, 5614 symbols, 300 processes). Dưới đây là các load-bearing facts mà đọc file lẻ khó nhận ra — xác nhận bằng `gitnexus_context` / `gitnexus_query` trước khi sửa:

**Shared pipelines (đừng modify riêng lẻ):**

- `ai-service-fastapi/app/engine/plate_pipeline.py:PlatePipelineResult` — **một engine duy nhất** phục vụ 3 routes: `/ai/parking/scan-plate/`, `/ai/parking/check-in/`, `/ai/parking/check-out/`. Đổi return shape → phải verify cả 3 flows (processes `proc_159_check_in`, `proc_161_check_out`, `proc_185_scan_plate`).
- `ai-service-fastapi/app/engine/pipeline.py:PipelineResult` (+ `PipelineDecision`, `ClassificationMethod`) là **pipeline khác** — dùng cho banknote / license-plate detection (routes `/ai/detection/license-plate/`). Không nhầm với `plate_pipeline.py`.

**Chatbot DDD layering (đừng flatten khi thêm feature):**

```
chatbot-service-fastapi/app/
├── domain/value_objects/      # Intent, AIMetricType, ai_metrics.py      ← pure types
├── application/dto/           # IntentDecision, EntityExtraction         ← process_message output
├── application/services/      # ResponseService, AIMetricsCollector, observability_service
└── engine/orchestrator.py     # ChatbotOrchestrator — entry point
```

Intent có đúng 16 mapping values trong `domain/value_objects/intent.py` (lines 45-61). Khi thêm intent mới, update cả `Intent.mapping` + downstream `ResponseService` branches.

**God classes — Refactored in Sprint 2 (trước đó vượt 300-line limit):**

| File | Class | Trước | Sau | Ghi chú |
|---|---|---|---|---|
| `booking-service/bookings/views.py` | `BookingViewSet` | ~655 | ~60 | Refactored in S2-IMP-4: tách action methods sang `services/booking_actions.py` |
| `ai-service-fastapi/app/routers/esp32.py` | (router) | ~1623 | ~138 | Refactored in S2-IMP-5: tách sang `services/esp32_service.py` + `services/barrier_service.py` |
| `chatbot-service-fastapi/app/engine/orchestrator.py` | `ChatbotOrchestrator` | ~567 | ~300 | Refactored in S2-IMP-7: extract stage methods sang `engine/stages/` |
| `chatbot-service-fastapi/app/application/services/response_service.py` | `ResponseService` | ~517 | ~221 | Refactored in S2-IMP-7: extract sub-formatters sang `services/formatters/` |

Các file này đã được refactor về dưới hoặc gần 300-line limit. Nếu cần thêm logic mới, tiếp tục extract — không grow ngược lại. Trước khi đụng, chạy `gitnexus_context({name: "<ClassName>"})` để nắm blast radius.

**Key route files (`ai-service-fastapi`):**

- `app/routers/parking.py` — `/scan-plate/`, `/check-in/`, `/check-out/` (consumer FE + Unity + ESP32 loop)
- `app/routers/detection.py` — `/license-plate/` (standalone test/kiosk)
- `app/routers/esp32.py` — `ESP32CheckInRequest`, `BarrierAction`, `GateEvent` (IoT barrier contract)
- `app/routers/camera.py` — virtual camera streams (Unity frames)

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Project_Main** (6306 symbols, 13327 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/Project_Main/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Project_Main/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Project_Main/clusters` | All functional areas |
| `gitnexus://repo/Project_Main/processes` | All execution flows |
| `gitnexus://repo/Project_Main/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
