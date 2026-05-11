# Docker Container Logs Audit Report

**Date:** 2026-04-13 | **Type:** Infrastructure Audit | **Containers:** 16/16 running

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **Tất cả 16 containers đều UP và healthy** — không có crash hay restart loop
> 2. **parking-service bị spam Forbidden (403)** trên `/parking/cameras/`, `/parking/slots/{id}/`, `/parking/lots/{id}/` — nghi do thiếu/sai authentication header từ internal calls
> 3. **ai-service liên tục fail kết nối physical cameras** (RTSP 192.168.1.100:554, DroidCam 192.168.100.130:4747) — expected nếu không có hardware
> 4. **Django migration race conditions** trên auth-service, vehicle-service, parking-service khi startup — "Table already exists" errors (non-blocking, services recovered)
> 5. **booking-service có pending migration** chưa được apply — `models have changes not yet reflected in a migration`
> 6. **RabbitMQ memory high watermark** triggered 2 lần — RAM pressure

---

## 2. Chi Tiết Từng Service

### 2.1 Services Chạy Sạch (Không Lỗi)

| Service                     | Status | Ghi chú                                                                |
| --------------------------- | ------ | ---------------------------------------------------------------------- |
| **gateway-service-go**      | CLEAN  | Tất cả requests 200. Health check OK.                                  |
| **chatbot-service-fastapi** | CLEAN  | Chỉ health checks + conversation history 200.                          |
| **payment-service-fastapi** | CLEAN  | Health checks 200 + 2x `POST /api/payments/initiate/` 201 Created.     |
| **booking-celery-beat**     | CLEAN  | Scheduler chạy đúng: auto-cancel mỗi 1 phút, no-show check mỗi 5 phút. |
| **parksmartdb_redis**       | CLEAN  | Background save (RDB) hoạt động bình thường mỗi ~5 phút.               |

### 2.2 Services Có Lỗi/Warning

---

### parking-service

**Severity: WARNING**

**Issue 1: Massive Forbidden (403) Spam**

```
Forbidden: /parking/cameras/
Forbidden: /parking/slots/00bdb32f-7abe-4a7b-95b8-1912a4ebc766/
Forbidden: /parking/lots/bc1a3e4a-0b24-4510-892d-2d4b2b64c7b5/
```

- Hàng trăm requests liên tục bị 403
- **Root cause khả năng**: Internal service-to-service calls thiếu gateway secret hoặc authentication token. Các endpoint này yêu cầu permission mà caller không cung cấp.
- **Impact**: Chức năng liên quan camera/slot/lot detail có thể không hoạt động cho non-admin users

**Issue 2: Unordered QuerySet pagination warning**

```
UnorderedObjectListWarning: Pagination may yield inconsistent results with an unordered object_list: <class 'infrastructure.models.Zone'> QuerySet.
```

- **Impact**: Zone pagination có thể trả kết quả không nhất quán giữa các page

**Issue 3: Django Migration Error (startup)**

```
django.db.migrations.exceptions.MigrationSchemaMissing: Unable to create the django_migrations table ((1050, "Table 'django_migrations' already exists"))
django.db.utils.OperationalError: (1050, "Table 'django_session' already exists")
```

- **Impact**: Non-blocking — service recovered và chạy bình thường sau đó

---

### auth-service

**Severity: WARNING**

**Issue 1: Django Migration Error (startup)**

```
django.db.utils.OperationalError: (1050, "Table 'django_session' already exists")
```

- Migration race condition khi container khởi động (nhiều services cùng migrate shared DB)
- **Impact**: Non-blocking — gunicorn started OK sau đó

**Issue 2: Bad Requests**

```
Method Not Allowed: /auth/login/
Bad Request: /auth/login/
Bad Request: /auth/register/  (x6)
```

- **Root cause**: Client gửi sai HTTP method hoặc sai request body format
- **Impact**: Một số login/register attempts bị fail

**Issue 3: Missing User Endpoint**

```
Not Found: /users/9026a2ec-b43d-40e3-9125-40b77fdccdb6/increment-no-show/  (x2)
```

- **Root cause**: Endpoint `increment-no-show` không tồn tại/chưa được implement trên auth-service
- **Impact**: No-show tracking bị silent fail

---

### vehicle-service

**Severity: WARNING**

**Issue 1: Django Migration Error (startup)**

```
django.db.migrations.exceptions.MigrationSchemaMissing: Unable to create the django_migrations table ((1050, "Table 'django_migrations' already exists"))
```

- Giống auth-service và parking-service — race condition
- **Impact**: Non-blocking — migrations applied OK sau retry, gunicorn started

**Issue 2: Bad Requests**

```
Bad Request: /vehicles/  (x8)
```

- **Root cause**: Client gửi sai format khi CRUD vehicles
- **Impact**: Một số vehicle operations bị fail

---

### booking-service

**Severity: WARNING**

**Issue 1: Pending Migration Not Applied**

```
Your models in app(s): 'bookings' have changes that are not yet reflected in a migration, and so won't be applied.
Run 'manage.py makemigrations' to make new migrations, and then re-run 'manage.py migrate' to apply them.
```

- **Impact**: Code có model changes nhưng DB schema chưa cập nhật — có thể gây runtime errors

**Issue 2: Not Found Endpoints**

```
Not Found: /bookings/current-parking/  (x3)
Not Found: /api/bookings/ef2d6d9a-fe09-4eac-8929-6bc6ebf54334/payment-status/
```

- `/bookings/current-parking/` — endpoint path mismatch (gateway có thể đang proxy sai)
- `/api/bookings/{id}/payment-status/` — endpoint chưa implement hoặc URL prefix sai

