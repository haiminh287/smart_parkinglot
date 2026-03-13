# 🚗 Quy Trình Check-in / Check-out / Camera — Tổng Quan

> **Trạng thái tổng thể:** Code 95% hoàn thành | Hardware đã tích hợp
> **Kiến trúc:** ESP32 → AI Service (FastAPI) → Booking/Parking Service (Django) → Realtime (Go)
> **Hardware:** ESP32 DevKit + Arduino Uno + Servo SG90 × 2

---

## 📁 Cấu Trúc File Liên Quan

```
backend-microservices/
├── ai-service-fastapi/
│   ├── app/routers/
│   │   ├── esp32.py                  ✅ ESP32 check-in/out/cash endpoints (chính)
│   │   ├── detection.py              ✅ Web upload check-in/out endpoints
│   │   └── cameras.py                ✅ Camera CRUD
│   ├── app/services/
│   │   ├── camera_service.py         ✅ Camera capture module
│   │   └── plate_recognition.py      ✅ YOLO + OCR pipeline
│   ├── app/core/
│   │   └── camera_monitor.py         ✅ Background camera monitor (30s interval)
│   └── app/engine/
│       ├── pipeline.py               ✅ Banknote pipeline (cho cash payment)
│       └── cash_session.py           ✅ Session quản lý tiền mặt
│
├── booking-service/
│   └── bookings/
│       ├── views.py                  ✅ check-in/check-out endpoints
│       ├── models.py                 ✅ Booking model + status transitions
│       └── urls.py                   ✅ URL routing
│
├── parking-service/
│   └── infrastructure/models/
│       └── slot.py + camera.py       ✅ Slot status + Camera management
│
hardware/
├── esp32/esp32_gate_controller/
│   └── esp32_gate_controller.ino     ✅ ESP32 firmware
└── arduino/barrier_control/
    └── barrier_control.ino           ✅ Arduino servo control

spotlove-ai/src/pages/
├── CheckInOutPage.tsx                ✅ Frontend check-in/out UI
├── CamerasPage.tsx                   ✅ Camera viewer
└── KioskPage.tsx                     ✅ Kiosk self-service UI
```

---

## 🔄 Luồng Check-in Hoàn Chỉnh

### Luồng A: Check-in tự động tại cổng (ESP32 — Primary)

```
┌─────────────────────────────────────────────────────────────────┐
│                        TẠI CỔNG VÀO                             │
│                                                                  │
│  User quét QR → Nhấn nút GPIO 4 trên ESP32                      │
│         │                                                        │
│         ▼                                                        │
│  ESP32 gửi POST /ai/parking/esp32/check-in/                     │
│  Body: { "gate_id": "GATE-IN-01" }                               │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────┐                     │
│  │ AI Service xử lý:                        │                    │
│  │                                           │                    │
│  │ 1. Đọc QR từ camera                      │                    │
│  │    ├─ IP camera: 192.168.100.130:4747     │                    │
│  │    ├─ OpenCV QRCodeDetector               │                    │
│  │    └─ Fallback: grayscale + pyzbar        │                    │
│  │                                           │                    │
│  │ 2. Parse QR → booking_id                  │                    │
│  │    ├─ JSON format: {"bookingId":"..."}    │                    │
│  │    └─ Hoặc plain text booking ID          │                    │
│  │                                           │                    │
│  │ 3. Fetch booking từ booking-service       │                    │
│  │    GET /bookings/{booking_id}/            │                    │
│  │                                           │                    │
│  │ 4. Validate:                              │                    │
│  │    ├─ Status phải = not_checked_in        │                    │
│  │    ├─ Thời gian: cho phép sớm 15 phút    │                    │
│  │    └─ Payment: nếu on_entry → phải paid   │                    │
│  │                                           │                    │
│  │ 5. Chụp biển số từ RTSP camera            │                    │
│  │    ├─ rtsp://admin:XGIMBN@192.168.1.100  │                    │
│  │    ├─ 2 retries, skip 3 frames            │                    │
│  │    └─ Fallback: test images               │                    │
│  │                                           │                    │
│  │ 6. OCR biển số:                           │                    │
│  │    ├─ YOLO detect plate region            │                    │
│  │    ├─ Blur check (Laplacian)              │                    │
│  │    └─ TrOCR → EasyOCR → Tesseract        │                    │
│  │                                           │                    │
│  │ 7. So khớp biển số (fuzzy):               │                    │
│  │    ├─ Normalize (bỏ space, dots, dashes)  │                    │
│  │    ├─ Cho phép ≤3 ký tự khác biệt        │                    │
│  │    └─ Hoặc ≥70% SequenceMatcher ratio     │                    │
│  │                                           │                    │
│  │ 8. Gọi booking-service check-in           │                    │
│  │    POST /bookings/{id}/checkin/           │                    │
│  │                                           │                    │
│  │ 9. Cập nhật slot → "occupied"             │                    │
│  │    PATCH /parking/slots/{id}/status/      │                    │
│  │                                           │                    │
│  │ 10. Broadcast realtime event              │                    │
│  │     POST /api/broadcast/notification/     │                    │
│  └──────────────────────┬──────────────────┘                     │
│                         │                                        │
│                         ▼                                        │
│  Response: { "barrier_action": "open", ... }                     │
│         │                                                        │
│         ▼                                                        │
│  ESP32 đọc "open" → gửi UART "OPEN_1" đến Arduino               │
│         │                                                        │
│         ▼                                                        │
│  Arduino → Servo pin 10 → barrier_open = 3000μs                  │
│  LED pin 13 ON                                                    │
│         │                                                        │
│         ▼ (5 giây sau)                                            │
│  ESP32 gửi "CLOSE_1" → Arduino đóng barrier                      │
│  (Arduino cũng có auto-close 5s riêng)                            │
└─────────────────────────────────────────────────────────────────┘
```

