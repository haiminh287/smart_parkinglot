# Research Report: Local-Run Prerequisites cho QA AI (No Docker)

**Task:** ISSUE-SECURITY-BLOCKERS-2026-03-13  
**Date:** 2026-03-16  
**Type:** Codebase

---

## 1. TL;DR — đọc nhanh

1. Có thể chạy QA local-only cho `chatbot health`, `banknote/currency detection`, và `parking occupancy detection` mà không cần Docker.
2. `chatbot` cần env fail-fast tối thiểu (`DB_USER`, `DB_PASSWORD`, `GATEWAY_SECRET`) ngay cả khi chỉ chạy smoke/health.
3. Blocker lớn nhất là mismatch Python baseline giữa service (`chatbot` Dockerfile 3.11, `ai-service` Dockerfile 3.10) và phụ thuộc ML nặng của `ai-service`.

---

## 2. Phân tích codebase hiện tại

### 2.1 Files/modules liên quan

| File | Mục đích | Relevance | Có thể tái dụng? |
| --- | --- | --- | --- |
| `backend-microservices/chatbot-service-fastapi/app/config.py` | Env fail-fast cho chatbot | High | Yes |
| `backend-microservices/chatbot-service-fastapi/app/main.py` | Lifespan + health + middleware | High | Yes |
| `backend-microservices/chatbot-service-fastapi/tests/test_smoke.py` | Smoke local cho chatbot | High | Yes |
| `backend-microservices/chatbot-service-fastapi/qa_probe_health.py` | Probe health local nhanh | High | Yes |
| `backend-microservices/ai-service-fastapi/app/config.py` | Env mặc định AI service | High | Yes |
| `backend-microservices/ai-service-fastapi/.env.example` | Template env local | High | Yes |
| `backend-microservices/ai-service-fastapi/.env.local` | Env local đã tune cho host | High | Yes |
| `backend-microservices/ai-service-fastapi/run_local.bat` | Local startup + preflight model check | High | Yes |
| `backend-microservices/ai-service-fastapi/app/main.py` | Lifespan AI + monitor worker | High | Yes |
| `backend-microservices/ai-service-fastapi/app/routers/detection.py` | Currency/banknote/license-plate endpoints | High | Yes |
| `backend-microservices/ai-service-fastapi/app/routers/parking.py` | Parking scan/check-in/out + detect-occupancy | High | Yes |
| `backend-microservices/ai-service-fastapi/app/engine/slot_detection.py` | YOLO parking + OpenCV fallback | High | Yes |
| `backend-microservices/ai-service-fastapi/tests/test_smoke.py` | AI smoke local tối thiểu | High | Yes |
| `backend-microservices/ai-service-fastapi/tests/test_ai_comprehensive.py` | Phân loại test cần DB/camera hay không | High | Yes |
| `backend-microservices/ai-service-fastapi/tests/test_api_banknote.py` | API banknote có thể mock DB | High | Yes |
| `backend-microservices/ai-service-fastapi/tests/test_detector.py` | Detector fallback không cần model thật | High | Yes |
| `backend-microservices/ai-service-fastapi/tests/test_ai_classifier.py` | Classifier stub mode không cần model thật | High | Yes |
| `backend-microservices/ai-service-fastapi/qa_probe_occupancy.py` | Probe occupancy local nhanh | High | Yes |
| `docs/testing/backend-smoke-env-retest-2026-03-14.txt` | Bằng chứng smoke trên Windows/Python 3.10.5 | High | Yes |

### 2.2 Pattern đang dùng (facts)

- Chatbot env fail-fast:
  - `DB_USER`, `DB_PASSWORD`, `GATEWAY_SECRET` là `Field(..., min_length=1)`.
- Chatbot DB được tạo qua SQLAlchemy sync engine và hầu hết router dùng `Depends(get_db)`.
- AI service có fallback rõ:
  - Slot detection: nếu YOLO parking model không load được thì fallback OpenCV.
  - Banknote detector/classifier có test cho fallback hoặc stub mode.
