# Research Report: Docker Service Log Issues

**Task:** DOCKER-LOGS | **Date:** 2026-04-12 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. 5 models thiếu `Meta.ordering` → thêm `ordering` vào `class Meta` là fix đơn giản nhất
> 2. `/parking/cameras/` 403 do `GatewayAuthMiddleware` reject requests thiếu `X-Gateway-Secret` header — KHÔNG phải lỗi permission class
> 3. `/auth/login/` 400 do `LoginSerializer.validate()` — sai email/password hoặc request body thiếu field — đây là behavior bình thường, không phải bug

---

## 2. Issue 1: UnorderedObjectListWarning — 5 Django Models

### Root Cause

Django's `PageNumberPagination` (hoặc tương tự) yêu cầu QuerySet phải có ordering xác định. Khi `class Meta` không có `ordering` và ViewSet không gọi `.order_by()`, Django raise `UnorderedObjectListWarning` vì pagination results có thể không nhất quán giữa các pages.

### 2.1 Model Analysis

| #   | Model            | File                                                                | Has `Meta.ordering`? | Existing `Meta`                               | ViewSet File                                     | ViewSet has `ordering`/`order_by()`?                                                |
| --- | ---------------- | ------------------------------------------------------------------- | -------------------- | --------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------- |
| 1   | `Booking`        | `backend-microservices/booking-service/bookings/models.py:43`       | ❌ **NO**            | `db_table`, `indexes` only                    | `bookings/views.py:53` `BookingViewSet`          | ❌ No default ordering. `.order_by('start_time')` chỉ dùng trong 1 aggregate action |
| 2   | `PackagePricing` | `backend-microservices/booking-service/bookings/models.py:12`       | ❌ **NO**            | `db_table`, `unique_together` only            | `bookings/views.py:46` `PackagePricingViewSet`   | ❌ No ordering, bare `queryset = PackagePricing.objects.all()`                      |
| 3   | `ParkingLot`     | `backend-microservices/parking-service/infrastructure/models.py:12` | ❌ **NO**            | `db_table`, `indexes` only                    | `infrastructure/views.py:16` `ParkingLotViewSet` | ❌ No ordering                                                                      |
| 4   | `CarSlot`        | `backend-microservices/parking-service/infrastructure/models.py:87` | ❌ **NO**            | `db_table`, `unique_together`, `indexes` only | `infrastructure/views.py:260` `CarSlotViewSet`   | ❌ No ordering                                                                      |
| 5   | `Vehicle`        | `backend-microservices/vehicle-service/vehicles/models.py:12`       | ❌ **NO**            | `db_table`, `indexes` only                    | `vehicles/views.py:13` `VehicleViewSet`          | ❌ No ordering                                                                      |

**Note:** `Floor` model (same file as ParkingLot) DOES have `ordering = ['level']` — good reference pattern.

### 2.2 Suggested Ordering Fields

| Model            | Suggested `ordering`               | Rationale                                    |
| ---------------- | ---------------------------------- | -------------------------------------------- |
| `Booking`        | `['-created_at']`                  | Newest bookings first — most common use case |
| `PackagePricing` | `['package_type', 'vehicle_type']` | Logical grouping, only ~8 rows total         |
| `ParkingLot`     | `['name']`                         | Alphabetical by name — stable, deterministic |
| `CarSlot`        | `['code']`                         | Slot codes like "A-01" sort naturally        |
| `Vehicle`        | `['-created_at']`                  | Newest vehicles first                        |

### 2.3 Fix Location Options

**Option A (preferred): Add `ordering` to `class Meta` in each model**

- Pros: Fix applies globally to ALL QuerySets of that model
- Cons: Minor performance impact if ordering column isn't indexed (but `created_at` is auto-indexed for Booking/Vehicle)

**Option B: Add `ordering` to ViewSet `queryset`**

- Example: `queryset = Booking.objects.all().order_by('-created_at')`
- Pros: Only affects API views
- Cons: Must remember to add to every ViewSet

