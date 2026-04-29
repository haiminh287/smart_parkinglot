# ParkSmart — Báo cáo Kỹ thuật Chi tiết KLTN

> **Hệ thống Bãi Đỗ Xe Thông Minh với AI + Digital Twin**
> Khóa luận tốt nghiệp — SV Nguyễn Hải Minh
>
> Tài liệu này giải thích **tại sao** mỗi kỹ thuật/thuật toán được chọn, **cách hoạt động**, **ưu điểm**, **so sánh với lựa chọn khác**, và **kết quả đo lường thực tế**.

---

# PHẦN 1 — KIẾN TRÚC TỔNG THỂ

## 1.1 Tại sao chọn kiến trúc Microservices?

### Bối cảnh

Hệ thống có 10+ chức năng khác nhau: auth, booking, parking, AI, chatbot, realtime, payment, notification, vehicle, gateway. Có 3 lựa chọn kiến trúc:

### So sánh 3 lựa chọn

| Tiêu chí | Monolith | Microservices | Serverless |
|---|---|---|---|
| Thời gian phát triển ban đầu | Nhanh (1 codebase) | Chậm (nhiều service) | Trung bình |
| Scale độc lập từng chức năng | Không | ✅ Có | ✅ Có |
| Công nghệ đa dạng (Python + Go + Node) | Khó | ✅ Dễ | ✅ Dễ |
| Debug cross-service | Dễ | Khó (tracing) | Khó nhất |
| Cost hosting | Thấp | Trung bình | Cao khi traffic lớn |
| Phù hợp đồ án KLTN | ⚠️ Hạn chế thể hiện | ✅ **Tối ưu cho trình bày** | Phức tạp, khó demo |

### Tại sao chọn Microservices

1. **Thể hiện năng lực công nghệ đa dạng** — KLTN cần show kiến thức rộng. Dùng Python (Django/FastAPI cho AI), Go (cho gateway + WebSocket tốc độ cao), phù hợp với kỹ năng yêu cầu.
2. **AI service tách biệt** — AI dùng PyTorch + GPU, nếu gộp chung monolith sẽ kéo chậm các service khác. Tách riêng → AI service chạy trên máy có GPU, các service nhẹ chạy trên VPS rẻ.
3. **Fault isolation** — nếu AI service crash, booking/payment vẫn hoạt động. Monolith thì cả hệ thống sụp.
4. **Scale theo nhu cầu** — giờ cao điểm cần nhiều booking-service, không cần nhiều AI-service → scale riêng biệt.

### Bằng chứng áp dụng trong dự án

10 services trong `backend-microservices/`:
```
auth-service (Django)        → user management, OAuth
booking-service (Django + Celery) → booking CRUD + scheduled tasks
parking-service (Django)     → parking lot/floor/zone/slot
vehicle-service (Django)     → xe đăng ký
notification-service (FastAPI) → email + push
payment-service (FastAPI)    → MoMo/VNPay integration
realtime-service (Go)        → WebSocket, realtime push
ai-service (FastAPI)         → ML inference
chatbot-service (FastAPI)    → LLM orchestration
gateway-service (Go)         → reverse proxy + session auth
```

---

## 1.2 Tại sao dùng API Gateway Pattern?

### Vấn đề

Nếu client gọi trực tiếp 10 service:
- FE phải biết URL của từng service → khó maintain
- Mỗi service tự implement authentication → code lặp
- CORS phải set cho 10 origin
- Rate limiting phải implement 10 lần

### Giải pháp: Gateway Pattern

**Single entry point:** `gateway-service-go :8000` nhận mọi request → proxy tới service đích.

### Cách hoạt động

```
Client (FE/Unity/ESP32)
      ↓
  Gateway :8000
      ├─ /auth/*     → auth-service
      ├─ /bookings/* → booking-service
      ├─ /parking/*  → parking-service
      ├─ /ai/*       → ai-service
      └─ /ws/*       → realtime-service (WebSocket upgrade)
```

### Ưu điểm

1. **Session management tập trung** — Gateway check session cookie, forward header `X-User-ID` + `X-User-Email` cho backend services → các service không cần hiểu session.
2. **Gateway Secret** — service chỉ nhận request có header `X-Gateway-Secret` đúng → chống gọi trực tiếp bypass gateway.
3. **Rate limiting** — 1 chỗ chặn abuse cho tất cả endpoint.
4. **Tech stack flexibility** — Gateway viết Go (performance cao, ít RAM), backend services tùy ý Python/Node/Java.

### Lý do chọn Go cho gateway (thay vì Python/Node)

| Metric | Python (FastAPI) | Node.js | **Go (Gin)** |
|---|---|---|---|
| Req/sec | ~5000 | ~15000 | ✅ ~40000+ |
| Memory | 80MB | 100MB | ✅ 15MB |
| Concurrent connections | GIL hạn chế | Tốt | ✅ Goroutines lý tưởng |
| WebSocket | OK | Tốt | ✅ Native concurrency |

Gateway là bottleneck → chọn công nghệ nhanh nhất.

---

## 1.3 Tại sao dùng Event-Driven với RabbitMQ?

### Bài toán

Khi booking được tạo:
- Notification service cần gửi email
- Payment service cần generate QR
- Analytics cần log event
- Chatbot cần update user behavior

Nếu booking-service gọi trực tiếp 4 service khác → **tight coupling** + chậm (tuần tự).

### Giải pháp: Event-Driven với RabbitMQ

```
booking-service → publish event "booking.created" → RabbitMQ
                                                      ↓
                            ┌─────────────┬──────────┴────┬────────────┐
                            ↓             ↓               ↓            ↓
                      notification    payment       analytics      chatbot
                        consume       consume       consume        consume
```

### Ưu điểm

1. **Asynchronous** — booking-service publish event xong về ngay, không chờ các consumer
2. **Loose coupling** — thêm consumer mới (e.g. logging SIEM) không cần sửa booking-service
3. **Retry & persistence** — RabbitMQ lưu message trên disk, nếu consumer down → message không mất
4. **Fan-out pattern** — 1 event broadcast tới nhiều consumer

### So sánh với các alternative

| | Direct HTTP call | **RabbitMQ** | Kafka |
|---|---|---|---|
| Latency | ~200ms (await tất cả) | ✅ ~10ms (fire-and-forget) | ~5ms |
| Throughput | Thấp | Trung bình (~50k msg/s) | Cao (~1M msg/s) |
| Ordering guarantee | Không | Per-queue | Per-partition |
| Setup complexity | Đơn giản nhất | Trung bình | Phức tạp nhất |
| Phù hợp | Sync, cần response | ✅ **Event hub VN scale** | Big data streaming |

Chọn RabbitMQ vì:
- Throughput đủ cho KLTN scale (không cần Kafka)
- Setup đơn giản hơn Kafka (không cần Zookeeper)
- Docker Compose 1 container là xong

---

## 1.4 Tại sao dùng Redis (6 database khác nhau)?

### Use cases trong dự án

| DB | Service | Purpose |
|---|---|---|
| 0 | Celery | Task queue broker + result backend |
| 1 | auth + gateway | Session storage |
| 2 | booking | Cache booking lookup |
| 3 | parking | Slot status cache |
| 5 | realtime-go | Pub/sub cho WebSocket |
| 6 | chatbot | Conversation state (30p TTL) |

### Tại sao chọn Redis (không dùng DB trực tiếp)?

1. **Session lookup:** check session mỗi request → DB query chậm (~5ms) vs Redis (~0.1ms). 50× nhanh hơn.
2. **WebSocket pub/sub:** broadcast slot update tới 1000 client simultaneously → Redis native pub/sub, không cần coding.
3. **Celery broker:** task queue cần FIFO + persistence → Redis list structure perfect.
4. **Conversation state:** chatbot context cần TTL 30p → Redis `EXPIRE` built-in.

### Ưu điểm Redis

- **In-memory** → tốc độ đọc/ghi < 1ms
- **Data structures đa dạng:** string, list, hash, set, sorted set, stream
- **Persistence options:** RDB snapshot hoặc AOF log → không mất data khi restart
- **Cluster mode** sẵn sàng scale horizontal khi cần

### So với alternatives

- **Memcached:** chỉ key-value đơn thuần, không có pub/sub → không dùng được cho WebSocket
- **In-memory Python dict:** không share giữa multi-service
- **PostgreSQL LISTEN/NOTIFY:** chỉ 1 node, không cluster được

---

# PHẦN 2 — AI MODULE (GIẢI THÍCH CHI TIẾT TỪNG MODEL)

## 2.1 License Plate OCR — Nhận diện biển số xe

### Bài toán

Camera gate chụp ảnh xe vào → xuất biển số text chính xác → match với biển đã đăng ký trong booking → mở cổng.

**Độ khó:**
- Ảnh mờ do motion (xe chạy)
- Ánh sáng ban đêm
- Biển nghiêng khi xe rẽ
- Biển bẩn, dán keo, che một phần
- Ký tự VN có dấu (hiếm — hầu hết biển số là số + chữ cái Latin)

### Kiến trúc 2-stage

```
Ảnh input (1920x1080)
      ↓
[Stage 1: YOLOv8 detection]
  → Tìm bounding box vùng biển số
  → Output: (x1, y1, x2, y2, confidence)
      ↓
[Crop + Perspective warp]
  → Cắt vùng bbox
  → Nắn biển nghiêng thành chữ nhật thẳng
      ↓
[Stage 2: EasyOCR text recognition]
  → Đọc ký tự trong ảnh đã crop
  → Output: "51A12345", confidence 0.92
      ↓
[Post-processing]
  → Normalize: xoá dấu "-", "." space → "51A12345"
  → Validate format VN: 2 số + 1 chữ + 4-5 số
  → Levenshtein distance với booking plate ≤ 1 → match
```

