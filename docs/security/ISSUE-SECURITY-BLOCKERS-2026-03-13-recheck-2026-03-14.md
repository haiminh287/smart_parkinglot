# Security Recheck — ISSUE-SECURITY-BLOCKERS-2026-03-13 (2026-03-14)

**Risk Level:** High  
**Deploy Ready:** NO

| Severity | Count |
| --- | ---: |
| 🔴 Critical | 0 |
| 🟠 High | 1 |
| 🟡 Medium | 0 |
| 🟢 Low | 0 |

## Scope
- Frontend: `spotlove-ai` (`npm audit --json`)
- Backend: tất cả file `requirements*.txt` trong `backend-microservices` (`pip-audit`)

## Findings

### [VULN-001] PyJWT vulnerability in backend baseline requirements
- **Package:** `PyJWT==2.10.1`
- **Vulnerability:** `CVE-2026-32597` (`GHSA-752w-5fwx-jx9f`)
- **Location:** `backend-microservices/requirements.txt`
- **Fix version:** `PyJWT>=2.12.0`
- **Assessment:** Blocking (classified High for security gate)
- **Evidence:** `docs/security/recheck-backend-microservices_requirements.txt.pip-audit.raw.txt`

## Recheck Results

### Frontend (flatted high recheck)
- `npm audit` metadata:
  - High: 0
  - Critical: 0
  - Remaining non-blocking: Low 3, Moderate 2
- `flatted` high issue is no longer present in audit result.
- Evidence: `docs/security/recheck-fe-npm-audit-2026-03-14.json`

### Backend (requests CVE recheck)
- `requests==2.32.5` appears with `vulns: []` in scan outputs (no active advisory in this run).
- New blocker found at platform baseline requirements: `PyJWT` CVE above.
- `ai-service-fastapi/requirements.txt` had pip resolution failure (`torch==1.13.1+cu116` not resolvable in audit sandbox), so this manifest is not fully auditable by current automated run.
- Evidence:
  - `docs/security/recheck-security-gate-2026-03-14.json`
  - `docs/security/recheck-backend-microservices_ai-service-fastapi_requirements.txt.pip-audit.raw.txt`

## Security Gate Decision
- **Gate:** FAIL
- **Reason:** `High/Critical must be zero` is not met due to `CVE-2026-32597` (PyJWT).
- **Deploy recommendation:** Block deployment until PyJWT is upgraded and backend audit is re-run clean.

## Follow-up Actions
1. Upgrade `PyJWT` to `>=2.12.0` in `backend-microservices/requirements.txt` and re-lock/retest.
2. Re-run backend `pip-audit` and confirm zero High/Critical.
3. For AI service, provide an audit-compatible index/source for CUDA-pinned torch package or use an SBOM-based scan fallback for that manifest.
