# Research Report: ParkSmart Backend — Audit Toàn Bộ Logic, Lỗi, Thiếu Nghiệp Vụ

**Task:** ISSUE-001 | **Date:** 2025-07-17 | **Type:** Mixed (Codebase audit — toàn bộ)

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **7 lỗi HIGH** có thể gây sai dữ liệu production: slot status sai, slot không được release sau cancel, no-show logic bỏ sót, camera ghi đè trạng thái `reserved`, checkout logic bị nhân đôi trong views, time-window check-in bị bypass qua API trực tiếp, race condition double-booking.
> 2. **PackagePricing** không có seed data — mọi giá tính toán đều fallback về hardcode (15000/5000); chatbot cũng trả hardcode nếu bảng rỗng.
> 3. **Không có rollback** khi booking tạo thành công trong DB nhưng PATCH sang parking-service thất bại — slot trạng thái không nhất quán giữa hai service.

---

## 2. Service Inventory

| Service | Port | Stack | Mục đích |
|---------|------|-------|----------|
| `auth-service` | 8000 | Django DRF | Đăng ký / đăng nhập / JWT / quản lý user |
| `parking-service` | 8001 | Django DRF | Quản lý hạ tầng bãi xe (lot/floor/zone/slot/camera) |
| `booking-service` | 8002 | Django DRF + Celery | Đặt chỗ, check-in/out, thanh toán, vòng đời booking |
| `vehicle-service` | 8003 | Django DRF | Đăng ký xe, lookup biển số |
| `ai-service-fastapi` | 8005 | FastAPI + YOLO | ESP32 gate control, camera OCR/QR, slot detection |
| `realtime-service-go` | 8006 | Go WebSocket | Push update slot/booking realtime tới frontend |
| `chatbot-service-fastapi` | 8007 | FastAPI + Gemini | AI chatbot 15 intents, pipeline 5 bước |
| `payment-service-fastapi` | 8008 | FastAPI | Tạo payment record, (stub) gateway integration |
| `notification-service-fastapi` | 8009 | FastAPI | Push notification |
| `gateway-service-go` | 8080 | Go | API Gateway, auth header injection, route forwarding |

---

## 3. Phân Tích Codebase: Files Liên Quan

| File | Mục đích | Relevance |
|------|----------|-----------|
| [booking-service/bookings/views.py](../../../booking-service/bookings/views.py) | REST API + inline business logic | HIGH |
| [booking-service/bookings/services.py](../../../booking-service/bookings/services.py) | Business logic layer | HIGH |
| [booking-service/bookings/serializers.py](../../../booking-service/bookings/serializers.py) | Booking creation + service calls | HIGH |
| [booking-service/bookings/tasks.py](../../../booking-service/bookings/tasks.py) | Celery periodic tasks | HIGH |
| [booking-service/bookings/models.py](../../../booking-service/bookings/models.py) | Booking + PackagePricing models | HIGH |
| [ai-service-fastapi/app/routers/esp32.py](../../../ai-service-fastapi/app/routers/esp32.py) | Hardware gate flow | HIGH |
| [ai-service-fastapi/app/engine/camera_monitor.py](../../../ai-service-fastapi/app/engine/camera_monitor.py) | Background camera scan | HIGH |
| [ai-service-fastapi/app/engine/cash_session.py](../../../ai-service-fastapi/app/engine/cash_session.py) | Cash payment session | MEDIUM |
| [parking-service/infrastructure/models.py](../../../parking-service/infrastructure/models.py) | Infrastructure schema | HIGH |
| [payment-service-fastapi/app/routers/payment.py](../../../payment-service-fastapi/app/routers/payment.py) | Payment gateway stub | MEDIUM |
| [chatbot-service-fastapi/app/application/services/](../../../chatbot-service-fastapi/app/application/services/) | Chatbot pipeline | MEDIUM |

---

## 4. Endpoint Overview

