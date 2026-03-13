"""
Unit tests for 🔥 Improvement 2.2: Hybrid Confidence & ConfidenceGate.

Tests:
  - HybridConfidence.calculate() formula verification
  - compute_entity_completeness() with various entity states
  - compute_context_match() flow mapping
  - ConfidenceGate.evaluate() threshold logic (clarify / confirm / execute)
"""

import pytest

from app.domain.value_objects.confidence import HybridConfidence, ConfidenceGate


# ─── HybridConfidence.calculate() ────────────────

class TestHybridConfidenceCalculate:

    def test_all_perfect(self):
        """All components at 1.0 → hybrid = 1.0."""
        result = HybridConfidence.calculate(
            llm_confidence=1.0,
            entity_completeness=1.0,
            context_match_score=1.0,
        )
        assert result == pytest.approx(1.0)

    def test_all_zero(self):
        """All components at 0.0 → hybrid = 0.0."""
        result = HybridConfidence.calculate(
            llm_confidence=0.0,
            entity_completeness=0.0,
            context_match_score=0.0,
        )
        assert result == pytest.approx(0.0)

    def test_weights_correct(self):
        """Formula: 0.5*llm + 0.3*entity + 0.2*context."""
        result = HybridConfidence.calculate(
            llm_confidence=0.8,
            entity_completeness=0.6,
            context_match_score=0.4,
        )
        expected = 0.5 * 0.8 + 0.3 * 0.6 + 0.2 * 0.4
        assert result == pytest.approx(expected)

    def test_clamp_above_one(self):
        """Result clamped to 1.0 if components exceed bounds."""
        result = HybridConfidence.calculate(
            llm_confidence=1.5,
            entity_completeness=1.0,
            context_match_score=1.0,
        )
        assert result <= 1.0

    def test_clamp_below_zero(self):
        """Result clamped to 0.0 if negative somehow."""
        result = HybridConfidence.calculate(
            llm_confidence=-0.5,
            entity_completeness=0.0,
            context_match_score=0.0,
        )
        assert result >= 0.0


# ─── HybridConfidence.compute_entity_completeness() ─

class TestEntityCompleteness:

    def test_all_present(self):
        """All required entities present → 1.0."""
        result = HybridConfidence.compute_entity_completeness(
            required_entities=["vehicle_type", "start_time", "end_time"],
            extracted_entities={"vehicle_type": "car", "start_time": "10:00", "end_time": "12:00"},
        )
        assert result == pytest.approx(1.0)

    def test_none_present(self):
        """No required entities present → 0.0."""
        result = HybridConfidence.compute_entity_completeness(
            required_entities=["vehicle_type", "start_time", "end_time"],
            extracted_entities={},
        )
        assert result == pytest.approx(0.0)

    def test_partial(self):
        """1 of 3 required → ~0.333."""
        result = HybridConfidence.compute_entity_completeness(
            required_entities=["vehicle_type", "start_time", "end_time"],
            extracted_entities={"vehicle_type": "car"},
        )
        assert result == pytest.approx(1.0 / 3.0, rel=1e-2)

    def test_no_required(self):
        """No required entities → 1.0 (nothing to miss)."""
        result = HybridConfidence.compute_entity_completeness(
            required_entities=[],
            extracted_entities={"foo": "bar"},
        )
        assert result == pytest.approx(1.0)

    def test_none_values_not_counted(self):
        """Entity present but None/empty → not counted."""
        result = HybridConfidence.compute_entity_completeness(
            required_entities=["vehicle_type", "start_time", "end_time"],
            extracted_entities={"vehicle_type": "car", "start_time": None, "end_time": ""},
        )
        assert result == pytest.approx(1.0 / 3.0, rel=1e-2)


# ─── HybridConfidence.compute_context_match() ────

class TestContextMatch:

    def test_no_last_intent(self):
        """No last intent → first message → 1.0."""
        result = HybridConfidence.compute_context_match(
            current_intent="book_slot",
            last_intent=None,
            conversation_state="idle",
        )
        assert result == pytest.approx(1.0)

    def test_natural_flow(self):
        """check_availability → book_slot is natural flow → 1.0."""
        result = HybridConfidence.compute_context_match(
            current_intent="book_slot",
            last_intent="check_availability",
            conversation_state="check_availability",
        )
        assert result == pytest.approx(1.0)

    def test_same_intent_repeated(self):
        """Same intent repeated → 0.8."""
        result = HybridConfidence.compute_context_match(
            current_intent="book_slot",
            last_intent="book_slot",
            conversation_state="book_slot",
        )
        assert result == pytest.approx(0.8)

    def test_abrupt_topic_switch(self):
        """Unrelated switch → 0.5."""
        result = HybridConfidence.compute_context_match(
            current_intent="feedback",
            last_intent="greeting",
            conversation_state="greeting",
        )
        assert result == pytest.approx(0.5)


# ─── ConfidenceGate.evaluate() ───────────────────

class TestConfidenceGate:

    def test_low_confidence_clarify(self):
        """Below CLARIFY_THRESHOLD → 'clarify'."""
        assert ConfidenceGate.evaluate(0.5, high_stakes=False) == "clarify"

    def test_medium_confidence_confirm(self):
        """Between clarify and confirm thresholds → 'confirm'."""
        assert ConfidenceGate.evaluate(0.80, high_stakes=True) == "confirm"

    def test_high_confidence_execute(self):
        """Above CONFIRM_THRESHOLD → 'execute'."""
        assert ConfidenceGate.evaluate(0.95, high_stakes=False) == "execute"

    def test_high_stakes_stricter(self):
        """High-stakes with medium confidence (below CONFIRM_THRESHOLD) → 'confirm'."""
        result = ConfidenceGate.evaluate(0.84, high_stakes=True)
        assert result == "confirm"

    def test_non_high_stakes_medium_execute(self):
        """Non-high-stakes with confidence above clarify → 'execute'."""
        result = ConfidenceGate.evaluate(0.80, high_stakes=False)
        assert result == "execute"

    def test_boundary_clarify_threshold(self):
        """Exactly at CLARIFY_THRESHOLD boundary."""
        result = ConfidenceGate.evaluate(
            ConfidenceGate.CLARIFY_THRESHOLD, high_stakes=False
        )
        # At boundary should be execute (>= threshold)
        assert result in ("execute", "confirm")
