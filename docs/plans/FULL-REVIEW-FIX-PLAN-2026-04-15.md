# KẾ HOẠCH FIX TOÀN DIỆN — Sau Review 2026-04-15

**Nguồn:** Hai code review song song (backend+DevOps + frontend+Unity) qua `superpowers:code-reviewer`.
**HEAD review:** `3f5104f`
**Status khởi điểm:** 🔴 NOT production-ready — 12 Critical, 33 Important, 30 Minor, ~28 god classes vi phạm "file ≤ 300 lines".
**Mục tiêu:** Đưa hệ thống về trạng thái **mergeable → deployable** trong 3 sprint (~5-7 tuần).

---

## 📌 CHANGELOG — Plan audit 2026-04-15 v2

Sau code-reviewer audit lần 2 trên plan này, các correction sau được apply:

- **S1-CRIT-1**: sửa line range `491-495` → `491-494` (file tổng 494 dòng).
- **S1-CRIT-2a**: bổ sung **4 file bị bỏ sót**: `realtime-service-go/internal/config/config.go:17` (Go source!), `ai-service-fastapi/run_local.bat:28`, `ai-service-fastapi/test_ai_detection_unity.py:23`, `test_e2e_full_flow.py:43`. Tổng **11 file**, không phải 7.
- **S1-CRIT-2a**: note rõ pydantic v2 phải import `from pydantic_settings import BaseSettings`.
- **S1-CRIT-4**: tách thành **S1-CRIT-4a (backend)** + **S1-CRIT-4b (Unity simulator X-Device-Token injection)**. Sửa tên hàm `verify_esp32_token` → `verify_device_token`, status `401` → `403`.
- **S1-CRIT-5**: xoá comment import `CarSlot` nhầm, thêm Lua CAS script cho Option B Redis lock.
- **S1-CRIT-9 TypeScript strict**: phase-in qua 3 sprint thay vì dồn vào Sprint 1.
- **S2-IMP-1**: thêm **Bước 0 — BE/FE contract audit**; sửa snippet không dùng `vehicle_brand`/`vehicle_model`/`floor_name` (không tồn tại trong model), dùng `floor_level` + `vehicle_license_plate`/`vehicle_type`. **Bỏ migration Bước 1** vì field đã có sẵn trong model.
- **S2-IMP-2**: thêm `event_id UUID` + consumer-side dedup table + DLQ pattern.
- **S2-IMP-3 Gateway Go**: rewrite snippet compile-clean (không shadow `url` package, tạo helper method `ServiceURLs()` nếu cần).
- **S2-IMP-5 esp32.py refactor**: bump 2 ngày → **3-4 ngày**.
- **S2-IMP-9 layering**: đếm lại pages thật, bump 3-4 ngày → **6-8 ngày**.
- **S2-IMP-10 Unity**: sửa path `Gate/BarrierController.cs` → `Parking/BarrierController.cs`.
- **S1-CRIT-2b**: thêm bước "re-trigger deploy workflow" sau khi rotate GitHub secret.
- **S1-CRIT-11**: thêm shared volume uid handling (entrypoint chown hoặc build-time copy thay vì mount).
- **S3-DEAD**: bổ sung `booking_for_unity*.json`, `test_e2e_results.json`.
- **Testing**: thêm mục **"Regression test checklist per task"** ở cuối mỗi sprint.
- **Timeline tổng**: bump 20-26 ngày → **27-35 ngày công** (5-7 tuần thay vì 5-6).

---

## Cách dùng tài liệu này

- Mỗi task có ID duy nhất (`S1-CRIT-1`, `S2-IMP-4`, v.v.) để tracking.
- Mỗi task ghi rõ: **file:line**, **triệu chứng hiện tại**, **fix chi tiết (có code snippet nếu phức tạp)**, **verification**, **thời gian ước tính**, **blast radius** (dùng `gitnexus_impact` trước khi đụng).
- Thứ tự trong Sprint 1 không được đảo — có dependency (vd phải fix CRIT-1 trước mới test được các thứ khác).
- Sau mỗi phase phải chạy verification matrix ở cuối file.

---

## TL;DR — Bản đồ Sprint

| Sprint | Thời lượng (v2) | Focus | Nhóm vấn đề | Gate thoát |
|---|---|---|---|---|
| **Sprint 1** | 7-10 ngày | Stability + Security | 12 Critical + 5 blocking Important | Toàn bộ service boot, e2e Playwright PASS, không hardcoded secret, Unity simulator PASS với token |
| **Sprint 2** | 14-18 ngày | Scale + Maintain | 18 Important còn lại + god-class refactor | N+1 gone, bundle cut ≥30%, file ≤ 500 lines toàn repo |
| **Sprint 3** | 6-8 ngày | Cleanup + Polish | 30 Minor + dead code + docs | Không còn dead deps, audit artifacts fresh, docs đồng bộ, TypeScript full strict |

---

# SPRINT 1 — STABILITY + SECURITY

**Mục tiêu cuối sprint:**
- ✅ Tất cả 11 service Docker boot khoẻ
- ✅ Không còn hardcoded secret fallback trong source
- ✅ ESP32 barrier không mở cho request thiếu token
- ✅ FE không log credentials trong prod
- ✅ Double-booking race đóng
- ✅ Production cookie hardening đúng
- ✅ TypeScript strict bật (ít nhất `noImplicitAny` + `strictNullChecks`)

**Thứ tự thực hiện bắt buộc:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → S1-IMP-0 → S1-IMP-1

---

## S1-CRIT-1 · Fix syntax error `parking-service/infrastructure/views.py`

**File:** `backend-microservices/parking-service/infrastructure/views.py:491-494` (file tổng 494 dòng)
**Impact:** Blocker tuyệt đối — service không boot, toàn bộ flow booking/slot-status/check-in/check-out chết.
**Thời gian:** 5 phút.

**Triệu chứng (verified bằng Read thực tế):**
```python
# dòng 482-488: CameraViewSet.get_stream() return Response bình thường
        return Response({
            'stream_url': camera.stream_url or f'rtsp://camera-server/{camera.id}/stream',
            ...
            'zone': camera.zone.name if camera.zone else None,
        })
# dòng 489-490: blank lines đóng method
# dòng 491-492: KHỐI DƯ duplicate (2 dòng content)
            'zone': camera.zone.name if camera.zone else None,
        })
# dòng 493-494: blank trailing
```

**Fix:**
1. Xoá dòng **491-494** (2 dòng content duplicate + 2 blank trailing).
2. File phải kết thúc ở dòng 490 với blank line cuối cùng.
3. Verify: `python -c "import ast; ast.parse(open('backend-microservices/parking-service/infrastructure/views.py').read())"` → PASS.
4. `cd backend-microservices/parking-service && python manage.py check` → PASS.

**Verification:**
```bash
cd backend-microservices && docker compose up -d --build parking-service
docker compose logs parking-service | grep -i "error\|traceback" # phải rỗng
curl http://localhost:8003/health/ # phải trả 200
```

---

## S1-CRIT-2a · Xoá hardcoded `GATEWAY_SECRET` fallback (11 file)

**Files + dòng chính xác (verified bằng grep thực tế 2026-04-15):**

*Python Django settings (4 file):*
1. `backend-microservices/parking-service/parking_service/settings.py:119`
2. `backend-microservices/booking-service/booking_service/settings.py:150`
3. `backend-microservices/vehicle-service/vehicle_service/settings.py:121`
4. (`auth-service/auth_service/settings.py` đã đúng fail-fast — không đụng)

*Python FastAPI pydantic (2 file):*
5. `backend-microservices/notification-service-fastapi/app/config.py:15`
6. `backend-microservices/ai-service-fastapi/app/config.py:14` (+ `DB_PASSWORD: str = "rootpassword"` cùng dòng gần đó — fix luôn)

*Python module-level (2 file):*
7. `backend-microservices/booking-service/bookings/tasks.py:63`
8. `backend-microservices/booking-service/bookings/serializers.py:19`

*Go service (1 file — bị bỏ sót trong plan v1):*
9. `backend-microservices/realtime-service-go/internal/config/config.go:17`

*Dev/test scripts hardcoded secret (2 file — bị bỏ sót):*
10. `backend-microservices/ai-service-fastapi/run_local.bat:28`
11. `backend-microservices/ai-service-fastapi/test_ai_detection_unity.py:23`
12. `backend-microservices/test_e2e_full_flow.py:43` (root-level e2e script)

**Thời gian:** 2 giờ (tăng từ 1.5h do có thêm Go + scripts).
**Blast radius:** Mọi inter-service HTTP call + gateway middleware. **Test toàn bộ e2e sau khi fix.**

**Fix pattern (Django settings):**
```python
# ❌ SAI
GATEWAY_SECRET = config('GATEWAY_SECRET', default='gateway-internal-secret-key')

# ✅ ĐÚNG
GATEWAY_SECRET = config('GATEWAY_SECRET')  # raise nếu thiếu
```

**Fix pattern (FastAPI pydantic v2 config — `ai-service-fastapi` dùng `pydantic==2.12.5` + `pydantic-settings==2.13.1`):**
```python
# ❌ SAI (pydantic v1 style, hoặc có default)
from pydantic import BaseSettings
class Settings(BaseSettings):
    GATEWAY_SECRET: str = "gateway-internal-secret-key"
    DB_PASSWORD: str = "rootpassword"

# ✅ ĐÚNG (pydantic v2)
from pydantic_settings import BaseSettings  # ← check import path
class Settings(BaseSettings):
    GATEWAY_SECRET: str  # required, no default — sẽ raise ValidationError nếu env thiếu
    DB_PASSWORD: str  # required
```

**Pre-check:** `grep -n "from pydantic" backend-microservices/*/app/config.py` — nếu còn `from pydantic import BaseSettings` phải đổi sang `from pydantic_settings import BaseSettings` (đã deprecated trong pydantic v2).

**Fix pattern (Go — `realtime-service-go/internal/config/config.go`):**
```go
// ❌ SAI
GatewaySecret: getEnv("GATEWAY_SECRET", "gateway-internal-secret-key"),

// ✅ ĐÚNG
GatewaySecret: mustGetEnv("GATEWAY_SECRET"),

// Helper (thêm nếu chưa có):
func mustGetEnv(key string) string {
    v := os.Getenv(key)
    if v == "" {
        log.Fatalf("required env var %s not set", key)
    }
    return v
}
```

**Fix pattern (dev scripts `run_local.bat` + `test_ai_detection_unity.py` + `test_e2e_full_flow.py`):**

Đọc secret từ `.env` local, không commit hardcoded. Ví dụ Python script:
```python
# ❌ SAI
GATEWAY_SECRET = "gateway-internal-secret-key"

# ✅ ĐÚNG
import os
from dotenv import load_dotenv
load_dotenv(".env")  # hoặc .env.local
GATEWAY_SECRET = os.environ["GATEWAY_SECRET"]  # raise nếu thiếu
```

`run_local.bat` (Windows):
```batch
REM ❌ SAI
set GATEWAY_SECRET=gateway-internal-secret-key

REM ✅ ĐÚNG — load từ .env
for /f "tokens=1,2 delims==" %%a in (.env) do if "%%a"=="GATEWAY_SECRET" set GATEWAY_SECRET=%%b
if "%GATEWAY_SECRET%"=="" (echo ERROR: GATEWAY_SECRET not set && exit /b 1)
```

**Fix pattern (module-level read, `serializers.py:19` + `tasks.py:63`):**
```python
# ❌ SAI
GATEWAY_SECRET = os.environ.get('GATEWAY_SECRET', 'gateway-internal-secret-key')

# ✅ ĐÚNG — đọc qua Django settings lazy
from django.conf import settings
# rồi dùng settings.GATEWAY_SECRET trong hàm, không module-level
```

**Side-task:** Test fixtures ở `*/tests/conftest.py` dùng literal `"gateway-internal-secret-key"` — sửa thành:
```python
@pytest.fixture(autouse=True)
def gateway_secret_env(monkeypatch):
    monkeypatch.setenv('GATEWAY_SECRET', 'test-secret-' + os.urandom(8).hex())
```

**Verification:**
```bash
# 1. Không còn literal trong bất kỳ source nào (Python + Go + bat)
grep -rn "gateway-internal-secret-key" backend-microservices/ \
  --include="*.py" --include="*.go" --include="*.bat" \
  | grep -v tests/ | grep -v __pycache__ | grep -v venv/
# phải rỗng (tests/conftest.py dùng fixture env sẽ không match)

# 2. Boot với env thiếu phải fail ngay
cd backend-microservices
GATEWAY_SECRET= docker compose up parking-service 2>&1 | grep -i "required\|missing\|validation"

# 3. Boot bình thường với env đầy đủ
docker compose up -d --build
docker compose ps | grep -c "healthy\|Up" # ≥ 11
```

**Gitnexus check trước khi fix:**
```
mcp__gitnexus__query({query: "GATEWAY_SECRET usage", repo: "Project_Main"})
mcp__gitnexus__context({name: "GATEWAY_SECRET", repo: "Project_Main"})
```
Xem tất cả caller, đảm bảo không quên file.

---

## S1-CRIT-2b · Rotate + di chuyển secret Playwright

**Files:**
- `spotlove-ai/e2e/global-setup.ts:16`
- `spotlove-ai/e2e/checkin-flow.spec.ts:22`
- (kiểm tra thêm) `spotlove-ai/e2e/api-endpoints.spec.ts`, các `.spec.ts` khác

**Impact:** Secret `gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE` có prefix trông như production → **phải treat as leaked**.

**Thời gian:** 2 giờ (rotate + update + verify).

**Fix (5 bước):**

### Bước 1 — Git history scan
```bash
cd "C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main"
git log -p -S "gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE" --all
git log -p -S "gw-prod-" --all
```
Ghi lại commit gốc + mọi file đã từng chứa secret này.

### Bước 2 — Quyết định repo status
- Nếu repo **public trên GitHub** → secret đã leak, rotate bắt buộc.
- Nếu repo **private only** → vẫn rotate vì có thể đã clone về nhiều máy.
- Dù sao cũng **phải rotate**.

### Bước 3 — Rotate secret
1. Generate secret mới: `python -c "import secrets; print('gw-prod-' + secrets.token_urlsafe(32))"`
2. Update Cloudflare Pages env `VITE_GATEWAY_SECRET` (Cloudflare dashboard → Pages project → Settings → Environment variables → update cả production + preview)
3. Update GitHub Secrets `VITE_GATEWAY_SECRET` + `GATEWAY_SECRET` (GitHub → repo → Settings → Secrets and variables → Actions)
4. Update `.env` trên server backend (`backend-microservices/.env` → `GATEWAY_SECRET=...`)
5. **Re-trigger deploy workflow để apply secret mới:**
   ```bash
   # Option 1: Trigger manual
   gh workflow run deploy-cloudflare-pages.yml --ref main

   # Option 2: Dummy commit để trigger auto-deploy
   git commit --allow-empty -m "chore: trigger redeploy after secret rotation  Refs: S1-CRIT-2b"
   git push origin main
   ```
6. Verify deploy log: `gh run list --workflow=deploy-cloudflare-pages.yml --limit 1`
7. Restart backend services để load env mới:
   ```bash
   cd backend-microservices && docker compose restart auth-service parking-service booking-service vehicle-service ai-service-fastapi chatbot-service-fastapi notification-service-fastapi payment-service-fastapi gateway-service-go realtime-service-go
   ```

### Bước 4 — Refactor Playwright
```ts
// spotlove-ai/e2e/global-setup.ts
import * as dotenv from "dotenv";
dotenv.config({ path: ".env.test" });

const GATEWAY_SECRET = process.env.E2E_GATEWAY_SECRET;
if (!GATEWAY_SECRET) {
  throw new Error("E2E_GATEWAY_SECRET must be set in .env.test");
}
```

Tạo `spotlove-ai/.env.test` (gitignored):
```
E2E_GATEWAY_SECRET=dev-only-secret-for-playwright
E2E_ADMIN_PASSWORD=<generated>
```

Update `.gitignore`:
```
spotlove-ai/.env.test
```

Update `.env.example`:
```
# Chỉ dùng cho Playwright e2e, KHÔNG phải cùng secret với prod
E2E_GATEWAY_SECRET=
E2E_ADMIN_PASSWORD=
```

### Bước 5 — Verify
```bash
grep -rn "gw-prod-" spotlove-ai/ --exclude-dir=node_modules --exclude-dir=dist
# phải rỗng

cd spotlove-ai && cp .env.test.example .env.test && npm run e2e -- --project=chromium
# phải PASS
```

**Lưu ý:** `BAO_CAO_PLAN.md` + `docs/report.md` có thể đã ghi secret vào log e2e — grep và redact luôn.

---

## S1-CRIT-3 · Xoá Django admin khỏi `auth-service`

**Files:**
- `backend-microservices/auth-service/auth_service/settings.py:20`
- `backend-microservices/auth-service/auth_service/urls.py:12`
- `backend-microservices/shared/gateway_middleware.py:29`

**Impact:** `/admin/` đang là bypass lane cho trust-model. Ai vào thẳng `auth-service:8001/admin/` (hoặc forge gateway route) đều thấy Django admin login.

**Thời gian:** 30 phút.

**Fix:**

### 1. `auth-service/auth_service/settings.py:20`
```python
INSTALLED_APPS = [
    # REMOVED: 'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    ...
]
```

### 2. `auth-service/auth_service/urls.py:12`
Xoá `path('admin/', admin.site.urls)` + import `from django.contrib import admin`.

### 3. `shared/gateway_middleware.py:29`
```python
# ❌ SAI
if request.path.endswith('/health/') or '/_test/' in request.path or request.path.startswith('/admin/'):
    return self.get_response(request)

# ✅ ĐÚNG
if request.path.endswith('/health/') or '/_test/' in request.path:
    return self.get_response(request)
```

### 4. Chạy migrate nếu có
```bash
cd backend-microservices/auth-service
python manage.py migrate  # verify không có migration liên quan admin
```

### 5. Verify
```bash
docker compose up -d --build auth-service
curl -i http://localhost:8001/admin/
# Expected: 403 Forbidden (gateway middleware chặn) HOẶC 404 Not Found (url xoá)
# KHÔNG được là 200 với Django admin HTML
```

---

## S1-CRIT-4 · ESP32 token bắt buộc (SPLIT thành 4a + 4b)

**Impact:** Router `/ai/parking/esp32/check-in`, `/check-out`, `/barrier/open`, `/barrier/close`, `/cash-payment` → **attacker mở barrier vật lý từ xa**.

⚠️ **CRITICAL ORDERING**: Phải merge **4b (Unity)** TRƯỚC hoặc CÙNG LÚC với **4a (backend)**. Nếu chỉ merge 4a, Unity simulator sẽ bị 403 mọi ESP32 request → Playwright e2e + Unity smoke test break.

---

### S1-CRIT-4a · Backend ESP32 token required

**Files:**
- `backend-microservices/ai-service-fastapi/app/config.py:27` (ESP32_DEVICE_TOKEN field)
- `backend-microservices/ai-service-fastapi/app/routers/esp32.py:62-69` (verify function)
- `backend-microservices/docker-compose.yml:339`
- `backend-microservices/docker-compose.prod.yml` (nếu override)
- `backend-microservices/.env.example` (thêm placeholder)

**Thời gian:** 45 phút.

#### 1. `ai-service-fastapi/app/config.py:27`
```python
# ❌ SAI
ESP32_DEVICE_TOKEN: str = ""

# ✅ ĐÚNG
ESP32_DEVICE_TOKEN: str  # required, no default
```

#### 2. `ai-service-fastapi/app/routers/esp32.py:62-69`

**Tên hàm thực tế là `verify_device_token`** (không phải `verify_esp32_token` như plan v1) và raise **403** (không phải 401). File hiện tại dùng `hmac.compare_digest` timing-safe — giữ lại.

```python
# ❌ SAI (hiện tại — skip auth khi empty token)
async def verify_device_token(
    x_device_token: str = Header(default=""),
) -> None:
    expected = settings.ESP32_DEVICE_TOKEN
    if not expected:
        return  # ← REMOVE: silent-skip khi empty
    if not x_device_token or not hmac.compare_digest(x_device_token, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing device token.")

# ✅ ĐÚNG — không còn early return
async def verify_device_token(
    x_device_token: str = Header(default=""),
) -> None:
    expected = settings.ESP32_DEVICE_TOKEN
    # Pydantic đã validate non-empty tại startup (config.py required field),
    # nên ở đây chỉ cần compare
    if not x_device_token or not hmac.compare_digest(x_device_token, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing device token.")
```

#### 3. `docker-compose.yml:339`
```yaml
# ❌ SAI
- ESP32_DEVICE_TOKEN=${ESP32_DEVICE_TOKEN:-}

# ✅ ĐÚNG
- ESP32_DEVICE_TOKEN=${ESP32_DEVICE_TOKEN:?ESP32_DEVICE_TOKEN must be set in .env}
```

#### 4. Generate token + update `.env` + `.env.example`
```bash
python -c "import secrets; print('esp32-' + secrets.token_urlsafe(32))"
# Copy vào .env: ESP32_DEVICE_TOKEN=esp32-...
```

Update `backend-microservices/.env.example`:
```bash
# ESP32 IoT device authentication (required for /ai/parking/esp32/* routes)
ESP32_DEVICE_TOKEN=
```

