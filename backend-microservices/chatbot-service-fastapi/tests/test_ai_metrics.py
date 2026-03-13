"""
Unit tests for 🔥 Improvement 2.6: AI Observability metrics.
"""

import pytest

from app.domain.value_objects.ai_metrics import AIMetricType


class TestAIMetricType:

    def test_all_metric_types_exist(self):
        expected = [
            "INTENT_DETECTED",
            "INTENT_MISMATCH",
            "CLARIFICATION_TRIGGERED",
            "CONFIRMATION_TRIGGERED",
            "ACTION_SUCCESS",
            "ACTION_FAILED",
            "ACTION_FAIL_AFTER_EXECUTE",
            "SAFETY_BLOCKED",
            "HANDOFF_REQUESTED",
            "USER_OVERRIDE",
            "USER_FEEDBACK_POSITIVE",
            "USER_FEEDBACK_NEGATIVE",
            "CONFIDENCE_VS_OUTCOME",
            "MEMORY_UPDATE_SKIPPED",
            "PROACTIVE_SUPPRESSED",
        ]
        for name in expected:
            assert hasattr(AIMetricType, name), f"AIMetricType.{name} missing"

    def test_metric_values_are_lowercase(self):
        for member in AIMetricType:
            assert member.value == member.value.lower()
