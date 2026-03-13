# Research: Deep audit dead code + file rác + project understanding (toàn workspace)

**Task:** ISSUE-SECURITY-BLOCKERS-2026-03-13  
**Ngày:** 2026-03-13  
**Researcher:** AI Research Agent  
**Loại research:** Codebase Audit / Dead Code & Cleanup Assessment

---

## 1. Tóm tắt (TL;DR)

- Workspace là monorepo hybrid: FE React/Vite (`spotlove-ai`), backend microservices Python (Django + FastAPI) + Go gateway/realtime, và hardware firmware (`hardware/*`).
- Runtime hiện tại đi qua `gateway-service-go` + Docker compose; `SupportPage` và `docs/status.yaml` vừa được cập nhật gần đây, không nằm trong vùng dead code.
- Có nhiều artifact tạm/cached có thể dọn ngay với độ tin cậy cao (đặc biệt `.tmp_*.py`, `.pytest_cache`, `test-results/.last-run.json`, log timeout).
- Có một số dead code mức symbol/file FE cần review kiến trúc trước khi xóa (ví dụ `AdminStatsPage`, `useWebSocket` export trong `websocket.service.ts`, lớp business services ít/no runtime usage trực tiếp).
- Có docs/config lệch thực tế (ví dụ `spotlove-ai/README.md` placeholder Lovable, `auth-service/README.md` và `.env.example` thiên về PostgreSQL trong khi stack hiện tại đang MySQL).

---

## 2. Bối cảnh và Yêu cầu

- Trạng thái mới nhất lấy từ `docs/status.yaml`: task đang `researching`, handoff gần nhất có chỉnh sửa `spotlove-ai/src/test/support-page.test.tsx` và `docs/status.yaml`.
- Runtime chính được xác nhận từ `backend-microservices/docker-compose.yml`, `spotlove-ai/package.json`, các `main.py`/`main.go`:
  - FE Vite (React TS)
  - Gateway Go (port 8000)
  - Realtime Go (port 8006)
  - Django services: auth/booking/parking/vehicle
  - FastAPI services: notification/payment/chatbot/ai
- Ràng buộc audit: ưu tiên facts, có usage-check cho từng mục, tách nhóm `SAFE_TO_REMOVE_NOW` / `REVIEW_REQUIRED` / `KEEP`.

---

## 3. A) Baseline kiến trúc ngắn gọn để giao task

### 3.1 Topology runtime hiện tại

1. `spotlove-ai` gửi request qua Vite proxy `/api` → `gateway-service-go`.
2. Gateway route đến các service Django/FastAPI theo prefix (`/auth`, `/bookings`, `/parking`, `/payments`, `/chatbot`, ...).
3. Realtime channel tách riêng qua `realtime-service-go` (`ws://...:8006/ws`).
4. FE route trung tâm ở `spotlove-ai/src/App.tsx`.

### 3.2 Nhóm module chính

- **Frontend**: `spotlove-ai/src/*`
- **Backend microservices**: `backend-microservices/*`
  - Django: `auth-service`, `booking-service`, `parking-service`, `vehicle-service`
  - FastAPI: `chatbot-service-fastapi`, `payment-service-fastapi`, `notification-service-fastapi`, `ai-service-fastapi`
  - Go: `gateway-service-go`, `realtime-service-go`
- **Hardware/Firmware**: `hardware/arduino/*`, `hardware/esp32/*`
- **Docs/Artifacts**: `docs/*` + nhiều file log/test tạm ở root

### 3.3 Legacy trạng thái

- Không còn thư mục `smart_parking/` trong working tree hiện tại (search không thấy path thực). Dấu vết legacy chủ yếu còn trong artifact/log cũ (ví dụ `git-check-output.txt`, docs bootstrap).

---

## 4. B) Dead code report chi tiết (bảng theo module)

## 4.1 SAFE_TO_REMOVE_NOW (confidence >= 0.85)

