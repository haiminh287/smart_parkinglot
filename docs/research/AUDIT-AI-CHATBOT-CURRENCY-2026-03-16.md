# Research Report: Audit AI / Chatbot / Currency Detection

**Task:** Full Codebase Audit — AI & Chatbot Feature  
**Date:** 2026-03-16  
**Type:** Codebase Audit (Mixed — Internal + External docs cross-check)  
**Scope:** `ai-service-fastapi/`, `chatbot-service-fastapi/`, `spotlove-ai/src/`

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Chatbot**: Code **~95% hoàn thành**, fully functional với Gemini 2.0 Flash. Pipeline 6-stage + 3-step intent hoạt động tốt. Rủi ro chính: `GEMINI_API_KEY` không validate → silent fallback sang keyword-only khi chưa set.
> 2. **Currency Detection**: Code **~85% hoàn thành** nhưng **0% có model được train** — toàn bộ ML models đều MISSING. Stage 0 (preprocessing) và Stage 2A (color HSV) hoạt động thật sự. Stage 1 (YOLOv8) và Stage 2B (MobileNetV3) chạy **fallback/stub mode**.
> 3. **Gotcha lớn nhất**: `CashSessionManager` dùng **in-memory dict** (không phải Redis) → **mất session khi restart service**. Trong production đây là data loss bug.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

#### AI Service (`backend-microservices/ai-service-fastapi/`)

| File | Mục đích | Relevance | Có thể tái dụng? |
|------|----------|-----------|-----------------|
| `app/main.py` | FastAPI app, lifespan, camera monitor | High | Yes — pattern lifespan |
| `app/config.py` | Settings: DB, media dirs, model paths | High | Cảnh báo: hardcoded defaults |
| `app/engine/pipeline.py` | **BanknoteRecognitionPipeline** — orchestrator 4-stage | High | Yes — pattern chính |
| `app/engine/preprocessing.py` | Stage 0: blur/exposure check + white balance | High | Yes — độc lập OpenCV |
| `app/engine/detector.py` | Stage 1: YOLOv8n banknote bbox detection | High | Stub khi không có model |
| `app/engine/color_classifier.py` | Stage 2A: HSV histogram → denomination | High | Yes — functional không cần ML |
| `app/engine/ai_classifier.py` | Stage 2B: MobileNetV3-Large fallback | High | Stub khi không có `.pth` |
| `app/engine/cash_session.py` | In-memory cash payment session tracking | High | ⚠️ Cần migrate sang Redis |
| `app/ml/inference/cash_recognition.py` | ResNet50 inference engine | High | Standalone, khác pipeline chính |
| `app/ml/training/train_cash_recognition.py` | ResNet50 training pipeline | Med | Script, không dùng trong runtime |
| `app/ml/banknote/train_classifier.py` | EfficientNetV2-S bank-grade trainer | Med | Script only |
| `app/ml/banknote/train_security.py` | Siamese + OneClass SVM (counterfeit) | Med | Script only |
| `app/routers/detection.py` | Endpoints: `/ai/detect/banknote/`, `/ai/detect/cash/`, `/ai/detect/license-plate/` | High | API layer |
| `app/routers/esp32.py` | Endpoint: `/ai/parking/esp32/cash-payment/` | High | Cash payment flow |
| `app/routers/training.py` | Endpoints: trigger training background task | Med | — |
| `tests/test_pipeline.py` | Unit tests pipeline logic | High | Pattern tốt cho tester |
| `tests/test_api_banknote.py` | API endpoint tests | High | Pattern tốt |
| `tests/test_ai_classifier.py` | AI classifier unit tests | High | — |
| `tests/test_color_classifier.py` | Color classifier unit tests | High | — |
| `tests/test_smoke.py` | Health + tablename + camelCase tests | High | — |

#### Chatbot Service (`backend-microservices/chatbot-service-fastapi/`)