#### 5. Verify backend
```bash
# Missing token → 403
curl -X POST http://localhost:8009/ai/parking/esp32/check-in/ \
  -H "Content-Type: application/json" -d '{}'
# Expected: {"detail": "Invalid or missing device token."}, status 403

# Correct token → pass
curl -X POST http://localhost:8009/ai/parking/esp32/check-in/ \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: esp32-..." -d '{}'
# Expected: không phải 403 (có thể 400/422 do body empty, nhưng đã qua auth)
```

---

### S1-CRIT-4b · Unity simulator inject `X-Device-Token`

**Files:**
- `ParkingSimulatorUnity/Assets/Resources/ApiConfig.asset` (ScriptableObject)
- `ParkingSimulatorUnity/Assets/Scripts/API/ApiConfig.cs`
- `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs`
- `ParkingSimulatorUnity/Assets/Scripts/IoT/ESP32Simulator.cs`

**Thời gian:** 1-2 giờ.

**Triệu chứng hiện tại:** grep `X-Device-Token` trên Unity → **0 match**. Simulator gọi `/ai/parking/esp32/*` không inject header → sau khi 4a merge sẽ bị 403 toàn bộ.

#### 1. Thêm field vào `ApiConfig.cs`
```csharp
[CreateAssetMenu(fileName = "ApiConfig", menuName = "ParkingSim/Api Config")]
public class ApiConfig : ScriptableObject
{
    public string GatewayUrl;
    public string GatewaySecret;
    public string Esp32DeviceToken;  // ← THÊM
    public bool useMockData;
    ...
}
```

#### 2. Gán token thật trong Inspector
Mở `Assets/Resources/ApiConfig.asset` trong Unity Editor → field `Esp32DeviceToken` → paste token giống backend `.env`.

**Lưu ý:** `ApiConfig.asset` hiện đang **committed trong git** (không gitignored). Nếu token được paste vào asset và commit, secret lộ. **Option an toàn:** đọc từ env var hoặc `PlayerPrefs`:
```csharp
// Assets/Scripts/API/ApiService.cs
public string Esp32DeviceToken => !string.IsNullOrEmpty(config.Esp32DeviceToken)
    ? config.Esp32DeviceToken
    : System.Environment.GetEnvironmentVariable("ESP32_DEVICE_TOKEN") ?? "";
```

#### 3. Inject header trong mọi ESP32 endpoint
`ApiService.cs` — tìm các method gọi `/ai/parking/esp32/*`. Ví dụ:
```csharp
public IEnumerator PostESP32CheckIn(ESP32CheckInRequest request, Action<ESP32Response> onComplete)
{
    var url = $"{config.GatewayUrl}/ai/parking/esp32/check-in/";
    using (var req = new UnityWebRequest(url, "POST"))
    {
        req.SetRequestHeader("Content-Type", "application/json");
        req.SetRequestHeader("X-Device-Token", Esp32DeviceToken);  // ← THÊM
        // ... upload + response handling
    }
}
```

**Áp dụng cho tất cả endpoint ESP32:** `/check-in/`, `/check-out/`, `/barrier/open/`, `/barrier/close/`, `/cash-payment/`, `/heartbeat/`, `/register/`, `/verify-slot/`.

Hoặc cleaner: wrap trong helper `CreateESP32Request(url, method)` inject header một chỗ.

#### 4. Verify Unity
Mở Unity Editor → Play scene → trigger vehicle checkin → kiểm tra Console:
- Không có log `403 Forbidden`
- ESP32Simulator log `Check-in successful`

#### 5. Test ngược — token sai
Tạm đổi `ApiConfig.asset.Esp32DeviceToken` thành `"wrong-token"` → Play → phải thấy 403 trong Console → revert.

---

### Verify kết hợp 4a + 4b
```bash
# Boot stack
docker compose up -d --build ai-service-fastapi

# Unity Play mode → checkin flow → PASS
# Playwright e2e → PASS
cd spotlove-ai && npm run e2e -- --grep checkin
```

---

## S1-CRIT-5 · Fix double-booking race

**File:** `backend-microservices/booking-service/bookings/serializers.py:271-322`
**Thời gian:** 0.5 ngày.
**Impact:** 2 user có thể book cùng 1 slot trong cùng khoảng thời gian → physical conflict.

**Gitnexus pre-check:**
```
mcp__gitnexus__context({name: "CreateBookingSerializer", repo: "Project_Main"})
mcp__gitnexus__impact({target: "CreateBookingSerializer", direction: "upstream", repo: "Project_Main"})
```
Ghi lại mọi caller trước khi sửa.

**Gốc vấn đề:**
```python
# ❌ SAI
with transaction.atomic():
    conflict = Booking.objects.select_for_update().filter(
        slot_id=slot_id,
        start_time__lt=end_time,
        end_time__gt=start_time,
        status__in=['active', 'confirmed']
    ).exists()
    if conflict:
        raise ValidationError(...)
    booking = Booking.objects.create(...)
```

`SELECT FOR UPDATE` với MySQL InnoDB chỉ lock hàng khớp filter. Nếu chưa có booking nào trong khoảng thời gian → không lock gì → 2 request đồng thời đều thấy `conflict=False` → cả 2 insert.

**Fix (chọn 1 trong 3, đề xuất Option A):**

### Option A — MySQL advisory lock qua `GET_LOCK` (đề xuất cho booking-service)

**Lưu ý quan trọng:**
- `CarSlot` model thuộc `parking-service`, **không** import trực tiếp trong `booking-service`. Dùng advisory lock `GET_LOCK` là đúng.
- `GET_LOCK` session-scoped: Django persistent connection OK. Nhưng cursor phải release trong `finally`, và phải ở **ngoài** `transaction.atomic()` (nếu atomic rollback vì exception, connection có thể reset và drop lock implicitly — OK nhưng code rõ ràng hơn khi lock bao quanh atomic).

```python
from django.db import connection, transaction
from rest_framework import serializers

def create(self, validated_data):
    slot_id = validated_data['slot_id']
    lock_name = f"slot_booking_{slot_id}"

    with connection.cursor() as cursor:
        # Acquire advisory lock với timeout 5s
        cursor.execute("SELECT GET_LOCK(%s, 5)", [lock_name])
        got_lock = cursor.fetchone()[0]
        if got_lock != 1:
            raise serializers.ValidationError(
                "Hệ thống đang bận, vui lòng thử lại sau"
            )

        try:
            with transaction.atomic():
                conflict = Booking.objects.filter(
                    slot_id=slot_id,
                    start_time__lt=validated_data['end_time'],
                    end_time__gt=validated_data['start_time'],
                    check_in_status__in=['not_checked_in', 'checked_in']
                ).exists()
                if conflict:
                    raise serializers.ValidationError(
                        "Slot đã được đặt trong khoảng thời gian này"
                    )

                # Pre-fetch slot metadata + write denormalized data
                # (xem S2-IMP-1 Bước 4 cho `fetch_slot_info`)
                slot_info = fetch_slot_info(slot_id)
                validated_data.update({
                    'parking_lot_name': slot_info['parking_lot_name'],
                    'zone_name': slot_info['zone_name'],
                    'slot_code': slot_info['slot_code'],
                    'floor_level': slot_info['floor_level'],
                })

                booking = Booking.objects.create(**validated_data)
        finally:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [lock_name])

    return booking
```

### Option B — Redis distributed lock với Lua CAS script (safe variant)

⚠️ **Không dùng `redis_client.delete(key)` naive** — nếu request chậm hơn TTL, lock expire, request khác grab lock, request đầu finally delete lock của request sau → race.

```python
import redis
import uuid
from contextlib import contextmanager

redis_client = redis.Redis.from_url(settings.REDIS_URL + "/7")  # DB 7 reserved for locks

# Lua script: chỉ delete nếu value khớp (CAS)
_RELEASE_LOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""
_release_lock = redis_client.register_script(_RELEASE_LOCK_SCRIPT)

@contextmanager
def slot_lock(slot_id: str, timeout: int = 5):
    key = f"lock:slot:{slot_id}"
    token = str(uuid.uuid4())  # unique per holder
    acquired = redis_client.set(key, token, nx=True, ex=timeout)
    if not acquired:
        raise serializers.ValidationError(
            "Slot đang được đặt bởi user khác, vui lòng thử lại"
        )
    try:
        yield
    finally:
        # Chỉ delete nếu token khớp — không xóa lock của request khác
        _release_lock(keys=[key], args=[token])

def create(self, validated_data):
    with slot_lock(validated_data['slot_id']):
        with transaction.atomic():
            # ... check conflict + create với denormalized fields ...
```

**Trade-off:**
- **Option A (MySQL GET_LOCK)**: đơn giản, không thêm infra, đủ safe cho single-DB deployment.
- **Option B (Redis Lua CAS)**: cần thêm Redis DB 7 reserved cho lock, nhưng scale horizontal tốt hơn (nhiều booking-service instance share lock).
- **Đề xuất:** Option A cho Sprint 1 (nhanh), Option B khi scale sau.

### Option C — Unique constraint (chính xác nhất nhưng phức tạp)
MySQL 8 không hỗ trợ exclusion constraint natively. Phải dùng trigger hoặc partial unique index — không khuyến khích.

**Test race condition:**
```python
# tests/test_booking_race.py
import threading
def test_no_double_booking(db):
    results = []
    def book():
        try:
            s = CreateBookingSerializer(data={...})
            s.is_valid(raise_exception=True)
            results.append(s.save())
        except ValidationError:
            results.append(None)

    threads = [threading.Thread(target=book) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    successes = [r for r in results if r is not None]
    assert len(successes) == 1  # chỉ 1 thành công
```

**Verify:**
```bash
pytest backend-microservices/booking-service/tests/test_booking_race.py -v
```

---

## S1-CRIT-6 · Production cookie hardening

**File:** `backend-microservices/docker-compose.prod.yml:101-113`
**Thời gian:** 20 phút.

**Fix:**
```yaml
# docker-compose.prod.yml, gateway-service-go section
gateway-service-go:
  environment:
    - ENV=production              # ❌ was development
    - SESSION_COOKIE_DOMAIN=.ghepdoicaulong.shop  # cross-subdomain
    - SESSION_COOKIE_SECURE=true  # ❌ was false
    - SESSION_COOKIE_SAMESITE=None  # ❌ was Lax — cần None để cross-subdomain
    - SESSION_COOKIE_HTTPONLY=true
```

**Verify production deployment:**
```bash
# Từ máy ngoài, gọi qua Cloudflare
curl -i -c cookies.txt https://api.ghepdoicaulong.shop/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test","password":"test"}'

cat cookies.txt
# session_id cookie phải có: Secure, HttpOnly, SameSite=None, Domain=.ghepdoicaulong.shop
```

---

## S1-CRIT-7 · CORS env-driven cho `ai-service-fastapi`

**File:** `backend-microservices/ai-service-fastapi/app/main.py:43-53` + `app/config.py`
**Thời gian:** 1 giờ.

**Fix:**

### 1. `app/config.py`
```python
class Settings(BaseSettings):
    ...
    CORS_ALLOWED_ORIGINS: str = ""  # comma-separated

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.CORS_ALLOWED_ORIGINS:
            # Dev fallback only
            return ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
```

### 2. `app/main.py:43-53`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. `docker-compose.prod.yml` — override cho ai-service
```yaml
ai-service-fastapi:
  environment:
    - CORS_ALLOWED_ORIGINS=https://app.ghepdoicaulong.shop,https://parksmart.ghepdoicaulong.shop
```

### 4. Verify
```bash
curl -i -X OPTIONS http://localhost:8009/ai/cameras/stream \
  -H "Origin: https://app.ghepdoicaulong.shop" \
  -H "Access-Control-Request-Method: GET"
# Expected header: Access-Control-Allow-Origin: https://app.ghepdoicaulong.shop
```

---

## S1-CRIT-8 · FE `webLogger` dev-only + redaction

**Files:**
- `spotlove-ai/src/lib/webLogger.ts`
- `spotlove-ai/src/services/api/axios.client.ts:61-94`

**Thời gian:** 2 giờ.

**Fix:**

### 1. `src/lib/webLogger.ts` — full rewrite top of file
```ts
const IS_DEV = import.meta.env.DEV;

const REDACT_KEYS = new Set([
  "password",
  "password_confirm",
  "currentPassword",
  "newPassword",
  "token",
  "refreshToken",
  "refresh_token",
  "access_token",
  "authorization",
  "cookie",
  "user_info",
  "session_id",
  "sessionId",
  "csrfToken",
  "X-Gateway-Secret",
  "qr_data",
]);

function redact(obj: unknown): unknown {
  if (!IS_DEV) return "[PROD-REDACTED]";
  if (obj == null || typeof obj !== "object") return obj;
  if (Array.isArray(obj)) return obj.map(redact);
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    if (REDACT_KEYS.has(k)) {
      out[k] = "[REDACTED]";
    } else {
      out[k] = redact(v);
    }
  }
  return out;
}

// Skip logging entirely in prod
function append(entry: LogEntry): void {
  if (!IS_DEV) return;
  const safe = { ...entry, data: redact(entry.data) };
  // ... existing sessionStorage logic
}

export const webLogger = {
  apiReq(method: string, url: string, body?: unknown) {
    if (!IS_DEV) return;
    // Don't log auth endpoints at all
    if (url.includes("/auth/login") || url.includes("/auth/register")) {
      append({ method, url, data: "[AUTH-REDACTED]" });
      return;
    }
    append({ method, url, data: redact(body) });
  },

  apiRes(method: string, url: string, status: number, body?: unknown) {
    if (!IS_DEV) return;
    if (url.includes("/auth/")) {
      append({ method, url, status, data: "[AUTH-REDACTED]" });
      return;
    }
    append({ method, url, status, data: redact(body) });
  },

  download() {
    if (!IS_DEV) {
      console.warn("[webLogger] download disabled in production");
      return;
    }
    // ... existing download logic
  },
};
```

### 2. `src/services/api/axios.client.ts:61-94`
Thêm guard `if (import.meta.env.DEV)` trước mỗi `webLogger.apiReq / apiRes`, hoặc dựa vào logger tự guard như trên.

### 3. Test
```ts
// src/test/webLogger-redact.test.ts
import { webLogger } from "@/lib/webLogger";

test("password is redacted in dev", () => {
  webLogger.apiReq("POST", "/api/auth/login", { email: "a@b.c", password: "secret123" });
  const logs = JSON.parse(sessionStorage.getItem("webLogger") || "[]");
  expect(JSON.stringify(logs)).not.toContain("secret123");
});
```

### 4. Verify prod build
```bash
cd spotlove-ai && npm run build
grep -r "secret\|password" dist/ # tìm kỹ trong chunks
# bundle không được chứa redacted PII từ sessionStorage
```

---

## S1-CRIT-9 · Bật TypeScript strict (PHASE-IN across 3 sprint)

**File:** `spotlove-ai/tsconfig.app.json`

⚠️ **Reality check:** Repo có **161 .ts/.tsx files**, strict:false → true sẽ sinh **hàng trăm đến 1000+ errors**. Không thể làm trong 0.5-1 ngày như plan v1. Phase-in qua 3 sprint:

### Sprint 1 (0.5-1 ngày) — chỉ bật `noImplicitAny`

```json
// spotlove-ai/tsconfig.app.json
{
  "compilerOptions": {
    "strict": false,
    "noImplicitAny": true,           // ← bật riêng cái này
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "alwaysStrict": true
  }
}
```

**Lý do:** `noImplicitAny` catch phần lớn bugs dễ nhất (missing type trên params, destructure, event handlers) với cost thấp nhất. Expect ~20-50 errors.

Thêm `npm run typecheck` + CI job ngay Sprint 1:
```json
// package.json
"scripts": {
  "typecheck": "tsc --noEmit"
}
```

`.github/workflows/ci.yml`:
```yaml
- run: npm ci
- run: npm run typecheck  # fail nếu có error
- run: npm run lint
- run: npm run test
- run: npm run build
```

### Sprint 2 (2-3 ngày) — bật `strictNullChecks`

Làm **sau** S2-IMP-9 (layering refactor) — vì refactor sẽ chạm nhiều page, bật strictNullChecks trước sẽ double-work.

```json
{
  "compilerOptions": {
    "strict": false,
    "noImplicitAny": true,
    "strictNullChecks": true,       // ← thêm
    "noImplicitReturns": true,
    ...
  }
}
```

Expect ~200-500 errors. Fix theo batch:
- **Group 1 (easy, ~50%):** Thêm `| null | undefined` cho Redux state, axios response types.
- **Group 2 (medium, ~30%):** Thay `as unknown as X` bằng Zod parse (đã có sẵn từ S2-IMP-9 Bonus).
- **Group 3 (hard, ~20%):** Components dùng `any` event handler → `React.ChangeEvent<HTMLInputElement>`, v.v.
- Chỗ nào chưa fix được → `// @ts-expect-error — TODO(S3-CRIT-9): <reason>`, **KHÔNG dùng** `@ts-ignore` (không track được).

### Sprint 3 (1-2 ngày) — bật full `strict`

```json
{
  "compilerOptions": {
    "strict": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    ...
  }
}
```

Clean up mọi `@ts-expect-error` còn lại.

### Verify mỗi sprint
```bash
cd spotlove-ai && npm run typecheck
# Sprint 1 gate: 0 errors với noImplicitAny
# Sprint 2 gate: 0 errors với noImplicitAny + strictNullChecks
# Sprint 3 gate: 0 errors với full strict + 0 @ts-expect-error
```

---

## S1-CRIT-10 · Gateway healthcheck + `cookies_test.txt` gitignore

**Files:**
- `backend-microservices/docker-compose.yml` (gateway section, dòng ~407-436)
- `.gitignore`
- `backend-microservices/cookies_test.txt` (xoá)

**Thời gian:** 30 phút.

**Fix 1 — gateway healthcheck:**
```yaml
gateway-service-go:
  ...
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:8000/health/"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 20s
```

**Fix 2 — `.gitignore`:**
```
# ... existing ...
cookies.txt
cookies_test.txt
cookies*.txt  # pattern wider
.env.test
spotlove-ai/.env.test
```

**Fix 3 — Xoá file:**
```bash
rm backend-microservices/cookies_test.txt
# Confirm không còn:
find . -name "cookies*.txt" -not -path "*/node_modules/*"
```

**Fix 4 — Revoke session_id nếu còn valid:**
Session đã leak: `1a5caaf9-e562-4365-baf6-67e3f46adb89`. Xoá khỏi Redis:
```bash
docker compose exec redis redis-cli -n 1 DEL "session:1a5caaf9-e562-4365-baf6-67e3f46adb89"
```

---

## S1-CRIT-11 · Fix Dockerfile security + non-root user

**Files:** toàn bộ `backend-microservices/*/Dockerfile` (8 file)
**Thời gian:** 2 giờ.

**Pattern Dockerfile chuẩn (apply cho mỗi Python service):**

```Dockerfile
FROM python:3.11-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root user với UID cụ thể (match với host uid để volume mount work)
ARG APP_UID=1000
RUN useradd --uid ${APP_UID} --create-home --shell /bin/bash app

WORKDIR /app

# Install deps (as root, trong pip cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app + chown
COPY --chown=app:app . .

# Switch to non-root
USER app

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --spider -q http://localhost:8000/health/ || exit 1

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

**⚠️ Shared volume uid mismatch — quan trọng:**

`docker-compose.yml` mount `./shared:/app/shared` cho mọi Python service. Nếu host uid khác container uid 1000 → `app` user không có permission đọc → ImportError runtime.

**Giải pháp (chọn 1):**

**Option 1: Entrypoint chown (an toàn nhất)**
```Dockerfile
USER root
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```
`docker-entrypoint.sh`:
```bash
#!/bin/bash
set -e
# Fix ownership of mounted volumes
chown -R app:app /app/shared || true
# Drop to non-root user
exec gosu app "$@"
```
Cần cài `gosu` trong base image: `apt-get install -y gosu`.

**Option 2: Build-time copy thay vì mount (đơn giản nhất, đề xuất)**

Thay vì mount `./shared:/app/shared`, copy `shared/` vào image build-time:

```Dockerfile
# Trong mỗi service Dockerfile
COPY --from=shared-base /shared /app/shared
```

Hoặc simpler — move `shared/` vào folder build context:
```yaml
# docker-compose.yml
parking-service:
  build:
    context: .  # ← repo root thay vì ./parking-service
    dockerfile: ./parking-service/Dockerfile
  # XOÁ: volumes: - ./shared:/app/shared
```

`parking-service/Dockerfile`:
```Dockerfile
COPY shared/ /app/shared/
COPY parking-service/ /app/
```

Lợi ích: container hoàn toàn self-contained, không phụ thuộc host filesystem permission, image có thể ship sang prod cluster mà không cần mount.

**Option 3: User `root` + runtime check (tạm thời, KHÔNG dùng prod)**

Nếu thời gian eo hẹp → giữ `USER root` cho Sprint 1, đẩy non-root sang Sprint 3 sau khi refactor build context.

**Đề xuất:** Option 2 cho Sprint 1 — thay mount bằng copy build-time. Kết hợp với multi-stage để cache dep tốt hơn.

**Đặc biệt: `ai-service-fastapi/Dockerfile:11,14` — xoá TLS bypass:**
```Dockerfile
# ❌ XOÁ 2 dòng này
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org ...
RUN PYTHONHTTPSVERIFY=0 python -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import easyocr; easyocr.Reader(['en'])"

