"""
Unit tests for domain policies — handoff logic.
"""

import pytest

from app.domain.policies.handoff import should_handoff


class TestHandoffPolicy:

    def test_high_frustration_triggers_handoff(self):
        assert should_handoff(frustration_score=0.95, clarification_count=0, message="") is True

    def test_many_clarifications_triggers_handoff(self):
        assert should_handoff(frustration_score=0.0, clarification_count=6, message="") is True

    def test_handoff_keyword(self):
        assert should_handoff(frustration_score=0.0, clarification_count=0, message="tôi muốn nói chuyện với nhân viên") is True

    def test_no_trigger(self):
        assert should_handoff(frustration_score=0.3, clarification_count=1, message="đặt chỗ cho tôi") is False

    def test_borderline_frustration(self):
        """Frustration at exactly 0.8 should not trigger."""
        assert should_handoff(frustration_score=0.8, clarification_count=0, message="") is False