| File | Mục đích | Relevance | Có thể tái dụng? |
|------|----------|-----------|-----------------|
| `app/main.py` | FastAPI v3.0, lifespan (Redis + RabbitMQ) | High | Pattern lifespan |
| `app/config.py` | Settings: Gemini, Redis, RabbitMQ, services | High | — |
| `app/engine/orchestrator.py` | **ChatbotOrchestrator** (653 lines) — 6-stage pipeline | High | Backbone |
| `app/application/services/intent_service.py` | **IntentService** (639 lines) — 3-step: classify → extract → build | High | Core |
| `app/application/services/response_service.py` | LLM + template response generation (598 lines) | High | Core |
| `app/application/services/action_service.py` | Dispatch actions → microservices + Booking Wizard | High | Core |
| `app/application/services/memory_service.py` | Anti-noise memory update | Med | — |
| `app/application/services/proactive_service.py` | Proactive notifications + cooldown | Med | — |
| `app/application/services/safety_service.py` | Safety validation (11 codes) | High | — |
| `app/application/services/observability_service.py` | AI metric collection | Med | — |
| `app/infrastructure/llm/gemini_client.py` | Gemini 2.0 Flash wrapper | High | Pattern |
| `app/infrastructure/external/service_client.py` | HTTP calls to all microservices (466 lines) | High | — |
| `app/infrastructure/cache/redis.py` | Async Redis | Med | — |
| `app/infrastructure/messaging/rabbitmq.py` | Async RabbitMQ consumer | Med | — |
| `app/domain/value_objects/intent.py` | 15 intents enum + required entities | High | Reference cho Tester |
| `app/domain/value_objects/confidence.py` | Hybrid confidence formula | High | — |
| `app/routers/chat.py` | `POST /chatbot/chat/` — main endpoint | High | — |
| `app/models/chatbot.py` | 9 SQLAlchemy models | High | — |
| `tests/test_smoke.py` | **File đang mở** — health, tablename, router prefix, endpoints | High | — |
| `tests/test_intent.py` | Intent service unit tests | High | — |
| `tests/test_chatbot_comprehensive.py` | Comprehensive chatbot tests | High | — |

#### Frontend (`spotlove-ai/src/`)

| File | Mục đích | Relevance |
|------|----------|-----------|
| `pages/BanknoteDetectionPage.tsx` | Upload ảnh → AI detect denomination UI | High |
| `pages/KioskPage.tsx` | Kiosk: check-in/out + cash payment flow | High |
| `pages/SupportPage.tsx` (843 lines) | Full chat UI | High |
| `services/api/chatbot.api.ts` | Chatbot API client — types khớp v3.0 | High |
| `services/api/ai.api.ts` | AI API client — detectBanknote, esp32CashPayment | High |
| `services/api/endpoints.ts` | Endpoint constants | Med |
| `test/ai-api.test.ts` | FE test AI API | Med |
| `test/chatbot-api.test.ts` | FE test chatbot API | Med |

### 2.2 Pattern Đang Dùng

#### Currency Detection Pipeline Pattern

```python
# Source: app/engine/pipeline.py
class BanknoteRecognitionPipeline:
    def process(self, img: np.ndarray) -> PipelineResult:
        # Stage 0: preprocess → quality check
        # Stage 1: detect banknote bbox (YOLO / full-image fallback)
        # Stage 2A: color HSV classification
        # meets_threshold? → ACCEPT (method=color)
        # else → Stage 2B: MobileNetV3 (or stub)
        # conf > 0.3 → ACCEPT, else LOW_CONFIDENCE
```

#### Chatbot Orchestrator Pattern

```python
# Source: app/engine/orchestrator.py
class ChatbotOrchestrator:
    async def process_message(self, message: str, context: dict) -> dict:
        # 1. Booking Wizard check (multi-step floor→zone→book)
        # 2. Confirmation handling (yes/no)
        # 3. Stage 1: IntentService.detect() [LLM classify + extract + build]
        # 4. HandoffPolicy check (frustration > 0.9 OR clarifications >= 6)
        # 5. Confidence Gate: < 0.65 → clarify, ≥ 0.65 → continue
        # 6. ActionService.dispatch() → call microservices
        # 7. ResponseService.generate_response()
```

#### Gemini Client Pattern

```python
# Source: app/infrastructure/llm/gemini_client.py
# Messages format: system_prompt → {"role":"user","parts":[sys]},
#                                  {"role":"model","parts":["Đã hiểu."]}
#                  then user_prompt → {"role":"user","parts":[msg]}
# Config: temperature=0.3, top_p=0.9, max_output_tokens=1024
```

#### Hybrid Confidence Formula

```python
# Source: app/domain/value_objects/confidence.py
# hybrid = 0.5 * llm_confidence + 0.3 * entity_completeness + 0.2 * context_match
# Gate: < 0.65 → CLARIFY; < 0.80 → CONFIRM (high-stakes); ≥ 0.80 → EXECUTE
```

