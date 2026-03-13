# Cloudflare Security Controls Evidence

Ngày cập nhật: 2026-03-13  
Mục tiêu: Cung cấp artifact verify cho Security/QC trước deploy production.

## 0) Trạng thái phiên deploy hiện tại

- Kết quả tổng quan: `BLOCKED`
- Lý do chính:
  - Không có local `wrangler` authentication cho Cloudflare Pages
  - Không có local env secrets `CF_API_TOKEN`, `CF_ACCOUNT_ID`, `CF_PAGES_PROJECT`, `CF_TUNNEL_TOKEN`
  - Chưa có hostname/zone production được xác nhận cho backend tunnel của dự án này
- Artifact chi tiết: `docs/deployment-report.md`

## 1) TLS mode — Full (strict)

- Zone: `CHƯA XÁC NHẬN`
- Vị trí dashboard: SSL/TLS → Overview
- Giá trị bắt buộc: `Full (strict)`
- Trạng thái phiên này: `BLOCKED - chưa có quyền verify dashboard/API`
- Evidence cần đính kèm khi unblock:
  - Screenshot trang SSL/TLS Overview có timestamp
  - Ghi chú cert origin đang dùng (Cloudflare Origin Cert hoặc CA chuẩn)

## 2) WAF Managed Rules

- Vị trí dashboard: Security → WAF → Managed rules
- Trạng thái bắt buộc:
  - Managed ruleset đang bật
  - OWASP baseline rules đang bật
- Trạng thái phiên này: `BLOCKED - chưa có quyền verify dashboard/API`
- Evidence cần đính kèm khi unblock:
  - Screenshot trạng thái ruleset ON
  - Export/ghi chú version ruleset (nếu có)

## 3) Rate limiting baseline

- Vị trí template rule: `infra/cloudflare/security-controls/rate-limit-rules.example.json`
- Baseline cần áp dụng:
  - `POST /api/auth/login`: 10 req/phút/IP
  - `POST /api/auth/register`: 5 req/phút/IP
  - `POST /api/chatbot/*`: 30 req/phút/IP
  - `/api/*` còn lại: 120 req/phút/IP
- Trạng thái phiên này:
  - Template baseline: `READY`
  - Active trên Cloudflare zone thật: `BLOCKED - chưa verify được`
- Evidence cần đính kèm khi unblock:
  - Screenshot danh sách rules đang active
  - Ảnh/ghi chú test vượt ngưỡng và action trả về (`block`/`managed_challenge`)

## 4) Origin protection baseline

- Chỉ expose public qua Cloudflare (`app.<domain>`, `api.<domain>`)
- Origin firewall chỉ allow Cloudflare IP ranges (nếu đã bật host firewall)
- Trạng thái phiên này: `PARTIAL`
  - Reverse proxy + tunnel skeleton đã có trong repo
  - Origin production firewall/routing thật chưa được cung cấp để verify
- Evidence cần đính kèm khi unblock:
  - Snapshot firewall rules hoặc IaC snippet tương đương

## 5) Kết quả xác nhận

- Security reviewer: `pending`
- QC reviewer: `pending`
- Kết luận: `FAIL - deploy blocked bởi thiếu quyền/secrets/runtime target`
- Ghi chú ngoại lệ/risk acceptance (nếu có):
  - Có thể re-run Security/QC sau khi bổ sung secrets GitHub + xác nhận zone/hostname + thu screenshot/API evidence thực tế.