- Một số endpoint AI bắt buộc DB (metrics/predictions/versions; detect cash/license-plate ghi log DB), một số endpoint có thể chạy không DB (health, camera list, detect-occupancy).

### 2.3 Potential conflicts

- Python version conflict trong repo:
  - `chatbot-service-fastapi/Dockerfile` dùng Python 3.11.
  - `ai-service-fastapi/Dockerfile` dùng Python 3.10.
  - Artifact test gần nhất cho chatbot PASS trên Python 3.10.5.
- `ai-service` startup luôn bật background camera monitor trong lifespan; worker này gọi parking/realtime service qua HTTP (không crash cứng, nhưng sinh warning/log khi thiếu sibling services).

### 2.4 Dependencies đã có (không cần thêm mới để research)

- Chatbot: FastAPI, SQLAlchemy, PyMySQL, pytest, redis, aio-pika, google-generativeai.
- AI service: FastAPI, SQLAlchemy, OpenCV, NumPy, Torch, Ultralytics, EasyOCR, pytest-asyncio.

---

## 3. Local prerequisites checklist (QA local-only, no Docker)

## 3.1 Python version

- [ ] Tối thiểu thực dụng để cover cả 2 service local: **Python 3.10.x** (đã có evidence PASS smoke chatbot trên 3.10.5; AI Dockerfile cũng pin 3.10).
- [ ] Nếu chạy chatbot độc lập theo Docker parity: Python 3.11 vẫn hợp lệ.
- [ ] Khuyến nghị QA local nhanh: tạo 2 venv riêng theo service, ưu tiên 3.10.x cho AI.

## 3.2 Env vars tối thiểu

### Chatbot (`backend-microservices/chatbot-service-fastapi`)

- [ ] `DB_USER` (bắt buộc)
- [ ] `DB_PASSWORD` (bắt buộc)
- [ ] `GATEWAY_SECRET` (bắt buộc)
- [ ] Khuyến nghị thêm nếu không override mặc định:
  - `DB_HOST` (default `localhost`)
  - `DB_PORT` (default `3307`)
  - `DB_NAME` (default `parksmartdb`)

Ghi chú: service này **không có `.env.example` riêng**; có thể dùng `backend-microservices/.env.example` làm baseline rồi set riêng cho chatbot.

### AI service (`backend-microservices/ai-service-fastapi`)

Theo `.env.local` + `run_local.bat`:

- [ ] `DB_HOST`
- [ ] `DB_PORT`
- [ ] `DB_NAME`
- [ ] `DB_USER`
- [ ] `DB_PASSWORD`
- [ ] `GATEWAY_SECRET`
- [ ] `MEDIA_ROOT`
- [ ] `ML_MODELS_DIR`
- [ ] `PLATE_MODEL_PATH`
- [ ] `PARKING_SERVICE_URL`
- [ ] `BOOKING_SERVICE_URL`
- [ ] `REALTIME_SERVICE_URL`

## 3.3 DB/service dependencies bắt buộc

### Chatbot

- [ ] MySQL: **bắt buộc** cho đa số business endpoints (`/chatbot/chat`, conversations, preferences, notifications/actions).
- [ ] Redis: **không bắt buộc** để service boot (startup catch exception, degrade).
- [ ] RabbitMQ: **không bắt buộc** để service boot (consumer start non-blocking, lỗi thì warning).
- [ ] Booking/Parking/Vehicle/Payment/Realtime services: cần cho full business flow; không cần cho health smoke.

### AI service

- [ ] MySQL: **bắt buộc** cho metrics endpoints và nhiều endpoint có DB log mạnh.
- [ ] Booking/Parking/Realtime services: **bắt buộc** cho check-in/check-out/monitoring integration path.
- [ ] Physical camera/RTSP: **không bắt buộc** cho smoke; bắt buộc nếu muốn test live camera/ESP32 path thực tế.

## 3.4 Model files cần có/thiếu

### Đang có trong workspace

- [x] `app/models/license-plate-finetune-v1m.pt` (tồn tại)
- [x] `ml/models/cash_recognition_best.pth` (tồn tại)