### Tại sao chọn YOLO cho stage 1?

**Đã thử 3 approach:**

| Approach | Ưu điểm | Nhược điểm | Kết quả |
|---|---|---|---|
| Classical CV (Canny + contour) | Nhanh, không cần train | Fail trên biển nghiêng, ánh sáng kém | ❌ accuracy ~60% |
| Haar Cascade | Đã có pretrained | Nhiều false positive với ảnh phức tạp | ❌ ~75% |
| **YOLOv8** | Deep learning, robust | Cần train + GPU | ✅ **95%+** |

### Thuật toán YOLOv8 (Ultralytics)

**YOLO = You Only Look Once** — CNN dự đoán tất cả bbox trong 1 forward pass:

```
Input image 640x640
      ↓
Backbone: CSPDarknet53 (Cross-Stage Partial network)
  → Feature maps 3 scale: 80x80, 40x40, 20x20
      ↓
Neck: FPN + PAN (Feature Pyramid Network)
  → Kết hợp feature các scale
      ↓
Head: 3 detection layer
  → Mỗi cell dự đoán (x, y, w, h, conf, class)
      ↓
NMS (Non-Maximum Suppression): loại bbox trùng nhau IoU > 0.45
      ↓
Output: list of bboxes
```

**Điểm hay của YOLOv8 (so với YOLOv5):**
- **Anchor-free head** — không cần config anchor boxes, đơn giản hơn
- **Decoupled head** — tách riêng classification và box regression → học tốt hơn
- **BCE loss + CIoU loss** — kết hợp binary cross-entropy cho class với Complete IoU cho bbox → hội tụ nhanh hơn

### Fine-tune trên biển số VN

Dataset:
- ~2000 ảnh biển số VN tự label bằng LabelImg
- Label format: `[class_id, x_center, y_center, width, height]` (YOLO format)
- Train 100 epoch, optimizer SGD + momentum 0.937, lr 1e-3 → 1e-6 cosine decay

**Weights file:** `app/models/license-plate-finetune-v1m.pt` (~6MB, nhẹ vì dùng YOLOv8-nano variant)

### Tại sao chọn EasyOCR cho stage 2?

**So sánh OCR engines:**

| Engine | Accuracy VN | Speed | Dependency |
|---|---|---|---|
| Tesseract 5 | ~70% | Nhanh | Không dấu VN tốt |
| **EasyOCR** | ~92% | Trung bình | ✅ Pretrained VN có dấu |
| Google Vision API | ~98% | Cloud call | Tốn tiền + cần internet |
| TrOCR (Transformer) | ~96% | Chậm | ✅ Fallback khi EasyOCR thấp |
| PaddleOCR | ~94% | Nhanh | Setup phức tạp |

**Thuật toán EasyOCR:**
1. **CRAFT (Character Region Awareness for Text)** — detect text region level character
2. **CRNN (CNN + RNN)** — feature extraction CNN → sequence RNN → CTC decoding

### Fallback TrOCR khi EasyOCR không chắc

```python
if easyocr_confidence < 0.60:
    # Fallback to TrOCR (slower but more accurate)
    ocr_plate = trocr.recognize(plate_crop)
```

TrOCR dùng **ViT (Vision Transformer)** làm encoder + Transformer decoder → đọc sequence text, tốt với ảnh phức tạp.

### Normalization biển số

```python
def normalize_plate(text):
    # Xoá mọi ký tự không phải chữ cái / số
    return re.sub(r'[^A-Z0-9]', '', text.upper())

# "51A-123.45" → "51A12345"
# "51 A 12345" → "51A12345"
```

### Match logic (Levenshtein)

```python
from rapidfuzz.distance import Levenshtein

def plates_match(ocr: str, expected: str) -> bool:
    distance = Levenshtein.distance(ocr, expected)
    return distance <= 1  # cho phép 1 ký tự sai
```

**Lý do:** OCR có thể nhầm `0` ↔ `O`, `1` ↔ `I`. Cho phép 1 sai → user experience tốt hơn, vẫn an toàn.

### Metrics thực tế

- **Detection accuracy (YOLO):** 96.3% (pass threshold 0.5 IoU)
- **OCR accuracy (EasyOCR):** 92.1% (exact match)
- **End-to-end with fallback:** **94.5%**
- **Latency:** ~2s (EasyOCR ~1.8s + YOLO ~0.2s)
- **False accept rate:** <0.5% (nhờ Levenshtein ≤ 1)

---

## 2.2 Banknote Classifier — Nhận diện mệnh giá tiền

### Bài toán

Camera tại cổng check-out chụp tờ tiền → AI phân loại mệnh giá (9 class: 1k, 2k, 5k, 10k, 20k, 50k, 100k, 200k, 500k) → cộng vào running total → mở barrier khi đủ.

**Độ khó cao hơn plate OCR:**
- Tiền VN các mệnh giá có màu giống nhau (500k đỏ-tím, 200k nâu-đỏ, dễ nhầm)
- Tiền cũ bị nhăn, gấp, phai màu
- Ánh sáng LED vàng/halogen thay đổi tông màu
- **Sai không được** (khác với plate, 1 ký tự sai vẫn pass Levenshtein; tiền nhầm 200k thành 500k = mất 300k)

### Kiến trúc 4-tầng (cascade)

```
Ảnh tờ tiền
     ↓
[Tầng 1: Quality Check]
  Laplacian variance → blur score
  Histogram spread → exposure score
  Nếu mờ/cháy sáng → reject "bad_quality"
     ↓
[Tầng 2: Banknote Detector]
  HSV mask + contour → tìm vùng chứa tờ tiền
  Nếu không thấy tờ → reject "no_banknote"
     ↓
[Tầng 3: Color Classifier (primary)]
  Gabor filter + color histogram + SVM
  Confidence > 0.85 → ACCEPT (fast path)
     ↓ (else fall through)
[Tầng 4: Deep Model (fallback)]
  MobileNetV3 / EfficientNetV2-S
  TTA + Rejection logic
  Confidence + margin check → ACCEPT or REJECT
```

### Tại sao thiết kế cascade?

**Performance + accuracy trade-off:**

| Tầng | Latency | Accuracy | Xử lý được |
|---|---|---|---|
| Quality check | 2ms | N/A | Filter ảnh xấu |
| Detector | 5ms | 98%+ detect | Tìm bbox |
| Color classifier | 5ms | ~80% | Easy cases (tiền rõ) |
| Deep model | 150ms | ~98% | Hard cases (tiền mờ, nghiêng) |

**Tổng latency trung bình:** 5+5+5 = 15ms cho easy case (chiếm 70%), 165ms cho hard case (30%) → **weighted avg ~50ms**. Nhanh hơn 3× so với dùng deep model cho mọi case.

### Thuật toán tầng Quality Check

**Laplacian variance for blur detection:**
```python
def is_blurry(img_gray, threshold=100):
    # Laplacian operator: second derivative, detect edges
    laplacian = cv2.Laplacian(img_gray, cv2.CV_64F)
    var = laplacian.var()
    return var < threshold  # var thấp = ít edge = mờ
```

**Nguyên lý:** Ảnh sharp có nhiều edge rõ → Laplacian response cao → variance cao. Ảnh mờ → edges mềm → variance thấp.

**Histogram exposure check:**
```python
def is_over_exposed(img_gray):
    hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256])
    high_bins = hist[230:256].sum()
    return high_bins / hist.sum() > 0.4  # >40% pixels ở vùng trắng
```

### Thuật toán tầng Color Classifier (Gabor + Histogram + SVM)

**Gabor filter** là bộ lọc band-pass mô phỏng khả năng thị giác người — detect edge theo frequency + orientation:

```python
def extract_gabor_features(img):
    features = []
    for theta in [0, 45, 90, 135]:  # 4 orientations
        for freq in [0.1, 0.3]:     # 2 frequencies
            kernel = cv2.getGaborKernel((21,21), sigma=5, theta=theta,
                                          lambd=1/freq, gamma=0.5)
            filtered = cv2.filter2D(img, cv2.CV_32F, kernel)
            features.extend([filtered.mean(), filtered.std()])
    return features  # 8 gabor * 2 stats = 16 features
```

**Color histogram** (HSV space):
```python
hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])  # 32-bin hue
hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
hist_v = cv2.calcHist([hsv], [2], None, [32], [0, 256])
features = np.concatenate([hist_h, hist_s, hist_v]).flatten()
```

**SVM classifier** (RBF kernel):
- Input: 16 Gabor + 96 histogram = 112 features
- Output: 9 class probability
- Training: 3000 ảnh (300/class) → test accuracy ~80%

**Ưu điểm Color Classifier:**
- **Fast** — 5ms/image, không cần GPU
- **Interpretable** — biết tại sao classify (color dominant Gabor response)
- **Catches easy cases** — giảm tải cho deep model

### Thuật toán tầng Deep Model

**MobileNetV3-Large (baseline v1):**

Kiến trúc chính:
```
Input 224x224x3
      ↓
[Stem: Conv2d 16 filters]
      ↓
[15 MBConv blocks với Squeeze-Excitation]
  - Depth-wise separable convolution
  - Inverted residual
  - Hard-swish activation
      ↓
[Avg Pool]
      ↓
[Classifier: Linear 1280 → 9]
      ↓
Softmax → 9-class probability
```

**Điểm hay MobileNetV3:**
- **Depth-wise separable conv** — thay `conv 3x3 full` (9x ops) bằng `depth-wise 3x3 + point-wise 1x1` (~1.1x ops) → nhẹ hơn 9 lần
- **Squeeze-Excitation (SE)** — học attention weight trên channel dimension → model tập trung channel quan trọng
- **Hard-swish** activation → xấp xỉ swish nhưng nhanh hơn trên mobile
- **5.5M parameters** — chạy được trên CPU mobile, fit mọi GPU

