# 💰 AI Nhận Diện Tiền Mặt — Tổng Quan Dự Án

> **Trạng thái tổng thể:** Code ~85% hoàn thành | Data: 0% | Trained Models: 0%
> **Kiến trúc:** Clean Architecture (API → Engine → ML Inference)
> **Service:** `ai-service-fastapi/` (FastAPI, Python 3.10+)

---

## 📁 Cấu Trúc File

```
ai-service-fastapi/
├── app/
│   ├── engine/                          ← Pipeline xử lý chính
│   │   ├── pipeline.py                  ✅ Hybrid MVP Pipeline Orchestrator
│   │   ├── detector.py                  ✅ YOLOv8n Banknote Detector (Stage 1)
│   │   ├── ai_classifier.py            ✅ MobileNetV3-Large AI Fallback (Stage 2B)
│   │   ├── color_classifier.py          ✅ HSV Color Classification (Stage 2A)
│   │   ├── preprocessing.py             ✅ White Balance + Quality Gate (Stage 0)
│   │   └── cash_session.py              ✅ Cash Payment Session Manager
│   ├── ml/
│   │   ├── inference/
│   │   │   └── cash_recognition.py      ✅ ResNet50 Inference Engine
│   │   ├── training/
│   │   │   └── train_cash_recognition.py ✅ ResNet50 Training Pipeline
│   │   └── banknote/
│   │       ├── train_classifier.py      ✅ EfficientNetV2-S (Bank-Grade)
│   │       └── train_security.py        ✅ Siamese + OneClass SVM (Bank-Grade)
│   ├── routers/
│   │   ├── esp32.py                     ✅ ESP32 Cash Payment Endpoint
│   │   └── detection.py                 ✅ Web Detection Endpoints
│   └── schemas/                         ✅ Pydantic schemas
├── capture_data.py                      ✅ Interactive Camera Data Collection
├── organize_banknote_images.py          ✅ Batch Image Organizer
├── CASH_DATA_COLLECTION_GUIDE.md        ✅ Hướng dẫn lấy data (Tiếng Việt)
└── tests/
    └── test_api_banknote.py             ✅ API Tests
```

---

## 🔄 Pipeline Xử Lý (Luồng Chính)

```
Hình ảnh đầu vào (upload / camera / base64)
         │
         ▼
┌─────────────────────────────────────┐
│  Stage 0: PREPROCESSING             │
│  ├─ check_quality()                  │
│  │   ├─ Blur: Laplacian variance     │
│  │   └─ Exposure: mean brightness    │
│  └─ white_balance() — LAB equal.     │
│  Status: ✅ HOÀN THÀNH (pure OpenCV) │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│  Stage 1: DETECTION (YOLOv8n)       │
│  ├─ Nếu có YOLO model → detect()    │
│  └─ Nếu không → dùng full image     │  ← HIỆN TẠI: Không có model
│  Status: ✅ Code xong | ❌ Chưa có   │
│           trained YOLO model          │
└────────────┬────────────────────────┘
             ▼ (cropped banknote)
┌─────────────────────────────────────┐
│  Stage 2A: COLOR (HSV Histogram)     │
│  ├─ Tính dominant hue                │
│  ├─ So sánh với 9 mệnh giá          │
│  ├─ SAFE group ≥ 0.75 → PASS        │
│  │   (100k xanh lá, 200k đỏ)        │
│  └─ DANGER group ≥ 0.90 → PASS      │
│  Status: ✅ HOÀN THÀNH (no ML)       │
└────────────┬────────────────────────┘
      ┌──────┴──────┐
      │  Đạt?       │
      ├── CÓ ───────┤──→ Return ACCEPT (method=color)
      │             │
      └── KHÔNG ────┤
                    ▼
┌─────────────────────────────────────┐
│  Stage 2B: AI FALLBACK               │
│  (MobileNetV3-Large)                 │
│  ├─ Nếu có model → classify()        │
│  └─ Nếu không → stub hue guess       │  ← HIỆN TẠI: Chạy stub
│     (confidence cố định = 0.50)       │
│  Status: ✅ Code xong | ❌ Chưa có    │
│           trained MobileNetV3 model   │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│  QUYẾT ĐỊNH CUỐI CÙNG               │
│  ├─ conf > 0.3 → ACCEPT             │
│  └─ else → LOW_CONFIDENCE            │
└─────────────────────────────────────┘
```

---

## 🤖 Danh Sách ML Models

