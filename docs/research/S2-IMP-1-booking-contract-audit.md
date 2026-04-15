# Research Report: FE/BE Booking Contract Audit — S2-IMP-1

**Task:** S2-IMP-1 Step 0 | **Date:** 2026-04-15 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. Model `Booking` đã có ĐẦY ĐỦ denormalized fields (27 fields total) — **không cần migration**.
> 2. `BookingSerializer` hiện tại gây **tối đa 6 HTTP calls + 5 DB UPDATE per booking** trong READ path do "lazy denormalization" pattern.
> 3. FE `mapBookingResponse()` trong `bookingSlice.ts` đã handle cả nested objects LẪN flat fields — serializer có thể chuyển sang flat fields ngay mà FE không cần sửa.
> 4. `get_zone()` **LUÔN** gọi HTTP tới parking-service để lấy `capacity`/`availableSlots` — kể cả khi zone_name đã có. Đây là N+1 nặng nhất.

---

## 2. Booking Model Fields (Complete List)

**Source:** `backend-microservices/booking-service/bookings/models.py`

| # | Field | Type | Default / Constraints | Notes |
|---|-------|------|----------------------|-------|
| 1 | `id` | UUIDField | PK, auto uuid4 | |
| 2 | `user_id` | UUIDField | indexed | From auth-service |
| 3 | `user_email` | EmailField | required | From auth-service |
| 4 | `vehicle_id` | UUIDField | required | From vehicle-service |
| 5 | `vehicle_license_plate` | CharField(50) | required | Denormalized |
| 6 | `vehicle_type` | CharField(20) | required | 'Car' / 'Motorbike' |
| 7 | `parking_lot_id` | UUIDField | required | From parking-service |
| 8 | `parking_lot_name` | CharField(255) | required | Denormalized |
| 9 | `floor_id` | UUIDField | null, blank | From parking-service |
| 10 | `floor_level` | IntegerField | null, blank | Denormalized |
| 11 | `zone_id` | UUIDField | required | From parking-service |
| 12 | `zone_name` | CharField(100) | required | Denormalized |
| 13 | `slot_id` | UUIDField | null, blank | Optional (auto-guarantee) |
| 14 | `slot_code` | CharField(20) | blank | Denormalized |
| 15 | `package_type` | CharField(20) | default='hourly' | hourly/daily/weekly/monthly |
| 16 | `start_time` | DateTimeField | required | |
| 17 | `end_time` | DateTimeField | null, blank | |
| 18 | `payment_method` | CharField(20) | choices | online / on_exit |
| 19 | `payment_status` | CharField(20) | default='pending' | pending/processing/completed/failed/refunded |
| 20 | `price` | DecimalField(10,2) | required | |
| 21 | `check_in_status` | CharField(20) | default='not_checked_in' | not_checked_in/checked_in/checked_out/no_show/cancelled |
| 22 | `checked_in_at` | DateTimeField | null, blank | |
| 23 | `checked_out_at` | DateTimeField | null, blank | |
| 24 | `qr_code_data` | TextField | blank | JSON string |
| 25 | `hourly_start` | DateTimeField | null, blank | Scheduled start for hourly |
| 26 | `hourly_end` | DateTimeField | null, blank | Scheduled end for hourly |
| 27 | `extended_until` | DateTimeField | null, blank | Extended end time |
| 28 | `late_fee_applied` | BooleanField | default=False | |
| 29 | `created_at` | DateTimeField | auto_now_add | |
| 30 | `updated_at` | DateTimeField | auto_now | |

**Kết luận:** Model đã denormalize đầy đủ. Không cần thêm field, không cần migration.

---

## 3. Current Serializer N+1 Methods

**Source:** `backend-microservices/booking-service/bookings/serializers.py` — `BookingSerializer` class (lines ~355–520)

### 3.1 SerializerMethodField declarations

```python
vehicle = serializers.SerializerMethodField()
parkingLot = serializers.SerializerMethodField(method_name='get_parking_lot')
floor = serializers.SerializerMethodField()
zone = serializers.SerializerMethodField()
carSlot = serializers.SerializerMethodField(method_name='get_car_slot')
```

