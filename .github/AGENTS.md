# 🤖 Quy tắc Phối hợp Hệ thống Đa Tác nhân (Multi-Agent Coordination Protocol)

> Tệp này thiết lập **giao thức phối hợp** cho toàn bộ đội ngũ tác nhân AI.
> Mọi agent PHẢI đọc và tuân thủ tệp này TRƯỚC KHI bắt đầu bất kỳ nhiệm vụ nào.

---

## 1. Kiến trúc Đội ngũ (Team Architecture)

```
┌──────────────────────────────────────────────────────────────┐
│                      👤 NGƯỜI DÙNG                           │
│                 (Khởi tạo ý tưởng/yêu cầu)                  │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                🎯 ORCHESTRATOR (Team Lead)                    │
│          Tiếp nhận → Phân tích → Phân công                   │
│          Giám sát tiến độ → Tổng hợp kết quả                 │
└────┬────┬──────────┬──────────┬──────────┬──────────┬────────────┘
     │    │          │          │          │          │
     ▼    ▼          ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌──────┐
│🔬 RESE││🏗️ ARCH ││💻 IMPL ││🔍 REVI ││🧪 TEST ││🛡️ SEC  ││🚀 DO │
│ARCHER │→│ITECT   │→│EMENTER │→│EWER    │→│ER      │→│URITY   │→│EVOPS │
│        │ │        │ │        │ │        │ │        │ │        │ │      │
│Nghiên  │ │Thiết kế│ │Lập     │ │Review  │ │Kiểm   │ │Security│ │Deploy│
│cứu     │ │hệ thống│ │trình   │ │Code    │ │thử    │ │Audit   │ │CI/CD │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────┬───┘ └──────┘
                                                   │
                                                   ▼
                                            ┌────────────┐
                                            │ 🎯 QC GATE │
                                            │            │
                                            │ Coverage   │
                                            │ Perf Check │
                                            │ Regression │
                                            └────────────┘
```

**Lưu ý quan trọng về luồng:**
- Mọi agent báo cáo **về Orchestrator**, không gọi trực tiếp agent khác
- Orchestrator là người duy nhất điều phối luồng tiếp theo
- Các mũi tên trên thể hiện luồng **dữ liệu** (artifacts), không phải handoff trực tiếp

---

## 2. Chia sẻ Trạng thái (Shared State Protocol)

### 2.1 Tệp trạng thái: `docs/status.yaml`

```yaml
project:
  name: "Tên dự án"
  phase: "analysis | planning | researching | designing | implementing | reviewing | testing | security_check | deploying | monitoring | done"
  started_at: "ISO-8601"
  updated_at: "ISO-8601"

task:
  id: "ISSUE-001"
  title: "Mô tả task"
  pipeline: "FAST | STANDARD | FULL | HOTFIX"
  state: "analysis | planning | researching | designing | implementing | reviewing | testing | security_check | deploying | monitoring | rollback | done | blocked"
  prev_state: ""
  started_at: "ISO-8601"
  updated_at: "ISO-8601"
  stack:
    language: ""
    package_manager: ""
    db_migration_tool: ""
    test_runner: ""
    dep_audit_tool: ""
    container_name: ""
    health_check_url: ""
  retries:
    researcher: 0
    architect: 0
    implementer: 0
    tester: 0
    reviewer: 0
    security: 0
    devops: 0
  blocked_reason: null
  cost_guard:
    steps_used: 0
    agent_calls_used: 0

agents:
  orchestrator: { status: "idle | working | waiting | done", current_task: "" }
  researcher:   { status: "idle | working | waiting | done", current_task: "" }
  architect:    { status: "idle | working | waiting | done", current_task: "" }
  implementer:  { status: "idle | working | waiting | done", current_task: "" }
  tester:       { status: "idle | working | waiting | done", current_task: "" }
  reviewer:     { status: "idle | working | waiting | done", current_task: "" }
  security:     { status: "idle | working | waiting | done", current_task: "" }
  qc:           { status: "idle | working | waiting | done", current_task: "" }
  devops:       { status: "idle | working | waiting | done", current_task: "" }

handoff_log:
  - from: "agent_name"
    to: "agent_name"
    timestamp: "ISO-8601"
    reason: "Lý do"
    artifacts: ["đường/dẫn/file"]
```