| #   | Model                 | Architecture                     | File cần có                   | Dùng ở đâu                  | Đã train?          |
| --- | --------------------- | -------------------------------- | ----------------------------- | --------------------------- | ------------------ |
| 1   | Color Classifier      | HSV histogram (thuật toán thuần) | Không cần file                | Pipeline Stage 2A           | ✅ Không cần train |
| 2   | Banknote Detector     | YOLOv8n                          | `banknote_yolov8n.pt`         | Pipeline Stage 1            | ❌ CHƯA            |
| 3   | AI Fallback           | MobileNetV3-Large                | `banknote_mobilenetv3.pth`    | Pipeline Stage 2B           | ❌ CHƯA            |
| 4   | Cash Classifier       | ResNet50                         | `cash_recognition_best.pth`   | Endpoint `/ai/detect/cash/` | ❌ CHƯA            |
| 5   | Bank-Grade Classifier | EfficientNetV2-S                 | `efficientnet_classifier.pth` | Chưa tích hợp pipeline      | ❌ CHƯA            |
| 6   | Siamese Network       | ResNet18 backbone                | `siamese_network.pth`         | Chưa tích hợp pipeline      | ❌ CHƯA            |
| 7   | OneClass SVM          | ResNet18 + SVM                   | `oneclass_svm.pkl`            | Chưa tích hợp pipeline      | ❌ CHƯA            |

**→ Hiện tại 0/6 model đã được train. Hệ thống chạy hoàn toàn bằng fallback/stub.**

---

## 📊 Data Cần Cung Cấp

### Cấu trúc thư mục

```
dataset_root/
├── real/                         ← BẮT BUỘC
│   ├── 1000/                     ← Mỗi mệnh giá 1 folder
│   │   ├── img_001.jpg
│   │   ├── img_002.jpg
│   │   └── ...
│   ├── 2000/
│   ├── 5000/
│   ├── 10000/
│   ├── 20000/
│   ├── 50000/
│   ├── 100000/
│   ├── 200000/
│   └── 500000/
├── print_attack/                 ← TÙY CHỌN (cho OneClass SVM)
│   └── (cùng cấu trúc)
└── screen_attack/                ← TÙY CHỌN (cho OneClass SVM)
    └── (cùng cấu trúc)
```

### Số lượng ảnh cần

| Mức độ              | Ảnh / mệnh giá | Tổng (9 mệnh giá) | Ghi chú              |
| ------------------- | -------------- | ----------------- | -------------------- |
| Tối thiểu           | 50             | 450               | Đủ để test           |
| Khuyến nghị         | 200            | 1,800             | Accuracy tốt         |
| Với attack (3 loại) | 200 × 3        | 5,400             | Cho anti-counterfeit |

### 9 Mệnh giá hỗ trợ

`1000`, `2000`, `5000`, `10000`, `20000`, `50000`, `100000`, `200000`, `500000` VND

### Yêu cầu ảnh

- **Kích thước:** Tối thiểu 224×224 pixels (script tự resize)
- **Định dạng:** JPG / PNG
- **Nền:** Đa dạng (bàn gỗ, nền trắng, tay cầm, v.v.)
- **Góc chụp:** Đa dạng (thẳng, nghiêng, xoay nhẹ)
- **Ánh sáng:** Đa dạng (tự nhiên, đèn, tối nhẹ)
- **Mặt:** Cả mặt trước và mặt sau

### Cách lấy data

**Cách 1: Dùng camera (Interactive)**

```bash
cd ai-service-fastapi
python capture_data.py
# Điều khiển: SPACE=chụp, N/P=đổi mệnh giá, A=tự động chụp, Q=thoát
```

**Cách 2: Sắp xếp ảnh có sẵn (Batch)**

```bash
python organize_banknote_images.py --input /path/to/photos --output dataset/ --augment
# Tự nhận diện mệnh giá từ tên file hoặc tên subfolder
```

---

## 🌐 API Endpoints

| Endpoint                               | Method | Mô tả                                | Model dùng                  |
| -------------------------------------- | ------ | ------------------------------------ | --------------------------- |
| `POST /ai/detect/banknote/`            | POST   | **Pipeline chính** (full/fast mode)  | Color + MobileNetV3         |
| `POST /ai/detect/banknote/?mode=fast`  | POST   | Chỉ color (bỏ AI fallback)           | Color only                  |
| `POST /ai/detect/cash/`                | POST   | ResNet50 standalone                  | `cash_recognition_best.pth` |
| `POST /ai/parking/esp32/cash-payment/` | POST   | Thanh toán tiền mặt tại cổng         | Hybrid pipeline             |
| `POST /ai/train/cash/`                 | POST   | Train ResNet50 (background)          | —                           |
| `POST /ai/train/banknote-pipeline/`    | POST   | Train bank-grade models (background) | —                           |

---

## 🖥️ Frontend Integration

| Frontend Component               | Backend Endpoint                       | Protocol            |
| -------------------------------- | -------------------------------------- | ------------------- |
| `BanknoteDetectionPage.tsx`      | `POST /ai/detect/banknote/`            | multipart/form-data |
| `ai.api.ts` → `detectBanknote()` | Response: `BanknoteDetectionResponse`  | JSON                |
| `KioskPage.tsx` (cash payment)   | `POST /ai/parking/esp32/cash-payment/` | JSON base64         |