# ✅ THAY BẰNG
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import easyocr; easyocr.Reader(['en'], model_storage_directory='/app/ml/models')"
```

Nếu mạng build thực sự có vấn đề với CA → fix CA trên base image, không bypass TLS.

**Verify:**
```bash
cd backend-microservices && docker compose up -d --build
docker compose exec auth-service whoami  # expected: app
docker compose ps  # tất cả healthy
```

---

## S1-CRIT-12 · `uvicorn` multi-worker cho `ai-service-fastapi`

**File:** `backend-microservices/ai-service-fastapi/Dockerfile:26`
**Thời gian:** 1 giờ + load test.

**Fix:**
```Dockerfile
# ❌ SAI — 1 worker block event loop khi YOLO inference
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009"]

# ✅ ĐÚNG
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009", "--workers", "2"]
```

**Cảnh báo:** Mỗi worker pre-warm YOLO + EasyOCR model → RAM tăng 2×. Verify memory trước khi tăng thêm:
```bash
docker compose up -d ai-service-fastapi
docker stats ai-service-fastapi --no-stream
# Nếu RAM < 60% cap, OK; nếu > 80%, dừng ở 2 workers hoặc upgrade host
```

**Load test:**
```bash
# Simulate 5 concurrent scan-plate requests
for i in {1..5}; do
  curl -X POST http://localhost:8009/ai/parking/scan-plate/ \
    -F "image=@test_plate.jpg" \
    -H "X-Gateway-Secret: $GATEWAY_SECRET" &
done
wait
# p99 phải < 10s
```

**Nếu cần scale thêm:** Chuyển AI inference sang model server riêng (Triton hoặc TorchServe) — ra khỏi scope Sprint 1.

---

## S1-IMP-0 · Test verification toàn bộ Sprint 1

Sau khi hoàn tất S1-CRIT-1 → S1-CRIT-12, chạy toàn bộ verification trước khi mở Sprint 2:

### Backend smoke
```bash
cd backend-microservices
docker compose down -v && docker compose up -d --build

# Đợi 60s cho services boot
sleep 60

# Health check tất cả
for svc in auth-service:8001 parking-service:8003 booking-service:8002 ai-service-fastapi:8009; do
  curl -f http://localhost:${svc##*:}/health/ || echo "FAIL: $svc"
done

# Gateway health
curl -f http://localhost:8000/health/ || echo "FAIL: gateway"
curl -f http://localhost:8000/health/services/ | jq
```

### E2E
```bash
cd backend-microservices
python seed_e2e_data.py
python seed_unity_test_data.py

cd ../spotlove-ai
npm ci
cp .env.test.example .env.test
# Set E2E_GATEWAY_SECRET trong .env.test
npm run e2e
# Expected: 5/5 PASS (booking-full-flow, checkin-flow x2, global-setup x2)
```

### Unit tests
```bash
cd backend-microservices
for svc in auth-service parking-service booking-service vehicle-service; do
  (cd $svc && pytest --tb=short)
done
for svc in ai-service-fastapi chatbot-service-fastapi notification-service-fastapi payment-service-fastapi; do
  (cd $svc && pytest --tb=short)
done
cd gateway-service-go && go test ./...
cd ../realtime-service-go && go test ./...

cd ../../spotlove-ai
npm run typecheck
npm run lint
npm run test
npm run build
```

### Security grep
```bash
# Không còn hardcoded secrets
grep -rn "gateway-internal-secret-key\|gw-prod-" \
  backend-microservices/ spotlove-ai/src/ spotlove-ai/e2e/ \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=__pycache__
# Expected: chỉ các match ở .env.example placeholder

# Không còn cookies_test
find . -name "cookies*.txt" -not -path "*/node_modules/*"
# Expected: rỗng
```

**Gate thoát Sprint 1:** Tất cả 4 khối trên PASS, không regression test.

**Commit strategy Sprint 1:**
- Mỗi CRIT task = 1 commit atomic
- Format: `fix(scope): description  Refs: S1-CRIT-N`
- Ví dụ: `fix(parking): remove duplicate block in views.py  Refs: S1-CRIT-1`
- `fix(auth): disable Django admin + remove middleware bypass  Refs: S1-CRIT-3`

---

# SPRINT 2 — SCALE + MAINTAIN

**Mục tiêu:** Loại bỏ scaling cliffs, refactor god classes, gỡ dead deps, bundle cut.

**Thứ tự:** Priority cao (IMP-1, IMP-2, IMP-3) → god class refactor → FE bundle → Unity refactor.

---

## S2-IMP-1 · Loại N+1 HTTP trong `BookingSerializer`

**File:** `backend-microservices/booking-service/bookings/serializers.py:367-512`
**Thời gian:** 2.5 ngày (tăng 0.5 ngày cho contract audit + rollback-safe migration).
**Impact:** Biggest perf win. Biến hệ thống từ "chết ở 20 req/s" → "handle hàng nghìn req/s".

**Gốc vấn đề:**
5 `SerializerMethodField`: `get_vehicle`, `get_parking_lot`, `get_floor`, `get_zone`, `get_car_slot`. Mỗi method gọi `_fetch_*_info()` → HTTP cross-service. List 100 booking = **500 HTTP calls**, best-case ~25s, worst-case 2500s.

Ngoài ra 6 chỗ có `Booking.objects.filter(id=obj.id).update(...)` trong `get_*` method → side-effect lúc serialize, race.

**Booking model đã có các denormalized fields sau** (verified bằng Read `bookings/models.py:71-117` ngày 2026-04-15):

| Field | Type | Có sẵn? |
|---|---|---|
| `user_id`, `user_email` | UUID, Email | ✅ |
| `vehicle_id`, `vehicle_license_plate`, `vehicle_type` | UUID, Char, Char | ✅ |
| `parking_lot_id`, `parking_lot_name` | UUID, Char(255) | ✅ |
| `floor_id`, **`floor_level`** (không phải `floor_name`) | UUID nullable, Int nullable | ✅ |
| `zone_id`, `zone_name` | UUID, Char(100) | ✅ |
| `slot_id`, `slot_code` | UUID nullable, Char(20) | ✅ |
| `vehicle_brand`, `vehicle_model` | — | ❌ **KHÔNG CÓ** |
| `floor_name` (string) | — | ❌ **KHÔNG CÓ** (chỉ có `floor_level` int) |

**Pre-check gitnexus + FE contract audit (Bước 0 BẮT BUỘC):**
```
mcp__gitnexus__context({name: "BookingSerializer", repo: "Project_Main"})
mcp__gitnexus__api_impact({route: "/bookings/", repo: "Project_Main"})
```

---

### Bước 0 — BE/FE contract audit (0.5 ngày)

Xác định FE hiện dùng field nào từ response `Booking` — nếu bỏ nested fetch sẽ mất gì.

```bash
cd spotlove-ai
# Grep mọi access path
grep -rn "booking\.\(vehicle\|parking_lot\|floor\|zone\|car_slot\)" src/ \
  --include="*.ts" --include="*.tsx" | sort > /tmp/fe-booking-usage.txt

# Xem unique field access
grep -rn "booking\.\(vehicle\|parking_lot\|floor\|zone\|car_slot\)\.[a-z_]*" src/ \
  -o | sort -u
```

**Checklist FE consumer — phải đảm bảo mọi access path dưới đây resolve được từ denormalized columns:**

| FE access | Denormalized resolution | Action |
|---|---|---|
| `booking.vehicle.license_plate` | `obj.vehicle_license_plate` | OK |
| `booking.vehicle.type` | `obj.vehicle_type` | OK |
| `booking.vehicle.brand` / `.model` | **KHÔNG CÓ** | Option A: thêm field + migration; Option B: FE không dùng → xóa |
| `booking.vehicle.owner_name` / `.owner_email` | `obj.user_email` có; owner_name không có | Nếu FE cần → thêm `user_name` field |
| `booking.parking_lot.name` | `obj.parking_lot_name` | OK |
| `booking.parking_lot.address` / `.latitude` / `.longitude` | **KHÔNG CÓ** | Thêm migration nếu FE cần |
| `booking.floor.name` | **KHÔNG CÓ** (có `floor_level: Int`) | Nếu FE expect string → map ở serializer `f"Tầng {obj.floor_level}"` |
| `booking.floor.level` | `obj.floor_level` | OK |
| `booking.zone.name` | `obj.zone_name` | OK |
| `booking.car_slot.code` | `obj.slot_code` | OK |

**Nếu phát hiện FE dùng field thiếu:**
1. Thêm field vào model + migration (xem Bước 1)
2. Hoặc update FE để dùng field khác + commit song song (cân nhắc backward compat)

---

### Bước 1 — Migration bổ sung field thiếu (NẾU cần)

**Quan trọng:** Migration phải **rollback-safe** — forward adds nullable fields, backward no-op (không drop vì đã có data).

```python
# bookings/migrations/0XXX_add_missing_denormalized.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('bookings', '0XXX_previous')]

    operations = [
        # Chỉ add những field FE THẬT SỰ cần (confirmed từ Bước 0)
        migrations.AddField(
            'booking', 'user_name',
            models.CharField(max_length=100, blank=True, default='')
        ),
        # vehicle_brand, vehicle_model — chỉ add nếu FE cần, có default '' để nullable-safe
        migrations.AddField(
            'booking', 'vehicle_brand',
            models.CharField(max_length=50, blank=True, default='')
        ),
        migrations.AddField(
            'booking', 'vehicle_model',
            models.CharField(max_length=50, blank=True, default='')
        ),
    ]
```

Rollback: `python manage.py migrate bookings <previous>` — Django tự generate `RemoveField` reverse. Tuy nhiên nếu đã backfill data → rollback sẽ mất. Ghi lại trong PR description: "Migration này forward-only; rollback sẽ mất denormalized data."

---

### Bước 2 — Backfill management command

Chỉ cần nếu Bước 1 thêm field mới. `bookings/management/commands/backfill_denormalized.py`:

```python
from django.core.management.base import BaseCommand
from bookings.models import Booking
from bookings.services import fetch_vehicle_info, fetch_user_info

class Command(BaseCommand):
    help = "Backfill denormalized fields for legacy bookings"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=100)

    def handle(self, *args, **opts):
        qs = Booking.objects.filter(vehicle_brand='').only('id', 'vehicle_id', 'user_id')
        total = qs.count()
        self.stdout.write(f"Backfilling {total} bookings")

        for i, booking in enumerate(qs.iterator(chunk_size=opts['batch_size'])):
            try:
                vehicle = fetch_vehicle_info(booking.vehicle_id)
                user = fetch_user_info(booking.user_id)

                if not opts['dry_run']:
                    Booking.objects.filter(id=booking.id).update(
                        vehicle_brand=vehicle.get('brand', ''),
                        vehicle_model=vehicle.get('model', ''),
                        user_name=user.get('name', ''),
                    )

                if i % 100 == 0:
                    self.stdout.write(f"  {i}/{total}")
            except Exception as e:
                self.stderr.write(f"  failed {booking.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Done: {total}"))
```

Chạy:
```bash
docker compose exec booking-service python manage.py backfill_denormalized --dry-run
# Review output
docker compose exec booking-service python manage.py backfill_denormalized
```

---

### Bước 3 — Rewrite `BookingSerializer`

```python
class BookingSerializer(serializers.ModelSerializer):
    # ❌ XOÁ tất cả SerializerMethodField gọi _fetch_*_info
    # ❌ XOÁ mọi Booking.objects.filter(id=obj.id).update(...)
    # ✅ Map từ field denormalized, KHÔNG HTTP call

    vehicle = serializers.SerializerMethodField()
    parking_lot = serializers.SerializerMethodField()
    floor = serializers.SerializerMethodField()
    zone = serializers.SerializerMethodField()
    car_slot = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'user_id', 'user_email',
            'vehicle', 'parking_lot', 'floor', 'zone', 'car_slot',
            'package_type', 'start_time', 'end_time',
            'payment_method', 'payment_status', 'price',
            'check_in_status', 'checked_in_at', 'checked_out_at',
            'qr_code_data',
            'hourly_start', 'hourly_end', 'extended_until', 'late_fee_applied',
            'created_at', 'updated_at',
        ]

    def get_vehicle(self, obj):
        return {
            "id": str(obj.vehicle_id),
            "license_plate": obj.vehicle_license_plate,
            "type": obj.vehicle_type,
            # brand/model chỉ có sau khi Bước 1 + backfill
            "brand": getattr(obj, 'vehicle_brand', ''),
            "model": getattr(obj, 'vehicle_model', ''),
        }

    def get_parking_lot(self, obj):
        return {
            "id": str(obj.parking_lot_id),
            "name": obj.parking_lot_name,
        }

    def get_floor(self, obj):
        # Model chỉ có floor_level (int), FE expect string → map ở đây
        if obj.floor_id is None:
            return None
        return {
            "id": str(obj.floor_id),
            "level": obj.floor_level,
            "name": f"Tầng {obj.floor_level}" if obj.floor_level is not None else None,
        }

    def get_zone(self, obj):
        return {
            "id": str(obj.zone_id),
            "name": obj.zone_name,
        }

    def get_car_slot(self, obj):
        if obj.slot_id is None:
            return None
        return {
            "id": str(obj.slot_id),
            "code": obj.slot_code,
        }
```

**KHÔNG còn HTTP call, KHÔNG còn `Booking.objects.update()` trong serialize path.**

---

### Bước 4 — Cập nhật `CreateBookingSerializer` để write denormalized lúc tạo

Đồng bộ với S1-CRIT-5 advisory lock:

```python
def create(self, validated_data):
    slot_id = validated_data['slot_id']

    # Pre-fetch TRƯỚC khi acquire lock để giảm lock hold time
    slot_info = fetch_slot_info(slot_id)  # parking-service call
    vehicle_info = fetch_vehicle_info(validated_data['vehicle_id'])  # vehicle-service
    user_info = fetch_user_info(validated_data['user_id'])  # auth-service

    validated_data.update({
        'parking_lot_id': slot_info['parking_lot_id'],
        'parking_lot_name': slot_info['parking_lot_name'],
        'floor_id': slot_info.get('floor_id'),
        'floor_level': slot_info.get('floor_level'),
        'zone_id': slot_info['zone_id'],
        'zone_name': slot_info['zone_name'],
        'slot_code': slot_info['slot_code'],
        'vehicle_license_plate': vehicle_info['license_plate'],
        'vehicle_type': vehicle_info['type'],
        'vehicle_brand': vehicle_info.get('brand', ''),
        'vehicle_model': vehicle_info.get('model', ''),
        'user_email': user_info['email'],
        'user_name': user_info.get('name', ''),
    })

    # Lock sau khi đã có đầy đủ data → lock hold time ngắn
    with slot_lock(slot_id):  # hoặc GET_LOCK per S1-CRIT-5 Option A
        with transaction.atomic():
            # Chỉ check conflict + insert, không còn HTTP call
            conflict = Booking.objects.filter(
                slot_id=slot_id,
                start_time__lt=validated_data['end_time'],
                end_time__gt=validated_data['start_time'],
                check_in_status__in=['not_checked_in', 'checked_in']
            ).exists()
            if conflict:
                raise serializers.ValidationError("Slot đã được đặt")
            booking = Booking.objects.create(**validated_data)

    return booking
```

---

### Bước 5 — Load test
```bash
# Seed 100 booking
for i in {1..100}; do
  curl -X POST http://localhost:8002/bookings/ -H "..." -d '{...}'
done

# Time list endpoint
time curl http://localhost:8002/bookings/?limit=100 -H "..."
# Before: 25-2500s
# After: < 200ms
```

**Verify gitnexus sau khi fix:**
```
mcp__gitnexus__detect_changes({scope: "staged", repo: "Project_Main"})
```
Confirm scope chỉ touch `booking-service/bookings/`.

---

## S2-IMP-2 · Event bus RabbitMQ cho broadcast realtime + slot sync

**Files:**
- `backend-microservices/booking-service/bookings/views.py:33-48, 153-169, 200-216`
- `backend-microservices/booking-service/bookings/serializers.py:313-322` (slot PATCH)

**Thời gian:** 3 ngày.
**Impact:** Checkin latency độc lập với downstream; system availability tăng.

**Pattern Outbox:**

### Bước 1 — Outbox table (với `event_id` UUID làm dedup key)
```python
# bookings/models.py
import uuid

class OutboxEvent(models.Model):
    """Transactional outbox — events to publish to RabbitMQ.

    event_id là UUID unique truyền xuống consumer để dedup (RabbitMQ at-least-once).
    """
    id = models.AutoField(primary_key=True)
    event_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)  # ← dedup key
    event_type = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    published_at = models.DateTimeField(null=True, db_index=True)
    error_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True)
    dead_lettered_at = models.DateTimeField(null=True, db_index=True)  # ← DLQ marker

    class Meta:
        indexes = [
            models.Index(fields=['published_at', 'dead_lettered_at', 'created_at']),
        ]
```

**Consumer-side dedup table** (tạo trong mỗi service consume events — `parking-service`, `realtime-service-go`):

```python
# parking-service/infrastructure/models.py
class ProcessedEvent(models.Model):
    """Track events đã consume để dedup khi RabbitMQ redeliver."""
    event_id = models.UUIDField(primary_key=True)
    event_type = models.CharField(max_length=64)
    processed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'processed_events'
```

Go equivalent (realtime-service-go):
```go
// internal/dedup/store.go
type DedupStore struct {
    redis *redis.Client
}

func (d *DedupStore) IsProcessed(eventID string) (bool, error) {
    key := "processed:" + eventID
    // SET NX with 7-day TTL
    ok, err := d.redis.SetNX(ctx, key, "1", 7*24*time.Hour).Result()
    return !ok, err  // already existed = already processed
}
```

Migration:
```bash
docker compose exec booking-service python manage.py makemigrations
docker compose exec booking-service python manage.py migrate
```

### Bước 2 — Publish event trong transaction (thay vì HTTP inline)
```python
# views.py::checkin (was line 153-169)
@action(detail=True, methods=['post'])
def checkin(self, request, pk=None):
    booking = self.get_object()

    with transaction.atomic():
        booking.status = 'active'
        booking.actual_start = timezone.now()
        booking.save()

        # Outbox event thay vì HTTP call trực tiếp
        # event_id auto-generated UUID cho dedup
        OutboxEvent.objects.create(
            event_type='booking.checked_in',
            payload={
                'event_id': None,  # filled below via refresh_from_db or keep None here
                'booking_id': str(booking.id),
                'slot_id': str(booking.slot_id),
                'user_id': str(booking.user_id),
                'timestamp': booking.actual_start.isoformat(),
            }
        )
    # atomic() commit xong → worker sẽ publish

    return Response({'status': 'checked_in'})
```

### Bước 3 — Celery task poll outbox (với DLQ threshold)
```python
# bookings/tasks.py
from celery import shared_task
import pika
import json
from django.utils import timezone
from django.db.models import F

DLQ_THRESHOLD = 5  # sau 5 failed attempts → move to DLQ + alert

# Module-level persistent connection (tránh reconnect mỗi tick)
_amqp_connection = None
_amqp_channel = None

def get_amqp_channel():
    global _amqp_connection, _amqp_channel
    if _amqp_connection is None or _amqp_connection.is_closed:
        _amqp_connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
        _amqp_channel = _amqp_connection.channel()
        _amqp_channel.exchange_declare('parksmart.events', exchange_type='topic', durable=True)
        _amqp_channel.exchange_declare('parksmart.events.dlq', exchange_type='topic', durable=True)
    return _amqp_channel

@shared_task
def publish_outbox_events():
    """Chạy mỗi 2s qua celery beat."""
    events = OutboxEvent.objects.filter(
        published_at__isnull=True,
        dead_lettered_at__isnull=True,
        error_count__lt=DLQ_THRESHOLD,
    ).order_by('created_at')[:100]

    if not events.exists():
        return

    channel = get_amqp_channel()

    for event in events:
        try:
            # Include event_id trong payload cho consumer dedup
            payload = {**event.payload, 'event_id': str(event.event_id)}
            channel.basic_publish(
                exchange='parksmart.events',
                routing_key=event.event_type,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistent
                    message_id=str(event.event_id),  # AMQP-level dedup hint
                ),
            )
            event.published_at = timezone.now()
            event.save(update_fields=['published_at'])
        except Exception as exc:
            OutboxEvent.objects.filter(id=event.id).update(
                error_count=F('error_count') + 1,
                last_error=str(exc)[:500],
            )
            # Reset connection nếu broker drop
            global _amqp_connection
            _amqp_connection = None