| Path/Symbol | Lý do nghi ngờ dead code | Confidence | Impact nếu xóa | Dependency/usage check đã làm |
|---|---|---:|---|---|
| `/.tmp_ai_timeout.py` | Script tạm chạy test AI và ghi output vào file log; không thuộc runtime | 0.99 | low | Đọc file: chỉ `subprocess pytest` + ghi `backend-ai-test-timeout.txt`; không được route/import bởi app runtime |
| `/.tmp_parse_backend.py` | Script parse text summary test cũ, chỉ phục vụ local ad-hoc | 0.99 | low | Đọc file: parse `backend-test-summary.txt`; không có tham chiếu runtime |
| `/.tmp_parse_pip_audit.py` | Script parse `pip-audit.json` local | 0.99 | low | Đọc file: chỉ đọc JSON và `print`; không import bởi module khác |
| `/.tmp_payment_rerun.py` | Script rerun riêng payment tests với env cứng | 0.99 | low | Đọc file: chạy pytest và ghi `payment-rerun-log.txt`; không có call từ pipeline chính |
| `/.tmp_timeout_tail.py` | Script trích tail test timeout cho vài service | 0.99 | low | Đọc file: chạy pytest local, ghi `backend-test-tail-timeout.txt` |
| `/ai-timeout-run.log` | Log runtime/test tạm thời | 0.95 | low | Tên + nội dung log timeout; không được load bởi code |
| `/timeout-tail-run.log` | Log runtime/test tạm thời | 0.95 | low | Tương tự trên |
| `spotlove-ai/test-results/.last-run.json` | Artifact Playwright lần chạy gần nhất | 0.98 | low | Chuẩn artifact test runner, không phải source |
| `backend-microservices/*/.pytest_cache/` (8 services) | Cache pytest tự sinh | 0.98 | low | Search thấy chỉ README cache; không phải source |

## 4.2 REVIEW_REQUIRED (0.5 - 0.84)

| Path/Symbol | Lý do nghi ngờ dead code | Confidence | Impact nếu xóa | Dependency/usage check đã làm |
|---|---|---:|---|---|
| `spotlove-ai/src/pages/admin/AdminStatsPage.tsx` | Có file lớn nhưng không thấy import route trong `App.tsx`, không có nav item `/admin/stats` | 0.92 | med | Đối chiếu `App.tsx` admin routes + `AppSidebar.tsx`; không thấy path tương ứng |
| `spotlove-ai/src/services/websocket.service.ts::useWebSocket` (exported hook) | Hook wrapper cũ, FE dùng `useWebSocketConnection` thay thế | 0.88 | low | Search usage không thấy import thực tế `useWebSocket`; chỉ thấy export declaration |
| `spotlove-ai/src/services/business/*.service.ts` (nhất là `booking.service.ts`) | Có lớp business abstraction nhưng runtime page/hook hiện chủ yếu gọi API/hook khác | 0.72 | med | Scan `BookingPage`, `PaymentPage`, `PanicButtonPage`, hooks; thấy call `bookingApi`/slice/hook nhiều hơn service |
| `spotlove-ai/src/services/api/endpoints.ts` | Nhiều endpoint hard-coded ở từng api file; constants có dấu hiệu ít dùng | 0.68 | low | Search chỉ thấy export; chưa thấy import rộng rãi trong các api modules chính |
| `/backend-test-summary.txt`, `/backend-test-tail.txt`, `/backend-test-tail-timeout.txt`, `/backend-test-parsed.txt`, `/backend-ai-test-timeout.txt`, `/payment-rerun-log.txt`, `/backend-ai-test-timeout.txt` | Artifact điều tra test có thể còn giá trị forensic ngắn hạn | 0.75 | med | Nội dung là summary/timeout; docs bootstrap vẫn tham chiếu chúng |
| `spotlove-ai/e2e/.auth/admin.json`, `spotlove-ai/e2e/.auth/user.json` | Auth state test, có thể regenerate; có rủi ro chứa state nhạy cảm | 0.74 | med | Nằm trong `e2e/.auth`, thường là generated storage state |
| `backend-microservices/ai-service-fastapi/.env.local` | File local env riêng, có thể không cần trong repo sạch | 0.70 | med | Search chỉ thấy file standalone; không có chuẩn docs commit file này |

## 4.3 KEEP (cần giữ)