---

## ✅ Đã Hoàn Thành

| Component                          | Chi tiết                                     |
| ---------------------------------- | -------------------------------------------- |
| Color Classifier (HSV)             | Chạy không cần model, pure OpenCV            |
| Preprocessing (Quality Gate)       | Blur + Exposure check, White Balance         |
| Pipeline Orchestrator              | Graceful degradation, singleton              |
| Cash Session Manager               | In-memory, thread-safe, 30-min TTL           |
| Data Collection Tool               | Interactive GUI, auto-capture                |
| Image Organizer                    | Batch processing, augmentation               |
| ResNet50 Training Script           | Transfer learning, LR scheduling, early stop |
| EfficientNetV2-S Training Script   | Bank-grade classifier                        |
| Siamese + OneClass Training Script | Bank-grade security                          |
| Training API Endpoints             | Background task execution                    |
| API Tests                          | Route + response validation                  |
| Frontend UI                        | Full detection interface với drag-drop       |
| Frontend API Types                 | Khớp chính xác với backend                   |
| Documentation Guide                | Hướng dẫn tiếng Việt đầy đủ                  |
| ESP32 Cash Payment                 | Session tracking + barrier control           |

---

## ❌ Chưa Hoàn Thành / Cần Cải Tiến

### 🔴 Quan Trọng (Blocking)

| #   | Vấn đề                            | Chi tiết                                                                                |
| --- | --------------------------------- | --------------------------------------------------------------------------------------- |
| 1   | **CHƯA CÓ TRAINING DATA**         | 0 ảnh banknote được thu thập                                                            |
| 2   | **CHƯA CÓ TRAINED MODEL**         | 0/6 model files tồn tại → pipeline chạy stub                                            |
| 3   | **YOLO training script thiếu**    | Không có script train YOLOv8n cho banknote detection                                    |
| 4   | **Import lỗi trong detection.py** | `from app.ml.inference import plate_recognizer` — file `plate_recognizer` không tồn tại |

### 🟡 Trung Bình

| #   | Vấn đề                                            | Chi tiết                                                                                             |
| --- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| 5   | **Bank-grade models chưa tích hợp**               | EfficientNetV2-S, Siamese, OneClass SVM train riêng nhưng CHƯA nối vào `BanknoteRecognitionPipeline` |
| 6   | **Cash session dùng in-memory**                   | Mất data khi restart service. Cần chuyển sang Redis                                                  |
| 7   | **`/ai/detect/cash/` tạo object mới mỗi request** | `CashRecognitionInference()` không có singleton/cache → tốn RAM, slow                                |
| 8   | **Model không preload lúc startup**               | Lazy-load lần đầu gọi → cold start latency                                                           |
| 9   | **2 endpoint trùng chức năng**                    | `/ai/detect/cash/` (ResNet50) vs `/ai/detect/banknote/` (Pipeline) — gây confuse                     |
| 10  | **EfficientNetV2-S val transform bug**            | `dataset.transform = val_transforms` ghi đè toàn bộ dataset, không chỉ val split                     |

### 🟢 Nhỏ

| #   | Vấn đề                           | Chi tiết                                                                               |
| --- | -------------------------------- | -------------------------------------------------------------------------------------- |
| 11  | **Color classifier**             | Hầu hết mệnh giá thuộc DANGER group (threshold 0.90), hiếm khi pass → luôn fallback AI |
| 12  | **AI stub hue ranges chồng lấn** | 500000: (75,105) vs 20000: (95,120) → hue 95-105 undefined                             |

---

## 🗺️ Roadmap Tiếp Theo

```
1. Thu thập data     ──→  2. Train models      ──→  3. Tích hợp & Test
   ├─ capture_data.py      ├─ ResNet50               ├─ Load model at startup
   ├─ organize_images.py   ├─ MobileNetV3            ├─ Singleton caching
   └─ ~1800 ảnh             ├─ YOLOv8n (cần script)  ├─ Remove duplicate endpoint
                            └─ EfficientNetV2-S       └─ E2E test with real model
```

### Ước tính thời gian

| Bước                                 | Thời gian     |
| ------------------------------------ | ------------- |
| Thu thập 1800 ảnh (9 mệnh giá × 200) | 2-3 ngày      |
| Train ResNet50 + MobileNetV3         | 1-2 giờ (GPU) |
| Train/Fine-tune YOLOv8n              | 2-4 giờ (GPU) |
| Tích hợp models vào pipeline         | 1 ngày        |
| Testing E2E                          | 1 ngày        |
| **Tổng**                             | **~5-6 ngày** |
