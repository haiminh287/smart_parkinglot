# 📋 Tiêu chuẩn Lập trình Cấp Doanh nghiệp (Enterprise Coding Standards)

> Tệp này là **nguồn quy tắc duy nhất (Single Source of Truth)** cho mọi tác nhân AI hoạt động trong dự án.
> Mọi agent PHẢI tuân thủ toàn bộ nội dung dưới đây trước khi thực hiện bất kỳ tác vụ nào.

---

## 1. Bảo mật (Security First)

- **Tuyệt đối KHÔNG** hardcode mật khẩu, secret key, API key, token, hoặc bất kỳ thông tin nhạy cảm nào.
- Luôn sử dụng **biến môi trường** qua `.env` (không commit) và `.env.example` (commit mẫu).
- Mọi kết nối tới dịch vụ bên ngoài phải qua **TLS/SSL**.
- Dữ liệu nhạy cảm (PII) phải được **mã hóa at rest và in transit**.
- Input người dùng luôn phải được **validate và sanitize** trước khi xử lý.
- Dùng **parameterized queries hoặc ORM** để phòng SQL Injection.
- Áp dụng **OWASP Top 10** làm checklist bảo mật bắt buộc.

---

## 2. Kiến trúc Mã nguồn (Code Architecture)

- Áp dụng nguyên tắc **SOLID** và **Clean Code** trong mọi module.
- **Kiến trúc được chọn theo yêu cầu dự án** — không có kiến trúc mặc định.
  Architect quyết định pattern phù hợp (Layered / Hexagonal / CQRS / Event-Driven / ...) và ghi vào ADR.
  Mọi agent follow đúng ADR của project đó.
- Mỗi module chỉ chịu trách nhiệm **một chức năng duy nhất** (Single Responsibility).
- Sử dụng **Dependency Injection** thay vì khởi tạo trực tiếp.
- Tách biệt rõ ràng **business logic** và **infrastructure code**.
- Tên biến, hàm, class bằng **tiếng Anh**, rõ ràng, có ý nghĩa.
- Mỗi hàm không vượt quá **50 dòng** (ngoại lệ phải có chú thích).
- Mỗi file không vượt quá **300 dòng** — vượt thì tách module.

---

## 3. Quản lý Lỗi (Error Handling)

- Mọi tác vụ async/IO **phải** có error handling (try/catch, if err != nil, Result type, ...).
- Sử dụng **Custom Error Classes** thay vì throw error chung:
  ```
  AppError → ValidationError, AuthError, NotFoundError, ConflictError, InfraError
  ```
- **Structured logging** (JSON format) với: `timestamp`, `level`, `message`, `context`, `stackTrace`.
- Phân biệt **operational errors** (dự đoán được) và **programmer errors** (bugs).
- Mọi API endpoint trả về format lỗi thống nhất:
  ```json
  {
    "success": false,
    "error": {
      "code": "ERR_VALIDATION",
      "message": "Mô tả lỗi",
      "details": []
    }
  }
  ```

---

## 4. Ngôn ngữ và Quy ước Đặt tên

- **Tài liệu, comment, PRD, ADR**: viết bằng **tiếng Việt**.
- **Tên biến, hàm, class, commit message, log**: viết bằng **tiếng Anh**.
- **Naming Conventions — theo convention của ngôn ngữ đang dùng:**

  ```
  Python:
    snake_case      → biến, hàm: get_user_by_email(), total_amount
    PascalCase      → class: UserService, IAuthProvider
    SCREAMING_SNAKE → hằng số: MAX_RETRY_COUNT
    snake_case      → file và thư mục: user_service.py, api_routes/

  TypeScript/JavaScript:
    camelCase       → biến, hàm: getUserByEmail(), totalAmount
    PascalCase      → class, interface: UserService, IAuthProvider
    SCREAMING_SNAKE → hằng số: MAX_RETRY_COUNT
    kebab-case      → file và thư mục: user-service.ts, api-routes/

  Go:
    camelCase       → biến, hàm unexported: getUserByEmail()
    PascalCase      → exported: GetUserByEmail(), UserService
    SCREAMING_SNAKE → hằng số: MaxRetryCount (hoặc iota)

  Java:
    camelCase       → biến, phương thức: getUserByEmail()
    PascalCase      → class: UserService
    SCREAMING_SNAKE → hằng số: MAX_RETRY_COUNT
    kebab-case/lowercase → package: com.example.userservice
  ```

  **Nguyên tắc**: Nếu project đã có conventions → **follow conventions đó**, không tự đặt ra mới.
  - Prefix `I` cho interface (TypeScript/Java): `IUserRepository`
  - Prefix `is/has/can` cho boolean: `isActive`, `hasPermission`, `is_active`

---

## 5. Kiểm thử (Testing Standards)

- Code Coverage tối thiểu: **80%** unit test, **60%** integration test.
- Mỗi module có test file tương ứng (theo convention của test framework đang dùng).
- Mock tất cả external dependencies trong unit test.
- Viết test cho cả **happy path** và **edge cases**.
- Test database riêng biệt — không dùng dev DB.

---

## 6. Git & Version Control

- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`, `perf:`, `style:`.
- Mỗi commit chỉ chứa **một thay đổi logic duy nhất**.
- **KHÔNG** `git add .` — add specific files.
- Branch naming: `feature/`, `bugfix/`, `hotfix/`, `release/`, `chore/`.
- Mọi thay đổi qua **Pull Request** với ít nhất **1 reviewer**.

---

## 7. Documentation

- Mỗi hàm/method public có **docstring / JSDoc** với params, returns, throws.
- Mỗi module có **README.md** hoặc inline docs mô tả mục đích, cách dùng.
- API endpoints documented bằng **format phù hợp stack** (OpenAPI / GraphQL schema / proto / event catalog).
- Architectural decisions ghi nhận trong **ADR** tại `docs/architecture/`.

---

## 8. Performance & Optimization

- **Caching** (Redis / in-memory) cho dữ liệu truy vấn nhiều.
- **Pagination** cho tất cả API trả về danh sách.
- Tối ưu **database queries**: tránh N+1, dùng index đúng.
- Lazy loading cho module không cần thiết lúc khởi động.
- Giám sát **memory leaks** và **connection pools**.

---

## 9. Agent Delegation (Quy tắc Ủy quyền)

- **Orchestrator** là Team Lead — chỉ có tool `agent`. KHÔNG có `editFiles`, `runInTerminal`.
- Orchestrator **BẮT BUỘC** dùng tool `agent` cho mọi task chuyên môn:
  - Viết code → `implementer`
  - Viết test → `tester`
  - Review code → `reviewer`
  - Deploy / Infra → `devops`
  - Security audit → `security`
  - QC Gate (coverage, perf, regression, checklist) → `qc`
  - Thiết kế hệ thống → `architect`
  - Research / Khảo sát codebase, best practices → `researcher`
- Mỗi sub-agent **chỉ làm trong phạm vi quyền** của mình.
- **Sub-agent KHÔNG GỌI sub-agent khác** — báo về Orchestrator, để Orchestrator điều phối.

---

## 10. Active Agent Reporting

```
Khi bắt đầu:   🤖 [AGENT_NAME] đang thực thi: [mô tả task]
Khi hoàn tất:  ✅ [AGENT_NAME] hoàn tất: [kết quả tóm tắt]
```

Orchestrator ghi nhận trong báo cáo cuối:
```
📊 Agents đã dùng: researcher → architect → implementer → reviewer → tester → security → qc → devops
```