### 3.2 Per-method analysis

| Method | HTTP Target | Condition | HTTP Calls | DB Update in READ? |
|--------|-------------|-----------|------------|---------------------|
| `get_vehicle()` | `GET vehicle-service/vehicles/{id}/` | `license_plate` empty or `'PLACEHOLDER'` | 0–1 | ✅ `Booking.objects.filter(id=obj.id).update(vehicle_license_plate=, vehicle_type=)` |
| `get_parking_lot()` | `GET parking-service/parking/lots/{id}/` | `parking_lot_name` empty | 0–1 | ✅ `Booking.objects.filter(id=obj.id).update(parking_lot_name=)` |
| `get_floor()` | `GET parking-service/parking/zones/{id}/` + `GET parking-service/parking/floors/{id}/` | `floor_id` missing AND `zone_id` present | 0–2 | ✅ `Booking.objects.filter(id=obj.id).update(floor_id=, floor_level=)` |
| `get_zone()` | `GET parking-service/parking/zones/{id}/` | **ALWAYS** (even when zone_name populated — fetches capacity/availableSlots) | **1 ALWAYS** | ✅ `Booking.objects.filter(id=obj.id).update(zone_name=, floor_id=)` (conditional) |
| `get_car_slot()` | `GET parking-service/parking/slots/{id}/` | `slot_code` empty or `'PLACEHOLDER'` | 0–1 | ✅ `Booking.objects.filter(id=obj.id).update(slot_code=)` |

### 3.3 Worst-case per booking (list page):

- **6 HTTP calls** (vehicle + lot + zone×2 + floor + slot) each with 5s timeout
- **5 DB UPDATE queries** (write-on-read side effects)
- **30 second** potential timeout for a single booking serialization
- For a list of 10 bookings: **60 HTTP calls + 50 DB writes** in a single GET request

### 3.4 The `get_zone()` problem (most critical)

```python
def get_zone(self, obj):
    # ...
    if not zone_name or zone_name == 'PLACEHOLDER':
        zone_info = _fetch_zone_info(obj.zone_id)   # HTTP call
        # ...
    else:
        # Still fetch capacity for display
        zone_info = _fetch_zone_info(obj.zone_id)   # HTTP call EVEN WHEN zone_name EXISTS
        # ...
```

This method calls `_fetch_zone_info()` in **BOTH branches** — it ALWAYS makes an HTTP call, making it the most impactful N+1 source.

---

## 4. FE Field Access Matrix

### 4.1 Two competing Booking interfaces in FE

| Interface Location | Style | Used By |
|---|---|---|
| `types/parking.ts:Booking` (line 112) | **Nested objects** (`vehicle: Vehicle`, `parkingLot: ParkingLot`, `floor: Floor`, `zone: Zone`, `carSlot?: CarSlot`) | Type declarations, used in some component prop types |
| `store/slices/bookingSlice.ts:Booking` (line 30) | **Flat fields** (`licensePlate`, `lotName`, `zoneName`, `slotCode`, etc.) | **ALL runtime code** — pages, components, Redux state |

### 4.2 `mapBookingResponse()` — the normalization bridge

Located at `bookingSlice.ts:143`. This function handles **both** nested and flat formats:

```typescript
// Extracts from nested OR flat:
slotCode: (data.slotCode || data.carSlot?.code || data.car_slot?.code || data.slot?.code || data.slot_code || "")
zoneName: (data.zoneName || data.zone?.name || data.zone_name || "")
lotName: (data.lotName || data.parkingLot?.name || data.parking_lot?.name || data.lot_name || "")
licensePlate: (data.licensePlate || data.vehicle?.licensePlate || data.vehicle?.license_plate || data.license_plate || "")
```

**Implication:** Serializer can switch to flat camelCase fields directly — `mapBookingResponse()` already handles both.

### 4.3 Actual FE field usage (pages/components)