### 2.3 Potential Conflicts

- `app/config.py` (ai-service) có **hardcoded defaults** cho `DB_USER="root"`, `DB_PASSWORD="rootpassword"`, `GATEWAY_SECRET="gateway-internal-secret-key"` — không dùng `Field(...)` như chatbot-service. Nếu `.env` không override → security risk.
- `detect_cash()` endpoint (`/ai/detect/cash/`) và `detect_banknote()` (`/ai/detect/banknote/`) là 2 pipeline KHÁC NHAU. `detect_cash` dùng ResNet50, `detect_banknote` dùng Hybrid MVP. FE dùng `detectBanknote()` → pipeline chính. Endpoint `/ai/detect/cash/` ít được test hơn.
- `CashSessionManager` singleton là in-memory. Nếu ai-service restart giữa session thanh toán → **mất toàn bộ tổng tiền đã nhét**, barrier không mở nữa.

### 2.4 Dependencies Đã Có

**ai-service-fastapi:**
- `ultralytics==8.4.18` — YOLOv8
- `torch==1.13.1+cu116` + `torchvision==0.14.1+cu116` — PyTorch (CUDA 11.6)
- `opencv-python==4.10.0.84` + `opencv-python-headless==4.10.0.84` — ⚠️ **DUPLICATE** — hai package này conflict lẫn nhau
- `easyocr==1.7.2` — OCR cho biển số
- `timm==1.0.25` — Model zoo (EfficientNetV2)
- `numpy==1.26.4`

**chatbot-service-fastapi:**
- `google-generativeai==0.8.0` — Gemini SDK
- `redis==5.0.8` — Redis async client
- `aio-pika==9.4.0` — RabbitMQ async

---

## 3. External Research

### 3.1 Model File Status (Critical)

Tất cả model files **KHÔNG TỒN TẠI** trong codebase:

| Model File | Path | Status | Cần cho |
|------------|------|--------|---------|
| `banknote_yolov8n.pt` | `ml/models/banknote_yolov8n.pt` | ❌ MISSING | Stage 1 detection |
| `banknote_mobilenetv3.pth` | `ml/models/banknote_mobilenetv3.pth` | ❌ MISSING | Stage 2B AI fallback |
| `cash_recognition_best.pth` | `ml/models/cash_recognition_best.pth` | ❌ MISSING | `/ai/detect/cash/` endpoint |
| `license-plate-finetune-v1m.pt` | `app/models/license-plate-finetune-v1m.pt` | ✅ EXISTS | License plate detection |

**Consequence hiện tại:**
- Stage 1 → full-image fallback (không crop được banknote, toàn ảnh đưa vào classifier)
- Stage 2B → `_stub_classify()` cho confidence cố định 0.50 dựa trên hue đơn giản
- `/ai/detect/cash/` → model not found → 500 error hoặc fallback tùy implementation

### 3.2 Chatbot Intent Coverage

15 intents được định nghĩa trong `app/domain/value_objects/intent.py`:

```
book_slot, cancel_booking, check_in, check_out, check_status,
get_pricing, find_parking, check_availability, check_payment,
check_vehicles, get_directions, check_notifications, greeting,
help, handoff, unknown
```

Fallback: keyword-based detection khi Gemini không available (e.g., `GEMINI_API_KEY` trống).

### 3.3 Frontend ↔ Backend Alignment

| Feature | FE Component | BE Endpoint | Alignment |
|---------|-------------|-------------|-----------|
| Banknote detect (web) | `BanknoteDetectionPage.tsx` | `POST /ai/detect/banknote/` | ✅ Khớp |
| Kiosk cash payment | `KioskPage.tsx` | `POST /ai/parking/esp32/cash-payment/` | ✅ Khớp |
| Chatbot UI | `SupportPage.tsx` | `POST /chatbot/chat/` | ✅ Khớp |
| Quick actions | `SupportPage.tsx` | `GET /chatbot/quick-actions/` | ✅ Khớp |
| Chat history | `SupportPage.tsx` | `GET /chatbot/conversations/{id}/history/` | ✅ Khớp |

**Response format**: AI service trả `camelCase` (Pydantic `by_alias=True`). Chatbot v3.0 trả camelCase. FE types align.

---

## 4. So Sánh Phương Án (N/A cho audit này)

Không áp dụng — đây là audit, không phải design decision.

