# Research Report: ParkSmart — 6-Area Deep Analysis

**Date:** 2026-03-27 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **ESP32 endpoints: ZERO authentication** — Tất cả 8 ESP32 endpoints nằm trong `EXEMPT_PATHS`, bất kỳ ai trên mạng đều gọi được. ESP32 hardware hardcode WiFi password + gateway secret trong source code.
> 2. **CI/CD: Không có backend tests** — Chỉ test frontend (lint/test/build) + structure check. Không chạy Python tests, Go tests, hay security scan.
> 3. **Booking → Payment: TODO stubs** — Booking service có `payment` action nhưng trả fake URL. Payment service tồn tại riêng nhưng booking KHÔNG gọi payment service khi tạo booking. Chỉ payment service gọi ngược lại booking khi verify.
> 4. **Gateway rate limiter: In-memory, hardcoded 100 req/min** — Không configurable, không per-route, mất khi restart, không distributed.
> 5. **PyTorch 1.13.1 (released Jan 2023)** — Cực kỳ cũ, conflict với `ultralytics==8.4.18` (cần torch ≥ 2.0) và `timm==1.0.25`. Dùng `torch.load(weights_only=False)` — security risk.
> 6. **23+ hardcoded IPs** trải khắp `esp32.py`, `camera.py`, hardware `.ino`, seed scripts, frontend components. Bao gồm RTSP credentials trong source code.

---

## 1. ESP32 Endpoint Security

### 1.1 ALL ESP32 Endpoints — NO Authentication

**File:** `backend-microservices/ai-service-fastapi/app/middleware/gateway_auth.py` (L11-29)

```python
class GatewayAuthMiddleware(BaseHTTPMiddleware):
    """Verify requests come through the API gateway."""

    EXEMPT_PATHS = [
        "/health/",
        "/health",
        "/ai/health/",
        "/ai/health",
        "/docs",
        "/openapi.json",
        "/ai/cameras/",
        # ESP32 device endpoints — ESP32 connects directly (no gateway)
        "/ai/parking/esp32/register",
        "/ai/parking/esp32/heartbeat",
        "/ai/parking/esp32/log",
        # Existing ESP32 gate endpoints (also direct)
        "/ai/parking/esp32/check-in",
        "/ai/parking/esp32/check-out",
        "/ai/parking/esp32/verify-slot",
        "/ai/parking/esp32/cash-payment",
        "/ai/parking/esp32/status",
    ]
```

**Impact:** Mọi endpoint ESP32 đều bypass gateway auth. Bất kỳ ai biết IP:port của AI service đều có thể:
- Fake check-in/check-out → mở barrier
- Register fake devices
- Send fake cash payment → mark booking as paid
- Access device status/logs

### 1.2 ESP32 Router — No Auth Dependencies

**File:** `backend-microservices/ai-service-fastapi/app/routers/esp32.py` (L58, L601-605, L923-927)

```python
router = APIRouter(prefix="/ai/parking/esp32", tags=["esp32"])

# Check-in — NO auth dependency
@router.post("/check-in/", response_model=ESP32Response)
async def esp32_check_in(
    payload: ESP32CheckInRequest,
    db: Session = Depends(get_db),    # Only DB dependency, no auth
) -> ESP32Response:

# Check-out — NO auth dependency
@router.post("/check-out/", response_model=ESP32Response)
async def esp32_check_out(
    payload: ESP32CheckOutRequest,
    db: Session = Depends(get_db),    # Only DB dependency, no auth
) -> ESP32Response:

# Cash payment — NO auth dependency
@router.post("/cash-payment/", response_model=ESP32Response)
async def esp32_cash_payment(
    payload: CashPaymentRequest,
    db: Session = Depends(get_db),    # Only DB dependency, no auth
) -> ESP32Response:

# Register/heartbeat/log — NO auth dependency
@router.post("/register", response_model=ESP32AckResponse)
async def esp32_register(body: ESP32RegisterRequest) -> ESP32AckResponse:

@router.post("/heartbeat", response_model=ESP32AckResponse)
async def esp32_heartbeat(body: ESP32HeartbeatRequest) -> ESP32AckResponse:

@router.post("/log", response_model=ESP32AckResponse)
async def esp32_log(body: ESP32LogRequest) -> ESP32AckResponse:

# Status — NO auth, GET endpoint
@router.get("/status/")

# Device list/logs — NO auth either
@router.get("/devices", response_model=ESP32DeviceListResponse)
@router.get("/devices/{device_id}/logs", response_model=ESP32DeviceLogsResponse)
```

