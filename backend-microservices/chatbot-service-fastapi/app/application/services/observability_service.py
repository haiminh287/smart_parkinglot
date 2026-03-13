"""
🔥 CẢI TIẾN 2.6: AI Observability Service — log AI-specific metrics.

Tracks:
- intent_mismatch_rate → phát hiện prompt hỏng
- clarification_rate → prompt quá mơ hồ
- confirmation_rate → confidence chưa tốt
- action_fail_after_execute → logic domain sai
- user_override_rate → chatbot đoán sai
- memory_update_skipped → anti-noise triggered
- proactive_suppressed → cooldown triggered

Không có mấy metric này = AI mù.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.domain.value_objects.ai_metrics import AIMetricType

logger = logging.getLogger(__name__)


class AIMetricsCollector:
    """
    Collects and stores AI-specific metrics for observability.

    Logs to both structured logging AND database for analytics dashboard.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    async def record(
        self,
        metric_type: AIMetricType,
        user_id: str = "",
        conversation_id: str = "",
        intent: str = "",
        confidence: float = 0.0,
        **extra: Any,
    ) -> None:
        """
        Record an AI metric event.

        Args:
            metric_type: Type of metric event.
            user_id: User who triggered the event.
            conversation_id: Active conversation.
            intent: Related intent.
            confidence: Confidence score at time of event.
            **extra: Additional context data.
        """
        # 1. Structured logging (always available, even without DB)
        logger.info(
            f"AI_METRIC | type={metric_type.value} | user={user_id} | "
            f"conv={conversation_id} | intent={intent} | conf={confidence:.4f} | "
            f"extra={extra}"
        )

        # 2. Database persistence (for analytics dashboard)
        if self.db:
            try:
                from app.models.chatbot import AIMetricLog
                metric = AIMetricLog(
                    id=str(uuid.uuid4()),
                    metric_type=metric_type.value,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    intent=intent,
                    confidence=confidence,
                    extra_data=extra or {},
                    created_at=datetime.utcnow(),
                )
                self.db.add(metric)
                # Don't commit here — let the caller's transaction handle it
            except ImportError:
                pass  # AIMetricLog model not yet created
            except Exception as e:
                logger.warning(f"Failed to persist AI metric: {e}")

    async def record_pipeline_outcome(
        self,
        user_id: str,
        conversation_id: str,
        intent: str,
        hybrid_confidence: float,
        llm_confidence: float,
        entity_completeness: float,
        context_match: float,
        gate_action: str,
        safety_code: str = "OK",
        action_status: str = "",
        processing_time_ms: int = 0,
    ) -> None:
        """
        Record a complete pipeline execution for analysis.

        This is the main metric — tracks the entire request lifecycle.
        """
        # Determine outcome metric type
        if gate_action == "clarify":
            await self.record(
                AIMetricType.CLARIFICATION_TRIGGERED,
                user_id=user_id,
                conversation_id=conversation_id,
                intent=intent,
                confidence=hybrid_confidence,
                llm_confidence=llm_confidence,
                entity_completeness=entity_completeness,
                context_match=context_match,
            )
        elif gate_action == "confirm":
            await self.record(
                AIMetricType.CONFIRMATION_TRIGGERED,
                user_id=user_id,
                conversation_id=conversation_id,
                intent=intent,
                confidence=hybrid_confidence,
            )
        elif safety_code != "OK":
            await self.record(
                AIMetricType.SAFETY_BLOCKED,
                user_id=user_id,
                conversation_id=conversation_id,
                intent=intent,
                confidence=hybrid_confidence,
                safety_code=safety_code,
            )
        elif action_status == "error":
            await self.record(
                AIMetricType.ACTION_FAIL_AFTER_EXECUTE,
                user_id=user_id,
                conversation_id=conversation_id,
                intent=intent,
                confidence=hybrid_confidence,
            )
        else:
            await self.record(
                AIMetricType.ACTION_SUCCESS,
                user_id=user_id,
                conversation_id=conversation_id,
                intent=intent,
                confidence=hybrid_confidence,
                processing_time_ms=processing_time_ms,
            )

        # Always record confidence vs outcome for calibration
        await self.record(
            AIMetricType.CONFIDENCE_VS_OUTCOME,
            user_id=user_id,
            conversation_id=conversation_id,
            intent=intent,
            confidence=hybrid_confidence,
            was_correct=action_status not in ("error", ""),
            llm_confidence=llm_confidence,
            entity_completeness=entity_completeness,
            context_match=context_match,
        )

    async def record_intent_mismatch(
        self,
        user_id: str,
        conversation_id: str,
        old_intent: str,
        new_intent: str,
    ) -> None:
        """
        Record when user re-asks → indicates previous intent was wrong.
        Called when the same user sends consecutive messages that change intent.
        """
        await self.record(
            AIMetricType.INTENT_MISMATCH,
            user_id=user_id,
            conversation_id=conversation_id,
            intent=new_intent,
            old_intent=old_intent,
        )
