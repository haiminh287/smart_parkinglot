# 🤖 Intelligent Parking Chatbot v3.0 — FastAPI Production Plan

> **Ngôn ngữ**: Python 3.11 (FastAPI)
> **Kiến trúc**: Clean Architecture 4-Layer (tuân thủ COPILOT_MASTER_PLAN.md Section A-H)
> **Database**: MySQL (SQLAlchemy 2.0 + Pydantic v2)
> **LLM**: Google Gemini API via LangChain
> **Port**: 8008

---

## I. ARCHITECTURE OVERVIEW

```
User Message (via Gateway :8000)
     ↓
[API Layer]          ← Parse request (Pydantic), validate token
     ↓
[Application Layer]  ← Orchestrate pipeline: Intent → Safety → Action → Response
     ↓
[Domain Layer]       ← Pure business rules, entities, policies
     ↓
[Infrastructure]     ← MySQL, Redis, RabbitMQ, Gemini Client
```

### Pipeline Chi Tiết (5-Stage)

```
Message Input
     ↓
┌─────────────────────────────┐
│ 1. Intent Decision Graph    │ ← Gemini 2.0 Flash + Context
│    → primary_intent         │
│    → sub_intents            │
│    → missing_entities       │
│    → confidence             │
│    → clarification_needed   │
└────────────┬────────────────┘
             ↓
┌─────────────────────────────┐
│ 2. Confidence Gate          │ ← Rule-based
│    < 0.75 → ask clarify     │
│    < 0.90 + high-stakes → confirm │
│    ≥ 0.90 → execute         │
└────────────┬────────────────┘
             ↓
┌─────────────────────────────┐
│ 3. Safety Rules Layer       │ ← Non-LLM validation
│    → No double booking      │
│    → Within operating hours │
│    → Vehicle exists          │
│    → Slot available          │
└────────────┬────────────────┘
             ↓
┌─────────────────────────────┐
│ 4. Action Executor          │ ← HTTP calls to internal services
│    → booking-service        │
│    → parking-service        │
│    → vehicle-service        │
│    → payment-service        │
└────────────┬────────────────┘
             ↓
┌─────────────────────────────┐
│ 5. Response Generator       │ ← User Style Profile + LLM
│    → Personalized tone      │
│    → Emoji level            │
│    → Short/detailed format  │
│    → Suggestions            │
└─────────────────────────────┘
```

---

## II. THƯ MỤC CHUẨN — CLEAN ARCHITECTURE

```
chatbot-service-fastapi/
├── app/
│   ├── api/
│   │   ├── dependencies.py    # get_current_user, get_db
│   │   ├── middleware/        # GatewayAuthMiddleware
│   │   └── routers/
│   │       ├── chat.py        # POST /api/chat/
│   │       ├── conversation.py # CRUD conversations
│   │       ├── feedback.py    # Submit feedback
│   │       ├── preferences.py # User preferences
│   │       ├── notifications.py # Proactive notifications
│   │       └── actions.py     # Undo/Action logs
│   │
│   ├── application/
│   │   ├── dto/               # Data Transfer Objects
│   │   │   ├── intent.py      # IntentDecision
│   │   │   └── context.py     # PipelineContext
│   │   ├── services/
│   │       ├── orchestrator.py # Main pipeline logic
│   │       ├── intent.py      # Intent detection logic
│   │       ├── safety.py      # Safety rules validation
│   │       ├── action.py      # Action execution
│   │       ├── response.py    # Response generation
│   │       ├── memory.py      # Behavior/Preference updating
│   │       └── proactive.py   # Proactive triggers
│   │
│   ├── domain/
│   │   ├── entities/          # Pydantic models (Internal)
│   │   │   ├── conversation.py
│   │   │   └── behavior.py
│   │   ├── value_objects/
│   │   │   ├── intent.py      # Intent Enum
│   │   │   └── confidence.py  # Confidence Logic
│   │   └── exceptions.py      # Domain exceptions
│   │
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── session.py     # SQLAlchemy engine
│   │   │   └── models.py      # SQL Tables (ORM)
│   │   ├── llm/
│   │   │   ├── gemini.py      # Gemini Client
│   │   │   └── prompts.py     # System prompts
│   │   ├── external/
│   │   │   └── service_client.py # HTTP calls to other services
│   │   ├── messaging/
│   │   │   ├── producer.py    # RabbitMQ Producer
│   │   │   └── consumer.py    # RabbitMQ Consumer
│   │   └── cache/
│   │       └── redis.py       # Redis Client
│   │
│   ├── schemas/               # API Request/Response (CamelModel)
│   │   ├── base.py            # CamelModel
│   │   └── chatbot.py         # ChatRequest, ChatResponse...
│   │
│   ├── config.py              # Environment variables
│   └── main.py                # FastAPI app entrypoint
│
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── requirements.txt
└── alembic.ini                # DB Migrations (if needed)
```

