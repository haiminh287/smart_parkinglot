# Banknote Recognition v2 — Precision-First Design

**Date:** 2026-04-20
**Author:** ParkSmart AI
**Priority:** HIGH — tiền không được sai

## Goal

Upgrade bộ nhận diện mệnh giá tiền Việt Nam từ accuracy ~89% MobileNetV3 baseline lên **≥99% precision** với cơ chế **rejection** (model trả "không chắc" → user scan lại). Ưu tiên "thà từ chối còn hơn classify sai".

## Success Criteria

| Metric | Target |
|---|---|
| **Precision at accept** | ≥ 99.5% (sai < 1/200 lần accept) |
| **Accept rate** | 85-90% (10-15% reject — acceptable UX) |
| **Val accuracy top-1** | ≥ 98% |
| **Inference latency** | ≤ 200ms với TTA ×5 |
| **Class coverage** | 9 classes (1k/2k/5k/10k/20k/50k/100k/200k/500k) |

## Architecture

### Model

- **Backbone:** `torchvision.models.efficientnet_v2_s` (pretrained ImageNet)
- **Classifier head:** `Linear(1280, 9)` thay cho default ImageNet head
- **Rationale:** EfficientNetV2-S (22M params) có accuracy > MobileNetV3 (5.5M) mà vẫn fit GPU GTX 1650 4GB với batch 12 + fp16 AMP. Ensemble 3 models bị loại vì latency ×3.

### Training config

```python
epochs = 50
batch_size = 12
optimizer = AdamW(lr=3e-4, weight_decay=1e-4)
scheduler = CosineAnnealingLR(T_max=50)
loss = CrossEntropyLoss(label_smoothing=0.1)  # calibration
sampler = WeightedRandomSampler  # cân lớp 200k
class_weights = [1.0]*8 + [1.3]  # 200k nhân 1.3×
precision = fp16 (AMP) — tiết kiệm VRAM
early_stop_patience = 8 epochs
```

### Augmentation pipeline (train)

Dùng **albumentations** để nhanh + đa dạng transforms:

```python
A.Compose([
    A.RandomResizedCrop(224, scale=(0.8, 1.0), ratio=(0.9, 1.1)),
    A.HorizontalFlip(p=0.5),
    A.Rotate(limit=20, border_mode=cv2.BORDER_REFLECT, p=0.7),
    A.Perspective(scale=(0.02, 0.08), p=0.3),
    A.RandomBrightnessContrast(brightness=0.3, contrast=0.3, p=0.7),
    A.HueSaturationValue(hue=10, sat=20, val=15, p=0.4),
    A.CLAHE(clip_limit=2.0, p=0.2),
    A.OneOf([
        A.GaussianBlur(blur_limit=(3, 5), p=1.0),
        A.MotionBlur(blur_limit=7, p=1.0),
    ], p=0.3),
    A.GaussNoise(var_limit=(10, 40), p=0.3),
    A.CoarseDropout(max_holes=3, max_height=30, max_width=30, p=0.3),
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ToTensorV2(),
])
```

**Val augmentation:** chỉ resize 224 + normalize (deterministic, không random).

### Key augmentation design choices

- **KHÔNG dùng:** ElasticTransform, heavy RGBShift, MixUp — vì làm biến dạng số seri + mệnh giá in trên tờ → model học sai pattern. Tiền là object có số/chữ fixed, không biến dạng tự do như ảnh tự nhiên.
- **Rotation giới hạn ±20°** — người dùng cầm tiền không bao giờ lật ngược.
- **CoarseDropout** mô phỏng ngón tay che — nhưng max 3 holes để không che hết thông tin.

## Inference pipeline (precision-first)

### TTA (Test-Time Augmentation)

Predict 5 biến thể của cùng 1 ảnh → average softmax → stable hơn single prediction:

```python
tta_transforms = [
    original,
    horizontal_flip,
    rotate(+10),
    rotate(-10),
    brightness(1.1),
]

all_probs = []
for t in tta_transforms:
    img_t = t(image)
    logits = model(img_t)
    probs = softmax(logits)  # shape (9,)
    all_probs.append(probs)

avg_probs = mean(all_probs)
```

### Decision rules

```python
top1_idx = argmax(avg_probs)
top1_conf = avg_probs[top1_idx]
top2_conf = sorted(avg_probs)[-2]
margin = top1_conf - top2_conf

if top1_conf >= 0.92 and margin >= 0.25:
    return ACCEPT, denominations[top1_idx], top1_conf
elif top1_conf >= 0.80 and margin >= 0.40:
    return ACCEPT, denominations[top1_idx], top1_conf
else:
    return REJECT, None, top1_conf
```

