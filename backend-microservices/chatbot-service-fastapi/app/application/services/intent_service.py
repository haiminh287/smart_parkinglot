"""
🔥 CẢI TIẾN 2.1: IntentService — tách thành 3 bước.

IntentService
├── classify_intent()      # Gemini reasoning → primary_intent + confidence
├── extract_entities()     # Schema-driven extraction → entities + missing
└── build_decision()       # Merge + validate + hybrid confidence

Giảm hallucination vì:
- LLM chỉ trả lời "intent là gì và tại sao"
- Entity extraction theo schema cứng, không cho LLM tự bịa field
"""

import json
import logging
import re
from typing import Any, Optional

from app.application.dto import (
    IntentClassification,
    EntityExtraction,
    IntentDecision,
)
from app.domain.value_objects.intent import Intent
from app.domain.value_objects.confidence import HybridConfidence

logger = logging.getLogger(__name__)


class IntentService:
    """
    3-step intent detection: classify → extract → build.
    With context-aware follow-up for multi-turn conversations.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client  # Gemini client injected

    async def detect(
        self,
        message: str,
        context: dict[str, Any],
        user_style: Optional[dict] = None,
    ) -> IntentDecision:
        """
        Full pipeline: context-check → classify → extract → build.
        Falls back to keyword-based if LLM unavailable.

        🔥 CRITICAL: Before 3-step pipeline, check if user is answering
        a clarification question. If so, reuse the previous intent and
        merge entities from context + current message.
        """
        try:
            # ─── Context-Aware Follow-Up Check ───
            # If the previous turn asked for clarification, treat this message
            # as providing the missing entity, NOT as a new intent.
            follow_up = self._try_context_followup(message, context)
            if follow_up is not None:
                return follow_up

            # ─── Standard 3-Step Pipeline ───
            # Step 1: Classify Intent (LLM reasoning)
            classification = await self.classify_intent(message, context)

            # Step 2: Extract Entities (schema-driven)
            extraction = await self.extract_entities(
                message, classification.primary_intent, context
            )

            # Step 3: Build merged decision with hybrid confidence
            decision = self.build_decision(classification, extraction, context)

            return decision

        except Exception as e:
            logger.warning(f"LLM detection failed, using keyword fallback: {e}")
            return self._keyword_fallback(message, context)

    def _try_context_followup(
        self, message: str, context: dict[str, Any]
    ) -> Optional[IntentDecision]:
        """
        🔥 Context-aware follow-up: When the bot asked for clarification
        in the previous turn, interpret this message as providing the
        missing information instead of re-classifying from scratch.

        Returns IntentDecision if follow-up detected, None otherwise.
        """
        last_gate = context.get("lastGateAction")
        last_intent = context.get("lastIntent")

        # Only activate if previous turn was a clarification
        if last_gate != "clarify" or not last_intent:
            return None

        # Don't follow-up on unknown/handoff
        if last_intent in ("unknown", "handoff", "error"):
            return None

        # Check if the user's message is a NEW intent (explicit keywords)
        # If user says something clearly different, don't force follow-up
        new_classify = self._keyword_classify(message)
        if (
            new_classify.primary_intent != "unknown"
            and new_classify.primary_intent != last_intent
            and new_classify.llm_confidence >= 0.8
        ):
            # User switched intent explicitly — don't force follow-up
            return None

        # Resolve the previous intent's required entities
        try:
            intent_enum = Intent(last_intent)
        except ValueError:
            return None

        required = intent_enum.required_entities
        if not required:
            return None

        # Merge: start with lastEntities, then extract new entities from message
        last_entities = dict(context.get("lastEntities", {}))
        new_extraction = self._keyword_extract(message, required)

        # Merge new entities on top of previous
        merged = {**last_entities, **new_extraction.entities}

        # Calculate what's still missing
        still_missing = [f for f in required if f not in merged or not merged[f]]

        # Build a high-confidence decision since we're continuing a known intent
        entity_completeness = (
            (len(required) - len(still_missing)) / len(required) if required else 1.0
        )

        # Context match is high because we're continuing the same intent
        context_match = 1.0

        # Use the previous intent's confidence as base, boosted by context
        base_conf = context.get("lastConfidence", 0.8)
        if base_conf < 0.7:
            base_conf = 0.8  # Floor for follow-ups

        hybrid_conf = HybridConfidence.calculate(
            llm_confidence=base_conf,
            entity_completeness=entity_completeness,
            context_match_score=context_match,
        )

        clarification_needed = len(still_missing) > 0
        clarification_question = None
        if clarification_needed:
            missing_str = ", ".join(still_missing)
            clarification_question = (
                f"Bạn vui lòng cung cấp thêm thông tin: {missing_str}"
            )

        logger.info(
            f"Context follow-up: intent={last_intent}, "
            f"merged_entities={merged}, missing={still_missing}, "
            f"hybrid_conf={hybrid_conf}"
        )

        return IntentDecision(
            primary_intent=last_intent,
            entities=merged,
            missing_entities=still_missing,
            llm_confidence=base_conf,
            entity_completeness=entity_completeness,
            context_match_score=context_match,
            hybrid_confidence=hybrid_conf,
            clarification_needed=clarification_needed,
            clarification_question=clarification_question,
            reasoning="context_followup",
        )

    async def classify_intent(
        self,
        message: str,
        context: dict[str, Any],
    ) -> IntentClassification:
        """
        Step 1: LLM classifies intent + reasoning.
        LLM only answers: WHAT intent + WHY (no entity extraction here).
        """
        if not self.llm_client:
            return self._keyword_classify(message)

        system_prompt = self._build_classification_prompt(context)
        user_prompt = f"""Phân tích tin nhắn sau và trả về JSON:
{{
  "primary_intent": "<intent>",
  "sub_intents": [],
  "confidence": <0.0-1.0>,
  "reasoning": "<giải thích ngắn gọn tại sao chọn intent này>",
  "clarification_needed": false,
  "clarification_question": null
}}