### 1.3 ESP32 Hardware — Hardcoded Secrets

**File:** `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino` (L41-50)

```cpp
// WiFi credentials
const char* WIFI_SSID     = "FPT Telecom-755C-IOT";      // ← Hardcoded WiFi SSID
const char* WIFI_PASSWORD = "2462576d";                    // ← Hardcoded WiFi password

// AI Service URL — chạy local (máy tính cùng mạng WiFi)
const char* AI_SERVICE_BASE_URL = "http://192.168.100.194:8009";

// Gateway Secret — phải trùng với server
const char* GATEWAY_SECRET = "gateway-internal-secret-key";  // ← Hardcoded secret
```

**Note:** ESP32 gửi `GATEWAY_SECRET` trong header nhưng server EXEMPT tất cả ESP32 paths nên header này bị bỏ qua hoàn toàn.

### 1.4 ESP32 Inter-Service Calls — Use GATEWAY_SECRET

**File:** `backend-microservices/ai-service-fastapi/app/routers/esp32.py` (L308-312)

```python
async def _call_booking_checkin(booking_id: str, user_id: str) -> dict:
    """Call booking-service checkin endpoint."""
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/checkin/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET, "X-User-ID": user_id, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers)
        return {"status_code": resp.status_code, "data": resp.json()}
```

---

## 2. CI/CD Backend

### 2.1 Full Content: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "20"

jobs:
  backend-structure-check:         # ← CHỈ check file tồn tại, KHÔNG chạy tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "${{ env.PYTHON_VERSION }}"
      - name: Verify backend repository layout
        run: |
          python - <<'PY'
          from pathlib import Path
          root = Path("backend-microservices")
          required_paths = [
              root,
              root / ".env.example",
              root / "gateway-service-go",
              root / "realtime-service-go",
              root / "chatbot-service-fastapi",
              root / "payment-service-fastapi",
          ]
          missing = [str(path) for path in required_paths if not path.exists()]
          if missing:
              raise SystemExit(f"Missing required backend paths: {missing}")
          print("backend-microservices layout check: OK")
          PY

  lint-frontend:                    # ← Frontend lint only
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: spotlove-ai
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "${{ env.NODE_VERSION }}"
          cache: npm
          cache-dependency-path: spotlove-ai/package-lock.json
      - run: npm ci
      - run: npm run lint

  test-frontend:                    # ← Frontend test only
    runs-on: ubuntu-latest
    needs: lint-frontend
    # ... npm run test

  build-frontend:                   # ← Frontend build + audit
    runs-on: ubuntu-latest
    needs: test-frontend
    # ... npm run build + npm audit --audit-level=high