### Thiếu (nhưng có fallback)

- [ ] `ml/models/yolo11n.pt` không thấy trong repo hiện tại.
  - Kết quả: detect-occupancy vẫn chạy qua OpenCV fallback (`detection_method=opencv_fallback`).
- [ ] `ml/models/banknote_yolov8n.pt` không thấy.
  - Kết quả: banknote pipeline vẫn chạy fallback/stub theo thiết kế test.
- [ ] `ml/models/banknote_mobilenetv3.pth` không thấy.
  - Kết quả: fast mode vẫn chạy; full mode có thể degrade chất lượng AI fallback.

---

## 4. Phần nào test local thuần được / không được

## 4.1 Test local thuần (không DB/camera/model thật)

### Chatbot

- [x] `qa_probe_health.py` (health only)
- [x] `tests/test_smoke.py` (route/schema/health checks mức smoke)
- [x] Gateway auth unit/schema tests (không cần DB thật)

### AI service

- [x] `tests/test_detector.py` (fallback detector)
- [x] `tests/test_ai_classifier.py` (stub classifier)
- [x] `tests/test_pipeline.py` (pipeline logic với synthetic images)
- [x] `tests/test_api_banknote.py` (nhiều test patch/mock DB)
- [x] `qa_probe_occupancy.py` và endpoint `/ai/parking/detect-occupancy/` (không cần DB; dùng ảnh upload + slots JSON)
- [x] `/health/`, `/ai/cameras/list` mức contract check

## 4.2 Không thể verify đầy đủ nếu thiếu phụ thuộc thật

- [ ] Chatbot full conversation CRUD/action/preferences nếu thiếu MySQL.
- [ ] AI `/ai/models/metrics|predictions|versions` nếu thiếu MySQL.
- [ ] AI `/ai/parking/check-in` và `/check-out` nếu thiếu booking/realtime services.
- [ ] AI ESP32 flow thực nếu thiếu camera feed/QR thật/UART hardware.
- [ ] Parking detection chất lượng YOLO thực nếu thiếu `yolo11n.pt`.

---

## 5. Known blockers

- [ ] **[BLOCKER] Python runtime không đồng nhất giữa 2 service**:
  - Chatbot Dockerfile: 3.11
  - AI Dockerfile: 3.10
  - QA local dễ phát sinh mismatch wheel (đặc biệt Torch/vision).
- [ ] **[BLOCKER] Chatbot thiếu `.env.example` riêng service**:
  - Cần suy luận từ `app/config.py` hoặc dùng `.env.example` ở mức `backend-microservices`.
- [ ] **[WARNING] Thiếu các model YOLO banknote/parking trong `ml/models`**:
  - Chạy được nhờ fallback nhưng không phản ánh accuracy production.
- [ ] **[WARNING] AI lifespan luôn bật camera monitor background**:
  - Khi thiếu sibling services/camera sẽ log warning liên tục, có thể gây nhiễu QA log.

---

## 6. Fastest local verification path

## 6.1 Chatbot (nhanh nhất)

1. Set env tối thiểu: `DB_USER`, `DB_PASSWORD`, `GATEWAY_SECRET`.
2. Chạy `qa_probe_health.py` để xác nhận app boot + health contract.
3. Chạy `pytest tests/test_smoke.py -q` để verify route/schema/smoke mà không cần full integration stack.

## 6.2 Currency detection (banknote/cash)

1. Dùng AI service env từ `.env.local` (hoặc `run_local.bat`).
2. Verify banknote nhanh: chạy `pytest tests/test_api_banknote.py -q` (đa phần patch DB, dùng ảnh synthetic).
3. Verify logic engine thuần: `pytest tests/test_detector.py tests/test_ai_classifier.py tests/test_pipeline.py -q`.
4. Nếu muốn thử endpoint runtime nhanh: gọi `/ai/detect/banknote/?mode=fast` với ảnh test.

Ghi chú:
- `detect_cash` phụ thuộc model `cash_recognition_best.pth` + DB logging path.
- `detect_license-plate` có thể trả 503 nếu phần model/inference import lỗi.