Các intent hợp lệ: greeting, goodbye, check_availability, book_slot, rebook_previous,
cancel_booking, check_in, check_out, my_bookings, current_parking,
pricing, help, feedback, handoff, unknown

Tin nhắn: "{message}"
"""

        try:
            response = await self.llm_client.generate(system_prompt, user_prompt)
            data = self._parse_json_response(response)

            llm_result = IntentClassification(
                primary_intent=data.get("primary_intent", "unknown"),
                sub_intents=data.get("sub_intents", []),
                llm_confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                clarification_needed=data.get("clarification_needed", False),
                clarification_question=data.get("clarification_question"),
            )

            # 🔥 Keyword override: for critical intents, keyword match takes
            # precedence when the LLM disagrees.  This prevents Gemini from
            # confusing e.g. "hủy đặt chỗ" (cancel_booking) with book_slot.
            keyword_result = self._keyword_classify(message)
            critical_intents = {"cancel_booking", "check_in", "check_out"}
            if (
                keyword_result.primary_intent in critical_intents
                and keyword_result.primary_intent != llm_result.primary_intent
                and keyword_result.llm_confidence >= 0.85
            ):
                logger.info(
                    f"Keyword override: LLM={llm_result.primary_intent} "
                    f"→ keyword={keyword_result.primary_intent} "
                    f"for message='{message}'"
                )
                return keyword_result

            return llm_result
        except Exception as e:
            logger.error(f"classify_intent LLM error: {e}")
            return self._keyword_classify(message)

    async def extract_entities(
        self,
        message: str,
        intent: str,
        context: dict[str, Any],
    ) -> EntityExtraction:
        """
        Step 2: Schema-driven entity extraction.
        Only extracts fields defined in Intent.required_entities.
        """
        try:
            intent_enum = Intent(intent)
        except ValueError:
            intent_enum = Intent.UNKNOWN

        required = intent_enum.required_entities

        if not required:
            return EntityExtraction()

        if not self.llm_client:
            return self._keyword_extract(message, required)

        # Build extraction prompt with explicit schema
        schema_fields = ", ".join(f'"{e}": "<value or null>"' for e in required)
        user_prompt = f"""Trích xuất thông tin từ tin nhắn. CHỈ trả về JSON với các field sau:
{{
  {schema_fields}
}}