---

## III. DOMAIN LAYER — ENTITIES & VALUE OBJECTS

### 3.1 Intent Enum

```python
# app/domain/value_objects/intent.py
from enum import Enum

class Intent(str, Enum):
    GREETING = "greeting"
    CHECK_AVAILABILITY = "check_availability"
    BOOK_SLOT = "book_slot"
    REBOOK_PREVIOUS = "rebook_previous"
    CANCEL_BOOKING = "cancel_booking"
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    MY_BOOKINGS = "my_bookings"
    CURRENT_PARKING = "current_parking"
    PRICING = "pricing"
    HELP = "help"
    FEEDBACK = "feedback"
    HANDOFF = "handoff"
    UNKNOWN = "unknown"

    @property
    def is_high_stakes(self) -> bool:
        return self in [
            Intent.BOOK_SLOT, 
            Intent.CANCEL_BOOKING, 
            Intent.CHECK_OUT
        ]
```

### 3.2 Confidence Logic

```python
# app/domain/value_objects/confidence.py
class ConfidenceGate:
    CLARIFY_THRESHOLD = 0.75
    CONFIRM_THRESHOLD = 0.90

    @classmethod
    def evaluate(cls, confidence: float, high_stakes: bool) -> str:
        if confidence < cls.CLARIFY_THRESHOLD:
            return "clarify"
        if high_stakes and confidence < cls.CONFIRM_THRESHOLD:
            return "confirm"
        return "execute"
```

---

## IV. APPLICATION LAYER — ORCHESTRATOR & SERVICES

### 4.1 Orchestrator (Pipeline)

```python
# app/application/services/orchestrator.py
class ChatbotOrchestrator:
    def __init__(self, user_id: str, db: Session):
        self.user_id = user_id
        self.db = db
        self.intent_svc = IntentService()
        self.safety_svc = SafetyService()
        self.action_svc = ActionService()
        self.response_svc = ResponseService()
        self.memory_svc = MemoryService(db, user_id)

    async def process_message(self, message: str, context: dict) -> dict:
        start_time = time.time()

        # 1. Detect Intent
        decision = await self.intent_svc.detect(message, context)

        # 2. Confidence Gate
        gate_action = ConfidenceGate.evaluate(
            decision.confidence, 
            Intent(decision.primary_intent).is_high_stakes
        )
        
        if gate_action == "clarify":
            return await self.response_svc.generate_clarification(decision)

        if gate_action == "confirm":
            return await self.response_svc.generate_confirmation(decision)

        # 3. Safety Rules
        if not self.safety_svc.validate(decision):
            return await self.response_svc.generate_safety_error(decision)

        # 4. Execute Action
        action_result = await self.action_svc.execute(self.user_id, decision)

        # 5. Generate Response
        response = await self.response_svc.generate_response(
            decision, action_result, self.memory_svc.get_style()
        )

        # 6. Update Memory (Async)
        BackgroundTasks().add_task(
            self.memory_svc.update_behavior, decision, action_result
        )

        return response
```

### 4.2 Intent Decision Model

```python
# app/application/dto/intent.py
from pydantic import BaseModel, Field

class IntentDecision(BaseModel):
    primary_intent: str
    sub_intents: list[str] = []
    missing_entities: list[str] = []
    entities: dict = {}
    assumptions: dict = {}
    confidence: float
    clarification_needed: bool = False
    clarification_question: str | None = None
```

---

## V. API LAYER — FULL ENDPOINT SPEC

### 5.1 Request/Response Schemas (CamelModel)

> **LƯU Ý QUAN TRỌNG**: Tất cả schema PHẢI kế thừa `app.schemas.base.CamelModel`.