### Luồng B: Check-in từ Web (Upload ảnh)

```
User mở CheckInOutPage.tsx
    │
    ├─ Tab "Check-in" → Chọn booking active
    ├─ Upload ảnh biển số
    │
    ▼
POST /ai/parking/check-in/
Body: multipart/form-data { image: File, data: JSON }
    │
    ▼
Xử lý tương tự ESP32 nhưng:
  ├─ Không cần đọc QR (user chọn booking trực tiếp)
  ├─ Không cần camera (user upload ảnh)
  └─ So khớp biển số CHÍNH XÁC (không fuzzy)
```

---

## 🔄 Luồng Check-out Hoàn Chỉnh

### Luồng A: Check-out tại cổng (ESP32)

```
┌─────────────────────────────────────────────────────────────────┐
│                       TẠI CỔNG RA                                │
│                                                                  │
│  User quét QR → Nhấn nút GPIO 5 trên ESP32                      │
│         │                                                        │
│         ▼                                                        │
│  ESP32 gửi POST /ai/parking/esp32/check-out/                    │
│  Body: { "gate_id": "GATE-OUT-01" }                              │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────┐                     │
│  │ AI Service xử lý:                        │                    │
│  │                                           │                    │
│  │ 1. Đọc QR → booking_id                   │                    │
│  │                                           │                    │
│  │ 2. Fetch booking (status = checked_in)    │                    │
│  │                                           │                    │
│  │ 3. Chụp biển số + OCR + Fuzzy match       │                    │
│  │    ⚠️ Nếu OCR fail → BỎ QUA (không block) │                    │
│  │                                           │                    │
│  │ 4. KIỂM TRA THANH TOÁN:                  │                    │
│  │    ├─ payment_method = "on_exit"          │                    │
│  │    │   → Bypass (luôn cho qua)            │                    │
│  │    └─ payment_method ≠ "on_exit"          │                    │
│  │        └─ payment_status phải = "completed"│                    │
│  │        └─ Nếu chưa paid:                  │                    │
│  │            → barrier_action = "closed"     │                    │
│  │            → payment_required = true       │                    │
│  │            → amount_due = xxx VNĐ          │                    │
│  │                                           │                    │
│  │ 5. Gọi booking-service check-out          │                    │
│  │    POST /bookings/{id}/checkout/          │                    │
│  │    → Tính total_amount, parking_fee,      │                    │
│  │      late_fee, check_out_time             │                    │
│  │                                           │                    │
│  │ 6. Release slot → "available"             │                    │
│  │    PATCH /parking/slots/{id}/status/      │                    │
│  │                                           │                    │
│  │ 7. Broadcast check-out event              │                    │
│  └──────────────────────┬──────────────────┘                     │
│                         │                                        │
│                         ▼                                        │
│  Response: { "barrier_action": "open", "total_amount": ... }     │
│         │                                                        │
│         ▼                                                        │
│  ESP32 → "OPEN_2" → Arduino → Servo pin 9 → barrier open        │
│  (5s auto-close)                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Luồng Cash Payment (Nếu chưa thanh toán)

```
ESP32 barrier = CLOSED (chưa paid)
    │
    ▼