**Training setup v1:**
- Pretrained ImageNet weights → replace classifier head
- Fine-tune 25 epochs
- Optimizer Adam, lr 1e-3
- Loss CrossEntropy (không có label smoothing)
- Augment đơn giản: flip + ColorJitter

**Kết quả v1:** **89% accuracy**, chưa đủ cho "tiền không được sai".

### Nâng cấp v2 — EfficientNetV2-S + TTA + Rejection

### Tại sao chuyển sang EfficientNetV2-S?

| Yếu tố | MobileNetV3-Large | **EfficientNetV2-S** | Lý do |
|---|---|---|---|
| Params | 5.5M | 22M | Capacity cao hơn |
| ImageNet top-1 | 75.2% | **83.9%** | Pretrained mạnh hơn |
| Training speed | OK | Fast (fused-MBConv) | ✅ Nhanh hơn v1 |
| Fit GTX 1650 4GB | ✅ | ✅ (với fp16) | Mixed-precision AMP |

**Fused-MBConv** — kỹ thuật mới của EfficientNetV2:
- Các tầng đầu: replace depth-wise conv bằng regular conv 3x3 → nhanh hơn 5× trên GPU
- Các tầng sau: giữ depth-wise → nhẹ
- → **Training speed 4× nhanh hơn** EfficientNet gốc

### Test-Time Augmentation (TTA)

**Ý tưởng:** Thay vì predict 1 lần, predict 5 biến thể của cùng ảnh → average softmax → prediction ổn định hơn.

```python
tta_variants = [
    original,                  # 1. Nguyên ảnh
    horizontal_flip,           # 2. Lật ngang
    rotate_+10_degrees,        # 3. Xoay +10°
    rotate_-10_degrees,        # 4. Xoay -10°
    brightness_+10_percent,    # 5. Sáng hơn 10%
]

probs_list = [model(variant(img)) for variant in tta_variants]
avg_probs = mean(probs_list)  # shape (9,)
```

**Tại sao hiệu quả?**
- Model có thể bias với 1 orientation/lighting cụ thể
- 5 predictions average → giảm variance (random error)
- Tăng accuracy ~1-2% mà không cần train thêm
- Trade-off: inference 5× chậm hơn (25ms → 125ms) — vẫn <200ms

### Rejection Logic — "Precision-First"

**Vấn đề với confidence thuần túy:**

Model có thể trả `top1_conf = 0.85` nhưng thực tế ảnh bị nhiễu, confusion giữa 2 class:
```
probabilities = [0.05, 0.05, 0.05, 0.05, 0.05, 0.40, 0.05, 0.45, 0.05]
                                          50k↑        200k↑
top1 = 200k (0.45)
top2 = 50k (0.40)
margin = 0.05  ← VERY CLOSE — không nên tin
```

**Giải pháp:** Dùng **margin** (chênh lệch top-1 và top-2) để phát hiện ambiguous case.

```python
if top1_conf >= 0.92 AND margin >= 0.25:
    → ACCEPT (rất tự tin)
elif top1_conf >= 0.80 AND margin >= 0.40:
    → ACCEPT (kém tự tin nhưng class khác biệt rõ)
else:
    → REJECT → user scan lại
```

**Kết quả target:**
- Accept rate 85-90% (10-15% reject → user scan lại)
- **Precision at accept ≥ 99.5%** (sai < 1/200 lần)

### Label Smoothing — Calibration

**Vấn đề:** Model có xu hướng over-confident (output 0.99 cho class không đúng).

**Label smoothing:**
```python
# Normal one-hot target:
true_label = [0, 0, 0, 0, 1, 0, 0, 0, 0]  # class 4

# Smoothed target (ε=0.1):
smoothed = [0.0125, 0.0125, ..., 0.9, ..., 0.0125]  # 90% true class, 1.25% cho 8 class khác
```

**Ưu điểm:**
- Model không "cháy" confidence → probability chính xác hơn
- Confidence threshold (0.92) có ý nghĩa hơn
- Giảm overfitting

### Augmentation Strategy — Albumentations

**Tại sao Albumentations (không dùng torchvision)?**
- Nhanh hơn 2× (tối ưu C++ under the hood)
- Nhiều transform hơn: Perspective, CLAHE, CoarseDropout, MotionBlur
- Unified API: image + bbox + mask same transform

**Các transform đã chọn + lý do:**

| Transform | Xác suất | Lý do |
|---|---|---|
| `RandomResizedCrop(0.8-1.0)` | 100% | User chụp xa/gần khác nhau |
| `HorizontalFlip` | 50% | Tiền lật 2 mặt — tăng data |
| `Rotate(±20°)` | 70% | Cầm tiền nghiêng là bình thường |
| `Perspective(0.02-0.08)` | 30% | Không chụp thẳng 90° |
| `RandomBrightnessContrast(±30%)` | 70% | Ánh sáng phòng thay đổi |
| `HueSaturationValue` | 40% | Đèn LED/halogen tông khác |
| `CLAHE` | 20% | Khôi phục vùng thiếu sáng |
| `GaussianBlur` hoặc `MotionBlur` | 30% | Tay run + mất nét |
| `GaussNoise` | 30% | Sensor kém (ban đêm) |
| `CoarseDropout` | 30% | Ngón tay che 1 phần tờ tiền |

**Transform KHÔNG dùng + lý do:**

- **ElasticTransform** — làm biến dạng số seri + mệnh giá in → model học sai pattern
- **MixUp** — mix 2 ảnh với alpha → không phù hợp với tiền (thực tế không có tiền "lai")
- **RGBShift heavy** — thay đổi màu chủ đạo → 50k từ xanh lam có thể thành xanh lá → confused với 100k

### Class Imbalance Handling

**Vấn đề:** 200k chỉ có 457 ảnh train (các class khác ~1800). Sampler uniform → model ít thấy 200k → predict kém.

**Giải pháp: WeightedRandomSampler**

```python
counts = {200000: 457, others: ~1800}
weights = [
    (1.0 / counts[label]) * CLASS_WEIGHTS[label]
    for (_, label) in dataset
]
sampler = WeightedRandomSampler(weights, num_samples=len(dataset), replacement=True)
```

**Kết quả:** Mỗi epoch, class 200k xuất hiện tương đương class khác (do weight 1/count cao). Model học đều các class.

Thêm **class_weights trong CrossEntropyLoss:**
```python
CLASS_WEIGHTS = [1.0]*8 + [1.3]  # 200k nhân 1.3×
loss = CrossEntropyLoss(weight=CLASS_WEIGHTS, label_smoothing=0.1)
```

Double-layer bảo vệ: sampling cân bằng + loss weighted.

### Mixed Precision Training (AMP fp16)

**Vấn đề:** GTX 1650 chỉ 4GB VRAM. EfficientNetV2-S full fp32 + batch 16 = OOM.

**Giải pháp:** Training dùng fp16 cho forward/backward, fp32 chỉ cho weight update:

```python
scaler = GradScaler()  # handle gradient scaling

with autocast():  # fp16 context
    output = model(inputs)
    loss = criterion(output, labels)

scaler.scale(loss).backward()  # scale to avoid underflow
scaler.step(optimizer)
scaler.update()
```

**Ưu điểm:**
- **Memory -50%** → batch 12 fit 4GB
- **Speed +50%** (Tensor Cores on GTX 1650)
- Accuracy gần như identical với fp32

### Kết quả mong đợi v2

| Metric | v1 (MobileNetV3) | **v2 (EfficientNetV2-S)** |
|---|---|---|
| Val top-1 | 89% | **≥98%** |
| Precision at accept | ~90% | **≥99.5%** |
| Accept rate | 100% (không reject) | 85-90% |
| Inference | 50ms | 150-200ms (TTA ×5) |
| Model size | 21MB | 85MB |

---

## 2.3 Parking Slot Detection — Nhận diện ô đỗ xe

### Bài toán

Camera overview chụp 4 hàng slot V1 (72 ô) → AI detect vị trí từng ô + trạng thái (available/occupied/reserved) → hiển thị admin dashboard realtime.

### Tại sao KHÔNG dùng YOLO cho task này?

**Thử nghiệm 3 approach:**

| Approach | Kết quả | Lý do |
|---|---|---|
| YOLO detect xe (COCO class) | ~60% | Unity xe là primitive ngẫu nhiên, không match ảnh thực YOLO train |
| YOLO fine-tune detect "slot" class | Tốn tháng train + label | Không hiệu quả cho grid có shape rõ |
| **OpenCV HSV orange-grid** | ✅ 100% (bãi trống) | Deterministic, không cần train |

### Thuật toán OpenCV HSV

```
Frame Unity (640x480)
      ↓
[Convert BGR → HSV]
      ↓
[HSV mask orange viền slot]
  H: 5-24 (orange range)
  S: >100 (saturated, not pale)
  V: >90 (not too dark)
      ↓
[Morphology]
  CLOSE kernel 3×3, 2 iter → nối gap từ anti-alias
  DILATE kernel 3×3, 1 iter → grid liên tục
      ↓
[findContours RETR_CCOMP]
  Returns 2-level hierarchy:
    - Outer contours (parent=-1): grid cam
    - Inner contours (parent≠-1): HOLES = slot interior
      ↓
[Filter child contours]
  area 0.04% - 2% img_area
  aspect ratio ≤ 3.5
  contour_area / bbox_area > 0.55 (rectangularity)
      ↓
[Classify status per slot]
  Sample HSV patch 35% × 35% ở tâm ô:
    - Green ratio > 55% → "available"
    - Orange ratio > 40% → "reserved"
    - Dark ratio > 75% → "available" (cột/aisle)
    - else → "occupied"
      ↓
[Row reconstruction]
  Nhóm slot theo Y → median spacing → nội suy slot bị xe che
      ↓
[Best-grid cache]
  Nhớ grid đầy đủ nhất từng thấy → fallback khi frame hiện tại kém
      ↓
Output: list of {x1, y1, x2, y2, status, confidence}
```