```python
# app/schemas/chatbot.py
from typing import Optional, Dict, Any, List
from app.schemas.base import CamelModel

class ChatRequest(CamelModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(CamelModel):
    response: str
    intent: Optional[str] = None
    entities: Dict[str, Any] = {}
    suggestions: List[str] = []
    data: Dict[str, Any] = {}
    conversation_id: str
    message_id: str
    confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    show_map: bool = False
    show_qr_code: bool = False
    clarification_needed: bool = False
    confirmation_needed: bool = False

class FeedbackRequest(CamelModel):
    conversation_id: str
    rating: int  # 1-5
    comment: Optional[str] = None
```

### 5.2 API Endpoints

| Method | Path | Usage |
|--------|------|-------|
| `POST` | `/api/chat/` | Main chat endpoint |
| `GET` | `/api/quick-actions/` | Get localized quick action buttons |
| `POST` | `/api/feedback/` | Submit User Feedback (RLHF data) |
| `GET` | `/api/conversations/` | List user history |
| `GET` | `/api/conversations/active/` | Get current active context |
| `GET` | `/api/preferences/` | Get user parking preferences |
| `PUT` | `/api/preferences/` | Update preferences manual override |

---

## VI. INFRASTRUCTURE LAYER — DATABASE MODELS

### 6.1 SQLAlchemy Models (table definitions)

> **QUY TẮC**: `__tablename__` phải khớp chính xác với Convention.

```python
# app/infrastructure/db/models.py
from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.infrastructure.db.session import Base
import uuid

class Conversation(Base):
    __tablename__ = "chatbot_conversation"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True, nullable=False)
    current_state = Column(String(50), default="idle")
    context = Column(JSON, default={})
    total_turns = Column(Integer, default=0)
    satisfaction_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class ChatMessage(Base):
    __tablename__ = "chatbot_chatmessage"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("chatbot_conversation.id"))
    role = Column(String(20)) # user/assistant
    content = Column(Text)
    intent = Column(String(100))
    entities = Column(JSON)
    confidence = Column(Float)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=func.now())

class UserPreferences(Base):
    __tablename__ = "chatbot_user_preferences"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), unique=True, index=True)
    favorite_lot_id = Column(String(36), nullable=True)
    default_vehicle_id = Column(String(36), nullable=True)
    profile_summary = Column(Text, default="")
    behavior_data = Column(JSON, default={}) # Stores cancel_rate, avg_duration
```

---

## VII. MEMORY ARCHITECTURE & PERSONALIZATION

### 7.1 Personalized System Prompt

```python
# app/infrastructure/llm/prompts.py
def build_system_prompt(prefs: UserPreferences) -> str:
    # 1. Load behavior data
    avg_duration = prefs.behavior_data.get("avg_duration", 60)
    cancel_rate = prefs.behavior_data.get("cancel_rate", 0.0)
    
    # 2. Adjust tone based on style
    tone = "ngắn gọn, súc tích" if prefs.behavior_data.get("prefers_short") else "thân thiện, chi tiết"

    return f"""
    Bạn là ParkSmart AI Assistant.
    
    USER PROFILE:
    - Thời gian đậu xe trung bình: {avg_duration} phút
    - Tỷ lệ hủy: {cancel_rate:.0%}
    - Phong cách ưa thích: {tone}
    
    NHIỆM VỤ:
    - Giúp người dùng tìm chỗ, đặt chỗ, kiểm tra phương tiện.
    - Luôn kiểm tra tính an toàn trước khi hành động.
    """
```

### 7.2 Memory Service

- **Short-term**: Lưu trong `Conversation.context` (Redis cache).
- **Long-term**: Lưu trong `UserPreferences` (MySQL).
- **Update Rule**: Sau mỗi booking thành công/hủy, cập nhật `behavior_data` async.

---

## VIII. PROACTIVE INTELLIGENCE

### 8.1 Event Rules

| Sự kiện (RabbitMQ) | Điều kiện | Hành động Chatbot |
|-------------------|-----------|-------------------|
| `booking.created` | - | Lưu booking vào context, update behavior |
| `booking.check_in` | Late > 30p | Gửi thông báo: "Bạn quên check-in? Cần hỗ trợ không?" |
| `slot.maintenance` | User booked this slot | "⚠️ Slot A-15 bảo trì đột xuất. Đổi sang A-16 nhé?" |
| `weather.rain` | Parking is outdoor | "Trời sắp mưa 🌧️. Slot bạn đặt ở ngoài trời. Đổi vào trong nhà?" |

