# 🅿️ PARKING SYSTEM PLAN — ParkSmart v4.0

> **Ngày tạo**: 2025 | **Phiên bản**: 4.0-comprehensive
> **Mục tiêu**: Kiểm tra toàn bộ logic backend + frontend, lên plan chi tiết cho flow đặt chỗ → check-in → đậu xe → check-out → thanh toán.
> **Lưu ý**: File này CHỈ là plan, KHÔNG thay đổi code.

---

## MỤC LỤC

1. [Tổng quan hệ thống hiện tại](#1-tổng-quan-hệ-thống-hiện-tại)
2. [Kiểm kê trạng thái: Đã code vs Chưa code](#2-kiểm-kê-trạng-thái-đã-code-vs-chưa-code)
3. [FLOW 1: Đặt chỗ online (Booking)](#3-flow-1-đặt-chỗ-online-booking)
4. [FLOW 2: Check-in (Vào bãi)](#4-flow-2-check-in-vào-bãi)
5. [FLOW 3: Xác minh tại ô đậu (Slot Verification)](#5-flow-3-xác-minh-tại-ô-đậu-slot-verification)
6. [FLOW 4: Giám sát camera (Slot Detection)](#6-flow-4-giám-sát-camera-slot-detection)
7. [FLOW 5: Check-out (Ra bãi + Thanh toán)](#7-flow-5-check-out-ra-bãi--thanh-toán)
8. [FLOW 6: Thanh toán tiền mặt (AI Cash Recognition)](#8-flow-6-thanh-toán-tiền-mặt-ai-cash-recognition)
9. [File thừa / cần xoá](#9-file-thừa--cần-xoá)
10. [Bugs / Inconsistencies phát hiện được](#10-bugs--inconsistencies-phát-hiện-được)
11. [Cải tiến cần thiết (Improvements)](#11-cải-tiến-cần-thiết-improvements)
12. [Task Breakdown chi tiết](#12-task-breakdown-chi-tiết)
13. [Service Impact Map](#13-service-impact-map)
14. [Risk Assessment](#14-risk-assessment)
15. [**Frontend Audit — Kiểm kê chi tiết toàn bộ Frontend**](#15-frontend-audit--kiểm-kê-chi-tiết-toàn-bộ-frontend)
16. [**Frontend — Cải tiến cần thiết (Improvements)**](#16-frontend--cải-tiến-cần-thiết-improvements)
17. [**Frontend — Task Breakdown chi tiết**](#17-frontend--task-breakdown-chi-tiết)
18. [**Frontend — Service Impact Map**](#18-frontend--service-impact-map)
19. [**Frontend — Recommended Implementation Order**](#19-frontend--recommended-implementation-order)

---

## 1. TỔNG QUAN HỆ THỐNG HIỆN TẠI

### 1.1 Architecture

```
                    ┌──────────────────────────────────────────┐
                    │         Frontend (spotlove-ai)           │
                    │      React + Vite + TypeScript + Redux   │
                    │          localhost:5173 → :8080           │
                    └──────────────┬───────────────────────────┘
                                   │ HTTP / WebSocket
                                   ▼
                    ┌──────────────────────────────────────────┐
                    │     Gateway Service (Go/Gin) :8000       │
                    │  JWT Redis Session + Proxy + CORS        │
                    └──┬────┬────┬────┬────┬────┬────┬────┬───┘
                       │    │    │    │    │    │    │    │
          ┌────────────┘    │    │    │    │    │    │    └──────────┐
          ▼                 ▼    ▼    ▼    ▼    ▼    ▼              ▼
    ┌──────────┐  ┌────────┐ ┌──────┐ ┌───────┐ ┌──────┐ ┌─────┐ ┌──────┐
    │  Auth    │  │Booking │ │Park- │ │Vehicle│ │Notif │ │Pay- │ │ AI   │
    │ :8001    │  │ :8002  │ │ing   │ │       │ │:8005 │ │ment │ │:8009 │
    │ Django   │  │Django  │ │Django│ │Django │ │FastAPI│ │:8007│ │Fast  │
    └──────────┘  └────────┘ └──────┘ └───────┘ └──────┘ │Fast │ │API   │
                                                          └─────┘ └──────┘
          ┌────────────────────────┐    ┌──────────────────────────────┐
          │  Realtime (Go) :8006   │    │  Chatbot (FastAPI) :8008     │
          │  WebSocket Hub         │    │  Gemini LLM + Booking Wizard │
          └────────────────────────┘    └──────────────────────────────┘
                      │
              ┌───────┴───────┐
              │   共享基建     │
              │ MySQL 8 :3306  │
              │ Redis 7 :6379  │
              │ RabbitMQ :5672 │
              └───────────────┘
```

### 1.2 Docker Services (15 containers)

| #   | Container                    | Type           | Port                | Trạng thái |
| --- | ---------------------------- | -------------- | ------------------- | ---------- |
| 1   | mysql                        | Infrastructure | 3306                | ✅ Running |
| 2   | redis                        | Infrastructure | 6379                | ✅ Running |
| 3   | rabbitmq                     | Infrastructure | 5672/15672          | ✅ Running |
| 4   | auth-service                 | Django DRF     | 8001(internal:8000) | ✅ Built   |
| 5   | parking-service              | Django DRF     | internal:8000       | ✅ Built   |
| 6   | vehicle-service              | Django DRF     | internal:8000       | ✅ Built   |
| 7   | booking-service              | Django DRF     | internal:8000       | ✅ Built   |
| 8   | booking-celery-worker        | Celery         | —                   | ✅ Built   |
| 9   | booking-celery-beat          | Celery Beat    | —                   | ✅ Built   |
| 10  | notification-service-fastapi | FastAPI        | 8005                | ✅ Built   |
| 11  | payment-service-fastapi      | FastAPI        | 8007                | ✅ Built   |
| 12  | chatbot-service-fastapi      | FastAPI        | 8008                | ✅ Built   |
| 13  | ai-service-fastapi           | FastAPI        | 8009                | ✅ Built   |
| 14  | gateway-service-go           | Go/Gin         | 8000                | ✅ Built   |
| 15  | realtime-service-go          | Go/Gin         | 8006                | ✅ Built   |

### 1.3 Frontend Pages

| Page                    | File                           | Trạng thái |
| ----------------------- | ------------------------------ | ---------- |
| Login                   | `LoginPage.tsx`                | ✅ Built   |
| Register                | `RegisterPage.tsx`             | ✅ Built   |
| Dashboard               | `UserDashboard.tsx`            | ✅ Built   |
| Booking (5-step wizard) | `BookingPage.tsx` (1328 lines) | ✅ Built   |
| Payment (VietQR)        | `PaymentPage.tsx` (472 lines)  | ✅ Built   |
| History                 | `HistoryPage.tsx` (739 lines)  | ✅ Built   |
| Cameras                 | `CamerasPage.tsx` (612 lines)  | ✅ Built   |
| Banknote Detection      | `BanknoteDetectionPage.tsx`    | ✅ Built   |
| Map                     | `MapPage.tsx`                  | ✅ Built   |
| Settings                | `SettingsPage.tsx`             | ✅ Built   |
| Support                 | `SupportPage.tsx`              | ✅ Built   |
| Panic Button            | `PanicButtonPage.tsx`          | ✅ Built   |
| Admin Dashboard         | `AdminDashboard.tsx`           | ✅ Built   |
| Admin Cameras           | `admin/AdminCamerasPage.tsx`   | ✅ Built   |
| Admin Slots             | `admin/AdminSlotsPage.tsx`     | ✅ Built   |
| Admin Stats             | `admin/AdminStatsPage.tsx`     | ✅ Built   |
| Admin Users             | `admin/AdminUsersPage.tsx`     | ✅ Built   |
| Admin Zones             | `admin/AdminZonesPage.tsx`     | ✅ Built   |
| Admin Config            | `admin/AdminConfigPage.tsx`    | ✅ Built   |

---

## 2. KIỂM KÊ TRẠNG THÁI: ĐÃ CODE VS CHƯA CODE

### 2.1 ✅ ĐÃ HOÀN THÀNH

#### Backend

| Feature                 | Service              | File(s)                                   | Chi tiết                                                                       |
| ----------------------- | -------------------- | ----------------------------------------- | ------------------------------------------------------------------------------ |
| Booking CRUD            | booking-service      | `views.py`, `serializers.py`, `models.py` | Create, cancel, checkin, checkout, current-parking, upcoming, stats, QR code   |
| PackagePricing model    | booking-service      | `models.py`                               | hourly/daily/weekly/monthly × Car/Motorbike                                    |
| Price calculation       | booking-service      | `serializers.py` (line ~320)              | Tính giá từ `PackagePricing` table khi create booking                          |
| QR Code generation      | booking-service      | `serializers.py` (line ~350)              | JSON: `{id, user_id, vehicle_license_plate, ...}`                              |
| Check-in validation     | booking-service      | `views.py` checkin action                 | Check status, mark `checked_in`, set `checked_in_at`                           |
| Check-out + late fee    | booking-service      | `views.py` checkout action                | Calculate duration, overtime, late_fee (1.5x surcharge)                        |
| Auto-cancel unpaid      | booking-service      | `tasks.py`                                | Celery: cancel online bookings unpaid >15min                                   |
| No-show detection       | booking-service      | `tasks.py`                                | Celery: mark no_show after 30min past hourly_start                             |
| Parking lot CRUD        | parking-service      | `views.py`, `models.py`                   | Lots, Floors, Zones, Slots, Cameras                                            |
| Nearest lot search      | parking-service      | `views.py` nearest action                 | Haversine formula + bounding box prefilter                                     |
| Lot availability        | parking-service      | `views.py` availability action            | Total/available/occupied by vehicle type                                       |
| Slot availability check | parking-service      | `views.py` check_slots_availability       | Cross-check with booking-service                                               |
| Camera model            | parking-service      | `models.py`                               | ip_address, port, stream_url, zone FK, is_active                               |
| Slot bounding box       | parking-service      | `models.py` CarSlot                       | x1, y1, x2, y2, camera FK — ready for AI detection                             |
| Payment initiate/verify | payment-service      | `routers/payment.py`                      | momo/vnpay/zalopay/cash methods                                                |
| License plate OCR       | ai-service           | `engine/plate_pipeline.py`                | YOLO detect → blur check → TrOCR/EasyOCR/Tesseract → format validate           |
| AI check-in flow        | ai-service           | `routers/parking.py` check-in             | QR parse → fetch booking → validate → OCR → plate match → call booking checkin |
| AI check-out flow       | ai-service           | `routers/parking.py` check-out            | Same as check-in but for checkout                                              |
| Cash detection          | ai-service           | `routers/detection.py`                    | `/ai/detect/cash/` endpoint                                                    |
| Banknote detection      | ai-service           | `routers/detection.py`                    | Hybrid MVP: YOLOv8 + HSV color + AI fallback                                   |
| Model training          | ai-service           | `routers/training.py`                     | BackgroundTasks for cash + banknote training                                   |
| Model metrics           | ai-service           | `routers/metrics.py`                      | Prediction logs, model versions                                                |
| WebSocket realtime      | realtime-service-go  | `handler/broadcast.go`                    | Slot/zone/lot/booking broadcast via Hub                                        |
| Gateway proxy           | gateway-service-go   | `router/routes.go`                        | Catch-all proxy with JWT session auth                                          |
| Notifications           | notification-service | `routers/notification.py`                 | CRUD notifications                                                             |
| Chatbot                 | chatbot-service      | Full service                              | Gemini LLM + intent classification + booking wizard                            |

#### Frontend

| Feature                | Component                   | Chi tiết                                                 |
| ---------------------- | --------------------------- | -------------------------------------------------------- |
| 5-step booking wizard  | `BookingPage.tsx`           | Lot → Vehicle → Floor/Zone/Slot → Time/Package → Payment |
| Parking lot selector   | `ParkingLotSelector.tsx`    | Nearest lots with geolocation                            |
| Slot grid              | `SlotGrid.tsx`              | Visual slot selection with availability                  |
| Price summary sidebar  | `PriceSummary.tsx`          | ⚠️ HARDCODED prices (see bugs)                           |
| VietQR payment         | `PaymentPage.tsx`           | QR code + bank transfer + countdown                      |
| Booking history        | `HistoryPage.tsx`           | Filter, cancel, view QR, stats chart                     |
| Camera tracking        | `CamerasPage.tsx`           | Admin: all cameras. User: parked vehicle camera          |
| Banknote detection     | `BanknoteDetectionPage.tsx` | Upload image → AI detect denomination                    |
| WebSocket service      | `websocket.service.ts`      | Slot/zone/lot/booking realtime updates                   |
| Booking API client     | `booking.api.ts`            | Full CRUD + checkIn/checkOut/cancel                      |
| Parking API client     | `parking.api.ts`            | Lots/floors/zones/slots/availability                     |
| AI API client          | `ai.api.ts`                 | Banknote detection only                                  |
| Multi-day picker       | `MultiDayPicker.tsx`        | Custom date selection                                    |
| Auto-guarantee booking | `AutoGuaranteeBooking.tsx`  | Auto parking tab                                         |
| Calendar auto-hold     | `CalendarAutoHold.tsx`      | Calendar-based booking                                   |

### 2.2 ❌ CHƯA CODE / THIẾU

| #   | Feature                             | Mô tả                                                                                                                                                         | Priority    |
| --- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| 1   | **ESP32/IoT Integration API**       | Không có endpoint nào cho ESP32 gọi. Hiện AI check-in/check-out nhận `UploadFile` + `Form` — ESP32 cần endpoint nhận tín hiệu nút bấm, trigger camera capture | 🔴 Critical |
| 2   | **Camera Capture API**              | ESP32 bấm nút → hệ thống phải tự capture ảnh từ camera IP (192.168.100.130:4747). Hiện tại user phải upload ảnh thủ công                                      | 🔴 Critical |
| 3   | **QR Code Scanner Integration**     | Camera QR tại cổng phải tự đọc QR code. Hiện tại QR data được truyền qua Form field                                                                           | 🔴 Critical |
| 4   | **Slot-level Verification**         | Tại ô đậu: nút bấm → QR scan → verify booking checked_in + đúng slot → mở barrier. Chưa có endpoint nào                                                       | 🔴 Critical |
| 5   | **Barrier Control API**             | Không có API điều khiển barrier (mở/đóng). Cần endpoint cho ESP32 gọi                                                                                         | 🔴 Critical |
| 6   | **Camera-based Slot Detection**     | 1 camera giám sát 5 slots, detect trạng thái chiếm/trống realtime. Model CarSlot đã có bbox (x1,y1,x2,y2) + camera FK nhưng chưa có AI pipeline xử lý         | 🔴 Critical |
| 7   | **Wrong-slot Detection**            | Detect xe đậu sai ô so với booking. Cần so sánh biển số detected với booking assigned                                                                         | 🟡 High     |
| 8   | **Lane Violation Detection**        | Detect xe đậu lấn lane/vi phạm ranh giới. Cần AI model                                                                                                        | 🟡 High     |
| 9   | **Box vs Line Parking Detection**   | Phân biệt kiểu đậu xe hộp vs kiểu đậu xe theo vạch                                                                                                            | 🟡 Medium   |
| 10  | **Cash Payment at Checkout**        | Offline checkout: nhét tiền → AI nhận diện → tính tổng → mở barrier. Flow chưa connect                                                                        | 🔴 Critical |
| 11  | **Transfer QR Auto-verification**   | PaymentPage hiện "Tôi đã thanh toán" button (manual confirm). Cần auto-verify via bank webhook                                                                | 🟡 High     |
| 12  | **Payment-before-barrier**          | Check-out flow KHÔNG enforce "phải thanh toán xong mới mở barrier". Hiện booking checkout API chạy bất kể payment status                                      | 🔴 Critical |
| 13  | **Camera Live Stream**              | CamerasPage hiện placeholder "Live Feed". Chưa connect stream_url từ camera thật                                                                              | 🟡 Medium   |
| 14  | **Slot Occupancy Realtime from AI** | Parking-service `available_slots` trên Zone KHÔNG tự cập nhật khi AI detect slot status change                                                                | 🟡 High     |
| 15  | **Frontend fetch PackagePricing**   | `PriceSummary.tsx` HARDCODE giá. `PackagePricing` API endpoint chưa expose                                                                                    | 🟡 High     |

---

## 3. FLOW 1: ĐẶT CHỖ ONLINE (BOOKING)

### 3.1 Flow hiện tại (✅ Đã code)

```
User mở BookingPage
    │
    ├── Step 1: Chọn bãi xe (ParkingLotSelector)
    │   ├── Lấy vị trí GPS user
    │   ├── GET /parking/lots/nearest/?lat=...&lng=...
    │   ├── Hiển thị bãi gần nhất + khoảng cách + available slots
    │   └── WebSocket subscribe: parking_updates (realtime slot changes)
    │
    ├── Step 2: Chọn xe
    │   ├── Chọn loại: Car / Motorbike
    │   ├── GET /vehicles/ → hiển thị xe đã lưu
    │   ├── Chọn xe cũ hoặc nhập biển số mới
    │   └── Motorbike: chỉ cần chọn zone, không cần slot
    │
    ├── Step 3: Chọn vị trí
    │   ├── GET /parking/floors/?lot_id=... → hiển thị tầng
    │   ├── Chọn tầng → filter zone theo vehicle_type
    │   ├── Chọn zone (hiển thị available/capacity)
    │   ├── (Car only) GET /parking/slots/?zone_id=... → SlotGrid
    │   ├── Chọn ô cụ thể (SlotGrid component)
    │   └── WebSocket: nhận realtime slot status updates
    │
    ├── Step 4: Chọn thời gian
    │   ├── Package: monthly / weekly / hourly / custom (multi-day)
    │   ├── Hourly: chọn ngày + giờ bắt đầu + giờ kết thúc
    │   ├── Custom: MultiDayPicker chọn nhiều ngày
    │   └── PriceSummary sidebar hiển thị giá (⚠️ HARDCODED)
    │
    └── Step 5: Thanh toán
        ├── Chọn: online / on_exit (thanh toán khi lấy xe)
        ├── No-show > 2 lần → forceOnlinePayment (chỉ được chọn online)
        ├── POST /bookings/ → create booking
        │   ├── Backend: fetch vehicle-service (verify xe)
        │   ├── Backend: fetch parking-service (verify slot)
        │   ├── Backend: tính giá từ PackagePricing table
        │   ├── Backend: generate QR code JSON
        │   └── Backend: mark slot as reserved
        ├── Nếu online → redirect PaymentPage (VietQR)
        └── Nếu on_exit → show QR code dialog → History
```

### 3.2 Vấn đề cần fix

| #   | Vấn đề                     | Chi tiết                                                                                                                     | Fix                                                           |
| --- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| 1   | **PriceSummary hardcoded** | `PriceSummary.tsx` dùng const `PRICES = { Car: { hourly: 20000, daily: 100000, ... } }`. Không fetch từ `PackagePricing` API | Tạo endpoint `GET /bookings/pricing/` → Frontend fetch giá    |
| 2   | **Giá FE ≠ BE**            | FE hiển thị giá hardcoded, BE tính từ DB. Nếu admin thay đổi giá → user thấy giá cũ                                          | FE phải gọi API lấy giá real                                  |
| 3   | **No PackagePricing API**  | `PackagePricing` model có trong DB nhưng không có endpoint nào expose                                                        | Thêm `PackagePricingViewSet` hoặc action trong BookingViewSet |
| 4   | **Monthly/Weekly dates**   | Step 4: monthly/weekly chỉ có start date, không generate end_date tự động                                                    | Cần auto-calculate end_date = start + 30d/7d                  |
| 5   | **Slot release on cancel** | Celery task cancel unpaid bookings → broadcast slot release. Nhưng parking-service `available_slots` field KHÔNG tự cập nhật | Cần parking-service listener hoặc slot_status API             |

### 3.3 Cần thêm

```
❌ GET /bookings/pricing/?vehicle_type=Car → return PackagePricing list
❌ Frontend PriceSummary.tsx → fetch from API thay vì hardcode
❌ Auto-calculate end_date cho monthly/weekly
```

---

## 4. FLOW 2: CHECK-IN (VÀO BÃI)

### 4.1 Flow MONG MUỐN (theo yêu cầu user)

```
ESP32 tại cổng vào
    │
    ├── 1. Người dùng bấm nút ESP32
    │
    ├── 2. Camera QR (IP: 192.168.100.130:4747) → capture → đọc QR booking
    │   └── QR chứa: { booking_id, user_id, vehicle_license_plate, ... }
    │
    ├── 3. ✅ QR OK → MỚI mở Camera Biển Số (IP: TBD, chưa mua) → capture biển số xe
    │   └── AI: YOLO detect → OCR read plate → normalize
    │
    ├── 4. Hệ thống verify:
    │   ├── a. QR valid → fetch booking → status = not_checked_in
    │   ├── b. Booking chưa hết hạn (within time window)
    │   ├── c. Biển số OCR == booking.vehicle_license_plate
    │   └── d. Payment status OK (online=completed, on_exit=pending OK)
    │
    ├── 5. Nếu OK:
    │   ├── Update booking: check_in_status = checked_in
    │   ├── Update slot: status = occupied
    │   ├── Broadcast realtime: slot status + booking update
    │   └── ESP32 → MỞ BARRIER
    │
    └── 6. Nếu FAIL:
        ├── Hiển thị lỗi trên màn hình LED/screen
        └── Barrier KHÔNG mở
```

### 4.2 Trạng thái hiện tại

| Step                    | Đã code    | File                                                      | Ghi chú                                                           |
| ----------------------- | ---------- | --------------------------------------------------------- | ----------------------------------------------------------------- |
| QR Parse                | ✅         | `ai-service/routers/parking.py` line 230-240              | Parse JSON từ `qr_data` Form field                                |
| Fetch booking           | ✅         | `ai-service/routers/parking.py` `_get_booking()`          | HTTP call tới booking-service                                     |
| Validate status         | ✅         | `ai-service/routers/parking.py` line 253-268              | Check `checkInStatus == not_checked_in`                           |
| Validate time           | ✅         | `ai-service/routers/parking.py` line 271-287              | Allow 15min early                                                 |
| OCR plate               | ✅         | `ai-service/engine/plate_pipeline.py`                     | Full pipeline: YOLO→blur→OCR→format                               |
| Plate match             | ✅         | `ai-service/routers/parking.py` `_plates_match()`         | Normalize + compare                                               |
| Call booking checkin    | ✅         | `ai-service/routers/parking.py` `_call_booking_checkin()` | HTTP POST to booking-service                                      |
| **ESP32 trigger**       | ❌         | —                                                         | Không có endpoint cho ESP32                                       |
| **Camera auto-capture** | ❌         | —                                                         | Không có code capture từ camera IP                                |
| **QR auto-read**        | ❌         | —                                                         | QR data truyền thủ công qua Form                                  |
| **Barrier control**     | ❌         | —                                                         | Không có API mở/đóng barrier                                      |
| **Slot status update**  | ⚠️ Partial | booking-service `views.py` checkin                        | Broadcast realtime nhưng parking-service slot status KHÔNG update |

### 4.3 CẦN TRIỂN KHAI

#### 4.3.1 ESP32 Integration Endpoint (ai-service)

```
POST /ai/parking/esp32/check-in/
  Headers: X-Gateway-Secret (ESP32 gọi trực tiếp, bypass gateway)
  Body: { "gate_id": "GATE-01", "action": "check_in" }

  Flow (tuần tự, KHÔNG song song):
    1. Nhận trigger từ ESP32
    2. Capture frame từ QR camera (192.168.100.130:4747)
    3. Decode QR code (pyzbar hoặc opencv)
       → NẾU THẤT BẠI: return { success: false, message: "QR không đọc được" }
    4. ✅ QR thành công → Capture frame từ plate camera (IP: TBD)
    5. Gọi pipeline check-in hiện có (OCR plate → match → checkin)
    6. Return: { success, message, barrier_action: "open"/"stay_closed" }
```

#### 4.3.2 Camera Capture Module (ai-service)

```python
# Cần tạo: ai-service-fastapi/app/engine/camera_capture.py

import cv2

class CameraCapture:
    """Capture frames from IP cameras."""

    def __init__(self, camera_url: str):
        self.url = camera_url

    def capture_frame(self) -> bytes:
        """Capture single frame from IP camera."""
        cap = cv2.VideoCapture(self.url)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError(f"Cannot capture from {self.url}")
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()

# Camera URLs (from parking-service Camera model):
# QR Camera: http://192.168.100.130:4747/video (DroidCam)
# Plate Camera: TBD (chưa mua — sẽ cập nhật IP/port sau)
```

#### 4.3.3 QR Code Reader Module (ai-service)

```python
# Cần tạo: ai-service-fastapi/app/engine/qr_reader.py

from pyzbar import pyzbar
import cv2
import numpy as np

class QRReader:
    """Read QR codes from camera frames."""

    def decode(self, image_bytes: bytes) -> dict | None:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        decoded = pyzbar.decode(img)
        if decoded:
            return json.loads(decoded[0].data.decode('utf-8'))
        return None
```

#### 4.3.4 Barrier Control API

```
POST /ai/parking/barrier/
  Body: { "gate_id": "GATE-01", "action": "open" | "close" }

  Option A: ESP32 gọi API sau khi nhận response check-in success
  Option B: AI-service gọi trực tiếp ESP32 qua MQTT/HTTP
  Option C: Return barrier_action trong response, ESP32 tự xử lý

  → Recommend Option C (đơn giản nhất cho prototype)
```

---

## 5. FLOW 3: XÁC MINH TẠI Ô ĐẬU (SLOT VERIFICATION)

### 5.1 Flow mong muốn

```
Xe đã check-in, đi vào ô đậu
    │
    ├── 1. Người dùng bấm nút ESP32 tại ô đậu
    │
    ├── 2. Camera tại zone → capture → đọc QR booking
    │
    ├── 3. Hệ thống verify:
    │   ├── a. Booking có check_in_status == checked_in
    │   ├── b. Booking.slot_id == slot hiện tại (đúng ô)
    │   ├── c. Booking chưa hết hạn
    │   └── d. (Optional) OCR biển số == booking plate
    │
    ├── 4. Nếu OK:
    │   ├── Update slot: status = occupied
    │   ├── Broadcast realtime
    │   └── Mở barrier ô đậu (nếu có)
    │
    └── 5. Nếu SAI Ô:
        ├── Cảnh báo: "Bạn đang ở sai ô! Ô của bạn là X-XX"
        ├── Log incident
        └── Barrier KHÔNG mở
```

### 5.2 Trạng thái hiện tại

| Component                        | Trạng thái                           |
| -------------------------------- | ------------------------------------ |
| Slot-level verification endpoint | ❌ Chưa có                           |
| Booking has slot_id              | ✅ `booking.slot_id` (booking model) |
| Slot has zone FK                 | ✅ `CarSlot.zone` (parking model)    |
| Wrong-slot detection logic       | ❌ Chưa có                           |

### 5.3 CẦN TRIỂN KHAI

#### Endpoint mới (ai-service)

```
POST /ai/parking/esp32/verify-slot/
  Body: { "slot_code": "A-01", "zone_id": "uuid", "gate_id": "SLOT-GATE-01" }

  Flow:
    1. ESP32 tại ô gửi slot info
    2. Camera capture → QR decode → lấy booking_id
    3. Fetch booking → verify:
       - check_in_status == checked_in
       - booking.slot_code == slot_code HOẶC booking.slot_id matches
    4. Return: { verified: true/false, message, correct_slot: "A-05" }
```

#### Booking-service cần thêm

```
GET /bookings/by-slot/?slot_id=xxx&status=checked_in
  → Return booking đang active tại slot đó
```

---

## 6. FLOW 4: GIÁM SÁT CAMERA (SLOT DETECTION)

### 6.1 Flow mong muốn

```
Camera giám sát (1 camera = 5 slots)
    │
    ├── Liên tục chụp frame (mỗi 5-10 giây)
    │
    ├── AI Pipeline:
    │   ├── 1. YOLO detect xe trong frame
    │   ├── 2. Map xe → slot (dùng bounding box x1,y1,x2,y2 từ CarSlot model)
    │   ├── 3. Xác định slot status:
    │   │   ├── available: không có xe trong bbox
    │   │   ├── occupied: có xe trong bbox
    │   │   ├── wrong_parking: xe nằm ngoài bbox hoặc cross-boundary
    │   │   └── lane_violation: xe lấn vào lane di chuyển
    │   ├── 4. (Optional) OCR biển số → so sánh với booking assigned
    │   └── 5. Phân biệt box-type vs line-type parking
    │
    ├── So sánh với trạng thái trước:
    │   ├── Nếu thay đổi → update slot status
    │   ├── Broadcast realtime → frontend SlotGrid
    │   └── Nếu wrong parking → tạo incident + notify user
    │
    └── Dashboard admin:
        ├── View camera feeds (CamerasPage)
        ├── View slot heatmap
        └── View violations list
```

### 6.2 Trạng thái hiện tại

| Component                            | Trạng thái     | File                                                                          |
| ------------------------------------ | -------------- | ----------------------------------------------------------------------------- |
| CarSlot model có bbox                | ✅             | `parking-service/models.py` — `x1, y1, x2, y2, camera FK`                     |
| Camera model                         | ✅             | `parking-service/models.py` — `ip_address, port, stream_url, zone, is_active` |
| CarSlot has camera FK                | ✅             | `camera = ForeignKey('Camera', related_name='monitored_slots')`               |
| YOLO detector                        | ✅             | `ai-service/engine/detector.py` — YOLOv8 loaded                               |
| Slot detection pipeline              | ❌             | Chưa có pipeline cho slot occupancy                                           |
| Wrong-slot detection                 | ❌             | —                                                                             |
| Lane violation detection             | ❌             | —                                                                             |
| Camera frame capture loop            | ❌             | —                                                                             |
| Slot status update → parking-service | ❌             | —                                                                             |
| CamerasPage live stream              | ⚠️ Placeholder | `CamerasPage.tsx` — shows "Live Feed" text, no actual stream                  |

### 6.3 CẦN TRIỂN KHAI

#### 6.3.1 Slot Detection Pipeline (ai-service)

```python
# Cần tạo: ai-service-fastapi/app/engine/slot_detection.py

class SlotDetectionPipeline:
    """
    Detect parking slot occupancy from camera frames.
    Uses YOLO to detect vehicles, then maps to slot bounding boxes.
    """

    def __init__(self, yolo_model):
        self.detector = yolo_model  # Reuse existing YOLO detector

    def process_frame(self, frame: np.ndarray, slots: list[SlotBBox]) -> list[SlotStatus]:
        """
        1. YOLO detect all vehicles in frame
        2. For each slot bbox, check IoU with detected vehicles
        3. Determine: available / occupied / wrong_parking
        """
        detections = self.detector.detect(frame)  # [{bbox, class, confidence}]

        results = []
        for slot in slots:
            # Calculate IoU between each detection and slot bbox
            best_iou = 0
            for det in detections:
                iou = self._calculate_iou(slot.bbox, det.bbox)
                best_iou = max(best_iou, iou)

            if best_iou > 0.3:
                status = "occupied"
            elif best_iou > 0.1:
                status = "wrong_parking"  # Partially in slot
            else:
                status = "available"

            results.append(SlotStatus(slot_id=slot.id, status=status, confidence=best_iou))

        return results
```

#### 6.3.2 Camera Monitoring Worker (ai-service)

```python
# Cần tạo: ai-service-fastapi/app/workers/camera_monitor.py

class CameraMonitorWorker:
    """Background worker that monitors cameras and updates slot status."""

    async def run(self):
        """Main loop: fetch cameras → capture → detect → update."""
        while True:
            cameras = await self._fetch_active_cameras()
            for camera in cameras:
                try:
                    frame = self.capture.capture_frame(camera.stream_url)
                    slots = await self._fetch_camera_slots(camera.id)
                    results = self.pipeline.process_frame(frame, slots)

                    for result in results:
                        if result.status_changed:
                            await self._update_slot_status(result)
                            await self._broadcast_update(result)

                            if result.status == "wrong_parking":
                                await self._create_incident(result)
                except Exception as e:
                    logger.error(f"Camera {camera.id} error: {e}")

            await asyncio.sleep(5)  # Every 5 seconds
```

#### 6.3.3 Parking-service: Slot Status Update API

```
PATCH /parking/slots/{slot_id}/status/
  Body: { "status": "occupied" | "available" | "maintenance" }
  Headers: X-Gateway-Secret (internal only)

  → Update slot status
  → Update zone.available_slots (increment/decrement)
  → Return updated slot
```

#### 6.3.4 Frontend: Camera Live Stream

```
CamerasPage.tsx cần:
1. Fetch camera.stream_url từ API
2. Render <img src={stream_url} /> cho MJPEG streams
3. Hoặc dùng WebRTC / HLS cho better streaming
4. Overlay slot bounding boxes trên video (canvas)
5. Show slot status indicators (green=available, red=occupied)
```

#### 6.3.5 Box-type vs Line-type Parking

```
- Box-type: Xe nằm hoàn toàn trong bbox → simple IoU check
- Line-type: Xe nằm giữa 2 vạch → detect vạch + check xe position
- Cần train YOLO model nhận diện vạch kẻ ô đậu
- Hoặc define polygon thay vì rectangle cho slot boundary
```

---

## 7. FLOW 5: CHECK-OUT (RA BÃI + THANH TOÁN)

### 7.1 Flow mong muốn

```
Xe muốn ra bãi
    │
    ├── 1. Bấm nút ESP32 tại cổng ra
    │
    ├── 2. Camera QR → scan booking QR
    │
    ├── 3. Hệ thống verify:
    │   ├── a. Booking status == checked_in
    │   ├── b. OCR biển số khớp
    │   └── c. ⚠️ KIỂM TRA THANH TOÁN
    │
    ├── 4. Kiểm tra payment:
    │   │
    │   ├── Case A: payment_method=online, payment_status=completed
    │   │   └── ✅ Đã thanh toán → mở barrier
    │   │
    │   ├── Case B: payment_method=on_exit
    │   │   ├── Tính: base_price + late_fee (nếu quá giờ)
    │   │   ├── Hiển thị tổng tiền lên screen
    │   │   │
    │   │   ├── Sub-case B1: Thanh toán chuyển khoản
    │   │   │   ├── Hiển thị QR VietQR trên screen
    │   │   │   ├── Chờ user chuyển khoản
    │   │   │   ├── (Ideal) Auto-verify via bank webhook
    │   │   │   ├── (Current) Manual confirm
    │   │   │   └── Sau khi confirm → mở barrier
    │   │   │
    │   │   ├── Sub-case B2: Thanh toán tiền mặt
    │   │      ├── User nhét tiền vào khe (hoặc đưa trước camera)
    │   │      ├── AI nhận diện mệnh giá tiền
    │   │      ├── Cộng dồn cho đến khi đủ/thừa
    │   │      ├── Tính tiền thối (nếu có)
    │   │      └── Sau khi đủ → mở barrier
    │   │
    │   │
    │   └── Case C: Chưa thanh toán → KHÔNG mở barrier
    │       └── Hiển thị: "Vui lòng thanh toán trước khi ra"
    │
    ├── 5. Sau thanh toán OK:
    │   ├── Update booking: check_in_status = checked_out
    │   ├── Update payment_status = completed
    │   ├── Update slot: status = available
    │   ├── Broadcast realtime
    │   └── MỞ BARRIER
    │
    └── 6. Special cases:
        ├── Quá giờ: late_fee = overtime_hours × hourly_rate × 1.5
        ├── Xe sai biển số → reject, gọi nhân viên
        └── Booking đã checkout → reject
```

### 7.2 Trạng thái hiện tại

| Component                     | Trạng thái | Chi tiết                                                          |
| ----------------------------- | ---------- | ----------------------------------------------------------------- |
| AI check-out (QR + plate)     | ✅         | `ai-service/routers/parking.py` check_out endpoint                |
| Booking checkout logic        | ✅         | `booking-service/views.py` checkout action (late fee calculation) |
| Payment-before-barrier check  | ❌         | **KHÔNG** kiểm tra payment trước khi cho ra                       |
| Cash payment flow             | ❌         | AI detect tiền có sẵn, nhưng KHÔNG connect vào checkout flow      |
| Transfer QR at exit           | ❌         | Chỉ có PaymentPage web, không có tại cổng                         |
| ESP32 check-out trigger       | ❌         | —                                                                 |
| Barrier control after payment | ❌         | —                                                                 |

### 7.3 CẦN TRIỂN KHAI

#### 7.3.1 Check-out Flow với Payment Verification

```
POST /ai/parking/esp32/check-out/
  Body: { "gate_id": "GATE-EXIT-01" }

  Flow:
    1. Camera capture QR → parse booking_id
    2. Camera capture plate → OCR
    3. Fetch booking + verify plate match
    4. CHECK PAYMENT:
       a. If payment_status == completed → proceed to step 5
       b. If payment_method == on_exit:
          - Calculate total = base_price + late_fee
          - Return: {
              status: "awaiting_payment",
              total_amount: 85000,
              late_fee: 15000,
              payment_options: ["cash", "transfer", "qr"]
            }
          - ESP32 screen hiển thị options
          - Chờ payment completion (polling hoặc WebSocket)
    5. After payment confirmed:
       - Call booking checkout
       - Return: { barrier_action: "open" }
```

#### 7.3.2 Payment Completion Endpoint (for ESP32 checkout)

```
POST /ai/parking/esp32/check-out/payment/
  Body: {
    "booking_id": "uuid",
    "payment_method": "cash",
    "cash_images": [UploadFile],  // Ảnh tiền mặt
    "total_required": 85000
  }

  Flow (cash):
    1. AI detect mỗi ảnh tiền → tổng = sum(denominations)
    2. If tổng >= total_required:
       a. Create payment record (status=completed)
       b. Update booking payment_status=completed
       c. Return: { paid: true, change: tổng - total_required, barrier_action: "open" }
    3. If tổng < total_required:
       Return: { paid: false, current_total: tổng, remaining: total_required - tổng }
```

---

## 8. FLOW 6: THANH TOÁN TIỀN MẶT (AI CASH RECOGNITION)

### 8.1 Trạng thái hiện tại

| Component                       | Trạng thái | File                                                               |
| ------------------------------- | ---------- | ------------------------------------------------------------------ |
| Cash detection endpoint         | ✅         | `ai-service/routers/detection.py` `/ai/detect/cash/`               |
| Banknote detection              | ✅         | `ai-service/routers/detection.py` `/ai/detect/banknote/`           |
| BanknoteRecognitionPipeline     | ✅         | `ai-service/engine/pipeline.py` — HSV color + YOLOv8 + AI fallback |
| ResNet50 cash classifier        | ✅ (plan)  | Training pipeline ready in `routers/training.py`                   |
| EfficientNetV2-S classifier     | ✅ (plan)  | Bank-grade pipeline in training                                    |
| Frontend BanknoteDetectionPage  | ✅         | Upload ảnh → detect → hiển thị kết quả                             |
| **Cash → Checkout integration** | ❌         | AI detect tiền ✅ nhưng KHÔNG connect vào payment/checkout flow    |
| **Running total accumulation**  | ❌         | Không có session tracking "đã nhét bao nhiêu tiền"                 |
| **Change calculation**          | ❌         | —                                                                  |

### 8.2 CẦN TRIỂN KHAI

#### Cash Payment Session (ai-service hoặc payment-service)

```python
# Redis-based cash payment session
class CashPaymentSession:
    """Track running total of cash inserted during checkout."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def start(self, booking_id: str, total_required: float):
        key = f"cash_session:{booking_id}"
        await self.redis.hset(key, mapping={
            "total_required": total_required,
            "current_total": 0,
            "denominations": "[]",
            "status": "active"
        })
        await self.redis.expire(key, 600)  # 10 min timeout

    async def add_cash(self, booking_id: str, denomination: int) -> dict:
        key = f"cash_session:{booking_id}"
        current = float(await self.redis.hget(key, "current_total"))
        required = float(await self.redis.hget(key, "total_required"))

        new_total = current + denomination
        await self.redis.hset(key, "current_total", new_total)

        if new_total >= required:
            change = new_total - required
            await self.redis.hset(key, "status", "completed")
            return {"paid": True, "change": change, "total_paid": new_total}
        else:
            return {"paid": False, "remaining": required - new_total, "total_paid": new_total}
```

#### Endpoint mới

```
POST /ai/parking/cash-payment/
  Body: { "booking_id": "uuid", "image": UploadFile }

  Flow:
    1. AI detect denomination from image
    2. Add to running total in Redis session
    3. Return: { denomination: 50000, total_paid: 70000, remaining: 15000, paid: false }
    4. Khi đủ: Return: { paid: true, change: 5000, barrier_action: "open" }
```

---

## 9. FILE THỪA / CẦN XOÁ

### 9.1 Backend Files

| File                                              | Lý do                                                            | Action                              |
| ------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------- |
| `backend-microservices/_check_payments.py`        | Test script, không phải production code                          | ⚠️ Giữ nếu cần test, xoá nếu không  |
| `backend-microservices/_health.py`                | Quick health check script                                        | ⚠️ Giữ cho dev                      |
| `backend-microservices/_test_zones.py`            | Quick test script                                                | ⚠️ Giữ cho dev                      |
| `backend-microservices/test_chatbot_e2e.py`       | Root-level test → nên nằm trong `chatbot-service-fastapi/tests/` | 🔄 Move                             |
| `backend-microservices/test_chatbot_lifecycle.py` | Root-level test → nên nằm trong `chatbot-service-fastapi/tests/` | 🔄 Move                             |
| `backend-microservices/test_e2e_full_flow.py`     | Root-level e2e test                                              | ⚠️ Giữ hoặc move to `tests/` folder |
| `booking-service/create_incident_table.py`        | One-time migration script, nên dùng Django migration             | 🔄 Chuyển sang migration            |

### 9.2 Frontend Files

| Component                             | Vấn đề                   | Action                      |
| ------------------------------------- | ------------------------ | --------------------------- |
| `PriceSummary.tsx` hardcoded `PRICES` | Giá hardcode sẽ outdated | 🔄 Refactor: fetch from API |

### 9.3 Files KHÔNG thừa (giải thích)

| File                       | Tưởng thừa nhưng KHÔNG | Lý do                                     |
| -------------------------- | ---------------------- | ----------------------------------------- |
| `AI.md`                    | Documentation          | Giữ — plan cho banknote hybrid MVP        |
| `AI_nhan_dien_tien_mat.md` | Documentation          | Giữ — plan cho ATM-grade cash recognition |
| `chatbot_plan.md`          | Documentation          | Giữ — chatbot implementation plan         |
| `COPILOT_MASTER_PLAN.md`   | Master documentation   | Giữ — architecture bible                  |

---

## 10. BUGS / INCONSISTENCIES PHÁT HIỆN ĐƯỢC

### 10.1 Critical Bugs

| #   | Bug                                    | Service         | File                           | Chi tiết                                                                                                                                         |
| --- | -------------------------------------- | --------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | **PriceSummary hardcoded**             | Frontend        | `PriceSummary.tsx` L28-39      | `PRICES = { Car: { hourly: 20000 } }` — Không fetch từ `PackagePricing` API. Nếu admin đổi giá DB, FE vẫn hiển thị giá cũ                        |
| 2   | **Check-out không kiểm tra payment**   | ai-service      | `routers/parking.py` check_out | Chỉ check `check_in_status == checked_in`, KHÔNG check `payment_status`. Xe có thể ra mà chưa trả tiền                                           |
| 3   | **Slot status không sync**             | parking-service | `models.py` + `views.py`       | `Zone.available_slots` là static field, KHÔNG auto-update khi slot status thay đổi. Booking checkin broadcast nhưng parking-service không listen |
| 4   | **Camera live stream = placeholder**   | Frontend        | `CamerasPage.tsx`              | Shows "Live Feed" text + Video icon. Không render actual `stream_url`                                                                            |
| 5   | **Booking checkout không update slot** | booking-service | `views.py` checkout            | Checkout chỉ update booking status, KHÔNG call parking-service để release slot                                                                   |

### 10.2 High Priority Bugs

| #   | Bug                                 | Service         | File                   | Chi tiết                                                                                                                                                                |
| --- | ----------------------------------- | --------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 6   | **PaymentPage manual confirm**      | Frontend        | `PaymentPage.tsx` L466 | "Tôi đã thanh toán" button → gọi API confirm. Không có webhook auto-verify. User có thể bấm confirm mà chưa chuyển khoản                                                |
| 7   | **No PackagePricing endpoint**      | booking-service | —                      | `PackagePricing` model exists nhưng không có API endpoint nào expose cho FE                                                                                             |
| 8   | **AI API client thiếu**             | Frontend        | `ai.api.ts`            | Chỉ có `detectBanknote()`. Thiếu: `scanPlate()`, `checkIn()`, `checkOut()`                                                                                              |
| 9   | **Booking serializer HTTP calls**   | booking-service | `serializers.py` L~200 | `CreateBookingSerializer.validate()` gọi HTTP tới vehicle-service + parking-service TRONG serializer. Nếu service down → 500 error cho user. Nên move vào service layer |
| 10  | **Checkout late_fee không persist** | booking-service | `views.py` checkout    | Tính `late_fee` nhưng check xem field `late_fee` có được save() không — cần verify                                                                                      |

### 10.3 Medium Bugs

| #   | Bug                           | Service         | Chi tiết                                                                                                     |
| --- | ----------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------ |
| 11  | `PriceSummary` discount logic | Frontend        | Monthly -20%, Weekly -10% — hardcoded discounts. `PackagePricing` model không có discount field              |
| 12  | `BookingPage` monthly/weekly  | Frontend        | Step 4: monthly/weekly chỉ có start date picker, không tính end_date                                         |
| 13  | WebSocket reconnection        | Frontend        | `websocket.service.ts` có reconnect logic nhưng cần verify timeout handling                                  |
| 14  | Camera model `is_active`      | parking-service | COPILOT_MASTER_PLAN ghi Bug 14: `camera.status` KHÔNG tồn tại, phải dùng `is_active`. Cần verify đã fix chưa |

---

## 11. CẢI TIẾN CẦN THIẾT (IMPROVEMENTS)

### 11.1 Backend Improvements

| #   | Cải tiến                                 | Service              | Priority | Chi tiết                                                                               |
| --- | ---------------------------------------- | -------------------- | -------- | -------------------------------------------------------------------------------------- |
| 1   | **PackagePricing API**                   | booking-service      | 🔴       | Thêm `GET /bookings/pricing/?vehicle_type=Car`                                         |
| 2   | **Slot status sync mechanism**           | parking-service      | 🔴       | Auto-update `Zone.available_slots` khi slot status thay đổi. Dùng signal hoặc listener |
| 3   | **Payment verification before checkout** | ai-service + booking | 🔴       | Check `payment_status == completed` trước khi cho ra                                   |
| 4   | **ESP32 endpoints**                      | ai-service           | 🔴       | `check-in`, `check-out`, `verify-slot` endpoints cho ESP32                             |
| 5   | **Camera capture module**                | ai-service           | 🔴       | Auto-capture frame từ IP camera                                                        |
| 6   | **QR reader module**                     | ai-service           | 🔴       | Auto-read QR code từ camera frame                                                      |
| 7   | **Slot detection pipeline**              | ai-service           | 🔴       | YOLO detect → map to slot bbox → status update                                         |
| 8   | **Camera monitoring worker**             | ai-service           | 🟡       | Background loop: capture → detect → update slot status                                 |
| 9   | **Cash payment session**                 | ai-service/payment   | 🟡       | Redis session tracking running total                                                   |
| 10  | **Checkout slot release**                | booking-service      | 🟡       | Checkout action phải call parking-service release slot                                 |
| 11  | **Business logic extraction**            | booking-service      | 🟡       | Move logic từ views.py → services.py (per COPILOT_MASTER_PLAN Bug 13)                  |
| 12  | **RabbitMQ events**                      | All services         | 🟢       | Thay thế direct HTTP calls bằng event-driven (per master plan)                         |
| 13  | **Transactional outbox**                 | All services         | 🟢       | Đảm bảo event publish consistency (per master plan H.2)                                |

### 11.2 Frontend Improvements

| #   | Cải tiến                     | Component                | Priority | Chi tiết                                                        |
| --- | ---------------------------- | ------------------------ | -------- | --------------------------------------------------------------- |
| 1   | **PriceSummary → API**       | `PriceSummary.tsx`       | 🔴       | Xoá hardcoded `PRICES`, fetch từ `GET /bookings/pricing/`       |
| 2   | **Camera live stream**       | `CamerasPage.tsx`        | 🟡       | Render `stream_url` thay vì placeholder. Dùng `<img>` cho MJPEG |
| 3   | **AI API client**            | `ai.api.ts`              | 🟡       | Thêm `scanPlate()`, `checkIn()`, `checkOut()`                   |
| 4   | **Auto payment verify**      | `PaymentPage.tsx`        | 🟡       | Polling `GET /payments/{id}/` mỗi 5s thay vì manual confirm     |
| 5   | **Monthly/weekly end date**  | `BookingPage.tsx` Step 4 | 🟡       | Auto-fill end_date = start + 30d/7d                             |
| 6   | **Slot overlay on camera**   | `CamerasPage.tsx`        | 🟢       | Canvas overlay with slot bounding boxes + status indicators     |
| 7   | **Check-in/out status page** | New page                 | 🟢       | Real-time check-in/out status display for kiosk screen          |

---

## 12. TASK BREAKDOWN CHI TIẾT

### Phase A: Foundation — ESP32 & Camera Integration (🔴 Highest Priority)

```
A1. @architect: Design ESP32 ↔ AI-service API contracts
    - POST /ai/parking/esp32/check-in/
    - POST /ai/parking/esp32/check-out/
    - POST /ai/parking/esp32/verify-slot/
    - Response schema with barrier_action field

A2. @coder-backend [ai-service-fastapi]: Camera Capture Module
    - File: app/engine/camera_capture.py
    - CameraCapture class: capture_frame(url) → bytes
    - Support MJPEG (DroidCam), RTSP, HTTP snapshot
    - Camera URL: 192.168.100.130:4747

A3. @coder-backend [ai-service-fastapi]: QR Code Reader Module
    - File: app/engine/qr_reader.py
    - QRReader class: decode(image_bytes) → dict
    - Dependencies: pyzbar, opencv-python

A4. @coder-backend [ai-service-fastapi]: ESP32 Check-in Endpoint
    - File: app/routers/esp32.py
    - POST /ai/parking/esp32/check-in/
    - Flow: trigger → capture QR → capture plate → existing check-in pipeline

A5. @coder-backend [ai-service-fastapi]: ESP32 Check-out Endpoint
    - File: app/routers/esp32.py
    - POST /ai/parking/esp32/check-out/
    - Flow: trigger → QR → plate → payment check → checkout

A6. @coder-backend [ai-service-fastapi]: ESP32 Verify-slot Endpoint
    - File: app/routers/esp32.py
    - POST /ai/parking/esp32/verify-slot/
    - Flow: trigger → QR → verify booking slot == physical slot

A7. @tester: E2E tests cho ESP32 endpoints
    - Test check-in flow end-to-end
    - Test check-out with payment verification
    - Test verify-slot correct/wrong scenarios
```

### Phase B: Payment-Before-Barrier (🔴 Critical)

```
B1. @architect: Design checkout-with-payment flow
    - State machine: check-out → awaiting_payment → paid → barrier_open
    - Cash/transfer/QR payment options

B2. @coder-backend [ai-service-fastapi]: Payment verification in check-out
    - Modify: app/routers/parking.py check_out (or esp32.py)
    - Add: check payment_status before allowing barrier open
    - Add: return payment_required with amount if unpaid

B3. @coder-backend [ai-service-fastapi]: Cash payment endpoint
    - File: app/routers/esp32.py
    - POST /ai/parking/esp32/cash-payment/
    - Cash session in Redis: running total, denominations

B4. @coder-backend [payment-service-fastapi]: On-site payment initiation
    - Add: payment method "on_site_cash", "on_site_transfer"
    - Webhook endpoint for bank transfer verification

B5. @tester: Payment flow tests
    - Test: online payment already completed → barrier opens
    - Test: on_exit → cash → amount accumulation → barrier opens
    - Test: on_exit → transfer → manual/auto confirm → barrier opens
    - Test: insufficient cash → barrier stays closed
```

### Phase C: Slot Detection & Camera Monitoring (🟡 High)

```
C1. @architect: Design slot detection pipeline architecture
    - Camera → Frame → YOLO → Slot mapping → Status update flow
    - Data flow: ai-service → parking-service → realtime-service → frontend

C2. @coder-backend [ai-service-fastapi]: Slot Detection Pipeline
    - File: app/engine/slot_detection.py
    - SlotDetectionPipeline class
    - YOLO detect → IoU with slot bbox → status determination
    - Support: box-type + line-type parking

C3. @coder-backend [ai-service-fastapi]: Camera Monitoring Worker
    - File: app/workers/camera_monitor.py
    - Background async loop: capture → detect → compare → update
    - Configurable interval (default 5s)
    - Start in FastAPI lifespan

C4. @coder-backend [parking-service]: Slot Status Update API
    - PATCH /parking/slots/{id}/status/
    - Internal only (X-Gateway-Secret)
    - Auto-update Zone.available_slots

C5. @coder-backend [parking-service]: Zone available_slots sync
    - Signal/trigger: when slot status changes → recalculate zone available_slots
    - Or: computed property based on slot queryset

C6. @coder-frontend: Camera live stream rendering
    - CamerasPage.tsx: render actual stream_url
    - Support MJPEG: <img src={streamUrl} />
    - Fallback: snapshot refresh every 2s

C7. @coder-frontend: Slot overlay on camera feed
    - Canvas overlay: draw bounding boxes from slot x1,y1,x2,y2
    - Color code: green=available, red=occupied, yellow=violation

C8. @tester: Slot detection tests
    - Unit: IoU calculation
    - Integration: pipeline with sample images
    - E2E: camera → detect → slot status update → WS broadcast
```

### Phase D: Booking & Pricing Fixes (🟡 High)

```
D1. @coder-backend [booking-service]: PackagePricing API endpoint
    - GET /bookings/pricing/?vehicle_type=Car
    - Return list of PackagePricing objects

D2. @coder-frontend: PriceSummary fetch from API
    - Remove hardcoded PRICES const
    - Add usePackagePricing() hook → fetch from API
    - Cache in Redux store

D3. @coder-backend [booking-service]: Checkout slot release
    - In checkout action: call parking-service to release slot
    - PATCH /parking/slots/{id}/status/ → "available"

D4. @coder-backend [booking-service]: Auto-calculate end_date
    - monthly: end_date = start_date + 30 days
    - weekly: end_date = start_date + 7 days

D5. @coder-frontend: Monthly/weekly end_date display
    - Step 4: auto-fill and show calculated end_date

D6. @coder-frontend: AI API client expansion
    - ai.api.ts: add scanPlate(), checkIn(), checkOut()

D7. @coder-frontend: Payment auto-verification polling
    - PaymentPage.tsx: poll GET /payments/{booking_id}/ every 5s
    - Auto-redirect when status=completed

D8. @tester: Pricing + booking tests
    - Test PackagePricing API
    - Test PriceSummary renders API prices
    - Test checkout releases slot
```

### Phase E: Wrong-parking & Violations (🟢 Medium)

```
E1. @architect: Design incident/violation data model
    - Incident: { booking_id, slot_id, type, evidence_image, status }
    - Types: wrong_slot, lane_violation, overtime, no_show

E2. @coder-backend [booking-service]: Incident model + API
    - Model: Incident (booking FK, slot FK, type, evidence, resolved)
    - POST /bookings/incidents/ (internal)
    - GET /bookings/incidents/ (admin)

E3. @coder-backend [ai-service-fastapi]: Wrong-slot detection
    - Compare OCR plate with booking.slot assignment
    - If mismatch → create incident

E4. @coder-backend [ai-service-fastapi]: Lane violation detection
    - Detect vehicle bounding box overlapping with lane markers
    - Requires: lane marker annotation data

E5. @coder-frontend: Admin violations page
    - List incidents with evidence images
    - Resolve/dismiss actions

E6. @tester: Violation tests
```

---

## 13. SERVICE IMPACT MAP

| Service                         | Framework  | Impact               | Tasks                                                         |
| ------------------------------- | ---------- | -------------------- | ------------------------------------------------------------- |
| `auth-service/`                 | Django DRF | ➖ Không ảnh hưởng   | —                                                             |
| `parking-service/`              | Django DRF | ✅ Affected          | C4, C5: Slot status update API + zone sync                    |
| `vehicle-service/`              | Django DRF | ➖ Không ảnh hưởng   | —                                                             |
| `booking-service/`              | Django DRF | ✅ Affected          | D1, D3, D4, E2: Pricing API, checkout slot release, incidents |
| `notification-service-fastapi/` | FastAPI    | ⚠️ Minor             | Notification for violations                                   |
| `payment-service-fastapi/`      | FastAPI    | ✅ Affected          | B4: On-site payment methods                                   |
| `chatbot-service-fastapi/`      | FastAPI    | ➖ Không ảnh hưởng   | —                                                             |
| `ai-service-fastapi/`           | FastAPI    | ✅ **MOST Affected** | A2-A6, B2-B3, C2-C3, E3-E4: ESP32, camera, detection          |
| `gateway-service-go/`           | Golang Gin | ⚠️ Minor             | May need ESP32 bypass route                                   |
| `realtime-service-go/`          | Golang Gin | ⚠️ Minor             | Already has broadcast, may need new event types               |
| `spotlove-ai/`                  | React+Vite | ✅ Affected          | C6-C7, D2, D5-D7: Camera, pricing, payment                    |

---

## 14. RISK ASSESSMENT

### 14.1 Technical Risks

| Risk                                   | Impact    | Probability | Mitigation                                                                     |
| -------------------------------------- | --------- | ----------- | ------------------------------------------------------------------------------ |
| Camera IP thay đổi                     | 🔴 High   | 🟡 Medium   | Config camera URL qua environment variable, không hardcode                     |
| ESP32 network instability              | 🔴 High   | 🟡 Medium   | Retry logic + offline fallback (cache last QR)                                 |
| AI YOLO accuracy cho slot detection    | 🟡 Medium | 🟡 Medium   | Fine-tune trên dataset parking lot thực. Fallback: manual monitoring           |
| OCR accuracy thấp                      | 🟡 Medium | 🟢 Low      | Pipeline đã có 3-tier OCR (TrOCR → EasyOCR → Tesseract) + confidence threshold |
| Cash recognition sai denomination      | 🔴 High   | 🟡 Medium   | Multi-stage pipeline (HSV + YOLO + ResNet). Set confidence threshold cao       |
| Camera latency / dropped frames        | 🟡 Medium | 🟡 Medium   | Buffer frames, retry capture, timeout handling                                 |
| Race condition: 2 xe check-in cùng lúc | 🟡 Medium | 🟢 Low      | DB lock trên booking + slot status update                                      |
| Payment webhook not received           | 🟡 Medium | 🟡 Medium   | Polling fallback + manual confirm button                                       |

### 14.2 Integration Risks

| Risk                                   | Impact    | Mitigation                                                        |
| -------------------------------------- | --------- | ----------------------------------------------------------------- |
| ESP32 ↔ AI-service auth                | 🟡 Medium | ESP32 gửi X-Gateway-Secret header trực tiếp                       |
| Camera format mismatch (MJPEG vs RTSP) | 🟡 Medium | Support multiple capture backends in CameraCapture                |
| Parking-service slot count mismatch    | 🔴 High   | Periodic reconciliation task: count slots vs Zone.available_slots |
| QR code damaged/unreadable             | 🟡 Medium | Retry capture + fallback: manual booking ID input on screen       |

### 14.3 Recommended Implementation Order

```
Week 1-2: Phase A (ESP32 + Camera Integration)
    ├── A2: Camera capture module
    ├── A3: QR reader module
    ├── A4: ESP32 check-in endpoint
    └── A5: ESP32 check-out endpoint

Week 2-3: Phase B (Payment-Before-Barrier)
    ├── B2: Payment verification in check-out
    ├── B3: Cash payment endpoint
    └── B4: On-site payment methods

Week 3-4: Phase D (Pricing & Booking Fixes)
    ├── D1: PackagePricing API
    ├── D2: PriceSummary from API
    ├── D3: Checkout slot release
    └── D7: Payment auto-polling

Week 4-6: Phase C (Slot Detection)
    ├── C2: Slot detection pipeline
    ├── C3: Camera monitoring worker
    ├── C4: Slot status update API
    └── C6-C7: Frontend camera + overlay

Week 6-8: Phase E (Violations)
    ├── E2: Incident model
    ├── E3: Wrong-slot detection
    └── E5: Admin violations page
```

---

## APPENDIX A: API CONTRACTS SUMMARY

### Endpoints CẦN TẠO MỚI

```
ai-service-fastapi:
  POST /ai/parking/esp32/check-in/          ← ESP32 trigger check-in
  POST /ai/parking/esp32/check-out/          ← ESP32 trigger check-out
  POST /ai/parking/esp32/verify-slot/        ← ESP32 verify đúng ô
  POST /ai/parking/esp32/cash-payment/       ← Nhận tiền mặt từ camera
  POST /ai/parking/slot-detection/process/   ← Manual trigger slot detect

booking-service:
  GET  /bookings/pricing/                    ← PackagePricing list
  GET  /bookings/by-slot/?slot_id=...        ← Booking active tại slot
  POST /bookings/incidents/                  ← Tạo incident (internal)
  GET  /bookings/incidents/                  ← List incidents (admin)

parking-service:
  PATCH /parking/slots/{id}/status/          ← Update slot status (internal)
```

### Endpoints ĐÃ CÓ (tham khảo)

```
ai-service-fastapi:
  POST /ai/parking/scan-plate/              ✅
  POST /ai/parking/check-in/               ✅
  POST /ai/parking/check-out/              ✅
  POST /ai/detect/license-plate/           ✅
  POST /ai/detect/cash/                    ✅
  POST /ai/detect/banknote/                ✅
  POST /ai/train/cash/                     ✅
  POST /ai/train/banknote/                 ✅
  GET  /ai/models/metrics/                 ✅
  GET  /ai/models/predictions/             ✅
  GET  /ai/models/versions/                ✅

booking-service:
  GET/POST /bookings/                      ✅
  POST /bookings/{id}/checkin/             ✅
  POST /bookings/{id}/checkout/            ✅
  POST /bookings/{id}/cancel/              ✅
  GET  /bookings/current-parking/          ✅
  GET  /bookings/upcoming/                 ✅
  GET  /bookings/stats/                    ✅

parking-service:
  GET /parking/lots/                        ✅
  GET /parking/lots/nearest/                ✅
  GET /parking/lots/{id}/availability/      ✅
  GET /parking/floors/                      ✅
  GET /parking/zones/                       ✅
  GET /parking/slots/                       ✅
  GET /parking/cameras/                     ✅

payment-service:
  POST /payments/initiate/                  ✅
  POST /payments/verify/                    ✅
  GET  /payments/                           ✅
```

---

## APPENDIX B: EVENT SCHEMA (RabbitMQ)

### Events CẦN THÊM

| Event                   | Source     | Consumers                               | Data                                                                        |
| ----------------------- | ---------- | --------------------------------------- | --------------------------------------------------------------------------- |
| `slot.status_changed`   | ai-service | parking, realtime                       | `{slot_id, zone_id, old_status, new_status, detected_by: "camera"}`         |
| `parking.violation`     | ai-service | booking (create incident), notification | `{slot_id, booking_id, type: "wrong_slot"\|"lane_violation", evidence_url}` |
| `payment.cash_received` | ai-service | payment, realtime                       | `{booking_id, denomination, running_total, required_total}`                 |
| `barrier.opened`        | ai-service | realtime                                | `{gate_id, booking_id, action: "check_in"\|"check_out"}`                    |

---

## APPENDIX C: HARDWARE SETUP

### Cổng vào (Gate In)

```
┌─────────────────────────────────────┐
│  Gate In                            │
│                                     │
│  [ESP32] ←── Button                 │
│     │                               │
│     ├── Camera #1: QR Scanner       │
│     │   IP: 192.168.100.130:4747    │
│     │   (DroidCam / IP Webcam)      │
│     │   → Quét QR booking TRƯỚC     │
│     │                               │
│     ├── Camera #2: Plate Capture    │
│     │   IP: TBD (chưa mua)         │
│     │   → Chỉ mở SAU KHI QR OK     │
│     │                               │
│     ├── LED Screen (status display) │
│     │                               │
│     └── Barrier Motor               │
│         (controlled by ESP32 relay) │
│                                     │
└─────────────────────────────────────┘
```

### Cổng ra (Gate Out)

```
┌─────────────────────────────────────┐
│  Gate Out                           │
│                                     │
│  [ESP32] ←── Button                 │
│     │                               │
│     ├── Camera: QR + Plate (shared) │
│     │                               │
│     ├── LED Screen                  │
│     │   (amount, QR payment, status)│
│     │                               │
│     ├── Cash Slot Camera            │
│     │   (nhận diện tiền mặt)        │
│     │                               │
│     └── Barrier Motor               │
│                                     │
└─────────────────────────────────────┘
```

### Khu vực đậu xe (Parking Zone)

```
┌──────────────────────────────────────────┐
│  Zone A (5 slots per camera)             │
│                                          │
│  [Camera] ──────────────────┐            │
│     │ monitors:             │            │
│     ├── Slot A-01 (bbox)    │            │
│     ├── Slot A-02 (bbox)    │ ← 1 cam   │
│     ├── Slot A-03 (bbox)    │   5 slots  │
│     ├── Slot A-04 (bbox)    │            │
│     └── Slot A-05 (bbox)    │            │
│                              │            │
│  [ESP32 per slot] ← Optional button      │
│     (verify đúng ô)                      │
│                                          │
└──────────────────────────────────────────┘
```

---

## 15. FRONTEND AUDIT — KIỂM KÊ CHI TIẾT TOÀN BỘ FRONTEND

### 15.1 Cấu trúc Frontend hiện tại

```
spotlove-ai/
├── src/
│   ├── pages/                          ← 19 pages (15 user + 6 admin)
│   │   ├── LoginPage.tsx               ✅ Built
│   │   ├── RegisterPage.tsx            ✅ Built
│   │   ├── UserDashboard.tsx           ✅ Built (current parking + stats)
│   │   ├── BookingPage.tsx             ✅ Built (1328 lines, 5-step wizard)
│   │   ├── PaymentPage.tsx             ⚠️ Has bugs (manual confirm)
│   │   ├── HistoryPage.tsx             ✅ Built (739 lines)
│   │   ├── CamerasPage.tsx             ⚠️ Has bugs (placeholder stream)
│   │   ├── BanknoteDetectionPage.tsx   ✅ Built
│   │   ├── MapPage.tsx                 ✅ Built (client-side only)
│   │   ├── SettingsPage.tsx            ✅ Built
│   │   ├── SupportPage.tsx             ✅ Built
│   │   ├── PanicButtonPage.tsx         ✅ Built
│   │   └── admin/
│   │       ├── AdminDashboard.tsx      ✅ Built
│   │       ├── AdminCamerasPage.tsx    ⚠️ Has bugs (no live stream)
│   │       ├── AdminSlotsPage.tsx      ✅ Built
│   │       ├── AdminStatsPage.tsx      ✅ Built
│   │       ├── AdminUsersPage.tsx      ✅ Built
│   │       ├── AdminZonesPage.tsx      ✅ Built
│   │       └── AdminConfigPage.tsx     ✅ Built
│   ├── components/
│   │   ├── booking/
│   │   │   ├── PriceSummary.tsx        ⚠️ HARDCODED PRICES (Bug #1)
│   │   │   ├── ParkingLotSelector.tsx  ✅ Built
│   │   │   ├── SlotGrid.tsx           ✅ Built
│   │   │   ├── BookingQRCode.tsx      ✅ Built
│   │   │   ├── MultiDayPicker.tsx     ✅ Built
│   │   │   ├── AutoGuaranteeBooking.tsx ✅ Built
│   │   │   └── CalendarAutoHold.tsx   ✅ Built
│   │   ├── dashboard/                  ✅ Dashboard widgets
│   │   ├── layout/                     ✅ App layout + sidebar
│   │   ├── map/                        ✅ Map components
│   │   ├── settings/                   ✅ Settings panels
│   │   ├── support/                    ✅ Support widgets
│   │   └── ui/                         ✅ ShadcnUI base components
│   ├── services/
│   │   ├── api/
│   │   │   ├── axios.client.ts         ✅ Base HTTP client + interceptors
│   │   │   ├── endpoints.ts            ⚠️ Nhiều endpoint bị commented (admin, map, calendar)
│   │   │   ├── auth.api.ts             ✅ Login/register/logout
│   │   │   ├── booking.api.ts          ✅ Full CRUD + checkIn/checkOut
│   │   │   ├── parking.api.ts          ✅ Lots/floors/zones/slots
│   │   │   ├── ai.api.ts              ⚠️ CHỈ có detectBanknote() — thiếu nhiều
│   │   │   ├── admin.api.ts            ✅ Full admin CRUD (427 lines)
│   │   │   ├── incident.api.ts         ✅ Report/cancel/security (150 lines)
│   │   │   ├── chatbot.api.ts          ✅ Chat messages
│   │   │   ├── notification.api.ts     ✅ CRUD notifications
│   │   │   ├── vehicle.api.ts          ✅ Vehicle CRUD
│   │   │   └── payment.api.ts          ✅ (nếu có) hoặc dùng booking.api
│   │   ├── business/                   ✅ Business logic services
│   │   ├── websocket.service.ts        ✅ WebSocket (323 lines) + Redux dispatch
│   │   └── index.ts                    ✅ Service barrel exports
│   ├── store/slices/
│   │   ├── authSlice.ts                ✅ Auth state
│   │   ├── bookingSlice.ts             ✅ Booking state + async thunks
│   │   ├── parkingSlice.ts             ✅ Parking state + realtime updates
│   │   ├── notificationSlice.ts        ✅ Notifications
│   │   └── websocketSlice.ts           ✅ WS connection state
│   ├── hooks/
│   │   ├── useAuth.ts                  ✅ Auth hook
│   │   ├── useBooking.ts              ✅ Booking hook
│   │   ├── useParking.ts              ✅ Parking hook
│   │   ├── useNotifications.ts        ✅ Notifications hook
│   │   └── useWebSocketConnection.ts  ✅ WS connection hook
│   └── types/
│       └── parking.ts                  ✅ All parking types (177 lines)
```

### 15.2 Frontend Bugs / Inconsistencies

| #     | Bug                                            | File(s)                   | Severity    | Chi tiết                                                                                                                                                         |
| ----- | ---------------------------------------------- | ------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FE-1  | **PriceSummary HARDCODED PRICES**              | `PriceSummary.tsx` L28-39 | 🔴 Critical | `PRICES = { Car: { hourly: 20000, daily: 100000, weekly: 600000, monthly: 2000000 } }` — Không fetch từ API. Admin đổi giá DB → FE vẫn hiện giá cũ               |
| FE-2  | **PriceSummary HARDCODED DISCOUNTS**           | `PriceSummary.tsx` L42-47 | 🔴 Critical | `DISCOUNTS = { monthly: 0.2, weekly: 0.1 }` — Hardcoded, không có trong DB. BE không trả về discount                                                             |
| FE-3  | **PaymentPage manual confirm**                 | `PaymentPage.tsx` L134    | 🔴 Critical | `handleConfirmPayment()` → `setPaymentConfirmed(true)` → navigate. Không verify payment thật qua API. User bấm "Tôi đã thanh toán" mà chưa chuyển khoản vẫn pass |
| FE-4  | **PaymentPage no auto-polling**                | `PaymentPage.tsx`         | 🟡 High     | Không có `setInterval` polling `GET /payments/{id}/verify` để auto-detect payment. Chỉ có countdown timer cho UI                                                 |
| FE-5  | **CamerasPage placeholder stream**             | `CamerasPage.tsx`         | 🟡 High     | Admin cameras có `streamUrl` từ API nhưng không render `<img src={streamUrl}>` cho MJPEG. User mode chỉ show "camera của xe đã đậu"                              |
| FE-6  | **AdminCamerasPage no live feed**              | `AdminCamerasPage.tsx`    | 🟡 High     | Fetch cameras từ API + có `streamUrl` field nhưng không render actual video/image stream                                                                         |
| FE-7  | **ai.api.ts incomplete**                       | `ai.api.ts`               | 🟡 High     | Chỉ có `detectBanknote()`. Thiếu: `scanPlate()`, `checkIn()`, `checkOut()`, `detectCash()`, `getModelMetrics()`, `getPredictionLogs()`                           |
| FE-8  | **endpoints.ts mostly commented**              | `endpoints.ts`            | 🟡 Medium   | INCIDENTS, MAP, SUPPORT, ADMIN, AI, CALENDAR sections all commented out. Một số endpoints duplicate với trực tiếp trong api files                                |
| FE-9  | **BookingPage no end_date for monthly/weekly** | `BookingPage.tsx` L357    | 🟡 Medium   | Monthly/Weekly booking chỉ gửi `start_time`, không tự tính `end_time = start + 30d/7d`. Backend phải tự xử lý (và có thể sai)                                    |
| FE-10 | **SlotGrid no realtime update**                | `SlotGrid.tsx`            | 🟡 Medium   | WebSocket dispatch `updateSlotStatus` vào Redux nhưng SlotGrid component có thể không re-render đúng nếu đang ở booking flow                                     |
| FE-11 | **No check-in/check-out UI flow**              | —                         | 🟡 High     | User không có UI để check-in/check-out từ phone. Chỉ có API endpoint trong `booking.api.ts`. Dashboard show current parking nhưng ko có button                   |
| FE-12 | **No parking kiosk display page**              | —                         | 🟡 Medium   | Không có page cho màn hình LED/kiosk tại cổng: hiện trạng thái check-in, số tiền, QR payment                                                                     |
| FE-13 | **Admin no violations page**                   | —                         | 🟢 Low      | `incident.api.ts` và `admin.api.ts` có incident types nhưng chưa có trang admin riêng cho violations (wrong slot, lane violation)                                |
| FE-14 | **WebSocket không handle slot.batch_update**   | `websocket.service.ts`    | 🟡 Medium   | `WSMessageType.SLOTS_BATCH_UPDATE` defined nhưng handler chỉ log, không update Redux state cho batch slot changes                                                |
| FE-15 | **UserDashboard no quick actions**             | `UserDashboard.tsx`       | 🟡 Medium   | Dashboard hiện current parking nhưng không có nút: "Show QR Code", "Navigate to slot", "Request Check-out", "Pay Now"                                            |

---

## 16. FRONTEND — CẢI TIẾN CẦN THIẾT (IMPROVEMENTS)

### 16.1 API Client Improvements

| #    | Cải tiến                                     | File(s)                   | Priority | Chi tiết                                                                                                                                                             |
| ---- | -------------------------------------------- | ------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FC-1 | **ai.api.ts: Thêm tất cả AI endpoints**      | `ai.api.ts`               | 🔴       | Thêm: `scanPlate(image)`, `checkIn(qrData, image)`, `checkOut(qrData, image)`, `detectCash(image)`, `getModelMetrics()`, `getPredictionLogs()`, `getModelVersions()` |
| FC-2 | **ai.api.ts: ESP32 endpoints (admin/kiosk)** | `ai.api.ts`               | 🟡       | Thêm: `esp32CheckIn(gateId, cameraUrl?)`, `esp32CheckOut(gateId)`, `esp32VerifySlot(slotCode, zoneId)`, `esp32CashPayment(bookingId, image)` — cho admin kiosk mode  |
| FC-3 | **endpoints.ts: Uncomment + activate**       | `endpoints.ts`            | 🟡       | Uncomment INCIDENTS, ADMIN, AI sections. Align với backend endpoints đã implement                                                                                    |
| FC-4 | **parking.api.ts: Slot status update**       | `parking.api.ts`          | 🟡       | Thêm: `updateSlotStatus(slotId, status)` — cho admin manual override + AI auto-update                                                                                |
| FC-5 | **booking.api.ts: PackagePricing fetch**     | `booking.api.ts`          | 🔴       | Thêm: `getPackagePricing(vehicleType?)` → `GET /bookings/pricing/?vehicle_type=Car`                                                                                  |
| FC-6 | **booking.api.ts: Get booking by slot**      | `booking.api.ts`          | 🟡       | Thêm: `getBookingBySlot(slotId)` → `GET /bookings/by-slot/?slot_id=xxx&status=checked_in`                                                                            |
| FC-7 | **payment polling service**                  | New: `payment.polling.ts` | 🔴       | Thêm polling service: `startPaymentPolling(bookingId, interval)` → poll `GET /payments/{id}/` mỗi 5s. Auto-stop khi `status=completed`                               |

### 16.2 Component Improvements

| #    | Cải tiến                                   | File(s)             | Priority | Chi tiết                                                                                                                              |
| ---- | ------------------------------------------ | ------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| CC-1 | **PriceSummary → fetch API**               | `PriceSummary.tsx`  | 🔴       | Xoá hardcoded `PRICES` + `DISCOUNTS`. Thêm `useEffect` fetch `bookingApi.getPackagePricing()`. Cache trong component state hoặc Redux |
| CC-2 | **PriceSummary → loading + error state**   | `PriceSummary.tsx`  | 🟡       | Thêm skeleton loading khi đang fetch pricing. Error fallback nếu API fail (có thể show cached/default prices)                         |
| CC-3 | **BookingPage → auto end_date**            | `BookingPage.tsx`   | 🟡       | Step 4: monthly → `end_time = start + 30 days`. Weekly → `end_time = start + 7 days`. Gửi `end_time` trong `createBooking` request    |
| CC-4 | **BookingPage → PriceSummary prop update** | `BookingPage.tsx`   | 🟡       | Truyền fetched pricing data xuống `PriceSummary` thay vì để PriceSummary tự hardcode                                                  |
| CC-5 | **SlotGrid → realtime badge**              | `SlotGrid.tsx`      | 🟡       | Thêm animated pulse dot cho slots đang thay đổi realtime. Subscribe WebSocket `slot.status_update` for booking zone                   |
| CC-6 | **BookingQRCode → fullscreen mode**        | `BookingQRCode.tsx` | 🟢       | Thêm nút fullscreen QR cho dễ scan tại cổng                                                                                           |

### 16.3 Page Improvements

| #     | Cải tiến                                      | File(s)                     | Priority | Chi tiết                                                                                                                                                  |
| ----- | --------------------------------------------- | --------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PC-1  | **PaymentPage → auto-polling verify**         | `PaymentPage.tsx`           | 🔴       | Thêm `useEffect` với `setInterval` polling payment status. Khi `status=completed` → auto navigate to success. Bỏ hoặc giữ "Tôi đã thanh toán" as fallback |
| PC-2  | **PaymentPage → cash payment option**         | `PaymentPage.tsx`           | 🟡       | Thêm tab "Thanh toán tiền mặt tại cổng" → hiện hướng dẫn: đến cổng ra → nhét tiền → camera detect → auto verify                                           |
| PC-3  | **CamerasPage → render actual stream**        | `CamerasPage.tsx`           | 🟡       | Thay placeholder bằng: `<img src={camera.streamUrl} alt="Live Feed" />` cho MJPEG. Fallback: snapshot refresh mỗi 2s                                      |
| PC-4  | **CamerasPage → slot overlay (canvas)**       | `CamerasPage.tsx`           | 🟢       | Overlay slot bounding boxes lên camera feed. Màu: xanh=trống, đỏ=occupied, vàng=violation. Data từ `slots` API                                            |
| PC-5  | **AdminCamerasPage → live stream + CRUD**     | `AdminCamerasPage.tsx`      | 🟡       | Render actual `stream_url`. Thêm CRUD camera (create/update/delete). Preview stream khi thêm camera mới                                                   |
| PC-6  | **UserDashboard → quick action buttons**      | `UserDashboard.tsx`         | 🟡       | Khi có `currentParking`: thêm buttons "Xem QR Code", "Dẫn đường đến ô", "Yêu cầu Check-out", "Thanh toán ngay"                                            |
| PC-7  | **UserDashboard → check-in/check-out status** | `UserDashboard.tsx`         | 🟡       | Hiện realtime check-in status: "Đang chờ check-in", "Đã check-in lúc 14:30", "Đang đậu 2h30p"                                                             |
| PC-8  | **HistoryPage → payment status badge**        | `HistoryPage.tsx`           | 🟡       | Hiện badge: "Đã thanh toán ✅", "Chưa thanh toán ⚠️", "Đang xử lý 🔄" cho mỗi booking                                                                     |
| PC-9  | **HistoryPage → re-pay failed bookings**      | `HistoryPage.tsx`           | 🟢       | Button "Thanh toán lại" cho bookings có `payment_status=failed`                                                                                           |
| PC-10 | **BanknoteDetectionPage → integration guide** | `BanknoteDetectionPage.tsx` | 🟢       | Thêm section hướng dẫn: "Tính năng này dùng cho cổng thanh toán tiền mặt". Link đến checkout flow                                                         |

### 16.4 New Pages Cần Tạo

| #    | Page mới                               | File                                       | Priority | Chi tiết                                                                                                                                                    |
| ---- | -------------------------------------- | ------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NP-1 | **GateKioskPage (Check-in/Check-out)** | `pages/GateKioskPage.tsx`                  | 🔴       | Fullscreen page cho màn hình LED cổng: hiện trạng thái ESP32, camera feed, QR scan result, barrier status. Auto-refresh. Không cần login                    |
| NP-2 | **CashPaymentKioskPage**               | `pages/CashPaymentKioskPage.tsx`           | 🔴       | Fullscreen page cho màn hình cổng ra: hiện số tiền cần trả, tiền đã nhét, remaining, camera feed. Connect WebSocket `payment.cash_received`                 |
| NP-3 | **ParkingStatusPage (public)**         | `pages/ParkingStatusPage.tsx`              | 🟡       | Public page (no auth): hiện realtime available slots per lot/zone. Dùng WebSocket. Cho hiện trên bảng LED ngoài bãi xe                                      |
| NP-4 | **AdminViolationsPage**                | `pages/admin/AdminViolationsPage.tsx`      | 🟡       | Admin: list violations (wrong slot, lane, overtime). Evidence images. Resolve/dismiss actions. Filter by type/status                                        |
| NP-5 | **AdminRealtimeMonitorPage**           | `pages/admin/AdminRealtimeMonitorPage.tsx` | 🟡       | Admin: grid view tất cả cameras + slot status realtime. Click camera → fullscreen + slot overlay. Alert khi violation detected                              |
| NP-6 | **CheckInOutStatusPage (user)**        | `pages/CheckInOutStatusPage.tsx`           | 🟢       | User: scan QR on phone → hiện check-in progress realtime (QR scanned ✅ → Plate verified ✅ → Barrier opening... → Done ✅). Connect WebSocket `gate.event` |

---

## 17. FRONTEND — TASK BREAKDOWN CHI TIẾT

### Phase FA: API Client & Type Updates (🔴 Highest — phải làm trước mọi thứ FE)

```
FA1. @coder-frontend: Mở rộng ai.api.ts
    - Thêm types: ScanPlateResponse, CheckInResponse, CheckOutResponse,
      CashDetectionResponse, ModelMetrics, PredictionLog
    - Thêm methods: scanPlate(), checkIn(), checkOut(), detectCash(),
      getModelMetrics(), getPredictionLogs(), getModelVersions()
    - Thêm ESP32 methods (admin): esp32CheckIn(), esp32CheckOut(),
      esp32VerifySlot(), esp32CashPayment()

FA2. @coder-frontend: Thêm PackagePricing API vào booking.api.ts
    - Type: PackagePricing { id, vehicleType, packageType, price, discount? }
    - Method: getPackagePricing(vehicleType?: string) → GET /bookings/pricing/
    - Method: getBookingBySlot(slotId: string) → GET /bookings/by-slot/

FA3. @coder-frontend: Thêm updateSlotStatus vào parking.api.ts
    - Method: updateSlotStatus(slotId, status) → PATCH /parking/slots/{id}/status/
    - For admin manual override + AI-triggered updates

FA4. @coder-frontend: Cập nhật endpoints.ts
    - Uncomment INCIDENTS section → align with incident.api.ts
    - Add AI section: SCAN_PLATE, CHECK_IN, CHECK_OUT, DETECT_CASH,
      ESP32_CHECK_IN, ESP32_CHECK_OUT, ESP32_VERIFY_SLOT, CASH_PAYMENT
    - Add PRICING section: PACKAGE_PRICING
    - Uncomment relevant ADMIN sections

FA5. @coder-frontend: Update types/parking.ts
    - Thêm: ESP32Response, BarrierAction, GateEvent, CashPaymentSession
    - Thêm: PackagePricing interface
    - Thêm: SlotDetectionResult, ViolationType

FA6. @coder-frontend: Update WebSocket message types
    - websocket.service.ts: Thêm handlers cho:
      - gate.check_in_complete / gate.check_out_complete
      - payment.cash_received
      - slot.batch_update (fix: dispatch to Redux properly)
      - parking.violation
    - Dispatch mới vào parkingSlice + bookingSlice
```

### Phase FB: Fix Critical Bugs (🔴 Critical)

```
FB1. @coder-frontend: Fix PriceSummary.tsx — xoá hardcoded prices
    - Xoá const PRICES và DISCOUNTS
    - Thêm prop: pricing?: PackagePricing[] (truyền từ BookingPage)
    - HOẶC: useEffect + fetch bookingApi.getPackagePricing(vehicleType)
    - Thêm loading skeleton + error state
    - Tính toán dựa trên data từ API thay vì hardcode
    - Note: BE PackagePricingViewSet PHẢI expose endpoint trước (xem D1 backend)

FB2. @coder-frontend: Fix PaymentPage.tsx — auto-polling payment verify
    - Thêm useEffect:
        const interval = setInterval(async () => {
          const result = await paymentApi.verify(bookingId);
          if (result.status === 'completed') {
            clearInterval(interval);
            navigate to success;
          }
        }, 5000);
    - Giữ "Tôi đã thanh toán" button as manual fallback
    - Thêm visual indicator: "Đang kiểm tra thanh toán..."
    - Auto-stop polling khi component unmount hoặc payment confirmed

FB3. @coder-frontend: Fix BookingPage.tsx — auto end_date
    - Monthly: endTime = new Date(startTime); endTime.setDate(endTime.getDate() + 30)
    - Weekly: endTime = new Date(startTime); endTime.setDate(endTime.getDate() + 7)
    - Gửi cả startTime + endTime trong createBooking request
    - Hiện end_date trong PriceSummary và confirmation step

FB4. @coder-frontend: Fix CamerasPage.tsx — render live stream
    - Admin mode: <img src={camera.streamUrl} /> cho MJPEG
    - User mode: Fetch camera by booking zone → render stream
    - Fallback: snapshot <img> refresh mỗi 2s khi stream fail
    - Error handling: "Camera offline" placeholder

FB5. @coder-frontend: Fix AdminCamerasPage.tsx — live stream render
    - Render actual streamUrl trong camera card
    - Preview stream khi create/edit camera
    - Indicator: green dot = online, red dot = offline
```

### Phase FC: Page Enhancements (🟡 High)

```
FC1. @coder-frontend: UserDashboard.tsx — quick action buttons
    - Khi currentParking:
      - Button "📱 Xem QR Code" → modal BookingQRCode fullscreen
      - Button "🗺️ Dẫn đường" → navigate to MapPage with slot
      - Button "🚗 Yêu cầu Check-out" → call bookingApi.checkOut()
      - Button "💳 Thanh toán ngay" → navigate to PaymentPage
    - Khi no currentParking:
      - Button "📍 Đặt chỗ ngay" → navigate to BookingPage

FC2. @coder-frontend: UserDashboard.tsx — realtime status timeline
    - Timeline component:
      "Đặt chỗ lúc 14:00 ✅" → "Check-in lúc 14:25 ✅" →
      "Đang đậu tại A-05 🚗 (2h30p)" → "Check-out: chưa"
    - Update via WebSocket booking.status_update

FC3. @coder-frontend: HistoryPage.tsx — payment status badges
    - Mỗi booking card: badge [Đã TT ✅ | Chưa TT ⚠️ | Đang xử lý 🔄]
    - Button "Thanh toán lại" cho failed payments
    - Button "Xem hoá đơn" cho completed payments

FC4. @coder-frontend: SlotGrid.tsx — realtime pulse animation
    - Slot đang thay đổi (WebSocket update): animated pulse ring
    - Slot vừa được book bởi user khác: brief flash → occupied
    - useSelector từ parkingSlice để track realtime updates

FC5. @coder-frontend: BookingQRCode.tsx — fullscreen mode
    - Button "Phóng to" → fullscreen modal
    - Max brightness suggestion
    - Auto-rotate QR cho dễ scan
```

### Phase FD: New Pages — Kiosk & Public (🟡 High)

```
FD1. @coder-frontend: GateKioskPage.tsx — Màn hình cổng vào/ra
    - Route: /kiosk/gate/:gateId (no auth required)
    - Layout: fullscreen, dark theme, large text
    - Sections:
      ┌─────────────────────────────────────┐
      │  ParkSmart Gate-In                  │
      │  ┌─────────┐  ┌──────────────────┐  │
      │  │ Camera  │  │ Status:          │  │
      │  │ Feed    │  │ ✅ QR Scanned    │  │
      │  │ (MJPEG) │  │ 🔄 Verifying...  │  │
      │  │         │  │ ✅ Plate: 29A-123│  │
      │  │         │  │ ✅ Barrier Open  │  │
      │  └─────────┘  └──────────────────┘  │
      │  [Vehicle: 29A-12345] [Slot: A-05]  │
      └─────────────────────────────────────┘
    - WebSocket: subscribe gate.{gateId} channel
    - Auto-clear status after 10s

FD2. @coder-frontend: CashPaymentKioskPage.tsx — Màn hình thanh toán tiền mặt
    - Route: /kiosk/payment/:gateId (no auth required)
    - Layout:
      ┌─────────────────────────────────────┐
      │  💰 Thanh toán tiền mặt            │
      │                                     │
      │  Tổng cần trả:     50,000 VND      │
      │  Đã nhận:          20,000 VND      │
      │  ─────────────────────────────      │
      │  Còn thiếu:        30,000 VND      │
      │                                     │
      │  Tiền đã nhận:                      │
      │  ├── 10,000 VND × 1               │
      │  └── 10,000 VND × 1               │
      │                                     │
      │  📷 [Camera feed - chờ tiền]       │
      │                                     │
      │  ⏳ Vui lòng nhét tiền vào khe...  │
      └─────────────────────────────────────┘
    - WebSocket: payment.cash_received → update running total
    - Auto-open barrier khi total >= required

FD3. @coder-frontend: ParkingStatusPage.tsx — Bảng LED công cộng
    - Route: /status/:lotId (no auth required)
    - Show: lot name, total slots, available by zone
    - Realtime via WebSocket zone.availability_update
    - Large font, high contrast cho LED display
    - Auto-refresh fallback nếu WS disconnect

FD4. @coder-frontend: AdminViolationsPage.tsx
    - Route: /admin/violations (admin only)
    - Table: incident list with filters (type, status, date)
    - Evidence image viewer (click to expand)
    - Actions: Resolve, Dismiss, Contact user
    - Stats: total violations today, by type chart

FD5. @coder-frontend: AdminRealtimeMonitorPage.tsx
    - Route: /admin/monitor (admin only)
    - Grid: 2x3 or 3x3 camera feeds
    - Click camera → fullscreen + slot overlay
    - Alert panel: recent violations, anomalies
    - WebSocket: all parking events
```

### Phase FE: Redux Store & WebSocket Updates (🟡 Medium)

```
FE1. @coder-frontend: parkingSlice.ts — thêm pricing state
    - State: packagePricing: PackagePricing[]
    - AsyncThunk: fetchPackagePricing(vehicleType?)
    - Selector: selectPricingByVehicleType(vehicleType)

FE2. @coder-frontend: bookingSlice.ts — thêm gate event tracking
    - State: currentGateEvent: GateEvent | null
    - Reducer: setGateEvent(event)
    - Clear after 10s timeout

FE3. @coder-frontend: websocketSlice.ts — thêm connection quality
    - State: latency, lastPongAt, messageCount
    - Indicator component: 🟢 Good / 🟡 Slow / 🔴 Disconnected

FE4. @coder-frontend: websocket.service.ts — fix batch update handler
    - SLOTS_BATCH_UPDATE: loop through data.slots → dispatch updateSlotStatus for each
    - Thêm: GATE_CHECK_IN_COMPLETE, GATE_CHECK_OUT_COMPLETE handlers
    - Thêm: PAYMENT_CASH_RECEIVED handler → dispatch to new cashPaymentSlice
    - Thêm: PARKING_VIOLATION handler → dispatch to notificationSlice + alertSlice

FE5. @coder-frontend: Thêm cashPaymentSlice.ts (nếu cần kiosk page)
    - State: { bookingId, requiredAmount, currentTotal, denominations[], isComplete }
    - Reducers: addCashPayment, resetSession
    - Selector: selectCashPaymentProgress
```

### Phase FF: Testing & Validation (🟡 Medium)

```
FF1. @tester: Unit tests cho API clients
    - Test ai.api.ts: mock axios, verify request format
    - Test booking.api.ts: getPackagePricing mock
    - Test parking.api.ts: updateSlotStatus mock

FF2. @tester: Component tests
    - PriceSummary: test renders fetched pricing (not hardcoded)
    - PaymentPage: test polling starts on mount, stops on unmount
    - CamerasPage: test renders img with streamUrl

FF3. @tester: E2E Playwright tests (MCP Playwright)
    - Test 1: Login → BookingPage → verify pricing từ API
    - Test 2: PaymentPage → verify auto-polling active
    - Test 3: CamerasPage (admin) → verify stream rendering
    - Test 4: UserDashboard → verify quick action buttons
    - Test 5: GateKioskPage → verify WebSocket connection
    - Test 6: CashPaymentKioskPage → simulate cash events
    - Test 7: AdminViolationsPage → CRUD operations
    - Test 8: All 19+ pages load without console errors

FF4. @tester: Integration tests
    - Test FE ↔ BE pricing consistency
    - Test WebSocket event → Redux state → UI update pipeline
    - Test payment flow: initiate → poll → complete → redirect
```

---

## 18. FRONTEND — SERVICE IMPACT MAP

| File/Component                        | Impact Level         | Phases Affected  | Chi tiết                                              |
| ------------------------------------- | -------------------- | ---------------- | ----------------------------------------------------- |
| `ai.api.ts`                           | 🔴 **MOST Affected** | FA1, FA2         | Hiện chỉ 1 method → cần thêm ~10 methods              |
| `PriceSummary.tsx`                    | 🔴 **Critical Fix**  | FB1              | Xoá hardcode → fetch API. Ảnh hưởng BookingPage       |
| `PaymentPage.tsx`                     | 🔴 **Critical Fix**  | FB2, PC-2        | Thêm polling + cash option. Flow chính của thanh toán |
| `BookingPage.tsx`                     | 🟡 Affected          | FB3, CC-3, CC-4  | Auto end_date + truyền pricing data                   |
| `CamerasPage.tsx`                     | 🟡 Affected          | FB4, PC-3, PC-4  | Render stream + slot overlay                          |
| `AdminCamerasPage.tsx`                | 🟡 Affected          | FB5, PC-5        | Live stream + improved CRUD                           |
| `UserDashboard.tsx`                   | 🟡 Affected          | FC1, FC2, PC-6-7 | Quick actions + realtime timeline                     |
| `HistoryPage.tsx`                     | 🟡 Minor             | FC3, PC-8-9      | Payment badges + re-pay                               |
| `websocket.service.ts`                | 🟡 Affected          | FA6, FE4         | New event handlers + fix batch update                 |
| `booking.api.ts`                      | 🟡 Affected          | FA2, FA5         | Thêm 2 methods                                        |
| `parking.api.ts`                      | 🟡 Minor             | FA3              | Thêm 1 method                                         |
| `endpoints.ts`                        | 🟡 Minor             | FA4              | Uncomment + thêm sections                             |
| `parkingSlice.ts`                     | 🟡 Affected          | FE1              | Thêm pricing state                                    |
| `bookingSlice.ts`                     | 🟡 Minor             | FE2              | Thêm gate event                                       |
| **NEW: GateKioskPage.tsx**            | 🔴 New page          | FD1              | Fullscreen kiosk page                                 |
| **NEW: CashPaymentKioskPage.tsx**     | 🔴 New page          | FD2              | Cash payment kiosk                                    |
| **NEW: ParkingStatusPage.tsx**        | 🟡 New page          | FD3              | Public parking availability                           |
| **NEW: AdminViolationsPage.tsx**      | 🟡 New page          | FD4              | Admin violations management                           |
| **NEW: AdminRealtimeMonitorPage.tsx** | 🟡 New page          | FD5              | Multi-camera realtime monitor                         |
| **NEW: CheckInOutStatusPage.tsx**     | 🟢 New page          | NP-6             | User check-in/out progress                            |

---

## 19. FRONTEND — RECOMMENDED IMPLEMENTATION ORDER

```
Week 1: Phase FA (API Clients — MUST DO FIRST)
    ├── FA1: ai.api.ts expansion (~10 new methods)
    ├── FA2: booking.api.ts + PackagePricing
    ├── FA3: parking.api.ts + slot status
    ├── FA4: endpoints.ts cleanup
    ├── FA5: types/parking.ts updates
    └── FA6: WebSocket new handlers

Week 1-2: Phase FB (Critical Bug Fixes)
    ├── FB1: PriceSummary.tsx → fetch from API ← DEPENDS ON backend D1
    ├── FB2: PaymentPage.tsx → auto-polling
    ├── FB3: BookingPage.tsx → auto end_date
    ├── FB4: CamerasPage.tsx → live stream
    └── FB5: AdminCamerasPage.tsx → live stream

Week 2-3: Phase FC (Page Enhancements)
    ├── FC1: UserDashboard quick actions
    ├── FC2: UserDashboard realtime timeline
    ├── FC3: HistoryPage payment badges
    ├── FC4: SlotGrid realtime animation
    └── FC5: BookingQRCode fullscreen

Week 3-4: Phase FD (New Pages)
    ├── FD1: GateKioskPage ← DEPENDS ON backend A4-A5 (ESP32 endpoints)
    ├── FD2: CashPaymentKioskPage ← DEPENDS ON backend B3
    ├── FD3: ParkingStatusPage (independent)
    ├── FD4: AdminViolationsPage ← DEPENDS ON backend E2
    └── FD5: AdminRealtimeMonitorPage ← DEPENDS ON backend C3

Week 4-5: Phase FE (Redux & WebSocket)
    ├── FE1-FE3: Store updates
    ├── FE4: WebSocket fix + new handlers
    └── FE5: cashPaymentSlice (if kiosk)

Week 5-6: Phase FF (Testing)
    ├── FF1: Unit tests
    ├── FF2: Component tests
    ├── FF3: E2E Playwright (MCP)
    └── FF4: Integration tests
```

### Frontend ↔ Backend Dependency Map

```
FE Task         →  Requires BE Task First
─────────────────────────────────────────
FB1 (PriceSummary)  →  D1 (PackagePricing API)
FD1 (GateKiosk)     →  A4-A6 (ESP32 endpoints)
FD2 (CashKiosk)     →  B3 (Cash payment endpoint)
FD4 (Violations)    →  E2 (Incident model + API)
FD5 (Monitor)       →  C2-C3 (Slot detection + camera worker)
FB4 (CameraStream)  →  Camera hardware configured
PC-4 (SlotOverlay)  →  C4 (Slot status PATCH endpoint)
```

---

## APPENDIX D: FRONTEND COMPONENT TREE (cần thêm)

```
App.tsx
├── Layout (sidebar + header)
│   ├── UserDashboard ← FC1, FC2 enhancements
│   │   ├── CurrentParkingCard (quick actions) ← NEW
│   │   ├── UpcomingBookings
│   │   └── NotificationsFeed
│   ├── BookingPage (5-step wizard)
│   │   ├── Step 1: ParkingLotSelector
│   │   ├── Step 2: VehicleSelector
│   │   ├── Step 3: SlotGrid ← FC4 realtime
│   │   ├── Step 4: TimeSelector ← FB3 auto end_date
│   │   ├── Step 5: Confirmation
│   │   └── PriceSummary ← FB1 fetch API
│   ├── PaymentPage ← FB2 auto-polling, PC-2 cash option
│   ├── HistoryPage ← FC3 payment badges
│   ├── CamerasPage ← FB4 live stream, PC-4 slot overlay
│   ├── BanknoteDetectionPage
│   ├── MapPage
│   ├── SettingsPage
│   ├── SupportPage
│   ├── PanicButtonPage
│   ├── admin/
│   │   ├── AdminDashboard
│   │   ├── AdminCamerasPage ← FB5 live stream
│   │   ├── AdminSlotsPage
│   │   ├── AdminStatsPage
│   │   ├── AdminUsersPage
│   │   ├── AdminZonesPage
│   │   ├── AdminConfigPage
│   │   ├── AdminViolationsPage ← FD4 NEW
│   │   └── AdminRealtimeMonitorPage ← FD5 NEW
│   └── CheckInOutStatusPage ← NP-6 NEW
├── Kiosk (no-auth routes)
│   ├── GateKioskPage ← FD1 NEW
│   ├── CashPaymentKioskPage ← FD2 NEW
│   └── ParkingStatusPage ← FD3 NEW
└── Auth
    ├── LoginPage
    └── RegisterPage
```

---

> **END OF PLAN** — File này là tài liệu tham khảo. Mọi thay đổi code phải tuân theo execution order: `@planner → @architect → @coder-backend → @coder-frontend → @tester → @reviewer → @deployer`