---

## 5. ⚠️ Gotchas & Known Issues

- [ ] **[BLOCKER]** `CashSessionManager` dùng **in-memory dict** không phải Redis.  
  → Service restart = mất tất cả cash payment sessions đang chạy. Booking_id tích lũy mất, tiền đã nhét mất, barrier không mở.  
  → File: `app/engine/cash_session.py` — comment trong code đã ghi nhận: _"In production, this should use Redis"_.

- [ ] **[BLOCKER]** **Không có training data** cho bất kỳ banknote ML model nào.  
  → `docs/01_AI_CASH_DETECTION_OVERVIEW.md` xác nhận: _"Data: 0%"_.  
  → Training scripts có nhưng không chạy được nếu không có dataset.  
  → Hướng dẫn thu thập data: `ai-service-fastapi/CASH_DATA_COLLECTION_GUIDE.md`.

- [ ] **[BLOCKER]** **Không có trained models** (`banknote_yolov8n.pt`, `banknote_mobilenetv3.pth`, `cash_recognition_best.pth`).  
  → Mọi ML inference đang chạy **stub/fallback** → kết quả là guesswork từ hue màu sắc.

- [ ] **[WARNING]** `GEMINI_API_KEY` defaults to empty string `""`.  
  → Không có validation `Field(...)`. Nếu key không set trong `.env`, `get_llm_client()` trả `None` silently.  
  → Orchestrator sẽ fallback sang keyword-only intent detection — không báo lỗi cho user.  
  → File: `app/config.py:22`, `app/main.py:34`.

- [ ] **[WARNING]** `opencv-python==4.10.0.84` và `opencv-python-headless==4.10.0.84` cùng trong `requirements.txt` của ai-service.  
  → Hai package này conflict với nhau — chỉ nên dùng một. Headless là đúng cho server (không cần display).

- [ ] **[WARNING]** `torch==1.13.1+cu116` (CUDA 11.6) — phiên bản cũ (2022).  
  → Không tương thích với `timm==1.0.25` mới nhất (yêu cầu PyTorch >= 2.0).  
  → `train_classifier.py` dùng EfficientNetV2 từ `timm` → có thể fail lúc training.

- [ ] **[WARNING]** `detect_cash()` endpoint tạo mới `CashRecognitionInference` instance **mỗi request**.  
  → Model load lên mỗi lần = penalty khởi động PyTorch mỗi request.  
  → File: `app/routers/detection.py` — khác với `detect_banknote()` dùng singleton.

- [ ] **[WARNING]** `ai-service/app/config.py` hardcode defaults: `DB_USER="root"`, `DB_PASSWORD="rootpassword"`, `GATEWAY_SECRET="gateway-internal-secret-key"`.  
  → Chatbot service dùng `Field(...)` để enforce — ai-service thì không. Security gap.

- [ ] **[NOTE]** `test_smoke.py` (chatbot) dùng `@pytest.mark.anyio` nhưng fixture `client` dùng `async def` không có `@pytest.mark.anyio`.  
  → `pytest.ini` phải có `asyncio_mode = auto` hoặc `anyio_mode = auto`.

- [ ] **[NOTE]** `KioskPage.tsx` flow: `detectBanknote()` → nếu `decision === "accept"` mới gọi `esp32CashPayment()`.  
  → Với stub pipeline, confidence = 0.50 > threshold 0.30 → `PipelineDecision.ACCEPT` vẫn trả → flow hoạt động về mặt code nhưng denomination là **guesswork**.

- [ ] **[NOTE]** `chatbot-service/requirements.txt` có version mismatch: `fastapi==0.134.0` nhưng `starlette==0.49.1`.  
  → FastAPI 0.134 yêu cầu Starlette 0.40+ — cần verify compatibility.

---

## 6. Code Examples từ Official Docs (Extracted từ Codebase)

### Currency Detection — Full Request/Response

```bash
# POST /ai/detect/banknote/?mode=full
# Request: multipart/form-data với field "image"
# Response JSON:
{
  "decision": "accept" | "low_confidence" | "no_banknote" | "bad_quality" | "error",
  "denomination": "100000",        # VND denomination string, null nếu không detect
  "confidence": 0.8750,
  "method": "color" | "ai_fallback" | "none",
  "quality": { "blurScore": 120.5, "exposureScore": 128.3, "status": "ok", "message": "" },
  "detection": { "found": true, "confidence": 0.82, "message": "" },
  "allProbabilities": { "100000": 0.875, "50000": 0.05, ... },
  "stagesExecuted": ["preprocessing", "detection", "color"],
  "processingTimeMs": 45.2,
  "pipelineVersion": "hybrid-mvp-v1"
}
```