### booking-service (port 8002)
| Method | Path | Mô tả |
|--------|------|-------|
| GET/POST | `/bookings/` | List / create booking |
| GET/PUT/DELETE | `/bookings/{id}/` | Retrieve / update / delete |
| POST | `/bookings/{id}/checkin/` | Manual check-in (API) |
| POST | `/bookings/{id}/checkout/` | Checkout + tính tiền |
| POST | `/bookings/{id}/cancel/` | Hủy booking |
| POST | `/bookings/{id}/extend/` | Gia hạn thêm giờ |
| POST | `/bookings/{id}/initiate-payment/` | Khởi tạo thanh toán |
| POST | `/bookings/{id}/verify-payment/` | Xác nhận thanh toán (TODO stub) |
| GET | `/bookings/packagepricings/` | Danh sách giá gói |
| POST/PUT/DELETE | `/bookings/packagepricings/{id}/` | CRUD giá |

### parking-service (port 8001)
| Method | Path | Mô tả |
|--------|------|-------|
| GET/POST | `/parking/lots/` | CRUD bãi xe |
| GET | `/parking/lots/nearest/` | Tìm bãi gần nhất (Haversine) |
| GET | `/parking/slots/` | List slots với filter zone |
| PATCH | `/parking/slots/{id}/` | Update slot status |
| PATCH | `/parking/slots/{id}/update-status/` | Update status từ camera |

### ai-service-fastapi (port 8005)
| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/ai/parking/esp32/check-in/` | ESP32 gate check-in (QR + OCR) |
| POST | `/ai/parking/esp32/check-out/` | ESP32 gate check-out |
| POST | `/ai/parking/esp32/verify-slot/` | Verify slot sau check-in |
| POST | `/ai/parking/esp32/cash-payment/` | Nhận tiền mặt (banknote detection) |
| GET | `/ai/parking/esp32/status/` | Health check |
| POST | `/ai/parking/check-in/` | Manual check-in với camera |
| POST | `/ai/parking/check-out/` | Manual check-out |

---

## 5. Logic Bugs — Đã Xác Nhận

### BUG-01 | HIGH | Slot broadcast `occupied` ngay khi đặt chỗ (chưa checkin)

**File:** [booking-service/bookings/views.py](../../../booking-service/bookings/views.py)  
**Vị trí:** Action `create()`, gọi `broadcast_slot_status()`

**Vấn đề:**
```python
# views.py — sau khi Booking.create() thành công
broadcast_slot_status(
    slot_id=str(booking.slot_id),
    slot_status='occupied',   # ← SAI: xe chưa đến, chỉ mới đặt
    ...
)
```
Hệ thống realtime broadcast cho tất cả client rằng slot đã `occupied`, trong khi slot chỉ ở trạng thái `reserved`. Frontend map màu sẽ hiển thị sai.

**Fix:**
```python
broadcast_slot_status(slot_id=..., slot_status='reserved', ...)
```

---

### BUG-02 | HIGH | Checkout logic bị nhân đôi giữa `views.py` và `services.py`

**File:** [booking-service/bookings/views.py](../../../booking-service/bookings/views.py)  
**Vị trí:** Action `checkout()` ~lines 151–244 + private method `_get_hourly_price()`

**Vấn đề:** `views.py` implement lại TOÀN BỘ logic tính tiền thay vì gọi `services.perform_checkout()`. Hai bản logic tồn tại song song:

```python
# views.py — inline logic (sai pattern)
def checkout(self, request, pk=None):
    hourly_price = self._get_hourly_price(booking.vehicle_type)
    late_fee_rate = hourly_price * Decimal('1.5')
    # ... ~80 dòng logic tính tiền

# services.py — canonical path (đúng nhưng không được dùng)
def perform_checkout(booking) -> dict:
    pricing = calculate_checkout_price(booking)
    # ... update DB + return
```

Nếu `services.py` được sửa (thêm logic hoặc fix bug), `views.py` sẽ không nhận update → logic drift trong production.

**Fix:** Trong `views.py checkout()`, xóa toàn bộ inline logic, thay bằng:
```python
from . import services
result = services.perform_checkout(booking)
```

---

### BUG-03 | HIGH | `validate_checkin()` không kiểm tra time window — bypass qua API trực tiếp

**File:** [booking-service/bookings/services.py](../../../booking-service/bookings/services.py)  
**Vị trí:** Function `validate_checkin()` ~line 113

**Vấn đề:**
```python
def validate_checkin(booking) -> str | None:
    if booking.check_in_status != 'not_checked_in':
        return 'Only confirmed bookings can be checked in'
    return None  # ← Không có time check!