| Path/Symbol | Lý do giữ | Confidence giữ | Impact nếu xóa | Dependency/usage check đã làm |
|---|---|---:|---|---|
| `spotlove-ai/src/pages/SupportPage.tsx` + `spotlove-ai/src/test/support-page.test.tsx` | Mới chỉnh sửa gần đây theo handoff; đang là focus regression | 0.99 | high | Xác nhận trong `docs/status.yaml` handoff artifacts mới nhất |
| `backend-microservices/*/app/main.py`, `*/cmd/server/main.go` | Entrypoint runtime services | 0.99 | high | Đọc trực tiếp các file main + compose services |
| `backend-microservices/docker-compose.yml` | Runtime orchestration trung tâm | 0.99 | high | Service map + dependencies lấy từ file này |
| `hardware/arduino/barrier_control/barrier_control.ino` | Firmware phần cứng thực tế | 0.97 | high | Là source `.ino`, không phải artifact |
| `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino` | Firmware phần cứng thực tế | 0.97 | high | Là source `.ino`, không phải artifact |
| `docs/status.yaml` | SSOT trạng thái pipeline hiện tại | 0.99 | high | Được workflow agent sử dụng trực tiếp |

---

## 5. File rác / duplicate configs / docs lệch / TODO-FIXME blockers

### 5.1 tmp/log/artifact test cũ

- Root scripts tạm: `.tmp_*.py`
- Root logs: `ai-timeout-run.log`, `timeout-tail-run.log`, `backend-test-*.txt`, `payment-rerun-log.txt`
- Cache test: `backend-microservices/*/.pytest_cache/`, `spotlove-ai/test-results/.last-run.json`

### 5.2 Duplicate/misaligned config

- `backend-microservices/.env.example` (MySQL-centric) **vs** `backend-microservices/auth-service/.env.example` (PostgreSQL URL style) → lệch chuẩn môi trường hiện tại.
- `spotlove-ai/.env` chứa block “Supabase legacy - not currently used”.

### 5.3 Docs cũ/lệch thực tế

- `spotlove-ai/README.md`: template Lovable placeholder (`REPLACE_WITH_PROJECT_ID`), không phản ánh kiến trúc thật.
- `backend-microservices/auth-service/README.md`: mô tả setup/env lệch so với runtime compose/MySQL hiện dùng.
- `docs/04_FRONTEND_BACKEND_API_OVERVIEW.md`: chứa mismatch report cũ (nhiều mục đã thay đổi theo runtime hiện tại), cần re-validate trước khi dùng làm tài liệu chuẩn.

### 5.4 TODO/FIXME/Blocker comments

- Phát hiện TODO bảo mật trong production FE: `spotlove-ai/src/services/websocket.service.ts` có `TODO(security)` về signed short-lived token cho WebSocket auth.
- Có nhiều commented-out blocks lớn trong `docker-compose.yml` (service AI đang comment) và `spotlove-ai/src/services/api/endpoints.ts` (MAP/SUPPORT/CALENDAR blocks chưa implement) → không phải bug ngay, nhưng gây nhiễu khi đọc kiến trúc.

---

## 6. C) Cleanup execution plan theo wave (quick wins trước)

### P0 — Quick wins (0.5 ngày)

1. Xóa artifacts chắc chắn an toàn:
   - `.tmp_*.py`
   - `spotlove-ai/test-results/.last-run.json`
   - toàn bộ `backend-microservices/*/.pytest_cache/`
   - logs timeout tạm (`ai-timeout-run.log`, `timeout-tail-run.log`)
2. Cập nhật `.gitignore` để chặn tái phát:
   - `.pytest_cache/`, `test-results/`, `*.log`, `.tmp_*.py`
3. Chuẩn hóa lưu trữ forensic: nếu cần giữ evidence, di chuyển sang `docs/testing/artifacts/` và đặt naming chuẩn date-based.

**Effort:** ~3-4 giờ

### P1 — Medium cleanup (1-2 ngày)

1. Quyết định fate của `AdminStatsPage.tsx`:
   - hoặc add route/nav chính thức,
   - hoặc xóa nếu không dùng product-wise.
2. Quyết định fate của `useWebSocket` export và `services/business/*` abstraction (giữ làm API public hay gỡ bớt).
3. Reconcile config docs:
   - hợp nhất `auth-service/.env.example` với root env strategy hiện tại.