| FE Field | Used In | Source in bookingSlice |
|----------|---------|----------------------|
| `booking.licensePlate` | UserDashboard:138, PaymentPage:233, MapPage:410, CheckInOutPage:300,405, HistoryPage:173,518,676, DirectionsPanel:67, RecentBookings:~130 | `data.licensePlate \|\| data.vehicle?.licensePlate` |
| `booking.vehicleType` | UserDashboard:129, PaymentPage:234, MapPage:411, CheckInOutPage:402, HistoryPage:504,509, DirectionsPanel:69, RecentBookings:124,129 | `data.vehicleType \|\| data.vehicle?.vehicleType` |
| `booking.lotName` | PaymentPage:235 | `data.lotName \|\| data.parkingLot?.name` |
| `booking.lotId` | MapPage:445 | `data.lotId \|\| data.parkingLot?.id` |
| `booking.zoneName` | UserDashboard:148, PaymentPage:237, MapPage:412, CheckInOutPage:312,406, HistoryPage:540,677, RecentBookings:153 | `data.zoneName \|\| data.zone?.name` |
| `booking.slotCode` | UserDashboard:149, PaymentPage:238, MapPage:413, CheckInOutPage:407, HistoryPage:540,678, RecentBookings:153 | `data.slotCode \|\| data.carSlot?.code` |
| `booking.slotId` | (indirect via mapBookingResponse) | `data.slotId \|\| data.carSlot?.id` |
| `booking.zoneId` | (indirect via mapBookingResponse) | `data.zoneId \|\| data.zone?.id` |
| `booking.vehicleId` | (indirect via mapBookingResponse) | `data.vehicleId \|\| data.vehicle?.id` |
| `booking.userId` | (indirect) | `data.userId` |
| `booking.price` | PaymentPage, HistoryPage | `data.price \|\| data.totalAmount` |
| `booking.packageType` | PaymentPage, HistoryPage | `data.packageType` |
| `booking.checkInStatus` | Everywhere | `data.checkInStatus` |
| `booking.paymentStatus` | PaymentPage, HistoryPage | `data.paymentStatus` |
| `booking.startTime` | HistoryPage, PaymentPage | `data.startTime` |
| `booking.endTime` | HistoryPage | `data.endTime` |
| `booking.checkInTime` | HistoryPage, CheckInOutPage | `data.checkedInAt` |
| `booking.checkOutTime` | HistoryPage | `data.checkedOutAt` |
| `booking.createdAt` | HistoryPage | `data.createdAt` |

### 4.4 Fields FE does NOT use from serializer

| Serializer Field | FE Uses? | Action |
|---|---|---|
| `zone.capacity` | ❌ NOT used from booking response | **REMOVE** from serializer — eliminates always-fetch N+1 |
| `zone.availableSlots` | ❌ NOT used from booking response | **REMOVE** from serializer |
| `zone.floorId` | ❌ NOT used from booking response | Can omit |
| `floor.zones` | ❌ Always `[]` | Can omit |
| `carSlot.isAvailable` | ❌ Always `False` | Can omit |
| `vehicle.name` | ❌ Just duplicate of licensePlate | Can omit |
| `vehicle.userId` | ❌ Redundant with booking.userId | Can omit |

---

## 5. Missing Denormalized Fields

**NONE.** The model has all fields FE needs:

| FE needs | Model has | Field name |
|----------|-----------|------------|
| licensePlate | ✅ | `vehicle_license_plate` |
| vehicleType | ✅ | `vehicle_type` |
| vehicleId | ✅ | `vehicle_id` |
| lotName | ✅ | `parking_lot_name` |
| lotId | ✅ | `parking_lot_id` |
| zoneName | ✅ | `zone_name` |
| zoneId | ✅ | `zone_id` |
| slotCode | ✅ | `slot_code` |
| slotId | ✅ | `slot_id` |
| floorLevel | ✅ | `floor_level` |
| floorId | ✅ | `floor_id` |

**No migration needed.**

---

## 6. Existing Service Functions (`services.py`)

**Source:** `backend-microservices/booking-service/bookings/services.py`

