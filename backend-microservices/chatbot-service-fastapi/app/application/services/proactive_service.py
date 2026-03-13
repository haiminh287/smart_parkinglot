"""
🔥 CẢI TIẾN 2.5: Proactive Service — cooldown + priority + suppression.

Event-driven chatbot rất dễ spam user. Cải tiến:
- priority (HIGH / MEDIUM / LOW)
- cooldown window (per user, per event_type)
- suppression rules (nếu user vừa active)
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.chatbot import ProactiveNotification, Conversation
from app.domain.value_objects.proactive import (
    NotificationPriority, CooldownConfig,
)
from app.domain.value_objects.ai_metrics import AIMetricType

logger = logging.getLogger(__name__)


class ProactiveService:
    """Handles proactive notifications with anti-spam controls."""

    def __init__(
        self,
        db: Session,
        cooldown_config: Optional[CooldownConfig] = None,
        metrics_collector=None,
    ):
        self.db = db
        self.cooldown = cooldown_config or CooldownConfig()
        self.metrics_collector = metrics_collector

    async def handle_event(
        self,
        event_type: str,
        user_id: str,
        event_data: dict[str, Any],
    ) -> Optional[str]:
        """
        Process an incoming event and optionally create a notification.

        Returns notification_id if created, None if suppressed.
        """
        # Determine priority
        priority = self._get_priority(event_type)

        # 🔥 2.5: Check cooldown
        if self._is_in_cooldown(user_id, event_type, priority):
            logger.info(
                f"Proactive SUPPRESSED: cooldown for user={user_id}, "
                f"event={event_type}, priority={priority.value}"
            )
            if self.metrics_collector:
                await self.metrics_collector.record(
                    AIMetricType.PROACTIVE_SUPPRESSED,
                    user_id=user_id,
                    event_type=event_type,
                    reason="cooldown",
                )
            return None

        # 🔥 2.5: Check user active suppression
        if priority != NotificationPriority.HIGH and self._is_user_active(user_id):
            logger.info(
                f"Proactive SUPPRESSED: user active for user={user_id}, "
                f"event={event_type}"
            )
            if self.metrics_collector:
                await self.metrics_collector.record(
                    AIMetricType.PROACTIVE_SUPPRESSED,
                    user_id=user_id,
                    event_type=event_type,
                    reason="user_active",
                )
            return None

        # 🔥 2.5: Check max per hour
        if self._exceeds_hourly_limit(user_id):
            logger.info(
                f"Proactive SUPPRESSED: hourly limit for user={user_id}"
            )
            if self.metrics_collector:
                await self.metrics_collector.record(
                    AIMetricType.PROACTIVE_SUPPRESSED,
                    user_id=user_id,
                    event_type=event_type,
                    reason="hourly_limit",
                )
            return None

        # Build and save notification
        title, message, actions = self._build_notification(event_type, event_data)

        notification = ProactiveNotification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type=event_type,
            status="pending",
            title=title,
            message=message,
            event_data={
                **event_data,
                "priority": priority.value,  # 🔥 2.5: Store priority
            },
            suggested_actions=actions,
            trigger_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        self.db.add(notification)
        self.db.commit()

        logger.info(
            f"Proactive notification created: {notification.id} "
            f"for user={user_id}, event={event_type}, priority={priority.value}"
        )
        return notification.id

    def _get_priority(self, event_type: str) -> NotificationPriority:
        """Map event type to priority level."""
        high_events = {"slot.maintenance", "booking.expired", "booking.conflict"}
        medium_events = {"booking.no_checkin", "booking.expiring_soon"}
        # Everything else is LOW

        if event_type in high_events:
            return NotificationPriority.HIGH
        if event_type in medium_events:
            return NotificationPriority.MEDIUM
        return NotificationPriority.LOW

    def _is_in_cooldown(
        self, user_id: str, event_type: str, priority: NotificationPriority
    ) -> bool:
        """
        🔥 2.5: Check if we recently sent same event_type to this user.
        """
        cooldown_minutes = self.cooldown.get_cooldown(priority)
        since = datetime.utcnow() - timedelta(minutes=cooldown_minutes)

        recent = (
            self.db.query(ProactiveNotification)
            .filter(
                ProactiveNotification.user_id == user_id,
                ProactiveNotification.event_type == event_type,
                ProactiveNotification.created_at >= since,
            )
            .first()
        )
        return recent is not None

    def _is_user_active(self, user_id: str) -> bool:
        """
        🔥 2.5: Suppress non-HIGH notifications if user had activity recently.
        Don't interrupt an active conversation.
        """
        since = datetime.utcnow() - timedelta(
            minutes=self.cooldown.USER_ACTIVE_SUPPRESS_MINUTES
        )
        recent_conversation = (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user_id,
                Conversation.updated_at >= since,
            )
            .first()
        )
        return recent_conversation is not None

    def _exceeds_hourly_limit(self, user_id: str) -> bool:
        """🔥 2.5: Max notifications per user per hour."""
        since = datetime.utcnow() - timedelta(hours=1)
        count = (
            self.db.query(ProactiveNotification)
            .filter(
                ProactiveNotification.user_id == user_id,
                ProactiveNotification.created_at >= since,
            )
            .count()
        )
        return count >= self.cooldown.MAX_PER_HOUR

    def _build_notification(
        self, event_type: str, event_data: dict[str, Any]
    ) -> tuple[str, str, list[str]]:
        """Build notification content from event."""
        builders = {
            "booking.expiring_soon": self._build_expiring,
            "booking.no_checkin": self._build_no_checkin,
            "slot.maintenance": self._build_maintenance,
            "slot.conflict": self._build_conflict,
            "weather.rain": self._build_weather,
        }

        builder = builders.get(event_type)
        if builder:
            return builder(event_data)

        return (
            "Thông báo",
            f"Bạn có thông báo mới: {event_type}",
            ["Xem chi tiết"],
        )

    @staticmethod
    def _build_expiring(data: dict) -> tuple[str, str, list[str]]:
        slot = data.get("slot_code", "N/A")
        minutes = data.get("minutes_left", 30)
        return (
            "⏰ Booking sắp hết hạn",
            f"Booking tại slot {slot} sẽ hết hạn trong {minutes} phút. Bạn muốn gia hạn không?",
            ["Gia hạn", "Đồng ý kết thúc"],
        )

    @staticmethod
    def _build_no_checkin(data: dict) -> tuple[str, str, list[str]]:
        slot = data.get("slot_code", "N/A")
        return (
            "📍 Nhắc nhở check-in",
            f"Bạn chưa check-in tại slot {slot}. Cần hỗ trợ không?",
            ["Check-in ngay", "Hủy booking"],
        )

    @staticmethod
    def _build_maintenance(data: dict) -> tuple[str, str, list[str]]:
        slot = data.get("slot_code", "N/A")
        alt_slot = data.get("alternative_slot", "")
        msg = f"⚠️ Slot {slot} đang bảo trì đột xuất."
        if alt_slot:
            msg += f" Đổi sang slot {alt_slot} nhé?"
        return (
            "🔧 Bảo trì slot",
            msg,
            ["Đổi slot", "Hủy booking"],
        )

    @staticmethod
    def _build_conflict(data: dict) -> tuple[str, str, list[str]]:
        slot = data.get("slot_code", "N/A")
        return (
            "⚠️ Xung đột slot",
            f"Có xung đột tại slot {slot}. Vui lòng chọn slot khác.",
            ["Xem slot trống", "Liên hệ hỗ trợ"],
        )

    @staticmethod
    def _build_weather(data: dict) -> tuple[str, str, list[str]]:
        slot = data.get("slot_code", "N/A")
        return (
            "🌧️ Cảnh báo thời tiết",
            f"Trời sắp mưa. Slot {slot} ở ngoài trời. Đổi vào trong nhà?",
            ["Đổi slot trong nhà", "Giữ nguyên"],
        )
