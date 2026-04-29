"""Chatbot Orchestrator v3.0 — Wizard → Intent → Gate → Safety → Action → Response → Memory."""

import logging
import time
from typing import Any, Dict, Optional

from app.application.dto import IntentDecision
from app.application.services.action_service import ActionService
from app.application.services.intent_service import IntentService
from app.application.services.memory_service import MemoryService
from app.application.services.observability_service import AIMetricsCollector
from app.application.services.response_service import ResponseService
from app.application.services.safety_service import SafetyService
from app.domain.policies.handoff import should_handoff
from app.domain.value_objects.ai_metrics import AIMetricType
from app.domain.value_objects.confidence import ConfidenceGate
from app.domain.value_objects.intent import Intent
from app.engine.booking_wizard import BookingWizard
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ChatbotOrchestrator:
    """v3.0 Orchestrator — 5-stage pipeline with booking wizard."""

    def __init__(
        self,
        user_id: str,
        db: Optional[Session] = None,
        llm_client=None,
        service_client=None,
    ):
        self.user_id = user_id
        self.db = db
        self.intent_svc = IntentService(llm_client=llm_client)
        self.safety_svc = SafetyService(service_client=service_client)
        self.action_svc = ActionService(service_client=service_client)
        self.response_svc = ResponseService(llm_client=llm_client)
        self.memory_svc = MemoryService(db, user_id) if db else None
        self.metrics = AIMetricsCollector(db=db)
        self.wizard = BookingWizard(
            action_svc=self.action_svc,
            response_svc=self.response_svc,
            intent_svc=self.intent_svc,
        )

    async def process_message(
        self, message: str, conversation_context: Dict = None
    ) -> Dict[str, Any]:
        """Main pipeline: Intent → Gate → Safety → Action → Response → Memory."""
        start_time = time.time()
        context = conversation_context or {}
        conversation_id = context.get("conversationId", "")

        try:
            wizard_result = await self.wizard.try_booking_wizard(
                message, context, self.user_id
            )
            if wizard_result is not None:
                elapsed = int((time.time() - start_time) * 1000)
                wizard_result["processingTimeMs"] = elapsed
                return wizard_result

            if context.get("lastGateAction") == "confirm":
                confirmed = BookingWizard.is_confirmation(message)
                if confirmed is True:
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

                    safety_result = await self.safety_svc.validate(
                        decision, self.user_id
                    )
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

                    action_result = await self.action_svc.execute(
                        self.user_id, decision, user_message=message
                    )
                    user_style = self.memory_svc.get_style() if self.memory_svc else {}
                    response = await self.response_svc.generate_response(
                        decision, action_result, user_style
                    )
                    elapsed = int((time.time() - start_time) * 1000)
                    response["processingTimeMs"] = elapsed
                    response["confidenceBreakdown"] = self._confidence_breakdown(
                        decision
                    )

                    if self.memory_svc:
                        await self.memory_svc.update_after_action(
                            intent=decision.primary_intent,
                            action_result=action_result,
                            conversation_turns=context.get("totalTurns", 0),
                        )
                    return response

                elif confirmed is False:
                    elapsed = int((time.time() - start_time) * 1000)
                    return {
                        "response": "Đã hủy bỏ. Bạn cần tôi giúp gì khác không?",
                        "intent": "cancelled",
                        "entities": {},
                        "suggestions": [
                            "Xem chỗ trống",
                            "Đặt chỗ",
                            "Xem booking",
                            "Trợ giúp",
                        ],
                        "data": {},
                        "confidence": 1.0,
                        "processingTimeMs": elapsed,
                        "clarificationNeeded": False,
                        "confirmationNeeded": False,
                    }
                # Fall through if neither yes nor no

            user_style = self.memory_svc.get_style() if self.memory_svc else {}
            decision = await self.intent_svc.detect(message, context, user_style)

            last_intent = context.get("lastIntent")
            if last_intent and last_intent != decision.primary_intent:
                if context.get("lastGateAction") == "clarify":
                    await self.metrics.record_intent_mismatch(
                        user_id=self.user_id,
                        conversation_id=conversation_id,
                        old_intent=last_intent,
                        new_intent=decision.primary_intent,
                    )
            # ─── Handoff Check ───
            frustration = (
                user_style.get("frustration_score", 0.0) if user_style else 0.0
            )
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

            action_result = await self.action_svc.execute(self.user_id, decision, user_message=message)

            response = await self.response_svc.generate_response(
                decision, action_result, user_style
            )

            elapsed = int((time.time() - start_time) * 1000)
            response["processingTimeMs"] = elapsed
            response["confidenceBreakdown"] = self._confidence_breakdown(decision)

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
                response["booking_wizard"] = None

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
        """Expose confidence components for debugging & FE display."""
        return {
            "hybrid": decision.hybrid_confidence,
            "llm": decision.llm_confidence,
            "entityCompleteness": decision.entity_completeness,
            "contextMatch": decision.context_match_score,
        }