### Chatbot — Request/Response

```bash
# POST /chatbot/chat/
# Headers: X-Gateway-Secret, X-User-ID (set bởi gateway)
# Request:
{ "message": "Đặt chỗ A1 ngày mai 2 tiếng", "conversationId": "uuid-optional" }

# Response:
{
  "response": "Bạn muốn đặt chỗ A1...",
  "intent": "book_slot",
  "entities": { "slotCode": "A1", "duration": 2 },
  "confidence": 0.82,
  "confidenceBreakdown": { "llm": 0.9, "entityCompleteness": 0.75, "contextMatch": 0.6 },
  "clarificationNeeded": false,
  "confirmationNeeded": true,
  "suggestions": ["Xác nhận", "Hủy"],
  "conversationId": "...",
  "messageId": "..."
}
```

---

## 7. Checklist cho Implementer

### Ưu tiên cao (Blockers)

- [ ] **[CashSession → Redis]** Migrate `CashSessionManager` từ in-memory sang Redis.  
  → Reference: `app/infrastructure/cache/redis.py` (chatbot-service có pattern Redis async).  
  → Key: `cash_session:{booking_id}`, TTL 30 phút.

- [ ] **[Data Collection]** Thu thập dataset tiền mặt theo hướng dẫn:  
  → Script: `ai-service-fastapi/capture_data.py`  
  → Guide: `ai-service-fastapi/CASH_DATA_COLLECTION_GUIDE.md`  
  → Structure: `datasets/banknote_v1/{1000,2000,5000,...,500000}/img*.jpg`

- [ ] **[Model Training]** Sau khi có data:
  ```bash
  # Train ResNet50 (simple)
  python -m app.ml.training.train_cash_recognition \
    --train-dir ./ml/datasets/banknote_v1/real \
    --val-dir ./ml/datasets/banknote_v1_val/real \
    --output-dir ./ml/models --epochs 50 --batch-size 32
  # Output: ml/models/cash_recognition_best.pth
  
  # Train MobileNetV3 for Stage 2B
  # train_classifier.py hoặc custom script
  # Output: ml/models/banknote_mobilenetv3.pth
  ```

- [ ] **[GEMINI_API_KEY validation]** Thêm `Field(min_length=1)` vào `GEMINI_API_KEY` trong `config.py` nếu muốn mandatory, hoặc log rõ warning khi empty.

### Ưu tiên trung (Warnings)

- [ ] **[OpenCV duplicate]** Xóa `opencv-python==4.10.0.84` khỏi `requirements.txt` — chỉ giữ `opencv-python-headless`.
- [ ] **[detect_cash singleton]** Đổi `detect_cash()` dùng singleton pattern như `detect_banknote()` (`_get_pipeline()`).
- [ ] **[ai config security]** Đổi defaults trong `ai-service/app/config.py` sang `Field(...)` mandatory hoặc ít nhất không có production credentials.
- [ ] **[PyTorch upgrade]** Upgrade từ `torch==1.13.1+cu116` lên `torch>=2.0` để tương thích `timm==1.0.25`.

### Thông tin cho Tester

- [ ] **Test currency**: Dùng ảnh tiền VND thật (xem `test_pipeline.py` pattern — make_green_banknote(), make_blue_banknote()).
- [ ] **Test chatbot**: Xem `tests/test_intent.py` và `test_chatbot_comprehensive.py` để biết pattern mock.
- [ ] **Test smoke hiện tại** (`test_smoke.py` chatbot): Covers health, 9 tablenames, camelCase output, 5 router prefixes, 2 endpoint registrations.
- [ ] **Chưa có test** cho: `cash_session.py`, `detect_cash()` endpoint, Gemini timeout/retry, RabbitMQ consumer failure.

---

## 8. Trạng Thái Tổng Hợp

### Currency / Money Detection

