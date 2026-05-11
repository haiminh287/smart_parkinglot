# Research Report: Early-Arrival Check-In + Dynamic Slot Reallocation

**Task:** early-arrival check-in business change | **Date:** 2026-04-23 | **Type:** Codebase Analysis

## Current behavior

- `backend-microservices/booking-service/bookings/services.py`
  - `validate_checkin()` is the authoritative reject point for early arrival.
  - Current rule: reject when `timezone.now() < booking.start_time - 30 minutes`.
  - `perform_checkin()` only sets `check_in_status="checked_in"` and `checked_in_at=now`; it does not re-evaluate slot allocation and does not mutate booking window.
- `backend-microservices/booking-service/bookings/views_lifecycle.py`
  - `checkin()` calls `validate_checkin()` then `perform_checkin()`, then emits one `slot.status_changed` event with current `booking.slot_id -> occupied` and one `booking.checked_in` event.
  - There is no branch for `arrival_time`, no overlap re-check, and no fallback slot search.
- `backend-microservices/ai-service-fastapi/app/services/esp32_checkin_service.py`
  - ESP32 flow performs its own pre-check using booking data before calling booking-service.
  - Current local rule is `15` minutes early, via `CHECK_IN_EARLY_MINUTES` from `esp32_helpers.py`.
  - After booking-service check-in returns, the code still marks slot occupied using the **old** slot from the pre-fetch booking payload, not the slot from the check-in response.
- `backend-microservices/parking-service/infrastructure/views.py`
  - parking-service exposes list/filter primitives for zones and slots, plus a zone-scoped time-window availability helper.
  - It does not currently expose a single endpoint that says "find me the best replacement slot for this booking".

## Files/symbols to change

### Primary implementation surface

- `backend-microservices/booking-service/bookings/services.py`
  - `validate_checkin`
    - Current hard reject for early arrival lives here.
    - This is the symbol that currently decides whether "đến sớm" fails.
  - `perform_checkin`
    - Too small today; it only changes status/timestamp.
    - Best minimal place to extend or wrap with a new helper such as `prepare_checkin_slot()` / `resolve_checkin_slot()` before final save.
  - `check_overlapping_bookings`
    - Reusable helper for overlap detection against arbitrary candidate slot IDs.
- `backend-microservices/booking-service/bookings/views_lifecycle.py`
  - `BookingLifecycleViewSet.checkin`
    - Smallest controller surface to insert: validate -> resolve slot/window -> perform check-in -> emit correct events.
    - If implementation stays here, service layer should still own the slot/window decision to avoid leaking business logic into views.

### Directly affected consumers / adapters

- `backend-microservices/ai-service-fastapi/app/services/esp32_checkin_service.py`
  - `process_checkin`
    - Must stop using stale pre-checkin `booking.slot_id` after slot reassignment.
    - Must read slot ID/code from `checkin_resp["data"]["booking"]` when updating parking status and when broadcasting Unity spawn.
- `backend-microservices/ai-service-fastapi/app/services/esp32_helpers.py`
  - `CHECK_IN_EARLY_MINUTES`
    - Mismatch with booking-service authoritative 30-minute rule.
    - Either align to the same rule or remove local early-window decision and defer to booking-service.

### Potentially affected denormalized data surfaces

- `backend-microservices/booking-service/bookings/models.py`
  - Booking stores denormalized `floor_id`, `floor_level`, `zone_id`, `zone_name`, `slot_id`, `slot_code`.
  - If fallback slot may cross zone/floor, implementation must update these fields atomically, not only `slot_id`.
- `backend-microservices/booking-service/bookings/serializers.py`
  - `BookingSerializer.get_car_slot()` already serializes slot from booking fields.
  - No response schema change is strictly required if booking fields are updated before serialization.
  - If cross-zone fallback is allowed, serializer output will already reflect new zone/floor/slot if denormalized fields are updated correctly.

### Adjacent dependent flows to verify

- `backend-microservices/ai-service-fastapi/app/services/esp32_verify_service.py`
  - `process_verify_slot` compares physical slot with booking `carSlot/slotCode` after check-in.
  - Any stale slot data after reassignment will create false mismatch failures.
- `backend-microservices/booking-service/bookings/events.py`
  - `create_slot_event` and `create_booking_event` are the current event surfaces.
- `backend-microservices/parking-service/infrastructure/views.py`
  - `CarSlotViewSet.get_queryset`
  - `CarSlotViewSet.check_slots_availability`
  - `CarSlotViewSet.update_status`

## Existing helpers to reuse

- Booking overlap helper:
  - `backend-microservices/booking-service/bookings/services.py::check_overlapping_bookings(slot_ids, start_time, end_time)`
  - Best reusable helper for excluding booked candidate slots in a new interval.
- Existing overlap query pattern in create flow:
  - `backend-microservices/booking-service/bookings/serializers.py::CreateBookingSerializer.create`
  - Already checks `slot_id`, `check_in_status in ["not_checked_in", "checked_in"]`, `start_time__lt=end_time`, `end_time__gt=start_time`.
  - Useful as the local query template if implementer keeps all logic inside booking-service without new HTTP hops.
- parking-service slot discovery primitives:
  - `GET /parking/zones/?lot_id=<lot>&vehicle_type=<type>`
  - `GET /parking/slots/?lot_id=<lot>&zone_id=<zone>&status=available&vehicle_type=<type>`
  - `POST /parking/slots/check-slots-availability/` with `zone_id`, `start_time`, `end_time`
  - These are sufficient to find candidates by zone/lot/vehicle_type, but the time-window helper is currently zone-scoped only.
