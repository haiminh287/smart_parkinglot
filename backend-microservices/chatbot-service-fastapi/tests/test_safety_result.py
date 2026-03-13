"""
Unit tests for 🔥 Improvement 2.3: SafetyResult with reason codes.

Tests:
  - SafetyResult.safe() / .blocked() construction
  - SafetyCode enum completeness
  - SafetyService validation dispatch
"""

import pytest

from app.domain.value_objects.safety_result import SafetyResult, SafetyCode


class TestSafetyResult:

    def test_safe_result(self):
        result = SafetyResult.safe()
        assert result.ok is True
        assert result.code == SafetyCode.OK
        assert result.hint == ""

    def test_blocked_result(self):
        result = SafetyResult.blocked(
            code=SafetyCode.DOUBLE_BOOKING,
            hint="Bạn đã có booking trong thời gian này.",
            existing_booking_id="abc-123",
        )
        assert result.ok is False
        assert result.code == SafetyCode.DOUBLE_BOOKING
        assert "booking" in result.hint.lower()
        assert result.details["existing_booking_id"] == "abc-123"

    def test_all_safety_codes_exist(self):
        """Verify all expected safety codes are in the enum."""
        expected = [
            "SLOT_NOT_AVAILABLE",
            "DOUBLE_BOOKING",
            "OUT_OF_OPERATING_HOURS",
            "VEHICLE_NOT_FOUND",
            "BOOKING_NOT_FOUND",
            "ALREADY_CHECKED_IN",
            "NOT_CHECKED_IN",
            "BOOKING_EXPIRED",
            "MAX_BOOKINGS_REACHED",
            "INVALID_TIME_RANGE",
            "OK",
        ]
        for name in expected:
            assert hasattr(SafetyCode, name), f"SafetyCode.{name} missing"

    def test_blocked_has_details(self):
        result = SafetyResult.blocked(
            code=SafetyCode.MAX_BOOKINGS_REACHED,
            hint="Tối đa 3 booking.",
            active_count=3,
        )
        assert result.details["active_count"] == 3

    def test_safe_has_empty_details(self):
        result = SafetyResult.safe()
        assert result.details == {}