Nếu không tìm thấy thông tin cho field nào, để null.
Tin nhắn: "{message}"
Context: {json.dumps(context.get("lastEntities", {}), ensure_ascii=False)}
"""

        try:
            response = await self.llm_client.generate(
                "Bạn là entity extractor. Chỉ trả về JSON, không giải thích.",
                user_prompt,
            )
            data = self._parse_json_response(response)

            entities = {}
            missing = []
            assumptions = {}

            for field_name in required:
                value = data.get(field_name)
                if value and value != "null":
                    entities[field_name] = value
                else:
                    # Try to fill from context
                    ctx_value = context.get("lastEntities", {}).get(field_name)
                    if ctx_value:
                        entities[field_name] = ctx_value
                        assumptions[field_name] = "from_context"
                    else:
                        missing.append(field_name)

            return EntityExtraction(
                entities=entities,
                missing_entities=missing,
                assumptions=assumptions,
            )
        except Exception as e:
            logger.error(f"extract_entities LLM error: {e}")
            return self._keyword_extract(message, required)

    def build_decision(
        self,
        classification: IntentClassification,
        extraction: EntityExtraction,
        context: dict[str, Any],
    ) -> IntentDecision:
        """
        Step 3: Merge classification + extraction + compute hybrid confidence.

        🔥 2.2: Hybrid confidence = 0.5*LLM + 0.3*entity + 0.2*context
        """
        try:
            intent_enum = Intent(classification.primary_intent)
        except ValueError:
            intent_enum = Intent.UNKNOWN

        # Compute hybrid confidence components
        entity_completeness = HybridConfidence.compute_entity_completeness(
            required_entities=intent_enum.required_entities,
            extracted_entities=extraction.entities,
        )
        context_match = HybridConfidence.compute_context_match(
            current_intent=classification.primary_intent,
            last_intent=context.get("lastIntent"),
            conversation_state=context.get("state"),
        )
        hybrid_conf = HybridConfidence.calculate(
            llm_confidence=classification.llm_confidence,
            entity_completeness=entity_completeness,
            context_match_score=context_match,
        )

        # If missing entities → force clarification
        clarification_needed = classification.clarification_needed
        clarification_question = classification.clarification_question

        if extraction.missing_entities and not clarification_needed:
            clarification_needed = True
            missing_str = ", ".join(extraction.missing_entities)
            clarification_question = (
                f"Bạn vui lòng cung cấp thêm thông tin: {missing_str}"
            )

        return IntentDecision(
            primary_intent=classification.primary_intent,
            sub_intents=classification.sub_intents,
            entities=extraction.entities,
            missing_entities=extraction.missing_entities,
            assumptions=extraction.assumptions,
            llm_confidence=classification.llm_confidence,
            entity_completeness=entity_completeness,
            context_match_score=context_match,
            hybrid_confidence=hybrid_conf,
            clarification_needed=clarification_needed,
            clarification_question=clarification_question,
            reasoning=classification.reasoning,
        )

    # ─── Keyword Fallbacks ─────────────────────────────

    @staticmethod
    def _word_match(keyword: str, message: str) -> bool:
        """Check if keyword matches as a whole word/phrase in message."""
        # For short keywords (<=3 chars), require word boundary
        if len(keyword) <= 3:
            return bool(re.search(r'(?:^|\s)' + re.escape(keyword) + r'(?:\s|$|[?!.,])', message))
        return keyword in message

    @staticmethod
    def _normalize_vietnamese(msg: str) -> str:
        """Normalize Vietnamese text for better keyword matching.
        Handles common no-accent Vietnamese typing patterns.
        """
        replacements = {
            # Vehicle types
            "oto": "ô tô",
            "o to": "ô tô",
            "xe oto": "xe ô tô",
            "xe hoi": "xe hơi",
            "xe may": "xe máy",
            # Availability keywords
            "cho trong": "chỗ trống",
            "cho trống": "chỗ trống",
            "may cho": "mấy chỗ",
            "con may": "còn mấy",
            "con cho": "còn chỗ",
            "bao nhieu cho": "bao nhiêu chỗ",
            "bao nhieu": "bao nhiêu",
            "trong": "trống",
            # Booking keywords
            "dat cho": "đặt chỗ",
            "dat xe": "đặt xe",
            "gui xe": "gửi xe",
            "huy": "hủy",
            "lich dat": "lịch đặt",
            "lich su": "lịch sử",
            "lich su booking": "lịch sử booking",
            "xem lich su": "xem lịch sử",
            # Pricing
            "gia": "giá",
            "bao nhieu tien": "bao nhiêu tiền",
            # Time
            "hom nay": "hôm nay",
            "ngay mai": "ngày mai",
            "bay gio": "bây giờ",
            # Greeting/goodbye
            "tam biet": "tạm biệt",
            "xin chao": "xin chào",
            # Parking
            "dau xe": "đậu xe",
            # Check-in/out (normalize spaces)
            "check in": "check-in",
            "check out": "check-out",
        }
        result = msg.lower()
        # Apply longer replacements first to avoid partial matches
        for old, new in sorted(replacements.items(), key=lambda x: -len(x[0])):
            result = result.replace(old, new)
        return result

    def _keyword_classify(self, message: str) -> IntentClassification:
        """Fallback classification using keywords with word-boundary matching."""
        msg = self._normalize_vietnamese(message)

        # Order: specific intents first, generic greeting last
        mapping = [
            # Rebook
            (["đặt lại", "rebook", "như lần trước", "đặt lại như"], "rebook_previous", 0.9),
            # Check-in / Check-out
            (["check-in", "checkin", "check in", "vào bãi", "nhận chỗ"], "check_in", 0.9),
            (["check-out", "checkout", "check out", "ra bãi", "trả chỗ"], "check_out", 0.9),
            # Cancel
            (["hủy", "cancel", "hủy booking", "hủy đặt", "hủy đặt chỗ", "huy dat cho"], "cancel_booking", 0.9),
            # My bookings — covers history/list/schedule queries
            (["booking của tôi", "my booking", "xem booking", "lịch đặt",
              "lịch đặt chỗ", "danh sách booking", "xem lịch đặt", "đặt chỗ của tôi",
              "cho tôi xem lịch", "booking cua toi", "xem lich dat",
              "lịch sử booking", "lịch sử đặt", "lịch sử", "xem lịch sử",
              "history", "booking history", "các booking"], "my_bookings", 0.9),
            # Current parking
            (["đang đậu", "ở đâu", "xe tôi", "xe đang đậu", "vị trí xe"], "current_parking", 0.9),
            # Check availability — must be BEFORE book_slot
            (["trống", "còn chỗ", "available", "chỗ trống", "slot trống",
              "mấy chỗ", "bao nhiêu chỗ", "còn mấy", "chỗ nào trống",
              "tìm chỗ", "xem chỗ", "xem chỗ trống", "tìm chỗ trống"], "check_availability", 0.85),
            # Pricing
            (["giá", "price", "bảng giá", "bao nhiêu tiền", "xem giá",
              "giá đậu xe", "giá gửi xe", "phí", "chi phí", "giá xe"], "pricing", 0.9),
            # Book slot — only booking-creation keywords (NOT generic "booking")
            (["đặt chỗ", "đặt slot", "book", "muốn đặt",
              "đặt xe", "gửi xe", "đặt chỗ đậu", "dat cho", "dat xe",
              "muốn gửi", "muốn đậu", "đặt ngay"], "book_slot", 0.85),
            # Help
            (["giúp", "help", "hướng dẫn", "trợ giúp", "hỗ trợ", "cách sử dụng"], "help", 0.9),
            # Feedback
            (["đánh giá", "feedback", "nhận xét", "góp ý"], "feedback", 0.9),
            # Goodbye
            (["tạm biệt", "goodbye", "bye", "bye bye", "hẹn gặp lại",
              "tạm biệt nhé", "thôi nhé", "cảm ơn bye"], "goodbye", 1.0),
            # Greeting — LAST (lowest priority)
            (["xin chào", "hello", "chào bạn", "chào", "hi there"], "greeting", 1.0),
        ]

        for keywords, intent, conf in mapping:
            if any(self._word_match(kw, msg) for kw in keywords):
                return IntentClassification(
                    primary_intent=intent,
                    llm_confidence=conf,
                    reasoning="keyword_fallback",
                )

        return IntentClassification(
            primary_intent="unknown",
            llm_confidence=0.3,
            reasoning="keyword_fallback_no_match",
        )

    def _keyword_extract(
        self, message: str, required: list[str]
    ) -> EntityExtraction:
        """Keyword entity extraction fallback with Vietnamese support."""
        entities: dict[str, Any] = {}
        missing: list[str] = []

        msg = self._normalize_vietnamese(message)

        for field_name in required:
            if field_name == "vehicle_type":
                if any(w in msg for w in ["ô tô", "xe hơi", "car", "4 bánh", "xe ô tô"]):
                    entities["vehicle_type"] = "car"
                elif any(w in msg for w in ["xe máy", "moto", "2 bánh", "xe gắn máy", "motorcycle"]):
                    entities["vehicle_type"] = "motorcycle"
                else:
                    missing.append(field_name)
            elif field_name == "start_time":
                # Basic time extraction
                if "ngày mai" in msg:
                    entities["start_time"] = "tomorrow"
                elif "hôm nay" in msg:
                    entities["start_time"] = "today"
                elif "bây giờ" in msg or "ngay" in msg:
                    entities["start_time"] = "now"
                else:
                    missing.append(field_name)
            elif field_name == "end_time":
                # Will be derived from start_time + duration or default
                if "1 giờ" in msg or "1 tiếng" in msg or "một giờ" in msg:
                    entities["end_time"] = "+1h"
                elif "2 giờ" in msg or "2 tiếng" in msg or "hai giờ" in msg:
                    entities["end_time"] = "+2h"
                elif "3 giờ" in msg or "3 tiếng" in msg:
                    entities["end_time"] = "+3h"
                elif "cả ngày" in msg or "nguyên ngày" in msg:
                    entities["end_time"] = "+8h"
                else:
                    missing.append(field_name)
            else:
                missing.append(field_name)

        return EntityExtraction(entities=entities, missing_entities=missing)

    def _keyword_fallback(
        self, message: str, context: dict[str, Any]
    ) -> IntentDecision:
        """Full keyword fallback producing IntentDecision."""
        classification = self._keyword_classify(message)
        try:
            intent_enum = Intent(classification.primary_intent)
        except ValueError:
            intent_enum = Intent.UNKNOWN
        extraction = self._keyword_extract(message, intent_enum.required_entities)
        return self.build_decision(classification, extraction, context)

    def _build_classification_prompt(self, context: dict[str, Any]) -> str:
        """System prompt for intent classification with Vietnamese examples."""
        last_intent = context.get("lastIntent", "none")
        state = context.get("state", "idle")
        return f"""Bạn là ParkSmart AI — hệ thống phân tích intent cho chatbot bãi đậu xe thông minh.