@shared_task
def process_dead_letter_events():
    """Chạy mỗi 5 phút — move events đã fail quá threshold sang DLQ."""
    failed = OutboxEvent.objects.filter(
        published_at__isnull=True,
        dead_lettered_at__isnull=True,
        error_count__gte=DLQ_THRESHOLD,
    )

    channel = get_amqp_channel()

    for event in failed:
        payload = {**event.payload, 'event_id': str(event.event_id), 'dlq_reason': event.last_error}
        channel.basic_publish(
            exchange='parksmart.events.dlq',
            routing_key=event.event_type,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        event.dead_lettered_at = timezone.now()
        event.save(update_fields=['dead_lettered_at'])

    if failed.exists():
        # TODO: tích hợp alerting (Slack, Sentry) — trigger khi có DLQ entry
        logger.error(f"Moved {failed.count()} events to DLQ")
```

Celery beat schedule:
```python
# booking_service/celery.py
app.conf.beat_schedule = {
    'publish-outbox-events': {
        'task': 'bookings.tasks.publish_outbox_events',
        'schedule': 2.0,  # 2s thay vì 1s — persistent connection nên không overhead lớn
    },
    'process-dead-letter-events': {
        'task': 'bookings.tasks.process_dead_letter_events',
        'schedule': 300.0,  # 5 phút
    },
}
```

### Bước 4 — Consumer ở `realtime-service-go` (với dedup)

Thêm dep: `go get github.com/rabbitmq/amqp091-go`

`realtime-service-go/internal/consumer/booking_events.go`:
```go
package consumer

import (
    "context"
    "encoding/json"
    "log"

    amqp "github.com/rabbitmq/amqp091-go"
)

func ConsumeBookingEvents(ch *amqp.Channel, dedup *DedupStore, hub *WSHub) error {
    if err := ch.ExchangeDeclare("parksmart.events", "topic", true, false, false, false, nil); err != nil {
        return err
    }
    q, err := ch.QueueDeclare("realtime.booking", true, false, false, false, nil)
    if err != nil {
        return err
    }
    if err := ch.QueueBind(q.Name, "booking.*", "parksmart.events", false, nil); err != nil {
        return err
    }

    // Manual ack để có thể reject + redeliver nếu fail
    msgs, err := ch.Consume(q.Name, "", false, false, false, false, nil)
    if err != nil {
        return err
    }

    for msg := range msgs {
        var payload map[string]interface{}
        if err := json.Unmarshal(msg.Body, &payload); err != nil {
            msg.Nack(false, false)  // malformed — drop
            continue
        }

        eventID, ok := payload["event_id"].(string)
        if !ok || eventID == "" {
            log.Printf("event missing event_id, dropping: %s", msg.Body)
            msg.Nack(false, false)
            continue
        }

        // Dedup check
        alreadyProcessed, err := dedup.IsProcessed(eventID)
        if err != nil {
            log.Printf("dedup check failed: %v", err)
            msg.Nack(false, true)  // requeue
            continue
        }
        if alreadyProcessed {
            msg.Ack(false)  // skip, không broadcast 2 lần
            continue
        }

        if err := hub.Broadcast(payload); err != nil {
            log.Printf("broadcast failed: %v", err)
            msg.Nack(false, true)  // requeue
            continue
        }
        msg.Ack(false)
    }
    return nil
}
```

### Bước 5 — Consumer ở `parking-service` (Python with dedup table)
```python
# parking-service/infrastructure/consumers.py
import json
import pika
from django.db import transaction, IntegrityError
from .models import ProcessedEvent, CarSlot

def consume_booking_events():
    connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare('parksmart.events', exchange_type='topic', durable=True)
    result = channel.queue_declare('parking.booking_sync', durable=True)
    channel.queue_bind(result.method.queue, 'parksmart.events', routing_key='booking.*')

    def callback(ch, method, properties, body):
        try:
            payload = json.loads(body)
            event_id = payload.get('event_id')
            if not event_id:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Dedup check via unique constraint
            with transaction.atomic():
                try:
                    ProcessedEvent.objects.create(
                        event_id=event_id,
                        event_type=method.routing_key,
                    )
                except IntegrityError:
                    # Already processed
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                # Apply business logic
                if method.routing_key == 'booking.checked_in':
                    CarSlot.objects.filter(id=payload['slot_id']).update(status='occupied')
                elif method.routing_key == 'booking.checked_out':
                    CarSlot.objects.filter(id=payload['slot_id']).update(status='available')

            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.exception(f"consumer failed: {exc}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    channel.basic_consume(queue=result.method.queue, on_message_callback=callback, auto_ack=False)
    channel.start_consuming()
```

**DLQ alerting:** Sprint 3 add Prometheus metric `outbox_dead_lettered_total` + Grafana alert khi > 0.

### Bước 6 — Verify
```bash
# Restart stack
docker compose down && docker compose up -d --build

# Trigger checkin
curl -X POST http://localhost:8000/api/bookings/<id>/checkin/ -H "..."

# Verify latency không phụ thuộc downstream
# (Stop realtime-service)
docker compose stop realtime-service-go
# Checkin vẫn nhanh, event sẽ deliver khi realtime up lại
```

---

## S2-IMP-3 · Gateway proxy connection pooling

**File:** `backend-microservices/gateway-service-go/internal/handler/proxy.go:54-59`
**Thời gian:** 0.5 ngày.

**Gốc vấn đề:** `httputil.NewSingleHostReverseProxy(targetURL)` + `http.DefaultTransport.(*http.Transport).Clone()` allocate mới mỗi request → không tận dụng connection pool.

**Pre-check:** Đọc `gateway-service-go/internal/config/config.go` — Config struct hiện tại chỉ có field `AuthServiceURL`, `ParkingServiceURL`, v.v. **Không có** method `ServiceURLs()`. Phải tự thêm helper trước khi apply fix.

### Bước 1 — Thêm helper method `ServiceURLs()` vào config

`gateway-service-go/internal/config/config.go`:
```go
// ServiceURLs returns map of service name → upstream URL.
func (c *Config) ServiceURLs() map[string]string {
    return map[string]string{
        "auth":         c.AuthServiceURL,
        "parking":      c.ParkingServiceURL,
        "vehicle":      c.VehicleServiceURL,
        "booking":      c.BookingServiceURL,
        "notification": c.NotificationServiceURL,
        "realtime":     c.RealtimeServiceURL,
        "payment":      c.PaymentServiceURL,
        "chatbot":      c.ChatbotServiceURL,
        "ai":           c.AIServiceURL,
    }
}
```

### Bước 2 — Rewrite `ProxyHandler` với shared transport

```go
// internal/handler/proxy.go
package handler

import (
    "encoding/json"
    "log"
    "net"
    "net/http"
    "net/http/httputil"
    neturl "net/url"  // ← alias để tránh shadow với biến loop
    "sync"
    "time"

    "github.com/gin-gonic/gin"
    "gateway-service/internal/config"
)

type ProxyHandler struct {
    cfg     *config.Config
    proxies map[string]*httputil.ReverseProxy  // service name → proxy
    mu      sync.RWMutex
}

func NewProxyHandler(cfg *config.Config) *ProxyHandler {
    h := &ProxyHandler{
        cfg:     cfg,
        proxies: make(map[string]*httputil.ReverseProxy),
    }

    // Shared transport với connection pooling
    transport := &http.Transport{
        MaxIdleConns:        200,
        MaxIdleConnsPerHost: 100,
        IdleConnTimeout:     90 * time.Second,
        DialContext: (&net.Dialer{
            Timeout:   5 * time.Second,
            KeepAlive: 30 * time.Second,
        }).DialContext,
        ResponseHeaderTimeout: 30 * time.Second,
    }

    // Init một ReverseProxy mỗi service, reuse qua map
    for serviceName, rawURL := range cfg.ServiceURLs() {
        targetURL, err := neturl.Parse(rawURL)
        if err != nil {
            log.Fatalf("invalid URL for service %s: %v", serviceName, err)
        }
        proxy := httputil.NewSingleHostReverseProxy(targetURL)
        proxy.Transport = transport
        proxy.ErrorHandler = h.errorHandler(serviceName)
        h.proxies[serviceName] = proxy
    }

    return h
}

func (h *ProxyHandler) HandleProxy(c *gin.Context) {
    route := h.resolveRoute(c.Request.URL.Path)  // existing logic

    h.mu.RLock()
    proxy, ok := h.proxies[route.ServiceName]
    h.mu.RUnlock()

    if !ok {
        c.JSON(http.StatusBadGateway, gin.H{"error": "unknown service"})
        return
    }

    // Inject gateway headers (existing logic — giữ nguyên)
    c.Request.Header.Set("X-Gateway-Secret", h.cfg.GatewaySecret)
    // X-User-ID / X-User-Email từ session...

    proxy.ServeHTTP(c.Writer, c.Request)
}

func (h *ProxyHandler) errorHandler(serviceName string) func(http.ResponseWriter, *http.Request, error) {
    return func(w http.ResponseWriter, r *http.Request, err error) {
        log.Printf("proxy error service=%s: %v", serviceName, err)
        // MIN-13: dùng json.Marshal thay vì string concat để tránh JSON injection
        body, _ := json.Marshal(map[string]string{
            "error":   "Service unavailable",
            "service": serviceName,
        })
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusBadGateway)
        _, _ = w.Write(body)
    }
}
```

**Bug cần tránh:**
- Biến loop `for ..., rawURL := range ...` KHÔNG được tên `url` — nếu đặt `url` sẽ shadow package `net/url`.
- `neturl.Parse(rawURL)` dùng alias `neturl` cho rõ ràng.

### Bước 3 — Verify
```bash
cd backend-microservices/gateway-service-go
go build ./...          # phải compile clean
go test ./internal/handler
# Load test
ab -n 10000 -c 100 http://localhost:8000/api/parking/lots/
# p99 latency phải < 100ms
```

---

## S2-IMP-4 · Refactor `BookingViewSet` 716 dòng

**File:** `backend-microservices/booking-service/bookings/views.py`
**Thời gian:** 2 ngày.

**Gitnexus pre-check:**
```
mcp__gitnexus__context({name: "BookingViewSet", repo: "Project_Main"})
mcp__gitnexus__impact({target: "BookingViewSet", direction: "upstream", repo: "Project_Main"})
```

**Kế hoạch tách:**

### Bước 1 — Xoá duplicate
1. Xoá `BookingViewSet._get_hourly_price` (dòng 239-253) — dùng `services.get_hourly_price` đã tồn tại ở `services.py:27-39`.
2. Xoá `BookingViewSet.booking_stats` (dòng 380-463) — dùng `services.get_user_stats` ở `services.py:392-430`.
3. Consolidate `current()` + `current_parking()` → 1 endpoint với query param `?mode=full|parking`.
4. Consolidate `payment()` + `initiate_payment()` → 1 endpoint với query param.

### Bước 2 — Extract business logic sang `services.py`
Move từ views.py → services.py:
- `_validate_booking_time()` → `services.validate_booking_time()`
- `_calculate_extend_price()` → `services.calculate_extend_price()`
- `_broadcast_*` → event bus (đã làm ở S2-IMP-2)

### Bước 3 — Tách ViewSet con
```python
# bookings/views.py — 300-400 dòng
class BookingViewSet(viewsets.ModelViewSet):
    """CRUD + list"""
    # chỉ list, retrieve, create, update, destroy
    pass

# bookings/views_lifecycle.py
class BookingLifecycleViewSet(viewsets.ViewSet):
    """checkin, checkout, extend, cancel"""
    @action(...)
    def checkin(self, request, pk=None): ...
    def checkout(self, request, pk=None): ...
    def extend(self, request, pk=None): ...
    def cancel(self, request, pk=None): ...

# bookings/views_payment.py
class BookingPaymentViewSet(viewsets.ViewSet):
    """payment, initiate_payment, verify_payment"""
    pass

# bookings/views_stats.py
class BookingStatsView(APIView):
    """stats cho 1 user"""
    pass
```

### Bước 4 — Update `urls.py`
```python
# bookings/urls.py
router = DefaultRouter()
router.register(r'bookings', BookingViewSet)
router.register(r'bookings-lifecycle', BookingLifecycleViewSet, basename='booking-lifecycle')
router.register(r'bookings-payment', BookingPaymentViewSet, basename='booking-payment')
```

Hoặc dùng DRF nested routing để giữ URL `/bookings/{id}/checkin/` bằng `@action` trên ViewSet chính, chỉ tách file code.

### Bước 5 — Verify
```bash
wc -l backend-microservices/booking-service/bookings/views*.py
# Expected: mỗi file < 400 dòng

cd backend-microservices/booking-service && pytest
# Expected: toàn bộ PASS

cd ../../spotlove-ai && npm run e2e
# Expected: 5/5 PASS
```

---

## S2-IMP-5 · Refactor `ai-service-fastapi/app/routers/esp32.py` 1893 dòng

**File:** `backend-microservices/ai-service-fastapi/app/routers/esp32.py`
**Thời gian:** 3-4 ngày (bump từ 2 vì 1893 dòng + 4 flow đan xen state → cần đủ thời gian test regression).

**Plan tách:**

```
ai-service-fastapi/app/
├── routers/esp32.py                  # ≤ 200 dòng — chỉ HTTP adapter
├── engine/
│   └── esp32_device_store.py         # in-memory device registry (heartbeat, register)
└── services/
    ├── esp32_checkin.py              # logic check-in flow
    ├── esp32_checkout.py             # logic check-out flow
    ├── esp32_barrier.py              # open/close barrier
    └── esp32_cash_payment.py         # cash payment pipeline
```

**Bước thực hiện:**

### Bước 1 — Extract device store
Tạo `app/engine/esp32_device_store.py`:
```python
from datetime import datetime
from typing import Dict, Optional

class ESP32DeviceStore:
    def __init__(self):
        self._devices: Dict[str, dict] = {}

    def register(self, device_id: str, info: dict) -> None: ...
    def heartbeat(self, device_id: str) -> None: ...
    def get(self, device_id: str) -> Optional[dict]: ...
    def list_all(self) -> list[dict]: ...

store = ESP32DeviceStore()
```

### Bước 2 — Extract checkin service
`app/services/esp32_checkin.py`:
```python
async def process_checkin(
    device_token: str,
    request: ESP32CheckInRequest,
    db: Session,
) -> ESP32CheckInResponse:
    # Business logic extracted from esp32.py:checkin endpoint
    ...
```

### Bước 3 — Router thin
`app/routers/esp32.py`:
```python
from app.services import esp32_checkin, esp32_checkout, esp32_barrier, esp32_cash_payment
from app.engine.esp32_device_store import store

router = APIRouter(prefix="/ai/parking/esp32", tags=["esp32"])

@router.post("/check-in/", dependencies=[Depends(verify_esp32_token)])
async def checkin(request: ESP32CheckInRequest, db: Session = Depends(get_db)):
    return await esp32_checkin.process_checkin(request, db)

@router.post("/check-out/", dependencies=[Depends(verify_esp32_token)])
async def checkout(request: ESP32CheckOutRequest, db: Session = Depends(get_db)):
    return await esp32_checkout.process_checkout(request, db)

# ... tương tự cho barrier + cash_payment
```

### Bước 4 — Xoá dead code trong quá trình
- `_parse_qr_data` (đã flagged 2026-03-27)
- `_capture_plate_image` (commented out TẠM THỜI)
- `_get_test_image_bytes`

### Bước 5 — Verify
```bash
wc -l backend-microservices/ai-service-fastapi/app/routers/esp32.py
# Expected: ≤ 200

cd backend-microservices/ai-service-fastapi && pytest tests/ -k esp32 -v
```

---

## S2-IMP-6 · Refactor `ai-service-fastapi/app/routers/parking.py` 760 dòng

**File:** `backend-microservices/ai-service-fastapi/app/routers/parking.py`
**Thời gian:** 1 ngày.

**Plan:** Tách theo action, mỗi file 1 endpoint + helper cục bộ.
```
app/routers/
├── parking/
│   ├── __init__.py        # APIRouter init
│   ├── scan_plate.py
│   ├── check_in.py
│   ├── check_out.py
│   └── detect_occupancy.py
```

`app/routers/parking/__init__.py`:
```python
from fastapi import APIRouter
from . import scan_plate, check_in, check_out, detect_occupancy

router = APIRouter(prefix="/ai/parking", tags=["parking"])
router.include_router(scan_plate.router)
router.include_router(check_in.router)
router.include_router(check_out.router)
router.include_router(detect_occupancy.router)
```

Mỗi file con:
```python
# app/routers/parking/scan_plate.py
from fastapi import APIRouter, UploadFile
from app.engine.plate_pipeline import PlatePipeline

router = APIRouter()

@router.post("/scan-plate/")
async def scan_plate(image: UploadFile):
    pipeline = PlatePipeline.get_instance()
    result = await pipeline.process(image)
    return result.to_dict()
```

**Verify:** gitnexus trace `/scan-plate/`, `/check-in/`, `/check-out/` route đều resolve được.

---

## S2-IMP-7 · Refactor `chatbot-service-fastapi` god classes

**Files:**
- `backend-microservices/chatbot-service-fastapi/app/engine/orchestrator.py` (652 dòng)
- `backend-microservices/chatbot-service-fastapi/app/application/services/response_service.py` (608 dòng)

**Thời gian:** 2 ngày.

**Plan:**

### ResponseService: Strategy pattern cho mỗi intent
```python
# app/application/services/response_strategies/
├── __init__.py           # strategy registry
├── base.py               # BaseStrategy ABC
├── booking_create.py     # xử lý intent create_booking
├── booking_cancel.py
├── booking_list.py
├── parking_info.py
├── payment_info.py
├── help.py
└── ... 16 intents
```

`app/application/services/response_strategies/__init__.py`:
```python
from app.domain.value_objects.intent import IntentType
from .booking_create import BookingCreateStrategy
from .booking_cancel import BookingCancelStrategy
# ...

STRATEGIES = {
    IntentType.BOOKING_CREATE: BookingCreateStrategy,
    IntentType.BOOKING_CANCEL: BookingCancelStrategy,
    # ...
}

def get_strategy(intent_type: IntentType):
    return STRATEGIES[intent_type]()
```

`response_service.py` giờ chỉ:
```python
class ResponseService:
    async def generate_response(self, intent: Intent, context: Context) -> str:
        strategy = get_strategy(intent.type)
        return await strategy.respond(intent, context)
```

~50 dòng thay vì 608.

### Orchestrator: Tách pipeline stage
```python
# app/engine/pipeline_stages/
├── __init__.py
├── wizard_stage.py
├── intent_stage.py
├── confidence_gate_stage.py
├── safety_stage.py
├── action_stage.py
├── response_stage.py
└── memory_stage.py
```

```python
# app/engine/orchestrator.py
class ChatbotOrchestrator:
    def __init__(self, ...):
        self.stages = [
            WizardStage(),
            IntentStage(intent_service),
            ConfidenceGateStage(),
            SafetyStage(),
            ActionStage(action_service),
            ResponseStage(response_service),
            MemoryStage(memory_service),
        ]

    async def process_message(self, message: Message) -> Response:
        context = PipelineContext(message=message)
        for stage in self.stages:
            context = await stage.execute(context)
            if context.should_short_circuit:
                break
        return context.response
```

~150 dòng thay vì 652.

**Verify:**
```bash
wc -l backend-microservices/chatbot-service-fastapi/app/engine/orchestrator.py
wc -l backend-microservices/chatbot-service-fastapi/app/application/services/response_service.py
# Cả 2 < 250

cd backend-microservices/chatbot-service-fastapi && pytest
# Expected: PASS

python backend-microservices/test_chatbot_e2e.py
# Expected: tất cả 16 intent flow PASS
```

---

## S2-IMP-8 · FE dead deps + code splitting

**Files:**
- `spotlove-ai/package.json`
- `spotlove-ai/src/App.tsx`
- `spotlove-ai/src/integrations/` (rỗng, xoá)

**Thời gian:** 1 ngày.

**Fix:**

### Bước 1 — Gỡ React Query
```bash
cd spotlove-ai
npm uninstall @tanstack/react-query
```

`src/App.tsx`:
```tsx
// ❌ XOÁ
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
const queryClient = new QueryClient();

// ❌ XOÁ wrapper
<QueryClientProvider client={queryClient}>
  ...
</QueryClientProvider>
```

### Bước 2 — Gỡ Supabase
```bash
npm uninstall @supabase/supabase-js
rm -rf src/integrations/
```

Grep xác nhận:
```bash
grep -r "supabase\|QueryClient\|useQuery" src/
# Expected: rỗng
```

### Bước 3 — Route-level lazy loading
`src/App.tsx`:
```tsx
import { lazy, Suspense } from "react";
import { PageSkeleton } from "@/components/PageSkeleton";

// Eager cho page vào đầu tiên
import Index from "./pages/Index";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

// Lazy cho mọi page nặng
const BookingPage = lazy(() => import("./pages/BookingPage"));
const MapPage = lazy(() => import("./pages/MapPage"));
const CamerasPage = lazy(() => import("./pages/CamerasPage"));
const CheckInOutPage = lazy(() => import("./pages/CheckInOutPage"));
const DetectionHistoryPage = lazy(() => import("./pages/DetectionHistoryPage"));
const BanknoteDetectionPage = lazy(() => import("./pages/BanknoteDetectionPage"));

// Admin — lazy tất cả
const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const AdminConfigPage = lazy(() => import("./pages/admin/AdminConfigPage"));
const AdminUsersPage = lazy(() => import("./pages/admin/AdminUsersPage"));
const AdminRevenuePage = lazy(() => import("./pages/admin/AdminRevenuePage"));
const AdminESP32Page = lazy(() => import("./pages/admin/AdminESP32Page"));
// ... 9 admin pages total

function App() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/" element={<Index />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/booking" element={<BookingPage />} />
        <Route path="/map" element={<MapPage />} />
        {/* ... */}
      </Routes>
    </Suspense>
  );
}
```

Tạo `src/components/PageSkeleton.tsx`:
```tsx
export function PageSkeleton() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="animate-pulse text-muted-foreground">Đang tải...</div>
    </div>
  );
}
```

### Bước 4 — Vite config manual chunks
`vite.config.ts` thêm:
```ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        "vendor-react": ["react", "react-dom", "react-router-dom"],
        "vendor-ui": ["@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu", /* ... */],
        "vendor-charts": ["recharts"],
        "vendor-redux": ["@reduxjs/toolkit", "react-redux"],
      },
    },
  },
},
```

### Bước 5 — Verify bundle size
```bash
npm run build
ls -lh dist/assets/ | sort -k5 -h
# Tìm chunks lớn nhất
du -sh dist/assets/index-*.js
```

**Target:** initial JS < 400kB (gzipped), từ ~700-800kB trước đó.

### Bước 6 — Run app
```bash
npm run dev
# Mở browser DevTools → Network → filter JS
# Trang / chỉ load chunks eager + PageSkeleton
# Click /booking → mới load booking chunk
```

---

## S2-IMP-9 · FE layering compliance — ~25-28 pages về đúng `services/business/*`

**Files:** Toàn bộ `src/pages/*.tsx` (19 top-level) + `src/pages/admin/*.tsx` (8-9 file) = ~25-28 pages + Redux slices + một số components vi phạm.
**Thời gian:** 6-8 ngày (bump từ 3-4 vì số lượng thực tế gấp đôi plan v1 và mỗi page cần Zod schema + mapping function).

**Chiến thuật:** Mỗi page 1 commit.

**Pattern refactor mỗi page:**

### Trước (violation)
```tsx
// src/pages/BookingPage.tsx
import { bookingApi } from "@/services/api/booking.api";
import { parkingApi } from "@/services/api/parking.api";

const BookingPage = () => {
  const [lots, setLots] = useState([]);

  useEffect(() => {
    parkingApi.getLots().then(setLots); // ❌ direct API call
  }, []);

  const handleSubmit = async (data) => {
    const response = await bookingApi.create(data); // ❌
    // inline mapping snake_case → camelCase
    // inline error handling
  };
};
```

### Sau (compliance)
```tsx
// src/services/business/parking.service.ts (bổ sung nếu chưa có)
export async function listParkingLots(): Promise<ParkingLot[]> {
  const raw = await parkingApi.getLots();
  return raw.map(mapParkingLotResponse); // unified mapping
}

// src/services/business/booking.service.ts
export async function createBooking(input: CreateBookingInput): Promise<Booking> {
  try {
    const raw = await bookingApi.create(toBookingRequest(input));
    return mapBookingResponse(raw);
  } catch (err) {
    throw toUserFacingError(err);
  }
}

// src/pages/BookingPage.tsx
import * as parkingService from "@/services/business/parking.service";
import * as bookingService from "@/services/business/booking.service";

const BookingPage = () => {
  const [lots, setLots] = useState<ParkingLot[]>([]);

  useEffect(() => {
    parkingService.listParkingLots().then(setLots);
  }, []);

  const handleSubmit = async (data) => {
    try {
      const booking = await bookingService.createBooking(data);
      toast.success("Booking thành công");
    } catch (err) {
      toast.error(err.message);
    }
  };
};
```

**Danh sách pages cần refactor:**
1. `BookingPage.tsx`
2. `CheckInOutPage.tsx`
3. `MapPage.tsx`
4. `KioskPage.tsx`
5. `SupportPage.tsx`
6. `PanicButtonPage.tsx`
7. `DetectionHistoryPage.tsx`
8. `BanknoteDetectionPage.tsx`
9-16. `pages/admin/*.tsx` (8 files)

**Redux slices:** Sửa luôn `authSlice.ts`, `bookingSlice.ts`, `parkingSlice.ts` — import từ `services/business/*` thay vì `services/api/*`.

**Gate kiểm tra:**
```bash
cd spotlove-ai
# Không page nào import từ services/api/ trực tiếp
grep -rn 'from.*services/api' src/pages/ src/components/ src/store/slices/
# Expected: rỗng (hoặc chỉ có trong services/business/)
```

**Bonus — Zod schemas:** Tạo schema cho mọi response API, parse trước khi map:
```ts
// services/api/booking.api.ts
import { z } from "zod";

export const BookingResponseSchema = z.object({
  id: z.string().uuid(),
  slot_id: z.number(),
  slot_code: z.string(),
  parking_lot_name: z.string(),
  start_time: z.string().datetime(),
  end_time: z.string().datetime(),
  status: z.enum(["pending", "active", "completed", "cancelled"]),
  // ...
});

export type BookingResponse = z.infer<typeof BookingResponseSchema>;

export async function getBooking(id: string): Promise<BookingResponse> {
  const { data } = await axiosClient.get(`/bookings/${id}/`);
  return BookingResponseSchema.parse(data); // crash sớm nếu backend đổi shape
}
```

Xoá dual-case mapping `slotId | slot_id | car_slot.id` trong `bookingSlice.ts:142-230`.

---

## S2-IMP-10 · Unity — Extract `ParkingManager` 756 dòng

**File:** `ParkingSimulatorUnity/Assets/Scripts/Core/ParkingManager.cs`
**Thời gian:** 2 ngày.

**Plan tách:**
```
Assets/Scripts/Core/
├── ParkingManager.cs                 # ≤ 250 dòng — Singleton + lifecycle wiring
├── Bootstrap/
│   ├── ParkingManagerBootstrap.cs    # Awake + DI resolve
│   └── DependencyResolver.cs         # helper cho Find/Load Resources
├── Sync/
│   └── ParkingDataSync.cs            # Login, FetchData, PollSlots, WS subscribe
└── Flow/
    ├── GateFlowController.cs         # ESP32CheckInFlow, ESP32CheckOutFlow
    └── StaticVehicleSpawner.cs       # SpawnStaticParkedVehicle, AttachPlateText
```

**Bước thực hiện:**

### Bước 1 — Fix reflection hack trước (UNITY-IMP-1)
`ParkingSimulatorUnity/Assets/Scripts/Parking/BarrierController.cs` (**đúng path là `Parking/` không phải `Gate/`** — plan v1 sai):
```csharp
// Thêm public property thay vì private field
public Transform Arm
{
    get => barrierArm;
    set => barrierArm = value;
}
```

`ParkingManager.cs:122-136`:
```csharp
// ❌ XOÁ reflection
// var field = typeof(BarrierController).GetField("barrierArm", ...);
// field.SetValue(entryBarrier, entryPivot.transform);

// ✅ Direct property
entryBarrier.Arm = entryPivot.transform;
exitBarrier.Arm = exitPivot.transform;
```

### Bước 2 — Coroutine timeout helper (UNITY-IMP-2)
Tạo `Assets/Scripts/Utility/CoroutineHelpers.cs`:
```csharp
using System;
using System.Collections;
using UnityEngine;

public static class CoroutineHelpers
{
    public static IEnumerator WaitUntilOrTimeout(
        Func<bool> condition,
        float timeoutSeconds,
        Action onTimeout = null)
    {
        float elapsed = 0f;
        while (!condition() && elapsed < timeoutSeconds)
        {
            elapsed += Time.deltaTime;
            yield return null;
        }
        if (!condition())
        {
            onTimeout?.Invoke();
            Debug.LogWarning($"[CoroutineHelper] Timeout after {timeoutSeconds}s");
        }
    }
}
```

Thay mọi `while (!done) yield return null`:
```csharp
// ❌ SAI
apiService.Login(..., () => done = true);
while (!done) yield return null;

// ✅ ĐÚNG
bool done = false;
apiService.Login(..., () => done = true);
yield return CoroutineHelpers.WaitUntilOrTimeout(
    () => done,
    timeoutSeconds: 10f,
    onTimeout: () => Debug.LogError("[ParkingManager] Login timeout")
);
if (!done) yield break; // hoặc retry
```

### Bước 3 — Extract `ParkingDataSync`
```csharp
// Assets/Scripts/Core/Sync/ParkingDataSync.cs
public class ParkingDataSync : MonoBehaviour
{
    [SerializeField] private ApiService apiService;
    [SerializeField] private AuthManager authManager;
    [SerializeField] private float pollInterval = 5f;

    public event Action<List<SlotData>> OnSlotsUpdated;
    public event Action<List<FloorData>> OnFloorsUpdated;

    public IEnumerator LoginCoroutine() { /* ... */ }
    public IEnumerator FetchParkingDataCoroutine() { /* ... */ }
    public IEnumerator PollSlotsCoroutine() { /* ... */ }
    public void SubscribeWebSocket() { /* ... */ }
}
```

### Bước 4 — Extract `GateFlowController`
```csharp
public class GateFlowController : MonoBehaviour
{
    [SerializeField] private BarrierController entryBarrier;
    [SerializeField] private BarrierController exitBarrier;
    [SerializeField] private VehicleQueue vehicleQueue;
    [SerializeField] private ESP32Simulator esp32;

