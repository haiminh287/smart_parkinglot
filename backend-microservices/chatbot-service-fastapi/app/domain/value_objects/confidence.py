"""
🔥 CẢI TIẾN 2.2: Hybrid Confidence — không tin LLM mù quáng.

final_confidence = 0.5 * llm_confidence
                 + 0.3 * entity_completeness
                 + 0.2 * context_match_score

- Thiếu entity → auto tụt confidence
- Context lệch intent trước → tụt confidence
"""


class HybridConfidence:
    """Calculates a weighted confidence score combining LLM + heuristics."""

    LLM_WEIGHT = 0.5
    ENTITY_WEIGHT = 0.3
    CONTEXT_WEIGHT = 0.2

    @classmethod
    def calculate(
        cls,
        llm_confidence: float,
        entity_completeness: float,
        context_match_score: float,
    ) -> float:
        """
        Compute hybrid confidence.

        Args:
            llm_confidence: Raw LLM confidence [0.0–1.0].
            entity_completeness: Fraction of required entities present [0.0–1.0].
            context_match_score: How well intent matches conversation context [0.0–1.0].

        Returns:
            Weighted hybrid confidence [0.0–1.0].
        """
        raw = (
            cls.LLM_WEIGHT * llm_confidence
            + cls.ENTITY_WEIGHT * entity_completeness
            + cls.CONTEXT_WEIGHT * context_match_score
        )
        return round(min(max(raw, 0.0), 1.0), 4)

    @classmethod
    def compute_entity_completeness(
        cls,
        required_entities: list[str],
        extracted_entities: dict,
    ) -> float:
        """
        Fraction of required entities that are present and non-empty.

        If no entities are required, returns 1.0 (fully complete).
        """
        if not required_entities:
            return 1.0

        present = sum(
            1 for e in required_entities
            if extracted_entities.get(e) not in (None, "", [])
        )
        return round(present / len(required_entities), 4)

    @classmethod
    def compute_context_match(
        cls,
        current_intent: str,
        last_intent: str | None,
        conversation_state: str | None,
    ) -> float:
        """
        Score how well current intent matches conversation flow.

        Rules:
        - If first message (no last_intent) → 1.0
        - Natural follow-ups (check_availability → book_slot) → 1.0
        - Same intent repeated → 0.8 (maybe confused)
        - Abrupt topic switch → 0.5
        """
        if not last_intent:
            return 1.0

        # Natural conversation flows
        natural_flows: dict[str, set[str]] = {
            "greeting": {"check_availability", "help", "my_bookings", "pricing"},
            "check_availability": {"book_slot", "pricing"},
            "book_slot": {"check_in", "my_bookings", "cancel_booking"},
            "cancel_booking": {"book_slot", "check_availability"},
            "check_in": {"current_parking", "check_out"},
            "check_out": {"feedback", "book_slot"},
            "my_bookings": {"cancel_booking", "check_in", "check_out"},
            "pricing": {"book_slot", "check_availability"},
            "help": {"check_availability", "book_slot", "my_bookings"},
        }

        # Same intent = maybe confused / looping
        if current_intent == last_intent:
            return 0.8

        # Natural follow-up
        allowed_next = natural_flows.get(last_intent, set())
        if current_intent in allowed_next:
            return 1.0

        # Abrupt topic switch
        return 0.5


class ConfidenceGate:
    """
    Rule-based gate using hybrid confidence thresholds.

    Returns: "clarify" | "confirm" | "execute"
    """

    CLARIFY_THRESHOLD = 0.65
    CONFIRM_THRESHOLD = 0.85

    @classmethod
    def evaluate(cls, confidence: float, high_stakes: bool) -> str:
        if confidence < cls.CLARIFY_THRESHOLD:
            return "clarify"
        if high_stakes and confidence < cls.CONFIRM_THRESHOLD:
            return "confirm"
        return "execute"