**Effort:** ~1.0-1.5 ngày

### P2 — Hygiene/documentation hardening (1-2 ngày)

1. Rewrite docs lệch (`spotlove-ai/README.md`, service README cũ).
2. Tách rõ “runtime docs” vs “forensics snapshot docs”.
3. Resolve TODO bảo mật WebSocket auth (thiết kế + contract backend).

**Effort:** ~1.5 ngày

---

## 7. D) Danh sách file đề xuất xóa ngay trong lượt này

> Chỉ liệt kê đề xuất; chưa thực hiện xóa trong phiên research này.

1. `.tmp_ai_timeout.py`
2. `.tmp_parse_backend.py`
3. `.tmp_parse_pip_audit.py`
4. `.tmp_payment_rerun.py`
5. `.tmp_timeout_tail.py`
6. `ai-timeout-run.log`
7. `timeout-tail-run.log`
8. `spotlove-ai/test-results/.last-run.json`
9. `backend-microservices/ai-service-fastapi/.pytest_cache/` (folder)
10. `backend-microservices/auth-service/.pytest_cache/` (folder)
11. `backend-microservices/booking-service/.pytest_cache/` (folder)
12. `backend-microservices/chatbot-service-fastapi/.pytest_cache/` (folder)
13. `backend-microservices/notification-service-fastapi/.pytest_cache/` (folder)
14. `backend-microservices/parking-service/.pytest_cache/` (folder)
15. `backend-microservices/payment-service-fastapi/.pytest_cache/` (folder)
16. `backend-microservices/vehicle-service/.pytest_cache/` (folder)

---

## 8. Blockers/Gotchas khi audit

- **Tool output cap:** một số lệnh read/search trả về quá lớn nên phải chia batch nhỏ để tránh truncation (đã xử lý bằng đọc theo lô và head/tail).
- **No single static analyzer run:** phiên này không chạy tooling chuyên sâu (`ts-prune`, `depcheck`, `vulture`) do phạm vi researcher mode; classification dựa trên static usage-check từ code search + route/runtime mapping.
- **Forensic ambiguity:** một số file test summary có thể vẫn cần cho điều tra ngắn hạn, nên xếp `REVIEW_REQUIRED` thay vì `SAFE`.

---

## 9. Checklist cho Implementer

- [ ] Xóa batch P0 safe artifacts (list ở Section 7)
- [ ] Thêm rules `.gitignore` chống tái sinh artifact
- [ ] Chốt `AdminStatsPage.tsx` (add route hoặc remove)
- [ ] Chốt `useWebSocket` hook export (remove/keep)
- [ ] Chốt chiến lược `services/business/*` (đang ít usage trực tiếp)
- [ ] Đồng bộ lại README + `.env.example` theo MySQL + compose runtime hiện tại
- [ ] Tạo ticket xử lý TODO WebSocket security token

---

## 10. Nguồn tham khảo nội bộ (đã kiểm tra)

| # | Path | Mục đích |
|---|---|---|
| 1 | `docs/status.yaml` | Trạng thái mới nhất + handoff SupportPage |
| 2 | `backend-microservices/docker-compose.yml` | Runtime topology hiện tại |
| 3 | `spotlove-ai/src/App.tsx` | FE route usage |
| 4 | `spotlove-ai/src/components/layout/AppSidebar.tsx` | Nav usage admin/user |
| 5 | `spotlove-ai/src/services/websocket.service.ts` | Dead symbol + TODO security |
| 6 | `spotlove-ai/src/pages/admin/AdminStatsPage.tsx` | Candidate dead page |
| 7 | `backend-microservices/*/app/main.py`, `*/cmd/server/main.go` | Entrypoints |
| 8 | Root `.tmp_*.py` + `backend-test-*.txt` + `*.log` | Artifact/tmp evidence |
| 9 | `spotlove-ai/README.md`, `backend-microservices/auth-service/README.md` | Docs lệch thực tế |

---

_Research được thực hiện bởi AI Research Agent — cần Architect/Implementer review trước khi áp dụng xóa hàng loạt._