### 2.2 Quy trình cập nhật
1. **TRƯỚC KHI** bắt đầu: Đọc `docs/status.yaml`
2. Cập nhật `status` → `"working"`
3. **SAU KHI** hoàn thành: Cập nhật `status`, và ghi vào `handoff_log`
4. Nếu blocked: `status → "waiting"`, ghi `blocked_reason`

---

## 3. Nguyên tắc Chuyển giao (Handoff Protocol)

### 3.1 Luật vàng
- **TUYỆT ĐỐI KHÔNG** làm thay công việc của agent khác
- Mỗi agent chỉ hoạt động trong **phạm vi quyền hạn** đã định nghĩa
- **Sub-agent KHÔNG GỌI sub-agent khác** — báo về Orchestrator, để Orchestrator điều phối
- Chuyển giao phải kèm **đầy đủ artifacts** và **log chi tiết**

### 3.2 Luồng chuyển giao chuẩn

```
Orchestrator → Researcher   : Yêu cầu + context → Research report
Researcher   → Orchestrator : Research report hoàn tất / không cần research / BLOCKER

Orchestrator → Architect    : PRD + yêu cầu + research report → System design
Architect    → Orchestrator : ADR + contracts hoàn tất

Orchestrator → Implementer  : Design docs → Code
Implementer  → Orchestrator : Code hoàn tất / cần tham vấn

Orchestrator → Reviewer     : Code sẵn sàng → Review
Reviewer     → Orchestrator : Score + findings
                              [Nếu < 7: Orchestrator → Implementer → Orchestrator → Reviewer]

Orchestrator → Tester       : Code đã pass review → Test
Tester       → Orchestrator : PASS hoặc bug report
                              [Nếu FAIL: Orchestrator → Implementer → Orchestrator → Tester]

Orchestrator → Security     : Code pass test → Security audit
Security     → Orchestrator : PASS hoặc vulnerability report
                              [Nếu FAIL: Orchestrator → Implementer → Orchestrator → Security]

Orchestrator → QC          : Code pass security → QC Gate
QC           → Orchestrator : PASS hoặc gate failures (coverage / perf / regression)
                              [Nếu FAIL: Orchestrator → Implementer → Orchestrator → QC]
                              [Skip cho FAST/HOTFIX với skip_reason ghi vào status.yaml]

Orchestrator → DevOps       : Tất cả pass → Deploy
DevOps       → Orchestrator : Deploy report
```

### 3.3 Quy tắc khi phát hiện lỗi
- **Tester** phát hiện bug → báo về **Orchestrator** kèm bug report
- **Orchestrator** → giao **Implementer** fix → giao lại **Tester** re-test
- **KHÔNG** tester tự gọi implementer rồi tự nhận kết quả

---

## 4. Cấu trúc Thư mục Chuẩn

