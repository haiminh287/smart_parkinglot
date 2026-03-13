"""
Application DTOs — Data Transfer Objects for the chatbot pipeline.

🔥 CẢI TIẾN 2.1: IntentDecision now separates classification from extraction.
🔥 CẢI TIẾN 2.2: Tracks hybrid confidence components.
🔥 CẢI TIẾN 2.3: PipelineContext carries SafetyResult with code/hint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class IntentClassification:
    """
    🔥 2.1: Output of classify_intent() — LLM reasoning only.
    Separated from entity extraction to reduce hallucination.
    """
    primary_intent: str
    sub_intents: list[str] = field(default_factory=list)
    llm_confidence: float = 0.0
    reasoning: str = ""                          # Why LLM chose this intent
    clarification_needed: bool = False
    clarification_question: str | None = None


@dataclass
class EntityExtraction:
    """
    🔥 2.1: Output of extract_entities() — schema-driven extraction.
    No guessing — only extract what schema allows.
    """
    entities: dict[str, Any] = field(default_factory=dict)
    missing_entities: list[str] = field(default_factory=list)
    assumptions: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentDecision:
    """
    🔥 2.1 + 2.2: Merged decision with hybrid confidence breakdown.

    Built by IntentService.build_decision() from Classification + Extraction.
    """
    primary_intent: str
    sub_intents: list[str] = field(default_factory=list)
    entities: dict[str, Any] = field(default_factory=dict)
    missing_entities: list[str] = field(default_factory=list)
    assumptions: dict[str, Any] = field(default_factory=dict)

    # 🔥 2.2: Hybrid confidence breakdown
    llm_confidence: float = 0.0
    entity_completeness: float = 0.0
    context_match_score: float = 0.0
    hybrid_confidence: float = 0.0              # Final weighted score

    clarification_needed: bool = False
    clarification_question: str | None = None
    reasoning: str = ""                          # LLM reasoning trace for debugging


@dataclass
class PipelineContext:
    """
    Carries state through the 5-stage pipeline.
    Accumulates results from each stage.
    """
    user_id: str
    message: str
    conversation_id: str
    conversation_context: dict[str, Any] = field(default_factory=dict)

    # Stage 1: Intent
    decision: Optional[IntentDecision] = None

    # Stage 2: Gate
    gate_action: str = ""  # "clarify" | "confirm" | "execute"

    # Stage 3: Safety (🔥 2.3: carries SafetyResult)
    safety_code: str = "OK"
    safety_hint: str = ""
    safety_details: dict[str, Any] = field(default_factory=dict)

    # Stage 4: Action
    action_result: dict[str, Any] = field(default_factory=dict)
    action_taken: str = ""

    # Stage 5: Response
    response_text: str = ""
    suggestions: list[str] = field(default_factory=list)
    show_map: bool = False
    show_qr_code: bool = False

    # Timing
    processing_time_ms: int = 0
