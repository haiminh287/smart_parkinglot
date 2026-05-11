# Research Report: Parking-Service Slot Listing, Pagination & lot_id Filtering

**Date:** 2026-04-14 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **CarSlotViewSet KHÔNG có `lot_id` filter** — chỉ filter bằng `zone_id`, `status`, `vehicle_type`. Client muốn lọc slot theo lot phải biết zone_id trước.
> 2. **Pagination: PageNumberPagination, PAGE_SIZE = 20** — áp dụng global cho tất cả ViewSets.
> 3. **Hierarchy: ParkingLot → Floor → Zone → CarSlot** — Không có shortcut filter từ slot → lot. Phải đi qua zone → floor → lot.

---

## 2. Entity Hierarchy

```
ParkingLot (parking_lot table)
  └── Floor (floor table)         FK: parking_lot_id
       └── Zone (zone table)      FK: floor_id
            └── CarSlot (car_slot table)  FK: zone_id
```

---

## 3. CarSlot Model

**File:** `backend-microservices/parking-service/infrastructure/models.py` (Lines 91–124)

| Field         | Type                | Notes                                            |
| ------------- | ------------------- | ------------------------------------------------ |
| `id`          | UUIDField (PK)      | auto uuid4                                       |
| `zone`        | ForeignKey → Zone   | CASCADE, related_name='slots'                    |
| `code`        | CharField(20)       | unique_together with zone                        |
| `status`      | CharField(20)       | choices: available/occupied/reserved/maintenance |
| `camera`      | ForeignKey → Camera | SET_NULL, nullable                               |
| `x1,y1,x2,y2` | IntegerField        | nullable, bbox for AI detection                  |
| `created_at`  | DateTimeField       | auto_now_add                                     |
| `updated_at`  | DateTimeField       | auto_now                                         |

**Meta:** `db_table = 'car_slot'`, `unique_together = [['zone', 'code']]`, `ordering = ['code']`, index on `status`.

---

## 4. Zone Model

**File:** `backend-microservices/parking-service/infrastructure/models.py` (Lines 60–89)

| Field             | Type               | Notes                         |
| ----------------- | ------------------ | ----------------------------- |
| `id`              | UUIDField (PK)     | auto uuid4                    |
| `floor`           | ForeignKey → Floor | CASCADE, related_name='zones' |
| `name`            | CharField(100)     |                               |
| `vehicle_type`    | CharField(20)      | choices: Car/Motorbike        |
| `capacity`        | IntegerField       |                               |
| `available_slots` | IntegerField       | default=0                     |
| `created_at`      | DateTimeField      | auto_now_add                  |
| `updated_at`      | DateTimeField      | auto_now                      |

**Meta:** `db_table = 'zone'`, index on `vehicle_type`.  
**Properties:** `occupied_slots`, `reserved_slots` (computed from slots queryset).

---

## 5. CarSlotViewSet — Slot Listing View

**File:** `backend-microservices/parking-service/infrastructure/views.py` (Lines 222–270)

```python
class CarSlotViewSet(viewsets.ModelViewSet):
    """ViewSet for CarSlot."""

    queryset = CarSlot.objects.all()
    serializer_class = CarSlotSerializer
    permission_classes = [IsGatewayAuthenticated]

    def get_queryset(self):
        """Filter slots by zone_id, status, vehicle_type."""
        queryset = super().get_queryset()

        zone_id = self.request.query_params.get('zone_id')
        if zone_id:
            try:
                import uuid
                uuid.UUID(zone_id)
                queryset = queryset.filter(zone_id=zone_id)
            except (ValueError, TypeError, AttributeError):
                queryset = queryset.none()

        slot_status = self.request.query_params.get('status')
        if slot_status:
            queryset = queryset.filter(status=slot_status)

        vehicle_type = self.request.query_params.get('vehicle_type')
        if vehicle_type:
            queryset = queryset.filter(zone__vehicle_type=vehicle_type)

        return queryset
```

### Available Query Params on `/parking/slots/`:

| Param          | Filter Logic                       | Supports lot_id? |
| -------------- | ---------------------------------- | ---------------- |
| `zone_id`      | `filter(zone_id=zone_id)`          | No — zone level  |
| `status`       | `filter(status=status)`            | No               |
| `vehicle_type` | `filter(zone__vehicle_type=vtype)` | No               |

### ⚠️ KEY FINDING: NO `lot_id` FILTER ON CarSlotViewSet

Calling `GET /parking/slots/` **without `zone_id`** returns **ALL slots across ALL lots**, paginated at 20 per page.

Calling `GET /parking/slots/?lot_id=xxx` — the `lot_id` param is **IGNORED** (not in `get_queryset`).

To get slots for a specific lot, client must:

