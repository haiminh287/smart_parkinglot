# Research Report: Check-in Time Validation & Booking Creation API

**Task:** Ad-hoc research | **Date:** 2026-04-14 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **Hai lớp time validation khác nhau**: AI service (esp32.py) cho phép check-in **15 phút** trước `start_time`, nhưng booking-service (views.py + services.py) cho phép **30 phút** trước. Booking-service là lớp cuối cùng gọi — nên 30 phút là giới hạn thực tế.
> 2. **Booking creation API**: `POST /bookings/` với headers `X-Gateway-Secret` + `X-User-ID` + `X-User-Email`. Body cần: `vehicle_id`, `zone_id`, `parking_lot_id`, `start_time`, `end_time` (optional), `slot_id` (optional), `package_type`, `payment_method`.
> 3. **72 available slots**: V1-15 đến V1-72 (58 car), V2-09 đến V2-20 (12 moto), G-04 đến G-05 (2 car).

---

## 2. Check-in Time Validation Logic (CHI TIẾT)

### 2.1 AI Service — ESP32 Router (Lớp 1)

**File:** `backend-microservices/ai-service-fastapi/app/routers/esp32.py`

```python
# Line 97
CHECK_IN_EARLY_MINUTES = 15  # Allow 15 min early check-in

# Lines 773-786 (inside esp32_check_in)
start_time = dp.parse(booking.get("startTime", booking.get("start_time", "")))
now = datetime.now(tz=timezone.utc)
earliest = start_time - timedelta(minutes=CHECK_IN_EARLY_MINUTES)
if now < earliest:
    remaining = int((earliest - now).total_seconds() / 60)
    return ESP32Response(
        success=False,
        event=GateEvent.CHECK_IN_FAILED,
        barrier_action=BarrierAction.CLOSE,
        message=f"❌ Chưa đến giờ check-in. Còn {remaining} phút.",
        ...
    )
```

**Kết quả**: AI service chặn check-in sớm hơn **15 phút** trước `start_time`. Nếu parse thất bại → bỏ qua kiểm tra (pass).

### 2.2 Booking Service — Views + Services (Lớp 2)

**File:** `backend-microservices/booking-service/bookings/views.py` (lines 132-139)

```python
if booking.start_time and timezone.now() < booking.start_time - timedelta(
    minutes=30
):
    return Response(
        {"message": "Chưa đến giờ check-in. Vui lòng đến trong vòng 30 phút trước giờ đặt."},
        status=status.HTTP_400_BAD_REQUEST,
    )
```

**File:** `backend-microservices/booking-service/bookings/services.py` (line 175-178)

```python
def validate_checkin(booking: Booking) -> str | None:
    if booking.check_in_status != "not_checked_in":
        return "Only confirmed bookings can be checked in"
    if booking.start_time and timezone.now() < booking.start_time - timedelta(minutes=30):
        return "Chưa đến giờ check-in. Vui lòng đến trong vòng 30 phút trước giờ đặt."
    return None
```

**Kết quả**: Booking service cho phép check-in **30 phút** trước `start_time`.

### 2.3 Luồng kiểm tra

```
ESP32 button → AI service esp32/check-in/
  → Step 2: Validate time window (15 min early) ← AI-SIDE CHECK
  → Step 5: Call booking-service POST /bookings/{id}/checkin/
                → views.py checkin() → 30 min early ← BOOKING-SIDE CHECK
```

**⚠️ Mâu thuẫn**: AI cho phép 15 phút, booking-service cho phép 30 phút. Vì AI check trước, nếu `now` nằm giữa `start_time - 30min` và `start_time - 15min`, AI service sẽ từ chối dù booking-service có thể chấp nhận. Giới hạn thực tế khi đi qua AI service: **15 phút trước start_time**.

**→ Nếu cần check-in ngay lập tức**: đặt `start_time` ≤ `now + 15 phút`.

### 2.4 Các kiểm tra khác trong check-in flow

| Kiểm tra | Nơi kiểm tra | Chi tiết |
|---------|-------------|---------|
| `check_in_status == "not_checked_in"` | AI + Booking | Phải chưa check-in |
| Time window | AI (15min) + Booking (30min) | Sớm nhất: `start_time - N phút` |
| Payment (online) | AI service | `payment_status == "completed"` hoặc `payment_method == "on_exit"` |
| Plate match | AI service | Chỉ khi real camera — test/virtual camera bỏ qua |

---

## 3. Booking Creation API

### 3.1 Endpoint

```
POST http://localhost:8002/bookings/
```

Hoặc qua Gateway:
```
POST http://localhost:8000/api/bookings/
```

Gateway routing: `bookings/` → `booking-service` (protected route, requires auth).

### 3.2 Authentication Headers

```
X-Gateway-Secret: gateway-internal-secret-key
X-User-ID: <user_uuid>
X-User-Email: <user_email>
Content-Type: application/json
```

- `X-Gateway-Secret` = `gateway-internal-secret-key` (from `.env`)
- `X-User-ID` = UUID of the user (no hyphens, 32-char hex format in DB, but dashed UUID also works)
- `X-User-Email` = user email (used for denormalized storage)