User đưa tiền mặt trước camera
    │
    ▼
POST /ai/parking/esp32/cash-payment/
Body: { "booking_id": "...", "camera_url": "..." }
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Capture ảnh tiền từ camera        │
│ 2. BanknoteRecognitionPipeline:      │
│    ├─ Preprocessing (quality check)  │
│    ├─ Detection (YOLOv8n / full img) │
│    ├─ Color classify (HSV)           │
│    └─ AI fallback (MobileNetV3)      │
│ 3. Nếu ACCEPT:                      │
│    ├─ Lấy denomination              │
│    ├─ Cộng vào CashSessionManager    │
│    └─ Check total ≥ amount_due?      │
│        ├─ CÓ → PATCH booking paid    │
│        │      → barrier_action=open  │
│        └─ CHƯA → return remaining    │
└──────────────────┬──────────────────┘
                   │
    Lặp lại cho đến khi đủ tiền
```

---

## 📹 Hệ Thống Camera

### Camera Hardware

| Camera       | Loại                   | URL mặc định                            | Chức năng            |
| ------------ | ---------------------- | --------------------------------------- | -------------------- |
| QR Camera    | MJPEG (DroidCam/phone) | `http://192.168.100.130:4747/video`     | Đọc QR code tại cổng |
| Plate Camera | RTSP (security cam)    | `rtsp://admin:XGIMBN@192.168.1.100:554` | OCR biển số          |
| Cash Camera  | MJPEG/RTSP             | Configurable                            | Chụp tiền mặt        |

### Camera Capture Module (`camera_service.py`)

- Singleton `CameraCapture` class
- Timeout configurable (default 10s)
- Skip 3 buffered frames để lấy frame mới nhất
- Retry: 3 lần, delay 0.5s giữa mỗi lần
- Async wrapper qua `asyncio.to_thread()`

### Camera Monitor Background Worker (`camera_monitor.py`)

```
Chạy mỗi 30 giây:
  1. Fetch danh sách camera online: GET /parking/cameras/?status=online
  2. Với mỗi camera:
     ├─ Fetch slot bounding boxes (x1, y1, x2, y2)
     ├─ Capture frame từ stream
     ├─ Chạy YOLO plate detection
     └─ Push status changes → parking-service + realtime broadcast
  3. Chỉ update nếu confidence ≥ 0.6
```

### Camera Data Model (parking-service)

| Field               | Type      | Mô tả                     |
| ------------------- | --------- | ------------------------- |
| id                  | UUID      | Primary key               |
| name                | string    | Tên camera                |
| stream_url          | string    | URL stream RTSP/MJPEG     |
| camera_type         | enum      | entry / exit / monitoring |
| zone                | FK → Zone | Zone camera thuộc về      |
| status              | enum      | online / offline          |
| slot_bounding_boxes | JSON      | Tọa độ slot trên frame    |

### Camera API Endpoints

| Method | Endpoint                        | Mô tả                                     |
| ------ | ------------------------------- | ----------------------------------------- |
| GET    | `/parking/cameras/`             | Danh sách camera (filter by zone, status) |
| GET    | `/parking/cameras/{id}/`        | Chi tiết camera                           |
| GET    | `/parking/cameras/{id}/stream/` | URL stream                                |
| POST   | `/parking/cameras/`             | Thêm camera (admin)                       |
| PUT    | `/parking/cameras/{id}/`        | Sửa camera (admin)                        |
| DELETE | `/parking/cameras/{id}/`        | Xóa camera (admin)                        |

---

## ⚡ ESP32 Hardware

### Thông số ESP32 Gate Controller

| Thông số         | Giá trị                                    |
| ---------------- | ------------------------------------------ |
| Board            | ESP32 DevKit V1                            |
| WiFi             | SSID: `FPT Telecom-755C-IOT`               |
| AI Service URL   | `http://192.168.100.194:8009`              |
| Button Check-in  | GPIO 4 (INPUT_PULLUP, active LOW)          |
| Button Check-out | GPIO 5 (INPUT_PULLUP, active LOW)          |
| UART → Arduino   | Serial2: TX2=GPIO17, RX2=GPIO16, 9600 baud |
| LED              | GPIO 2 (built-in)                          |
| HTTP Timeout     | 30 giây                                    |
| Debounce         | 300ms                                      |