```

Time window check (15 phút sớm) CHỈ tồn tại trong `esp32.py` (hardware path). Khi gọi trực tiếp `POST /bookings/{id}/checkin/` qua API, không có gì chặn check-in 3 giờ trước giờ bắt đầu, hoặc check-in sau khi booking đã hết giờ.

**Fix:** Thêm vào `validate_checkin()`:
```python
from django.utils import timezone

now = timezone.now()
EARLY_MINUTES = 15

if now < booking.start_time - timedelta(minutes=EARLY_MINUTES):
    return f'Too early to check in. Earliest: {booking.start_time - timedelta(minutes=EARLY_MINUTES)}'
if now > booking.end_time:
    return 'Booking has expired'
```

---

### BUG-04 | HIGH | Race condition: không có `select_for_update` khi tạo booking

**File:** [booking-service/bookings/serializers.py](../../../booking-service/bookings/serializers.py)  
**Vị trí:** `CreateBookingSerializer.create()`

**Vấn đề:** Không có transaction lock. Hai request đồng thời cho cùng `slot_id` đều pass qua availability check (HTTP call sang parking-service) trong cùng khoảnh khắc, đều tạo Booking thành công.

```python
# serializers.py — NO select_for_update, NO atomic transaction
def create(self, validated_data):
    # Check slot availability → HTTP call → parking-service (no lock)
    # Create Booking → DB insert (no lock)
    # PATCH parking-service set reserved → fire and forget
```

Hệ quả: Hai booking cho cùng một slot tồn tại trong DB với `check_in_status='not_checked_in'`.

**Fix:**
1. Wrap creation trong `transaction.atomic()`
2. Dùng `select_for_update()` trên bảng Booking khi query slot hiện tại
3. Thêm DB-level unique partial index (xem DB-01)

---

### BUG-05 | HIGH | `auto_cancel_unpaid_bookings` không PATCH parking-service để release slot

**File:** [booking-service/bookings/tasks.py](../../../booking-service/bookings/tasks.py)  
**Vị trí:** Function `auto_cancel_unpaid_bookings()` ~line 44

**Vấn đề:**
```python
@shared_task
def auto_cancel_unpaid_bookings():
    bookings = Booking.objects.filter(
        payment_method='online',
        payment_status='pending',
        check_in_status='not_checked_in',
        created_at__lt=cutoff,
    )
    for booking in bookings:
        booking.check_in_status = 'cancelled'
        booking.save()
        broadcast_slot_status(slot_id=str(booking.slot_id), slot_status='available', ...)
        # ← THIẾU: requests.patch(PARKING_SERVICE/parking/slots/{id}/, {'status': 'available'})
```

Booking bị cancel trong `booking-service` DB và realtime broadcast `available`, nhưng `parking-service` DB vẫn giữ slot ở trạng thái `reserved`. Sau khi service restart hoặc reload, slot vẫn bị block.

**Fix:** Thêm HTTP call sau khi set `cancelled`:
```python
import requests
PARKING_URL = settings.PARKING_SERVICE_URL
try:
    requests.patch(
        f"{PARKING_URL}/parking/slots/{booking.slot_id}/",
        json={"status": "available"},
        headers={"X-Gateway-Secret": settings.GATEWAY_SECRET},
        timeout=5,
    )
except Exception as e:
    logger.warning("Failed to release slot %s: %s", booking.slot_id, e)