---

## IX. CẢI TIẾN KIẾN TRÚC (Critical Improvements)

> [!IMPORTANT]
> Các cải tiến này là **bắt buộc** trước khi đưa lên production. Đây là sự khác biệt giữa chatbot demo vs chatbot thực chiến.

### 🔥 9.1 Intent Service — Tách "Decision + Extract"

**Vấn đề**: `intent_svc.detect()` đang gộp reasoning + extraction → dễ hallucination, khó debug.

**Giải pháp**: Tách thành 3 bước rõ ràng:

```
IntentService
├── classify_intent()      # Gemini reasoning → WHY (lý do chọn intent)
├── extract_entities()     # Schema-driven → WHAT (extract dữ liệu cụ thể)
└── build_decision()       # Merge + Validate → Final IntentDecision
```

```python
# app/application/services/intent.py
class IntentService:
    async def classify_intent(self, message: str, context: dict) -> IntentClassification:
        """Step 1: Gemini reasoning — xác định intent + lý do."""
        # Prompt Gemini chỉ cho classification, KHÔNG extract entity
        # → Giảm hallucination vì LLM chỉ làm 1 việc
        ...

    async def extract_entities(self, message: str, intent: str) -> dict:
        """Step 2: Schema-driven extraction — dựa theo intent schema."""
        # Mỗi intent có entity schema riêng (required + optional)
        # Ví dụ: BOOK_SLOT cần {lot_id, vehicle_id, start_time, duration}
        ...

    async def build_decision(
        self, classification: IntentClassification, entities: dict, context: dict
    ) -> IntentDecision:
        """Step 3: Merge + validate → tính confidence hybrid."""
        entity_completeness = self._calc_entity_completeness(
            classification.intent, entities
        )
        hybrid_confidence = self._calc_hybrid_confidence(
            classification.llm_confidence, entity_completeness, context
        )
        ...
```

**Orchestrator cập nhật**:

```python
# Trước (gộp):
decision = await self.intent_svc.detect(message, context)

# Sau (tách):
classification = await self.intent_svc.classify_intent(message, context)
entities = await self.intent_svc.extract_entities(message, classification.intent)
decision = await self.intent_svc.build_decision(classification, entities, context)
```

> ⟶ Giảm hallucination, dễ debug từng bước, dễ A/B test prompt.

---

### 🔥 9.2 Hybrid Confidence — Không "tin LLM hơi nhiều"

**Vấn đề**: `confidence: float` do LLM trả → rất nguy hiểm khi scale vì LLM có xu hướng overconfident.

**Giải pháp**: Hybrid confidence từ 3 nguồn:

```python
# app/domain/value_objects/confidence.py
class HybridConfidence:
    """Tính confidence từ 3 nguồn, không chỉ LLM."""

    WEIGHTS = {
        "llm": 0.5,
        "entity_completeness": 0.3,
        "context_match": 0.2,
    }

    @classmethod
    def calculate(
        cls,
        llm_confidence: float,
        entity_completeness: float,
        context_match_score: float,
    ) -> float:
        """
        final_confidence =
            0.5 * llm_confidence
          + 0.3 * entity_completeness
          + 0.2 * context_match_score

        Ví dụ:
        - Thiếu entity → entity_completeness thấp → auto tụt confidence
        - Context lệch intent trước → context_match thấp → tụt confidence
        """
        return (
            cls.WEIGHTS["llm"] * llm_confidence
            + cls.WEIGHTS["entity_completeness"] * entity_completeness
            + cls.WEIGHTS["context_match"] * context_match_score
        )

    @staticmethod
    def calc_entity_completeness(intent: str, entities: dict) -> float:
        """Tỷ lệ entity required đã có / tổng required."""
        required = INTENT_ENTITY_SCHEMA.get(intent, {}).get("required", [])
        if not required:
            return 1.0
        found = sum(1 for e in required if e in entities and entities[e])
        return found / len(required)

    @staticmethod
    def calc_context_match(intent: str, context: dict) -> float:
        """Intent hiện tại có hợp lý với conversation flow không?"""
        prev_intent = context.get("last_intent")
        if not prev_intent:
            return 1.0
        # Ví dụ: CHECK_OUT sau CHECK_IN → match cao
        # BOOK_SLOT ngay sau CANCEL_BOOKING → match thấp
        return INTENT_FLOW_SCORES.get((prev_intent, intent), 0.7)
```