### Tại sao RETR_CCOMP?

**4 flags trong OpenCV findContours:**

| Flag | Output |
|---|---|
| `RETR_EXTERNAL` | Chỉ outer contour ngoài cùng |
| `RETR_LIST` | Tất cả contour, không hierarchy |
| **`RETR_CCOMP`** | **2-level: outer + holes** |
| `RETR_TREE` | Full hierarchy tree |

Bài toán cần tìm "lỗ" trong grid cam (mỗi ô là 1 lỗ) → **CCOMP** là lựa chọn đúng. TREE thừa thông tin, EXTERNAL không thấy lỗ.

### Tại sao Unlit Shader trong Unity?

**Kinh nghiệm rút ra:** Ban đầu dùng default URP Lit shader → light chiếu làm cam chỗ tối chỗ sáng → HSV mask chỗ được chỗ không → detect không ổn định.

**Fix:** Dùng `Universal Render Pipeline/Unlit` → màu cam đồng nhất 100%, không phụ thuộc lighting.

```csharp
private static void SetFlatOrange(GameObject go, Color color) {
    var shader = Shader.Find("Universal Render Pipeline/Unlit");
    var mat = new Material(shader);
    mat.color = color;
    go.GetComponent<Renderer>().sharedMaterial = mat;
}
```

**Bonus:** Share material giữa tất cả divider → GPU chỉ render 1 material → performance tốt hơn.

### Row Reconstruction

**Vấn đề:** Xe to che hoàn toàn viền cam giữa 2 ô → 2 ô merge thành 1 blob → filter reject → mất 2 ô.

**Giải pháp:** Nhóm slot đã detect theo Y, trong mỗi hàng tính median X spacing → nội suy slot missing:

```python
def reconstruct_missing_slots_in_rows(cells):
    # 1. Cluster by Y coordinate
    rows = group_by_y(cells, threshold=0.5 * median_height)

    # 2. Per row, find X step pattern
    for row in rows:
        row_sorted = sort_by_x(row)
        med_step = median([x2 - x1 for consecutive pairs])
        med_width = median([cell.width for cell in row])

        # 3. Detect gaps > 1.7 × median step → interpolate
        for i in range(len(row) - 1):
            gap = row[i+1].x - row[i].x
            if gap / med_step > 1.7:
                n_missing = int(round(gap / med_step)) - 1
                for m in range(1, n_missing + 1):
                    x = row[i].x + m * med_step
                    interpolated_cell = create_cell_at(x, row[i].y, med_width)
                    # Classify status from HSV patch
                    row.append(interpolated_cell)
```

**Ưu điểm:** Robust với xe che + xe đỗ lệch.

### Best-Grid Cache (in-memory)

**Ý tưởng:** Memo grid lớn nhất từng detect được. Frame hiện tại kém → dùng cache + re-classify status ở vị trí cache:

```python
_BEST_GRID_CACHE = []

def detect_slots(frame):
    kept = detect_current_frame(frame)

    global _BEST_GRID_CACHE
    if len(kept) > len(_BEST_GRID_CACHE):
        _BEST_GRID_CACHE = deep_copy(kept)

    if len(kept) < len(_BEST_GRID_CACHE):
        # Use cache for missing slots, re-classify status
        return fill_from_cache(kept, _BEST_GRID_CACHE, current_hsv)

    return kept
```

**Kịch bản thực tế:**
- Sáng bãi trống → cache đầy đủ 72 slot
- Trưa xe đỗ nhiều → current detect chỉ 60 slot
- Dùng cache 72 slot, re-classify 12 slot bị che → vẫn trả đủ 72 với status chính xác

### Metrics

- **Accuracy slot count:** 100% khi bãi trống, 86-93% khi đầy xe
- **Precision status:** ~95% (occasional false positive ở edge)
- **Latency:** p50 ~80ms/frame
- **Realtime update:** 5 FPS trên dashboard

---

## 2.4 Chatbot NLP — LLM Orchestration

### Bài toán

User chat tự nhiên: "Bãi Vincom ngày mai có chỗ ô tô không?" → bot phải:
1. Hiểu intent (check_availability)
2. Extract entity (lot="Vincom", vehicle_type="ô tô", date="tomorrow")
3. Gọi API parking-service lấy data
4. Trả lời tự nhiên tiếng Việt

### Kiến trúc DDD 3-layer

**Domain-Driven Design** tách rõ 3 tầng:

```
┌─────────────────────────────────────────┐
│ domain/                                 │
│   value_objects/                        │  ← Pure types, không depend FW
│     intent.py       (16 intent enum)    │
│     ai_metrics.py   (metric types)     │
├─────────────────────────────────────────┤
│ application/                            │
│   dto/              (IntentDecision)    │  ← Orchestration layer
│   services/                             │
│     intent_service       (classify)     │
│     action_service       (dispatch)     │
│     response_service     (format)       │
│     metrics_collector    (logging)      │
├─────────────────────────────────────────┤
│ infrastructure/                         │
│   llm/gemini_client.py (Gemini SDK)    │  ← External dependencies
│   external/service_client.py (HTTP)    │
└─────────────────────────────────────────┘

engine/orchestrator.py  ← Entry point, gọi các service
```

### Tại sao chọn DDD?

- **Domain độc lập framework** — đổi Gemini → OpenAI chỉ sửa infrastructure layer
- **Application service testable** — mock infrastructure, test logic business
- **Code tìm đâu rõ ràng** — "muốn sửa response format?" → `response_service`

### Pipeline 5-stage xử lý message

```
[Stage 1: Preprocessing]
  - Normalize: lower, trim, expand abbreviation
  - Detect language (vi/en/mixed)
  - Compute frustration score (past messages có từ "?!!", "wtf")
  - Load user communication style từ DB
          ↓
[Stage 2: Intent Classification]
  - LLM prompt với 16 intent + example
  - Output JSON: {intent, confidence}
  - Fallback: keyword rules nếu LLM fail
          ↓
[Stage 3: Entity Extraction]
  - Schema-driven per intent
  - LLM prompt với required fields
  - Example required cho check_availability: [vehicle_type, lot_name]
  - Fill missing từ context (user's last message)
          ↓
[Stage 4: Action Execution]
  - ActionService.dispatch(intent, entities)
  - Gọi microservice tương ứng
  - E.g. check_availability → parking-service /slots/?lot_id=X
          ↓
[Stage 5: Response Formatting]
  - Template-based (response_formatters.py)
  - Markdown + emoji + suggestions
  - LLM paraphrase cho câu tự nhiên
          ↓
[Logging]
  - chatbot_ai_metric_log: intent_conf, entity_completeness, processing_time
```

### Tại sao dùng LLM thay vì rule-based hoặc CNN intent classifier?

**3 approach đã cân nhắc:**

| | Rule-based | CNN intent classifier | **LLM (Gemini)** |
|---|---|---|---|
| Training data cần | 0 | ~1000 samples / intent | 0 (zero-shot) |
| New intent | Edit code | Re-train | ✅ Chỉ add prompt |
| Entity extraction | Regex khó | NER model riêng | ✅ Trả JSON luôn |
| Vietnamese support | Manual | Tokenizer phức tạp | ✅ Built-in |
| Cost | 0 | GPU training | API cost |
| Accuracy | ~70% | ~85% | ✅ ~93%+ |

LLM thắng rõ ở mọi tiêu chí ngoài cost → cost chấp nhận được cho demo.

### Tại sao chọn Gemini (không dùng GPT-4)?

| | GPT-4 | **Gemini 2.5 Flash** | Claude 3 |
|---|---|---|---|
| Vietnamese accuracy | ✅ Xuất sắc | ✅ Tốt | ✅ Tốt |
| Latency | ~2s | ✅ **0.8s** | ~1.5s |
| Cost per 1M tokens | $30 (input) | **$0.15** | $3 |
| Free tier | Không | ✅ 1500 req/day | Hạn chế |

Gemini Flash rẻ hơn 200× GPT-4, nhanh hơn 2.5× → phù hợp budget KLTN.

### Dual LLM Backend (flexibility)

Code hỗ trợ **2 backend** tự động switch:

```python
class GeminiClient:
    def __init__(self):
        if settings.LLM_BASE_URL:  # OpenAI-compat endpoint (local proxy)
            self._use_openai = True
        else:  # Google Gemini SDK direct
            self._use_openai = False
```

**Use cases:**
- **Primary:** local OpenAI-compat proxy (`gemini-3-flash`) — tránh quota limit
- **Fallback:** Gemini SDK direct khi local proxy down

### Intent Taxonomy — 16 class

```
check_availability  — hỏi chỗ trống
book_slot           — đặt chỗ mới (wizard)
rebook_previous     — đặt lại booking cũ
cancel_booking      — hủy
check_in / check_out — vào/ra
pricing             — hỏi giá
current_parking     — xe tôi đang ở đâu
my_bookings         — lịch sử đặt
payment             — thanh toán
directions          — chỉ đường đến bãi
greeting / goodbye  — xã giao
help                — menu hỗ trợ
feedback            — phản hồi
handoff             — chuyển người thật
unknown             — fallback
```

