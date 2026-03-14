# 🤖 Multi-Agent Coordination Protocol v10

> **Single Source of Truth** cho giao thức phối hợp.
> Mọi agent đọc file này trước khi bắt đầu bất kỳ task nào.
> Chi tiết từng agent → xem file agent tương ứng trong `.github/agents/`.

---

## 1. Kiến Trúc & Luồng

```
👤 USER
  ↓ yêu cầu
🎯 ORCHESTRATOR (decision engine — không tự execute)
  ├── expand prompt → phân tích → chọn pipeline
  ├── delegate qua tool `agent`
  └── giám sát + tổng hợp
  ↓ delegates to
[🔬 researcher] [🏗️ architect] [💻 implementer] [🔍 reviewer]
[🧪 tester]    [🛡️ security]  [🎯 qc]          [🚀 devops]
```

**Artifacts flow** (không phải direct handoffs):

```
researcher  → docs/research/          → architect, implementer đọc
architect   → docs/architecture/      → implementer đọc
implementer → src/**                  → reviewer, tester scan
reviewer    → docs/reviews/ + score   → orchestrator quyết định
tester      → tests/** + coverage     → qc đọc
security    → docs/security/          → qc + orchestrator
qc          → docs/qc/                → orchestrator quyết định deploy
devops      → git + deploy + monitor  → orchestrator nhận báo cáo
```

---

## 2. Golden Rules

**R1: Sub-agents KHÔNG gọi sub-agents**

```
✅ Agent → Orchestrator → Agent khác
❌ Agent → Agent (dù khẩn cấp)
```

**R2: Git operations là độc quyền DevOps**

```
✅ Orchestrator → DevOps → git
❌ Orchestrator tự git | Implementer tự commit
```

**R3: Deploy chỉ khi ALL gates PASS**

```
Test PASS + Security PASS (0 Critical/High) + QC PASS (≥ 80) + Review ≥ 7
```

**R4: Cleanup state sau mỗi review**

```
Reviewer PHẢI output dead code list (dù là empty)
Orchestrator PHẢI tạo cleanup state nếu list không rỗng
Implementer xóa → DevOps commit "chore(cleanup)"
```

**R5: Context đầy đủ khi giao task**

```
Luôn truyền: task ID, paths đến docs liên quan, stack info, expected output
Không bao giờ: "hãy implement cái này" mà không có context cụ thể
```

---

## 3. Pipeline States

```
IDLE → analysis → planning → researching → designing → implementing
     → reviewing → cleanup → migrating → testing → security_check
     → qc_gate → deploying → monitoring → done

Errors: monitoring → rollback → blocked
        * → blocked (hết retry / unresolvable)
```

**Cleanup state** (MỚI — v10):

- Xảy ra sau `reviewing`, trước `migrating`/`testing`
- Mục đích: xóa dead code, file thừa, approach-drift artifacts
- Skip nếu reviewer report không có dead code
- DevOps tạo commit riêng: `"chore(cleanup): remove dead code  Refs: #ID"`

---

## 4. Shared State: `docs/status.yaml`

**Mọi agent PHẢI:**

```yaml
# TRƯỚC khi bắt đầu
agents.{name}.status: "working"
agents.{name}.current_task: "mô tả"

# SAU khi hoàn thành
agents.{name}.status: "done"
agents.{name}.current_task: ""
task.updated_at: "{ISO timestamp}"
handoff_log: [append entry]
```

---

## 5. Communication Format

```
Bắt đầu:  🤖 [{AGENT}] đang thực thi: {task cụ thể}
PASS:     ✅ [{AGENT}] hoàn tất: {kết quả + metrics + artifacts}
FAIL:     ❌ [{AGENT}] FAIL: {reason + action needed from Orchestrator}
BLOCKER:  ⚠️ [{AGENT}] BLOCKER: {description + impact + options (facts only)}
```

---

## 6. Cấu Trúc Thư Mục

```
project/
├── .github/agents/          # Agent definitions
├── docs/
│   ├── status.yaml          # Shared state
│   ├── architecture/        # context.md, ADRs, system-design
│   ├── api/openapi.yaml     # API contracts
│   ├── research/            # ISSUE-{ID}-{topic}.md
│   ├── reviews/             # ISSUE-{ID}-review.md
│   ├── testing/             # test-plan, coverage-report
│   ├── security/            # ISSUE-{ID}-audit.md
│   ├── qc/                  # ISSUE-{ID}-gate.md
│   ├── migrations/backups/  # DB backups
│   └── notes/session-log.md # Memory fallback
├── src/                     # Source code
├── tests/unit|integration|e2e/
├── migrations/              # DB migration files
└── infra/                   # Dockerfile, docker-compose
```

---

## 7. Quality Thresholds (Reference)

| Metric               | Standard           | Sensitive modules |
| -------------------- | ------------------ | ----------------- |
| Unit coverage        | ≥ 80%              | ≥ 90%             |
| Integration coverage | ≥ 60%              | ≥ 75%             |
| Branch coverage      | ≥ 70%              | ≥ 85%             |
| Review score         | ≥ 7/10             | ≥ 8/10            |
| QC Gate              | ≥ 80/100           | ≥ 90/100          |
| Security             | 0 Critical, 0 High | + 0 Medium        |

**Sensitive modules**: auth, payment, billing, security, crypto, pii, admin

---

## 8. Portability

```bash
# Copy sang project mới:
cp -r .github/agents/ /new-project/.github/agents/
cp .vscode/mcp.json /new-project/.vscode/

# Cập nhật .vscode/mcp.json nếu cần (DB URL, ports)
# Không sửa gì trong agents/ files

# Orchestrator tự detect: không có docs/architecture/context.md
# → Kích hoạt BOOTSTRAP MODE tự động
```

---

## 9. MCP Server Mapping

| Server                  | Agents                                     |
| ----------------------- | ------------------------------------------ |
| `github/*`              | orchestrator, devops                       |
| `filesystem/*`          | all                                        |
| `postgres/*`            | devops                                     |
| `context7/*`            | researcher, architect, implementer, tester |
| `sequential-thinking/*` | orchestrator, architect                    |
| `docker/*`              | devops                                     |
| `memory/*`              | orchestrator, researcher, reviewer         |
| `playwright/*`          | researcher, tester, qc                     |
| `fetch/*`               | orchestrator, researcher, security, qc     |