```

---

### BUG-06 | HIGH | `check_no_show_bookings` bỏ sót online-payment users

**File:** [booking-service/bookings/tasks.py](../../../booking-service/bookings/tasks.py)  
**Vị trí:** Function `check_no_show_bookings()` ~line 84

**Vấn đề:**
```python
overdue = Booking.objects.filter(
    package_type='hourly',
    payment_method='on_exit',   # ← CHỈ cash/on_exit
    check_in_status='not_checked_in',
    start_time__lt=cutoff,
)
```

Users đặt online (trả tiền trước) mà không check-in đúng giờ → KHÔNG bao giờ bị đánh dấu `no_show`. Slot vẫn bị giữ `reserved`. Dữ liệu thống kê no-show của hệ thống sẽ thiếu.

**Fix:** Xóa filter `payment_method='on_exit'`:
```python
overdue = Booking.objects.filter(
    package_type='hourly',
    check_in_status='not_checked_in',
    start_time__lt=cutoff,
).exclude(check_in_status__in=['cancelled', 'checked_out'])
```

---

### BUG-07 | HIGH | Camera monitor ghi đè `reserved` → `available`

**File:** [ai-service-fastapi/app/engine/camera_monitor.py](../../../ai-service-fastapi/app/engine/camera_monitor.py)  
**Vị trí:** Function `_push_slot_updates()` ~line 182

**Vấn đề:**
```python
async def _push_slot_updates(session, updates):
    for slot_id, new_status in updates.items():
        await session.patch(
            f"{PARKING_URL}/parking/slots/{slot_id}/update-status/",
            json={"status": new_status},   # ← "available" hoặc "occupied"
        )
        # Không check xem slot hiện tại là "reserved" không
```

Scan cycle 30 giây: YOLO thấy ô trống → gửi `available` → parking-service ghi `available` → overwrite `reserved`. Booking hợp lệ đang chờ xe đến bị mất trạng thái reserved.

**Fix:** Trước khi push, query trạng thái hiện tại của slot:
```python
# Fetch current status
resp = await session.get(f"{PARKING_URL}/parking/slots/{slot_id}/")
current = resp.json().get("status")
if current == "reserved":
    logger.debug("Slot %s is reserved, skipping camera update", slot_id)
    continue
