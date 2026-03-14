# 📋 Enterprise Coding Standards v10

> **Single Source of Truth** cho mọi agent.
> **Priority**: `docs/architecture/context.md` của project thắng khi conflict với file này.

---

## 1. Security (Non-Negotiable)

- KHÔNG hardcode secrets, keys, tokens — dùng env vars
- `.env` gitignored | `.env.example` committed (không có real values)
- Mọi external connection: TLS/SSL
- User input: validate + sanitize trước khi process
- SQL queries: parameterized/ORM — không string interpolation
- Passwords: bcrypt/argon2/scrypt (không MD5/SHA1)
- Randoms: cryptographically secure (crypto.randomBytes, secrets module)
- Logs: không chứa passwords, tokens, card numbers, PII
- OWASP Top 10 = security checklist bắt buộc

---

## 2. Architecture

Architect quyết định pattern (Layered/Hexagonal/CQRS/Event-Driven) và ghi ADR.
**Mọi agent follow ADR của project — không tự đặt pattern mới.**

Principles bất biến:

- **Single Responsibility**: mỗi class/module 1 lý do thay đổi
- **Dependency Injection**: không hardcode dependencies
- **Interface-based**: depend on abstractions
- **Fail Fast**: validate sớm, throw descriptive errors
- **Idempotency**: mutations nên idempotent khi có thể
- **Observability**: metrics/logs/traces từ day 1, không phải afterthought

---

## 3. Error Handling

```
AppError (base, with code + statusCode)
├── ValidationError    (400)
├── UnauthorizedError  (401)
├── ForbiddenError     (403)
├── NotFoundError      (404)
├── ConflictError      (409)
└── InternalError      (500)
```

API error format (bất biến):

```json
{
  "success": false,
  "error": { "code": "ERR_VALIDATION", "message": "...", "details": [] }
}
```

Logs (structured JSON): `timestamp`, `level`, `message`, `context` — no sensitive data.

---

## 4. Naming Conventions

Docs/comments/ADR → **tiếng Việt**
Code/variables/commits/logs → **tiếng Anh**

| Language      | variables/funcs      | classes    | constants       | files      |
| ------------- | -------------------- | ---------- | --------------- | ---------- |
| TypeScript/JS | camelCase            | PascalCase | SCREAMING_SNAKE | kebab-case |
| Python        | snake_case           | PascalCase | SCREAMING_SNAKE | snake_case |
| Go            | camelCase/PascalCase | PascalCase | MixedCaps       | snake_case |
| Java          | camelCase            | PascalCase | SCREAMING_SNAKE | lowercase  |

Universal: boolean → `is/has/can` prefix. Interface → `I` prefix (TS/Java).
**Nếu project đã có conventions → FOLLOW chúng.**

---

## 5. Code Quality

| Metric          | Limit                               |
| --------------- | ----------------------------------- |
| Function length | ≤ 50 lines                          |
| File length     | ≤ 300 lines                         |
| Nesting depth   | ≤ 4 levels                          |
| Function params | ≤ 4 (dùng object/DTO cho nhiều hơn) |

---

## 6. Dead Code Policy

**Sau mỗi task hoàn thành, codebase phải sạch:**

- Không có approach-drift files (thử A, dùng B, files của A phải xóa)
- Không có unused imports, variables, functions
- Không có commented-out code blocks > 10 dòng
- Không có `.old`, `.bak`, `_backup` files trong src/
- Không có `console.log`/`print` debug

**Workflow**: Reviewer flag → Orchestrator tạo cleanup state → Implementer xóa → DevOps commit riêng.

---

## 7. Testing

| Type        | Standard | Sensitive |
| ----------- | -------- | --------- |
| Unit        | ≥ 80%    | ≥ 90%     |
| Integration | ≥ 60%    | ≥ 75%     |
| Branch      | ≥ 70%    | ≥ 85%     |

- Test naming: `should {behavior} when {condition}`
- Pattern: AAA (Arrange-Act-Assert)
- Mock: only external dependencies
- Test DB: isolated, never dev/prod
- No flaky tests

---

## 8. Git Workflow

Branches: `feature/ISSUE-{ID}-{desc}` | `bugfix/` | `hotfix/` | `chore/` | `refactor/`

Commits: `{type}({scope}): {description}  Refs: #{ID}`
Types: `feat fix refactor test docs chore ci perf style build`

Rules: **KHÔNG** `git add .` | KHÔNG force push protected | KHÔNG `git reset --hard` shared | commit per logical unit

---

## 9. Performance

- Pagination bắt buộc cho list APIs
- Avoid N+1 queries (use eager loading / batch)
- Indexes cho frequent query patterns
- Timeout cho mọi external calls
- Connection pooling cho DB/external services

---

## 10. Documentation

- Public functions: docstring/JSDoc (params, returns, throws)
- Architecture decisions: ADR tại `docs/architecture/`
- API: OpenAPI 3.0 / GraphQL schema / proto
- Env vars: documented trong `.env.example` với comments

---

## 11. Agent Delegation

```
Orchestrator: CHỈ có tool `agent` — KHÔNG editFiles/runInTerminal
  write code      → implementer
  write tests     → tester
  review code     → reviewer
  deploy/git      → devops
  migrations      → devops
  security audit  → security
  QC gate         → qc
  system design   → architect
  research        → researcher

Sub-agents: KHÔNG gọi nhau — báo Orchestrator, để Orchestrator điều phối
```

---

## 12. Reporting

```
Start:   🤖 [{AGENT}] đang thực thi: {task}
Done:    ✅ [{AGENT}] hoàn tất: {result + metrics}
Fail:    ❌ [{AGENT}] FAIL: {reason + action needed}
```

Final summary:

```
📊 Agents: researcher→architect→implementer→reviewer→[cleanup→]devops→tester→security→qc→devops
```