| Function | Purpose | Relevant? |
|----------|---------|-----------|
| `get_hourly_price(vehicle_type)` | Get hourly pricing | No (pricing, not serialization) |
| `calculate_checkout_price(booking)` | Checkout pricing + late fees | No |
| `calculate_current_cost(booking)` | Running cost for active parking | No |
| `validate_checkin(booking)` | Pre-checkin validation | No |
| `validate_checkout(booking)` | Pre-checkout validation | No |
| `validate_cancel(booking)` | Pre-cancel validation | No |
| `calculate_extension_price(booking, hours)` | Extension cost calc | No |
| `perform_extend(booking, hours)` | Execute extension | No |
| `perform_checkin(booking)` | Execute check-in | No |
| `perform_checkout(booking)` | Execute checkout | No |
| `perform_cancel(booking)` | Execute cancel | No |
| `create_payment_for_booking(booking)` | Call payment service | No |
| `get_booking_payments(booking_id, user_id)` | Fetch payments from payment-service | No |
| `initiate_payment(...)` | Initiate payment | No |
| `get_user_stats(user_id)` | Aggregate user stats (DB only) | No |

**Kết luận:** `services.py` chỉ chứa logic tính price + lifecycle actions. Không có function nào liên quan đến serialization/inter-service data fetching. Các `_fetch_*_info()` helpers nằm trong `serializers.py` (module-level functions).

---

## 7. Side-Effect Calls in `get_*` Methods (FULL LIST)

| Method | Side-Effect | Condition |
|--------|------------|-----------|
| `get_vehicle()` line ~410 | `Booking.objects.filter(id=obj.id).update(vehicle_license_plate=..., vehicle_type=...)` | When license_plate empty/PLACEHOLDER |
| `get_parking_lot()` line ~425 | `Booking.objects.filter(id=obj.id).update(parking_lot_name=name)` | When name empty |
| `get_floor()` line ~443 | `Booking.objects.filter(id=obj.id).update(floor_id=..., floor_level=...)` | When floor_id missing + zone has floor |
| `get_zone()` line ~471 | `Booking.objects.filter(id=obj.id).update(zone_name=..., floor_id=...)` | When zone_name empty/PLACEHOLDER |
| `get_zone()` line ~485 | `Booking.objects.filter(id=obj.id).update(floor_id=...)` | When floor_id discovered from zone (even when zone_name populated) |
| `get_car_slot()` line ~498 | `Booking.objects.filter(id=obj.id).update(slot_code=...)` | When slot_code empty/PLACEHOLDER |

**Analysis:** Đây là "lazy denormalization" — nghĩa là `CreateBookingSerializer.create()` đã fetch tất cả denormalized data lúc tạo, nhưng serializer vẫn re-fetch nếu field trống. Vấn đề:
- Nếu CreateBookingSerializer populate đúng → các `get_*` sẽ KHÔNG cần fetch (trừ `get_zone()` luôn fetch capacity).
- Nhưng nếu service-to-service call fail lúc create → field = empty → serializer cố gắng "heal" data mỗi lần read.

**Recommended approach:** Bỏ tất cả lazy heal logic. Nếu data empty lúc create thì trả empty string cho FE hiển thị fallback, không cố fetch lại trong read path.

---

## 8. Proposed New BookingSerializer Structure

Serializer mới chỉ cần đọc denormalized fields từ model — **zero HTTP calls**:

