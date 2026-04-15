"""
Response Service — generates personalized responses via LLM.
Uses user style profile for tone/emoji/format personalization.
"""

import logging
from typing import Any, Optional

from app.application.dto import IntentDecision
from app.application.services.response_formatters import (
    build_rich_response,
    build_smart_clarification,
    get_action_suggestions,
    get_clarification_suggestions,
    get_safety_suggestions,
)

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
        question = build_smart_clarification(intent, missing, decision.entities)

        return {
            "response": question,
            "intent": intent,
            "entities": decision.entities,
            "suggestions": get_clarification_suggestions(decision),
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
            "suggestions": get_safety_suggestions(safety_code),
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
            "suggestions": get_action_suggestions(decision.primary_intent),
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
            text = build_rich_response(intent, entities, action_result)

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
            suggestions = get_action_suggestions(intent)

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