### Luồng ESP32

```
1. Button press → POST JSON đến AI service
2. Parse response JSON → đọc field "barrierAction"
3. Nếu "open" → gửi UART "OPEN_1" (entry) / "OPEN_2" (exit)
4. Đợi 5 giây → gửi "CLOSE_1" / "CLOSE_2"
5. Đọc ACK từ Arduino (debug)
```

### Arduino Barrier Controller

| Thông số    | Giá trị                       |
| ----------- | ----------------------------- |
| Board       | Arduino Uno/Mega              |
| Entry Servo | Pin 10, pulse 500-2400μs      |
| Exit Servo  | Pin 9, pulse 500-2400μs       |
| UART        | 9600 baud, newline-terminated |
| LED         | Pin 13 (ON khi barrier mở)    |
| Auto-close  | 5 giây                        |

### UART Commands

| Command   | Mô tả                               | ACK                                         |
| --------- | ----------------------------------- | ------------------------------------------- |
| `OPEN_1`  | Mở barrier entry (servo → 3000μs)   | `ACK:OPEN_1`                                |
| `CLOSE_1` | Đóng barrier entry (servo → 1500μs) | `ACK:CLOSE_1`                               |
| `OPEN_2`  | Mở barrier exit                     | `ACK:OPEN_2`                                |
| `CLOSE_2` | Đóng barrier exit                   | `ACK:CLOSE_2`                               |
| `STATUS`  | Query trạng thái                    | `STATUS:entry=open/closed,exit=open/closed` |

---

## 📊 Booking Status Transitions

```
                    ┌──────────────────┐
      Create        │ not_checked_in   │  ← Trạng thái mặc định
    ──────────────► │ (pending/confirmed)│
                    └────┬──────────┬──┘
                         │          │
                   checkin()    cancel()
                         │          │
                 ┌───────▼───┐  ┌──▼────────┐
                 │ checked_in │  │ cancelled  │  ← Terminal
                 └─────┬─────┘  └────────────┘
                       │
                 checkout()
                       │
                 ┌─────▼──────┐
                 │ checked_out │  ← Terminal
                 └────────────┘

  Thêm: no_show (terminal, admin/system set)
```

### Payment Status

```
pending → processing → completed
                    ↘ failed
completed → refunded
```

---

## 🖥️ Frontend Pages

### `CheckInOutPage.tsx` — Check-in/Check-out

- 2 tabs: Check-in / Check-out
- Hiển thị QR code cho gate scanning
- Manual upload: user chọn ảnh biển số
- Gọi `aiApi.checkIn()` / `aiApi.checkOut()`
- Auto-detect active session → chuyển tab Check-out

### `CamerasPage.tsx` — Camera Viewer

- **Admin view:** Grid tất cả cameras từ parking-service
- **User view:** Chỉ camera liên quan đến slot đang đậu
- Fullscreen view, vehicle tracking

### `KioskPage.tsx` — Kiosk tự phục vụ

- UI cho physical terminal tại cổng
- Idle → Check-in / Check-out buttons
- Gọi cùng endpoint ESP32 hardware
- Cash payment flow:
  1. Nếu `payment_required` → chuyển sang mode cash
  2. User upload ảnh banknote
  3. Gọi `/ai/parking/esp32/cash-payment/`
  4. Lặp lại cho đến khi đủ tiền
- Gate event log (20 events gần nhất)
- Processing time display

---

## ✅ Đã Hoàn Thành

| Component                        | Chi tiết                                    |
| -------------------------------- | ------------------------------------------- |
| ESP32 check-in/check-out flow    | End-to-end từ button → barrier              |
| Arduino barrier control (UART)   | Servo control + auto-close                  |
| QR code reading                  | OpenCV + pyzbar fallbacks                   |
| License plate OCR pipeline       | YOLO → blur check → TrOCR/EasyOCR/Tesseract |
| Fuzzy plate matching             | Character diff + SequenceMatcher            |
| Booking status validation        | Tất cả status transitions                   |
| Time window validation           | 15 phút sớm cho phép                        |
| Payment enforcement              | Block barrier nếu chưa paid                 |
| Cash payment with AI detection   | Pipeline + session tracking                 |
| Slot status update               | Auto-update occupied/available              |
| Camera monitor background worker | 30s interval slot detection                 |
| Frontend check-in/out page       | Upload + QR display                         |
| Frontend kiosk page              | Full ESP32-equivalent flow                  |
| Test image fallback              | Khi camera không available                  |
| Prediction logging to DB         | Log mỗi operation                           |
| Realtime broadcast               | WebSocket events qua realtime-service       |

