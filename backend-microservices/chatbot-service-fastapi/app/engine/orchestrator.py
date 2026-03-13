"""
Chatbot Orchestrator v3.0 — Full pipeline with 6 improvements.

🔥 2.1: IntentService tách 3 bước (classify → extract → build)
🔥 2.2: Hybrid Confidence (0.5*LLM + 0.3*entity + 0.2*context)
🔥 2.3: SafetyResult with reason code (not just bool)
🔥 2.4: Memory anti-noise (skip noisy updates)
🔥 2.5: Proactive cooldown + priority
🔥 2.6: AI Observability (intent_mismatch, clarification_rate, etc.)
🔥 3.0: Booking wizard — multi-step floor → zone → book

Pipeline: Wizard → Intent → Confidence Gate → Safety → Action → Response → Memory
"""

import logging
import re
import time
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.application.dto import IntentDecision, PipelineContext
from app.application.services.intent_service import IntentService
from app.application.services.safety_service import SafetyService
from app.application.services.action_service import ActionService
from app.application.services.response_service import ResponseService
from app.application.services.memory_service import MemoryService
from app.application.services.observability_service import AIMetricsCollector
from app.domain.value_objects.intent import Intent
from app.domain.value_objects.confidence import ConfidenceGate
from app.domain.policies.handoff import should_handoff
from app.domain.value_objects.ai_metrics import AIMetricType

logger = logging.getLogger(__name__)