**Recommendation for Implementer:** Option A — add to `class Meta`. This matches the existing pattern used by `Floor` model.

### 2.4 All fields available for ordering (per model)

- **Booking**: `id`, `user_id`, `start_time`, `end_time`, `created_at`, `updated_at`, `check_in_status`, `payment_status`
- **PackagePricing**: `id`, `package_type`, `vehicle_type`, `price`, `created_at`
- **ParkingLot**: `id`, `name`, `total_slots`, `available_slots`, `is_open`, `created_at`
- **CarSlot**: `id`, `code`, `status`, `created_at`
- **Vehicle**: `id`, `user_id`, `license_plate`, `vehicle_type`, `is_default`, `created_at`

---

## 3. Issue 2: Forbidden on `/parking/cameras/`

### 3.1 Request Flow

```
Client → Gateway (Go) → parking-service Django
                         ├── GatewayAuthMiddleware (checks X-Gateway-Secret)
                         └── CameraViewSet (permission_classes = [IsGatewayAuthenticated])
```

### 3.2 Files Involved

| File                                                                | Role                                                              |
| ------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `backend-microservices/parking-service/infrastructure/views.py:432` | `CameraViewSet` — `permission_classes = [IsGatewayAuthenticated]` |
| `backend-microservices/parking-service/infrastructure/urls.py:14`   | `router.register(r'cameras', ...)`                                |
| `backend-microservices/shared/gateway_middleware.py:16`             | `GatewayAuthMiddleware`                                           |
| `backend-microservices/shared/gateway_permissions.py:9`             | `IsGatewayAuthenticated`                                          |

### 3.3 Two Layers That Can Return 403

**Layer 1: `GatewayAuthMiddleware` (line 49-53)**

```python
if not is_public and (not gateway_secret or gateway_secret != expected_secret):
    return JsonResponse({
        'error': 'Forbidden - Direct access not allowed',
        'message': 'All requests must go through API Gateway'
    }, status=403)
```

- `/parking/cameras/` is NOT in `public_paths` list
- If `X-Gateway-Secret` header is missing or wrong → **403 at middleware level**
- Django logs this as `Forbidden: /parking/cameras/`

**Layer 2: `IsGatewayAuthenticated` (line 19)**

```python
return bool(getattr(request, 'user_id', None))
```

- If gateway secret is valid BUT `X-User-ID` header is missing → `request.user_id = None` → **403 at permission level**

### 3.4 Most Likely Cause

The 403 is from **Layer 1 (middleware)** — a request hitting `/parking/cameras/` directly without going through the Go gateway, or the gateway not forwarding the `X-Gateway-Secret` header. This is the most common scenario because:

- The log message `Forbidden: /parking/cameras/` is Django's default `JsonResponse` format
- If it were Layer 2, DRF would return `{"detail": "Authentication required"}` instead

### 3.5 Possible Callers

- **AI service (FastAPI)** calling parking-service directly without gateway secret
- **Frontend** calling parking-service directly (bypassing gateway)
- **Health check / monitoring** hitting the endpoint without headers
- **Unity camera streamer** or other internal service

---

## 4. Issue 3: Bad Request `/auth/login/`

### 4.1 Files Involved

| File                                                         | Role                                            |
| ------------------------------------------------------------ | ----------------------------------------------- |
| `backend-microservices/auth-service/users/views.py:143`      | `LoginView` — `permission_classes = [AllowAny]` |
| `backend-microservices/auth-service/users/serializers.py:98` | `LoginSerializer` validation logic              |

### 4.2 LoginView Flow

```python
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # ← raises 400 here
        ...
```

### 4.3 Three Validation Points That Return 400

**LoginSerializer** (`serializers.py:98-120`):

```python
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise ValidationError('Invalid email or password')  # ← 400
            if not user.is_active:
                raise ValidationError('User account is disabled')   # ← 400
            attrs['user'] = user
            return attrs
        else:
            raise ValidationError('Must include "email" and "password"')  # ← 400
```