**Tại sao 16 (không ít hơn hoặc nhiều hơn)?**
- Ít hơn: gộp nhiều intent → accuracy giảm (LLM phân vân)
- Nhiều hơn: mỗi intent ít example → LLM confuse

16 là điểm cân bằng tốt cho scope bãi xe.

### Booking Wizard — Multi-turn Conversation

Intent `book_slot` không xong trong 1 câu. Cần wizard 3 bước:

```
User: "Tôi muốn đặt chỗ"
Bot: "Bạn đặt cho ô tô hay xe máy?" (Step 1: vehicle_type)
User: "ô tô"
Bot: "Bãi nào? [List 5 bãi]" (Step 2: select_lot)
User: Chọn Vincom
Bot: "Tầng + zone?" (Step 3: select_floor_zone)
User: Tầng 1 zone V1
Bot: "Đã đặt V1-16 ✅ + QR code"
```

**State lưu ở Redis DB 6:**
- Key: `chatbot:wizard:<user_id>`
- Value: `{current_step, vehicle_type, lot_id, floor_id, ...}`
- TTL: 30 phút (user bỏ giữa chừng → auto clear)

### Hybrid Confidence Scoring

Đơn giản chỉ dùng LLM confidence không đủ — đôi khi LLM "chắc chắn" nhưng thực tế sai context.

**Hybrid formula:**
```python
hybrid_conf = (
    0.4 * llm_confidence       # LLM tự nhận
    + 0.3 * entity_completeness # Entity đã extract đủ chưa
    + 0.3 * context_match       # Có match history không
)

if hybrid_conf < 0.5:
    return "Xin lỗi, tôi chưa hiểu rõ. Bạn nói lại được không?"
```

**Ưu điểm:** Kết hợp 3 dimension → ít false confident.

### AI Metrics Collection

Mọi message lưu log vào `chatbot_ai_metric_log`:

```python
{
    "id": uuid,
    "user_id": uuid,
    "message": "có chỗ ô tô không",
    "intent": "check_availability",
    "intent_confidence": 0.92,
    "entities": {"vehicle_type": "ô tô"},
    "entity_completeness": 0.5,  # missing lot_name
    "context_match": 1.0,
    "hybrid_confidence": 0.73,
    "response": "🅿️ Hiện có 161 chỗ trống cho ô tô...",
    "processing_time_ms": 1820,
    "feedback": null  # user rating after response
}
```

**Dùng để:**
- Debug — tìm câu nào fail + tại sao
- Improve — tune prompt theo trend sai
- Report — thống kê intent distribution

### Proactive Notification

Worker consume RabbitMQ event → push notification:

```
booking.confirmed → push "✅ Booking V1-16 đã được xác nhận"
booking.expiring_soon → push "⏰ Còn 15 phút hết giờ đỗ, gia hạn?"
payment.failed → push "❌ Thanh toán thất bại, vui lòng check thẻ"
```

**Channel:**
- In-app qua WebSocket
- Telegram bot (dùng `python-telegram-bot` lib)
- Email (SMTP qua notification-service)

---

# PHẦN 3 — UNITY DIGITAL TWIN

## 3.1 Tại sao dùng Unity làm Digital Twin?

### Bài toán

Demo KLTN cần show toàn bộ flow end-to-end: xe vào → check-in → navigate → check-out. Options:

### So sánh 3 cách demo

| Cách | Budget | Visual | Automation | Phù hợp KLTN |
|---|---|---|---|---|
| Bãi xe thật + camera thật | 50tr+ | ✅ Real | Khó automate | ❌ Không khả thi |
| Screenshots + video ghép | 0đ | Tĩnh | Không | ⚠️ Kém thuyết phục |
| **Unity Digital Twin** | 0đ | ✅ 3D animated | ✅ Full automation | ✅ **Tối ưu** |

### Ưu điểm Unity

1. **Visual hóa** — hội đồng thấy xe chạy, cổng mở, ô đổi màu → dễ hiểu hơn console log
2. **Gọi backend thật** — Unity không mock, dùng HTTP client thật → test end-to-end thực sự
3. **Training data source** — camera ảo stream về AI service = source data training (nếu muốn mở rộng)
4. **Tái sử dụng** — sau KLTN có thể scale thành production, chỉ thay "virtual camera" bằng camera IP thật
5. **Budget-friendly** — Unity Personal miễn phí

### So sánh Unity với alternatives

| | Unity | Unreal | Web 3D (Three.js) |
|---|---|---|---|
| Learning curve | Trung bình | Cao | Thấp |
| C# scripting | ✅ | C++ khó | JavaScript OK |
| Performance 3D | ✅ Tốt | ✅ Tốt nhất | Trung bình |
| Mobile build | ✅ Dễ | ✅ | ⚠️ PWA |
| Community VN | ✅ Lớn | Nhỏ | Trung bình |

Unity thắng ở điểm balance: dễ học, performance đủ, VN dễ support.

## 3.2 Procedural Parking Lot Generation

### Tại sao procedural (không hard-code)?

**2 approach dựng bãi:**

| Hard-code (Editor) | **Procedural (Runtime)** |
|---|---|
| Kéo thả mesh trong Editor | Code sinh mesh runtime |
| Thay đổi size = remake scene | Thay param = regenerate tự động |
| File scene nặng | File scene nhẹ (chỉ config) |
| Khó version control | Code trong Git |

Procedural thắng khi cần **scale** + **iterate nhanh**.

### Cách hoạt động `ParkingLotGenerator.cs`

```csharp
public class ParkingLotGenerator : MonoBehaviour {
    public int paintedSlotsPerRow = 18;  // 18 slot/hàng
    public int paintedRows = 2;           // 2 hàng × 2 = 4 hàng tổng
    public int garageSlotCount = 5;
    public float slotWidth = 2.5f;
    public float slotDepth = 5f;

    public void Generate() {
        // 1. Clear existing
        ClearExisting();

        // 2. Sinh floor platform
        CreateCube(parent, "FloorPlatform", pos, size, color);

        // 3. Sinh 4 hàng × 18 slot
        for (int row = 0; row < paintedRows * 2; row++) {
            for (int col = 0; col < paintedSlotsPerRow; col++) {
                Vector3 pos = ComputeSlotPosition(row, col);
                CreateSlot(pos, row, col);
            }
        }

        // 4. Sinh garage + motorbike
        CreateGarageSlots();
        CreateMotorbikeSlots();

        // 5. Sinh pillar, wall, curb, road markings
        CreatePillars();
        CreateRoadMarkings();

        // 6. Register slot codes vào dictionary cho sync
        slotRegistry["V1-01"] = slotGO1;
        slotRegistry["V1-02"] = slotGO2;
        // ...
    }
}
```

**Output:** 72 V1 + 5 garage + 20 motorbike = 97 slot, sinh trong 2-3 giây.

### Best practices khi dựng Unity simulator

1. **Dùng primitive shapes** — Cube, Cylinder, Plane → nhẹ, render nhanh
2. **Shared material** — tất cả divider dùng 1 material → GPU 1 draw call
3. **Flat color / Unlit shader** — cho các object AI cần detect (viền cam) → HSV ổn định
4. **Layer + tag đúng** — xe ở layer "Vehicle", slot ở "Slot" → easy raycast + physics collision
5. **Naming convention** — `Slot_V1_01`, `Barrier_GATE_IN_01` → debug nhìn hierarchy dễ
6. **NavMesh baked ở Editor** — không bake runtime (tốn 30s)

## 3.3 Virtual Camera System

### Mục tiêu

Unity scene có 8 "camera ảo" đặt ở vị trí khác nhau → stream JPEG về AI service:

```
virtual-f1-overview       ← top-down y=13, FOV 120°, bao 4 hàng V1
virtual-anpr-entry        ← gate vào, chụp biển số xe tới
virtual-anpr-exit         ← gate ra
virtual-f1-checkin-ocr    ← gate camera ANPR riêng
virtual-f1-checkout-ocr   ← gate camera check-out
virtual-f1-slot-camera    ← camera trên slot
virtual-cash-scanner      ← chụp tiền ở check-out
virtual-garage-overview   ← bao garage
```

### Cách implementation

```csharp
public class VirtualCamera : MonoBehaviour {
    public string cameraId;
    public Camera unityCamera;
    public float fps = 5f;

    private RenderTexture rt;
    private Texture2D readbackTex;

    void Start() {
        // Setup render texture 640x480
        rt = new RenderTexture(640, 480, 24);
        unityCamera.targetTexture = rt;
        readbackTex = new Texture2D(640, 480, TextureFormat.RGBA32, false);

        InvokeRepeating(nameof(CaptureFrame), 0, 1f / fps);
    }

    void CaptureFrame() {
        // 1. Render scene vào RT
        unityCamera.Render();

        // 2. Readback GPU → CPU
        RenderTexture.active = rt;
        readbackTex.ReadPixels(new Rect(0, 0, 640, 480), 0, 0);
        readbackTex.Apply();

        // 3. Encode JPEG
        byte[] jpegBytes = readbackTex.EncodeToJPG(75);

        // 4. POST lên AI service
        StartCoroutine(PostFrame(jpegBytes));
    }

    IEnumerator PostFrame(byte[] jpeg) {
        var form = new WWWForm();
        form.AddBinaryData("frame", jpeg, "frame.jpg", "image/jpeg");
        form.AddField("camera_id", cameraId);
        UnityWebRequest.Post(aiServiceUrl + "/ai/cameras/frame", form).SendWebRequest();
    }
}
```

### Backend lưu frame buffer

