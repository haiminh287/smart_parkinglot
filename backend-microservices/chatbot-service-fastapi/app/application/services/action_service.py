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

    def __init__(self, service_client: Optional[Any] = None, llm_client: Optional[Any] = None):
        self.service_client = service_client
        self.llm_client = llm_client  # Optional, used by FAQ handler to summarize RAG hits

    async def execute(
        self, user_id: str, decision: IntentDecision, user_message: str = ""
    ) -> dict[str, Any]:
        """Execute the appropriate action for the intent.

        user_message: raw message from user, dùng cho FAQ RAG retrieval.
        """
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
            Intent.OPERATING_HOURS: self._get_operating_hours,
        }

        dispatcher = dispatchers.get(intent)

        # FAQ intent xử lý riêng — cần user_message cho RAG retrieval
        if intent == Intent.FAQ:
            return await self._handle_faq(user_id, decision.entities, user_message)

        if not dispatcher:
            return {"status": "no_action", "intent": intent.value}

        try:
            return await dispatcher(user_id, decision.entities)
        except Exception as e:
            logger.error(f"Action execution failed for {intent}: {e}")
            return {"status": "error", "error": str(e), "intent": intent.value}

    async def _check_availability(self, user_id: str, entities: dict) -> dict:
        """Check availability với 3 bước enhancement so với phiên bản cũ:

        1. Resolve `lot_name` → `lot_id` (LLM thường trả tên "Vincom..." chứ
           không có UUID). Match fuzzy theo tên.
        2. Query slots với status=available + lot_id filter.
        3. Group slot theo zone → trả danh sách mã slot cụ thể đầu mỗi zone.
           Time-window filter để sau (cần booking-service support `?available_at=`).
        """
        if not self.service_client:
            return {"status": "ok", "message": "Service client not configured"}

        vehicle_type = self._map_vehicle_type(entities.get("vehicle_type"))
        lot_id = entities.get("lot_id")
        lot_name = entities.get("lot_name") or entities.get("parking_lot")

        # ── Resolve lot_name → lot_id nếu thiếu ID ──
        if not lot_id and lot_name:
            try:
                lots = await self.service_client.get_parking_lots(user_id=user_id)
                target = (lot_name or "").lower().strip()
                for lot in lots or []:
                    name = (lot.get("name") or "").lower()
                    # Fuzzy: tên lot chứa từ khoá user nói hoặc ngược lại
                    if target in name or any(t in name for t in target.split() if len(t) > 2):
                        lot_id = lot.get("id")
                        logger.info("Resolved lot_name '%s' → lot_id %s", lot_name, lot_id)
                        break
            except Exception as e:
                logger.warning("Failed to resolve lot_name: %s", e)

        result = await self.service_client.get_available_slots(
            vehicle_type=vehicle_type,
            lot_id=lot_id,
            user_id=user_id,
        )

        # ── Enrich: group slot theo zone + limit codes để FE/LLM dễ format ──
        slots = result.get("slots", []) if isinstance(result, dict) else []
        zones_grouped: dict[str, list[str]] = {}
        for s in slots:
            # Zone name có thể null (seed cũ) — fallback zone code prefix
            zone_name = s.get("zoneName") or s.get("zone_name") or ""
            code = s.get("code", "")
            if not zone_name and code and "-" in code:
                zone_name = f"Zone {code.split('-')[0]}"
            zone_name = zone_name or "Khu vực chung"
            zones_grouped.setdefault(zone_name, []).append(code)

        # Limit mỗi zone lấy 5 slot đầu để câu trả lời ngắn gọn
        zones_summary = [
            {
                "zone": zone,
                "count": len(codes),
                "sample_codes": sorted(c for c in codes if c)[:5],
            }
            for zone, codes in sorted(zones_grouped.items(), key=lambda kv: -len(kv[1]))
        ]
        result["zones"] = zones_summary
        result["lot_id_resolved"] = lot_id
        result["lot_name_query"] = lot_name
        return result

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

    async def _get_operating_hours(self, user_id: str, entities: dict) -> dict:
        return {
            "status": "ok",
            "operating_hours": {
                "weekdays": "06:00 - 22:00",
                "weekends": "06:00 - 23:00",
                "note": "Mở cửa 7 ngày/tuần"
            }
        }

    async def _handle_faq(self, user_id: str, entities: dict, user_message: str) -> dict:
        """FAQ handler — dùng RAG retrieve docs + LLM sinh câu trả lời có citation.

        Nếu RAG không available → fallback message.
        Nếu retrieve rỗng → "chưa biết" thành thật.
        """
        from app.infrastructure.rag import get_rag_store

        rag = get_rag_store()
        if not rag:
            return {
                "status": "error",
                "error": "Tôi chưa kết nối được knowledge base. Vui lòng liên hệ hotline 1900-PARKSMART.",
            }

        docs = rag.retrieve(user_message, top_k=3)
        if not docs:
            return {
                "status": "no_match",
                "message": (
                    "Tôi chưa tìm được thông tin phù hợp với câu hỏi của bạn. "
                    "Bạn có thể mô tả rõ hơn hoặc liên hệ support@parksmart.com."
                ),
            }

        # Build context cho LLM — đính kèm citation
        context_blocks = [
            f"[Nguồn {i+1}: {doc.metadata.get('source', '?')}]\n{doc.content}"
            for i, doc in enumerate(docs)
        ]
        context = "\n\n".join(context_blocks)

        if not self.llm_client:
            # Fallback: trả raw chunk đầu
            return {
                "status": "ok",
                "answer": docs[0].content[:500],
                "sources": [d.metadata.get("source", "?") for d in docs],
                "num_docs": len(docs),
            }

        system_prompt = (
            "Bạn là trợ lý ParkSmart. Trả lời câu hỏi người dùng CHỈ DỰA VÀO "
            "context được cung cấp. Nếu context không đủ thông tin để trả lời, "
            "hãy nói thành thật là bạn chưa có thông tin đó. "
            "Trích dẫn nguồn [Nguồn N] khi đưa ra mỗi thông tin cụ thể. "
            "Trả lời ngắn gọn, rõ ràng bằng tiếng Việt."
        )
        user_prompt = (
            f"Context:\n{context}\n\n"
            f"Câu hỏi người dùng: {user_message}\n\n"
            f"Trả lời ngắn gọn, kèm trích dẫn nguồn:"
        )

        try:
            answer = await self.llm_client.generate(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"FAQ LLM generate failed: {e}")
            answer = docs[0].content[:500]

        return {
            "status": "ok",
            "answer": answer,
            "sources": [d.metadata.get("source", "?") for d in docs],
            "num_docs": len(docs),
            "top_score": docs[0].score if docs else 0.0,
        }

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