| Top1 conf | Margin | Decision |
|---|---|---|
| ≥ 0.92 | ≥ 0.25 | ACCEPT |
| ≥ 0.80 | ≥ 0.40 | ACCEPT (kém tự tin nhưng class khác biệt rõ) |
| < 0.80 | any | REJECT — user scan lại |
| ≥ 0.80 | < 0.25 | REJECT — 2 class tranh nhau (50k vs 500k etc.) |

### Integration

- Sửa `app/ml/inference/cash_recognition.py` → thêm TTA + margin check, return `(status, denomination, confidence)`
- Pipeline `app/engine/pipeline.py` gọi — nếu `REJECT` trả `decision="low_confidence"` cho FE
- FE Unity cash popup hiện "Không nhận diện được tiền, vui lòng chụp lại"

## Dataset

### Current inventory

| Class | Front | Back | Total | So với TB (~1150) |
|---|---|---|---|---|
| 1000 | 604 | 604 | 1208 | ✓ |
| 2000 | ~600 | ~600 | 1208 | ✓ |
| 5000 | ~600 | ~600 | 1196 | ✓ |
| 10000 | ~550 | ~550 | 1092 | ✓ |
| 20000 | ~580 | ~580 | 1172 | ✓ |
| 50000 | 574 | 372 | 946 | Hơi ít back |
| 100000 | 578 | 588 | 1166 | ✓ |
| **200000** | **173** | **209** | **382** | **Chỉ 33%** |
| 500000 | 592 | 558 | 1150 | ✓ |

### Data strategy

1. **Re-extract 200k videos với fps cao hơn** (`--fps 30`) → target ~800 frames (gấp đôi hiện tại)
2. **WeightedRandomSampler + class_weights 1.3×** cho 200k — compensate imbalance mà không duplicate file
3. **Augmentation mạnh hơn** cho 200k batch — tăng diversity từ ít ảnh gốc

## Files

### New files

| Path | Purpose |
|---|---|
| `train_banknote_v2.py` | Training script EfficientNetV2-S + albumentations + AMP |
| `eval_banknote_v2.py` | Eval accuracy + confusion matrix + reliability plot |
| `app/ml/augmentations.py` | Reusable train/val transforms |

### Modified files

| Path | Change |
|---|---|
| `app/ml/inference/cash_recognition.py` | Thêm TTA + rejection logic |
| `app/engine/pipeline.py` | Thay threshold 0.60 → 0.80 + margin check |
| `.env` | Thêm `BANKNOTE_MODEL_PATH` trỏ sang weights mới |

## Workflow

```bash
# Step 1: Re-extract 200k với fps cao hơn
python extract_banknote_frames.py --denom 200000 --fps 30

# Step 2: Re-split 80/20 train/val
python split_dataset.py

# Step 3: Train (~5h GTX 1650)
python train_banknote_v2.py --epochs 50 --batch 12 --amp

# Step 4: Eval + confusion matrix
python eval_banknote_v2.py --weights ml/models/banknote_effv2s.pth

# Step 5: Swap model + restart AI service
# Set BANKNOTE_MODEL_PATH trong .env
# kill uvicorn + restart
```

## Sanity Tests

Trước khi deploy production:

- [ ] Val accuracy ≥ 98% trên top-1
- [ ] Confusion matrix: không có cặp class nào confuse > 2% (e.g. 50k→500k)
- [ ] Precision at accept ≥ 99.5%
- [ ] Reject rate 10-15%
- [ ] Inference time < 200ms (TTA ×5)
- [ ] Chạy thử 20 ảnh real từ ESP32 camera Unity simulator

## Rollback

- Giữ `ml/models/banknote_mobilenetv3.pth` làm backup
- Rollback: đổi `BANKNOTE_MODEL_PATH` về mobilenetv3 trong `.env`, restart uvicorn

## Out of scope

- Tiền nước ngoài (USD, CNY, EUR) — chỉ tập trung VND
- Tiền giả detection — đây là classifier mệnh giá, không phải forensic
- Recognition từ video liên tục (tracking) — chỉ single-frame

## References

- EfficientNetV2 paper: https://arxiv.org/abs/2104.00298
- Albumentations: https://albumentations.ai/
- Label smoothing + calibration: https://arxiv.org/abs/1906.02629