```python
_virtual_frame_buffer: dict[str, VirtualFrame] = {}
_buffer_lock = threading.Lock()

@router.post("/ai/cameras/frame")
async def receive_frame(frame: UploadFile, camera_id: str):
    jpeg_bytes = await frame.read()
    with _buffer_lock:
        _virtual_frame_buffer[camera_id] = VirtualFrame(
            jpeg_data=jpeg_bytes,
            timestamp=time.monotonic(),
        )
    return {"ok": True}
```

**Khi AI cần detect:** đọc từ buffer (thay vì capture camera thật):
```python
vf = _virtual_frame_buffer.get("virtual-f1-overview")
if vf and (time.monotonic() - vf.timestamp < 10):
    frame = decode_jpeg(vf.jpeg_data)
    slots = detect_slots(frame)
```

### Ưu điểm thiết kế này

1. **Thay thế 1:1 camera thật** — backend code giống y như production, chỉ khác nguồn frame
2. **Stream rate linh hoạt** — Unity chỉnh FPS theo nhu cầu (overview 5 FPS, ANPR 15 FPS)
3. **Multi-camera** — 8 camera cùng 1 scene, không cần 8 máy
4. **Debug trực quan** — admin dashboard hiển thị tất cả camera song song

## 3.4 ESP32 IoT Simulator

### Mục tiêu

Giả lập 4 ESP32 gate (check-in/out, verify-slot, cash-pay) mà không cần phần cứng thật.

### Cách hoạt động

`ESP32Simulator.cs` là MonoBehaviour có IMGUI debug panel:

```csharp
void OnGUI() {
    // Debug panel for KLTN demo
    GUILayout.BeginArea(new Rect(10, 10, 400, 600));
    GUILayout.Label("ESP32 IoT Simulator");

    if (GUILayout.Button("🟢 Press CHECK-IN (Gate 1)"))
        StartCoroutine(DoCheckIn(gateId: "GATE-IN-01"));

    if (GUILayout.Button("🔴 Press CHECK-OUT (Gate 2)"))
        StartCoroutine(DoCheckOut(gateId: "GATE-OUT-01"));

    if (showMomoQr)
        DrawMomoPaymentPopup();

    GUILayout.EndArea();
}

IEnumerator DoCheckIn(string gateId) {
    // Gọi AI service ESP32 check-in endpoint giống device thật
    var request = new ESP32CheckInRequest {
        GateId = gateId,
        QrData = latestPendingQr,
    };

    yield return apiService.ESP32CheckIn(request, response => {
        if (response.Data.Success) {
            // Animate barrier mở
            StartCoroutine(AnimateBarrier(gateId, open: true));
            // Spawn xe trong scene
            vehicleQueue.SpawnCarForBooking(response.Data.BookingId);
        }
    });
}
```

### Barrier animation

Servo thật → quay 0° ↔ 90° trong 0.5s. Unity mô phỏng:

```csharp
IEnumerator AnimateBarrier(GameObject barrier, bool open) {
    float targetAngle = open ? 90f : 0f;
    float startAngle = barrier.transform.localEulerAngles.z;
    float duration = 0.5f;
    float elapsed = 0;

    while (elapsed < duration) {
        elapsed += Time.deltaTime;
        float angle = Mathf.Lerp(startAngle, targetAngle, elapsed / duration);
        barrier.transform.localEulerAngles = new Vector3(0, 0, angle);
        yield return null;
    }

    // Auto close after 5s
    if (open) {
        yield return new WaitForSeconds(5f);
        StartCoroutine(AnimateBarrier(barrier, open: false));
    }
}
```

### Full trust test của Unity simulator

Unity gọi đúng endpoint ESP32 sẽ gọi:
- `POST /ai/parking/esp32/check-in/` — auth bằng `X-Device-Token`
- `POST /ai/parking/esp32/check-out/`
- `POST /ai/parking/esp32/verify-slot/`
- `POST /ai/parking/esp32/cash-payment/`
- `POST /ai/parking/esp32/heartbeat` (mỗi 30s)

**Tức là:** Unity simulator + ESP32 vật lý gọi CÙNG backend code → test Unity = verify ESP32 cũng pass.

## 3.5 Vehicle Spawning & NavMesh

### Flow

```
1. User web: đặt V1-23
2. Backend: booking_created → WebSocket broadcast "unity.spawn_vehicle"
3. Unity: ParkingDataSync nhận event → VehicleQueue.Spawn(slot=V1-23)
4. Xe spawn ở gate entry (Vector3.zero trước gate)
5. NavMeshAgent.SetDestination(slot.position)
6. Unity NavMesh tự tính path → xe chạy đến slot
7. Khi tới → xe park, đổi state "parked"
```

### NavMesh setup

1. **Bake NavMesh** ở Editor (Window → AI → Navigation)
2. **Walkable surface:** floor platform của ParkingLotGenerator
3. **Obstacles:** pillar, wall, curb
4. **Agent radius:** 0.8m (bằng xe VN)
5. **Auto-unparent** vehicle khỏi parent scene → agent có thể free move

### License plate trên xe

Mỗi xe có plate procedural:
```csharp
void AssignPlate(GameObject vehicle, string plate) {
    var renderer = vehicle.GetComponentInChildren<TextMeshPro>();
    renderer.text = plate;
    // Render ra texture → project lên body xe
}
```

---

# PHẦN 4 — SECURITY & PERFORMANCE

## 4.1 Session-based Authentication

### Tại sao không dùng JWT?

**So sánh JWT vs Session:**

| | JWT | **Session (cookie + Redis)** |
|---|---|---|
| Stateless | ✅ | ❌ (cần Redis) |
| Revoke token | Khó (blacklist) | ✅ Delete Redis key |
| Payload size | Lớn (~1KB) | Nhỏ (~100 bytes cookie) |
| Refresh flow | Phức tạp | Không cần |
| XSS protection | ⚠️ JS đọc được | ✅ HttpOnly cookie |

Chọn session-based vì:
- **Security:** HttpOnly cookie không bị XSS đọc
- **Simple:** Không cần refresh token flow
- **Revokable:** User logout → delete Redis key luôn

### Implementation

```go
// Gateway login handler
func HandleLogin(c *gin.Context) {
    user, err := authService.Login(email, password)

    sessionID := uuid.New().String()
    redis.Set("session:" + sessionID, user.ID, 7 * 24 * time.Hour)

    c.SetCookie("session_id", sessionID,
        MaxAge: 604800,  // 7 days
        HttpOnly: true,
        SameSite: Lax,
        Secure: true,
    )
}

// Middleware check session
func SessionAuth(c *gin.Context) {
    sessionID := c.Cookie("session_id")
    userID, err := redis.Get("session:" + sessionID)
    if err != nil {
        c.AbortWithStatus(401)
        return
    }

    c.Request.Header.Set("X-User-ID", userID)
    c.Next()
}
```

## 4.2 Gateway Secret — Service-to-Service Auth

**Vấn đề:** Service trong Docker network có thể bị attacker truy cập nếu không firewall kỹ.

**Giải pháp:** Mọi service check header `X-Gateway-Secret`:

```python
class GatewayAuthMiddleware:
    PUBLIC_PATHS = ["/health/", "/admin/", "/_test/"]

    def __call__(self, request):
        if request.path in self.PUBLIC_PATHS:
            return self.get_response(request)

        if request.headers.get("X-Gateway-Secret") != settings.GATEWAY_SECRET:
            return JsonResponse({"error": "Access denied"}, status=403)

        # Set user_id from gateway
        request.user_id = request.headers.get("X-User-ID")
        return self.get_response(request)
```

**Ưu điểm:**
- Attacker chọc vào Docker không gọi được service
- Service không cần tự implement session logic
- Gateway là single source of truth cho auth

## 4.3 Rate Limiting

Gateway implement **token bucket** per user:

```go
rateLimiter := NewTokenBucket(
    rate: 100,      // 100 requests
    per: time.Minute,  // per minute
    burst: 20,      // allow short bursts
)

if !rateLimiter.Allow(userID) {
    c.AbortWithStatus(429)  // Too Many Requests
    return
}
```

## 4.4 AI Model Caching

**Vấn đề:** Load MobileNetV3 (~20MB) mỗi request → 3-5s → timeout.

**Giải pháp:** Singleton + lifespan pre-warm:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm tất cả model ngay startup
    get_slot_detector()           # YOLO
    get_plate_pipeline()          # YOLO + EasyOCR
    _get_pipeline()               # Banknote
    _get_cash_inference()         # Cash classifier

    yield  # app runs here
    # cleanup
```

**Kết quả:** Request đầu tiên sau restart service ~50ms thay vì 30s.

---

# PHẦN 5 — DEPLOYMENT & OPS

## 5.1 Docker Compose — Local Development

**Tại sao Docker (không install trực tiếp)?**

- **Reproducibility:** "works on my machine" → "works in container" → works everywhere
- **Isolation:** 10 service dependencies không conflict nhau
- **1 command run all:** `docker compose up -d` → 10 services + DB + Redis + RabbitMQ
- **Resource control:** `mem_limit`, `cpu_shares` per service

## 5.2 Cloudflare Tunnel — Production

**Bài toán:** KLTN demo cần public URL (`parksmart.ghepdoicaulong.shop`) mà không mua VPS.

**Giải pháp:** Cloudflare Tunnel — reverse proxy từ Cloudflare edge về local machine:

```
User: parksmart.ghepdoicaulong.shop
  → Cloudflare edge (HTTPS, DDoS protection, CDN cache)
  → Cloudflared daemon trên máy SV (outbound connection)
  → Local nginx :80
  → FE dist/ (static) + proxy /api → gateway :8000