> ⟶ Đây là thứ làm chatbot "ít ngu" hơn 80%.

---

### 🔥 9.3 SafetyService — Trả Reason Code, Không Chỉ True/False

**Vấn đề**: `safety_svc.validate()` trả `bool` → FE không biết lý do, logging mù, analytics trống.

**Giải pháp**: Trả `SafetyResult` với reason code + hint:

```python
# app/domain/value_objects/safety.py
from enum import Enum
from pydantic import BaseModel

class SafetyCode(str, Enum):
    OK = "OK"
    SLOT_NOT_AVAILABLE = "SLOT_NOT_AVAILABLE"
    DOUBLE_BOOKING = "DOUBLE_BOOKING"
    OUT_OF_OPERATING_HOURS = "OUT_OF_OPERATING_HOURS"
    VEHICLE_NOT_FOUND = "VEHICLE_NOT_FOUND"
    BOOKING_NOT_FOUND = "BOOKING_NOT_FOUND"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    MAX_ACTIVE_BOOKINGS = "MAX_ACTIVE_BOOKINGS"

class SafetyResult(BaseModel):
    ok: bool
    code: SafetyCode = SafetyCode.OK
    hint: str = ""
    details: dict = {}
```

**Orchestrator cập nhật**:

```python
# Trước:
if not self.safety_svc.validate(decision):
    return await self.response_svc.generate_safety_error(decision)

# Sau:
safety_result = self.safety_svc.validate(decision)
if not safety_result.ok:
    return await self.response_svc.generate_safety_error(
        code=safety_result.code,
        hint=safety_result.hint,
        details=safety_result.details,
    )
```

> ⟶ FE hiển thị lỗi cụ thể, logging rõ ràng, analytics track được nguyên nhân.

---

### 🔥 9.4 Memory Update — Anti-Noise Rules

**Vấn đề**: Không phải hành động nào cũng nên update `behavior_data`. Nếu học bừa, chatbot sẽ hiểu sai user.

**Giải pháp**: Thêm `MemoryFilter` trước khi update:

```python
# app/application/services/memory.py
class MemoryFilter:
    """Lọc noise trước khi update behavior."""

    RULES = {
        "min_booking_duration_minutes": 5,
        "ignore_system_cancels": True,
        "require_conversation_complete": True,
    }

    @classmethod
    def should_update(cls, decision: IntentDecision, action_result: dict, context: dict) -> bool:
        # Rule 1: Booking < 5 phút rồi hủy → không update
        if cls._is_quick_cancel(action_result):
            return False

        # Rule 2: Cancel do system (maintenance, error) → không tính cancel_rate
        if cls._is_system_cancel(action_result):
            return False

        # Rule 3: Conversation chưa hoàn tất → không học
        if not cls._is_conversation_complete(context):
            return False

        return True

    @staticmethod
    def _is_quick_cancel(result: dict) -> bool:
        """Booking tạo < 5 phút rồi bị hủy."""
        if result.get("action") != "cancel":
            return False
        booking_duration = result.get("booking_age_minutes", float("inf"))
        return booking_duration < 5

    @staticmethod
    def _is_system_cancel(result: dict) -> bool:
        """Cancel do hệ thống, không phải do user."""
        return result.get("cancel_source") == "system"

    @staticmethod
    def _is_conversation_complete(context: dict) -> bool:
        """Conversation có kết thúc hợp lệ không."""
        return context.get("conversation_state") in ["completed", "resolved"]
```

**Orchestrator cập nhật**:

```python
# Trước:
BackgroundTasks().add_task(self.memory_svc.update_behavior, decision, action_result)

# Sau:
if MemoryFilter.should_update(decision, action_result, context):
    BackgroundTasks().add_task(self.memory_svc.update_behavior, decision, action_result)
```

> ⟶ Nếu không lọc noise, chatbot sẽ học sai và đề xuất sai cho user.