await session.patch(...)
```
Hoặc tốt hơn: parking-service tự guard — `update-status` endpoint từ chối ghi đè `reserved` bằng `available` (chỉ `occupied` được phép).

---

### BUG-08 | MEDIUM | Payment service gọi sai URL của booking-service

**File:** [payment-service-fastapi/app/routers/payment.py](../../../payment-service-fastapi/app/routers/payment.py)  
**Vị trí:** ~line 90

**Vấn đề:**
```python
# payment-service — sai path
await client.patch(
    f"{settings.BOOKING_SERVICE_URL}/api/bookings/{booking_id}/payment-status/",
    ...
)
# booking-service route thực tế:
# /bookings/{id}/payment-status/  (không có prefix /api/)
```

Mọi callback từ payment-service sẽ trả về 404. `payment_status` không bao giờ được update sau khi payment hoàn thành.

**Fix:** Sửa URL thành `/bookings/{booking_id}/payment-status/`

---

### BUG-09 | MEDIUM | ESP32 device registry bị mất sau restart

**File:** [ai-service-fastapi/app/routers/esp32.py](../../../ai-service-fastapi/app/routers/esp32.py)  
**Vị trí:** Dict `_esp32_devices` (module-level)

**Vấn đề:**
```python
_esp32_devices: dict[str, dict] = {}  # In-memory only
```

2 device mặc định được re-seed khi startup. Nhưng bất kỳ ESP32 nào đăng ký động qua API (`/register/`) đều biến mất sau restart. Nếu ai deploy/restart service thường xuyên, device config mất liên tục.

**Fix:** Persist registry vào Redis hoặc DB table `esp32_device`.

---

### BUG-10 | MEDIUM | Cash session in-memory — mất khi service restart

**File:** [ai-service-fastapi/app/engine/cash_session.py](../../../ai-service-fastapi/app/engine/cash_session.py)

**Vấn đề:** Khách đã bỏ tiền vào → AI service restart → session mất → checkout bị block. TTL 30 phút.

**Fix:** Persist active sessions vào Redis hash với TTL 30 phút:
```python
redis.setex(f"cash_session:{session_id}", 1800, json.dumps(session_data))
```

---

### BUG-11 | LOW | Error message sai: "confirmed" không phải trạng thái hợp lệ

**File:** [booking-service/bookings/services.py](../../../booking-service/bookings/services.py)  
**Vị trí:** `validate_checkin()` ~line 113

**Vấn đề:**
```python
return 'Only confirmed bookings can be checked in'
# CHECK_IN_STATUS choices: not_checked_in, checked_in, checked_out, no_show, cancelled
# Không có "confirmed"
```

**Fix:**
```python
return 'Booking must be in not_checked_in status to check in'
```

---

### BUG-12 | LOW | `_get_hourly_price()` bị duplicate trong views.py và services.py

**File:** [booking-service/bookings/views.py](../../../booking-service/bookings/views.py) ~line 244  
**File:** [booking-service/bookings/services.py](../../../booking-service/bookings/services.py) ~line 19

**Vấn đề:** Cả hai file đều có hàm giống hệt nhau với hardcode fallback `15000/5000`. Nếu giá mặc định thay đổi, phải sửa 2 nơi.

**Fix:** Xóa `_get_hourly_price()` trong `views.py`; import hàm từ `services.py`.

---

## 6. Missing Business Logic

### MISSING-01 | HIGH | Chatbot không có intent `operating_hours`

**Vấn đề:** User hỏi "Bãi xe mở cửa mấy giờ?", "Giờ hoạt động thế nào?" → intent = `unknown`.

Confirmed từ code — `_keyword_classify` không có key `operating_hours`. Danh sách 15 intents trong LLM prompt không có intent này. `ParkingLot` model không có field `operating_hours`.

**Fix cần:**
1. Thêm field `operating_hours: str` (hoặc JSON) vào `ParkingLot` model
2. Thêm intent `operating_hours` vào keyword map và LLM prompt
3. Thêm action handler trong `action_service.py`
4. Thêm response template trong `response_service.py`

---

### MISSING-02 | HIGH | `PackagePricing` không có seed data

**Vấn đề:** 
- `init-mysql.sql` không INSERT row nào vào `package_pricing`
- `seed_e2e_data.py` không có hàm `seed_pricing()`
- Nếu bảng rỗng: `services.get_hourly_price()` → fallback 15000/5000; chatbot `_format_pricing()` → hardcode "20.000đ/giờ"

```python
# chatbot — response_service.py
if not pricing:  # Bảng rỗng
    text += "• Ô tô: 20.000đ/giờ\n"   # Hardcode, có thể lỗi thời
    text += "• Xe máy: 5.000đ/giờ\n"
```

Frontend Admin page (`AdminConfigPage.tsx`) cho phép cấu hình giá nhưng nếu DB rỗng, mọi booking đều dùng fallback.

**Fix:** Thêm vào `seed_e2e_data.py` và `init-mysql.sql`:
```sql
INSERT INTO package_pricing (id, package_type, vehicle_type, price, duration_days, created_at, updated_at)
VALUES
  (UUID(), 'hourly',   'Car',      15000, NULL,  NOW(), NOW()),
  (UUID(), 'hourly',   'Motorbike', 5000, NULL,  NOW(), NOW()),
  (UUID(), 'daily',    'Car',      80000,    1,  NOW(), NOW()),
  (UUID(), 'daily',    'Motorbike',30000,    1,  NOW(), NOW()),
  (UUID(), 'weekly',   'Car',     400000,    7,  NOW(), NOW()),
  (UUID(), 'weekly',   'Motorbike',150000,   7,  NOW(), NOW()),
  (UUID(), 'monthly',  'Car',    1200000,   30,  NOW(), NOW()),
  (UUID(), 'monthly',  'Motorbike',500000,  30,  NOW(), NOW());
