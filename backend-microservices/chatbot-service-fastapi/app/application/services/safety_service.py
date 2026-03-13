"""
🔥 CẢI TIẾN 2.3: SafetyService — trả SafetyResult(ok, code, hint).

Không chỉ True/False. FE hiển thị reason, logging theo code, analytics aggregate.
"""

import logging
from typing import Any

from app.application.dto import IntentDecision
from app.domain.value_objects.intent import Intent
from app.domain.value_objects.safety_result import SafetyResult, SafetyCode

logger = logging.getLogger(__name__)


class SafetyService:
    """
    Non-LLM safety validation before action execution.
    Returns SafetyResult with machine-readable code + human hint.
    """

    def __init__(self, service_client=None):
        self.service_client = service_client

    async def validate(self, decision: IntentDecision, user_id: str) -> SafetyResult:
        """
        Dispatch validation based on intent type.
        Returns SafetyResult — ok=True if safe, ok=False with code+hint if blocked.
        """
        try:
            intent = Intent(decision.primary_intent)
        except ValueError:
            return SafetyResult.safe()

        validators = {
            Intent.BOOK_SLOT: self._validate_booking,
            Intent.CANCEL_BOOKING: self._validate_cancel,
            Intent.CHECK_IN: self._validate_check_in,
            Intent.CHECK_OUT: self._validate_check_out,
        }

        validator = validators.get(intent)
        if not validator:
            return SafetyResult.safe()

        return await validator(decision, user_id)

    async def _validate_booking(
        self, decision: IntentDecision, user_id: str
    ) -> SafetyResult:
        """Validate booking safety rules."""
        entities = decision.entities

        # Rule: Time range must be valid
        start_time = entities.get("start_time")
        end_time = entities.get("end_time")
        if start_time and end_time and start_time >= end_time:
            return SafetyResult.blocked(
                code=SafetyCode.INVALID_TIME_RANGE,
                hint="Thời gian bắt đầu phải trước thời gian kết thúc.",
                start_time=start_time,
                end_time=end_time,
            )

        # Rule: Check for double booking via service
        if self.service_client:
            try:
                existing = await self.service_client.get_active_bookings(user_id)
                if len(existing) >= 3:
                    return SafetyResult.blocked(
                        code=SafetyCode.MAX_BOOKINGS_REACHED,
                        hint="Bạn đã có tối đa 3 booking đang hoạt động.",
                        active_count=len(existing),
                    )

                # Check double booking for same time
                for booking in existing:
                    if self._time_overlap(
                        start_time, end_time,
                        booking.get("start_time"), booking.get("end_time"),
                    ):
                        return SafetyResult.blocked(
                            code=SafetyCode.DOUBLE_BOOKING,
                            hint="Bạn đã có booking trong khoảng thời gian này.",
                            existing_booking_id=booking.get("id"),
                        )
            except Exception as e:
                logger.warning(f"Could not check existing bookings: {e}")

        # Rule: Check slot availability
        slot_id = entities.get("slot_id")
        if slot_id and self.service_client:
            try:
                available = await self.service_client.check_slot_available(slot_id)
                if not available:
                    return SafetyResult.blocked(
                        code=SafetyCode.SLOT_NOT_AVAILABLE,
                        hint="Slot này hiện không còn trống.",
                        slot_id=slot_id,
                    )
            except Exception as e:
                logger.warning(f"Could not check slot availability: {e}")

        return SafetyResult.safe()

    async def _validate_cancel(
        self, decision: IntentDecision, user_id: str
    ) -> SafetyResult:
        """Validate cancel booking safety."""
        booking_id = decision.entities.get("booking_id")
        if not booking_id:
            return SafetyResult.safe()  # Will fail at action layer

        if self.service_client:
            try:
                booking = await self.service_client.get_booking(user_id, booking_id)
                if not booking:
                    return SafetyResult.blocked(
                        code=SafetyCode.BOOKING_NOT_FOUND,
                        hint="Không tìm thấy booking này.",
                        booking_id=booking_id,
                    )
                if booking.get("status") == "checked_in":
                    return SafetyResult.blocked(
                        code=SafetyCode.ALREADY_CHECKED_IN,
                        hint="Booking đã check-in, không thể hủy. Hãy check-out trước.",
                        booking_id=booking_id,
                    )
            except Exception as e:
                logger.warning(f"Could not validate cancel: {e}")

        return SafetyResult.safe()

    async def _validate_check_in(
        self, decision: IntentDecision, user_id: str
    ) -> SafetyResult:
        """Validate check-in safety."""
        booking_id = decision.entities.get("booking_id")
        if not booking_id or not self.service_client:
            return SafetyResult.safe()

        try:
            booking = await self.service_client.get_booking(user_id, booking_id)
            if not booking:
                return SafetyResult.blocked(
                    code=SafetyCode.BOOKING_NOT_FOUND,
                    hint="Không tìm thấy booking.",
                )
            if booking.get("status") == "checked_in":
                return SafetyResult.blocked(
                    code=SafetyCode.ALREADY_CHECKED_IN,
                    hint="Bạn đã check-in rồi.",
                )
            if booking.get("status") in ("expired", "cancelled"):
                return SafetyResult.blocked(
                    code=SafetyCode.BOOKING_EXPIRED,
                    hint="Booking đã hết hạn hoặc bị hủy.",
                )
        except Exception as e:
            logger.warning(f"Could not validate check-in: {e}")

        return SafetyResult.safe()

    async def _validate_check_out(
        self, decision: IntentDecision, user_id: str
    ) -> SafetyResult:
        """Validate check-out safety."""
        booking_id = decision.entities.get("booking_id")
        if not booking_id or not self.service_client:
            return SafetyResult.safe()

        try:
            booking = await self.service_client.get_booking(user_id, booking_id)
            if not booking:
                return SafetyResult.blocked(
                    code=SafetyCode.BOOKING_NOT_FOUND,
                    hint="Không tìm thấy booking.",
                )
            if booking.get("status") != "checked_in":
                return SafetyResult.blocked(
                    code=SafetyCode.NOT_CHECKED_IN,
                    hint="Bạn chưa check-in, không thể check-out.",
                )
        except Exception as e:
            logger.warning(f"Could not validate check-out: {e}")

        return SafetyResult.safe()

    @staticmethod
    def _time_overlap(
        s1: Any, e1: Any, s2: Any, e2: Any
    ) -> bool:
        """Check if two time ranges overlap. Returns False if any value is None."""
        if not all([s1, e1, s2, e2]):
            return False
        return s1 < e2 and s2 < e1