---

### 🔥 9.5 Proactive Intelligence — Cooldown + Priority

**Vấn đề**: Event-driven chatbot rất dễ spam user → biến assistant thông minh thành annoying bot.

**Giải pháp**: Thêm `ProactivePolicy` với priority, cooldown, suppression:

```python
# app/application/services/proactive.py
from enum import Enum
from datetime import timedelta

class NotificationPriority(str, Enum):
    HIGH = "high"       # Bảo trì đột xuất, booking sắp hết hạn
    MEDIUM = "medium"   # Thời tiết, gợi ý slot
    LOW = "low"         # Tips, parking history insight

class ProactivePolicy:
    """Kiểm soát thông báo proactive — tránh spam."""

    COOLDOWN_WINDOWS = {
        NotificationPriority.HIGH: timedelta(minutes=5),
        NotificationPriority.MEDIUM: timedelta(minutes=30),
        NotificationPriority.LOW: timedelta(hours=4),
    }

    SUPPRESSION_RULES = {
        "user_active_within_minutes": 2,   # User đang chat → không push LOW/MEDIUM
        "max_notifications_per_hour": 3,
        "max_low_per_day": 5,
    }

    @classmethod
    async def should_send(
        cls,
        user_id: str,
        priority: NotificationPriority,
        notification_type: str,
        cache: RedisClient,
    ) -> bool:
        # 1. Check cooldown per (user, type)
        last_sent = await cache.get(f"notif:{user_id}:{notification_type}:last")
        if last_sent and not cls._cooldown_passed(last_sent, priority):
            return False

        # 2. Check suppression — user đang active
        if priority != NotificationPriority.HIGH:
            last_active = await cache.get(f"user:{user_id}:last_active")
            if last_active and cls._user_recently_active(last_active):
                return False

        # 3. Check rate limit per hour
        hourly_count = await cache.get(f"notif:{user_id}:hourly_count")
        if hourly_count and int(hourly_count) >= cls.SUPPRESSION_RULES["max_notifications_per_hour"]:
            return False

        return True
```

**Event Rules cập nhật (bổ sung Priority)**:

| Sự kiện (RabbitMQ) | Priority | Cooldown | Hành động |
|---------------------|----------|----------|-----------|
| `booking.check_in` late > 30p | **HIGH** | 5 min | "Bạn quên check-in?" |
| `slot.maintenance` (user booked) | **HIGH** | 5 min | "⚠️ Slot bảo trì, đổi slot?" |
| `weather.rain` (outdoor slot) | **MEDIUM** | 30 min | "Trời sắp mưa, đổi vào trong?" |
| `parking.insight` (weekly) | **LOW** | 4 hours | "Tuần này bạn đậu trung bình 2h" |

> ⟶ Đây là khác biệt giữa assistant thông minh vs annoying bot.

---

### 🔥 9.6 AI Observability — Log AI-Specific Metrics

**Vấn đề**: Chỉ log API metrics (latency, error rate) là **không đủ** cho AI system. Cần metrics riêng để phát hiện prompt hỏng, model drift.

**Giải pháp**: Thêm `AIMetricsCollector`:

```python
# app/infrastructure/observability/ai_metrics.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AIMetrics:
    """Metrics riêng cho AI pipeline — không chỉ API metrics."""

    # Intent quality
    intent_mismatch_rate: float = 0.0     # User chọn lại intent → prompt hỏng
    clarification_rate: float = 0.0       # Tỷ lệ phải hỏi lại → prompt mơ hồ
    confirmation_rate: float = 0.0        # Tỷ lệ cần confirm → confidence chưa tốt

    # Action quality
    action_fail_after_execute: float = 0.0  # Execute xong nhưng fail → logic domain sai
    user_override_rate: float = 0.0         # User đổi ý sau khi bot gợi ý → bot đoán sai

class AIMetricsCollector:
    """Thu thập và export AI metrics."""

    METRIC_DEFINITIONS = {
        "intent_mismatch_rate": "Phát hiện prompt hỏng — user phải chọn lại intent",
        "clarification_rate": "Prompt quá mơ hồ — cần hỏi clarification quá nhiều",
        "confirmation_rate": "Confidence chưa tốt — cần confirm quá nhiều",
        "action_fail_after_execute": "Logic domain sai — action fail sau khi execute",
        "user_override_rate": "Chatbot đoán sai — user override gợi ý",
    }

    async def record_intent_result(self, decision: IntentDecision, user_feedback: Optional[str] = None):
        """Ghi nhận kết quả intent detection."""
        if user_feedback and user_feedback != decision.primary_intent:
            await self._increment("intent_mismatch_rate")

        if decision.clarification_needed:
            await self._increment("clarification_rate")

    async def record_action_result(self, action: str, success: bool, user_overridden: bool):
        """Ghi nhận kết quả action execution."""
        if not success:
            await self._increment("action_fail_after_execute")
        if user_overridden:
            await self._increment("user_override_rate")

    async def export_dashboard(self) -> dict:
        """Export metrics cho monitoring dashboard (Grafana/Prometheus)."""
        ...
```