```

---

### MISSING-03 | MEDIUM | Không có `booking_status` field riêng biệt

**Vấn đề:** Model hiện tại dùng `check_in_status` cho cả trạng thái vòng đời booking:
- `not_checked_in` = booking tồn tại (có thể pending payment HOẶC đã paid)
- Không phân biệt được "chờ thanh toán" vs "đã xác nhận"

Seed data trong `seed_e2e_data.py` dùng field `status` (không tồn tại trong model — dùng `check_in_status`). `PARKING_SYSTEM_PLAN.md` note rằng đây là vấn đề đã biết.

**Fix:** Thêm field:
```python
BOOKING_STATUS_CHOICES = [
    ('pending', 'Pending Payment'),
    ('confirmed', 'Confirmed'),
    ('cancelled', 'Cancelled'),
    ('expired', 'Expired'),
    ('completed', 'Completed'),
]
booking_status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending')
```

---

### MISSING-04 | MEDIUM | `Zone.available_slots` / `ParkingLot.available_slots` không tự đồng bộ

**File:** [parking-service/infrastructure/models.py](../../../parking-service/infrastructure/models.py)

**Vấn đề:** Cả hai field là integer counters thủ công — không có Django signal hay DB trigger tự update khi `CarSlot.status` thay đổi. Sau N giờ hoạt động, counter bị drift.

**Fix:** Thêm Django `post_save` signal trên `CarSlot`:
```python
@receiver(post_save, sender=CarSlot)
def update_available_slots(sender, instance, **kwargs):
    zone = instance.zone
    zone.available_slots = CarSlot.objects.filter(zone=zone, status='available').count()
    zone.save(update_fields=['available_slots'])
    # Tương tự propagate lên ParkingLot
```

---

### MISSING-05 | MEDIUM | Không có rollback khi booking tạo OK nhưng slot PATCH thất bại

**File:** [booking-service/bookings/serializers.py](../../../booking-service/bookings/serializers.py)

**Vấn đề:**
```python
def create(self, validated_data):
    booking = Booking.objects.create(...)   # Step 1: booking tạo thành công
    try:
        requests.patch(PARKING_URL/slots/{id}/, {'status': 'reserved'})  # Step 2
    except Exception:
        logger.warning("Failed to update slot status")   # ← Silent fail, no rollback