1. `GET /parking/zones/?lot_id=xxx` → get zone IDs
2. `GET /parking/slots/?zone_id=yyy` (one zone at a time)

Or use the ZoneViewSet which DOES support `lot_id` filtering (line 196):

```python
# ZoneViewSet.get_queryset() — line 196
lot_id = self.request.query_params.get('lot_id')
if lot_id:
    queryset = queryset.filter(floor__parking_lot_id=lot_id)
```

---

## 6. Pagination Configuration

**File:** `backend-microservices/parking-service/parking_service/settings.py` (Lines 99–110)

```python
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

| Setting                    | Value                                            |
| -------------------------- | ------------------------------------------------ |
| `DEFAULT_PAGINATION_CLASS` | `rest_framework.pagination.PageNumberPagination` |
| `PAGE_SIZE`                | **20**                                           |
| Custom pagination class?   | **No** — uses DRF built-in                       |
| `filter_backends`          | **None configured** — no DjangoFilterBackend     |

**Response format** (standard DRF PageNumberPagination):

```json
{
  "count": 100,
  "next": "http://.../parking/slots/?page=2",
  "previous": null,
  "results": [...]
}
```

Note: CamelCaseJSONRenderer is active, so response keys are camelCased.

---

## 7. URL Routing

**File:** `backend-microservices/parking-service/parking_service/urls.py` (Lines 1–13)

Root prefix: `/parking/`

**File:** `backend-microservices/parking-service/infrastructure/urls.py` (Lines 1–16)

| Endpoint            | ViewSet           | Key filters                             |
| ------------------- | ----------------- | --------------------------------------- |
| `/parking/lots/`    | ParkingLotViewSet | lat, lng, radius, vehicle_type, is_open |
| `/parking/floors/`  | FloorViewSet      | lot_id                                  |
| `/parking/zones/`   | ZoneViewSet       | lot_id, floor_id, vehicle_type          |
| `/parking/slots/`   | CarSlotViewSet    | zone_id, status, vehicle_type           |
| `/parking/cameras/` | CameraViewSet     | zone_id, floor, status                  |

---

## 8. Other ViewSets That DO Filter by lot_id

### FloorViewSet (line 173)

```python
lot_id = self.request.query_params.get('lot_id')
if lot_id:
    queryset = queryset.filter(parking_lot_id=lot_id)
```

### ZoneViewSet (line 196)

```python
lot_id = self.request.query_params.get('lot_id')
if lot_id:
    queryset = queryset.filter(floor__parking_lot_id=lot_id)
```

### CarSlotViewSet — **MISSING lot_id filter**

---

## 9. Serializer Details

**File:** `backend-microservices/parking-service/infrastructure/serializers.py` (Lines 62–78)

```python
class CarSlotSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = CarSlot
        fields = [
            'id', 'zone', 'code', 'status', 'is_available', 'camera',
            'x1', 'y1', 'x2', 'y2', 'created_at', 'updated_at',
        ]

    def get_is_available(self, obj):
        return obj.status == 'available'
```

Note: `zone` field returns the zone UUID. No nested zone/floor/lot info in the default serializer.

---

## 10. ⚠️ Gotchas & Key Issues

- [ ] **[WARNING]** `CarSlotViewSet` has NO `lot_id` filter — calling `/parking/slots/` returns ALL slots globally (paginated 20/page)
- [ ] **[NOTE]** No `filter_backends` configured (no DjangoFilterBackend/SearchFilter/OrderingFilter)
- [ ] **[NOTE]** No `select_related` / `prefetch_related` on CarSlotViewSet queryset — potential N+1 when serializing `zone` field
- [ ] **[NOTE]** CamelCaseJSONRenderer active — all response keys are auto-converted to camelCase

---

## 11. Nguồn

| #   | File                                                                  | Mô tả                 | Lines   |
| --- | --------------------------------------------------------------------- | --------------------- | ------- |
| 1   | `backend-microservices/parking-service/infrastructure/views.py`       | CarSlotViewSet        | 222–270 |
| 2   | `backend-microservices/parking-service/parking_service/settings.py`   | REST_FRAMEWORK config | 99–110  |
| 3   | `backend-microservices/parking-service/infrastructure/models.py`      | CarSlot model         | 91–124  |
| 4   | `backend-microservices/parking-service/infrastructure/models.py`      | Zone model            | 60–89   |
| 5   | `backend-microservices/parking-service/infrastructure/serializers.py` | CarSlotSerializer     | 62–78   |
| 6   | `backend-microservices/parking-service/infrastructure/urls.py`        | Router config         | 1–16    |
| 7   | `backend-microservices/parking-service/parking_service/urls.py`       | Root URL prefix       | 1–13    |
