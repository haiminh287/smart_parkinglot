---
name: security-audit
description: 'Bộ kỹ năng audit bảo mật ứng dụng. Bao gồm SAST scanning, dependency audit, secrets detection, và OWASP compliance check.'
---

# 🔒 Kỹ năng Audit Bảo mật Ứng dụng (Security Audit Skill)

## Mục đích
Skill này cung cấp quy trình kiểm tra bảo mật toàn diện cho ứng dụng, đảm bảo tuân thủ OWASP Top 10 và các tiêu chuẩn bảo mật doanh nghiệp.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Cần audit bảo mật trước khi deploy
- Cần kiểm tra dependencies có lỗ hổng
- Cần phát hiện secrets bị lộ trong code
- Cần đánh giá OWASP compliance

## Quy trình Thực hiện

### 1. Dependency Vulnerability Scan
```bash
# NPM Audit
npm audit --json > reports/npm-audit.json

# Kiểm tra với better-npm-audit (strict mode)
npx better-npm-audit audit --level moderate

# Snyk (nếu có)
npx snyk test --json > reports/snyk-report.json
```

### 2. Secret Detection
```bash
# Tìm kiếm patterns nhạy cảm trong codebase
# API Keys
grep -rn "AKIA[A-Z0-9]{16}" src/ --include="*.{js,ts,json,env}"

# Private Keys
grep -rn "BEGIN.*PRIVATE KEY" src/ --include="*.{js,ts,pem}"

# Passwords
grep -rn "password\s*=\s*['\"]" src/ --include="*.{js,ts,json}"

# Connection strings
grep -rn "mongodb://\|postgres://\|mysql://" src/ --include="*.{js,ts,json}"

# JWT Tokens
grep -rn "eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*" src/
```

### 3. OWASP Top 10 Checklist (2021)

#### A01: Broken Access Control
- [ ] Role-based access control (RBAC) được implement
- [ ] Default deny principle được áp dụng
- [ ] APIs kiểm tra authorization ở mọi endpoint
- [ ] CORS policy được cấu hình strict

#### A02: Cryptographic Failures
- [ ] Mật khẩu hash bằng bcrypt/argon2 với salt
- [ ] Dữ liệu nhạy cảm mã hóa at-rest và in-transit
- [ ] TLS/SSL được sử dụng cho mọi kết nối
- [ ] Không sử dụng thuật toán mã hóa yếu (MD5, SHA1)

#### A03: Injection
- [ ] Parameterized queries / ORM cho SQL
- [ ] Input sanitization cho mọi user input
- [ ] Output encoding cho HTML, JS, URL
- [ ] Command injection prevention

#### A04: Insecure Design
- [ ] Threat modeling đã thực hiện
- [ ] Security requirements trong design docs
- [ ] Authentication flow được thiết kế an toàn

#### A05: Security Misconfiguration
- [ ] Default credentials đã được thay đổi
- [ ] Error messages không expose stack traces
- [ ] Security headers được thiết lập (CSP, HSTS, X-Frame-Options)
- [ ] Không có directory listing enabled

#### A06: Vulnerable & Outdated Components
- [ ] Dependencies đều ở phiên bản mới nhất
- [ ] Không có known vulnerabilities trong dependencies
- [ ] Lock file (package-lock.json) được commit

#### A07: Identification & Authentication Failures
- [ ] Multi-factor authentication (MFA) cho admin
- [ ] Password policy enforcement (min 8 chars, mixed case, digits)
- [ ] Account lockout sau N lần thử sai
- [ ] JWT tokens có expiration hợp lý

#### A08: Software & Data Integrity Failures
- [ ] CI/CD pipeline có integrity checks
- [ ] Dependencies từ trusted sources
- [ ] Code review trước khi merge

#### A09: Security Logging & Monitoring Failures
- [ ] Authentication events được log
- [ ] Authorization failures được log
- [ ] Input validation failures được log
- [ ] Logs không chứa sensitive data

#### A10: Server-Side Request Forgery (SSRF)
- [ ] Whitelist cho external URLs
- [ ] Internal network access restricted
- [ ] DNS rebinding prevention

### 4. Security Headers Checklist
```javascript
// Danh sách headers bảo mật cần có
const securityHeaders = {
  'Content-Security-Policy': "default-src 'self'",
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};
```

### 5. Quy tắc Xuất Báo cáo
- Mọi findings phải có **severity level**: Critical, High, Medium, Low, Info
- Mỗi finding phải có **remediation steps** cụ thể
- Báo cáo lưu tại `docs/security/audit-report-{date}.md`
- **KHÔNG BAO GIỜ** đưa giá trị thật của secrets vào báo cáo