    public IEnumerator ESP32CheckInFlow(VehicleController vehicle) { /* ... */ }
    public IEnumerator ESP32CheckOutFlow(VehicleController vehicle) { /* ... */ }
}
```

### Bước 5 — `ParkingManager` giữ là thin coordinator
```csharp
public class ParkingManager : MonoBehaviour
{
    [SerializeField] private ParkingDataSync dataSync;
    [SerializeField] private GateFlowController gateFlow;
    [SerializeField] private StaticVehicleSpawner vehicleSpawner;

    public static ParkingManager Instance { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;

        dataSync.OnSlotsUpdated += HandleSlotsUpdated;
    }

    private IEnumerator Start()
    {
        yield return dataSync.LoginCoroutine();
        yield return dataSync.FetchParkingDataCoroutine();
        dataSync.SubscribeWebSocket();
        StartCoroutine(dataSync.PollSlotsCoroutine());

        vehicleSpawner.SpawnInitialParkedVehicles();
        OnInitComplete?.Invoke();
    }
}
```

### Bước 6 — Verify
```bash
wc -l ParkingSimulatorUnity/Assets/Scripts/Core/ParkingManager.cs
# Expected: ≤ 250

# Unity Editor: mở scene ParkingSim, Play
# Expected: không error, data load, WS connect, simulator chạy
```

**Tương tự cho `ESP32Simulator.cs` (597 dòng) + `ApiService.cs` (561 dòng) — tách theo pattern tương tự.**

---

## S2-IMP-11 · Unity — Poll vs WebSocket duplication

**File:** `ParkingManager.cs:91-94, 274-299` (sau khi extract sang `ParkingDataSync.cs`)
**Thời gian:** 2 giờ.

**Fix:**
```csharp
// ParkingDataSync.cs
private bool isWebSocketConnected = false;

public IEnumerator PollSlotsCoroutine()
{
    while (true)
    {
        if (!isWebSocketConnected)
        {
            // Poll chỉ khi WS disconnect — fallback
            yield return FetchSlotsOnce();
        }
        yield return new WaitForSeconds(pollInterval);
    }
}

public void SubscribeWebSocket()
{
    ws.OnConnect += () => isWebSocketConnected = true;
    ws.OnDisconnect += () => isWebSocketConnected = false;
    ws.OnSlotUpdate += HandleSlotUpdate;
}
```

---

## S2-IMP-12 · `VirtualCameraStreamer` AsyncGPUReadback

**File:** `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraStreamer.cs:137-223`
**Thời gian:** 0.5 ngày.

**Fix:**
```csharp
// ❌ SAI — sync readback block main thread
private byte[] CaptureFrame(Camera cam)
{
    RenderTexture.active = renderTexture;
    tex2D.ReadPixels(new Rect(0, 0, width, height), 0, 0);
    tex2D.Apply();
    RenderTexture.active = null;
    return tex2D.EncodeToJPG(quality);
}