## 6.3 Parking detection (occupancy)

1. Dùng `qa_probe_occupancy.py` (đã có payload invalid/valid form sẵn).
2. Hoặc gọi thẳng `/ai/parking/detect-occupancy/` với:
   - `image` (jpeg/png)
   - `camera_id`
   - `slots` JSON hợp lệ
3. Chấp nhận fallback OpenCV khi không có `yolo11n.pt`; xác nhận response có `detection_method` và danh sách slot statuses.

---

## 7. Checklist cho Implementer/Tester

- [ ] Python local target: ưu tiên 3.10.x cho QA AI local.
- [ ] Tạo 2 venv tách riêng chatbot/ai-service.
- [ ] Bổ sung `.env` cho chatbot (do không có `.env.example` riêng).
- [ ] Dùng `.env.local` hoặc `run_local.bat` cho ai-service.
- [ ] Nếu test full business flow: bật MySQL + booking/parking/realtime services.
- [ ] Nếu test local-only nhanh: ưu tiên smoke/unit + probes nêu ở mục 6.

---

## 8. Nguồn

| # | Path | Mô tả | Date |
| --- | --- | --- | --- |
| 1 | `backend-microservices/chatbot-service-fastapi/app/config.py` | Env fail-fast chatbot | 2026-03-16 |
| 2 | `backend-microservices/chatbot-service-fastapi/app/main.py` | Startup/shutdown behavior chatbot | 2026-03-16 |
| 3 | `backend-microservices/chatbot-service-fastapi/tests/test_smoke.py` | Smoke scope chatbot | 2026-03-16 |
| 4 | `backend-microservices/chatbot-service-fastapi/qa_probe_health.py` | Quick health probe | 2026-03-16 |
| 5 | `backend-microservices/ai-service-fastapi/app/config.py` | Env defaults AI | 2026-03-16 |
| 6 | `backend-microservices/ai-service-fastapi/.env.example` | Env template AI | 2026-03-16 |
| 7 | `backend-microservices/ai-service-fastapi/.env.local` | Env local AI | 2026-03-16 |
| 8 | `backend-microservices/ai-service-fastapi/run_local.bat` | Local startup script + preflight | 2026-03-16 |
| 9 | `backend-microservices/ai-service-fastapi/app/main.py` | Lifespan + camera monitor | 2026-03-16 |
| 10 | `backend-microservices/ai-service-fastapi/app/routers/detection.py` | Currency endpoints + DB logging behavior | 2026-03-16 |
| 11 | `backend-microservices/ai-service-fastapi/app/routers/parking.py` | Occupancy/check-in/out contracts | 2026-03-16 |
| 12 | `backend-microservices/ai-service-fastapi/app/engine/slot_detection.py` | YOLO/OpenCV fallback occupancy | 2026-03-16 |
| 13 | `backend-microservices/ai-service-fastapi/tests/test_ai_comprehensive.py` | DB/camera dependency hints | 2026-03-16 |
| 14 | `backend-microservices/ai-service-fastapi/tests/test_api_banknote.py` | Banknote API tests with DB mock | 2026-03-16 |
| 15 | `backend-microservices/ai-service-fastapi/tests/test_detector.py` | Detector fallback tests | 2026-03-16 |
| 16 | `backend-microservices/ai-service-fastapi/tests/test_ai_classifier.py` | Classifier stub tests | 2026-03-16 |
| 17 | `backend-microservices/ai-service-fastapi/qa_probe_occupancy.py` | Occupancy probe local | 2026-03-16 |
| 18 | `backend-microservices/ai-service-fastapi/app/models/license-plate-finetune-v1m.pt` | Plate model presence | 2026-03-16 |
| 19 | `backend-microservices/ai-service-fastapi/ml/models/cash_recognition_best.pth` | Cash model presence | 2026-03-16 |
| 20 | `docs/testing/backend-smoke-env-retest-2026-03-14.txt` | Smoke evidence Python 3.10.5 | 2026-03-16 |
