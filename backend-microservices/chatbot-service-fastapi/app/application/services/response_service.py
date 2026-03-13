"""
Response Service — generates personalized responses via LLM.
Uses user style profile for tone/emoji/format personalization.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from app.application.dto import IntentDecision

logger = logging.getLogger(__name__)


class ResponseService:
    """Generates user-facing responses with personalization."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def generate_response(
        self,
        decision: IntentDecision,
        action_result: dict[str, Any],
        user_style: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Generate a personalized response after successful action."""
        style = user_style or {}

        if self.llm_client:
            try:
                return await self._llm_response(decision, action_result, style)
            except Exception as e:
                logger.warning(f"LLM response gen failed, using template: {e}")

        return self._template_response(decision, action_result, style)

    async def generate_clarification(
        self, decision: IntentDecision
    ) -> dict[str, Any]:
        """Generate a clarification question with helpful guidance."""
        intent = decision.primary_intent
        missing = decision.missing_entities or []

        # Build smart clarification messages per intent + missing entity
        question = self._build_smart_clarification(intent, missing, decision.entities)

        return {
            "response": question,
            "intent": intent,
            "entities": decision.entities,
            "suggestions": self._get_clarification_suggestions(decision),
            "data": {},
            "confidence": decision.hybrid_confidence,
            "clarificationNeeded": True,
            "confirmationNeeded": False,
        }

    async def generate_confirmation(
        self, decision: IntentDecision
    ) -> dict[str, Any]:
        """Generate a confirmation prompt for high-stakes actions."""
        intent_labels = {
            "book_slot": "đặt chỗ đậu xe",
            "cancel_booking": "hủy booking",
            "check_out": "check-out",
        }
        action_label = intent_labels.get(decision.primary_intent, decision.primary_intent)

        entity_summary = ""
        if decision.entities:
            parts = [f"{k}: {v}" for k, v in decision.entities.items()]
            entity_summary = " (" + ", ".join(parts) + ")"

        response = f"Bạn muốn {action_label}{entity_summary}. Bạn xác nhận không?"

        return {
            "response": response,
            "intent": decision.primary_intent,
            "entities": decision.entities,
            "suggestions": ["Xác nhận", "Hủy bỏ"],
            "data": {},
            "confidence": decision.hybrid_confidence,
            "clarificationNeeded": False,
            "confirmationNeeded": True,
        }

    async def generate_safety_error(
        self,
        decision: IntentDecision,
        safety_code: str,
        safety_hint: str,
    ) -> dict[str, Any]:
        """
        🔥 2.3: Generate error response with safety code and hint.
        """
        return {
            "response": f"⚠️ {safety_hint}",
            "intent": decision.primary_intent,
            "entities": decision.entities,
            "suggestions": self._get_safety_suggestions(safety_code),
            "data": {"safetyCode": safety_code, "safetyHint": safety_hint},
            "confidence": decision.hybrid_confidence,
            "clarificationNeeded": False,
            "confirmationNeeded": False,
        }

    async def generate_handoff(self) -> dict[str, Any]:
        """Response when handing off to human support."""
        return {
            "response": "Tôi sẽ chuyển bạn đến nhân viên hỗ trợ. Vui lòng chờ trong giây lát! 👋",
            "intent": "handoff",
            "entities": {},
            "suggestions": [],
            "data": {"handoff": True},
            "confidence": 1.0,
            "clarificationNeeded": False,
            "confirmationNeeded": False,
        }

    async def generate_fallback(self) -> dict[str, Any]:
        """Fallback when everything fails."""
        return {
            "response": "Xin lỗi, tôi chưa hiểu rõ yêu cầu của bạn. Bạn có thể thử lại?",
            "intent": "unknown",
            "entities": {},
            "suggestions": ["Xem chỗ trống", "Đặt chỗ", "Xem booking", "Trợ giúp"],
            "data": {},
            "confidence": 0.0,
            "clarificationNeeded": False,
            "confirmationNeeded": False,
        }

    # ─── Private ─────────────────────────────────────

    async def _llm_response(
        self,
        decision: IntentDecision,
        action_result: dict,
        style: dict,
    ) -> dict[str, Any]:
        """Generate response using LLM with user style context."""
        tone = "ngắn gọn" if style.get("prefers_short", True) else "chi tiết, thân thiện"
        emoji_note = ""
        emoji_level = style.get("emoji_level", 1)
        if emoji_level >= 2:
            emoji_note = "Dùng nhiều emoji."
        elif emoji_level == 0:
            emoji_note = "Không dùng emoji."

        system_prompt = f"""Bạn là ParkSmart AI. Phong cách: {tone}. {emoji_note}
