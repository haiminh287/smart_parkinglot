# ParkSmart — Hệ thống quản lý Bãi đỗ xe Thông minh tích hợp IoT

> **Khóa luận tốt nghiệp** · Khoa Công nghệ Thông tin · Đại học Mở TP.HCM · 2026
> Sinh viên thực hiện: **Nguyễn Hải Minh** — MSSV 2251012093

Hệ thống quản lý bãi đỗ xe tự động hoá end-to-end:
- 4 AI modules (License Plate OCR, Banknote Classifier, Chatbot LLM+RAG, Slot Detection)
- 10 microservices backend (Django REST + FastAPI + Go)
- IoT edge với 4 ESP32 devices (gate-in/out, slot verify, cash-pay)
- Unity Digital Twin để test E2E mà không cần phần cứng thật
- Frontend PWA React 18 + Redux Toolkit
- Triển khai production qua Cloudflare Tunnel

---

## Mục lục

1. [Kiến trúc tổng quan](#1-kiến-trúc-tổng-quan)
2. [Yêu cầu hệ thống](#2-yêu-cầu-hệ-thống)
3. [Quick start với Docker](#3-quick-start-với-docker)
4. [Cấu hình biến môi trường](#4-cấu-hình-biến-môi-trường)
5. [Setup notification (Gmail SMTP)](#5-setup-notification-gmail-smtp)
6. [Frontend](#6-frontend)
7. [Unity Digital Twin](#7-unity-digital-twin)
8. [Kiểm thử](#8-kiểm-thử)
9. [Cấu trúc thư mục](#9-cấu-trúc-thư-mục)
10. [Tech Stack](#10-tech-stack)
11. [Triển khai production](#11-triển-khai-production)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Kiến trúc tổng quan

```
┌──────────────────────────────────────────────────────────┐
│  L1 CLIENT       Web SPA · Unity Twin · ESP32 IoT       │
├──────────────────────────────────────────────────────────┤
│  L2 CLOUDFLARE   HTTPS · DDoS · public URL              │
├──────────────────────────────────────────────────────────┤
│  L3 GATEWAY      Go · session auth · rate limit         │
├──────────────────────────────────────────────────────────┤
│  L4 MICROSERVICES  auth · booking · parking · vehicle   │
│                    notif · payment · ai · chatbot       │
├──────────────────────────────────────────────────────────┤
│  L5 EVENT BUS    RabbitMQ fan-out                       │
│  L6 REALTIME     WebSocket Go push                      │
├──────────────────────────────────────────────────────────┤
│  L7 DATASTORE    MySQL 8 · Redis × 6 DBs                │
└──────────────────────────────────────────────────────────┘
```

**Communication patterns:**
- HTTP (sync) qua API Gateway với header `X-Gateway-Secret` xác thực service-to-service
- RabbitMQ events (async fan-out): `booking.created` → notification + payment + analytics + chatbot
- WebSocket realtime push tới FE qua `realtime-service-go`

---

## 2. Yêu cầu hệ thống

### Mức tối thiểu (Development)
- **OS**: Windows 10/11, macOS 12+, hoặc Linux Ubuntu 20.04+
- **CPU**: 4 cores
- **RAM**: 8 GB (16 GB khuyến nghị)
- **Disk**: 20 GB free
- **Software**:
  - Docker Desktop 4.20+
  - Git 2.30+
  - (Optional) Python 3.11+, Node.js 20+, Go 1.22+ nếu muốn chạy service ngoài Docker

### Khuyến nghị (chạy AI service local có GPU)
- **GPU**: NVIDIA GTX 1650 (4GB VRAM) trở lên
- **CUDA**: 11.6+
- **Python venv** với PyTorch + CUDA toolkit

### Production
- **Cloud server**: 4 vCPU · 8 GB RAM (mức tối thiểu)
- **Cloudflare account** (free tier đủ cho demo)
- **Gmail account** với 2FA + App Password để gửi notification

---

## 3. Quick start với Docker

### Bước 1: Clone repository

```bash
git clone https://github.com/haiminh287/smart_parkinglot.git
cd smart_parkinglot
```

### Bước 2: Tạo file `.env`

```bash
cd backend-microservices
cp .env.example .env
# Mở .env và điền các giá trị bắt buộc (xem mục 4)
```

### Bước 3: Khởi động toàn bộ stack

```bash
docker compose up -d --build
```

Quá trình build lần đầu mất ~5-10 phút. Sau khi xong, các services lắng nghe tại:

| Service | Port host | Mô tả |
|---|---|---|
| Gateway (Go) | 8000 | API entry point |
| Auth (Django) | 8001 | Đăng ký · đăng nhập · OAuth Google |
| Booking (Django) | 8002 | Đặt chỗ · Celery worker + beat |
| Parking (Django) | 8003 | Quản lý bãi · tầng · zone · slot |
| Notification (FastAPI) | — | Email + WebSocket push (internal) |
| Payment (FastAPI) | — | MoMo · VNPay · QR (internal) |
| AI (FastAPI) | 8009 | YOLO · OCR · banknote · slot (local) |
| Chatbot (FastAPI) | — | Gemini + RAG (internal) |
| Realtime (Go) | 8006 | WebSocket push |
| Nginx | 80 | FE static + reverse proxy |
| MySQL | 3307 | Database |
| Redis | 6379 | Cache + session |
| RabbitMQ | 5672 / 15672 | Event broker + management UI |

### Bước 4: Kiểm tra services healthy

```bash
docker compose ps
# Tất cả phải hiển thị "Up X minutes (healthy)"
```

### Bước 5: Seed test user account

```bash
python seed_test_user.py
```

Sẽ tạo user test:
- Email: `minhht2k4@gmail.com`
- Password: `ParkSmart@2026`

### Bước 6: Mở web app

Mở browser: `http://localhost:8080` hoặc `http://localhost` (qua Nginx)

Đăng nhập với credentials ở Bước 5 → đặt chỗ → nhận email notification.

---

## 4. Cấu hình biến môi trường

File `backend-microservices/.env` (không commit lên git):

```bash
# ─── Database ─────────────────────────────────────────────────
DB_USER=parksmartuser
DB_PASSWORD=<your-strong-password>

# ─── Auth & Security ──────────────────────────────────────────
SECRET_KEY=<django-secret-key-50-chars>
GATEWAY_SECRET=<random-secret-32-chars>

# ─── RabbitMQ ─────────────────────────────────────────────────
RABBITMQ_USER=admin
RABBITMQ_PASS=admin

# ─── Google OAuth (optional) ──────────────────────────────────
GOOGLE_CLIENT_ID=<your-google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-google-oauth-client-secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback/

# ─── Email Notification (Gmail SMTP) ──────────────────────────
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=<your-gmail-admin@gmail.com>
EMAIL_HOST_PASSWORD=<16-char-gmail-app-password>
EMAIL_FROM_NAME=ParkSmart
ADMIN_EMAIL=<admin-fallback@gmail.com>

# ─── Cloudflare (production only) ─────────────────────────────
CF_API_TOKEN=
CF_ACCOUNT_ID=
```

**Required (bắt buộc):** `DB_PASSWORD`, `SECRET_KEY`, `GATEWAY_SECRET`, `RABBITMQ_USER`, `RABBITMQ_PASS`.

---

## 5. Setup notification (Gmail SMTP)

### Bước 1: Bật 2FA cho Gmail
1. Vào https://myaccount.google.com/security
2. Bật "2-Step Verification"

### Bước 2: Tạo App Password
1. Vào https://myaccount.google.com/apppasswords
2. Chọn "Mail" → tạo password
3. Copy chuỗi 16 ký tự (xoá dấu cách)

### Bước 3: Cấu hình `.env`

```bash
EMAIL_HOST_USER=your-admin@gmail.com
EMAIL_HOST_PASSWORD=xxxxxxxxxxxxxxxx   # 16 ký tự, không space
ADMIN_EMAIL=your-admin@gmail.com
```

### Bước 4: Rebuild notification service

```bash
docker compose up -d --build notification-service-fastapi
```

### Bước 5: Test

```bash
# Đăng nhập web app → đặt 1 booking
# Check email inbox + FE notification bell
```

Logs:
```bash
docker compose logs -f notification-service-fastapi | grep -E "Email|Realtime"
```

---

## 6. Frontend

```bash
cd spotlove-ai
npm ci
cp .env.example .env
# Set VITE_GATEWAY_SECRET, VITE_API_URL, VITE_WS_URL trong .env
npm run dev       # http://localhost:8080
```

Build production:
```bash
npm run build     # output to dist/
```

---

## 7. Unity Digital Twin

```bash
cd ParkingSimulatorUnity
# Mở bằng Unity Hub với editor 2022.3.62f3 LTS
```

Trước khi Play, seed dữ liệu Unity tương thích:

```bash
cd backend-microservices
python seed_unity_test_data.py
python seed_unity_slots.py
```

Mở Play Mode trong Unity Editor → simulator gọi backend thật qua HTTP/WebSocket.

---

## 8. Kiểm thử

### Backend tests

Mỗi service Django/FastAPI có pytest:
```bash
cd backend-microservices/<service>
pip install -r requirements.txt
pytest
```

### E2E scripts (root `backend-microservices/`)

```bash
python test_e2e_full_flow.py      # Full booking → check-in → check-out
python test_ai_full.py             # AI services (plate + banknote + slot)
python test_chatbot_e2e.py         # Chatbot intent + RAG
```

### Frontend tests

```bash
cd spotlove-ai
npm run test            # Vitest unit
npm run e2e             # Playwright E2E
```

---

## 9. Cấu trúc thư mục

```
smart_parkinglot/
├── backend-microservices/
│   ├── auth-service/                # Django · /auth/* · OAuth
│   ├── booking-service/             # Django + Celery · /bookings/*
│   ├── parking-service/             # Django · /parking/*
│   ├── vehicle-service/             # Django · /vehicles/*
│   ├── notification-service-fastapi/# FastAPI · email + WS push
│   ├── payment-service-fastapi/     # FastAPI · MoMo/VNPay
│   ├── chatbot-service-fastapi/     # FastAPI · Gemini + RAG
│   ├── ai-service-fastapi/          # FastAPI · YOLO/OCR/banknote
│   ├── gateway-service-go/          # Go · API gateway
│   ├── realtime-service-go/         # Go · WebSocket
│   ├── shared/                      # Python shared package
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   ├── .env.example
│   └── seed_test_user.py            # Tạo test account
├── spotlove-ai/                     # Frontend React PWA
├── ParkingSimulatorUnity/           # Unity 2022.3 LTS Digital Twin
├── infra/
│   ├── nginx/nginx.conf
│   └── cloudflare/cloudflared/
├── docs/
│   ├── architecture/                # ADR + context
│   ├── slides/                      # KLTN presentation
│   │   ├── generate_kltn_slides.py
│   │   ├── ParkSmart_KLTN_Slides.pptx
│   │   └── PRESENTATION_GUIDE.md
│   ├── screenshots/
│   └── notes/
├── scripts/
│   └── deploy-local.ps1
├── CLAUDE.md                        # Instructions cho AI dev tool
└── README.md                        # File này
```

---

## 10. Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Django REST Framework · FastAPI (async) · Go + Gin |
| **Frontend** | React 18 · Vite · TypeScript · Redux Toolkit · shadcn/ui + Tailwind |
| **AI / ML** | PyTorch + CUDA 11.6 · YOLOv8 · EfficientNetV2-S · Siamese · OneClass SVM · Gemini 2.5 Flash · ChromaDB · sentence-transformers |
| **Database** | MySQL 8 (relational) · Redis × 6 DBs (cache/session/pub-sub) · RabbitMQ AMQP (event bus) |
| **Infrastructure** | Docker Compose · Nginx · Cloudflare Tunnel + Pages · GitHub Actions CI/CD |
| **Digital Twin** | Unity 2022.3 LTS · C# · NavMesh AI |

---

## 11. Triển khai production

### Local Production (Docker Compose + Cloudflare Tunnel)

```bash
cd backend-microservices

# Build FE static
cd ../spotlove-ai && npm run build && cd ../backend-microservices

# Up production overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Start Cloudflare Tunnel (configured in infra/cloudflare/cloudflared/config.yml)
cloudflared tunnel run parksmart
```

### Cloudflare Pages (Frontend only)

GitHub Actions workflow `.github/workflows/deploy-cloudflare-pages.yml` auto-deploy khi push `main`.

Required GitHub secrets:
- `CF_API_TOKEN` · `CF_ACCOUNT_ID` · `CF_PAGES_PROJECT`
- `VITE_API_URL` · `VITE_WS_URL` · `VITE_GATEWAY_SECRET`

---

## 12. Troubleshooting

### Service không healthy
```bash
docker compose logs <service-name> --tail=50
docker compose restart <service-name>
```

### MySQL connection refused
```bash
# Đợi MySQL fully started (~30s lần đầu)
docker compose ps mysql
# Phải hiện "(healthy)"
```

### Email không gửi
```bash
docker compose logs notification-service-fastapi | grep -i email
# Common issues:
# 1. EMAIL_HOST_PASSWORD chưa set hoặc sai (phải là 16-char Gmail App Password)
# 2. 2FA chưa bật cho Gmail account
# 3. SMTP rate limit (Gmail free: 500 emails/day)
```

### Gateway 403 Forbidden
- Service nội bộ thiếu header `X-Gateway-Secret` → kiểm tra `GATEWAY_SECRET` đồng nhất giữa các service env

### Unity simulator không kết nối backend
```bash
# Seed lại dữ liệu Unity-compatible
cd backend-microservices
python seed_unity_test_data.py
python seed_unity_slots.py
```

### AI service OOM (out of memory)
- GPU < 4GB → giảm batch size trong `ai-service-fastapi/app/config.py`
- Hoặc disable AI service nếu chỉ test web flow:
  ```bash
  docker compose stop ai-service-fastapi
  ```

---

## License

MIT — xem file [LICENSE](LICENSE) (nếu có).

## Contact

- **Sinh viên**: Nguyễn Hải Minh — `dang.nguyenhai2k2@gmail.com`
- **GitHub**: https://github.com/haiminh287/smart_parkinglot
- **Demo live**: https://parksmart.ghepdoicaulong.shop

## Tài liệu tham khảo

- Toàn bộ ADR (Architecture Decision Records): [`docs/architecture/`](docs/architecture/)
- Slide KLTN: [`docs/slides/ParkSmart_KLTN_Slides.pptx`](docs/slides/ParkSmart_KLTN_Slides.pptx)
- Hướng dẫn thuyết trình: [`docs/slides/PRESENTATION_GUIDE.md`](docs/slides/PRESENTATION_GUIDE.md)