### 3.3 Request Body (CreateBookingSerializer)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `vehicle_id` | string (UUID or plate) | ✅ | UUID of vehicle, or license plate string |
| `zone_id` | UUID | ✅ | Zone UUID |
| `parking_lot_id` | UUID | ✅ | Parking lot UUID |
| `start_time` | ISO 8601 datetime | ✅ | When booking starts |
| `end_time` | ISO 8601 datetime | ❌ | When booking ends (for hourly) |
| `slot_id` | UUID | ❌ | Specific slot UUID (optional) |
| `package_type` | string | ❌ | `hourly` (default), `daily`, `weekly`, `monthly` |
| `payment_method` | string | ❌ | `on_exit` (default), `online` |

**Lưu ý quan trọng:**
- Nếu `slot_id` được cung cấp, serializer sẽ kiểm tra slot conflict (cùng slot, thời gian trùng, status `not_checked_in` hoặc `checked_in`).
- Price được tự động tính từ `PackagePricing` table.
- `qr_code_data` được tự động generate: `{"booking_id": "<uuid>", "user_id": "<uuid>", "timestamp": "<iso>"}`
- Slot được tự động đánh dấu `reserved` trong parking-service sau khi booking tạo.

### 3.4 Response (201 Created)

```json
{
  "booking": {
    "id": "uuid",
    "userId": "uuid",
    "vehicle": { "id": "...", "licensePlate": "...", "vehicleType": "Car" },
    "packageType": "hourly",
    "startTime": "2026-04-14T...",
    "endTime": "2026-04-14T...",
    "parkingLot": { "id": "...", "name": "..." },
    "floor": { ... },
    "zone": { ... },
    "carSlot": { "id": "...", "code": "V1-15", "status": "reserved" },
    "paymentType": "on_exit",
    "paymentStatus": "pending",
    "checkInStatus": "not_checked_in",
    "price": "20000.00",
    "qrCodeData": "{...}",
    "createdAt": "..."
  },
  "message": "Booking created successfully",
  "qrCode": "{...}"
}
```

---

## 4. Known IDs (from seed scripts)

### 4.1 Parking Lot & Zone IDs

| Entity | ID (hex, no hyphens) | UUID (with hyphens) | Name |
|--------|---------------------|---------------------|------|
| Vincom Parking Lot | `3f54a675e64f4ea9a295ae8b068cc278` | `3f54a675-e64f-4ea9-a295-ae8b068cc278` | Vincom Center Parking |
| ParkSmart Tower | `bc1a3e4a0b244510892d2d4b2b64c7b5` | `bc1a3e4a-0b24-4510-892d-2d4b2b64c7b5` | ParkSmart Tower |
| Zone V1 (Car) | `dd657628ec4c477283e0f9b9a85e623d` | `dd657628-ec4c-4772-83e0-f9b9a85e623d` | Zone V1 |
| Zone V2 (Moto) | `ff5416ec518c41439db3fac3e0974b0a` | `ff5416ec-5184-41439db3-fac3e0974b0a` | Zone V2 |
| Floor B1 | `418fa423a86d4f26a29f653bf522c933` | `418fa423-a86d-4f26-a29f-653bf522c933` | B1 (level -1) |

### 4.2 Test Users (from seed scripts)

| Email | Password | Notes |
|-------|----------|-------|
| `chattest@parksmart.com` | `Test@1234` | Owns reserved slots |
| `testdriver@parksmart.com` | `Test@1234` | Owns occupied slots |
| `admin@example.com` | (varies) | Admin account |
| `user@example.com` | `user123` | Regular user |
| `e2e_playwright@parksmart.com` | `TestPass123!` | E2E test user |

---

## 5. Available Slot Codes (72 slots)

Theo `seed_unity_slots.py`, phân bổ slot (97 total):

### Zone V1 (Car) — 72 slots total
| Status | Slot Codes | Count |
|--------|-----------|-------|
| occupied | V1-01 → V1-08 | 8 |
| reserved | V1-09 → V1-14 | 6 |
| **available** | **V1-15 → V1-72** | **58** |

### Zone V2 (Motorbike) — 20 slots total
| Status | Slot Codes | Count |
|--------|-----------|-------|
| occupied | V2-01 → V2-04 | 4 |
| reserved | V2-05 → V2-08 | 4 |
| **available** | **V2-09 → V2-20** | **12** |

### Zone G (Garage/Car) — 5 slots total
| Status | Slot Codes | Count |
|--------|-----------|-------|
| occupied | G-01 → G-02 | 2 |
| reserved | G-03 | 1 |
| **available** | **G-04 → G-05** | **2** |

**⚠️ LƯU Ý**: `slot_id` (UUID) cần từ DB, không phải `slot_code`. Để dùng slot_id, cần query:
```sql
SELECT id, code FROM car_slot WHERE zone_id='dd657628ec4c477283e0f9b9a85e623d' AND status='available' ORDER BY code LIMIT 10;
```