| Cause                         | Trigger                                                     | Error Message                                                                         |
| ----------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Missing/invalid `email` field | Request body lacks `email` or it's not a valid email format | `"email": ["This field is required."]` or `"email": ["Enter a valid email address."]` |
| Missing `password` field      | Request body lacks `password`                               | `"password": ["This field is required."]`                                             |
| Wrong credentials             | `authenticate()` returns `None`                             | `"Invalid email or password"`                                                         |
| Disabled account              | `user.is_active == False`                                   | `"User account is disabled"`                                                          |

### 4.4 Assessment

This is **normal behavior, not a bug**. The `Bad Request: /auth/login/` log appears when:

1. A user enters wrong email/password (most common)
2. A bot/scanner hits the login endpoint with garbage data
3. Frontend sends malformed request (e.g., `username` instead of `email`)

**Note:** `/auth/login/` is in the `public_paths` list of `GatewayAuthMiddleware`, so it bypasses gateway secret check — anyone can hit it directly.

---

## 5. ⚠️ Gotchas & Known Issues

- [ ] **[WARNING]** `CarSlotViewSet` has NO `permission_classes` defined — it's using DRF default (likely `AllowAny` or `IsAuthenticated` depending on `REST_FRAMEWORK` settings). All other ViewSets in parking-service use `IsGatewayAuthenticated`.
- [ ] **[NOTE]** `PackagePricingViewSet` also has NO `permission_classes` — same concern for booking-service.
- [ ] **[NOTE]** The ordering fix should include DB index check — `Booking.created_at` already has `auto_now_add=True` but no explicit index. However, InnoDB auto-creates index for `auto_now_add` fields in most Django/MySQL setups.

---

## 6. Checklist cho Implementer

### Issue 1 Fix (UnorderedObjectListWarning):

- [ ] Add `ordering = ['-created_at']` to `Booking.Meta` in `booking-service/bookings/models.py`
- [ ] Add `ordering = ['package_type', 'vehicle_type']` to `PackagePricing.Meta` in same file
- [ ] Add `ordering = ['name']` to `ParkingLot.Meta` in `parking-service/infrastructure/models.py`
- [ ] Add `ordering = ['code']` to `CarSlot.Meta` in same file
- [ ] Add `ordering = ['-created_at']` to `Vehicle.Meta` in `vehicle-service/vehicles/models.py`
- [ ] No migration needed — `Meta.ordering` is a Django ORM query modifier, not a DB schema change

### Issue 2 Fix (cameras 403):

- [ ] Verify caller is sending `X-Gateway-Secret` header
- [ ] If AI service calls parking-service directly → must include `X-Gateway-Secret: gateway-internal-secret-key`
- [ ] Check gateway-service-go routing for `/parking/cameras/`

### Issue 3 (login 400):

- [ ] **No code fix needed** — this is expected behavior for failed login attempts
- [ ] Consider: rate limiting on `/auth/login/` if seeing high volume of 400s (bot protection)

---

## 7. Nguồn

| #   | Source                                                                                                                                           | Mô tả                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| 1   | `backend-microservices/booking-service/bookings/models.py`                                                                                       | Booking + PackagePricing model definitions      |
| 2   | `backend-microservices/parking-service/infrastructure/models.py`                                                                                 | ParkingLot + CarSlot + Camera model definitions |
| 3   | `backend-microservices/vehicle-service/vehicles/models.py`                                                                                       | Vehicle model definition                        |
| 4   | `backend-microservices/shared/gateway_middleware.py`                                                                                             | Gateway secret validation middleware            |
| 5   | `backend-microservices/shared/gateway_permissions.py`                                                                                            | IsGatewayAuthenticated permission class         |
| 6   | `backend-microservices/auth-service/users/serializers.py`                                                                                        | LoginSerializer validation logic                |
| 7   | `backend-microservices/auth-service/users/views.py`                                                                                              | LoginView implementation                        |
| 8   | [Django docs: UnorderedObjectListWarning](https://docs.djangoproject.com/en/5.0/ref/paginator/#django.core.paginator.UnorderedObjectListWarning) | Official documentation on ordering requirement  |