```

Nếu parking-service down tại thời điểm booking: booking tồn tại trong DB, slot vẫn `available` trong parking DB. Có thể bị đặt trùng bởi người khác.

**Fix:** Hoặc:
1. Rollback booking nếu slot PATCH thất bại (xóa booking vừa tạo và return error)
2. Hoặc implement outbox pattern / saga compensating transaction

---

## 7. Database Issues

### DB-01 | HIGH | Thiếu unique constraint ngăn double-booking

**Vấn đề:** Không có partial unique index ngăn 2 booking active cho cùng 1 slot:
```sql
-- Chưa tồn tại:
CREATE UNIQUE INDEX booking_slot_active
ON booking(slot_id)
WHERE check_in_status IN ('not_checked_in', 'checked_in');
```

MySQL không hỗ trợ partial index syntax này trực tiếp. Cần dùng generated column:
```sql
ALTER TABLE booking
ADD COLUMN active_slot_key VARCHAR(50) AS (
    IF(check_in_status IN ('not_checked_in', 'checked_in'), slot_id, NULL)
) VIRTUAL,
ADD UNIQUE INDEX uq_slot_active (active_slot_key);
```

Hoặc application-level: thêm `unique_together` tạm thời + `select_for_update`.

---

### DB-02 | MEDIUM | `ParkingLot.price_per_hour` tồn tại nhưng không được dùng

**Vấn đề:** `ParkingLot` model có field `price_per_hour` nhưng `booking-service` đọc giá từ `PackagePricing` table. Hai nguồn giá không đồng bộ.

Admin có thể config giá ở `price_per_hour` nhưng hệ thống không apply.

**Fix:** Deprecate `ParkingLot.price_per_hour` trong model comments; hoặc sync nó vào `PackagePricing` khi update.

---

### DB-03 | LOW | `seed_e2e_data.py` insert `vehicle_type='car'` (lowercase) thay vì `'Car'`

**File:** [seed_e2e_data.py](../../../seed_e2e_data.py)  
**Vị trí:** Line ~281

**Vấn đề:**
```python
"car",   # ← lowercase
# PackagePricing.vehicle_type choices: ('Car', 'Car'), ('Motorbike', 'Motorbike')
```

Booking do seed script tạo có `vehicle_type='car'`, nhưng `PackagePricing` được query theo `vehicle_type='Car'` → query sẽ fail → giá fallback về hardcode ngay cả khi bảng có data.

**Fix:** Sửa seed script: `"Car"` và `"Motorbike"` (capitalize đúng).

---

## 8. Frontend / Cross-Service Issues

### FE-01 | MEDIUM | `PriceSummary.tsx` hardcode giá không fetch từ API

**File:** `spotlove-ai/src/components/booking/PriceSummary.tsx`  
Documented trong `PARKING_SYSTEM_PLAN.md` Section 3.2

**Vấn đề:** `FALLBACK_PRICES` const trong component có giá hardcode. Nếu admin đổi giá qua `PackagePricing` API, user thấy giá cũ cho đến khi frontend được deploy lại.

**Fix:** Fetch từ `GET /bookings/packagepricings/` khi component mount.

---

### FE-02 | LOW | Payment service fake URL gateway

**File:** [payment-service-fastapi/app/routers/payment.py](../../../payment-service-fastapi/app/routers/payment.py)

**Vấn đề:**
```python
payment.payment_url = f"https://payment-gateway.example.com/pay/{payment.transaction_id}"
# verify_payment: # TODO: Verify with payment gateway
```

Toàn bộ online payment flow là stub. Không có tích hợp thực với MoMo/VNPay/ZaloPay.

**Note:** Đây là feature gap, không phải bug kỹ thuật — cần Architect quyết định payment provider.

---

## 9. Checklist cho Implementer

- [ ] **BUG-01**: Sửa `'occupied'` → `'reserved'` trong `views.py create()` broadcast
- [ ] **BUG-02**: Xóa inline checkout logic trong `views.py`, gọi `services.perform_checkout()`
- [ ] **BUG-03**: Thêm time-window validation vào `services.validate_checkin()`
- [ ] **BUG-04**: Wrap `CreateBookingSerializer.create()` trong `transaction.atomic()` + `select_for_update()`
- [ ] **BUG-05**: Thêm `requests.patch` tới parking-service trong `auto_cancel_unpaid_bookings`
- [ ] **BUG-06**: Xóa filter `payment_method='on_exit'` trong `check_no_show_bookings`
- [ ] **BUG-07**: Thêm guard trong `camera_monitor._push_slot_updates()` — skip nếu slot đang `reserved`
- [ ] **BUG-08**: Sửa URL path trong `payment-service` từ `/api/bookings/` → `/bookings/`
- [ ] **BUG-09**: Persist ESP32 device registry vào Redis
- [ ] **BUG-10**: Persist cash sessions vào Redis
- [ ] **BUG-11**: Sửa error message trong `validate_checkin()`
- [ ] **BUG-12**: Xóa `_get_hourly_price()` duplicate trong `views.py`
- [ ] **MISSING-01**: Thêm intent `operating_hours` vào chatbot
- [ ] **MISSING-02**: Seed `PackagePricing` trong `init-mysql.sql` và `seed_e2e_data.py`
- [ ] **MISSING-03**: Thêm field `booking_status` vào `Booking` model (migration cần)
- [ ] **MISSING-04**: Thêm Django signals update `available_slots` counter
- [ ] **MISSING-05**: Xử lý failure khi PATCH parking-service trong serializer
- [ ] **DB-01**: Thêm unique constraint ngăn double-booking cùng slot
- [ ] **DB-02**: Clarify `ParkingLot.price_per_hour` — unused hoặc sync vào PackagePricing
- [ ] **DB-03**: Sửa `vehicle_type` trong `seed_e2e_data.py` → `'Car'`/'`Motorbike'`
- [ ] **FE-01**: `PriceSummary.tsx` fetch giá từ API thay vì hardcode

**Migration cần:**
- `MISSING-03` → Django migration thêm field `booking_status`
- `DB-01` → Migration thêm generated column + unique index
- `MISSING-01` → Cần thêm field `operating_hours` vào `ParkingLot` (parking-service migration)