Hoặc qua API:
```
GET http://localhost:8003/parking/slots/?zone_id=dd657628-ec4c-4772-83e0-f9b9a85e623d&status=available
Headers: X-Gateway-Secret: gateway-internal-secret-key
```

---

## 6. Example Booking Creation Payloads

### 6.1 Via API (curl / httpx)

```bash
# Direct to booking-service (port 8002)
curl -X POST http://localhost:8002/bookings/ \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Secret: gateway-internal-secret-key" \
  -H "X-User-ID: <user_uuid_hex_or_dashed>" \
  -H "X-User-Email: chattest@parksmart.com" \
  -d '{
    "vehicle_id": "<vehicle_uuid>",
    "zone_id": "dd657628-ec4c-4772-83e0-f9b9a85e623d",
    "parking_lot_id": "3f54a675-e64f-4ea9-a295-ae8b068cc278",
    "start_time": "2026-04-14T15:00:00Z",
    "end_time": "2026-04-14T19:00:00Z",
    "slot_id": "<slot_uuid_of_available_slot>",
    "package_type": "hourly",
    "payment_method": "on_exit"
  }'
```

### 6.2 For immediate check-in (start_time = now or past)

Set `start_time` to current time or slightly in the past to make check-in immediately possible:

```json
{
  "vehicle_id": "<vehicle_uuid>",
  "zone_id": "dd657628-ec4c-4772-83e0-f9b9a85e623d",
  "parking_lot_id": "3f54a675-e64f-4ea9-a295-ae8b068cc278",
  "start_time": "2026-04-14T10:00:00Z",
  "end_time": "2026-04-14T14:00:00Z",
  "package_type": "hourly",
  "payment_method": "on_exit"
}
```

### 6.3 Via direct DB insert (seed script pattern)

From `seed_unity_slots.py`:

```python
bid = uuid.uuid4().hex
qr_data = json.dumps({
    "booking_id": bid,
    "slot_code": code,
    "license_plate": plate,
    "parking_lot_id": LOT_ID,
})

cursor.execute("""INSERT INTO booking
    (id, user_id, user_email,
     vehicle_id, vehicle_license_plate, vehicle_type,
     parking_lot_id, parking_lot_name,
     floor_id, floor_level,
     zone_id, zone_name,
     slot_id, slot_code,
     package_type, start_time, end_time,
     payment_method, payment_status, price,
     check_in_status, checked_in_at, checked_out_at,
     qr_code_data, late_fee_applied,
     created_at, updated_at)
   VALUES (...)""",
    (bid, user_id, user_email,
     vehicle_id, plate, "Car",
     LOT_ID, LOT_NAME,
     FLOOR_ID, FLOOR_LEVEL,
     zone_id, zone_name,
     slot_id, slot_code,
     "hourly", start_time, end_time,
     "cash", "pending", 20000.00,
     "not_checked_in", None, None,
     qr_data, False,
     now, now))
```

**QR code format cho ESP32 check-in:**
```json
{"booking_id": "<uuid>", "user_id": "<uuid>", "timestamp": "<iso>"}
```

(Cũng chấp nhận format cũ từ seed: `{"booking_id": "...", "slot_code": "...", "license_plate": "...", "parking_lot_id": "..."}`)

---

## 7. ⚠️ Gotchas & Known Issues

- [ ] **[WARNING]** Mâu thuẫn thời gian: AI service = 15 phút, booking-service = 30 phút. Khi đi qua AI flow, giới hạn thực tế = 15 phút.
- [ ] **[NOTE]** `slot_id` là optional trong booking API. Nếu không cung cấp, booking vẫn tạo được nhưng không có slot cụ thể.
- [ ] **[NOTE]** `payment_method: "on_exit"` bỏ qua payment check khi check-in. Dùng `"online"` thì phải có `payment_status: "completed"`.
- [ ] **[NOTE]** Slot UUID phải query từ DB hoặc parking-service API — không thể suy từ slot code.
- [ ] **[NOTE]** Booking serializer kiểm tra slot conflict: nếu slot đã có booking active (`not_checked_in` hoặc `checked_in`) trong thời gian trùng, sẽ reject.

---

## 8. Nguồn

| # | File | Mô tả | Key Lines |
|---|------|-------|-----------|
| 1 | `ai-service-fastapi/app/routers/esp32.py` | ESP32 check-in endpoint + time validation | L97, L666-960 |
| 2 | `booking-service/bookings/views.py` | Booking views + checkin validation | L120-155 |
| 3 | `booking-service/bookings/services.py` | validate_checkin helper | L173-178 |
| 4 | `booking-service/bookings/serializers.py` | CreateBookingSerializer | L148-310 |
| 5 | `booking-service/bookings/models.py` | Booking model fields | Full file |
| 6 | `booking-service/bookings/urls.py` | URL routing | Full file |
| 7 | `seed_unity_slots.py` | Slot definitions (97 total) | L100-145 |
| 8 | `shared/gateway_permissions.py` | Auth mechanism | Full file |
| 9 | `gateway-service-go/internal/config/config.go` | Gateway routing | L130-165 |
