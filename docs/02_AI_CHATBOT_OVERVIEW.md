# 🤖 AI Chatbot — Tổng Quan Dự Án

> **Trạng thái tổng thể:** Code ~95% hoàn thành | Fully functional với Gemini 2.0 Flash
> **Kiến trúc:** Clean Architecture (API → Engine → Application → Domain ← Infrastructure)
> **Service:** `chatbot-service-fastapi/` (FastAPI, Python 3.10+)
> **LLM Provider:** Google Gemini 2.0 Flash (`gemini-2.0-flash`)

---

## 📁 Cấu Trúc File

```
chatbot-service-fastapi/
├── app/
│   ├── main.py                          ✅ FastAPI app, lifespan, routers
│   ├── config.py                        ✅ Settings (DB, Redis, RabbitMQ, Gemini)
│   ├── database.py                      ✅ SQLAlchemy async engine
│   ├── dependencies.py                  ✅ FastAPI dependency injection
│   │
│   ├── engine/
│   │   └── orchestrator.py              ✅ 6-Stage Pipeline Orchestrator (653 lines)
│   │
│   ├── routers/                         ← API Layer
│   │   ├── chat.py                      ✅ POST /chatbot/chat/ (main endpoint)
│   │   ├── conversation.py              ✅ Conversation CRUD
│   │   ├── preferences.py              ✅ User preference CRUD
│   │   ├── notifications.py            ✅ Proactive notifications
│   │   └── actions.py                   ✅ Action log (undo support)
│   │
│   ├── application/                     ← Application Layer (UseCases)
│   │   ├── dto/                         ✅ IntentClassification, EntityExtraction, PipelineContext
│   │   └── services/
│   │       ├── intent_service.py        ✅ 3-step intent pipeline (639 lines)
│   │       ├── safety_service.py        ✅ Safety validation rules
│   │       ├── action_service.py        ✅ Dispatch to microservices + Booking Wizard
│   │       ├── response_service.py      ✅ LLM + Template response gen (598 lines)
│   │       ├── memory_service.py        ✅ Anti-noise memory update
│   │       ├── proactive_service.py     ✅ Proactive notifications with cooldown
│   │       └── observability_service.py ✅ AI metrics collector
│   │
│   ├── domain/                          ← Domain Layer (Pure Logic)
│   │   ├── exceptions.py               ✅ Custom domain errors
│   │   ├── policies/
│   │   │   └── handoff.py              ✅ Human handoff rules
│   │   └── value_objects/
│   │       ├── intent.py               ✅ 15 intents enum
│   │       ├── confidence.py           ✅ Hybrid confidence + gate
│   │       ├── safety_result.py        ✅ 11 safety codes
│   │       ├── ai_metrics.py           ✅ 15 AI metric types
│   │       └── proactive.py            ✅ Notification priority + cooldown
│   │
│   ├── infrastructure/                  ← Infrastructure Layer
│   │   ├── cache/redis.py              ✅ Async Redis cache
│   │   ├── external/service_client.py  ✅ HTTP calls to microservices (466 lines)
│   │   ├── llm/gemini_client.py        ✅ Gemini 2.0 Flash client
│   │   └── messaging/rabbitmq.py       ✅ Async RabbitMQ consumer
│   │
│   ├── models/chatbot.py               ✅ 9 SQLAlchemy models
│   ├── schemas/chatbot.py              ✅ Pydantic schemas (CamelCase)
│   └── middleware/gateway_auth.py      ✅ X-Gateway-Secret validation
│
└── tests/                               ✅ 8 unit test files + 2 E2E tests
```

---

## 🔄 Luồng Xử Lý Tin Nhắn (6-Stage Pipeline)

