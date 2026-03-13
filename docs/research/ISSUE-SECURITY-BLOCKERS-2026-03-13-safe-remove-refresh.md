# Research: Refresh SAFE_TO_REMOVE_NOW (no runtime impact)

**Task:** ISSUE-SECURITY-BLOCKERS-2026-03-13  
**Ngày:** 2026-03-13  
**Researcher:** AI Research Agent  
**Loại research:** Codebase Audit / Dead code & file rác refresh

---

## 1. Tóm tắt (TL;DR)

> Đã đối chiếu `docs/status.yaml` + handoff mới nhất: batch safe trước đó đã xóa 16 mục và build FE pass.  
> Lần refresh này chỉ còn một số artifact chắc chắn không ảnh hưởng runtime/business logic.  
> Các file forensic/debug có thể còn giá trị điều tra (nhóm backend-test/payment logs) tiếp tục bị loại khỏi SAFE theo tiêu chí bảo thủ.

---

## 2. Bối cảnh và Yêu cầu

- Trạng thái hiện tại: task đang ở pha implementing/testing, cleanup trước đã hoàn tất (`removed_targets: 16`).
- Yêu cầu lần này: chỉ trả về `SAFE_TO_REMOVE_NOW` với confidence >= 0.9 và loại toàn bộ mục còn nghi ngờ.
- Ràng buộc: không đụng runtime entrypoints, source business logic, hoặc file vận hành pipeline.

---

## 3. SAFE_TO_REMOVE_NOW (confidence >= 0.9)

| Path | Lý do | Confidence | Impact nếu xóa |
|---|---|---:|---|
| `.terminal-probe.txt` | Marker probe tạm, chỉ chứa `ok`, không được runtime/service nào đọc | 1.00 | Không ảnh hưởng runtime; chỉ mất dấu vết probe local |
| `.tmp_parse_audit.py` | Script ad-hoc parse `npm-audit.json`/`pip-audit.json`, không import trong app/runtime | 0.99 | Không ảnh hưởng runtime; chỉ mất tiện ích parse nhanh local |
| `test_output.txt` | Output text ngắn từ chạy tay (`[CHECK-IN] ...`), không phải source/config | 0.98 | Không ảnh hưởng runtime; mất log debug cục bộ |
| `test_error.txt` | Stacktrace output từ chạy test tay, không được tham chiếu bởi code runtime | 0.98 | Không ảnh hưởng runtime; mất lịch sử lỗi local |
| `git-check-output.txt` | Snapshot `git status`/`remote` ad-hoc, chỉ phục vụ forensic local | 0.96 | Không ảnh hưởng runtime; mất ảnh chụp trạng thái Git tại thời điểm cũ |
| `spotlove-ai/test-results/` (empty dir) | Thư mục artifact test hiện rỗng, không được app/runtime sử dụng | 0.95 | Không ảnh hưởng runtime; test runner sẽ tự tạo lại khi cần |

---

## 4. Loại trừ khỏi SAFE (REVIEW_REQUIRED)

Các mục sau **không** đưa vào SAFE lần này do còn giá trị forensic/documentation hoặc dễ gây hiểu nhầm tiến độ test:

- `backend-test-summary.txt`
- `backend-test-tail.txt`
- `backend-test-tail-timeout.txt`
- `backend-test-parsed.txt`
- `backend-ai-test-timeout.txt`
- `payment-rerun-log.txt`
- `test.json`

---

## 5. KEEP (implementer tránh đụng)

- `docs/status.yaml`
- `docs/research/ISSUE-SECURITY-BLOCKERS-2026-03-13-dead-code-audit.md`
- `docs/testing/test-plan.md`
- `docs/testing/coverage-report.md`
- `docs/testing/bug-report.md`
- `docs/architecture/context.md`
- `backend-microservices/docker-compose.yml`
- `backend-microservices/*/app/main.py`
- `backend-microservices/*/main.py`
- `backend-microservices/gateway-service-go/cmd/server/main.go`
- `backend-microservices/realtime-service-go/cmd/server/main.go`
- `spotlove-ai/src/**`
- `hardware/arduino/**`
- `hardware/esp32/**`

---

## 6. Checklist cho Implementer

- [ ] Xóa đúng 6 mục trong bảng SAFE_TO_REMOVE_NOW
- [ ] Không xóa bất kỳ mục nào trong nhóm REVIEW_REQUIRED/KEEP
- [ ] Nếu cần dọn thêm forensic logs, tạo ticket riêng để Orchestrator quyết định retention trước

---

## 7. Nguồn tham khảo nội bộ

| # | Path | Mục đích |
|---|---|---|
| 1 | `docs/status.yaml` | Trạng thái + cleanup metrics + handoff mới nhất |
| 2 | `docs/research/ISSUE-SECURITY-BLOCKERS-2026-03-13-dead-code-audit.md` | Baseline SAFE/REVIEW/KEEP trước đó |
| 3 | `.tmp_parse_audit.py` | Xác nhận script tạm không runtime usage |
| 4 | `.terminal-probe.txt` | Xác nhận marker file tạm |
| 5 | `test_output.txt`, `test_error.txt`, `git-check-output.txt` | Xác nhận artifact/log debug local |
| 6 | `spotlove-ai/test-results/` | Xác nhận thư mục rỗng |
| 7 | `docs/architecture/context.md` | Xác nhận một số backend logs còn được docs tham chiếu |

---

_Research được thực hiện bởi AI Research Agent — ưu tiên an toàn runtime/business logic._
