"""
🔥 CẢI TIẾN 2.4: Memory Service — anti-noise rules.

Không phải hành động nào cũng nên update behavior:
- booking < 5 phút rồi hủy → KHÔNG update
- cancel do system → KHÔNG tính cancel_rate  
- conversation chưa hoàn tất → KHÔNG học

Nếu không, chatbot sẽ học sai người dùng.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.chatbot import (
    UserPreferences, UserBehavior, UserCommunicationStyle
)
from app.domain.value_objects.ai_metrics import AIMetricType

logger = logging.getLogger(__name__)

# Anti-noise thresholds
MIN_BOOKING_DURATION_MINUTES = 5  # Booking must last > 5 min to learn from
MIN_CONVERSATION_TURNS = 2         # Need >= 2 turns to consider "complete"


class MemoryService:
    """Updates long-term user behavior and preferences with anti-noise rules."""

    def __init__(self, db: Session, user_id: str, metrics_collector=None):
        self.db = db
        self.user_id = user_id
        self.metrics_collector = metrics_collector

    def get_style(self) -> dict[str, Any]:
        """Load user communication style for response personalization."""
        style = (
            self.db.query(UserCommunicationStyle)
            .filter(UserCommunicationStyle.user_id == self.user_id)
            .first()
        )
        if not style:
            return {
                "prefers_short": True,
                "emoji_level": 1,
                "formality": "casual",
                "primary_language": "vi",
            }
        return {
            "prefers_short": style.prefers_short,
            "emoji_level": style.emoji_level,
            "formality": style.formality,
            "primary_language": style.primary_language,
            "frustration_score": style.frustration_score,
        }

    async def update_after_action(
        self,
        intent: str,
        action_result: dict[str, Any],
        conversation_turns: int,
        action_timestamp: Optional[datetime] = None,
    ) -> None:
        """
        🔥 2.4: Update behavior only if action passes anti-noise checks.
        """
        if not self._should_update(intent, action_result, conversation_turns):
            logger.info(
                f"Memory update SKIPPED for user={self.user_id}, intent={intent} "
                f"(anti-noise rule)"
            )
            if self.metrics_collector:
                await self.metrics_collector.record(
                    AIMetricType.MEMORY_UPDATE_SKIPPED,
                    user_id=self.user_id,
                    intent=intent,
                    reason="anti_noise_rule",
                )
            return

        try:
            self._update_behavior(intent, action_result)
            self._update_preferences(intent, action_result)
            self.db.commit()
            logger.info(f"Memory updated for user={self.user_id}, intent={intent}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Memory update failed: {e}")

    def _should_update(
        self,
        intent: str,
        action_result: dict[str, Any],
        conversation_turns: int,
    ) -> bool:
        """
        🔥 2.4: Anti-noise rules — filter out noisy data.

        Returns False if the action should NOT be used for learning.
        """
        # Rule 1: Conversation must have >= 2 turns (not accidental)
        if conversation_turns < MIN_CONVERSATION_TURNS:
            logger.debug("Anti-noise: conversation too short")
            return False

        # Rule 2: Action must have succeeded
        if action_result.get("status") == "error":
            logger.debug("Anti-noise: action failed")
            return False

        # Rule 3: Cancel booking — check if booking was < 5 minutes old
        if intent == "cancel_booking":
            booking_created_at = action_result.get("booking_created_at")
            if booking_created_at:
                try:
                    created = datetime.fromisoformat(str(booking_created_at))
                    if datetime.utcnow() - created < timedelta(minutes=MIN_BOOKING_DURATION_MINUTES):
                        logger.debug("Anti-noise: booking cancelled within 5 min")
                        return False
                except (ValueError, TypeError):
                    pass

            # Rule 4: System-initiated cancel → don't count
            cancel_source = action_result.get("cancel_source", "user")
            if cancel_source != "user":
                logger.debug(f"Anti-noise: cancel by {cancel_source}, not user")
                return False

        return True

    def _update_behavior(self, intent: str, action_result: dict[str, Any]) -> None:
        """Update UserBehavior with new data point."""
        behavior = (
            self.db.query(UserBehavior)
            .filter(UserBehavior.user_id == self.user_id)
            .first()
        )
        if not behavior:
            behavior = UserBehavior(user_id=self.user_id)
            self.db.add(behavior)
            self.db.flush()

        behavior.data_points = (behavior.data_points or 0) + 1
        n = behavior.data_points

        # Update cancel rate (weighted rolling average)
        if intent == "cancel_booking":
            old_rate = behavior.cancel_rate or 0.0
            behavior.cancel_rate = round(old_rate + (1.0 - old_rate) / n, 4)
        elif intent == "book_slot":
            old_rate = behavior.cancel_rate or 0.0
            behavior.cancel_rate = round(old_rate + (0.0 - old_rate) / n, 4)

        # Update confidence score (more data → more confident about profile)
        behavior.confidence_score = round(min(n / 20.0, 1.0), 4)

        behavior.updated_at = datetime.utcnow()

    def _update_preferences(self, intent: str, action_result: dict[str, Any]) -> None:
        """Update UserPreferences after successful booking."""
        if intent != "book_slot":
            return

        prefs = (
            self.db.query(UserPreferences)
            .filter(UserPreferences.user_id == self.user_id)
            .first()
        )
        if not prefs:
            prefs = UserPreferences(user_id=self.user_id)
            self.db.add(prefs)
            self.db.flush()

        prefs.total_bookings = (prefs.total_bookings or 0) + 1

        # Update last booked slot info
        slot_data = action_result.get("slot")
        if slot_data:
            prefs.last_booked_slot = slot_data

        # Update favorite lot (most recent)
        lot_id = action_result.get("lot_id")
        if lot_id:
            prefs.favorite_lot_id = lot_id

        prefs.updated_at = datetime.utcnow()