Trả lời dựa trên kết quả hành động. Gợi ý bước tiếp theo nếu phù hợp."""

        user_prompt = f"""Intent: {decision.primary_intent}
Entities: {decision.entities}
Action Result: {action_result}

Hãy tạo response tự nhiên cho người dùng."""

        raw = await self.llm_client.generate(system_prompt, user_prompt)

        return {
            "response": raw.strip(),
            "intent": decision.primary_intent,
            "entities": decision.entities,
            "suggestions": self._get_action_suggestions(decision.primary_intent),
            "data": action_result,
            "confidence": decision.hybrid_confidence,
            "clarificationNeeded": False,
            "confirmationNeeded": False,
        }

    def _template_response(
        self,
        decision: IntentDecision,
        action_result: dict,
        style: dict,
    ) -> dict[str, Any]:
        """Rich template-based response with actual data from action_result."""
        intent = decision.primary_intent
        entities = decision.entities
        status = action_result.get("status", "")

        if status == "error":
            error_msg = action_result.get("error", "Unknown")
            text = f"⚠️ Có lỗi xảy ra: {error_msg}"
        else:
            text = self._build_rich_response(intent, entities, action_result)

        # Build suggestions — use wizard-aware suggestions if wizard active
        wizard_step = action_result.get("wizard_step")
        if wizard_step == "select_floor":
            floors = action_result.get("floors", [])
            suggestions = [f.get("name", f"Tầng {i}") for i, f in enumerate(floors, 1)]
            suggestions.append("Hủy")
        elif wizard_step == "select_zone":
            zones = action_result.get("zones", [])
            suggestions = [z.get("name", f"Zone {i}") for i, z in enumerate(zones, 1)]
            suggestions.append("Hủy")
        else:
            suggestions = self._get_action_suggestions(intent)

        return {
            "response": text,
            "intent": intent,
            "entities": entities,
            "suggestions": suggestions,
            "data": action_result,
            "confidence": decision.hybrid_confidence,
            "showMap": intent in ("check_availability", "current_parking"),
            "showQrCode": intent in ("check_in",),
            "clarificationNeeded": False,
            "confirmationNeeded": False,
        }

    def _build_rich_response(
        self, intent: str, entities: dict, action_result: dict
    ) -> str:
        """Build detailed response text with actual data from microservices."""

        if intent == "greeting":
            return "Xin chào! 👋 Tôi có thể giúp gì cho bạn?"

        if intent == "goodbye":
            return "Tạm biệt! 👋 Hẹn gặp lại bạn. Chúc bạn một ngày tốt lành!"

        if intent == "check_availability":
            return self._format_availability(entities, action_result)

        if intent == "book_slot":
            # Check if this is a wizard step response
            wizard_step = action_result.get("wizard_step")
            if wizard_step == "select_floor":
                return self._format_floor_selection(entities, action_result)
            if wizard_step == "select_zone":
                return self._format_zone_selection(entities, action_result)
            return self._format_booking_result(entities, action_result)

        if intent == "cancel_booking":
            return "🗑️ Đã hủy booking thành công!"

        if intent == "check_in":
            return "✅ Check-in thành công! Chúc bạn đậu xe vui vẻ."

        if intent == "check_out":
            return "✅ Check-out thành công! Hẹn gặp lại bạn."

        if intent == "my_bookings":
            return self._format_bookings_list(action_result)

        if intent == "current_parking":
            return self._format_current_parking(action_result)

        if intent == "pricing":
            return self._format_pricing(entities, action_result)

        if intent == "help":
            return (
                "ℹ️ **Tôi có thể giúp bạn:**\n"
                "• **Xem chỗ trống** — hỏi \"Còn mấy chỗ trống cho ô tô?\"\n"
                "• **Đặt chỗ** — hỏi \"Tôi muốn đặt chỗ cho xe máy\"\n"
                "• **Xem booking** — hỏi \"Cho tôi xem lịch đặt\"\n"
                "• **Hủy booking** — hỏi \"Hủy booking\"\n"
                "• **Check-in/out** — hỏi \"Check-in\" hoặc \"Check-out\"\n"
                "• **Xem giá** — hỏi \"Giá đậu xe bao nhiêu?\"\n"
                "• **Xe đang đậu** — hỏi \"Xe tôi đang đậu ở đâu?\""
            )

        if intent == "feedback":
            return "Cảm ơn phản hồi của bạn! 🙏"

        return "Đã xử lý yêu cầu của bạn."

    def _format_availability(self, entities: dict, result: dict) -> str:
        """Format slot availability data into readable response."""
        vehicle_type = entities.get("vehicle_type", "")
        vehicle_label = "ô tô" if vehicle_type == "car" else "xe máy" if vehicle_type == "motorcycle" else "xe"
        slots = result.get("slots", [])
        total = result.get("totalAvailable", len(slots))

        if total == 0:
            return f"😔 Hiện tại không còn chỗ trống cho {vehicle_label}. Bạn có thể thử lại sau!"

        text = f"🅿️ Hiện có **{total} chỗ trống** cho {vehicle_label}:\n"

        # Group by zone/floor if data available
        zones: dict[str, list] = {}
        for slot in slots[:20]:  # Limit display
            zone_name = slot.get("zone_name") or slot.get("zone") or slot.get("lot_name") or "Khu vực chung"
            floor = slot.get("floor", "")
            key = f"{zone_name}" + (f" - Tầng {floor}" if floor else "")
            zones.setdefault(key, []).append(slot)

        if zones:
            for zone_key, zone_slots in zones.items():
                text += f"• **{zone_key}**: {len(zone_slots)} chỗ\n"
        else:
            text += f"• Tổng cộng: {total} chỗ trống\n"

        text += "\nBạn muốn đặt chỗ không?"
        return text

    def _format_floor_selection(self, entities: dict, result: dict) -> str:
        """Format floor selection step of booking wizard."""
        vehicle_type = entities.get("vehicle_type", "")
        vehicle_label = (
            "ô tô" if vehicle_type == "car"
            else "xe máy" if vehicle_type == "motorcycle"
            else "xe"
        )
        floors = result.get("floors", [])
        total = result.get("total_available", 0)

        text = f"🅿️ Có **{total} chỗ trống** cho {vehicle_label}.\n"
        text += "Bạn muốn đậu ở tầng nào?\n\n"

        for i, floor in enumerate(floors, 1):
            name = floor.get("name", f"Tầng {floor.get('level', i)}")
            avail = floor.get("total_available", 0)
            zones = floor.get("zones", [])
            zone_names = ", ".join(z.get("name", "") for z in zones)
            text += f"**{i}. {name}** — {avail} chỗ trống"
            if zone_names:
                text += f" ({zone_names})"
            text += "\n"

        text += "\n💡 Hãy chọn tầng bạn muốn (ví dụ: \"Tầng 1\" hoặc \"B1\")"
        return text

    def _format_zone_selection(self, entities: dict, result: dict) -> str:
        """Format zone selection step of booking wizard."""
        floor_name = result.get("floor_name", "")
        zones = result.get("zones", [])

        text = f"📍 **{floor_name}** — Chọn khu vực:\n\n"

        for i, zone in enumerate(zones, 1):
            name = zone.get("name", f"Zone {i}")
            avail = zone.get("availableSlots", 0)
            text += f"**{i}. {name}** — {avail} chỗ trống\n"

        text += "\n💡 Hãy chọn khu vực (ví dụ: \"Zone A\" hoặc \"1\")"
        return text

    def _format_booking_result(self, entities: dict, result: dict) -> str:
        """Format booking creation result with rich details."""
        if result.get("status") == "error":
            return f"⚠️ Không thể đặt chỗ: {result.get('error', 'Lỗi không xác định')}"

        # Extract from nested booking object (booking-service returns {booking: {...}, message, qrCode})
        booking = result.get("booking", result)
        booking_id = (
            booking.get("id") or booking.get("booking_id") or booking.get("bookingId", "")
        )
        slot_name = (
            booking.get("slotCode") or booking.get("slot_code")
            or booking.get("slot_name") or booking.get("slotName", "")
        )
        zone_name = booking.get("zoneName") or booking.get("zone_name", "")
        lot_name = booking.get("parkingLotName") or booking.get("parking_lot_name", "")
        vehicle_type = entities.get("vehicle_type", "")
        vehicle_label = "ô tô" if vehicle_type == "car" else "xe máy" if vehicle_type == "motorcycle" else "xe"
        start_time = booking.get("startTime") or booking.get("start_time", "")
        end_time = booking.get("endTime") or booking.get("end_time", "")
        price = booking.get("price", "")
        qr_code = result.get("qrCode") or result.get("qr_code", "")

        text = "✅ **Đặt chỗ thành công!** 🎉\n"
        if booking_id:
            text += f"• Mã booking: `{str(booking_id)[:8]}`\n"
        text += f"• Loại xe: {vehicle_label}\n"
        if slot_name:
            text += f"• Vị trí: {slot_name}\n"
        if zone_name:
            text += f"• Khu vực: {zone_name}\n"
        if lot_name:
            text += f"• Bãi: {lot_name}\n"
        if start_time:
            text += f"• Bắt đầu: {start_time[:16].replace('T', ' ')}\n"
        if end_time:
            text += f"• Kết thúc: {end_time[:16].replace('T', ' ')}\n"
        if price:
            text += f"• Giá: {float(price):,.0f}đ\n"

        text += "\nHãy nhớ check-in khi đến bãi nhé! 🚗"
        if qr_code:
            text += "\n📱 QR code đã sẵn sàng để check-in."
        return text

    def _format_bookings_list(self, result: dict) -> str:
        """Format user's bookings list with rich details."""
        bookings = result.get("bookings", [])

        if not bookings:
            return "📋 Bạn chưa có booking nào. Bạn muốn đặt chỗ không?"

        text = f"📋 **Booking của bạn** ({len(bookings)} booking):\n"
        for i, b in enumerate(bookings[:5], 1):
            check_in_status = b.get("checkInStatus") or b.get("check_in_status", "unknown")
            status_icon = {
                "not_checked_in": "🟡",
                "checked_in": "🟢",
                "checked_out": "✅",
                "cancelled": "🔴",
            }.get(check_in_status, "⚪")
            status_label = {
                "not_checked_in": "Chờ check-in",
                "checked_in": "Đang đậu",
                "checked_out": "Đã hoàn thành",
                "cancelled": "Đã hủy",
            }.get(check_in_status, check_in_status)

            slot = b.get("slotCode") or b.get("slot_code") or b.get("slotName") or b.get("slot_name", "")
            zone = b.get("zoneName") or b.get("zone_name", "")
            lot = b.get("parkingLotName") or b.get("parking_lot_name", "")
            vehicle_type = b.get("vehicleType") or b.get("vehicle_type", "")
            bid = str(b.get("id") or b.get("booking_id", ""))
            start_time = b.get("startTime") or b.get("start_time", "")

            text += f"\n{i}. {status_icon} **{status_label}**"
            if bid:
                text += f" (#{bid[:8]})"
            text += "\n"
            if vehicle_type:
                text += f"   🚗 {vehicle_type}\n"
            if slot:
                text += f"   📍 Vị trí: {slot}"
                if zone:
                    text += f" - {zone}"
                if lot:
                    text += f" ({lot})"
                text += "\n"
            if start_time:
                text += f"   🕐 {start_time[:16].replace('T', ' ')}\n"

        if len(bookings) > 5:
            text += f"\n... và {len(bookings) - 5} booking khác."
        return text

    def _format_current_parking(self, result: dict) -> str:
        """Format current parking info from booking data."""
        parking = result.get("parking")
        if not parking:
            return "📍 Bạn hiện không có xe nào đang đậu trong bãi."

        # Extract slot info
        slot_obj = parking.get("carSlot") or {}
        slot_name = (
            slot_obj.get("code") or slot_obj.get("slotCode")
            if isinstance(slot_obj, dict) else ""
        ) or parking.get("slotCode", "")

        # Extract zone info
        zone_obj = parking.get("zone") or {}
        zone_name = (
            zone_obj.get("name") if isinstance(zone_obj, dict) else ""
        ) or parking.get("zoneName", "")

        # Extract floor info
        floor_obj = parking.get("floor") or {}
        floor_level = (
            floor_obj.get("level") if isinstance(floor_obj, dict) else ""
        )

        # Extract parking lot info
        lot_obj = parking.get("parkingLot") or {}
        lot_name = (
            lot_obj.get("name") if isinstance(lot_obj, dict) else ""
        ) or parking.get("parkingLotName", "")

        # Extract check-in time
        checked_in_at = parking.get("checkedInAt", "")

        text = "📍 **Xe đang đậu:**\n"
        if lot_name:
            text += f"• Bãi xe: {lot_name}\n"
        if floor_level:
            text += f"• Tầng: {floor_level}\n"
        if zone_name:
            text += f"• Khu vực: {zone_name}\n"
        if slot_name:
            text += f"• Vị trí: {slot_name}\n"
        if checked_in_at:
            try:
                dt = datetime.fromisoformat(str(checked_in_at).replace("Z", "+00:00"))
                text += f"• Check-in lúc: {dt.strftime('%H:%M %d/%m/%Y')}\n"
            except (ValueError, TypeError):
                pass
        return text

    def _format_pricing(self, entities: dict, result: dict) -> str:
        """Format pricing information."""
        pricing = result.get("pricing", [])
        vehicle_type = entities.get("vehicle_type", "")

        if not pricing:
            text = "💰 **Bảng giá đậu xe:**\n"
            text += "• Ô tô: 20.000đ/giờ\n"
            text += "• Xe máy: 5.000đ/giờ\n"
            text += "\n_(Giá có thể thay đổi theo khu vực và thời gian)_"
            return text

        text = "💰 **Bảng giá đậu xe:**\n"
        for p in pricing:
            name = p.get("name") or p.get("vehicle_type", "")
            price = p.get("price") or p.get("hourly_rate") or p.get("amount", 0)
            unit = p.get("unit", "giờ")
            text += f"• {name}: {price:,.0f}đ/{unit}\n" if isinstance(price, (int, float)) else f"• {name}: {price}/{unit}\n"

        return text

    @staticmethod
    def _build_smart_clarification(
        intent: str, missing: list[str], entities: dict
    ) -> str:
        """Build natural clarification questions based on intent + missing entities."""
        if intent == "check_availability":
            if "vehicle_type" in missing:
                return "🅿️ Bạn muốn xem chỗ trống cho loại xe nào? Ô tô hay xe máy?"
            return "Bạn muốn tìm chỗ trống ở khu vực nào?"

        if intent == "book_slot":
            missing_parts = []
            if "vehicle_type" in missing:
                missing_parts.append("loại xe (ô tô / xe máy)")
            if "start_time" in missing:
                missing_parts.append("thời gian bắt đầu")
            if "end_time" in missing:
                missing_parts.append("thời gian kết thúc (hoặc số giờ)")

            if missing_parts:
                return f"🚗 Để đặt chỗ, bạn cho tôi biết thêm: {', '.join(missing_parts)} nhé!"
            return "Bạn muốn đặt chỗ như thế nào?"

        if intent == "cancel_booking":
            if "booking_id" in missing:
                return "🗑️ Bạn muốn hủy booking nào? Hãy cho tôi mã booking hoặc nói \"Xem booking của tôi\" để tôi liệt kê."

        if intent in ("check_in", "check_out"):
            if "booking_id" in missing:
                action = "check-in" if intent == "check_in" else "check-out"
                return f"✅ Bạn muốn {action} cho booking nào? Hãy cho tôi mã booking."

        # Generic fallback
        if missing:
            missing_str = ", ".join(missing)
            return f"Để giúp bạn, tôi cần thêm thông tin: {missing_str}. Bạn có thể cung cấp thêm không?"

        return "Bạn có thể nói rõ hơn không?"

    @staticmethod
    def _get_clarification_suggestions(decision: IntentDecision) -> list[str]:
        intent = decision.primary_intent
        missing = decision.missing_entities or []

        if "vehicle_type" in missing:
            return ["Ô tô", "Xe máy"]

        intent_suggestions = {
            "book_slot": ["Đặt ô tô 1 giờ", "Đặt xe máy 2 giờ", "Đặt lại như lần trước"],
            "check_availability": ["Ô tô", "Xe máy"],
            "cancel_booking": ["Xem booking của tôi"],
            "check_in": ["Xem booking của tôi"],
            "check_out": ["Xem booking của tôi"],
        }
        return intent_suggestions.get(intent, ["Trợ giúp"])

    @staticmethod
    def _get_action_suggestions(intent: str) -> list[str]:
        suggestions_map = {
            "greeting": ["Xem chỗ trống", "Đặt chỗ", "Xem booking", "Xem giá"],
            "goodbye": [],
            "check_availability": ["Đặt chỗ", "Xem giá"],
            "book_slot": ["Check-in", "Xem booking"],
            "cancel_booking": ["Đặt chỗ mới", "Xem chỗ trống"],
            "check_in": ["Xem vị trí xe", "Check-out"],
            "check_out": ["Đặt chỗ mới", "Xem giá"],
            "my_bookings": ["Hủy booking", "Check-in"],
            "pricing": ["Đặt chỗ", "Xem chỗ trống"],
            "help": ["Xem chỗ trống", "Đặt chỗ"],
        }
        return suggestions_map.get(intent, ["Trợ giúp"])

    @staticmethod
    def _get_safety_suggestions(safety_code: str) -> list[str]:
        """🔥 2.3: Context-aware suggestions based on safety code."""
        safety_suggestions = {
            "SLOT_NOT_AVAILABLE": ["Xem slot khác", "Chọn thời gian khác"],
            "DOUBLE_BOOKING": ["Xem booking hiện tại", "Hủy booking cũ"],
            "OUT_OF_OPERATING_HOURS": ["Xem giờ hoạt động", "Chọn thời gian khác"],
            "VEHICLE_NOT_FOUND": ["Thêm xe mới", "Xem danh sách xe"],
            "BOOKING_NOT_FOUND": ["Xem booking của tôi"],
            "ALREADY_CHECKED_IN": ["Check-out", "Xem vị trí xe"],
            "NOT_CHECKED_IN": ["Check-in", "Xem booking"],
            "MAX_BOOKINGS_REACHED": ["Hủy booking cũ", "Xem booking"],
        }
        return safety_suggestions.get(safety_code, ["Trợ giúp"])