Bạn CHỈ phân loại intent, KHÔNG trích xuất entity.

CONTEXT:
- Intent trước đó: {last_intent}
- Trạng thái hội thoại: {state}

═══════════════════════════════════════
DANH SÁCH 15 INTENT VÀ VÍ DỤ:
═══════════════════════════════════════

1. greeting — Chào hỏi, bắt đầu hội thoại
   VD: "xin chào", "hello", "chào bạn", "hi"

2. goodbye — Kết thúc, tạm biệt
   VD: "tạm biệt", "bye", "hẹn gặp lại", "cảm ơn bye"

3. check_availability — Hỏi chỗ trống, tìm slot (KHÔNG phải đặt)
   VD: "còn chỗ trống không?", "mấy chỗ trống cho ô tô?", "xem chỗ trống"

4. book_slot — Muốn ĐẶT chỗ đậu xe MỚI
   VD: "tôi muốn đặt chỗ", "đặt chỗ cho xe máy", "gửi xe", "book slot"
   ⚠️ KHÔNG nhầm với cancel_booking hay my_bookings

5. rebook_previous — Đặt lại giống lần trước
   VD: "đặt lại như lần trước", "rebook", "đặt lại"

6. cancel_booking — HỦY booking đã đặt
   VD: "hủy đặt chỗ", "hủy booking", "cancel booking", "tôi muốn hủy"
   ⚠️ "hủy đặt chỗ" = cancel_booking (KHÔNG PHẢI book_slot)

