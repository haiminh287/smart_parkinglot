"""Booking wizard — multi-step floor/zone selection flow."""

import logging
import re
from typing import Any, Dict, Optional

from app.application.dto import IntentDecision

logger = logging.getLogger(__name__)


class BookingWizard:
    """Handles multi-step booking wizard interactions (floor → zone selection)."""

    def __init__(self, action_svc, response_svc, intent_svc):
        self.action_svc = action_svc
        self.response_svc = response_svc
        self.intent_svc = intent_svc

    async def try_booking_wizard(
        self, message: str, context: Dict, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle multi-step booking wizard if active.

        Checks if a booking wizard is in progress and processes the user's
        selection (floor name, zone name, or cancellation).

        If the user's message clearly matches a different intent (e.g.,
        "Xem chỗ trống", "Giúp tôi"), the wizard is automatically
        cancelled and the normal pipeline handles the message.

        Returns:
            Response dict if wizard handled, None to fall through to normal pipeline.
        """
        wizard = context.get("booking_wizard")
        if not wizard:
            return None

        step = wizard.get("step", "")
        msg = message.strip().lower()

        # Allow user to cancel wizard at any step
        if self.is_confirmation(msg) is False:
            return {
                "response": "Đã hủy quá trình đặt chỗ. Bạn cần tôi giúp gì khác không?",
                "intent": "book_slot",
                "entities": {},
                "suggestions": ["Đặt chỗ", "Xem chỗ trống", "Trợ giúp"],
                "data": {},
                "confidence": 1.0,
                "clarificationNeeded": False,
                "confirmationNeeded": False,
                "booking_wizard": None,  # Clear wizard
            }

        # Check if user is switching to a completely different intent
        # If so, cancel wizard silently and let normal pipeline handle it
        intent_check = self.intent_svc._keyword_classify(msg)
        if (
            intent_check.primary_intent != "unknown"
            and intent_check.primary_intent != "book_slot"
            and intent_check.llm_confidence >= 0.8
        ):
            # User wants something else — cancel wizard, fall through
            # Mark for cleanup so the response will include booking_wizard=None
            context["booking_wizard"] = None
            context["_wizard_cancelled"] = True
            return None

        if step == "select_floor":
            return await self._wizard_select_floor(msg, wizard, user_id)

        if step == "select_zone":
            return await self._wizard_select_zone(msg, wizard, user_id)

        # Unknown wizard step — clear and fall through
        return None

    async def _wizard_select_floor(
        self, msg: str, wizard: Dict, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Process floor selection in booking wizard.

        Matches user input against available floor names/levels.
        """
        floors = wizard.get("floors", [])
        matched_floor = self.match_floor(msg, floors)

        if not matched_floor:
            # Didn't match — prompt again
            floor_names = ", ".join(f.get("name", "") for f in floors)
            return {
                "response": f"Tôi chưa nhận ra tầng bạn chọn. Các tầng có sẵn: {floor_names}. Bạn muốn chọn tầng nào?",
                "intent": "book_slot",
                "entities": {"vehicle_type": wizard.get("vehicle_type", "")},
                "suggestions": [f.get("name", "") for f in floors] + ["Hủy"],
                "data": {},
                "confidence": 1.0,
                "clarificationNeeded": False,
                "confirmationNeeded": False,
                "booking_wizard": wizard,  # Keep wizard active
            }

        # Floor matched — execute zone selection step
        floor_id = str(matched_floor.get("id", ""))
        action_result = await self.action_svc.book_slot_select_floor(
            user_id,
            wizard,
            floor_id,
        )

        if action_result.get("status") == "error":
            return {
                "response": f"⚠️ {action_result.get('error', 'Lỗi')}",
                "intent": "book_slot",
                "entities": {"vehicle_type": wizard.get("vehicle_type", "")},
                "suggestions": [f.get("name", "") for f in floors] + ["Hủy"],
                "data": {},
                "confidence": 1.0,
                "clarificationNeeded": False,
                "confirmationNeeded": False,
                "booking_wizard": wizard,  # Keep wizard
            }

        # Format zone selection response
        zones = action_result.get("zones", [])
        floor_name = action_result.get("floor_name", "")
        text = f"📍 **{floor_name}** — Chọn khu vực:\n\n"
        for i, zone in enumerate(zones, 1):
            name = zone.get("name", f"Zone {i}")
            avail = zone.get("availableSlots", 0)
            text += f"**{i}. {name}** — {avail} chỗ trống\n"
        text += '\n💡 Hãy chọn khu vực (ví dụ: "Zone A" hoặc "1")'

        # Update wizard state
        new_wizard = {
            **wizard,
            "step": "select_zone",
            "floor_id": floor_id,
            "floor_name": floor_name,
            "lot_id": action_result.get("lot_id", wizard.get("lot_id", "")),
            "zones": zones,
        }

        return {
            "response": text,
            "intent": "book_slot",
            "entities": {"vehicle_type": wizard.get("vehicle_type", "")},
            "suggestions": [z.get("name", "") for z in zones] + ["Hủy"],
            "data": action_result,
            "confidence": 1.0,
            "clarificationNeeded": False,
            "confirmationNeeded": False,
            "booking_wizard": new_wizard,
        }

    async def _wizard_select_zone(
        self, msg: str, wizard: Dict, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Process zone selection in booking wizard.

        Matches user input against available zones, then creates booking.
        """
        zones = wizard.get("zones", [])
        matched_zone = self.match_zone(msg, zones)

        if not matched_zone:
            zone_names = ", ".join(z.get("name", "") for z in zones)
            return {
                "response": f"Tôi chưa nhận ra khu vực bạn chọn. Các khu vực: {zone_names}. Bạn muốn chọn khu vực nào?",
                "intent": "book_slot",
                "entities": {"vehicle_type": wizard.get("vehicle_type", "")},
                "suggestions": [z.get("name", "") for z in zones] + ["Hủy"],
                "data": {},
                "confidence": 1.0,
                "clarificationNeeded": False,
                "confirmationNeeded": False,
                "booking_wizard": wizard,  # Keep wizard active
            }

        # Zone matched — create booking immediately
        zone_id = str(matched_zone.get("id", ""))
        result = await self.action_svc.book_slot_select_zone(
            user_id,
            wizard,
            zone_id,
        )

        if result.get("status") == "error":
            return {
                "response": f"⚠️ {result.get('error', 'Lỗi')}",
                "intent": "book_slot",
                "entities": {"vehicle_type": wizard.get("vehicle_type", "")},
                "suggestions": [z.get("name", "") for z in zones] + ["Hủy"],
                "data": {},
                "confidence": 1.0,
                "clarificationNeeded": False,
                "confirmationNeeded": False,
                "booking_wizard": wizard,  # Keep wizard
            }

        # Booking created! Format result
        decision = IntentDecision(
            primary_intent="book_slot",
            entities={"vehicle_type": wizard.get("vehicle_type", "")},
            missing_entities=[],
            llm_confidence=1.0,
            entity_completeness=1.0,
            context_match_score=1.0,
            hybrid_confidence=1.0,
            clarification_needed=False,
            reasoning="wizard_booking",
        )
        response = await self.response_svc.generate_response(decision, result, {})
        response["booking_wizard"] = None  # Clear wizard on success
        return response

    @staticmethod
    def match_floor(msg: str, floors: list[dict]) -> Optional[dict]:
        """Match user message to a floor.

        Handles patterns:
            - "Tầng 1", "tầng 1", "tang 1"
            - "B1", "b1"
            - Just the number "1", "2", "3"
            - Floor name directly "Tầng 3"

        Args:
            msg: Normalized lowercase user message.
            floors: List of floor dicts with name, level fields.

        Returns:
            Matched floor dict or None.
        """
        # Normalize common no-accent patterns
        normalized = msg.replace("tang", "tầng").strip()

        for floor in floors:
            name = (floor.get("name", "") or "").lower()
            level = floor.get("level", 0)

            # Exact name match
            if name and name in normalized:
                return floor

            # "tầng X" where X matches level
            match = re.search(r"tầng\s*(-?\d+)", normalized)
            if match and int(match.group(1)) == level:
                return floor

            # Just the number
            if normalized.strip().lstrip("-").isdigit():
                if int(normalized.strip()) == level:
                    return floor

        # Try ordinal match: "1" → first floor, "2" → second floor
        if normalized.strip().isdigit():
            idx = int(normalized.strip()) - 1
            if 0 <= idx < len(floors):
                return floors[idx]

        return None

    @staticmethod
    def match_zone(msg: str, zones: list[dict]) -> Optional[dict]:
        """Match user message to a zone.

        Handles patterns:
            - "Zone A", "zone a", "Zone B"
            - "A", "B" (single letter)
            - "V1", "V2" (zone code)
            - "1", "2" (ordinal selection)

        Args:
            msg: Normalized lowercase user message.
            zones: List of zone dicts with name field.

        Returns:
            Matched zone dict or None.
        """
        normalized = msg.strip().lower()

        for zone in zones:
            name = (zone.get("name", "") or "").lower()

            # Exact or contains match
            if name and name in normalized:
                return zone

            # "zone X" pattern
            match = re.search(r"zone\s+(\w+)", normalized)
            if match and f"zone {match.group(1)}" == name:
                return zone

            # Single letter match to zone name
            if len(normalized) <= 2 and name.endswith(normalized):
                return zone

        # Ordinal: "1" → first zone, "2" → second zone
        if normalized.isdigit():
            idx = int(normalized) - 1
            if 0 <= idx < len(zones):
                return zones[idx]

        return None

    @staticmethod
    def is_confirmation(message: str) -> Optional[bool]:
        """Check if the message is a yes/no response to a confirmation prompt.

        Returns:
            True if user confirms, False if user cancels, None if ambiguous.
        """
        msg = message.strip().lower()
        yes_words = [
            "xác nhận",
            "xac nhan",
            "đồng ý",
            "dong y",
            "ok",
            "có",
            "co",
            "yes",
            "ừ",
            "uh",
            "đúng",
            "dung",
            "confirm",
            "chắc chắn",
            "chac chan",
            "được",
            "duoc",
            "oke",
            "yep",
            "yeah",
        ]
        no_words = [
            "hủy",
            "huy",
            "hủy bỏ",
            "huy bo",
            "không",
            "khong",
            "no",
            "cancel",
            "thôi",
            "thoi",
            "bỏ",
            "bo",
            "dừng",
            "dung lai",
        ]

        for word in yes_words:
            if word in msg:
                return True
        for word in no_words:
            if word in msg:
                return False
        return None
