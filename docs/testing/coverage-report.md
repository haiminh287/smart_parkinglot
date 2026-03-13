# Coverage Report — Dependency Remediation Smoke (2026-03-13)

## Tổng quan nhanh

- Build status: **RED BUILD (partial fail)**.
- Frontend smoke (`npm run test`, `npm run build`): **PASS/PASS**.
- Backend Django smoke (`manage.py check`): **3 PASS / 1 FAIL**.
- Full backend pytest cho Django services: **chưa khả dụng trực tiếp** do test discovery chạm DRF settings khi thiếu `DJANGO_SETTINGS_MODULE`.
- Coverage: **N/A cho smoke run** (run này ưu tiên availability/smoke, không chạy full coverage).

## Critical Path Results

- FE critical path: **PASS** (`FE_TEST_EXIT=0`, `FE_BUILD_EXIT=0`).
- Backend critical path (Django boot check):
  - `auth-service`: **PASS** (`EXIT_CODE=0`)
  - `booking-service`: **FAIL** (`EXIT_CODE=1`, `ModuleNotFoundError: No module named 'celery'`)
  - `parking-service`: **PASS** (`EXIT_CODE=0`)
  - `vehicle-service`: **PASS** (`EXIT_CODE=0`)

## Artifacts

- `docs/testing/fe-smoke-result.txt`
- `docs/testing/backend-django-smoke.txt`
- `docs/testing/backend-django-manage-check.txt`

---

## Archive: Coverage & Regression Report — SECURITY-BLOCKERS-2026-03-13

## Tổng quan

- Kết quả chung: **FAIL** (có regression và env blocker).
- tests_added: **0**
- Ghi chú: chưa tìm thấy `docs/api/openapi.yaml` tại path chuẩn để đối chiếu contract trực tiếp.

## Suite Results

### 1) Frontend Unit/Integration (Vitest)

- Lệnh: `npm run test` tại `spotlove-ai`
- Kết quả: **FAIL**
- Summary: `Test Files 1 failed | 5 passed (6)`; `Tests 1 failed | 64 passed (65)`
- Failure chính:
  - `src/test/support-page.test.tsx`
  - Case: `falls back to local response on API error`
  - Expectation cũ: text `/Bảng giá dịch vụ/` không còn xuất hiện theo UI hiện tại.
- Phân loại: **Code change impact (FE)**, không phải lỗi env.

### 2) Frontend Coverage Attempt

- Lệnh: `npm run test -- --coverage`
- Kết quả: **Không có report coverage cuối cùng** vì suite vẫn fail tại cùng test regression nêu trên.

### 3) Frontend Build

- Lệnh: `npm run build`
- Kết quả: **PASS**
- Build thành công, có warning non-blocking về chunk size và dynamic/static import mix.

### 4) Backend Chatbot Tests (pytest)

- Lệnh vòng 1:
  - env: `DB_USER=test_user`, `DB_PASSWORD=test_password`, `GATEWAY_SECRET=test_gateway_secret`
  - kết quả: nhiều `403` do mismatch `X-Gateway-Secret` trong test fixtures.
- Lệnh vòng 2 (đã đồng bộ gateway secret theo fixture):
  - env: `DB_USER=test_user`, `DB_PASSWORD=test_password`, `GATEWAY_SECRET=gateway-internal-secret-key`
  - kết quả: **FAIL**
  - summary: `14 failed, 77 passed, 1 warning`
  - lỗi chính: `sqlalchemy.exc.OperationalError (1045) Access denied for user 'test_user'@'localhost'`
- Phân loại: **Env blocker (DB credentials/DB access)** sau khi đã xử lý guard secret.

### 5) Backend Payment Tests (pytest)

- Lệnh vòng 1:
  - env: `DB_USER=test_user`, `DB_PASSWORD=test_password`, `GATEWAY_SECRET=test_gateway_secret`
  - kết quả: nhiều `403` do mismatch gateway secret.