7. check_in — Nhận chỗ, vào bãi
   VD: "check-in", "checkin", "tôi đã đến", "vào bãi", "nhận chỗ"

8. check_out — Trả chỗ, ra bãi
   VD: "check-out", "checkout", "ra bãi", "trả chỗ"

9. my_bookings — Xem DANH SÁCH booking, lịch sử đặt chỗ
   VD: "xem booking của tôi", "lịch sử đặt", "danh sách booking", "cho tôi xem booking"
   ⚠️ "booking của tôi" = my_bookings (KHÔNG PHẢI book_slot)

10. current_parking — Hỏi xe đang đậu ở đâu
    VD: "xe tôi đang ở đâu?", "xe đang đậu chỗ nào?", "vị trí xe"

11. pricing — Hỏi giá, bảng giá, phí đậu xe
    VD: "giá đậu xe bao nhiêu?", "xem bảng giá", "phí gửi xe"

12. help — Cần hướng dẫn sử dụng
    VD: "giúp tôi", "hướng dẫn", "trợ giúp", "cách sử dụng"

13. feedback — Đánh giá, góp ý dịch vụ
    VD: "tôi muốn đánh giá", "feedback", "góp ý"

14. handoff — Cần nói chuyện với nhân viên
    VD: "nói chuyện với nhân viên", "chuyển cho người thật", "hỗ trợ viên"