// ✅ ĐÚNG — async
private IEnumerator CaptureFrameAsync(Camera cam, Action<byte[]> onComplete)
{
    var request = AsyncGPUReadback.Request(renderTexture, 0, TextureFormat.RGB24);
    yield return new WaitUntil(() => request.done);

    if (request.hasError)
    {
        onComplete(null);
        yield break;
    }

    var rawData = request.GetData<byte>();
    tex2D.LoadRawTextureData(rawData);
    tex2D.Apply();
    onComplete(tex2D.EncodeToJPG(quality));
}
```

Per-camera FPS config:
```csharp
[Serializable]
public class CameraConfig
{
    public Camera camera;
    public float captureFps = 5f;  // ANPR: 10fps, overview: 1fps
}
```

---

## S2-IMP-13 · Pip-audit refresh + CI wire

**Files:** `docs/notes/*-pipaudit.json`, `.github/workflows/ci.yml`
**Thời gian:** 1 giờ.

**Fix:**

### Bước 1 — Archive stale JSON
```bash
mkdir -p docs/notes/archive/2026-03-13
mv docs/notes/*-pipaudit.json docs/notes/archive/2026-03-13/
```

### Bước 2 — Thêm CI job
`.github/workflows/ci.yml`:
```yaml
jobs:
  security-audit:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [auth-service, parking-service, booking-service, vehicle-service,
                  ai-service-fastapi, chatbot-service-fastapi,
                  notification-service-fastapi, payment-service-fastapi]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install pip-audit
      - run: |
          cd backend-microservices/${{ matrix.service }}
          pip-audit -r requirements.txt --format json \
            --output ../../docs/notes/${{ matrix.service }}-pipaudit.json
      - uses: actions/upload-artifact@v4
        with:
          name: pipaudit-${{ matrix.service }}
          path: docs/notes/${{ matrix.service }}-pipaudit.json
      # Fail nếu có HIGH/CRITICAL
      - run: |
          python -c "
          import json; import sys
          d = json.load(open('docs/notes/${{ matrix.service }}-pipaudit.json'))
          vulns = [v for v in d.get('vulnerabilities', []) if v.get('severity') in ('HIGH', 'CRITICAL')]
          if vulns: print(f'Found {len(vulns)} HIGH/CRITICAL'); sys.exit(1)
          "
```

---

# SPRINT 3 — CLEANUP + POLISH

**Mục tiêu:** Xoá dead code, đồng bộ docs, siết convention, chuẩn bị production handover.

## S3-MIN-1 · FE Minor cluster (8 items)

**Scope:** `spotlove-ai/src/**`. Tổng thời gian ước tính: **~4 giờ** (trừ M3 đã done ở S2-IMP-8 và M8 có thể kéo dài).

### S3-MIN-1-M1 · React Query staleTime default

**File:** `spotlove-ai/src/App.tsx:42`
**Áp dụng khi:** Nếu Sprint 2 quyết định **giữ** `@tanstack/react-query` thay vì gỡ (S2-IMP-8 option A đã gỡ — nếu đã gỡ thì skip task này).

**Fix:**
```tsx
// ❌ Trước
const queryClient = new QueryClient();

// ✅ Sau
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30s trước khi mark stale
      gcTime: 5 * 60_000,      // 5 phút giữ cache
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

**Verify:** `npm run dev` → mở DevTools → React Query DevTools panel → xác nhận `staleTime: 30000` cho query bất kỳ. **5 phút.**

---

### S3-MIN-1-M2 · AdminStatsPage orphan

**File:** `spotlove-ai/src/pages/admin/AdminStatsPage.tsx`
**Triệu chứng:** File tồn tại nhưng không import trong `App.tsx` → dead page.

**Fix (chọn 1):**

**Option A — Wire up vào router (nếu cần page này):**
```tsx
// App.tsx
const AdminStatsPage = lazy(() => import("./pages/admin/AdminStatsPage"));
// Trong <Routes>:
<Route path="/admin/stats" element={<AdminStatsPage />} />
```
Kiểm tra `src/components/layout/AppSidebar.tsx` thêm link điều hướng.

**Option B — Xoá file nếu không cần:**
```bash
rm spotlove-ai/src/pages/admin/AdminStatsPage.tsx
grep -rn "AdminStatsPage" spotlove-ai/src/  # phải rỗng
```

**Verify:** Option A → navigate `/admin/stats` load ok. Option B → `npm run typecheck` PASS không error missing import. **15 phút.**

---

### S3-MIN-1-M3 · Xoá `src/integrations/`

**Status:** Đã fix ở S2-IMP-8 khi gỡ `@supabase/supabase-js`. Nếu folder vẫn còn:
```bash
rm -rf spotlove-ai/src/integrations/
grep -rn "integrations" spotlove-ai/src/  # phải rỗng
```

---

### S3-MIN-1-M4 · `authSlice.getUserFromCookie` cache 1 lần

**File:** `spotlove-ai/src/store/slices/authSlice.ts:72-74`
**Triệu chứng:** `getUserFromCookie()` gọi 2 lần trong `initialState`.

**Fix:**
```ts
// ❌ Trước
const initialState: AuthState = {
  user: getUserFromCookie(),
  isAuthenticated: !!getUserFromCookie(),
  // ...
};

// ✅ Sau
const cachedUser = getUserFromCookie();
const initialState: AuthState = {
  user: cachedUser,
  isAuthenticated: !!cachedUser,
  // ...
};
```

**Verify:** `npm run test -- authSlice` PASS. **10 phút.**

---

### S3-MIN-1-M5 · Axios config.metadata thay vì cast

**File:** `spotlove-ai/src/services/api/axios.client.ts:58`
**Triệu chứng:** `(config as InternalAxiosRequestConfig & { _t: number })._t = Date.now()` — type cast bẩn.

**Fix:**
```ts
// ✅ Dùng metadata field chính thức của axios
import type { InternalAxiosRequestConfig } from "axios";

declare module "axios" {
  export interface InternalAxiosRequestConfig {
    metadata?: { startTime: number };
  }
}

axiosClient.interceptors.request.use((config) => {
  config.metadata = { startTime: Date.now() };
  return config;
});

axiosClient.interceptors.response.use((response) => {
  const elapsed = Date.now() - (response.config.metadata?.startTime ?? 0);
  if (import.meta.env.DEV) console.debug(`[API] ${response.config.url} ${elapsed}ms`);
  return response;
});
```

**Verify:** `npm run typecheck` PASS không cần cast. **15 phút.**

---

### S3-MIN-1-M6 · Xoá comment `FE-BUG 17 FIX`

**File:** `spotlove-ai/src/services/websocket.service.ts:83`

**Fix:** Xoá comment, nếu cần thông tin về fix thì đã có trong git log của commit tương ứng.
```bash
grep -n "FE-BUG" spotlove-ai/src/services/websocket.service.ts  # trước khi xoá để verify
```

**Verify:** Sau sửa `grep -rn "FE-BUG" spotlove-ai/src/` rỗng. **2 phút.**

---

### S3-MIN-1-M7 · TODO(security) → GitHub issue

**File:** `spotlove-ai/src/services/websocket.service.ts:103`
**TODO hiện tại:** `// TODO(security): Migrate to signed short-lived token auth`

**Fix:**
1. Tạo GitHub issue: `gh issue create --title "Security: migrate WebSocket to signed short-lived token auth" --body "..."`
2. Replace comment bằng reference:
```ts
// Security: authentication via session cookie (see GH issue #XXX for short-lived token migration)
```

**Verify:** Issue tồn tại trên GitHub. **15 phút.**

---

### S3-MIN-1-M8 · `BookingPage.tsx` perf profile

**File:** `spotlove-ai/src/pages/BookingPage.tsx` (1326 dòng, 1 `useMemo`, 0 `useCallback`)
**Chú ý:** Tác vụ này phụ thuộc vào S2-IMP-9 đã refactor `BookingPage` thành các step components. Nếu chưa done S2-IMP-9, skip.

**Các bước:**
1. Start dev server `npm run dev`
2. Mở React DevTools → Profiler tab
3. Record 1 phiên booking đầy đủ (5 step)
4. Xác định các component re-render không cần thiết (cờ "Why did this render?")
5. Apply `useCallback` cho handler props truyền xuống memo'd child
6. Apply `useMemo` cho computed values tốn thời gian (ví dụ `calculatedPrice`)

**Verify:** Sau fix, profile lại → số commit giảm ≥ 30% cho cùng tương tác. **2 giờ** (hoặc dời sang backlog nếu không regression đáng kể).

## S3-MIN-2 · Backend Minor cluster (16 items)

**Scope:** `backend-microservices/**`. Tổng thời gian ước tính: **~1.5 ngày** (M3 chiếm phần lớn).

### S3-MIN-2-M1 · Xoá `booking_stats` duplicate

**File:** `backend-microservices/booking-service/bookings/views.py:380-463`
**Triệu chứng:** `BookingViewSet.booking_stats` duplicate hoàn toàn `services.get_user_stats` ở `services.py:392-430`.

**Fix:**
```python
# ❌ Trước — ~80 dòng code duplicate
@action(detail=False, methods=['get'])
def booking_stats(self, request):
    # ... logic tính stats ...
    return Response(data)

# ✅ Sau
from bookings.services import get_user_stats

@action(detail=False, methods=['get'])
def booking_stats(self, request):
    stats = get_user_stats(request.user_id)
    return Response(stats)
```

**Verify:** `pytest backend-microservices/booking-service/tests/ -k booking_stats` PASS. **15 phút.**

---

### S3-MIN-2-M2 · Xoá `_get_hourly_price` duplicate

**File:** `backend-microservices/booking-service/bookings/views.py:239-253`
**Fix:** Tương tự M1 — xoá method, thay bằng `from bookings.services import get_hourly_price`.
```python
# Trong place gọi cũ:
price = get_hourly_price(package_type, vehicle_type)
```

**Verify:** Grep `_get_hourly_price` → rỗng. `pytest` PASS. **10 phút.**

---

### S3-MIN-2-M3 · Fix `verify_payment` TODO stub

**File:** `backend-microservices/booking-service/bookings/views.py:474`
**Triệu chứng:** Hiện tại endpoint `verify_payment` trả cứng `{"success": true}` — có thể bypass payment trong test production.

**Fix:**
```python
# ❌ Trước
@action(detail=True, methods=['post'])
def verify_payment(self, request, pk=None):
    # TODO: Verify with payment gateway
    return Response({"success": True})

# ✅ Sau — delegate sang payment-service
@action(detail=True, methods=['post'])
def verify_payment(self, request, pk=None):
    booking = self.get_object()
    transaction_id = request.data.get('transaction_id')
    if not transaction_id:
        raise ValidationError({"transaction_id": "Required"})

    # Call payment-service verify endpoint
    resp = requests.post(
        f"{settings.PAYMENT_SERVICE_URL}/payments/verify/",
        json={"transaction_id": transaction_id, "booking_id": str(booking.id)},
        headers={"X-Gateway-Secret": settings.GATEWAY_SECRET},
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("status") == "success":
        booking.payment_status = 'completed'
        booking.save(update_fields=['payment_status'])
        return Response({"success": True, "transaction_id": transaction_id})
    else:
        return Response({"success": False, "reason": result.get("reason")}, status=400)
```

**Phụ thuộc:** `payment-service` đã implement endpoint `/payments/verify/` với logic kiểm tra giao dịch thực.

**Verify:** Integration test gọi `verify_payment` với transaction giả → trả 400 (không bypass). **0.5 ngày** (bao gồm cả thời gian implement payment-service endpoint nếu chưa có).

---

### S3-MIN-2-M4 · Sửa `_PAYMENT_METHOD_MAP`

**File:** `backend-microservices/booking-service/bookings/services.py:301-304`
**Triệu chứng:** `{"on_exit": "cash", "online": "cash"}` — map `online → cash` sai semantics.

**Fix:**
```python
# ❌ Trước
_PAYMENT_METHOD_MAP = {"on_exit": "cash", "online": "cash"}

# ✅ Sau
_PAYMENT_METHOD_MAP = {
    "on_exit": "cash",         # Thanh toán khi lấy xe → tiền mặt
    "online": "e_wallet",      # Thanh toán online → ví điện tử (sẽ chi tiết hóa khi tích hợp cổng)
}
```

**Verify:** Grep usage → các consumer đã xử lý đúng giá trị mới. `pytest services -v`. **15 phút.**

---

### S3-MIN-2-M5 · Lazy-read `GATEWAY_SECRET` trong serializer

**File:** `backend-microservices/booking-service/bookings/serializers.py:19`
**Triệu chứng:** `GATEWAY_SECRET = os.environ.get(...)` ở module-level — đọc 1 lần lúc import.

**Fix:**
```python
# ❌ Trước
import os
GATEWAY_SECRET = os.environ.get('GATEWAY_SECRET', 'gateway-internal-secret-key')
# ... trong method: headers={'X-Gateway-Secret': GATEWAY_SECRET}

# ✅ Sau
from django.conf import settings
# ... trong method:
headers = {'X-Gateway-Secret': settings.GATEWAY_SECRET}
```

**Verify:** `pytest` + startup test với env thay đổi runtime → service pick up đúng. **10 phút.**

---

### S3-MIN-2-M6 · gofmt mixed tab/space

**File:** `backend-microservices/gateway-service-go/internal/handler/auth.go:107-117, 219-224`

**Fix:**
```bash
cd backend-microservices/gateway-service-go
gofmt -w internal/handler/auth.go
git diff internal/handler/auth.go  # review thay đổi
```

**Verify:** `go vet ./...` + `gofmt -l ./...` → không output. **2 phút.**

---

### S3-MIN-2-M7 · Multi-stage Dockerfile cho `ai-service-fastapi`

**File:** `backend-microservices/ai-service-fastapi/Dockerfile`
**Triệu chứng:** Single-stage build → image nặng (~3-5 GB) do gom cả build tools + model download cache.

**Fix:**
```dockerfile
# Stage 1: Builder — install deps + download models
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Pre-download EasyOCR models
RUN python -c "import easyocr; easyocr.Reader(['en'], model_storage_directory='/build/models')"

# Stage 2: Runtime — chỉ copy cần thiết
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 wget \
    && rm -rf /var/lib/apt/lists/*

ARG APP_UID=1000
RUN useradd --uid ${APP_UID} --create-home app
WORKDIR /app

COPY --from=builder /root/.local /home/app/.local
COPY --from=builder /build/models /app/ml/models
COPY --chown=app:app . .

USER app
ENV PATH=/home/app/.local/bin:$PATH PYTHONPATH=/app:/app/shared

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --spider -q http://localhost:8009/health/ || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009", "--workers", "2"]
```

**Verify:**
```bash
docker build -t ai-service-fastapi:multi-stage backend-microservices/ai-service-fastapi/
docker images ai-service-fastapi:multi-stage --format "{{.Size}}"
# Expected: giảm ~30-50% so với single-stage
```
**1 giờ.**

---

### S3-MIN-2-M8 · YAML anchor cho docker-compose env

**File:** `backend-microservices/docker-compose.yml`
**Triệu chứng:** Env vars (DB_HOST, DB_USER, GATEWAY_SECRET, RABBITMQ_URL…) duplicate ~10 lần qua các service.

**Fix:**
```yaml
# Thêm ở đầu file, trước `services:`
x-common-env: &common_env
  DB_HOST: mysql
  DB_PORT: 3306
  DB_USER: ${DB_USER:?DB_USER must be set in .env}
  DB_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD must be set in .env}
  GATEWAY_SECRET: ${GATEWAY_SECRET:?GATEWAY_SECRET must be set in .env}
  RABBITMQ_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASS}@rabbitmq:5672/
  PYTHONPATH: /app:/app/shared

services:
  auth-service:
    # ...
    environment:
      <<: *common_env
      SECRET_KEY: ${SECRET_KEY}
      REDIS_URL: redis://redis:6379/1
      # service-specific vars...
```

**Verify:**
```bash
cd backend-microservices
docker compose config > /tmp/compose-rendered.yml
# Đếm số lần DB_USER xuất hiện trong file nguồn vs rendered
grep -c "DB_USER" docker-compose.yml   # giảm từ ~10 xuống 1 (trong anchor)
grep -c "DB_USER" /tmp/compose-rendered.yml   # vẫn ~10 sau khi merge
docker compose up -d --build
```
**30 phút.**

---

### S3-MIN-2-M9 · Shared volume restart chain

**File:** `backend-microservices/docker-compose.yml`
**Triệu chứng:** `./shared:/app/shared` mount được bind — khi `shared/` update (ví dụ fix `gateway_middleware.py`), các service Python không tự restart để reload.

**Fix (chọn 1 trong 2):**

**Option A — Build-time copy (đề xuất, tương thích với S1-CRIT-11):**
Xoá bind mount `./shared:/app/shared` khỏi mọi service. Dockerfile mỗi service copy `shared/` vào image build-time:
```dockerfile
# Trong mỗi service Dockerfile, build context = repo root
COPY shared/ /app/shared/
COPY <service>/ /app/
```
Compose:
```yaml
auth-service:
  build:
    context: .                                    # repo root
    dockerfile: ./auth-service/Dockerfile
  # volumes: - ./shared:/app/shared    ← XOÁ
```

**Option B — Restart script khi `shared/` thay đổi:**
```bash
# scripts/restart-shared-consumers.sh
#!/bin/bash
for svc in auth-service parking-service booking-service vehicle-service \
           ai-service-fastapi chatbot-service-fastapi \
           notification-service-fastapi payment-service-fastapi; do
  docker compose restart "$svc"
done
```
Chạy thủ công sau khi sửa `shared/`.

**Verify:** Sửa 1 câu log trong `shared/gateway_middleware.py` → build lại → restart → thấy log mới. **0.5 ngày** cho Option A (do phải đổi Dockerfile của 8 service + test).

---

### S3-MIN-2-M10 · auth-service `ALLOWED_HOSTS` fail-fast

**File:** `backend-microservices/auth-service/auth_service/settings.py`

**Fix:**
```python
# ❌ Trước
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# ✅ Sau — production mode bắt buộc ALLOWED_HOSTS
DEBUG = config('DEBUG', default=False, cast=bool)
_default_hosts = 'localhost,127.0.0.1' if DEBUG else None
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default=_default_hosts,
    cast=lambda v: [h.strip() for h in v.split(',')] if v else None,
)
if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS must be set in production")
```

**Verify:** `DEBUG=False ALLOWED_HOSTS= docker compose up auth-service` → fail ngay với RuntimeError. **15 phút.**

---

### S3-MIN-2-M11 · Rename root `test_*.py` scripts

**Files:**
- `backend-microservices/test_e2e_full_flow.py`
- `backend-microservices/test_ai_full.py`
- `backend-microservices/test_chatbot_e2e.py`
- `backend-microservices/test_chatbot_lifecycle.py`
- `backend-microservices/test_booking_plate_scenarios.py`
- `backend-microservices/test_e2e_parksmart.py`

**Triệu chứng:** Tên bắt đầu `test_*.py` khiến pytest auto-collect nếu chạy từ root → nhầm lẫn với pytest suite thật. Đây là scripts standalone chạy bằng `python file.py`.

**Fix:**
```bash
mkdir -p backend-microservices/scripts/e2e
cd backend-microservices
for f in test_e2e_full_flow.py test_ai_full.py test_chatbot_e2e.py \
         test_chatbot_lifecycle.py test_booking_plate_scenarios.py \
         test_e2e_parksmart.py; do
  git mv "$f" "scripts/e2e/${f#test_}"
done
```

Update `CLAUDE.md` reference nếu có, update `seed_e2e_data.py` nếu import từ các file trên.

Thêm `conftest.py` ở root với:
```python
# backend-microservices/conftest.py
collect_ignore = ["scripts"]
```

**Verify:**
```bash
pytest --collect-only backend-microservices/ 2>&1 | grep -v "scripts/e2e"
# Không có test collected từ scripts/e2e/
```
**30 phút.**

---

### S3-MIN-2-M12 · `.gitignore` logs files

**Files:** `backend-microservices/logs/*.txt`

**Fix:**
```bash
# Thêm vào .gitignore
echo "backend-microservices/logs/*.txt" >> .gitignore
echo "backend-microservices/logs/*.log" >> .gitignore

# Untrack existing nếu có
git rm --cached backend-microservices/logs/*.txt 2>/dev/null || true
```

**Verify:** `git status --ignored backend-microservices/logs/` list `*.txt` là ignored. **10 phút.**

---

### S3-MIN-2-M13 · JSON injection fix gateway proxy errorHandler

**Status:** Đã fix ở **S2-IMP-3** (rewrite proxy.go dùng `json.Marshal` thay string concat). Chỉ cần verify ở đây:

```bash
grep -n "json.Marshal" backend-microservices/gateway-service-go/internal/handler/proxy.go
# Phải có ít nhất 1 match trong errorHandler
```

Nếu chưa fix ở S2-IMP-3, apply từ snippet đó.

---

### S3-MIN-2-M14 · AI config `os.makedirs` side-effect

**File:** `backend-microservices/ai-service-fastapi/app/config.py:36`
**Triệu chứng:** `os.makedirs(settings.MEDIA_ROOT, exist_ok=True)` ở module-level → chạy lúc import, gây side-effect khi pytest collect.

**Fix:** Chuyển vào `lifespan()` ở `main.py`:
```python
# ❌ app/config.py — xoá dòng này
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

# ✅ app/main.py — trong lifespan()
@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
    Path(settings.ML_MODELS_DIR).mkdir(parents=True, exist_ok=True)
    # ... existing startup ...
    yield
```

**Verify:** `pytest backend-microservices/ai-service-fastapi/tests/ --collect-only` → không có "creating directory" log. **15 phút.**

---

### S3-MIN-2-M15 · Test fixture env GATEWAY_SECRET

**Files:** `backend-microservices/*/tests/conftest.py` (auth, parking, booking, vehicle, ai, chatbot, notification, payment — 8 service)
**Triệu chứng:** Test hardcode `GATEWAY_SECRET = "gateway-internal-secret-key"` → khi S1-CRIT-2a làm fail-fast, test cũng phải đọc từ env.

**Fix — áp dụng cho mỗi `conftest.py`:**
```python
import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def gateway_secret_env():
    """Đặt GATEWAY_SECRET cho toàn bộ test session."""
    if not os.environ.get('GATEWAY_SECRET'):
        os.environ['GATEWAY_SECRET'] = 'test-gateway-secret-' + os.urandom(8).hex()
    yield
```

Grep tất cả chỗ hardcode cũ và xoá:
```bash
grep -rn "gateway-internal-secret-key" backend-microservices/*/tests/
# Với mỗi match, replace thành settings.GATEWAY_SECRET hoặc os.environ['GATEWAY_SECRET']
```

**Verify:** `pytest backend-microservices/` PASS với env `GATEWAY_SECRET` không set explicit (fixture tự inject). **1 giờ.**

---

### S3-MIN-2-M16 · Fix fallback hostname `realtime-service-go`

**File:** `backend-microservices/booking-service/bookings/views.py:27-29`
**Triệu chứng:** `os.environ.get('REALTIME_SERVICE_URL', 'http://realtime-service:8006')` — default hostname sai (thực tế là `realtime-service-go`).

**Fix:**
```python
# ❌ Trước
REALTIME_SERVICE_URL = os.environ.get('REALTIME_SERVICE_URL', 'http://realtime-service:8006')

# ✅ Sau — không default, fail-fast
REALTIME_SERVICE_URL = settings.REALTIME_SERVICE_URL  # đọc từ settings, fail nếu thiếu
```

Hoặc nếu vẫn muốn default:
```python
REALTIME_SERVICE_URL = os.environ.get('REALTIME_SERVICE_URL', 'http://realtime-service-go:8006')
```

**Verify:** `grep -rn "realtime-service:" backend-microservices/ --include="*.py" | grep -v "go"` → rỗng. **5 phút.**

## S3-MIN-3 · Unity Minor cluster (6 items)

**Scope:** `ParkingSimulatorUnity/Assets/Scripts/**`. Tổng thời gian ước tính: **~1.5 ngày**.

### S3-MIN-3-UM1 · Extract `DashboardUI` thành EventLogPanel + StatsPanel

**File:** `ParkingSimulatorUnity/Assets/Scripts/UI/DashboardUI.cs` (444 dòng — vượt 300-line limit)

**Fix:**
```
Assets/Scripts/UI/
├── DashboardUI.cs                 (~150 dòng — orchestrator, bind UI refs)
└── Dashboard/
    ├── EventLogPanel.cs           (~100 dòng — history scroll, event formatting)
    └── StatsPanel.cs              (~100 dòng — counters, live stats)
```

`DashboardUI.cs` chỉ còn ref chính:
```csharp
public class DashboardUI : MonoBehaviour
{
    [SerializeField] private EventLogPanel eventLog;
    [SerializeField] private StatsPanel stats;

    private void OnEnable()
    {
        ParkingManager.Instance.OnStatusMessage += eventLog.AppendEntry;
        ParkingManager.Instance.OnStatsUpdated += stats.Refresh;
    }
    // ... unsubscribe OnDisable
}
```

**Verify:**
```bash
wc -l ParkingSimulatorUnity/Assets/Scripts/UI/DashboardUI.cs
wc -l ParkingSimulatorUnity/Assets/Scripts/UI/Dashboard/*.cs
# Mỗi file < 300 dòng
```
Mở Unity Editor → Dashboard scene → Play → event log và stats vẫn hoạt động. **0.5 ngày.**

---

### S3-MIN-3-UM2 · Camera config → ScriptableObject

**File:** `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraManager.cs:73-175`
**Triệu chứng:** 7 camera hardcode position/rotation literal trong code.

**Fix:**

1. Tạo `Assets/Scripts/Camera/CameraConfigAsset.cs`:
```csharp
using UnityEngine;
using System.Collections.Generic;

[CreateAssetMenu(fileName = "VirtualCameraConfig", menuName = "ParkingSim/Virtual Camera Config")]
public class CameraConfigAsset : ScriptableObject
{
    [System.Serializable]
    public class CameraEntry
    {
        public string cameraId;
        public Vector3 position;
        public Vector3 rotation;
        public float fieldOfView = 60f;
        public float captureFps = 5f;
    }

    public List<CameraEntry> cameras = new();
}
```

2. Tạo asset: Unity Editor → Assets → Create → ParkingSim → Virtual Camera Config → điền 7 entry.

3. Rewrite `VirtualCameraManager.cs`:
```csharp
[SerializeField] private CameraConfigAsset config;

private void SetupCameras()
{
    foreach (var entry in config.cameras)
    {
        var cam = CreateCamera(entry.cameraId);
        cam.transform.localPosition = entry.position;
        cam.transform.localEulerAngles = entry.rotation;
        cam.fieldOfView = entry.fieldOfView;
    }
}
```

**Verify:** Play scene → các camera vẫn ở đúng vị trí. Thay đổi FOV trong asset → thấy update runtime. **1 giờ.**

---

### S3-MIN-3-UM3 · Log level system verbose/production

**Files:** `ParkingManager.cs`, `ESP32Simulator.cs` (+ các file khác dùng `Debug.Log` tùy tiện)
**Triệu chứng:** Debug log rải rác, không có toggle → spam console khi demo.

**Fix:**

1. Tạo `Assets/Scripts/Utility/SimLogger.cs`:
```csharp
using UnityEngine;

public enum LogLevel { None, Error, Warning, Info, Verbose }

public static class SimLogger
{
    public static LogLevel Level = LogLevel.Info;

    public static void Verbose(string tag, string msg)
    {
        if (Level >= LogLevel.Verbose) Debug.Log($"[{tag}] {msg}");
    }
    public static void Info(string tag, string msg)
    {
        if (Level >= LogLevel.Info) Debug.Log($"[{tag}] {msg}");
    }
    public static void Warn(string tag, string msg)
    {
        if (Level >= LogLevel.Warning) Debug.LogWarning($"[{tag}] {msg}");
    }
    public static void Error(string tag, string msg)
    {
        if (Level >= LogLevel.Error) Debug.LogError($"[{tag}] {msg}");
    }
}
```

2. Replace `Debug.Log(...)` trong các file scripts:
```bash
# Grep và thay thế từng chỗ
grep -rn "Debug.Log" ParkingSimulatorUnity/Assets/Scripts/ --include="*.cs"
```

3. Set level dựa vào config trong `ParkingManager.Awake()`:
```csharp
SimLogger.Level = config.isVerbose ? LogLevel.Verbose : LogLevel.Info;
```

**Verify:** Unity Editor Play mode → toggle `isVerbose` ở ApiConfig → console log thưa/đặc tương ứng. **0.5 ngày.**

---

### S3-MIN-3-UM4 · Truncate AI body log

**File:** `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs:84-127`
**Triệu chứng:** Log body request/response AI (chứa base64 JPG frames ~200KB) spam Editor console.

**Fix:**
```csharp
// ❌ Trước
Debug.Log($"[ApiService] POST {url} body={bodyJson}");

// ✅ Sau — truncate body > 500 ký tự
private const int MaxLogBodyLength = 500;

private string TruncateForLog(string body)
{
    if (string.IsNullOrEmpty(body)) return body;
    return body.Length <= MaxLogBodyLength
        ? body
        : body.Substring(0, MaxLogBodyLength) + $"... ({body.Length} chars)";
}

SimLogger.Verbose("ApiService", $"POST {url} body={TruncateForLog(bodyJson)}");
```

**Verify:** Upload frame qua Unity → console log chỉ thấy preview 500 ký tự + tổng length. **15 phút.**

---

### S3-MIN-3-UM5 · Dual-cookie parsing CSRF + session

**File:** `ParkingSimulatorUnity/Assets/Scripts/API/AuthManager.cs:60`
**Triệu chứng:** Django dual-cookie response (CSRF + session) nhưng code chỉ lấy cookie đầu tiên.

**Fix:**
```csharp
// ❌ Trước
string rawCookie = response.GetResponseHeader("Set-Cookie");
sessionCookie = rawCookie.Split(';')[0].Trim();  // chỉ cookie 1

// ✅ Sau — parse tất cả Set-Cookie headers
var headers = request.GetResponseHeaders();
var cookies = new Dictionary<string, string>();

// UnityWebRequest trả headers là Dictionary, Set-Cookie có thể là multi-value
// Dùng regex để extract từng cookie
if (headers.TryGetValue("Set-Cookie", out var rawCookies))
{
    var matches = System.Text.RegularExpressions.Regex.Matches(
        rawCookies, @"([^=\s;]+)=([^;]+)(?:;|$)");
    foreach (System.Text.RegularExpressions.Match m in matches)
    {
        cookies[m.Groups[1].Value] = m.Groups[2].Value;
    }
}

if (cookies.TryGetValue("sessionid", out var sid)) sessionCookie = sid;
if (cookies.TryGetValue("csrftoken", out var csrf)) csrfToken = csrf;
```

**Verify:** Login flow Unity → cả `sessionCookie` và `csrfToken` đều có giá trị không null. Subsequent POST request có thể include cả 2. **30 phút.**

---

### S3-MIN-3-UM6 · Extract `MockResponder` strategy

**File:** `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs:165-189`
**Triệu chứng:** Mỗi method có `if (config.useMockData) return mockData;` inline, lặp 10+ lần.

**Fix:**
```csharp
// Assets/Scripts/API/MockResponder.cs
public interface IMockResponder
{
    bool TryGetMock<T>(string endpoint, out T response);
}

public class MockResponder : IMockResponder
{
    private readonly MockDataProvider provider;

    public MockResponder(MockDataProvider p) { provider = p; }

    public bool TryGetMock<T>(string endpoint, out T response)
    {
        response = default;
        if (!provider.Enabled) return false;

        // Map endpoint → mock data
        switch (endpoint)
        {
            case "/parking/lots/":
                if (typeof(T) == typeof(List<ParkingLot>))
                {
                    response = (T)(object)provider.GetLots();
                    return true;
                }
                break;
            // ... thêm case khác
        }
        return false;
    }
}
```

Refactor `ApiService`:
```csharp
public IEnumerator GetLots(Action<List<ParkingLot>> onComplete)
{
    if (mockResponder.TryGetMock<List<ParkingLot>>("/parking/lots/", out var mock))
    {
        onComplete(mock);
        yield break;
    }
    // ... real HTTP call
}
```

**Verify:** Toggle `useMockData` trong ApiConfig → Play mode → simulator vẫn có data (không phụ thuộc backend). **1 giờ.**

## S3-DEAD · Dead code sweep (21 nhóm)

**Scope:** Toàn repo. Tổng thời gian: **~1 ngày**. Hầu hết là xoá file/folder + update `.gitignore`.

### Các mục đã được fix ở sprint trước (chỉ verify)

| ID | Artifact | Fix tại |
|---|---|---|
| D1 | `parking-service/infrastructure/views.py:491-494` duplicate block | S1-CRIT-1 ✅ |
| D2 | `BookingViewSet.booking_stats` duplicate | S3-MIN-2-M1 |
| D3 | `BookingViewSet._get_hourly_price` duplicate | S3-MIN-2-M2 |
| D4 | `BookingViewSet.current` vs `current_parking` consolidate | S2-IMP-4 |
| D5 | `BookingViewSet.payment` vs `initiate_payment` consolidate | S2-IMP-4 |
| D6 | `esp32.py::_parse_qr_data / _capture_plate_image / _get_test_image_bytes` | S2-IMP-5 ✅ |
| D9 | `backend-microservices/cookies_test.txt` | S1-CRIT-10 ✅ |

**Verify bằng 1 lệnh:**
```bash
# D1: file parses
python -c "import ast; ast.parse(open('backend-microservices/parking-service/infrastructure/views.py').read())"

# D2-D5: grep không còn method cũ
grep -n "def booking_stats\|def _get_hourly_price\|def current_parking" backend-microservices/booking-service/bookings/views.py
# Chỉ nên trả về định nghĩa mới (nếu có), không phải code cũ

# D6: grep không còn helper cũ
grep -rn "_parse_qr_data\|_capture_plate_image\|_get_test_image_bytes" backend-microservices/ai-service-fastapi/app/routers/esp32.py

# D9: cookie file không còn
find . -name "cookies*.txt" -not -path "*/node_modules/*"
```

---

### Các mục mới cần fix ở Sprint 3

### S3-DEAD-D7 · Stale pipaudit JSON

**Status:** Được fix một phần ở S2-IMP-13 (archive + CI refresh). Verify lại:
```bash
ls docs/notes/*.json  # chỉ còn file MỚI từ CI, cũ đã archive vào docs/notes/archive/
ls docs/notes/archive/2026-03-13/  # 10 file cũ đã ở đây
```

### S3-DEAD-D8 · Log files root + backend

```bash
# Grep log files
find backend-microservices/logs -name "*.txt" -o -name "*.log" 2>/dev/null

# Gitignore
cat >> .gitignore <<'EOF'

# Backend logs
backend-microservices/logs/*.txt
backend-microservices/logs/*.log
EOF

# Untrack nếu đang tracked
git rm --cached backend-microservices/logs/*.txt 2>/dev/null || true
git rm --cached backend-microservices/logs/*.log 2>/dev/null || true
```

**Verify:** `git status --ignored backend-microservices/logs/` → các file là ignored. **10 phút.**

### S3-DEAD-D10 · Unity `Assets/Tests 1/` space folder

**Triệu chứng:** Folder tên có space — brittle trên một số filesystem, và là auto-generated Unity Test Runner stub.

```bash
# Verify không có test thật
find "ParkingSimulatorUnity/Assets/Tests 1" -name "*.cs" -exec grep -l "\[Test\]" {} \;
# Nếu rỗng → an toàn xoá
rm -rf "ParkingSimulatorUnity/Assets/Tests 1"
rm -f "ParkingSimulatorUnity/Assets/Tests 1.meta"
```

Unity Editor: Refresh → không còn folder trong Project view. **5 phút.**

### S3-DEAD-D11 · `MockDataProvider.GenerateMockESP32Devices()`

**File:** `ParkingSimulatorUnity/Assets/Scripts/*/MockDataProvider.cs` (grep xác định đúng path)

```bash
grep -rn "GenerateMockESP32Devices" ParkingSimulatorUnity/Assets/Scripts/
# Xoá method, verify không có caller
grep -rn "GenerateMockESP32Devices" ParkingSimulatorUnity/Assets/Scripts/
# Lần 2 phải rỗng sau khi xoá
```

**10 phút.**

### S3-DEAD-D12 · `DataModels.cs` 5 unused DTO

**File:** `ParkingSimulatorUnity/Assets/Scripts/API/DataModels.cs:29, 43, 381, 390, 399`

```bash
# List class/struct names ở các dòng cụ thể
sed -n '27,45p;379,402p' ParkingSimulatorUnity/Assets/Scripts/API/DataModels.cs
# Grep từng class name để verify no caller
for name in UnusedDTO1 UnusedDTO2 UnusedDTO3 UnusedDTO4 UnusedDTO5; do
  grep -rn "$name" ParkingSimulatorUnity/Assets/Scripts/ --include="*.cs"