```
project-root/
├── docs/
│   ├── status.yaml                # Shared State
│   ├── prd/                       # Product Requirements
│   ├── architecture/              # ADR, system design, context
│   │   ├── context.md             # Stack đã detect
│   │   ├── system-design.md
│   │   └── adr-*.md
│   ├── api/                       # API contracts (openapi / graphql / proto / events)
│   ├── research/                  # Research reports (từ Researcher agent)
│   ├── testing/                   # Test plans, coverage reports
│   └── notes/                     # Session logs (memory MCP fallback)
├── src/                           # Source code (structure theo stack)
├── tests/                         # Tests
├── infra/                         # Infrastructure (Dockerfile, CI/CD)
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. Quy tắc Giao tiếp

- Agent giao tiếp qua **artifacts** (files, documents), KHÔNG qua lời nói suông
- Mọi quyết định kiến trúc → ghi vào **ADR**
- Khi không chắc → báo **Orchestrator**, không tự đoán
- Báo cáo rõ ràng: **Đã làm gì**, **Đang làm gì**, **Cần làm gì tiếp**
- Mỗi agent khi bắt đầu ghi: `🤖 [AGENT] đang thực thi: [task]`
- Mỗi agent khi hoàn thành ghi: `✅ [AGENT] hoàn tất: [kết quả]`

---

## 6. Xử lý Xung đột

- Hai agent cùng muốn sửa một file → **Orchestrator** quyết định thứ tự
- Yêu cầu mâu thuẫn với thiết kế → **Architect** phán quyết về kiến trúc
- Pipeline blocked → **Orchestrator** báo user, chờ confirm

---

## 7. MCP Server Mapping

> Bảng này liệt kê chính xác MCP server nào agent nào sử dụng.
> Tất cả servers được config tại `.vscode/mcp.json`.

| MCP Server | Chức năng | Agents sử dụng |
|-----------|-----------|----------------|
| `github/*` | Issues, PRs, search repos, review code | orchestrator, devops |
| `filesystem/*` | Đọc/ghi file, duyệt thư mục, search | orchestrator, researcher, architect, implementer, reviewer, tester, security, devops, qc |
| `postgres/*` | Queries, schema inspection, migrations | devops |
| `context7/*` | Docs chính xác theo version của libraries | researcher, architect, implementer, tester |
| `sequential-thinking/*` | Planning phức tạp, debug step-by-step | orchestrator, architect |
| `docker/*` | Quản lý containers, images, health check | devops |
| `memory/*` | Lưu knowledge graph xuyên sessions | orchestrator, researcher, reviewer |
| `playwright/*` | E2E testing, browser automation | researcher, tester, qc |
| `fetch/*` | Tải URL, đọc API responses, crawl docs | orchestrator, researcher, security, qc |

**VS Code built-in tools** (không phải MCP): `editFiles`, `readFile`, `runInTerminal`, `codebase`, `agent`

---

## 8. Portability Guide — Mang `.github/` sang Dự Án Mới

> Folder `.github/` + `AGENTS.md` + `copilot-instructions.md` là **self-contained**.
> Copy sang bất kỳ dự án nào, orchestrator tự bootstraps ngay lần đầu.

### 8.1 Checklist khi chuyển dự án

```
[ ] Copy toàn bộ .github/ vào project root mới
[ ] Copy .vscode/mcp.json vào project .vscode/
[ ] Cập nhật .vscode/mcp.json nếu cần (postgres_url khác, port khác)
[ ] KHÔNG cần sửa gì trong .github/ — orchestrator tự detect
[ ] Mở VS Code workspace mới → nói với Orchestrator bất cứ yêu cầu gì
[ ] Orchestrator tự phát hiện chưa có context.md → kích hoạt BOOTSTRAP MODE
```

### 8.2 BOOTSTRAP MODE tự động (kích hoạt bởi Orchestrator)

Khi không có `docs/architecture/context.md`, Orchestrator chạy:

```
Orchestrator detect: fresh project
  ↓
 researcher → Codebase Audit:
   - Đọc toàn bộ cấu trúc qua filesystem/*
   - Detect stack, conventions, patterns
   - Tìm dead code, temp files, debug prints
   → docs/architecture/context.md
   → docs/architecture/cleanup-report.md
  ↓
Orchestrator → tạo docs/status.yaml skeleton
Orchestrator → lưu facts vào memory/*
  ↓
 implementer → dọn rác (nếu cleanup-report có items)
  ↓
 devops → commit "chore(bootstrap): add project context + cleanup"
  ↓
Tiếp tục xử lý yêu cầu gốc của user
```

### 8.3 Files được tạo sau Bootstrap

```
docs/
├── architecture/
│   ├── context.md          # Stack, conventions, patterns detect được
│   └── cleanup-report.md   # Danh sách rác đã/cần dọn
└── status.yaml             # Skeleton với stack info
```

### 8.4 Tiếp tục phát triển sau Bootstrap

- **Đọc docs/architecture/context.md** → mọi agent đều nắm stack
- **Đọc docs/status.yaml** → biết task gần nhất và state hiện tại
- **Đọc memory/*` → project facts từ các session trước
- Researcher **luôn** đọc context.md làm baseline trước khi research
- Implementer **luôn** follow conventions trong context.md