class ChatbotOrchestrator:
    """
    v3.0 Orchestrator — full 5-stage pipeline with 6 improvements.

    Public API:
        process_message(message, conversation_context) → dict
    """

    def __init__(
        self,
        user_id: str,
        db: Optional[Session] = None,
        llm_client=None,
        service_client=None,
    ):
        self.user_id = user_id
        self.db = db

        # Service injection — all accept None for graceful degradation
        self.intent_svc = IntentService(llm_client=llm_client)
        self.safety_svc = SafetyService(service_client=service_client)
        self.action_svc = ActionService(service_client=service_client)
        self.response_svc = ResponseService(llm_client=llm_client)
        self.memory_svc = MemoryService(db, user_id) if db else None
        self.metrics = AIMetricsCollector(db=db)  # 🔥 2.6

    async def process_message(
        self, message: str, conversation_context: Dict = None
    ) -> Dict[str, Any]:
        """
        Main pipeline: Intent → Gate → Safety → Action → Response → Memory.
        Integrates all 6 improvements.
        """
        start_time = time.time()
        context = conversation_context or {}
        conversation_id = context.get("conversationId", "")

        try:
            # ─── Booking Wizard Handling (🔥 3.0) ───
            # If a multi-step booking wizard is active, handle the user's
            # selection (floor/zone) before doing intent classification.
            wizard_result = await self._try_booking_wizard(message, context)
            if wizard_result is not None:
                elapsed = int((time.time() - start_time) * 1000)
                wizard_result["processingTimeMs"] = elapsed
                return wizard_result

            # ─── Confirmation Handling ───
            # If the previous turn asked for confirmation, check for yes/no answer
            if context.get("lastGateAction") == "confirm":
                confirmed = self._is_confirmation(message)
                if confirmed is True:
                    # User confirmed — execute the previous intent directly
                    last_intent = context.get("lastIntent", "unknown")
                    last_entities = context.get("lastEntities", {})
                    last_confidence = context.get("lastConfidence", 0.9)

                    decision = IntentDecision(
                        primary_intent=last_intent,
                        entities=last_entities,
                        missing_entities=[],
                        llm_confidence=last_confidence,
                        entity_completeness=1.0,
                        context_match_score=1.0,
                        hybrid_confidence=last_confidence,
                        clarification_needed=False,
                        reasoning="user_confirmed",
                    )

                    # Skip gate, go straight to safety → action → response
                    safety_result = await self.safety_svc.validate(decision, self.user_id)
                    if not safety_result.ok:
                        elapsed = int((time.time() - start_time) * 1000)
                        resp = await self.response_svc.generate_safety_error(
                            decision,
                            safety_code=safety_result.code.value,
                            safety_hint=safety_result.hint,
                        )
                        resp["processingTimeMs"] = elapsed
                        resp["safetyCode"] = safety_result.code.value
                        resp["safetyHint"] = safety_result.hint
                        return resp

                    action_result = await self.action_svc.execute(self.user_id, decision)
                    user_style = self.memory_svc.get_style() if self.memory_svc else {}
                    response = await self.response_svc.generate_response(
                        decision, action_result, user_style
                    )
                    elapsed = int((time.time() - start_time) * 1000)
                    response["processingTimeMs"] = elapsed
                    response["confidenceBreakdown"] = self._confidence_breakdown(decision)

                    if self.memory_svc:
                        await self.memory_svc.update_after_action(
                            intent=decision.primary_intent,
                            action_result=action_result,
                            conversation_turns=context.get("totalTurns", 0),
                        )
                    return response

                elif confirmed is False:
                    # User cancelled
                    elapsed = int((time.time() - start_time) * 1000)
                    return {
                        "response": "Đã hủy bỏ. Bạn cần tôi giúp gì khác không?",
                        "intent": "cancelled",
                        "entities": {},
                        "suggestions": ["Xem chỗ trống", "Đặt chỗ", "Xem booking", "Trợ giúp"],
                        "data": {},
                        "confidence": 1.0,
                        "processingTimeMs": elapsed,
                        "clarificationNeeded": False,
                        "confirmationNeeded": False,
                    }
                # If neither yes nor no, fall through to normal pipeline

            # ─── Stage 1: Intent Detection (🔥 2.1 + 2.2) ───
            user_style = self.memory_svc.get_style() if self.memory_svc else {}
            decision = await self.intent_svc.detect(message, context, user_style)

            # 🔥 2.6: Check for intent mismatch (user correcting previous intent)
            last_intent = context.get("lastIntent")
            if last_intent and last_intent != decision.primary_intent:
                # If user was asked to clarify and now gives different intent → mismatch
                if context.get("lastGateAction") == "clarify":
                    await self.metrics.record_intent_mismatch(
                        user_id=self.user_id,
                        conversation_id=conversation_id,
                        old_intent=last_intent,
                        new_intent=decision.primary_intent,
                    )

            # ─── Handoff Check ───
            frustration = user_style.get("frustration_score", 0.0) if user_style else 0.0
            clarification_count = context.get("clarificationCount", 0)
            if should_handoff(frustration, clarification_count, message):
                elapsed = int((time.time() - start_time) * 1000)
                await self.metrics.record(
                    AIMetricType.HANDOFF_REQUESTED,
                    user_id=self.user_id,
                    conversation_id=conversation_id,
                    intent=decision.primary_intent,
                    confidence=decision.hybrid_confidence,
                )
                resp = await self.response_svc.generate_handoff()
                resp["processingTimeMs"] = elapsed
                return resp

            # ─── Stage 2: Confidence Gate (🔥 2.2) ───
            try:
                intent_enum = Intent(decision.primary_intent)
                high_stakes = intent_enum.is_high_stakes
            except ValueError:
                high_stakes = False

            gate_action = ConfidenceGate.evaluate(
                decision.hybrid_confidence, high_stakes
            )

            if gate_action == "clarify":
                elapsed = int((time.time() - start_time) * 1000)
                # 🔥 2.6: Record clarification metric
                await self.metrics.record_pipeline_outcome(
                    user_id=self.user_id,
                    conversation_id=conversation_id,
                    intent=decision.primary_intent,
                    hybrid_confidence=decision.hybrid_confidence,
                    llm_confidence=decision.llm_confidence,
                    entity_completeness=decision.entity_completeness,
                    context_match=decision.context_match_score,
                    gate_action="clarify",
                    processing_time_ms=elapsed,
                )
                resp = await self.response_svc.generate_clarification(decision)
                resp["processingTimeMs"] = elapsed
                resp["confidenceBreakdown"] = self._confidence_breakdown(decision)
                return resp

            if gate_action == "confirm":
                elapsed = int((time.time() - start_time) * 1000)
                await self.metrics.record_pipeline_outcome(
                    user_id=self.user_id,
                    conversation_id=conversation_id,
                    intent=decision.primary_intent,
                    hybrid_confidence=decision.hybrid_confidence,
                    llm_confidence=decision.llm_confidence,
                    entity_completeness=decision.entity_completeness,
                    context_match=decision.context_match_score,
                    gate_action="confirm",
                    processing_time_ms=elapsed,
                )
                resp = await self.response_svc.generate_confirmation(decision)
                resp["processingTimeMs"] = elapsed
                resp["confidenceBreakdown"] = self._confidence_breakdown(decision)
                return resp

            # ─── Stage 3: Safety Rules (🔥 2.3) ───
            safety_result = await self.safety_svc.validate(decision, self.user_id)

            if not safety_result.ok:
                elapsed = int((time.time() - start_time) * 1000)
                await self.metrics.record_pipeline_outcome(
                    user_id=self.user_id,
                    conversation_id=conversation_id,
                    intent=decision.primary_intent,
                    hybrid_confidence=decision.hybrid_confidence,
                    llm_confidence=decision.llm_confidence,
                    entity_completeness=decision.entity_completeness,
                    context_match=decision.context_match_score,
                    gate_action="execute",
                    safety_code=safety_result.code.value,
                    processing_time_ms=elapsed,
                )
                resp = await self.response_svc.generate_safety_error(
                    decision,
                    safety_code=safety_result.code.value,
                    safety_hint=safety_result.hint,
                )
                resp["processingTimeMs"] = elapsed
                resp["safetyCode"] = safety_result.code.value
                resp["safetyHint"] = safety_result.hint
                return resp

            # ─── Stage 4: Execute Action ───
            action_result = await self.action_svc.execute(self.user_id, decision)

            # ─── Stage 5: Generate Response ───
            response = await self.response_svc.generate_response(
                decision, action_result, user_style
            )

            elapsed = int((time.time() - start_time) * 1000)
            response["processingTimeMs"] = elapsed
            response["confidenceBreakdown"] = self._confidence_breakdown(decision)

            # 🔥 3.0: If action returned wizard step, pass it through for context storage
            wizard_step = action_result.get("wizard_step")
            if wizard_step:
                response["booking_wizard"] = {
                    "step": wizard_step,
                    "vehicle_type": action_result.get("vehicle_type", ""),
                    "vehicle_type_db": action_result.get("vehicle_type_db", ""),
                    "floors": action_result.get("floors", []),
                    "floor_id": action_result.get("floor_id", ""),
                    "floor_name": action_result.get("floor_name", ""),
                    "lot_id": action_result.get("lot_id", ""),
                    "zones": action_result.get("zones", []),
                }
            elif context.get("_wizard_cancelled"):
                # Wizard was cancelled via intent-switch fallthrough
                # Ensure DB context is cleared
                response["booking_wizard"] = None

            # 🔥 2.6: Record full pipeline outcome
            await self.metrics.record_pipeline_outcome(
                user_id=self.user_id,
                conversation_id=conversation_id,
                intent=decision.primary_intent,
                hybrid_confidence=decision.hybrid_confidence,
                llm_confidence=decision.llm_confidence,
                entity_completeness=decision.entity_completeness,
                context_match=decision.context_match_score,
                gate_action="execute",
                action_status=action_result.get("status", ""),
                processing_time_ms=elapsed,
            )

            # ─── Stage 6: Memory Update (🔥 2.4 anti-noise) ───
            if self.memory_svc:
                conversation_turns = context.get("totalTurns", 0)
                await self.memory_svc.update_after_action(
                    intent=decision.primary_intent,
                    action_result=action_result,
                    conversation_turns=conversation_turns,
                )

            return response

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            elapsed = int((time.time() - start_time) * 1000)
            return {
                "response": "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.",
                "intent": "error",
                "entities": {},
                "suggestions": ["Thử lại", "Trợ giúp"],
                "data": {},
                "confidence": 0.0,
                "processingTimeMs": elapsed,
                "clarificationNeeded": False,
                "confirmationNeeded": False,
            }

    @staticmethod
    def _confidence_breakdown(decision: IntentDecision) -> Dict[str, float]:
        """
        🔥 2.2: Expose confidence components for debugging & FE display.
        """
        return {
            "hybrid": decision.hybrid_confidence,
            "llm": decision.llm_confidence,
            "entityCompleteness": decision.entity_completeness,
            "contextMatch": decision.context_match_score,
        }

    # ─── Booking Wizard (🔥 3.0) ─────────────────────────

    async def _try_booking_wizard(
        self, message: str, context: Dict
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
        if self._is_confirmation(msg) is False:
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
        intent_svc = self.intent_svc
        intent_check = intent_svc._keyword_classify(msg)
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
            return await self._wizard_select_floor(msg, wizard)

        if step == "select_zone":
            return await self._wizard_select_zone(msg, wizard)

        # Unknown wizard step — clear and fall through
        return None

    async def _wizard_select_floor(
        self, msg: str, wizard: Dict
    ) -> Optional[Dict[str, Any]]:
        """Process floor selection in booking wizard.

        Matches user input against available floor names/levels.
        """
        floors = wizard.get("floors", [])
        matched_floor = self._match_floor(msg, floors)

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
            self.user_id, wizard, floor_id,
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
        text += "\n💡 Hãy chọn khu vực (ví dụ: \"Zone A\" hoặc \"1\")"

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
        self, msg: str, wizard: Dict
    ) -> Optional[Dict[str, Any]]:
        """Process zone selection in booking wizard.

        Matches user input against available zones, then creates booking.
        """
        zones = wizard.get("zones", [])
        matched_zone = self._match_zone(msg, zones)

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
            self.user_id, wizard, zone_id,
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
    def _match_floor(msg: str, floors: list[dict]) -> Optional[dict]:
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
            match = re.search(r'tầng\s*(-?\d+)', normalized)
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
    def _match_zone(msg: str, zones: list[dict]) -> Optional[dict]:
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
            match = re.search(r'zone\s+(\w+)', normalized)
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
    def _is_confirmation(message: str) -> Optional[bool]:
        """Check if the message is a yes/no response to a confirmation prompt.

        Returns:
            True if user confirms, False if user cancels, None if ambiguous.
        """
        msg = message.strip().lower()
        yes_words = [
            "xác nhận", "xac nhan", "đồng ý", "dong y", "ok", "có", "co",
            "yes", "ừ", "uh", "đúng", "dung", "confirm", "chắc chắn",
            "chac chan", "được", "duoc", "oke", "yep", "yeah",
        ]
        no_words = [
            "hủy", "huy", "hủy bỏ", "huy bo", "không", "khong", "no",
            "cancel", "thôi", "thoi", "bỏ", "bo", "dừng", "dung lai",
        ]

        for word in yes_words:
            if word in msg:
                return True
        for word in no_words:
            if word in msg:
                return False
        return None