done
```

Xoá 5 class chưa có caller. **15 phút.**

### S3-DEAD-D13 · Consolidate `GetParkingLotDetail` / `GetParkingLotFullInfo`

**File:** `ParkingSimulatorUnity/Assets/Scripts/API/ApiService.cs:152, 157`

Hai method trả về data gần giống nhau (từ cùng endpoint). Gộp thành 1 với optional parameter:
```csharp
public IEnumerator GetParkingLot(
    string lotId,
    bool includeFloors = false,
    Action<ParkingLot> onComplete = null)
{
    string url = $"/parking/lots/{lotId}/";
    if (includeFloors) url += "?include=floors,zones,slots";
    // ... single HTTP call
}
```

Grep caller và update. **15 phút.**

### S3-DEAD-D14 · QR PNG/SVG files repo root

```bash
# Liệt kê
ls booking-qr-*.png booking_qr_*.svg 2>/dev/null

# Xoá
rm -f booking-qr-*.png booking_qr_*.svg

# Verify .gitignore đã có pattern
grep -E "booking-qr\*\.png|booking_qr_\*\.svg" .gitignore
```

Nếu chưa có:
```bash
cat >> .gitignore <<'EOF'

# Generated QR artifacts
booking-qr-*.png
booking_qr_*.svg
EOF
```
**5 phút.**

### S3-DEAD-D15 · `test.json` root

```bash
ls test.json 2>/dev/null && rm -f test.json
```
Verify: `git status` không còn. **2 phút.**

### S3-DEAD-D16 · Commented-out endpoints

**File:** `spotlove-ai/src/services/api/endpoints.ts` — 4 block commented-out:
- Dòng 22-27
- Dòng 118-127
- Dòng 131-140
- Dòng 169-179

**Fix:**
1. Đọc từng block, confirm đúng là commented code không phải docstring hữu ích.
2. Xoá toàn bộ 4 block.
3. Nếu cần tham chiếu cho roadmap, paste vào `docs/plans/fe-endpoints-roadmap.md`.

```bash
# Verify dòng ~40 commented-out code còn lại
grep -c "^//" spotlove-ai/src/services/api/endpoints.ts
# Expected < 5 dòng (chỉ giữ license header comment hoặc giải thích ngắn)
```

**15 phút.**

### S3-DEAD-D17 · Cloudflare tunnel config hardcoded Windows path

**File:** `infra/cloudflare/cloudflared/config.yml:15`
**Triệu chứng:** `credentials-file: C:\Users\MINH\.cloudflared\57eb6de9-...json` — Windows-specific + tunnel UUID committed.

**Fix:**

1. Tạo `infra/cloudflare/cloudflared/config.example.yml`:
```yaml
tunnel: ${CF_TUNNEL_ID}
credentials-file: ${CF_TUNNEL_CREDENTIALS_FILE}

ingress:
  - hostname: api.ghepdoicaulong.shop
    service: http://localhost:8000
  - hostname: app.ghepdoicaulong.shop
    service: http://localhost:5173
  - service: http_status:404
```

2. Update `infra/cloudflare/cloudflared/config.yml` để đọc env (nếu cloudflared hỗ trợ substitution) hoặc:
- Tạo script `infra/cloudflare/cloudflared/render-config.sh` để generate `config.yml` từ template + env vars runtime.

3. Add `infra/cloudflare/cloudflared/config.yml` vào `.gitignore`:
```bash
echo "infra/cloudflare/cloudflared/config.yml" >> .gitignore
git rm --cached infra/cloudflare/cloudflared/config.yml
```

**Verify:** Clone repo sạch, chạy script render → tạo được config.yml hợp lệ với env của máy khác. **30 phút.**

### S3-DEAD-D18 · `booking_for_unity*.json` root

```bash
ls booking_for_unity*.json 2>/dev/null
rm -f booking_for_unity*.json

cat >> .gitignore <<'EOF'

# Unity integration test artifacts
booking_for_unity*.json
EOF
```
**5 phút.**

### S3-DEAD-D19 · `test_e2e_results.json` root

```bash
rm -f test_e2e_results.json backend-microservices/test_e2e_results.json

echo "test_e2e_results.json" >> .gitignore
echo "backend-microservices/test_e2e_results.json" >> .gitignore
```
**5 phút.**

### S3-DEAD-D20 · Seed scripts — KHÔNG xoá

**Files:**
- `backend-microservices/seed_unity_slots.py`
- `backend-microservices/seed_unity_test_data.py`

**Status:** Active — dùng cho S1-CRIT-4b + CLAUDE.md documented. **Không xoá**, chỉ verify có docstring rõ ràng ở đầu file:

```python
"""
Seed Unity simulator test data.

Usage:
    python seed_unity_test_data.py

Prerequisites:
    - Backend stack đang chạy (docker compose up -d)
    - GATEWAY_SECRET set trong .env

Seeds:
    - 1 parking lot "ParkSmart Tower"
    - 158 slots (4 floors × ~40 slots)
    - ESP32 devices cho gate vào/ra
"""
```

Nếu thiếu docstring, thêm vào. **10 phút.**

### S3-DEAD-D21 · `.local-backups/` + `test-logs/` folders

```bash
ls -la .local-backups test-logs 2>/dev/null

# Gitignore
cat >> .gitignore <<'EOF'

# Local dev artifacts
.local-backups/
test-logs/
EOF