---

### ai-service-fastapi

**Severity: INFO (Expected)**

**Issue 1: Physical Camera Connection Failures (Recurring)**

```
[tcp] Connection to tcp://192.168.1.100:554?timeout=0 failed: Connection refused
Camera capture attempt 1/1 failed for rtsp://user:password@192.168.1.100:554/H.264: Cannot open camera stream
[tcp] Connection to tcp://192.168.100.130:4747 failed: Connection refused
Camera capture attempt 1/1 failed for http://192.168.100.130:4747/video: Cannot open camera stream
```

- **Root cause**: Physical cameras (Ezviz RTSP @ 192.168.1.100, DroidCam @ 192.168.100.130) không available — expected trong Docker environment không có hardware
- **Impact**: Physical camera streams không khả dụng, virtual cameras hoạt động bình thường
- **Note**: RTSP URL chứa credentials `user:password` hardcoded trong log — **security concern**

---

### realtime-service-go

**Severity: INFO**

**Issue: Frequent WebSocket Close 1006**

```
WebSocket read error: websocket: close 1006 (abnormal closure): unexpected EOF
```

- ~10+ occurrences trong 100 dòng log gần nhất
- **Root cause**: Client (browser) navigate away hoặc close tab mà không graceful close WebSocket
- **Impact**: Normal behavior cho SPA navigation, nhưng tần suất cao — có thể frontend reconnect logic cần optimize

---

### notification-service-fastapi

**Severity: WARNING**

**Issue: 422 Unprocessable Entity**

```
POST /notifications/ HTTP/1.1" 422 Unprocessable Entity  (x2, from 172.18.0.7 = booking-service)
```

- **Root cause**: booking-service gửi notification với payload không đúng schema
- **Impact**: Một số notifications bị fail delivery

---

### booking-celery-worker

**Severity: INFO**

**Issue: Celery Deprecation Warning**

```
CPendingDeprecationWarning: The broker_connection_retry configuration setting will no longer determine
whether broker connection retries are made during startup in Celery 6.0 and above.
```

- **Fix**: Thêm `broker_connection_retry_on_startup = True` vào Celery config
- **Impact**: No runtime impact hiện tại, nhưng sẽ break khi upgrade Celery 6.0

---

### parksmartdb_mysql

**Severity: INFO**

**Warnings:**

```
[Warning] [MY-011068] The syntax '--skip-host-cache' is deprecated
[Warning] [MY-010068] CA certificate ca.pem is self signed.
[Warning] [MY-011810] Insecure configuration for --pid-file: Location '/var/run/mysqld' accessible to all OS users
```

- All non-critical MySQL config warnings
- Self-signed CA — OK cho development

---

### parksmartdb_rabbitmq

**Severity: WARNING**

**Issue: Memory High Watermark**

```
alarm_handler: {set,{system_memory_high_watermark,[]}}   (08:16:23, 08:23:20)
alarm_handler: {clear,system_memory_high_watermark}       (08:17:23)
```

- RabbitMQ hit memory limit 2 lần — publishers bị blocked cho đến khi cleared
- **Impact**: Message delivery bị delay trong khoảng ~1 phút mỗi lần

**Deprecation Warning:**

```
Deprecated features: `management_metrics_collection`: Feature is deprecated
```

---

### parksmart-nginx

**Severity: INFO**

**Issue: 499 Client Closed Request**

```
"GET /ws/user/{id}/ HTTP/1.1" 499 0
```

- ~3 occurrences — client closed WebSocket connection before server could respond
- Normal browser behavior during navigation

---

## 3. Summary by Severity

### CRITICAL (0)

_None — no crashes, no data loss, no 500 errors detected._

### WARNING (6 services)

| #   | Service                  | Issue                                                          | Action Needed                                     |
| --- | ------------------------ | -------------------------------------------------------------- | ------------------------------------------------- |
| 1   | **parking-service**      | Massive 403 Forbidden spam on `/cameras/`, `/slots/`, `/lots/` | Investigate auth/permission for internal calls    |
| 2   | **booking-service**      | Pending migration not applied                                  | Run `manage.py makemigrations && migrate`         |
| 3   | **auth-service**         | `Not Found: /users/{id}/increment-no-show/`                    | Implement endpoint or fix caller                  |
| 4   | **notification-service** | 422 from booking-service POST /notifications/                  | Fix notification payload schema                   |
| 5   | **parksmartdb_rabbitmq** | Memory high watermark triggered 2x                             | Increase RabbitMQ RAM limit or optimize consumers |
| 6   | **ai-service-fastapi**   | RTSP credentials `user:password` visible in logs               | Remove/mask credentials from log output           |

### INFO (5 items)

| #   | Service                       | Issue                                                            |
| --- | ----------------------------- | ---------------------------------------------------------------- |
| 1   | auth/vehicle/parking services | Django migration race condition on startup (non-blocking)        |
| 2   | ai-service-fastapi            | Physical camera connection refused (expected without hardware)   |
| 3   | realtime-service-go           | WebSocket close 1006 (normal for SPA navigation)                 |
| 4   | booking-celery-worker         | Celery `broker_connection_retry` deprecation warning             |
| 5   | parksmartdb_mysql             | Deprecated `--skip-host-cache`, self-signed CA, pid-file warning |

---

## 4. Security Concerns

1. **ai-service-fastapi**: RTSP camera URL logs contain plaintext credentials `rtsp://user:password@192.168.1.100:554/H.264`
2. **parksmartdb_mysql**: Self-signed CA certificate (OK for dev, not for prod)
3. **parksmartdb_mysql**: PID file location accessible to all OS users
