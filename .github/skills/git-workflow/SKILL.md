---
name: git-workflow
description: 'Kỹ năng quản lý Git workflow chuẩn doanh nghiệp - Branching strategy, conventional commits, PR templates, changelog generation.'
---

# 🌿 Kỹ năng Git Workflow (Enterprise Git Workflow Skill)

## Mục đích
Skill này thiết lập quy trình Git chuẩn doanh nghiệp bao gồm branching strategy, commit conventions, và PR workflow.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Cần thiết lập branching strategy cho dự án
- Cần tạo PR template
- Cần commit code theo convention
- Cần generate changelog

## Branching Strategy (Git Flow Simplified)

```
main (production)
  │
  ├── develop (integration)
  │     │
  │     ├── feature/user-auth
  │     ├── feature/dashboard
  │     └── feature/api-v2
  │
  ├── release/v1.0.0
  │
  └── hotfix/fix-login-bug
```

### Branch Naming Convention
| Type | Pattern | Ví dụ |
|------|---------|-------|
| Feature | `feature/<ticket>-<description>` | `feature/PROJ-123-user-auth` |
| Bugfix | `bugfix/<ticket>-<description>` | `bugfix/PROJ-456-fix-login` |
| Hotfix | `hotfix/<description>` | `hotfix/fix-session-leak` |
| Release | `release/v<semver>` | `release/v1.2.0` |
| Chore | `chore/<description>` | `chore/update-deps` |

## Conventional Commits

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
| Type | Ý nghĩa | SemVer |
|------|---------|--------|
| `feat` | Tính năng mới | MINOR |
| `fix` | Sửa lỗi | PATCH |
| `docs` | Chỉ thay đổi tài liệu | - |
| `style` | Formatting, không thay đổi logic | - |
| `refactor` | Cấu trúc lại code, không thay đổi behavior | - |
| `perf` | Cải thiện hiệu suất | - |
| `test` | Thêm/sửa test | - |
| `chore` | Build, CI, tooling | - |
| `ci` | Thay đổi CI/CD config | - |
| `revert` | Hoàn tác commit trước | - |

### Ví dụ
```bash
# Feature
git commit -m "feat(auth): implement JWT-based authentication"

# Bug fix
git commit -m "fix(api): handle null response from payment service"

# Breaking change
git commit -m "feat(api)!: change user endpoint response format

BREAKING CHANGE: The /api/v1/users response now returns paginated format."

# With ticket reference
git commit -m "feat(dashboard): add analytics chart component

Implement real-time analytics chart using Chart.js.
Supports line, bar, and pie chart types.

Closes: PROJ-789"
```

## Pull Request Template

```markdown
## 📋 Mô tả
{Mô tả ngắn gọn thay đổi này làm gì}

## 🔗 Ticket
- Closes #{ticket_number}

## 🔄 Loại thay đổi
- [ ] ✨ Tính năng mới (feature)
- [ ] 🐛 Sửa lỗi (bugfix)
- [ ] ♻️ Refactor
- [ ] 📝 Documentation
- [ ] 🧪 Test
- [ ] 🔧 Chore

## 📸 Screenshots
{Nếu có thay đổi UI}

## ✅ Checklist
- [ ] Code compiles thành công
- [ ] Tests pass
- [ ] Đã self-review code
- [ ] Đã thêm JSDoc cho public APIs
- [ ] Đã cập nhật documentation
- [ ] Không có breaking changes (hoặc đã ghi chú)
- [ ] Security review (nếu liên quan)

## 🧪 Testing
{Mô tả cách test thay đổi này}

## 📝 Notes
{Ghi chú cho reviewer}
```

## Quy tắc Merge
1. **Squash merge** cho feature branches → develop
2. **Merge commit** cho develop → main
3. **KHÔNG** force push lên `main` hoặc `develop`
4. Xóa branch sau khi merge