```

### 2.2 Full Content: `.github/workflows/deploy-cloudflare-pages.yml`

Frontend deploy only. No backend deploy.

### 2.3 What's MISSING in CI:

| Missing Item                        | Impact      |
| ----------------------------------- | ----------- |
| Python service tests (pytest)       | **CRITICAL** |
| Go service tests (go test)          | **CRITICAL** |
| Django migration check              | HIGH        |
| Backend linting (ruff/flake8/golangci-lint) | HIGH |
| Docker build verification           | HIGH        |
| Security scanning (trivy/snyk/bandit) | HIGH      |
| Integration tests                   | MEDIUM      |
| Type checking (mypy/pyright)        | MEDIUM      |
| Backend deploy pipeline             | HIGH        |

---

## 3. Booking → Payment Integration

### 3.1 Booking Model Fields

**File:** `backend-microservices/booking-service/bookings/models.py` (L46-119)

```python
class Booking(models.Model):
    PAYMENT_METHODS = [
        ('online', 'Online'),
        ('on_exit', 'On Exit'),
    ]
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    CHECK_IN_STATUS = [
        ('not_checked_in', 'Not Checked In'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = models.UUIDField(db_index=True)
    user_email = models.EmailField()
    vehicle_id = models.UUIDField()
    vehicle_license_plate = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=20)
    parking_lot_id = models.UUIDField()
    parking_lot_name = models.CharField(max_length=255)
    floor_id = models.UUIDField(null=True, blank=True)
    zone_id = models.UUIDField()
    zone_name = models.CharField(max_length=100)
    slot_id = models.UUIDField(null=True, blank=True)
    slot_code = models.CharField(max_length=20, blank=True)
    package_type = models.CharField(max_length=20, default='hourly')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    check_in_status = models.CharField(max_length=20, choices=CHECK_IN_STATUS, default='not_checked_in')
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    qr_code_data = models.TextField(blank=True)
    hourly_start = models.DateTimeField(null=True, blank=True)
    hourly_end = models.DateTimeField(null=True, blank=True)
    extended_until = models.DateTimeField(null=True, blank=True)
    late_fee_applied = models.BooleanField(default=False)
```

### 3.2 Booking Creation — NO Payment Service Call

**File:** `backend-microservices/booking-service/bookings/views.py` (L79-97)

```python
def create(self, request, *args, **kwargs):
    """Create booking and return full BookingSerializer response."""
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    booking = serializer.save()          # ← Saves booking with payment_status='pending'

    if booking.slot_id:
        broadcast_slot_status(...)       # ← Only broadcasts slot, NO payment call

    output_serializer = BookingSerializer(booking)
    return Response({
        'booking': output_serializer.data,
        'message': 'Booking created successfully',
        'qrCode': booking.qr_code_data   # ← Returns QR immediately, no payment initiated
    }, status=status.HTTP_201_CREATED)
```

### 3.3 Booking Payment Actions — FAKE URLs (TODO stubs)

**File:** `backend-microservices/booking-service/bookings/views.py` (L334-358, L363-406)

```python
@action(detail=True, methods=['post'])
def payment(self, request, pk=None):
    """Initiate payment for a specific booking."""
    booking = self.get_object()
    payment_method = request.data.get('payment_method')

    # TODO: Integrate with payment gateway (MoMo, VNPay, ZaloPay)
    payment_url = f"https://payment-gateway.com/pay?booking={booking.id}&method={payment_method}"  # ← FAKE

    booking.payment_status = 'processing'
    booking.save(update_fields=['payment_status'])
    return Response({
        'payment_url': payment_url,     # ← FAKE URL
        'booking_id': str(booking.id),
        'amount': float(booking.price)
    })

@action(detail=False, methods=['post'], url_path='payment')
def initiate_payment(self, request):
    """Initiate payment (expects booking_id in body)."""
    # ... same pattern, FAKE URL
    # TODO: Integrate with payment gateway
    payment_url = f"https://payment-gateway.com/pay?booking={booking.id}&method={payment_method}"
```

### 3.4 Payment Service — Independent, Calls BACK to Booking

**File:** `backend-microservices/payment-service-fastapi/app/routers/payment.py` (L23-93)

```python
@router.post("/initiate/", response_model=PaymentResponse, status_code=201)
async def initiate_payment(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Initiate a payment for a booking."""
    # Creates Payment record in payment DB
    payment = Payment(
        id=str(uuid.uuid4()),
        booking_id=payload.booking_id,
        user_id=user_id,
        payment_method=payload.payment_method,
        amount=payload.amount,
        status="pending",
    )

    if payload.payment_method == "cash":
        payment.status = "completed"      # ← Cash auto-completes
    else:
        payment.status = "processing"
        payment.payment_url = f"https://payment-gateway.example.com/pay/{payment.transaction_id}"  # ← Also FAKE

    db.add(payment)
    db.commit()

    # Notify booking service about payment status (CALLBACK)
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{settings.BOOKING_SERVICE_URL}/api/bookings/{payload.booking_id}/payment-status/",
                json={"payment_status": payment.status},
                headers={"X-Gateway-Secret": settings.GATEWAY_SECRET},
                timeout=5.0,
            )
    except Exception:
        pass  # Non-critical: booking service will reconcile
```

### 3.5 Integration Gap Summary

| Flow                    | Status      | Detail                                            |
| ----------------------- | ----------- | ------------------------------------------------- |
| Booking create → Payment | **MISSING** | Booking service does NOT call payment service      |
| Payment verify → Booking | EXISTS      | Payment service PATCHes booking payment_status     |
| ESP32 checkout → Booking | EXISTS      | AI service calls booking checkout via httpx         |
| ESP32 cash → Booking     | EXISTS      | AI service PATCHes booking payment_status           |
| Frontend → Payment       | PARTIAL     | Frontend calls booking's fake payment endpoint      |

---

## 4. Gateway Rate Limiting

### 4.1 Current Rate Limiter — In-Memory Token Bucket

**File:** `backend-microservices/gateway-service-go/internal/middleware/ratelimit.go` (FULL)

```go
package middleware

import (
    "net/http"
    "sync"
    "time"
    "github.com/gin-gonic/gin"
)

type RateLimiter struct {
    mu       sync.Mutex
    visitors map[string]*visitor
    rate     int           // requests per window
    window   time.Duration // time window
}

type visitor struct {
    tokens    int
    lastReset time.Time
}

var limiter *RateLimiter

func init() {
    limiter = &RateLimiter{
        visitors: make(map[string]*visitor),
        rate:     100,              // 100 requests — HARDCODED
        window:   1 * time.Minute,  // per minute — HARDCODED
    }
    go func() {
        for {
            time.Sleep(5 * time.Minute)
            limiter.cleanup()
        }
    }()
}

func RateLimitMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        ip := c.ClientIP()       // ← IP-based only
        if !limiter.allow(ip) {
            c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{
                "error":   "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
            })
            return
        }
        c.Next()
    }
}
// ... allow() and cleanup() methods
```

### 4.2 Issues

| Issue                         | Detail                                              |
| ----------------------------- | --------------------------------------------------- |
| Hardcoded values              | 100 req/min, not configurable                        |
| No per-route differentiation  | Login gets same limit as static assets               |
| In-memory only                | Lost on restart, not shared across instances          |
| No burst handling             | No separate burst vs sustained rate                   |
| IP only                       | No user-based rate limiting                           |
| No `Retry-After` header       | Client doesn't know when to retry                     |
| No Redis integration          | Despite Redis being in `go.mod` for sessions          |

### 4.3 Gateway Config — No Rate Limit Settings

**File:** `backend-microservices/gateway-service-go/internal/config/config.go` (L14-39)

```go
type Config struct {
    Port          string
    Environment   string
    GatewaySecret string
    RedisURL      string
    Debug         bool
    CORSAllowedOrigins    []string
    FEAuthCallbackURL     string
    SessionCookieDomain   string
    SessionCookieSecure   bool
    SessionCookieSameSite string
    SessionCookieMaxAge   int
    // Service URLs
    AuthServiceURL         string
    ParkingServiceURL      string
    VehicleServiceURL      string
    BookingServiceURL      string
    NotificationServiceURL string
    RealtimeServiceURL     string
    PaymentServiceURL      string
    AIServiceURL           string
    ChatbotServiceURL      string
}
// ← NO rate limit config fields at all
```

### 4.4 Go Dependencies

**File:** `backend-microservices/gateway-service-go/go.mod`

```
module gateway-service
go 1.22
require (
    github.com/gin-contrib/cors v1.7.2
    github.com/gin-gonic/gin v1.10.0
    github.com/google/uuid v1.6.0
    github.com/joho/godotenv v1.5.1
    github.com/redis/go-redis/v9 v9.7.0    // ← Redis available but not used for rate limiting
)
```

---

## 5. PyTorch Version

### 5.1 Current Versions

**File:** `backend-microservices/ai-service-fastapi/requirements.txt` (L72-75, L78)

```
torch==1.13.1          # ← Released Dec 2022, 3+ YEARS old
torchvision==0.14.1    # ← Matches torch 1.13.1
timm==1.0.25           # ← Requires torch >= 2.0
ultralytics==8.4.18    # ← Requires torch >= 2.0
easyocr==1.7.2
```

### 5.2 Version Conflicts

| Package           | Required torch | Installed     | Conflict? |
| ----------------- | -------------- | ------------- | --------- |
| `ultralytics==8.4.18` | ≥ 2.0      | 1.13.1        | **YES**   |
| `timm==1.0.25`    | ≥ 2.0          | 1.13.1        | **YES**   |
| `easyocr==1.7.2`  | ≥ 1.7          | 1.13.1        | OK        |

### 5.3 Deprecated API Usage: `torch.load(weights_only=False)`

**File:** `backend-microservices/ai-service-fastapi/app/ml/inference/cash_recognition.py` (L92)
```python
checkpoint = torch.load(model_path, map_location=self._device, weights_only=False)
```

**File:** `backend-microservices/ai-service-fastapi/app/engine/ai_classifier.py` (L138)
```python
checkpoint = torch.load(model_path, map_location=self._device, weights_only=False)
```

**File:** `backend-microservices/ai-service-fastapi/train_and_evaluate.py` (L835)
```python
ckpt = torch.load(str(model_path), map_location=device)  # ← No weights_only param (defaults vary by version)
```

**File:** `backend-microservices/ai-service-fastapi/test_banknote_camera.py` (L157)
```python
checkpoint = torch.load(model_path, map_location=device, weights_only=False)
```

**Note:** `weights_only=False` allows arbitrary code execution during model loading — **security risk** if model files are untrusted. In torch ≥ 2.6, `weights_only=True` is the default.

### 5.4 Other Deprecated Patterns

- `torchvision.models.resnet50(weights=None)` — OK (new API), nhưng running on torch 1.13.1 where this API may not exist (added in torchvision 0.13).
- `MobileNet_V3_Large_Weights` import exists in code — requires torchvision ≥ 0.13 (OK with 0.14.1).

---

## 6. Camera IP Hardcode

### 6.1 Hardcoded IPs in AI Service

**File:** `backend-microservices/ai-service-fastapi/app/routers/esp32.py` (L167-168)
```python
# ── Default Camera URLs (hardcoded for prototype) ────────────────────────── #
DEFAULT_QR_CAMERA_URL = "http://192.168.100.130:4747/video"
DEFAULT_PLATE_CAMERA_URL = "rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main"  # ← CREDENTIALS IN CODE
```

**File:** `backend-microservices/ai-service-fastapi/app/routers/esp32.py` (L94-103)
```python
# seed_default_devices:
    {"device_id": "GATE-IN-01",  "ip": "192.168.100.194", ...},
    {"device_id": "GATE-OUT-01", "ip": "192.168.100.194", ...},
```

**File:** `backend-microservices/ai-service-fastapi/app/routers/camera.py` (L29-32)
```python
DEFAULT_PLATE_CAMERA_URL = "rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main"  # ← CREDENTIALS
DEFAULT_QR_CAMERA_URL = "http://192.168.100.130:4747/video"
```

**File:** `backend-microservices/ai-service-fastapi/app/routers/camera.py` (L34-55)
```python
CAMERAS = [
    {
        "id": "plate-camera-ezviz",
        "name": "Camera Biển Số (EZVIZ)",
        "stream_url": DEFAULT_PLATE_CAMERA_URL,   # ← contains credentials
    },
    {
        "id": "qr-camera-droidcam",
        "name": "Camera QR Code (DroidCam)",
        "stream_url": DEFAULT_QR_CAMERA_URL,
    },
]
```

**File:** `backend-microservices/ai-service-fastapi/app/routers/esp32.py` (L400-410)
```python
def _get_camera_url(camera_type: str = "qr") -> str:
    """Return the hardcoded camera URL for the given type."""
    if camera_type == "plate":
        return DEFAULT_PLATE_CAMERA_URL
    return DEFAULT_QR_CAMERA_URL
```

### 6.2 Config.py — NO Camera Config

**File:** `backend-microservices/ai-service-fastapi/app/config.py` (FULL)
```python
class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "parksmartdb"
    DB_USER: str = "root"
    DB_PASSWORD: str = "rootpassword"
    DEBUG: bool = True
    GATEWAY_SECRET: str = "gateway-internal-secret-key"
    MEDIA_ROOT: str = "/app/media"
    ML_MODELS_DIR: str = "/app/ml/models"
    PARKING_SERVICE_URL: str = "http://parking-service:8000"
    BOOKING_SERVICE_URL: str = "http://booking-service:8000"
    REALTIME_SERVICE_URL: str = "http://realtime-service-go:8006"
    PLATE_MODEL_PATH: str = "/app/app/models/license-plate-finetune-v1m.pt"
    YOLO_PARKING_MODEL_PATH: str = "/app/ml/models/yolo11n.pt"
    YOLO_PARKING_IOU_THRESHOLD: float = 0.15
    YOLO_PARKING_CONF_THRESHOLD: float = 0.25

    # ← NO camera URL settings
    # ← NO QR_CAMERA_URL
    # ← NO PLATE_CAMERA_URL
```

### 6.3 Hardcoded IPs in Other Locations

**File:** `hardware/esp32/esp32_gate_controller/esp32_gate_controller.ino` (L46)
```cpp
const char* AI_SERVICE_BASE_URL = "http://192.168.100.194:8009";
```

**File:** `backend-microservices/parking-service/infrastructure/management/commands/seed_cameras.py` (L22-40)
```python
cameras = [
    {"ip_address": "192.168.100.130", "port": 4747, "stream_url": "http://192.168.100.130:4747/video"},
    {"ip_address": "192.168.100.115", "port": 4747, "stream_url": "http://192.168.100.115:4747/video"},
    {"ip_address": "192.168.100.23",  "port": 554,  "stream_url": "rtsp://admin:XGIMBN@192.168.100.23:554/H.264"},
]
```

**File:** `backend-microservices/seed_e2e_data.py` (L386-408)
```python
cameras_data = [
    {"ip_address": "192.168.100.130", "stream_url": "http://192.168.100.130:4747/video"},
    {"ip_address": "192.168.100.23",  "stream_url": "rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main"},
    {"ip_address": "192.168.100.115", "stream_url": "http://192.168.100.115:4747/video"},
]
```

**File:** `backend-microservices/ai-service-fastapi/app/engine/camera_capture.py` (L12)
```python
# In docstring:
#   frame = await capture.capture_frame("http://192.168.100.130:4747/video")
```

**File:** `spotlove-ai/src/pages/admin/AdminCamerasPage.tsx` (L48, L60)
```typescript
{ id: "plate-camera-ezviz", ipAddress: "192.168.100.23", port: 554,  ... },
{ id: "qr-camera-droidcam", ipAddress: "192.168.100.130", port: 4747, ... },
```

**File:** `backend-microservices/parking-service/tests/conftest.py` (L96-101)
```python
Camera.objects.create(
    ip_address="192.168.100.23",
    stream_url="rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main",
)
```

### 6.4 Full Inventory of Hardcoded IPs

| IP               | Port | Protocol | Location                      | Contains Credentials? |
| ---------------- | ---- | -------- | ----------------------------- | --------------------- |
| 192.168.100.130  | 4747 | HTTP     | esp32.py, camera.py, seed     | No                    |
| 192.168.100.23   | 554  | RTSP     | esp32.py, camera.py, seed     | **YES** (admin:XGIMBN)|
| 192.168.100.194  | 8009 | HTTP     | esp32.py (devices), .ino      | No                    |
| 192.168.100.115  | 4747 | HTTP     | seed scripts                  | No                    |

---

## 5. ⚠️ Gotchas & Known Issues

- [x] **[BLOCKER]** ESP32 endpoints have ZERO authentication — anyone on the network can open barriers
- [x] **[BLOCKER]** RTSP camera credentials (`admin:XGIMBN`) hardcoded in source code (esp32.py L168, camera.py L29)
- [x] **[BLOCKER]** `torch==1.13.1` conflicts with `ultralytics==8.4.18` and `timm==1.0.25` (both require torch ≥ 2.0)
- [x] **[WARNING]** WiFi password hardcoded in `.ino` file committed to repo
- [x] **[WARNING]** `torch.load(weights_only=False)` allows arbitrary code execution
- [x] **[WARNING]** CI has NO backend tests — only frontend lint/test/build
- [x] **[WARNING]** Booking → Payment integration is TODO stubs with fake URLs
- [x] **[WARNING]** Rate limiter is in-memory, hardcoded, and not distributed
- [x] **[NOTE]** DB credentials in `config.py` defaults (`root`/`rootpassword`) — overridden by .env in prod
- [x] **[NOTE]** ESP32 check-out uses static test plate image instead of real camera (L935)