```
User gửi tin nhắn → POST /chatbot/chat/
│
├── 1. Get/Create Conversation (MySQL)
├── 2. Lưu ChatMessage (user)
├── 3. Build context (state, turns, clarification count)
│
├── 4. ChatbotOrchestrator.process_message()
│   │
│   ├── 🔥 Booking Wizard Check
│   │   └── Nếu wizard đang chạy → xử lý bước tiếp (floor → zone → book)
│   │
│   ├── Confirmation Handling
│   │   └── Nếu turn trước hỏi "có/không" → xử lý yes/no
│   │
│   ├── ┌─────────────────────────────────────────┐
│   │   │ Stage 1: INTENT DETECTION               │
│   │   │  ├─ Context follow-up check              │
│   │   │  ├─ classify_intent() → Gemini API       │
│   │   │  │   └─ Keyword override cho critical     │
│   │   │  │      intents (cancel, check-in/out)    │
│   │   │  ├─ extract_entities() → Schema-driven    │
│   │   │  └─ build_decision() → Hybrid Confidence  │
│   │   │      = 0.5×LLM + 0.3×entity + 0.2×context│
│   │   └─────────────────────────────────────────┘
│   │
│   ├── Handoff Check
│   │   └── frustration > 0.9 OR clarifications ≥ 6 → chuyển người thật
│   │
│   ├── ┌─────────────────────────────────────────┐
│   │   │ Stage 2: CONFIDENCE GATE                 │
│   │   │  ├─ < 0.65 → "clarify" (hỏi thêm)      │
│   │   │  ├─ 0.65–0.85 (high-stakes) → "confirm"  │
│   │   │  └─ ≥ threshold → "execute"              │
│   │   └─────────────────────────────────────────┘
│   │
│   ├── ┌─────────────────────────────────────────┐
│   │   │ Stage 3: SAFETY VALIDATION               │
│   │   │  ├─ Time range check                     │
│   │   │  ├─ Double booking check                 │
│   │   │  ├─ Max bookings (3) check               │
│   │   │  └─ Slot availability check              │
│   │   └─────────────────────────────────────────┘
│   │
│   ├── ┌─────────────────────────────────────────┐
│   │   │ Stage 4: ACTION EXECUTION                │
│   │   │  └─ Dispatch to microservices via HTTP    │
│   │   │     ├─ booking-service (book/cancel/      │
│   │   │     │   check-in/check-out)               │
│   │   │     ├─ parking-service (availability)     │
│   │   │     ├─ vehicle-service (get vehicles)     │
│   │   │     └─ payment-service (pricing)          │
│   │   └─────────────────────────────────────────┘
│   │
│   ├── ┌─────────────────────────────────────────┐
│   │   │ Stage 5: RESPONSE GENERATION             │
│   │   │  ├─ LLM personalized (nếu Gemini ok)     │
│   │   │  └─ Template fallback (rich format)       │
│   │   └─────────────────────────────────────────┘
│   │
│   └── ┌─────────────────────────────────────────┐
│       │ Stage 6: MEMORY UPDATE                    │
│       │  └─ Anti-noise rules:                     │
│       │     ├─ Skip nếu < 2 turns                 │
│       │     ├─ Skip nếu action failed             │
│       │     └─ Skip nếu short booking cancel      │
│       └─────────────────────────────────────────┘
│
├── 5. Lưu ChatMessage (assistant) + metadata
├── 6. Update Conversation context + state
├── 7. Record AI metrics (observability)
└── 8. Return ChatResponse
```

---

## 💬 15 Intents Hỗ Trợ