---

## ❌ Chưa Hoàn Thành / Cần Cải Tiến

### 🔴 Quan Trọng

| #   | Vấn đề                             | Chi tiết                                                       |
| --- | ---------------------------------- | -------------------------------------------------------------- |
| 1   | **Payment gateway chưa implement** | MoMo/VNPay/ZaloPay là TODO. Verify payment luôn return success |
| 2   | **Refund khi hủy chưa implement**  | Comment `TODO: Process refund if paid online`                  |
| 3   | **ESP32 không gửi QR data**        | `.ino` chỉ gửi `gate_id`, phụ thuộc hoàn toàn vào QR camera    |

### 🟡 Trung Bình

| #   | Vấn đề                                    | Chi tiết                                                                                |
| --- | ----------------------------------------- | --------------------------------------------------------------------------------------- |
| 4   | **Duplicate slot update**                 | Cả AI service VÀ booking-service đều PATCH `/slots/{id}/status/` → gọi 2 lần            |
| 5   | **Arduino servo misconfigured**           | `writeMicroseconds(3000)` vượt range `attach(pin, 500, 2400)` → bị clip                 |
| 6   | **Web vs ESP32 plate matching khác nhau** | Web = exact match, ESP32 = fuzzy (≤3 char) → inconsistent                               |
| 7   | **Cash session in-memory**                | Mất data khi restart AI service giữa chừng thanh toán                                   |
| 8   | **Camera monitor conflict**               | Background monitor có thể set slot "available" bằng AI vision dù booking nói "occupied" |
| 9   | **Double auto-close**                     | ESP32 (5s) + Arduino (5s) đều có timer → command close thừa                             |
| 10  | **No-show detection chưa có**             | Status `no_show` tồn tại nhưng không có automated logic                                 |

### 🟢 Nhỏ

| #   | Vấn đề                                 | Chi tiết                                                        |
| --- | -------------------------------------- | --------------------------------------------------------------- |
| 11  | **Hardcoded credentials**              | WiFi password, RTSP password, gateway secret trong source       |
| 12  | **Request ID không dùng**              | `request_id` field trong ESP32 schema tồn tại nhưng không check |
| 13  | **camelCase/snake_case inconsistency** | ESP32 code đọc cả 2 format từ response                          |

---

## 🗺️ Sơ Đồ Tổng Thể

```
                    ┌──────────┐
                    │  User    │
                    │  (Phone) │
                    └────┬─────┘
                         │
              ┌──────────▼──────────┐
              │   Frontend (React)   │
              │   localhost:8080     │
              │  ┌────────────────┐  │
              │  │CheckInOutPage  │  │
              │  │CamerasPage     │  │
              │  │KioskPage       │  │
              │  └────────────────┘  │
              └──────────┬──────────┘
                         │ /api/*
              ┌──────────▼──────────┐
              │  Gateway (Go)       │
              │  localhost:8000     │
              └──────────┬──────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼──────┐
│ AI Service   │ │Booking Svc   │ │Parking Svc │
│ :8009        │ │:8002         │ │:8003       │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌────────┐ │
│ │ESP32 API │ │ │ │checkin   │ │ │ │slots   │ │
│ │Plate OCR │ │ │ │checkout  │ │ │ │cameras │ │
│ │Cash AI   │ │ │ │cancel    │ │ │ │zones   │ │
│ │Cam Mon.  │ │ │ │payment   │ │ │ │floors  │ │
│ └──────────┘ │ │ └──────────┘ │ │ └────────┘ │
└───────┬──────┘ └──────────────┘ └────────────┘
        │
┌───────▼──────┐     ┌──────────────┐
│  ESP32       │ ────►│  Arduino     │
│  (WiFi+HTTP) │ UART │  (Servo ×2)  │
│  GPIO 4,5    │     │  Pin 9, 10   │
└──────────────┘     └──────────────┘
        ▲                    │
        │                    ▼
   [QR Camera]         [Barrier ×2]
   [Plate Cam]          Entry + Exit
```