**Metrics Dashboard**:

| Metric | Vì sao quan trọng | Ngưỡng cảnh báo |
|--------|-------------------|-----------------|
| `intent_mismatch_rate` | Phát hiện prompt hỏng | > 15% |
| `clarification_rate` | Prompt quá mơ hồ | > 30% |
| `confirmation_rate` | Confidence chưa tốt | > 40% |
| `action_fail_after_execute` | Logic domain sai | > 5% |
| `user_override_rate` | Chatbot đoán sai | > 20% |

> ⟶ Không có observability = bay mù. Đây là nền tảng để liên tục cải thiện chất lượng AI.

---

## X. IMPLEMENTATION ROADMAP

| Phase | Duration | Tasks |
|-------|----------|-------|
| **1. Foundation** | 2 Days | Setup FastAPI, SQLAlchemy 2.0, CamelModel, Redis, Gateway Middleware |
| **2. Pipeline Core** | 3 Days | Implement Orchestrator, Gemini Integration, Intent Graph (tách classify/extract/build) |
| **3. Safety & Action** | 2 Days | Service Client (HTTP), Safety Rules (reason codes), Booking Logic |
| **4. Memory & Pers.** | 2 Days | UserPreferences logic, Personalized Prompts, Behavior Updating + Anti-Noise Filter |
| **5. Proactive** | 2 Days | RabbitMQ Consumer, Event Handlers, Notification Logic + Cooldown/Priority |
| **6. Observability** | 1 Day | AI Metrics Collector, Dashboard Integration (Prometheus/Grafana) |
| **7. Integration** | 2 Days | Connect with Gateway, Test with Frontend, Docker Compose verify |
| **8. Polish** | 1 Day | Error Handling, Logging, Unit Tests, Hybrid Confidence tuning |

**Tổng cộng**: ~15 ngày làm việc.

---

## XI. CHECKLIST FOR AI CODING AGENT

> [!CAUTION]
> **READ CAREFULLY BEFORE CODING**

1.  **FastAPI Only**: Tuyệt đối không dùng Django code.
2.  **CamelModel**: Mọi API Schema phải kế thừa `CamelModel` (`alias_generator=to_camel`).
3.  **SQLAlchemy 2.0**: Dùng `select()`, `session.execute()`, không dùng `query()`.
4.  **Async/Await**: Tất cả I/O (DB, HTTP, LLM) phải là `async`.
5.  **Clean Architecture**: Không import `models` vào `routers`. Router gọi `service`, service gọi `repository/client`.
6.  **Gateway Auth**: Phải dùng `GatewayAuthMiddleware` kiểm tra `X-Gateway-Secret`.
7.  **Intent Service**: PHẢI tách `classify_intent()` → `extract_entities()` → `build_decision()`. Không gộp.
8.  **Hybrid Confidence**: KHÔNG dùng trực tiếp LLM confidence. Phải tính `HybridConfidence.calculate()`.
9.  **Safety Codes**: `SafetyService.validate()` PHẢI trả `SafetyResult` với `code` + `hint`, không trả `bool`.
10. **Memory Filter**: Trước khi update behavior, PHẢI qua `MemoryFilter.should_update()`.
11. **Proactive Policy**: Mọi notification PHẢI qua `ProactivePolicy.should_send()` — có priority + cooldown.
12. **AI Metrics**: Mọi intent/action result PHẢI log qua `AIMetricsCollector`.