- Lệnh xác nhận với secret đã đồng bộ (`--maxfail=1`):
  - env: `DB_USER=test_user`, `DB_PASSWORD=test_password`, `GATEWAY_SECRET=gateway-internal-secret-key`
  - kết quả: **FAIL**
  - summary: `1 failed, 1 passed, 1 warning` (dừng sớm theo `--maxfail=1`)
  - lỗi chính: `sqlalchemy.exc.OperationalError (1045) Access denied for user 'test_user'@'172.20.0.1'`
- Phân loại: **Env blocker (DB credentials/DB access)** sau khi đã xử lý guard secret.

## Kết luận cho Orchestrator

- FE regression cần implementer cập nhật test expectation hoặc behavior fallback của `SupportPage`.
- BE chatbot/payment cần test DB hợp lệ (hoặc mock DB/integration fixture) để hoàn tất regression sau security guard.

---

## Re-run Final Gate (sau lint fixes) — 2026-03-13

### Scope re-run

- Frontend release gate tại `spotlove-ai` theo chuỗi: `lint` → `test` → `build` → `npm audit --audit-level=high`.

### Kết quả

- `npm run lint`: **PASS** (`0 errors, 10 warnings`, exit `0`)
- `npm test`: **PASS** (`Test Files 6 passed`, `Tests 65 passed`, exit `0`)
- `npm run build`: **PASS** (build thành công, chỉ còn warning non-blocking, exit `0`)
- `npm audit --audit-level=high`: **PASS** (chỉ còn `low/moderate`, không có `high/critical`, exit `0`)

### Kết luận re-run

- **PASS** cho final FE gate sau lint fixes.
- Đủ điều kiện chuyển bước tiếp theo trong pipeline: `security` → `qc` → `devops` (theo điều phối của Orchestrator).

---

## Re-test — celery + Starlette CVEs (2026-03-13)

## Tổng quan nhanh

- Build status: **GREEN với release env tối thiểu**.
- Frontend sanity:
  - `npm run test`: **PASS** (`65/65`)
  - `npm run build` không set env: **FAIL-FAST như thiết kế** do thiếu `VITE_GATEWAY_SECRET`
  - `npm run build` với `VITE_GATEWAY_SECRET=test-gateway-secret`: **PASS**
- Backend smoke relevant:
  - `booking-service manage.py check`: **PASS**
  - `chatbot-service-fastapi tests/test_smoke.py`: **PASS** (`18 passed`)
  - `payment-service-fastapi tests/test_smoke.py`: **PASS** (`3 passed`)
  - `notification-service-fastapi tests/test_smoke.py`: **PASS** (`4 passed`)

## Chi tiết xác nhận

### Frontend

- Artifact: `docs/testing/fe-sanity-retest-2026-03-13.txt`
- Artifact: `docs/testing/fe-build-with-env-retest-2026-03-13.txt`
- Kết luận:
  - Test suite frontend vẫn xanh sau đợt fix.
  - Build production hiện có guard bắt buộc `VITE_GATEWAY_SECRET`; đây là behavior mong đợi của fail-fast secret policy, không phải regression.
  - Khi cung cấp env tối thiểu không nhạy cảm cho test (`test-gateway-secret`), Vite build hoàn tất thành công.

### Backend

- Artifact: `docs/testing/backend-smoke-retest-2026-03-13.txt`
- `booking-service` không còn lỗi `ModuleNotFoundError: celery`; `manage.py check` trả `System check identified no issues`.
- Ba FastAPI services được ảnh hưởng bởi remediation `starlette` đều pass smoke suite hiện có.
- Warnings còn lại là deprecation/non-blocking (`Pydantic Config`, `FastAPI on_event`) và không chặn testing gate hiện tại.

## Kết luận cho Orchestrator

- **TESTING GATE: PASS** cho scope re-test sau fix `celery` + Starlette CVEs.
- Điều kiện kèm theo: FE production build phải được chạy với `VITE_GATEWAY_SECRET` theo fail-fast policy mới.
- Đủ điều kiện chuyển bước tiếp theo trong pipeline: `security_check` / gate kế tiếp theo điều phối của Orchestrator.