- booking-service outward endpoint already reusable from parking-service and other services:
  - `POST /bookings/check-slot-bookings/`
  - Can exclude overlaps for an arbitrary slot ID list.

## Risks / edge cases

- Rule mismatch now exists:
  - AI/ESP32 pre-check allows only `15` minutes early.
  - booking-service authoritative check allows `30` minutes early.
  - Result today: a booking can be valid in booking-service but still be blocked by ESP32 before request reaches it.
- If business means "start parking session from arrival_time", changing only `checked_in_at` is not enough.
  - Overlap logic for the updated reservation window will still be wrong unless booking `start_time` is shifted.
  - For hourly bookings, `hourly_start` likely also needs to move to `arrival_time`, otherwise checkout base-price logic still uses the old scheduled window.
- If fallback slot changes zone/floor:
  - booking denormalized `zone_*` / `floor_*` fields must be updated.
  - verify-slot and Unity pathing depend on updated slot code and zone consistency.
- Current event flow assumes one slot per check-in.
  - If slot changes at check-in, old reserved slot must be released and new slot must be occupied.
  - Emitting only one `occupied` event for the new slot leaves the old slot stuck as reserved.
- `esp32_checkin_service.process_checkin` currently uses stale slot ID after check-in.
  - This becomes a direct bug as soon as reassignment is introduced.

## Blast radius

### Direct files

- `backend-microservices/booking-service/bookings/services.py`
- `backend-microservices/booking-service/bookings/views_lifecycle.py`
- `backend-microservices/ai-service-fastapi/app/services/esp32_checkin_service.py`
- `backend-microservices/ai-service-fastapi/app/services/esp32_helpers.py`
- `backend-microservices/booking-service/bookings/events.py`

### Conditionally direct if fallback may cross zone/floor

- `backend-microservices/booking-service/bookings/models.py`
- `backend-microservices/booking-service/bookings/serializers.py`
- `backend-microservices/parking-service/infrastructure/views.py`

### Dependent flows

- Manual REST check-in: `POST /bookings/{id}/checkin/`
- ESP32 gate-in flow: `ai-service-fastapi -> booking-service checkin`
- Realtime slot sync: `slot.status_changed -> parking-service consumer`
- Realtime booking broadcast: `booking.checked_in -> realtime-service`
- Unity spawn/navigation after check-in: `unity.spawn_vehicle` uses slot code from check-in response
- Verify-slot flow after parking: compares booking slot vs physical slot

### Risk level

- **MEDIUM-HIGH**
  - Code change can be kept small if the new decision stays inside booking-service.
  - Behavioral risk is higher because this is a cross-service entry flow touching booking validity, slot status synchronization, Unity spawn, and verify-slot.

## Recommended minimal implementation plan

1. Keep the authoritative decision in booking-service.
   - Add one new service-layer helper in `bookings/services.py` that receives a booking plus `arrival_time=timezone.now()`.
   - This helper should:
     - accept early arrival according to the new rule,
     - define the new interval `[arrival_time, existing end_time]`,
     - first test the current slot against that interval,
     - only if current slot conflicts, search replacement candidates.

2. Minimize search scope before widening it.
   - First pass: same `zone_id`, same `vehicle_type`, same lot.
   - If business requires wider fallback, second pass: same lot + vehicle type across zones.
   - This keeps the smallest implementation surface and avoids unnecessary denormalized zone/floor mutation when a same-zone slot exists.

3. Reuse existing overlap infrastructure.
   - Candidate discovery: parking-service `GET /parking/slots/`.
   - Conflict exclusion: booking-service `check_overlapping_bookings()` or its underlying query.
   - No new overlap algorithm is needed.

4. Persist slot/window change before serialization and events.
   - Update `start_time` and, for hourly bookings, `hourly_start` if the business truly means session starts at arrival time.
   - If slot changes, update `slot_id` and `slot_code`.
   - If cross-zone fallback is allowed, also update `zone_id`, `zone_name`, `floor_id`, `floor_level`.

5. Emit two slot events when reassignment happens.
   - Old slot: `available`
   - New slot: `occupied`
   - Existing `slot.status_changed` schema is enough for this; no schema change is strictly required.

6. Keep booking response shape stable, but fix consumers.
   - `BookingLifecycleViewSet.checkin` can keep returning serialized booking.
   - `esp32_checkin_service.process_checkin` must use the slot from the check-in response for `update_slot_status()` and Unity spawn.
   - `esp32_verify_service` should then continue to work without API shape change because booking data will already contain the new slot.

## Source anchors

- `booking-service/bookings/services.py`
  - `validate_checkin`
  - `perform_checkin`
  - `check_overlapping_bookings`
- `booking-service/bookings/views_lifecycle.py`
  - `BookingLifecycleViewSet.checkin`
- `booking-service/bookings/serializers.py`
  - `CreateBookingSerializer.create`
  - `BookingSerializer.get_car_slot`
- `ai-service-fastapi/app/services/esp32_checkin_service.py`
  - `process_checkin`
- `ai-service-fastapi/app/services/esp32_helpers.py`
  - `CHECK_IN_EARLY_MINUTES`
- `ai-service-fastapi/app/services/esp32_verify_service.py`
  - `process_verify_slot`
- `parking-service/infrastructure/views.py`
  - `ZoneViewSet.get_queryset`
  - `CarSlotViewSet.get_queryset`
  - `CarSlotViewSet.check_slots_availability`
  - `CarSlotViewSet.update_status`