15. unknown — Không thuộc intent nào ở trên

═══════════════════════════════════════
QUY TẮC PHÂN BIỆT (RẤT QUAN TRỌNG):
═══════════════════════════════════════

• "hủy" / "cancel" / "hủy đặt chỗ" → cancel_booking (KHÔNG PHẢI book_slot)
• "booking của tôi" / "xem booking" / "lịch sử" → my_bookings (KHÔNG PHẢI book_slot)
• "đặt chỗ" / "muốn đặt" / "gửi xe" → book_slot
• "còn chỗ" / "chỗ trống" / "xem chỗ" → check_availability
• "check-in" / "vào bãi" → check_in
• "check-out" / "ra bãi" → check_out

═══════════════════════════════════════
RULES:
═══════════════════════════════════════
- Trả về JSON duy nhất, KHÔNG giải thích thêm.
- confidence: 0.9-1.0 nếu chắc chắn, 0.7-0.89 nếu khá chắc, <0.7 nếu mơ hồ.
- Nếu không rõ ràng, đặt confidence thấp và clarification_needed=true.
- Nếu tin nhắn chứa từ "hủy" thì LUÔN là cancel_booking.
- Nếu tin nhắn hỏi "xem booking" / "lịch sử" thì LUÔN là my_bookings.
"""

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM JSON: {text[:200]}")
            return {}