# Untrack
git rm -r --cached .local-backups test-logs 2>/dev/null || true
```

Verify: `git status --ignored` list 2 folder. **5 phút.**

## S3-DOCS · Đồng bộ docs

**Scope:** Tất cả file markdown trong `docs/` và `.github/`. Tổng thời gian: **~2.5 giờ**.

### S3-DOCS-1 · Update `CLAUDE.md` sau refactor layering

**File:** `CLAUDE.md`
**Áp dụng khi:** S2-IMP-9 đã refactor 25-28 pages FE về đúng `services/business/*` layering — cần update section "Frontend architecture" trong CLAUDE.md để phản ánh state mới.

**Fix:**
1. Mở `CLAUDE.md` section "5. Frontend architecture — `spotlove-ai/src/`".
2. Update phần nói về layering để nhấn mạnh "đã được enforce ở Sprint 2".
3. Thêm note về TypeScript strict đã bật (nếu đã hoàn thành phase-in 3 sprint).
4. Update section "Code graph hotspots" — bỏ các god class đã được refactor (BookingViewSet, esp32.py, orchestrator.py).

**Verify:** `CLAUDE.md` đọc nhất quán với state hiện tại, không còn chỗ nào nói "KHÔNG được grow" về các file đã refactor. **15 phút.**

---

### S3-DOCS-2 · Sửa `auth-service/README.md` — bỏ Postgres + JWT refresh

**File:** `backend-microservices/auth-service/README.md`
**Triệu chứng:** README hiện tại nói `DATABASE_URL=postgresql://...` và `JWT_REFRESH_TOKEN_LIFETIME` — cả hai đều **sai** so với runtime thực tế (MySQL + session cookie, không có refresh token endpoint).

**Fix:** Rewrite section "Environment Variables":
```markdown
## Environment Variables

```
SECRET_KEY=<django-secret>
DB_HOST=mysql
DB_PORT=3306
DB_USER=<mysql-user>
DB_PASSWORD=<mysql-password>
REDIS_URL=redis://redis:6379/1
GATEWAY_SECRET=<shared-secret-with-gateway>
GOOGLE_CLIENT_ID=<google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<google-oauth-secret>
FACEBOOK_APP_ID=<facebook-app-id>
FACEBOOK_APP_SECRET=<facebook-app-secret>
```

**Auth Contract:**
- Session cookie-based (KHÔNG có JWT refresh token endpoint).
- Routes `/auth/refresh/`, `/auth/token/refresh/` KHÔNG thuộc contract.
```

**Verify:** Grep `postgresql\|JWT_REFRESH\|JWT_ACCESS_TOKEN_LIFETIME` trong README → rỗng. **15 phút.**

---

### S3-DOCS-3 · Update `docs/status.yaml`

**File:** `docs/status.yaml`
**Triệu chứng:** Blocker cũ `SECURITY-BLOCKERS-2026-03-13` vẫn ở state `blocked` mặc dù đã một phần được giải quyết ở Sprint 1-2.

**Fix:** Append entry mới phản ánh sprint hiện tại:
```yaml
task:
  id: "FIX-PIPELINE-SPRINT-1-2-3"
  title: "Full remediation after 2026-04-15 code review"
  pipeline: "FULL"
  state: "done"  # khi cả 3 sprint hoàn tất
  started_at: "2026-04-15T00:00:00Z"
  updated_at: "2026-XX-XXTXX:XX:XXZ"
  source_plan: "docs/plans/FULL-REVIEW-FIX-PLAN-2026-04-15.md"
  prev_task: "SECURITY-BLOCKERS-2026-03-13"
```

Close blocker cũ:
```yaml
# SECURITY-BLOCKERS-2026-03-13 section
state: "resolved"
resolved_at: "2026-XX-XX"
resolution: "See FIX-PIPELINE-SPRINT-1-2-3 — Cloudflare tunnel config fixed in S3-DEAD-D17"
```

**Verify:** `python -c "import yaml; yaml.safe_load(open('docs/status.yaml'))"` PASS (valid YAML). **10 phút.**

---

### S3-DOCS-4 · Archive outdated Cloudflare deploy runbook

**File:** `docs/notes/cloudflare-deploy-runbook.md`
**Áp dụng khi:** Runbook cũ tham chiếu đến `<TUNNEL_ID_PLACEHOLDER>` không còn relevant sau S3-DEAD-D17.

**Fix:**
```bash
mkdir -p docs/notes/archive
git mv docs/notes/cloudflare-deploy-runbook.md docs/notes/archive/cloudflare-deploy-runbook-2026-03-13.md
```

Viết lại một runbook mới tại `docs/notes/cloudflare-deploy-runbook.md` phản ánh workflow env-driven:
```markdown
# Cloudflare Deploy Runbook (2026-04)

## Prerequisites
- `CF_TUNNEL_ID` và `CF_TUNNEL_CREDENTIALS_FILE` set trong `.env`
- GitHub Secrets: `CF_API_TOKEN`, `CF_ACCOUNT_ID`, `CF_PAGES_PROJECT`

## Steps
1. Render `config.yml` từ template: `bash infra/cloudflare/cloudflared/render-config.sh`
2. Start tunnel: `cloudflared tunnel run ${CF_TUNNEL_ID}`
3. Deploy Pages: trigger workflow `deploy-cloudflare-pages.yml`
```

**Verify:** Runbook mới chạy end-to-end từ máy sạch. **15 phút.**

---

### S3-DOCS-5 · Post-sprint review report

**File:** `docs/reviews/sprint-execution-report-<date>.md` (tạo mới khi Sprint 3 kết thúc)

**Template:**
```markdown
# Sprint Execution Report — FIX PIPELINE 2026-04

**Plan nguồn:** `docs/plans/FULL-REVIEW-FIX-PLAN-2026-04-15.md`
**Execution start:** <YYYY-MM-DD>
**Execution end:** <YYYY-MM-DD>
**Branch:** `fix/sprint-1-stability-security`, `fix/sprint-2-scale-maintain`, `fix/sprint-3-cleanup-polish`

## Sprint 1 — Stability + Security
- Tasks completed: X/12 Critical
- Total commits: X
- Duration actual: X ngày (plan: 7-10)
- Issues encountered:
- Deviations from plan:

## Sprint 2 — Scale + Maintain
...

## Sprint 3 — Cleanup + Polish
...

## Metrics
- Lines changed: +X / -Y
- Files touched: X
- Test coverage delta: +X%
- Bundle size delta: -X% (FE)
- Backend p99 latency delta: -X%

## Lessons learned
...

## Follow-ups (out of scope for this pipeline)
...
```

**Verify:** File tạo xong + commit trong Sprint 3 cuối cùng. **1 giờ.**

---

### S3-DOCS-6 · Update `.github/copilot-instructions.md`

**File:** `.github/copilot-instructions.md`
**Áp dụng khi:** Có convention mới phát sinh trong quá trình fix (ví dụ: fail-fast pattern cho secret, contract-first cho DTO, TypeScript strict mode).

**Fix:** Thêm vào section tương ứng:
```markdown
## Additional conventions (post 2026-04 fix pipeline)

### Secret management
- NEVER default fallback cho secret — dùng `config('KEY')` hoặc `mustGetEnv("KEY")` fail-fast.
- Test fixtures đọc secret từ env, không hardcode literal.

### TypeScript strict
- `tsconfig.app.json` ENFORCE `strict: true`, `noImplicitAny: true`, `strictNullChecks: true`.
- Không dùng `@ts-ignore`; chỉ `@ts-expect-error — TODO(issue-#XXX): ...`.

### FE layering
- Pages và components CHỈ import từ `services/business/*`, KHÔNG từ `services/api/*` trực tiếp.
- Redux slices import từ `services/business/*`, không tự gọi `services/api/*`.
```

**Verify:** Đọc instructions mới nhất quán với CLAUDE.md. **15 phút.**

---

## S3-POLISH · Production readiness

**Scope:** `scripts/`, `infra/`, CI/CD. Tổng thời gian: **~1-5 ngày** (tùy scope).

### S3-POLISH-1 · Bash variant của `deploy-local.ps1`

**File:** `scripts/deploy-local.ps1` (433 dòng PowerShell, Windows-only)
**Mục tiêu:** Port sang `scripts/deploy-local.sh` để chạy trên Linux/macOS CI.

**Steps:**
1. Đọc `deploy-local.ps1`, liệt kê các step (typical):
   - Check env file
   - `docker compose build`
   - `docker compose up -d`
   - Health check các service
   - Seed data
   - Start Cloudflare tunnel (optional)

2. Viết `scripts/deploy-local.sh` bash equivalent:
```bash
#!/usr/bin/env bash
set -euo pipefail

SKIP_BUILD=${SKIP_BUILD:-0}
SKIP_DOCKER=${SKIP_DOCKER:-0}
SKIP_TUNNEL=${SKIP_TUNNEL:-0}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend-microservices"

if [ ! -f .env ]; then
  echo "ERROR: .env file not found" >&2
  exit 1
fi

if [ "$SKIP_DOCKER" = "0" ]; then
  if [ "$SKIP_BUILD" = "0" ]; then
    docker compose build
  fi
  docker compose up -d
fi

# Wait for services
sleep 30
for svc in mysql:3307 redis:6379 gateway:8000; do
  host="${svc%:*}"; port="${svc#*:}"
  timeout 60 bash -c "until nc -z localhost $port; do sleep 1; done"
  echo "✅ $svc ready"
done

# Seed data
python seed_e2e_data.py
python seed_unity_test_data.py

# Optional: start tunnel
if [ "$SKIP_TUNNEL" = "0" ] && [ -n "${CF_TUNNEL_ID:-}" ]; then
  cloudflared tunnel run "$CF_TUNNEL_ID" &
fi

echo "✅ Deploy complete"
```

3. Alternative: dùng `Makefile` với targets `make up`, `make down`, `make seed`, `make tunnel` — portable hơn PS1.

**Verify:** `bash scripts/deploy-local.sh` trên Linux CI → stack boot PASS. **1 ngày.**

---

### S3-POLISH-2 · Cloudflare tunnel config qua env

**Status:** Đã được cover ở **S3-DEAD-D17** — tạo `config.example.yml` + render script. Nếu chưa làm, apply tại đây. **30 phút.**

---

### S3-POLISH-3 · K8s/Nomad manifests (optional)

**Mục tiêu:** Port từ docker-compose sang K8s manifests để deploy production. **Optional** — chỉ làm nếu thesis hoặc deliverable yêu cầu.

**Structure:**
```
infra/k8s/
├── namespace.yaml
├── configmaps/
│   └── app-config.yaml
├── secrets/
│   └── app-secrets.yaml        # dùng sealed-secrets hoặc external-secrets
├── deployments/
│   ├── mysql.yaml
│   ├── redis.yaml
│   ├── rabbitmq.yaml
│   ├── auth-service.yaml
│   ├── booking-service.yaml
│   ├── ... (9 services)
│   └── ai-service-fastapi.yaml
├── services/
│   └── ... (ClusterIP cho internal, LoadBalancer cho gateway)
└── ingress/
    └── ingress.yaml             # Cloudflare Tunnel hoặc nginx-ingress
```

Mỗi `deployment.yaml` tương đương 1 service trong `docker-compose.yml`:
- Replicas: 1-3 tùy service
- Resource limits: memory 256Mi-2Gi, CPU 100m-1000m (AI service cần nhiều hơn)
- Env từ ConfigMap + Secret
- Health + readiness probes

**Verify:** `kubectl apply -f infra/k8s/` trên local minikube/kind → `kubectl get pods` tất cả Running. **2 ngày.**

---

### S3-POLISH-4 · Grafana/Prometheus observability (optional)

**Mục tiêu:** Metrics endpoint mỗi service + dashboard.

**Steps:**

1. Thêm `prometheus_client` vào Python services:
```python
# backend-microservices/shared/metrics.py
from prometheus_client import Counter, Histogram, generate_latest

requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

def metrics_endpoint():
    return generate_latest()
```

Mount endpoint `/metrics` trong mỗi service.

2. Thêm Prometheus scrape config:
```yaml
# infra/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'parksmart-services'
    static_configs:
      - targets:
          - 'auth-service:8000'
          - 'booking-service:8000'
          - 'parking-service:8000'
          - 'ai-service-fastapi:8009'
          - 'gateway-service-go:8000'
    metrics_path: /metrics
```

3. Add Prometheus + Grafana containers vào `docker-compose.yml`:
```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:?required}
```

4. Import dashboard JSON cho mỗi service (có thể dùng template từ [grafana.com/grafana/dashboards](https://grafana.com/grafana/dashboards) — search "FastAPI" hoặc "Django").

**Verify:** Mở `localhost:3000` → Grafana UI → dashboard hiển thị metrics real-time. **1-2 ngày.**

---

# VERIFICATION MATRIX — Gate thoát mỗi sprint

## Gate thoát Sprint 1
- [ ] `parking-service` boot khoẻ (S1-CRIT-1)
- [ ] `grep -rn "gateway-internal-secret-key" backend-microservices/` → không match source (S1-CRIT-2a)
- [ ] `grep -rn "gw-prod-" spotlove-ai/` → không match source (S1-CRIT-2b)
- [ ] Secret Cloudflare + GitHub đã rotate
- [ ] `curl http://localhost:8001/admin/` → không phải 200 Django admin HTML (S1-CRIT-3)
- [ ] `curl -X POST .../esp32/check-in/` without token → 401 (S1-CRIT-4)
- [ ] Concurrent booking test chỉ 1 thành công (S1-CRIT-5)
- [ ] Production cookie có `Secure; HttpOnly; SameSite=None; Domain=.ghepdoicaulong.shop` (S1-CRIT-6)
- [ ] CORS OPTIONS từ prod domain → allow (S1-CRIT-7)
- [ ] FE prod build không chứa credentials trong dist/ (S1-CRIT-8)
- [ ] `npm run typecheck` → 0 errors (S1-CRIT-9)
- [ ] Gateway healthcheck trong `docker compose ps` → healthy (S1-CRIT-10)
- [ ] `docker compose exec auth-service whoami` → `app` (S1-CRIT-11)
- [ ] AI service 5 concurrent requests p99 < 10s (S1-CRIT-12)
- [ ] Playwright `npm run e2e` 5/5 PASS
- [ ] Backend pytest tất cả service PASS
- [ ] Go test `gateway-service-go`, `realtime-service-go` PASS
- [ ] Không regression test nào

## Gate thoát Sprint 2
- [ ] `/bookings/?limit=100` response time < 500ms (S2-IMP-1)
- [ ] Checkin latency không phụ thuộc realtime-service (stop → vẫn fast) (S2-IMP-2)
- [ ] Gateway load test 10k req 100 concurrent p99 < 100ms (S2-IMP-3)
- [ ] `wc -l` mọi file Python < 500 dòng (trừ auto-generated) (S2-IMP-4..7)
- [ ] `wc -l` mọi `.tsx` page < 600 dòng (S2-IMP-9)
- [ ] `wc -l` Unity script < 400 dòng (S2-IMP-10..11)
- [ ] Không có `grep 'from.*services/api' src/pages/ src/components/` ngoài `src/services/business/` (S2-IMP-9)
- [ ] FE bundle initial JS < 400kB gzipped (S2-IMP-8)
- [ ] `npm run build` không warning chunk > 500kB
- [ ] Pipaudit CI GREEN weekly (S2-IMP-13)
- [ ] Zod parse mọi API response, không còn `as unknown as X`

## Gate thoát Sprint 3
- [ ] Không dead deps trong `package.json`
- [ ] Không commented-out code > 10 dòng (`grep -rn "^// TODO\|^/\*" src/` spot check)
- [ ] Không `backend-microservices/test_*.py` root confuse pytest
- [ ] `.gitignore` cover mọi local/credential files
- [ ] `docs/` không có `.bak`, `*-old-*`, stale artifact
- [ ] `CLAUDE.md` phản ánh đúng state hiện tại
- [ ] Sprint review docs viết xong

---

# REGRESSION TEST CHECKLIST — Ship kèm mỗi fix

Mỗi task CRIT/IMP phải ship **tối thiểu 1 regression test**. Không test = task chưa done.

## Sprint 1

| Task | Test file | Test case |
|---|---|---|
| S1-CRIT-1 | `parking-service/tests/test_smoke.py` | `test_views_py_parses()` — `ast.parse` file + `manage.py check` |
| S1-CRIT-2a | `*/tests/test_config.py` | `test_gateway_secret_required()` — `monkeypatch.delenv("GATEWAY_SECRET")` → `ImportError`/`ValidationError` |
| S1-CRIT-2b | `spotlove-ai/e2e/global-setup.spec.ts` | `test("E2E_GATEWAY_SECRET từ env")` — không hardcode |
| S1-CRIT-3 | `auth-service/tests/test_admin_disabled.py` | `test_admin_route_404()` — `GET /admin/` → 404 |
| S1-CRIT-4a | `ai-service-fastapi/tests/test_esp32_auth.py` | `test_missing_token_403()`, `test_wrong_token_403()`, `test_correct_token_passes()` |
| S1-CRIT-4b | `ParkingSim.Tests.PlayMode/ESP32SimulatorTests.cs` | `TestESP32RequestIncludesDeviceToken()` — verify UnityWebRequest header |
| S1-CRIT-5 | `booking-service/tests/test_booking_race.py` | `test_no_double_booking_under_concurrency()` — 10 threads, 1 thành công |
| S1-CRIT-6 | manual curl + deploy verify | Cookie flags `Secure; HttpOnly; SameSite=None; Domain=.ghepdoicaulong.shop` |
| S1-CRIT-7 | `ai-service-fastapi/tests/test_cors.py` | `test_cors_production_origin()` + `test_cors_localhost_dev()` |
| S1-CRIT-8 | `spotlove-ai/src/test/webLogger-redact.test.ts` | `test_password_redacted()`, `test_prod_noop()` |
| S1-CRIT-9 | CI `npm run typecheck` | Phase 1: 0 errors với `noImplicitAny` |
| S1-CRIT-10 | `docker compose ps` verify | Gateway healthcheck report `healthy` |
| S1-CRIT-11 | `docker compose exec <svc> whoami` | Return `app` không phải `root` |
| S1-CRIT-12 | Load test script | 5 concurrent scan-plate p99 < 10s |

## Sprint 2

| Task | Test file | Test case |
|---|---|---|
| S2-IMP-1 | `booking-service/tests/test_serializer_perf.py` | `test_list_100_bookings_no_http()` — mock `requests.get` → `call_count == 0` |
| S2-IMP-1 | `booking-service/tests/test_backfill.py` | `test_backfill_command_dry_run()`, `test_backfill_idempotent()` |
| S2-IMP-2 | `booking-service/tests/test_outbox.py` | `test_checkin_creates_outbox_event()`, `test_publish_outbox_retries_on_error()`, `test_dead_letter_after_5_failures()` |
| S2-IMP-2 | `parking-service/tests/test_consumer.py` | `test_dedup_processed_event()` — same event_id 2 lần → chỉ process 1 |
| S2-IMP-3 | `gateway-service-go/internal/handler/proxy_test.go` | `TestProxyReusesTransport()`, `TestProxyErrorHandlerJSON()` |
| S2-IMP-4 | `booking-service/tests/test_viewset.py` | Smoke test mọi endpoint sau tách ViewSet |
| S2-IMP-5 | `ai-service-fastapi/tests/test_esp32_flows.py` | 4 flow: checkin, checkout, barrier, cash_payment — happy path mỗi flow |
| S2-IMP-6 | `ai-service-fastapi/tests/test_parking_routes.py` | Scan-plate, check-in, check-out resolve đúng sau tách |
| S2-IMP-7 | `chatbot-service-fastapi/tests/test_intent_strategies.py` | `test_all_16_intents_have_strategy()`, `test_orchestrator_pipeline_order()` |
| S2-IMP-8 | `spotlove-ai/e2e/performance.spec.ts` | `test_initial_bundle_under_400kb()` — read dist manifest |
| S2-IMP-9 | CI grep check | `grep -rn "from.*services/api" src/pages/ src/components/` → rỗng |
| S2-IMP-10 | `ParkingSim.Tests.EditMode/ParkingManagerTests.cs` | `TestBootstrapResolvesDependencies()`, `TestDataSyncLoginWithTimeout()` |
| S2-IMP-11 | `ParkingSim.Tests.PlayMode/PollFallbackTests.cs` | `TestPollStopsWhenWebSocketConnected()` — mock WS connect event, verify PollSlotsCoroutine skip fetch |
| S2-IMP-12 | Unity profiler | `VirtualCameraStreamer` no main-thread block > 16ms (dùng `Profiler.BeginSample` + CSV export) |
| S2-IMP-13 | CI pipeline | `.github/workflows/ci.yml` có job `security-audit` chạy mỗi tuần; fail nếu có HIGH/CRITICAL vuln |

## Sprint 3

| Task | Test file / Command | Test case |
|---|---|---|
| S3-MIN-1-M1 (React Query) | `spotlove-ai/src/test/query-client-config.test.ts` | `test("staleTime default = 30000ms")` — tạo QueryClient mới, assert `defaultOptions.queries.staleTime` |
| S3-MIN-1-M2 (AdminStats) | `spotlove-ai/e2e/admin-stats.spec.ts` (nếu wire-up) | `test("admin/stats renders")` — navigate page, assert heading visible |
| S3-MIN-1-M4 (authSlice cache) | `spotlove-ai/src/test/authSlice.test.ts` | `test("getUserFromCookie called once in initialState")` — spy on `getUserFromCookie`, assert call_count = 1 |
| S3-MIN-1-M5 (axios metadata) | `spotlove-ai/src/test/axios-client.test.ts` | `test("config.metadata.startTime set")` — mock adapter, capture config, assert metadata field exists |
| S3-MIN-1-M8 (BookingPage perf) | React DevTools Profiler | Manual: so sánh "Commits per interaction" trước/sau — giảm ≥ 30% |
| S3-MIN-2-M1 (booking_stats) | `booking-service/tests/test_booking_stats.py` | `test("booking_stats delegates to services.get_user_stats")` — mock `services.get_user_stats`, assert called |
| S3-MIN-2-M2 (_get_hourly_price) | `booking-service/tests/test_pricing.py` | `test("no duplicate pricing logic")` — grep `_get_hourly_price` → 0 match |
| S3-MIN-2-M3 (verify_payment) | `booking-service/tests/test_verify_payment.py` | `test_verify_fake_transaction_returns_400()`, `test_verify_valid_transaction_returns_200()` — mock payment-service response |
| S3-MIN-2-M4 (PAYMENT_METHOD_MAP) | `booking-service/tests/test_services.py` | `test("online maps to e_wallet not cash")` — assert `_PAYMENT_METHOD_MAP['online'] == 'e_wallet'` |
| S3-MIN-2-M6 (gofmt) | CI check | `gofmt -l backend-microservices/gateway-service-go/ \| wc -l` → 0 |
| S3-MIN-2-M7 (multi-stage Dockerfile) | Size assertion | `docker images ai-service-fastapi --format '{{.Size}}'` → giảm ≥ 30% so với baseline |
| S3-MIN-2-M8 (YAML anchor) | Compose config validation | `docker compose -f backend-microservices/docker-compose.yml config` → render OK, grep `DB_USER` trong rendered vẫn đúng |
| S3-MIN-2-M10 (ALLOWED_HOSTS fail-fast) | `auth-service/tests/test_config.py` | `test("ALLOWED_HOSTS required in production")` — unset env, `DEBUG=False` → RuntimeError |
| S3-MIN-2-M11 (rename scripts) | Pytest collection check | `pytest --collect-only backend-microservices/ 2>&1 \| grep -c "scripts/e2e"` = 0 |
| S3-MIN-2-M14 (os.makedirs lifespan) | Pytest isolation | `pytest --collect-only ai-service-fastapi/tests/ 2>&1 \| grep -c "MEDIA_ROOT"` = 0 |
| S3-MIN-2-M15 (test fixture env) | `pytest` without env | `unset GATEWAY_SECRET && pytest backend-microservices/booking-service/tests/` → PASS (fixture tự inject) |
| S3-MIN-2-M16 (realtime-service-go hostname) | `grep -rn "realtime-service:8006" backend-microservices/ --include='*.py'` → 0 match |
| S3-MIN-3-UM1 (DashboardUI split) | `wc -l ParkingSimulatorUnity/Assets/Scripts/UI/DashboardUI.cs` → ≤ 300 |
| S3-MIN-3-UM2 (CameraConfigAsset) | Unity EditMode test | `TestVirtualCameraManager_LoadsConfigFromAsset()` — instantiate manager, assert camera count khớp asset |
| S3-MIN-3-UM3 (SimLogger) | Grep check | `grep -rn "Debug.Log" Assets/Scripts/ --include='*.cs' \| wc -l` → giảm đáng kể |
| S3-MIN-3-UM5 (dual-cookie) | `ParkingSim.Tests.EditMode/AuthManagerTests.cs` | `TestParseDualCookieSetsSessionAndCsrf()` — mock header, verify cả 2 token extracted |
| S3-DEAD-D* (dead code sweep) | `git status --ignored` | List tất cả file đã xoá không còn tracked, và các file mới thêm đã ignored |
| S3-DEAD-D17 (Cloudflare config env) | Clone fresh repo test | `git clone <repo> /tmp/test-clone && cd /tmp/test-clone && bash infra/cloudflare/cloudflared/render-config.sh` → tạo file config.yml thành công |
| S3-DOCS-2 (auth README) | Grep check | `grep -E "postgresql\|JWT_REFRESH" backend-microservices/auth-service/README.md` → 0 |
| S3-DOCS-3 (status.yaml) | YAML validation | `python -c "import yaml; yaml.safe_load(open('docs/status.yaml'))"` → không raise |
| S3-POLISH-1 (bash deploy script) | Linux CI smoke | `bash scripts/deploy-local.sh` trên ubuntu-latest runner → stack boot PASS |
| **Gate thoát Sprint 3** | Toàn bộ suite | Playwright 5/5 PASS, `npm run typecheck` 0 errors full strict, `pytest --cov ≥ 70%` per service, `docker compose up -d` boot trong 2 phút |

---

# ROLLBACK PLAN

Mỗi sprint commit theo git branch `fix/sprint-N`. Nếu hỏng tới mức không rollback file được:

1. `git reset --hard origin/main` (trên branch feature, KHÔNG phải main)
2. Docker: `docker compose down -v && docker compose up -d --build` (mất data test — OK vì đã có seed script)
3. Cloudflare secret: rotate lại nếu nghi ngờ leak mới
4. Database: dùng migration rollback `python manage.py migrate <app> <previous>`

## Migration rollback safety (QUAN TRỌNG cho S2-IMP-1 + S2-IMP-2)

Migrations thêm field mới + backfill data là **forward-only trên data** (rollback `RemoveField` sẽ mất data đã backfill). Để plan rollback-safe:

### Pattern `RunPython(forward, reverse=noop)`
```python
def forward_backfill(apps, schema_editor):
    Booking = apps.get_model('bookings', 'Booking')
    # ... backfill logic ...

def reverse_noop(apps, schema_editor):
    # Intentional no-op — giữ data, chỉ drop column nếu cần
    pass

class Migration(migrations.Migration):
    operations = [
        migrations.AddField('booking', 'vehicle_brand', models.CharField(max_length=50, blank=True, default='')),
        migrations.RunPython(forward_backfill, reverse_noop),
    ]
```

Rollback sẽ drop column nhưng không raise exception. Nếu muốn **đảm bảo không mất data**, dump table trước migration:
```bash
docker compose exec mysql mysqldump -u root -p parksmartdb booking > /backup/booking-pre-s2-imp-1.sql
python manage.py migrate bookings 0XXX
```

Restore:
```bash
python manage.py migrate bookings <previous>
docker compose exec -T mysql mysql -u root -p parksmartdb < /backup/booking-pre-s2-imp-1.sql
```

### Outbox + ProcessedEvent table rollback

`OutboxEvent`, `ProcessedEvent` pure-create tables — rollback `DROP TABLE` không destructive trên booking data gốc. An toàn.

## Secret rotation rollback

⚠️ **KHÔNG BAO GIỜ rollback secret mà không rotate lại lần nữa.** Nếu rotate S1-CRIT-2b xong phát hiện bug → generate secret V3 mới, đừng quay lại V1.

**Không bao giờ:**
- `git push --force origin main`
- Skip pre-commit hooks (`--no-verify`)
- Rollback secret mà không rotate (lý do trên)
- Drop denormalized column sau khi backfill mà không dump data trước

---

# ESTIMATED TIMELINE (đã điều chỉnh sau audit v2)

| Sprint | Ngày công (v1) | Ngày công (v2 — realistic) | Lý do bump |
|---|---|---|---|
| Sprint 1 | 5-7 | **7-10** | +1-2 ngày cho Unity X-Device-Token injection (S1-CRIT-4b) + TypeScript phase-in thực tế |
| Sprint 2 | 10-12 | **14-18** | +3-4 ngày cho 25-28 pages layering (gấp đôi count), +1-2 ngày `esp32.py` refactor, +0.5 ngày BE/FE contract audit S2-IMP-1 Bước 0 |
| Sprint 3 | 5-7 | **6-8** | +1 ngày strict mode full enable + docs sync |
| **Total** | **20-26** | **27-36 ngày công** | |
| **Tuần lịch (1 dev)** | 5-6 tuần | **5-7 tuần** | |

Nếu có **2 dev song song** (1 backend, 1 FE/Unity): **~3.5-5 tuần**.

**Buffer khuyến nghị:** thêm **+20%** (5-7 ngày) cho incident + scope creep + test flakiness → **plan thực tế 32-43 ngày công** trong pessimistic case.

---

# REFERENCES

- Review artifacts đầy đủ: transcript hai subagent `aacf7f0157682aa57` (backend) + `ae3eb76db5094fec7` (frontend/Unity) trong session 2026-04-15
- Reviews cũ: `docs/reviews/production-readiness-review.md`, `docs/reviews/UNITY-SIMULATOR-re-review.md`
- Dead code audit cũ: `docs/research/ISSUE-SECURITY-BLOCKERS-2026-03-13-dead-code-audit.md`
- Coding standards: `.github/copilot-instructions.md`
- Architecture: `CLAUDE.md` + `docs/architecture/context.md`
- Status: `docs/status.yaml`
- GitNexus: repo indexed as `Project_Main`, dùng `mcp__gitnexus__*` tools để verify blast radius trước mỗi refactor lớn