| Intent               | High Stakes | Hành động           | Chi tiết                 |
| -------------------- | :---------: | ------------------- | ------------------------ |
| `greeting`           |     ❌      | Template response   | "Xin chào!"              |
| `goodbye`            |     ❌      | Template response   | "Tạm biệt!"              |
| `check_availability` |     ❌      | Gọi parking-service | Kiểm tra chỗ trống       |
| `book_slot`          |     ✅      | **3-step Wizard**   | Floor → Zone → Auto-book |
| `rebook_last`        |     ❌      | Auto-rebook         | Đặt lại booking gần nhất |
| `cancel_booking`     |     ✅      | Gọi booking-service | Hủy booking đang active  |
| `check_in`           |     ❌      | Gọi booking-service | Check-in qua chatbot     |
| `check_out`          |     ✅      | Gọi booking-service | Check-out + tính phí     |
| `my_bookings`        |     ❌      | Gọi booking-service | Xem danh sách booking    |
| `current_parking`    |     ❌      | Gọi booking-service | Xem vị trí xe đang đậu   |
| `pricing_info`       |     ❌      | Template response   | Bảng giá                 |
| `help`               |     ❌      | Template response   | Hướng dẫn sử dụng        |
| `small_talk`         |     ❌      | Template response   | Nói chuyện nhẹ           |
| `human_handoff`      |     ❌      | Chuyển người thật   | Khi user yêu cầu         |
| `unknown`            |     ❌      | Fallback            | "Tôi chưa hiểu..."       |

---

## 🗄️ Database Models (9 bảng)

| Model                    | Table                              | Mô tả                        | Status            |
| ------------------------ | ---------------------------------- | ---------------------------- | ----------------- |
| `Conversation`           | `chatbot_conversation`             | Session hội thoại            | ✅ Active         |
| `ChatMessage`            | `chatbot_chatmessage`              | Tin nhắn (user + assistant)  | ✅ Active         |
| `UserPreferences`        | `chatbot_user_preferences`         | Bãi xe/zone/xe yêu thích     | ✅ Active         |
| `UserBehavior`           | `chatbot_user_behavior`            | Thói quen đặt xe             | ⚠️ Partially used |
| `UserCommunicationStyle` | `chatbot_user_communication_style` | Tone/emoji preference        | ❌ Never written  |
| `ConversationSummary`    | `chatbot_conversation_summary`     | AI-generated summaries       | ❌ Never written  |
| `ProactiveNotification`  | `chatbot_proactive_notification`   | Push notification thông minh | ✅ Active         |
| `ActionLog`              | `chatbot_action_log`               | Lịch sử hành động (undo)     | ✅ Active         |
| `AIMetricLog`            | `chatbot_ai_metric_log`            | AI observability metrics     | ✅ Active         |

---

## 🌐 API Endpoints

| Method | Endpoint                                 | Mô tả                    | Status |
| ------ | ---------------------------------------- | ------------------------ | ------ |
| POST   | `/chatbot/chat/`                         | Gửi tin nhắn chính       | ✅     |
| GET    | `/chatbot/chat/quick-actions/`           | Nút quick action         | ✅     |
| POST   | `/chatbot/chat/feedback/`                | Đánh giá (1-5 sao)       | ✅     |
| GET    | `/chatbot/conversations/`                | Danh sách conversations  | ✅     |
| POST   | `/chatbot/conversations/`                | Tạo conversation mới     | ✅     |
| GET    | `/chatbot/conversations/active/`         | Conversation đang active | ✅     |
| GET    | `/chatbot/conversations/{id}/`           | Chi tiết conversation    | ✅     |
| GET    | `/chatbot/conversations/{id}/history/`   | Lịch sử chat             | ✅     |
| GET    | `/chatbot/conversations/history/latest/` | Lịch sử mới nhất         | ✅     |
| GET    | `/chatbot/preferences/`                  | Preferences user         | ✅     |
| PUT    | `/chatbot/preferences/`                  | Cập nhật preferences     | ✅     |
| GET    | `/chatbot/notifications/`                | Proactive notifications  | ✅     |
| POST   | `/chatbot/notifications/{id}/status/`    | Cập nhật trạng thái      | ✅     |
| GET    | `/chatbot/actions/`                      | Action log               | ✅     |
| GET    | `/health/`                               | Health check             | ✅     |

---

## 🖥️ Frontend Integration

### `SupportPage.tsx` (843 lines) — ✅ HOÀN THÀNH

- Full chat UI với message bubbles, loading states
- Quick actions (nút gợi ý)
- Confirmation flow (Xác nhận / Hủy)
- Feedback submission (đánh giá sao)
- Confidence indicators, safety badges
- Map hints, QR code hints
- Offline fallback (local response khi API không available)
- Load chat history on mount