| Component | Status | Detail |
|-----------|--------|--------|
| Stage 0: Preprocessing | ✅ **IMPLEMENTED** | Pure OpenCV, no model needed |
| Stage 1: YOLOv8 Detection | ⚡ **STUB** | Code OK, model file MISSING |
| Stage 2A: Color HSV | ✅ **IMPLEMENTED** | Functional, SAFE/DANGER groups |
| Stage 2B: MobileNetV3 | ⚡ **STUB** | Code OK, model file MISSING |
| ResNet50 (`/ai/detect/cash/`) | ⚡ **STUB** | Code OK, model file MISSING |
| Training Pipeline | ✅ Code ready | Data = 0%, needs dataset |
| CashSessionManager | ⚠️ **IN-MEMORY** | Works but loses data on restart |
| ESP32 Cash Payment Endpoint | ✅ Code OK | Relies on stub recognition |
| FE BanknoteDetectionPage | ✅ **COMPLETE** | — |
| FE KioskPage cash flow | ✅ **COMPLETE** | Flow logic OK, accuracy guesswork |

### Chatbot AI

| Component | Status | Detail |
|-----------|--------|--------|
| LLM Provider | ✅ **Gemini 2.0 Flash** | `gemini-2.0-flash`, temp=0.3 |
| Intent Detection (3-step) | ✅ **IMPLEMENTED** | classify → extract → build |
| 15 Intents | ✅ **IMPLEMENTED** | Full parking domain coverage |
| Hybrid Confidence | ✅ **IMPLEMENTED** | 0.5×LLM + 0.3×entity + 0.2×ctx |
| Safety Validation (11 codes) | ✅ **IMPLEMENTED** | — |
| Booking Wizard | ✅ **IMPLEMENTED** | Multi-step floor→zone→slot |
| Memory anti-noise | ✅ **IMPLEMENTED** | — |
| Proactive notifications | ✅ **IMPLEMENTED** | RabbitMQ events |
| AI Observability metrics | ✅ **IMPLEMENTED** | 15 metric types |
| Redis cache | ✅ **IMPLEMENTED** | Session memory |
| FE SupportPage.tsx | ✅ **COMPLETE** | 843 lines |
| FE chatbot.api.ts | ✅ **COMPLETE** | Aligned v3.0 |
| GEMINI_API_KEY required | ⚠️ **WARNING** | Defaults to empty, silent fallback |

---

## 9. Nguồn

| # | File/URL | Mô tả | Ngày đọc |
|---|----------|-------|---------|
| 1 | `docs/01_AI_CASH_DETECTION_OVERVIEW.md` | Overview currency detection, pipeline diagram, status | 2026-03-16 |
| 2 | `docs/02_AI_CHATBOT_OVERVIEW.md` | Overview chatbot, 6-stage pipeline, FE integration | 2026-03-16 |
| 3 | `ai-service-fastapi/app/engine/pipeline.py` | BanknoteRecognitionPipeline source | 2026-03-16 |
| 4 | `ai-service-fastapi/app/engine/ai_classifier.py` | MobileNetV3 + stub logic | 2026-03-16 |
| 5 | `ai-service-fastapi/app/engine/color_classifier.py` | HSV denomination map | 2026-03-16 |
| 6 | `ai-service-fastapi/app/engine/cash_session.py` | CashSessionManager | 2026-03-16 |
| 7 | `ai-service-fastapi/app/routers/detection.py` | API endpoints | 2026-03-16 |
| 8 | `chatbot-service-fastapi/app/infrastructure/llm/gemini_client.py` | Gemini wrapper | 2026-03-16 |
| 9 | `chatbot-service-fastapi/app/application/services/intent_service.py` | IntentService 3-step | 2026-03-16 |
| 10 | `chatbot-service-fastapi/app/engine/orchestrator.py` | Orchestrator 6-stage | 2026-03-16 |
| 11 | `chatbot-service-fastapi/tests/test_smoke.py` | Test smoke hiện tại | 2026-03-16 |
| 12 | `spotlove-ai/src/pages/BanknoteDetectionPage.tsx` | FE detection UI | 2026-03-16 |
| 13 | `spotlove-ai/src/pages/KioskPage.tsx` | FE kiosk cash flow | 2026-03-16 |
| 14 | `spotlove-ai/src/services/api/chatbot.api.ts` | FE chatbot API types | 2026-03-16 |
| 15 | `spotlove-ai/src/services/api/ai.api.ts` | FE AI API types | 2026-03-16 |
| 16 | `PARKING_SYSTEM_PLAN.md` (lines 709-741) | Cash payment flow plan, known gaps | 2026-03-16 |
