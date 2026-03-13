"""
🔥 CẢI TIẾN 2.6: AI Observability Metrics — log AI-specific, không chỉ log API.

Tracks:
- intent_mismatch_rate → phát hiện prompt hỏng
- clarification_rate → prompt quá mơ hồ
- confirmation_rate → confidence chưa tốt
- action_fail_after_execute → logic domain sai
- user_override_rate → chatbot đoán sai
"""

from enum import Enum


class AIMetricType(str, Enum):
    # Pipeline outcomes
    INTENT_DETECTED = "intent_detected"
    INTENT_MISMATCH = "intent_mismatch"         # User corrected/re-asked → old intent was wrong
    CLARIFICATION_TRIGGERED = "clarification_triggered"
    CONFIRMATION_TRIGGERED = "confirmation_triggered"

    # Execution outcomes
    SAFETY_BLOCKED = "safety_blocked"
    ACTION_SUCCESS = "action_success"
    ACTION_FAILED = "action_failed"              # Action executed but failed
    ACTION_FAIL_AFTER_EXECUTE = "action_fail_after_execute"  # Safety passed but action still failed

    # User behavior signals
    USER_OVERRIDE = "user_override"              # User ignored suggestion, did something else
    USER_FEEDBACK_POSITIVE = "user_feedback_positive"
    USER_FEEDBACK_NEGATIVE = "user_feedback_negative"
    HANDOFF_REQUESTED = "handoff_requested"

    # Confidence calibration
    CONFIDENCE_VS_OUTCOME = "confidence_vs_outcome"  # Log (confidence, was_correct) for calibration

    # Memory
    MEMORY_UPDATE_SKIPPED = "memory_update_skipped"  # Anti-noise rule triggered
    PROACTIVE_SUPPRESSED = "proactive_suppressed"    # Cooldown/suppression rule triggered
