"""
Action Service — executes actions by calling internal microservices.

Smart booking flow:
  1. Convert relative times → ISO datetimes
  2. Auto-find available slot for the requested vehicle_type
  3. Auto-find user's vehicle (or first matching vehicle_type)
  4. Extract zone_id / parking_lot_id from slot data
  5. Call create_booking with all required fields
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.application.dto import IntentDecision
from app.domain.value_objects.intent import Intent

logger = logging.getLogger(__name__)


def _resolve_datetime(relative: Optional[str], base: Optional[datetime] = None) -> Optional[str]:
    """Convert relative time strings to ISO datetime.

    Args:
        relative: Relative time like 'now', 'today', 'tomorrow', '+1h', '+2h', '+3h', '+8h'.
        base: Base datetime to resolve from. Defaults to UTC now.

    Returns:
        ISO 8601 datetime string or None.
    """
    if not relative:
        return None
    now = base or datetime.now(timezone.utc)
    rel = relative.strip().lower()

    if rel in ("now", "bây giờ", "ngay"):
        return now.isoformat()
    if rel in ("today", "hôm nay"):
        return now.replace(minute=0, second=0, microsecond=0).isoformat()
    if rel in ("tomorrow", "ngày mai"):
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=8, minute=0, second=0, microsecond=0).isoformat()

    # +Nh pattern (e.g. +1h, +2h, +8h)
    if rel.startswith("+") and rel.endswith("h"):
        try:
            hours = int(rel[1:-1])
            return (now + timedelta(hours=hours)).isoformat()
        except ValueError:
            pass

    # Already ISO format — return as-is
    if "T" in relative or "-" in relative:
        return relative

    return None


class ActionService:
    """Dispatches intent to the correct microservice via HTTP.

    For book_slot, performs smart resolution:
    - Finds available slot matching vehicle_type
    - Gets user's vehicle of the right type
    - Extracts zone/lot info from slot
    - Converts relative times to ISO
    """

    def __init__(self, service_client: Optional[Any] = None):
        self.service_client = service_client

    async def execute(
        self, user_id: str, decision: IntentDecision
    ) -> dict[str, Any]:
        """Execute the appropriate action for the intent."""
        try:
            intent = Intent(decision.primary_intent)
        except ValueError:
            return {"status": "no_action", "intent": decision.primary_intent}

        dispatchers = {
            Intent.CHECK_AVAILABILITY: self._check_availability,
            Intent.BOOK_SLOT: self._book_slot,
            Intent.REBOOK_PREVIOUS: self._rebook_previous,
            Intent.CANCEL_BOOKING: self._cancel_booking,
            Intent.CHECK_IN: self._check_in,
            Intent.CHECK_OUT: self._check_out,
            Intent.MY_BOOKINGS: self._my_bookings,
            Intent.CURRENT_PARKING: self._current_parking,
            Intent.PRICING: self._get_pricing,
        }

        dispatcher = dispatchers.get(intent)
        if not dispatcher:
            return {"status": "no_action", "intent": intent.value}

        try:
            return await dispatcher(user_id, decision.entities)
        except Exception as e:
            logger.error(f"Action execution failed for {intent}: {e}")
            return {"status": "error", "error": str(e), "intent": intent.value}

    async def _check_availability(self, user_id: str, entities: dict) -> dict:
        if self.service_client:
            return await self.service_client.get_available_slots(
                vehicle_type=self._map_vehicle_type(entities.get("vehicle_type")),
                lot_id=entities.get("lot_id"),
            )
        return {"status": "ok", "message": "Service client not configured"}

    async def _book_slot(self, user_id: str, entities: dict) -> dict:
        """Smart booking wizard — Step 1: Show available floors.

        Instead of auto-booking, starts an interactive wizard flow:
          Step 1 (here): Fetch floors with zones → let user pick floor
          Step 2: _book_slot_select_floor() → show zones on that floor
          Step 3: _book_slot_select_zone() → auto-book in selected zone

        Returns wizard_step data for orchestrator to store in context.
        """
        if not self.service_client:
            return {"status": "ok", "message": "Booking simulated"}

        vehicle_type_input = entities.get("vehicle_type", "car")
        vehicle_type_db = self._map_vehicle_type(vehicle_type_input)

        # Fetch floors with nested zones from parking-service
        floors = await self.service_client.get_floors(user_id=user_id)

        if not floors:
            return {
                "status": "error",
                "error": "Không tìm thấy thông tin tầng nào. Vui lòng thử lại sau!",
            }

        # Filter floors that have zones matching the vehicle type
        matching_floors: list[dict] = []
        for floor in floors:
            zones = floor.get("zones", [])
            matching_zones = [
                z for z in zones
                if (z.get("vehicleType", "") or "").lower() == (vehicle_type_db or "").lower()
                and (z.get("availableSlots", 0) or 0) > 0
            ]
            if matching_zones:
                matching_floors.append({
                    "id": floor.get("id", ""),
                    "name": floor.get("name", ""),
                    "level": floor.get("level", 0),
                    "parkingLotId": floor.get("parkingLotId", ""),
                    "zones": matching_zones,
                    "total_available": sum(z.get("availableSlots", 0) for z in matching_zones),
                })

        if not matching_floors:
            return {
                "status": "error",
                "error": f"Không còn chỗ trống cho {self._vehicle_label(vehicle_type_input)} ở bất kỳ tầng nào.",
            }

        # Return wizard data — orchestrator will store in context
        return {
            "status": "ok",
            "wizard_step": "select_floor",
            "vehicle_type": vehicle_type_input,
            "vehicle_type_db": vehicle_type_db,
            "floors": matching_floors,
            "total_available": sum(f["total_available"] for f in matching_floors),
        }

    async def book_slot_select_floor(
        self, user_id: str, wizard: dict, floor_id: str
    ) -> dict:
        """Wizard Step 2: User selected a floor → show zones on that floor.

        Args:
            user_id: User ID.
            wizard: Current wizard state from context.
            floor_id: Selected floor ID.

        Returns:
            Dict with zones for the selected floor.
        """
        if not self.service_client:
            return {"status": "ok", "message": "Simulated"}

        vehicle_type_db = wizard.get("vehicle_type_db", "Car")
        floors = wizard.get("floors", [])

        # Find the selected floor
        selected_floor = None
        for f in floors:
            if str(f.get("id", "")) == floor_id:
                selected_floor = f
                break

        if not selected_floor:
            return {
                "status": "error",
                "error": "Không tìm thấy tầng được chọn. Vui lòng chọn lại.",
            }

        zones = selected_floor.get("zones", [])
        matching_zones = [
            z for z in zones
            if (z.get("vehicleType", "") or "").lower() == (vehicle_type_db or "").lower()
            and (z.get("availableSlots", 0) or 0) > 0
        ]

        if not matching_zones:
            return {
                "status": "error",
                "error": f"Tầng {selected_floor.get('name', '')} không còn chỗ trống.",
            }

        return {
            "status": "ok",
            "wizard_step": "select_zone",
            "floor_id": floor_id,
            "floor_name": selected_floor.get("name", ""),
            "lot_id": selected_floor.get("parkingLotId", ""),
            "zones": matching_zones,
        }

    async def book_slot_select_zone(
        self, user_id: str, wizard: dict, zone_id: str
    ) -> dict:
        """Wizard Step 3: User selected a zone → create booking.

        Auto-resolves: slot (first available), vehicle, times.
        Creates the booking directly.

        Args:
            user_id: User ID.
            wizard: Current wizard state from context.
            zone_id: Selected zone ID.

        Returns:
            Booking creation result.
        """
        if not self.service_client:
            return {"status": "ok", "message": "Booking simulated"}

        vehicle_type_input = wizard.get("vehicle_type", "car")
        vehicle_type_db = wizard.get("vehicle_type_db", "Car")
        lot_id = wizard.get("lot_id", "")
        floor_name = wizard.get("floor_name", "")
        now = datetime.now(timezone.utc)

        # Find zone name from wizard data
        zone_name = ""
        zones = wizard.get("zones", [])
        for z in zones:
            if str(z.get("id", "")) == zone_id:
                zone_name = z.get("name", "")
                break

        # Get available slots in this zone
        slots = await self.service_client.get_slots_by_zone(
            zone_id=zone_id, vehicle_type=vehicle_type_db,
        )

        if not slots:
            return {
                "status": "error",
                "error": f"Khu vực {zone_name} hiện không còn chỗ trống.",
            }

        chosen_slot = slots[0]
        slot_id = str(chosen_slot.get("id", ""))

        # If no lot_id from wizard, get from parking lots
        if not lot_id:
            lots = await self.service_client.get_parking_lots(user_id=user_id)
            if lots:
                lot_id = str(lots[0].get("id", ""))

        # Get user's vehicle
        vehicles = await self.service_client.get_user_vehicles(user_id)
        vehicle_id: Optional[str] = None
        if vehicles:
            for v in vehicles:
                v_type = (v.get("vehicleType") or v.get("vehicle_type") or "").lower()
                if vehicle_type_input in v_type or v_type in vehicle_type_input:
                    vehicle_id = str(v.get("id", ""))
                    break
            if not vehicle_id:
                vehicle_id = str(vehicles[0].get("id", ""))
        else:
            vehicle_id = f"chatbot-{vehicle_type_input}"

        # Default times: now → +1h
        start_iso = now.isoformat()
        end_iso = (now + timedelta(hours=1)).isoformat()

        logger.info(
            f"Wizard booking: user={user_id}, slot={slot_id}, zone={zone_id}, "
            f"lot={lot_id}, vehicle={vehicle_id}, floor={floor_name}"
        )

        # Create booking
        result = await self.service_client.create_booking(
            user_id=user_id,
            vehicle_id=vehicle_id,
            zone_id=zone_id,
            parking_lot_id=lot_id,
            slot_id=slot_id,
            start_time=start_iso,
            end_time=end_iso,
        )

        # Enrich result
        if result.get("status") != "error":
            result["slot_name"] = chosen_slot.get("code", slot_id)
            result["zone_name"] = zone_name
            result["floor_name"] = floor_name
            result["vehicle_type"] = vehicle_type_input

        return result

    async def _rebook_previous(self, user_id: str, entities: dict) -> dict:
        if self.service_client:
            # Get user's last booking and rebook with same params
            bookings_result = await self.service_client.get_user_bookings(user_id)
            bookings = bookings_result.get("bookings", [])
            if bookings:
                last = bookings[0]  # Most recent
                # Reuse same vehicle/zone/lot, new times
                now = datetime.now(timezone.utc)
                return await self.service_client.create_booking(
                    user_id=user_id,
                    vehicle_id=str(last.get("vehicleId") or last.get("vehicle_id", "")),
                    zone_id=str(last.get("zoneId") or last.get("zone_id", "")),
                    parking_lot_id=str(last.get("parkingLotId") or last.get("parking_lot_id", "")),
                    start_time=now.isoformat(),
                    end_time=(now + timedelta(hours=1)).isoformat(),
                )
            return {"status": "error", "error": "Bạn chưa có booking nào trước đó."}
        return {"status": "ok", "message": "Rebook simulated"}

    async def _cancel_booking(self, user_id: str, entities: dict) -> dict:
        if self.service_client:
            booking_id = entities.get("booking_id")
            if not booking_id:
                # Auto-cancel most recent active booking
                bookings_result = await self.service_client.get_user_bookings(user_id)
                bookings = bookings_result.get("bookings", [])
                for b in bookings:
                    status = b.get("status", b.get("checkInStatus", ""))
                    if status in ("not_checked_in", "confirmed", "pending", "active"):
                        booking_id = str(b.get("id", ""))
                        break
                if not booking_id:
                    return {"status": "error", "error": "Không tìm thấy booking để hủy."}

            return await self.service_client.cancel_booking(
                user_id=user_id, booking_id=booking_id,
            )
        return {"status": "ok", "message": "Cancel simulated"}

    async def _check_in(self, user_id: str, entities: dict) -> dict:
        if self.service_client:
            booking_id = entities.get("booking_id")
            if not booking_id:
                # Auto check-in most recent not-checked-in booking
                bookings_result = await self.service_client.get_user_bookings(user_id)
                bookings = bookings_result.get("bookings", [])
                for b in bookings:
                    if (b.get("checkInStatus") or b.get("check_in_status", "")) == "not_checked_in":
                        booking_id = str(b.get("id", ""))
                        break
                if not booking_id:
                    return {"status": "error", "error": "Không tìm thấy booking để check-in."}

            return await self.service_client.check_in(
                user_id=user_id, booking_id=booking_id,
            )
        return {"status": "ok", "message": "Check-in simulated"}

    async def _check_out(self, user_id: str, entities: dict) -> dict:
        if self.service_client:
            booking_id = entities.get("booking_id")
            if not booking_id:
                # Auto check-out the checked-in booking
                bookings_result = await self.service_client.get_user_bookings(user_id)
                bookings = bookings_result.get("bookings", [])
                for b in bookings:
                    if (b.get("checkInStatus") or b.get("check_in_status", "")) == "checked_in":
                        booking_id = str(b.get("id", ""))
                        break
                if not booking_id:
                    return {"status": "error", "error": "Không tìm thấy booking để check-out."}

            return await self.service_client.check_out(
                user_id=user_id, booking_id=booking_id,
            )
        return {"status": "ok", "message": "Check-out simulated"}

    async def _my_bookings(self, user_id: str, entities: dict) -> dict:
        if self.service_client:
            return await self.service_client.get_user_bookings(user_id=user_id)
        return {"status": "ok", "bookings": []}

    async def _current_parking(self, user_id: str, entities: dict) -> dict:
        if self.service_client:
            return await self.service_client.get_current_parking(user_id=user_id)
        return {"status": "ok", "parking": None}

    async def _get_pricing(self, user_id: str, entities: dict) -> dict:
        if self.service_client:
            return await self.service_client.get_pricing(
                vehicle_type=self._map_vehicle_type(entities.get("vehicle_type")),
            )
        return {"status": "ok", "pricing": []}

    @staticmethod
    def _map_vehicle_type(vtype: Optional[str]) -> Optional[str]:
        """Map chatbot vehicle type to DB format.

        Args:
            vtype: 'car', 'motorcycle', etc.

        Returns:
            'Car' or 'Motorbike' (matching parking-service DB values).
        """
        if not vtype:
            return None
        mapping = {
            "car": "Car",
            "ô tô": "Car",
            "xe hơi": "Car",
            "motorcycle": "Motorbike",
            "motorbike": "Motorbike",
            "xe máy": "Motorbike",
            "moto": "Motorbike",
        }
        return mapping.get(vtype.lower(), vtype.capitalize())

    @staticmethod
    def _vehicle_label(vtype: Optional[str]) -> str:
        """Get Vietnamese label for vehicle type."""
        if not vtype:
            return "xe"
        labels = {
            "car": "ô tô",
            "motorcycle": "xe máy",
        }
        return labels.get(vtype.lower(), vtype)
