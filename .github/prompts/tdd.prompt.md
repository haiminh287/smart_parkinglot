---
description: "Chạy quy trình Test-Driven Development (TDD) nhanh cho file hiện tại."
---

# TDD Prompt

**Bối cảnh**: Tôi muốn áp dụng phương pháp Test-Driven Development.
**Mục tiêu**: 
1. Phân tích `{{vscode:activeFile}}` (hoặc cấu trúc code tôi gửi).
2. Tự động viết test case TDD (Unit test hoặc Integration test).
3. Cover các User Flows, edge cases quan trọng (null data, invalid string, authentication error...).
4. Sau khi gửi test code, nếu cần thì tiếp tục đề xuất sửa code chính (Implement) để pass các test này.

Hãy tự động gọi đúng Agent `tester` để xử lý nếu bạn là Orchestrator, hoặc trực tiếp viết test nếu bạn là Tester.