### `chatbot.api.ts` — ✅ HOÀN THÀNH

- Types khớp backend v3.0
- Methods: `sendMessage`, `getQuickActions`, `submitFeedback`, `getConversations`, `getHistory`, `getActiveConversation`, `getPreferences`, `updatePreferences`, `getNotifications`, `updateNotificationStatus`, `getActionLog`

---

## 🏗️ Kiến Trúc Clean Architecture

```
┌─────────────────────────────────────────────────┐
│                  API Layer                        │
│  routers/ (chat, conversation, preferences,       │
│           notifications, actions)                  │
│  → KHÔNG truy cập ORM trực tiếp                   │
│  → CHỈ gọi Engine/Application services             │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│                Engine Layer                        │
│  orchestrator.py — 6-stage pipeline coordinator    │
│  → Gọi các Application services theo thứ tự       │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│             Application Layer                      │
│  services/ (intent, safety, action, response,      │
│            memory, proactive, observability)        │
│  → Định nghĩa UseCases                             │
│  → Dùng Repository interfaces                      │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│               Domain Layer                         │
│  value_objects/ (Intent, Confidence, SafetyResult) │
│  policies/ (handoff rules)                         │
│  exceptions/ (domain errors)                       │
│  → KHÔNG import framework libraries                │
│  → Pure business logic only                        │
└─────────────────────────────────────────────────┘
                    ↑
┌─────────────────────────────────────────────────┐
│           Infrastructure Layer                     │
│  llm/gemini_client.py — Google Gemini 2.0 Flash    │
│  cache/redis.py — Async Redis                      │
│  messaging/rabbitmq.py — RabbitMQ consumer         │
│  external/service_client.py — HTTP to services     │
│  → Implement interfaces                            │
│  → Chứa toàn bộ external I/O                      │
└─────────────────────────────────────────────────┘

Dependency Direction: API → Engine → Application → Domain ← Infrastructure ✅
```

---

## 🧪 Test Coverage

### Unit Tests (8 files)

| File                       | Nội dung                                                        | Status |
| -------------------------- | --------------------------------------------------------------- | ------ |
| `test_smoke.py`            | Health, table names, route prefixes, camelCase                  | ✅     |
| `test_intent.py`           | Intent enum, high-stakes flags, required entities               | ✅     |
| `test_confidence.py`       | Hybrid confidence formula, entity completeness, gate thresholds | ✅     |
| `test_safety_result.py`    | SafetyResult/SafetyCode construction                            | ✅     |
| `test_handoff.py`          | Handoff policy (frustration, clarification, keywords)           | ✅     |
| `test_memory_antinoise.py` | Anti-noise rules                                                | ✅     |
| `test_proactive.py`        | Priority values, cooldown config                                | ✅     |
| `test_ai_metrics.py`       | 15 metric types exist                                           | ✅     |

### E2E Tests (2 files — cần full stack)

| File                        | Nội dung                                                                          |
| --------------------------- | --------------------------------------------------------------------------------- |
| `test_chatbot_e2e.py`       | Multi-turn: greeting → availability → pricing → booking → no-accent               |
| `test_chatbot_lifecycle.py` | Full lifecycle: login → greeting → book → check-in → check-out → cancel → goodbye |

---

## ✅ Đã Hoàn Thành

| Component                     | Version | Chi tiết                                            |
| ----------------------------- | ------- | --------------------------------------------------- |
| 6-stage Orchestrator Pipeline | v3.0    | Intent → Gate → Safety → Action → Response → Memory |
| 3-step Intent Detection       | v2.1    | Classify → Extract → Build Decision                 |
| Hybrid Confidence             | v2.2    | 0.5×LLM + 0.3×entity + 0.2×context                  |
| Safety Validation             | v2.3    | 11 machine-readable error codes                     |
| Memory Anti-noise             | v2.4    | 4 skip rules                                        |
| Proactive Notifications       | v2.5    | RabbitMQ + priority + cooldown                      |
| AI Observability              | v2.6    | 15 metric types + DB logging                        |
| Booking Wizard                | v3.0    | Floor → Zone → Auto-book (multi-step)               |
| Confirmation Flow             | v3.0    | Yes/No handling cho high-stakes                     |
| Context Follow-up             | v3.0    | Merge entities từ clarification trước               |
| Vietnamese Support            | v1.0    | Accent-free normalization, keyword matching         |
| Frontend Chat UI              | v3.0    | Full UI, history, offline fallback                  |
| Docker                        | v1.0    | Containerized + health checks                       |
| Unit Tests                    | v2.6    | 8 files cover domain logic                          |