**Env vars cần verify:**
- `PARKING_SERVICE_URL` — booking-service tasks.py cần để release slot
- `GATEWAY_SECRET` — booking-service dùng khi gọi inter-service
- `BOOKING_SERVICE_URL` — payment-service cần URL đúng

---

## 10. Nguồn

| # | File / URL | Mô tả | Date |
|---|------------|-------|------|
| 1 | `booking-service/bookings/views.py` | BookingViewSet toàn bộ | 2025-07-17 |
| 2 | `booking-service/bookings/services.py` | Business logic layer | 2025-07-17 |
| 3 | `booking-service/bookings/serializers.py` | CreateBookingSerializer | 2025-07-17 |
| 4 | `booking-service/bookings/tasks.py` | Celery tasks | 2025-07-17 |
| 5 | `booking-service/bookings/models.py` | Booking + PackagePricing | 2025-07-17 |
| 6 | `ai-service-fastapi/app/routers/esp32.py` | ESP32 gate flow ~1200 lines | 2025-07-17 |
| 7 | `ai-service-fastapi/app/engine/camera_monitor.py` | Camera background worker | 2025-07-17 |
| 8 | `ai-service-fastapi/app/engine/cash_session.py` | Cash session manager | 2025-07-17 |
| 9 | `parking-service/infrastructure/models.py` | Infrastructure schema | 2025-07-17 |
| 10 | `payment-service-fastapi/app/routers/payment.py` | Payment gateway stub | 2025-07-17 |
| 11 | `chatbot-service-fastapi/app/application/services/` | Chatbot pipeline (4 files) | 2025-07-17 |
| 12 | `seed_e2e_data.py` | Seed script (thiếu pricing) | 2025-07-17 |
| 13 | `init-mysql.sql` | DB init (chatbot only, thiếu pricing) | 2025-07-17 |
| 14 | `PARKING_SYSTEM_PLAN.md` | Tài liệu kế hoạch hệ thống | 2025-07-17 |
| 15 | `docker-compose.yml` | Service ports + env vars | 2025-07-17 |

---

## 11. Tóm tắt Priority Matrix

| ID | Mức độ | Ảnh hưởng thực tế |
|----|--------|-------------------|
| BUG-01 | 🔴 HIGH | Hiển thị slot map sai ngay sau booking |
| BUG-02 | 🔴 HIGH | Logic drift checkout giữa 2 nơi |
| BUG-03 | 🔴 HIGH | Check-in bất kỳ lúc nào qua API bypass |
| BUG-04 | 🔴 HIGH | Double-booking cùng slot |
| BUG-05 | 🔴 HIGH | Slot bị kẹt `reserved` sau cancel |
| BUG-06 | 🔴 HIGH | No-show online payment không được detect |
| BUG-07 | 🔴 HIGH | Camera xóa trạng thái `reserved` hợp lệ |
| MISSING-02 | 🔴 HIGH | Toàn bộ pricing dùng hardcode nếu DB chưa seed |
| DB-01 | 🔴 HIGH | Không có DB-level guard cho double-booking |
| BUG-08 | 🟡 MEDIUM | Payment callback không bao giờ đến được booking-service |
| BUG-09 | 🟡 MEDIUM | ESP32 config mất sau restart |
| BUG-10 | 🟡 MEDIUM | Cash payment session mất sau restart |
| MISSING-01 | 🟡 MEDIUM | Chatbot mù với câu hỏi giờ hoạt động |
| MISSING-03 | 🟡 MEDIUM | Thiếu booking lifecycle status field |
| MISSING-04 | 🟡 MEDIUM | Counter available_slots drift |
| MISSING-05 | 🟡 MEDIUM | Không rollback khi inter-service PATCH fail |
| FE-01 | 🟡 MEDIUM | Giá hiển thị trên FE có thể lỗi thời |
| DB-02 | 🟠 LOW | price_per_hour trên ParkingLot không dùng |
| DB-03 | 🟠 LOW | Seed data vehicle_type lowercase |
| BUG-11 | 🟠 LOW | Error message misleading |
| BUG-12 | 🟠 LOW | Code duplicate nhỏ |
| FE-02 | 🟠 LOW | Payment stub (feature gap) |