```python
# Proposed structure - NO SerializerMethodField, NO HTTP calls
class BookingSerializer(serializers.ModelSerializer):
    # camelCase aliases cho FE
    userId = serializers.UUIDField(source='user_id')
    vehicleId = serializers.UUIDField(source='vehicle_id')
    licensePlate = serializers.CharField(source='vehicle_license_plate')
    vehicleType = serializers.CharField(source='vehicle_type')
    parkingLotId = serializers.UUIDField(source='parking_lot_id')
    parkingLotName = serializers.CharField(source='parking_lot_name')
    floorId = serializers.UUIDField(source='floor_id', allow_null=True)
    floorLevel = serializers.IntegerField(source='floor_level', allow_null=True)
    zoneId = serializers.UUIDField(source='zone_id')
    zoneName = serializers.CharField(source='zone_name')
    slotId = serializers.UUIDField(source='slot_id', allow_null=True)
    slotCode = serializers.CharField(source='slot_code')
    # ... (keep existing camelCase fields for lifecycle)
    
    # ALSO keep nested objects for backward compat with types/parking.ts
    vehicle = serializers.SerializerMethodField()  # Pure model, NO HTTP
    parkingLot = serializers.SerializerMethodField(method_name='get_parking_lot')  # Pure model
    zone = serializers.SerializerMethodField()  # Pure model, NO HTTP
    floor = serializers.SerializerMethodField()  # Pure model, NO HTTP  
    carSlot = serializers.SerializerMethodField(method_name='get_car_slot')  # Pure model

    class Meta:
        model = Booking
        fields = [...]
    
    # get_* methods return dict from model fields ONLY — no HTTP, no DB writes
```

**FE `mapBookingResponse()` sẽ hoạt động với cả hai format vì nó đã check flat fields trước nested objects.**

---

## 9. Checklist cho Implementer

- [ ] Rewrite `BookingSerializer.get_vehicle()` → return dict from `obj.vehicle_*` fields only
- [ ] Rewrite `BookingSerializer.get_parking_lot()` → return dict from `obj.parking_lot_*` fields only
- [ ] Rewrite `BookingSerializer.get_floor()` → return dict from `obj.floor_*` fields only
- [ ] Rewrite `BookingSerializer.get_zone()` → return dict from `obj.zone_*` fields only (DROP capacity/availableSlots)
- [ ] Rewrite `BookingSerializer.get_car_slot()` → return dict from `obj.slot_*` fields only
- [ ] Remove ALL `Booking.objects.filter(id=obj.id).update(...)` calls from get_* methods
- [ ] Add flat camelCase fields (`licensePlate`, `vehicleType`, `zoneName`, `slotCode`, `lotName`, etc.) for direct access
- [ ] Keep `_fetch_*_info()` module-level functions — still needed by `CreateBookingSerializer.create()`
- [ ] No migration needed
- [ ] No FE changes needed (`mapBookingResponse()` handles both formats)
- [ ] Run `pytest booking-service/` after changes

---

## 10. Nguồn

| # | File | Mô tả | Lines |
|---|------|-------|-------|
| 1 | `booking-service/bookings/models.py` | Booking model definition | 1–135 |
| 2 | `booking-service/bookings/serializers.py` | BookingSerializer + CreateBookingSerializer | 1–520 |
| 3 | `booking-service/bookings/services.py` | Business logic layer | 1–440 |
| 4 | `spotlove-ai/src/store/slices/bookingSlice.ts` | Redux Booking state + mapBookingResponse | 1–400 |
| 5 | `spotlove-ai/src/services/api/booking.api.ts` | API type definitions | 1–200 |
| 6 | `spotlove-ai/src/types/parking.ts` | Booking interface (nested) | 100–140 |
| 7 | `spotlove-ai/src/pages/PaymentPage.tsx` | Uses lotName, zoneName, slotCode | 233–238 |
| 8 | `spotlove-ai/src/pages/MapPage.tsx` | Uses licensePlate, zoneName, slotCode, lotId | 410–445 |
| 9 | `spotlove-ai/src/pages/HistoryPage.tsx` | Uses licensePlate, zoneName, slotCode | 173,518,540,676–678 |
| 10 | `spotlove-ai/src/pages/UserDashboard.tsx` | Uses licensePlate, zoneName, slotCode | 129–149 |
| 11 | `spotlove-ai/src/pages/CheckInOutPage.tsx` | Uses licensePlate, zoneName, slotCode | 300–407 |
| 12 | `spotlove-ai/src/components/dashboard/RecentBookings.tsx` | Uses zoneName, slotCode | 153 |
| 13 | `spotlove-ai/src/components/map/DirectionsPanel.tsx` | Uses licensePlate, zone, slot, floor | 67–82 |