---

## ❌ Chưa Hoàn Thành / Cần Cải Tiến

### 🔴 Quan Trọng

| #   | Vấn đề                             | Chi tiết                                                                              |
| --- | ---------------------------------- | ------------------------------------------------------------------------------------- |
| 1   | **GEMINI API KEY HARDCODED**       | API key nằm trong source code `config.py`. PHẢI chuyển sang env-only                  |
| 2   | **Không có Alembic migrations**    | `alembic` trong requirements nhưng không có migrations folder. Bảng phải tạo thủ công |
| 3   | **ConversationSummary không dùng** | Model tồn tại nhưng KHÔNG có service nào ghi → dead code                              |

### 🟡 Trung Bình

| #   | Vấn đề                               | Chi tiết                                                                                       |
| --- | ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| 4   | **Gateway default URL sai**          | Go config default `:8000`, actual service chạy `:8008`                                         |
| 5   | **Undo chưa implement**              | ActionLog + router chỉ LIST, không có endpoint UNDO thực sự                                    |
| 6   | **Không publish RabbitMQ events**    | Chatbot consume events nhưng không publish `chatbot.message.sent` / `chatbot.action.completed` |
| 7   | **Redis cache không dùng**           | `redis.py` có methods nhưng orchestrator KHÔNG gọi → luôn đọc MySQL                            |
| 8   | **Không rate limiting**              | Endpoint `/chatbot/chat/` không giới hạn request/second                                        |
| 9   | **UserBehavior dùng một phần**       | Chỉ update `booking_count`, `total_spend`, `preferred_lot_id`. Time-related fields KHÔNG ghi   |
| 10  | **UserCommunicationStyle không ghi** | Model tồn tại, KHÔNG có logic learn style over time                                            |

### 🟢 Nhỏ

| #   | Vấn đề                           | Chi tiết                                                                     |
| --- | -------------------------------- | ---------------------------------------------------------------------------- |
| 11  | **Inline imports trong chat.py** | Import service trong endpoint function thay vì DI                            |
| 12  | **RabbitMQ event key mismatch**  | Consumer listens `booking.checked_in` nhưng builder dùng `booking.checkedin` |
| 13  | **E2E tests cần full stack**     | Không chạy được trong CI mà không có docker-compose                          |

---

## 📊 Thống Kê Code

| Metric                  | Giá trị |
| ----------------------- | ------- |
| Tổng dòng code Python   | ~4,500+ |
| Số routers              | 5       |
| Số application services | 7       |
| Số domain value objects | 5       |
| Số database models      | 9       |
| Số unit test files      | 8       |
| Số E2E test files       | 2       |
| Số intents              | 15      |
| Số safety codes         | 11      |
| Số AI metric types      | 15      |

---

## 🗺️ Roadmap Cải Tiến

```
Priority 1 (Security):
  └─ Move Gemini API key to .env only

Priority 2 (Data Integrity):
  ├─ Setup Alembic migrations
  └─ Fix RabbitMQ event key mismatch

Priority 3 (Performance):
  ├─ Enable Redis caching for conversation context
  └─ Add rate limiting to /chatbot/chat/

Priority 4 (Features):
  ├─ Implement actual Undo functionality
  ├─ Populate UserBehavior + CommunicationStyle
  ├─ Publish chatbot events to RabbitMQ
  └─ Generate ConversationSummary after N turns
```
