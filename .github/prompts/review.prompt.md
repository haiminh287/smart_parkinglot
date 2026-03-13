---
description: "Review nhanh file hiện tại theo tiêu chuẩn Enterprise."
---

# Quick Review Prompt

**Bối cảnh**: Tôi cần đánh giá file `{{vscode:activeFile}}` trước khi commit.
**Yêu cầu**:
1. Đánh giá file dựa trên các tiêu chí SOLID, DRY, Clean Code.
2. Tìm kiếm security flaws (OWASP, injection, unhandled logic, lack of exception handling).
3. Tìm kiếm performance issues (N+1, lack of pagination, unused variables).
4. Chấm điểm trên thang 10.
5. Tạo một danh sách các "TODO" ngắn gọn những điểm cần sửa.

Vui lòng đóng vai trò chuyên gia Review để thực hiện.