```

**Ưu điểm:**
- **Free tier đủ demo** — 10k req/day
- **HTTPS tự động** — Cloudflare cấp SSL
- **No port forwarding** — không cần router config
- **DDoS protection** miễn phí

## 5.3 CI/CD — GitHub Actions

Trigger deploy Cloudflare Pages khi push `main`:

```yaml
# .github/workflows/deploy-cloudflare-pages.yml
on:
  push:
    branches: [main]

jobs:
  deploy:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci && npm run build
      - uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          projectName: ${{ secrets.CF_PAGES_PROJECT }}
          directory: spotlove-ai/dist
```

---

# PHẦN 6 — KINH NGHIỆM & BEST PRACTICES

## 6.1 Kinh nghiệm rút ra

### AI thất bại → rút kinh nghiệm

1. **YOLO cho slot detection fail** — Unity xe primitive không match COCO → phải fallback OpenCV HSV
2. **Banknote v1 89%** không đủ → v2 thêm TTA + rejection → mục tiêu 99.5%
3. **EasyOCR chậm 20s trên test image** → fast-path skip OCR khi dùng test image (cho dev)
4. **Gemini spending cap hit** → dual backend (Google + local OpenAI-compat)

### Backend bug rút kinh nghiệm

1. **ImageFolder sắp xếp alphabetical** (`'10000'` < `'2000'`) → remap sang thứ tự logic (1k→500k)
2. **`_fetch_slot_info` thiếu X-User-ID header** → silent 403 → slot_code rỗng → Unity sync không match
3. **Session cookie SameSite mismatch** → XHR không gửi cookie → 401 khắp FE
4. **`check_payment_status` đọc sai key** (`paymentMethod` vs `paymentType`) → on_exit luôn fail

### Unity kinh nghiệm

1. **URP Lit shader** biến orange không đều → phải dùng **Unlit**
2. **Divider 0.08m** quá nhỏ camera không detect được → tăng **0.18m**
3. **Unity booking poll** thiếu → booking mới tạo không sync → add **PollBookings 10s**
4. **testEmail config sai** → Unity login wrong user → không thấy booking của user khác

## 6.2 Coding standards đã tuân

### Conventional commits

```
feat(ai): add EfficientNetV2-S training script
fix(unity): ConfirmMomoPayment trigger StartDeparture
chore(cleanup): remove dead code
refactor(frontend): enforce FE layering via business services
docs(thesis): gộp 'tiền giấy' + 'tiền mặt' → 1 pipeline
```

### File size limits

- **Function ≤ 50 lines** — dễ review, dễ test
- **File ≤ 300 lines** — refactor khi vượt
- **Nesting ≤ 4** — sâu hơn = DTO hóa

### Language conventions

- **Vietnamese:** docs, commit body, comment giải thích
- **English:** tên biến, function, class, commit type prefix

### Dead code policy

Mỗi sprint xóa approach-drift file, không để `.old`/`.bak`/`_backup` > 1 tuần trong `src/`.

---

# PHẦN 7 — CHI PHÍ & THỰC TẾ TRIỂN KHAI

## 7.1 Budget thực tế cho bãi 50 slot

### Phần cứng

| Item | Qty | Đơn giá | Tổng |
|---|---|---|---|
| Camera IP 4K Hikvision DS-2CD2346G2-I (gate) | 2 | 3,500,000đ | 7,000,000đ |
| Camera dome 2MP Dahua (tầng) | 3 | 1,500,000đ | 4,500,000đ |
| ESP32 DevKit C + sensor module | 4 | 250,000đ | 1,000,000đ |
| Servo MG996R + driver L298N | 2 | 400,000đ | 800,000đ |
| NVR 8ch Hikvision DS-7608NI-Q1 | 1 | 4,000,000đ | 4,000,000đ |
| LED strip WS2812 5m + power 5V 60W | - | - | 2,500,000đ |
| Mini-PC Intel NUC 12 (i5 + 16GB) | 1 | 12,000,000đ | 12,000,000đ |
| GPU external NVIDIA GTX 1660 6GB | 1 | 5,500,000đ | 5,500,000đ |
| TP-Link Omada router + PoE switch 16-port | 1 set | 5,000,000đ | 5,000,000đ |
| Phụ kiện (tủ điện, dây, khung barrier...) | - | - | 8,000,000đ |
| **TỔNG PHẦN CỨNG** | | | **~50,300,000đ** |

### Phần mềm & Cloud (năm)

| Item | Phí |
|---|---|
| Domain `ghepdoicaulong.shop` | 300,000đ |
| Cloudflare Tunnel + Pages | 0đ (free tier) |
| Gemini API (~50k msg/tháng × 12) | 2,400,000đ |
| VPS backup DigitalOcean 2GB | 3,600,000đ |
| MoMo gateway fee 1.5% giao dịch | theo doanh thu |
| **TỔNG SaaS/NĂM** | **~6,300,000đ** |

### Vận hành (tháng)

- Nhân công: 1 tech + 1 bảo vệ luân phiên ca = **15,000,000đ**
- Điện (server + camera + LED): **500,000đ**
- Bảo trì hardware: **500,000đ** (trung bình)
- **TỔNG VẬN HÀNH: 16,000,000đ/tháng**

### Doanh thu ước tính

Giá trung bình 50,000đ/xe/ngày (mix hourly + daily):
- 50 slot × 30 ngày × 70% occupancy = **1,050 xe/tháng**
- Revenue: **52,500,000đ/tháng**
- Gross profit: 52.5 - 16 = **36,500,000đ/tháng**

### ROI

- Payback phần cứng: **50.3tr / 36.5tr ≈ 1.4 tháng**
- Payback cả hệ thống (hardware + 1 năm SaaS): ~1.5 tháng
- Kinh doanh 5 năm: (36.5 × 12 × 5) - 50.3 - (6.3 × 5) = **~2.2 tỷ** lợi nhuận

## 7.2 So sánh với bãi truyền thống

| Tiêu chí | Bãi truyền thống | ParkSmart |
|---|---|---|
| Setup ban đầu | ~20tr (thẻ từ cũ) | 50tr |
| Nhân sự | 3-5 người | 1-2 người |
| Chi phí nhân công/tháng | ~30tr | 15tr |
| Sai sót tính tiền | ~5% | <1% |
| Speed qua cổng | 30-60s | <5s |
| Booking trước | Không | ✅ |
| Chatbot | Intercom bảo vệ | ✅ 24/7 Gemini |
| Analytics | Sổ tay | ✅ Dashboard realtime |
| Payback period | ~6 tháng | ~1.5 tháng |

---

# PHẦN 8 — ĐIỂM KHÁC BIỆT & UNIQUE SELLING POINTS

## 8.1 So sánh ParkSmart vs bãi hiện tại VN

| Feature | Vincom/Aeon | Lot-Park | My-Parking app | **ParkSmart** |
|---|---|---|---|---|
| Đặt trước | ❌ | ⚠️ Chỉ tháng | ✅ | ✅ |
| AI biển số | Một số bãi lớn | ❌ | ❌ | ✅ YOLOv8 |
| AI nhận diện tiền | ❌ | ❌ | ❌ | ✅ **Unique** |
| AI slot detection | Cảm biến siêu âm | ❌ | ❌ | ✅ Camera + OpenCV |
| Chatbot LLM | ❌ | ❌ | Basic | ✅ Gemini 16 intents |
| QR check-in | Một số có | ❌ | ✅ | ✅ |
| Payment cash | Manual | Manual | ❌ | ✅ AI detect mệnh giá |
| Digital twin | ❌ | ❌ | ❌ | ✅ **Unique** |
| Mobile app | Basic | ❌ | ✅ | ✅ PWA |
| Proactive notification | ❌ | ❌ | Basic | ✅ Telegram + email |
| Open source | ❌ | ❌ | ❌ | ✅ Full source |

## 8.2 5 Unique Selling Points

### USP 1: AI nhận diện tiền mặt VN (9 mệnh giá)

**Không bãi nào ở VN hiện có.** Các bãi bắt user trả thẻ/QR/app, không cash. ParkSmart hỗ trợ cash → phục vụ user lớn tuổi, khách du lịch không có app local.

**Technical moat:**
- Dataset 10k+ ảnh thực tế Việt Nam
- MobileNetV3 → EfficientNetV2-S roadmap
- TTA + rejection logic precision-first

### USP 2: Unity Digital Twin

**Không project VN nào có.** Các smart parking project VN demo qua video ghép. ParkSmart có simulator 3D tương tác real-time.

**Technical moat:**
- ~2000 dòng C# (ParkingLotGenerator, VirtualCameraManager, ESP32Simulator, VehicleController)
- Backend agnostic — simulator call cùng API như ESP32 thật
- Training data source nếu muốn mở rộng

### USP 3: Microservices Open-Source Stack

**Không lock-in vendor.** Không như các giải pháp SaaS đóng (ParkingDesk, Zipl...), ParkSmart mã nguồn mở, ai cũng deploy được.

**Stack diversity demonstration:**
- Django + FastAPI + Go + React + Unity
- Docker + RabbitMQ + Redis + MySQL + WebSocket
- Cloudflare + GitHub Actions

### USP 4: Chatbot LLM thực sự thông minh

Khác các FAQ bot trả template. ParkSmart hiểu:
- "Bãi Vincom ngày mai còn chỗ ô tô?" → extract `lot="Vincom"` + `vehicle="car"` + `date="tomorrow"` → query API thật → trả "Vincom còn 67 chỗ, Zone V1: 63 (V1-05, V1-06...)"

**Technical moat:**
- DDD architecture separates concerns
- Schema-driven entity extraction per intent
- Hybrid confidence scoring
- AI metrics collection for continuous improvement

### USP 5: Precision-First AI (cho tiền & biển số)

**"Thà từ chối còn hơn sai"** — đặc biệt quan trọng cho giao dịch tài chính.

- Plate OCR: Levenshtein ≤ 1 filter OCR noise
- Banknote: confidence ≥ 0.92 AND margin ≥ 0.25 → accept, else reject
- Slot detect: best-grid cache fallback khi frame kém

## 8.3 Hướng phát triển (Roadmap sau KLTN)

### Sprint S3 — Offline-first Mode

Nếu mất internet, cổng tạm chuyển "local fallback":
- Barrier có buffer lệnh offline
- Sync lại backend khi online

### Sprint S4 — LiDAR cho Slot Detection 100%

Camera dù tốt cũng có corner case. LiDAR đo khoảng cách → biết chắc slot có chướng ngại.

### Sprint S5 — EV Charging Integration

Bãi có ổ sạc EV → detect xe EV (biển xanh) → gợi ý slot có ổ + tính tiền sạc.

### Sprint S6 — AI Dự đoán Occupancy

Time-series forecast (LSTM / Prophet) từ historical booking → dự đoán giờ nào bãi đầy → gợi ý user đặt trước.

### Sprint S7 — Mobile Native App

PWA đủ cho demo, nhưng native app (React Native / Flutter) có camera + push notification tốt hơn.

### Sprint S8 — Marketplace / Multi-tenant

Mỗi chủ bãi có tenant riêng → quản lý độc lập, ParkSmart làm platform trung gian như Grab Park.

---

# PHẦN 9 — CƠ CHẾ CHỨNG MINH QUY TRÌNH THỰC TẾ

## 9.1 Video demo đã/cần quay

### Video chính demo (5-7 phút) — CẦN QUAY TRƯỚC BUỔI DEFENSE

**Kịch bản:**

| Thời gian | Nội dung | Màn hình |
|---|---|---|
| 0:00 - 0:30 | Intro + đăng nhập web | FE login page |
| 0:30 - 1:30 | Đặt chỗ V1-16, chọn tầng + slot | Booking page wizard |
| 1:30 - 2:30 | Xem live occupancy admin dashboard + chatbot hỏi chỗ trống | Admin + Chatbot panel |
| 2:30 - 3:30 | Chuyển sang Unity: ESP32 Simulator bấm check-in | Unity Play mode + console |
| 3:30 - 4:30 | AI đọc biển số + mở barrier + xe chạy đến V1-16 | Unity scene view |
| 4:30 - 5:30 | Check-out: popup chọn tiền 500k, 200k → AI detect đúng | Unity popup + AI response |
| 5:30 - 6:30 | Xem history FE hiển thị booking completed + tiền đã trả | History page |
| 6:30 - 7:00 | Cloudflare Tunnel — show demo live trên mobile | Mobile screenshot |

### Video kỹ thuật backup (mỗi module 1-2p)

- **Plate OCR demo** — feed 5 biển khác nhau, show response
- **Banknote demo** — feed 9 mệnh giá, show classify + confidence
- **Slot detection before/after car parked** — show AI detect realtime
- **Chatbot conversation** — 5 câu khó khác nhau
- **Full E2E** — gọi 10 API consecutive, show response OK

### Video hardware (nếu có ESP32 vật lý)

- Bấm nút physical → response qua serial monitor
- Servo quay khi backend trả success
- So sánh Unity Simulator với hardware thật → chứng minh simulator trust

## 9.2 Bằng chứng kỹ thuật khác

### Git history

```bash
git log --oneline | wc -l  # ~200 commits
git log --author="Minh" | grep -c "^commit"  # các commit của SV
```

Conventional commit messages → trace feature evolution.

### Logs

- AI service log: mỗi inference có timing + input + output
- Training log: `train_v2.log` 50 epoch với val metrics
- Backend log: request/response, error traceback

### Metrics

- **AI accuracy:** confusion matrix PNG (Task 7 eval)
- **Chatbot confidence:** query `chatbot_ai_metric_log`
- **Performance:** Prometheus/Grafana nếu có, else query log

### Test artifacts

- **E2E test scripts:** `test_e2e_full_flow.py`, `test_ai_full.py`, `test_chatbot_e2e.py`
- **Playwright reports:** `spotlove-ai/test-results/`
- **Audit artifacts:** `docs/notes/*-pipaudit.json`

### Screenshots

Chuẩn bị sẵn folder `docs/screenshots/`:
- Admin dashboard
- Booking flow (5 screenshot từ đầu đến cuối)
- Unity scene với AI annotated
- Chatbot chat
- History page

## 9.3 Trình bày Unity trong defense

### Slide flow đề xuất (5-7p)

1. **Slide 1-2 (60s):** Why Digital Twin?
   - Pain point: không có 50tr mua hardware demo
   - Unity cho phép full E2E test miễn phí
   - Visual hóa giúp hội đồng dễ hiểu

2. **Slide 3 (30s):** Kiến trúc Unity ↔ Backend
   ```
   Unity Play Mode
     ├─ ApiService.cs  → HTTP Gateway :8000
     ├─ VirtualCamera  → stream JPEG AI :8009
     ├─ WebSocket      ← realtime update :8006
     └─ ESP32Simulator → IoT endpoints
   ```

3. **Slide 4-5 (3 phút):** Live demo
   - Trái: Unity scene (xe chạy, barrier animate, slot đổi màu)
   - Phải: FE admin dashboard (real-time metrics update)

4. **Slide 6 (1 phút):** Showcase 3 feature chính
   - Spawn xe tự động (WebSocket trigger)
   - Barrier sync với backend response
   - AI nhận diện tiền trong popup

5. **Slide 7 (30s):** Metrics realtime
   - Admin dashboard số xe, doanh thu, slot trống
   - AI latency, accuracy

### Kịch bản nói mẫu

> *"Thưa hội đồng, để mô phỏng bãi giữ xe thực tế mà không cần đầu tư 50 triệu đồng phần cứng, em đã dựng Digital Twin bằng Unity 2022.3. Mỗi camera ảo trong Unity stream JPEG 5 FPS về AI service đúng y như camera IP thật — bước này biến Unity thành source data realtime cho AI nhận diện.*
>
> *Mỗi nút bấm ESP32 ảo gọi đúng endpoint như board ESP32 vật lý — nghĩa là code backend đã test với simulator thì khi chuyển sang hardware không cần sửa.*
>
> *Bây giờ em demo một chu trình hoàn chỉnh: đặt chỗ qua web → xe chạy vào bãi với AI đọc biển số → trả tiền bằng cash với AI nhận diện mệnh giá → ra khỏi bãi, tất cả 4 AI models hoạt động end-to-end..."*

### Chuẩn bị dự phòng

- **Offline mode:** chạy tất cả service local 30 phút trước, test full flow 3 lần → đảm bảo hoạt động
- **Backup video:** screen record full demo sẵn, phát khi live demo fail
- **Fallback slides:** screenshots thay Unity live nếu máy chết
- **Q&A prep:** chuẩn bị 20 câu hội đồng có thể hỏi + trả lời sẵn

---

# PHẦN 10 — KẾT LUẬN

## 10.1 Điểm mạnh toàn diện

**ParkSmart** là đồ án KLTN hiếm có tính **production-ready**:

### Technical breadth

- 10 microservices + 4 AI models + Unity simulator + FE PWA
- 5+ ngôn ngữ lập trình (Python, Go, C#, TypeScript, SQL)
- Tech stack đa dạng (Django, FastAPI, Gin, Unity, React, Redux, Docker, RabbitMQ, Redis, MySQL)

### Technical depth

- Mỗi AI model giải thích được **tại sao chọn thuật toán**, **so sánh với alternatives**, **cách tuning**
- Kiến trúc có **clear separation of concerns** (DDD, microservices)
- **Security best practices** (session, gateway secret, rate limit, HttpOnly cookie)

### Real-world readiness

- **Chi phí setup thực tế** ~50tr cho bãi 50 slot
- **ROI ~1.5 tháng** — khả thi kinh doanh
- **Scalable** — horizontal scale từng service theo load

### Innovation

- **AI nhận diện tiền mặt VN** — unique, chưa có bãi nào
- **Digital Twin Unity** — unique, tăng giá trị demo
- **Dual LLM backend** — flexibility production

## 10.2 Điểm yếu + mitigation

| Điểm yếu | Mitigation hiện tại | Hướng xử lý tiếp |
|---|---|---|
| Banknote v1 mới 89% | v2 design ≥99.5% | Task 5-11 roadmap |
| Chatbot time filter kém | Precision-at-accept threshold | Sprint S3: time-window API |
| Unity multi-floor NavMesh | Single floor hoạt động tốt | Sprint S4: bake multi-floor |
| Offline fallback không có | Backend always-on | Sprint S3: local queue |

## 10.3 Lesson learned

**Về AI:**
- "Deep learning không phải lúc nào cũng tốt hơn classical CV" — slot detection HSV > YOLO
- "Precision-first > accuracy" cho use case financial
- "Data augmentation có giới hạn" — Elastic/MixUp không phù hợp cho object có text cố định

**Về kiến trúc:**
- "Microservices cần event-driven" — sync call là anti-pattern cho 10 service
- "Gateway là bottleneck" — chọn công nghệ nhanh nhất (Go)
- "Redis là đa năng" — session, cache, pub/sub, queue broker

**Về engineering:**
- "Unity là sandbox tuyệt vời" cho demo + training data
- "Docker Compose đủ cho KLTN" — không cần Kubernetes
- "Cloudflare Tunnel thay VPS" — free tier đủ

---

**Kết thúc báo cáo kỹ thuật. Mọi chi tiết implementation có thể tra cứu trong code base + file docs/.**

**Contact:** Nguyễn Hải Minh — `dang.nguyenhai2k2@gmail.com`
