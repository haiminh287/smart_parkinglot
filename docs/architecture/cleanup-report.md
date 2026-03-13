# Cleanup Report — Bootstrap

**Ngày:** 2026-03-13  
**Phạm vi:** dọn dẹp artifacts tạm và chuẩn hóa baseline tài liệu bootstrap

## 1) Hiện trạng phát hiện

- Có nhiều file tạm ở root dùng cho chạy test/thống kê nhanh:
  - `.tmp_parse_backend.py`
  - `.tmp_timeout_tail.py`
  - `.tmp_ai_timeout.py`
  - `timeout-tail-run.log`
  - `ai-timeout-run.log`
  - `backend-test-tail.txt`
  - `backend-test-tail-timeout.txt`
  - `backend-ai-test-timeout.txt`
  - `backend-test-summary.txt`
  - `backend-test-parsed.txt`

## 2) Đánh giá

- Các file trên là artifacts hữu ích cho điều tra pipeline hiện tại, chưa nên xóa ngay khi vẫn cần truy vết lỗi.
- Chưa thực hiện xóa tự động để tránh mất bằng chứng debug cho các bước QC/Security/DevOps tiếp theo.

## 3) Kế hoạch cleanup đề xuất

1. Sau khi Orchestrator xác nhận không cần forensic logs:
   - Di chuyển artifacts vào `docs/notes/` hoặc `docs/testing/` theo mục đích lưu trữ.
2. Chuẩn hóa script tạm:
   - Gộp các script `.tmp_*.py` thành 1 script có tên rõ nghĩa trong `scripts/diagnostics/`.
3. Thiết lập `.gitignore` mục tiêu:
   - Bổ sung pattern cho file tạm runtime/log nếu không cần theo dõi trong Git history.

## 4) Trạng thái

- Cleanup thực tế: **PENDING (chờ quyết định Orchestrator)**
- Tài liệu bootstrap: **DONE**
