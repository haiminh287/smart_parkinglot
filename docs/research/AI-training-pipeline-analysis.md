# Research Report: AI Banknote Training Pipeline & Classifier Analysis

**Date:** 2026-03-26 | **Type:** Codebase Analysis (Mixed)

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Có 2 model architecture khác nhau**: Training script (`train_and_evaluate.py`) dùng **MultiBranch EfficientNet-B3** (3 branches: visual + color + Gabor texture, 300x300, ~51MB). Production pipeline (`ai_classifier.py`) dùng **MobileNetV3-Large** (single-branch, 224x224, ~16MB). **Chúng KHÔNG tương thích.**
> 2. **EfficientNet-B3 MultiBranch đã được train và đạt 100% accuracy** trên val set (910 samples, 8 classes) — nhưng **KHÔNG ĐƯỢC dùng trong production pipeline** (`pipeline.py` load `banknote_mobilenetv3.pth`, không load `cash_recognition_best.pth`).
> 3. **LBP features đã có code** (`extract_lbp_features()`) trong `train_and_evaluate.py` nhưng **KHÔNG ĐƯỢC dùng** — chỉ Gabor + Color được feed vào model. LBP là cơ hội cải thiện texture recognition.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File | Mục đích | Relevance | Có thể tái dụng? |
|------|----------|-----------|-------------------|
| `train_and_evaluate.py` | Main training script (EfficientNet-B3 MultiBranch) | **HIGH** | Yes — architecture & feature extractors |
| `app/engine/ai_classifier.py` | Production AI fallback (MobileNetV3-Large) | **HIGH** | Yes — but architecture mismatch |
| `app/engine/pipeline.py` | Pipeline orchestrator | **HIGH** | Yes — integration point |
| `app/engine/color_classifier.py` | HSV color-based Stage 2A | **HIGH** | Yes — primary classifier |
| `train_mobilenetv3.py` | Separate MobileNetV3 training script | **MED** | Legacy/alternative |
| `app/ml/inference/cash_recognition.py` | Unified inference wrapper (supports v1+v2) | **HIGH** | Yes — already has v2 MultiBranch support |
| `app/ml/banknote/train_classifier.py` | EfficientNetV2-S training (bank-grade pipeline) | **MED** | Alternative pipeline |
| `test_banknote_camera.py` | Camera test using MultiBranch model | **MED** | Reference for inference code |
| `extract_banknote_frames.py` | Video → training frames extractor | **MED** | Dataset generation tool |

### 2.2 Two Completely Separate Architectures Exist

#### Architecture A: MultiBranch EfficientNet-B3 (Training Script)

**Source:** `train_and_evaluate.py` lines 218-292

```python
def build_model(n_classes: int, color_feat_dim: int, gabor_feat_dim: int):
    class MultiBranchBanknoteNet(nn.Module):
        def __init__(self):
            super().__init__()
            # Branch 1: Visual (EfficientNet-B3, 300x300)
            self.backbone = timm.create_model(
                "efficientnet_b3", pretrained=True, num_classes=0,
                global_pool="avg",
            )
            vis_dim = self.backbone.num_features  # 1536

            # Branch 2: Color histogram features (36-dim HSV)
            self.color_branch = nn.Sequential(
                nn.Linear(color_feat_dim, 128),
                nn.BatchNorm1d(128),
                nn.GELU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.GELU(),
            )

            # Branch 3: Gabor texture features (24-dim)
            self.texture_branch = nn.Sequential(
                nn.Linear(gabor_feat_dim, 128),
                nn.BatchNorm1d(128),
                nn.GELU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.GELU(),
            )

            # Fusion + Classifier
            fused_dim = vis_dim + 64 + 64  # 1536+64+64 = 1664
            self.classifier = nn.Sequential(
                nn.Dropout(0.40),
                nn.Linear(fused_dim, 512),
                nn.BatchNorm1d(512),
                nn.GELU(),
                nn.Dropout(0.25),
                nn.Linear(512, n_classes),
            )

        def forward(self, image, color_feat, gabor_feat):
            vis     = self.backbone(image)          # (B, 1536)
            color   = self.color_branch(color_feat)  # (B, 64)
            texture = self.texture_branch(gabor_feat) # (B, 64)
            fused   = torch.cat([vis, color, texture], dim=1)  # (B, 1664)
            return self.classifier(fused)
```

**Key properties:**
- Input: 300x300 images + 36-dim color vector + 24-dim Gabor vector
- Backbone: `timm` EfficientNet-B3 (ImageNet pretrained)
- Output features: 1536 (visual) + 64 (color) + 64 (texture) = **1664-dim fused**
- Final FC: 1664 → 512 → n_classes
- Saved as: `ml/models/cash_recognition_best.pth` (**51.47 MB**)

#### Architecture B: MobileNetV3-Large (Production)

**Source:** `app/engine/ai_classifier.py` lines 57-72

```python
model = models.mobilenet_v3_large(weights=None)
# Replace classifier head for 8 classes
model.classifier[-1] = torch.nn.Linear(
    model.classifier[-1].in_features, len(DENOMINATION_CLASSES)
)
state_dict = torch.load(model_path, map_location=self._device, weights_only=True)
model.load_state_dict(state_dict)
```

**Key properties:**
- Input: 224x224 images ONLY (no color/texture features)
- Backbone: torchvision MobileNetV3-Large
- Single-branch: raw image → CNN → logits
- Saved as: `ml/models/banknote_mobilenetv3.pth` (**16.26 MB**)

### 2.3 The Critical Gap

```
┌─────────────────────────────────────────────────────────────────────┐
│                      THE GAP                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TRAINING (train_and_evaluate.py)                                   │
│  ├─ EfficientNet-B3 MultiBranch                                     │
│  ├─ 3 inputs: image(300x300) + color(36d) + gabor(24d)             │
│  ├─ Output: cash_recognition_best.pth (51.47 MB)                   │
│  └─ Val accuracy: 100% (910 samples)                               │
│                                                                     │
│  PRODUCTION (pipeline.py → ai_classifier.py)                        │
│  ├─ MobileNetV3-Large                                               │
│  ├─ 1 input: image(224x224) ONLY                                   │
│  ├─ Loading: banknote_mobilenetv3.pth (16.26 MB)                   │
│  └─ No color/texture features used                                  │
│                                                                     │
│  BRIDGE EXISTS but NOT CONNECTED:                                   │
│  app/ml/inference/cash_recognition.py has CashRecognitionInference  │
│  that CAN load MultiBranch v2 — but pipeline.py uses ai_classifier │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.4 Pipeline Flow (Current Production)

**Source:** `app/engine/pipeline.py`

```
Stage 0: Preprocessing (white balance + quality gate)
    ↓
Stage 1: Detection (YOLOv8n → crop banknote)
    ↓
Stage 2A: Color Classification (HSV histogram)
    ├── SAFE group (100k, 200k) → threshold ≥ 0.75 → ACCEPT
    ├── DANGER group (20k, 50k, 10k, 500k) → threshold ≥ 0.90 → ACCEPT
    └── Below threshold → Stage 2B
    ↓
Stage 2B: AI Fallback (MobileNetV3 — single image input, 224x224)
    ├── confidence > 0.3 → ACCEPT
    └── else → LOW_CONFIDENCE
```

**Pipeline initializes AI classifier like this** (`pipeline.py` line 107):
```python
ai_path = os.path.join(model_dir, "banknote_mobilenetv3.pth")
self._ai_classifier = BanknoteAIClassifier(
    model_path=ai_path if os.path.exists(ai_path) else None
)
```

---

## 3. Training Configuration Details

### 3.1 Optimizer & Loss

**Source:** `train_and_evaluate.py` lines 433-443

```python
# Loss: CrossEntropy with class weights + label smoothing
criterion = nn.CrossEntropyLoss(weight=weights.to(device), label_smoothing=0.1)

# Phase 1 (epochs 0-14): Backbone frozen, train heads only
trainable = filter(lambda p: p.requires_grad, model.parameters())
optimizer = optim.AdamW(trainable, lr=3e-4, weight_decay=1e-4)
scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)

# Phase 2 (epoch 15+): Unfreeze backbone, lower LR
optimizer = optim.AdamW(model.parameters(), lr=3e-5, weight_decay=1e-4)  # lr * 0.1
scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)
```

### 3.2 Data Augmentation (Training Transforms)

**Source:** `train_and_evaluate.py` lines 311-325

```python
train_tf = transforms.Compose([
    transforms.Resize((img_size + 40, img_size + 40)),  # 340x340
    transforms.RandomCrop(img_size),                      # 300x300
    transforms.RandomHorizontalFlip(0.5),
    transforms.RandomVerticalFlip(0.3),
    transforms.RandomRotation(25),
    transforms.RandomPerspective(distortion_scale=0.2, p=0.4),
    transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.35),
    transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    transforms.RandomErasing(p=0.20, scale=(0.02, 0.15)),
])
```

**Note:** Augmentation is ONLY applied to the image tensor branch. Color/Gabor features are extracted from the **un-augmented** BGR image:
```python
# Load as BGR for OpenCV feature extraction (no augment for features)
bgr = cv2.imread(str(path))
bgr = cv2.resize(bgr, (300, 300))
color_feat = torch.tensor(extract_color_features(bgr), dtype=torch.float32)
gabor_feat = torch.tensor(extract_gabor_features(bgr), dtype=torch.float32)
```

### 3.3 Hyperparameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Epochs | 80 (max) | CLI default |
| Batch size | 24 | CLI default |
| Learning rate | 3e-4 (phase 1), 3e-5 (phase 2) | CLI + code |
| Image size | 300x300 | `IMG_SIZE = 300` |
| Early stopping patience | 15 epochs | CLI default |
| Backbone unfreeze epoch | 15 | CLI default |
| Label smoothing | 0.1 | Code |
| Weight decay | 1e-4 | Code |
| Dropout (fusion) | 0.40 | Model code |
| Dropout (classifier) | 0.25 | Model code |
| Dropout (branches) | 0.30 | Model code |

---

## 4. Feature Extractors

### 4.1 Gabor Texture Features (USED in model)

**Source:** `train_and_evaluate.py` lines 68-93

```python
def extract_gabor_features(image_bgr, n_orient=4, n_freq=3):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    gray = cv2.resize(gray, (128, 128))
    features = []
    freqs = [0.1, 0.3, 0.5]  # fine → coarse
    thetas = [i * np.pi / n_orient for i in range(n_orient)]  # 0°, 45°, 90°, 135°
    for freq in freqs:
        for theta in thetas:
            kernel = cv2.getGaborKernel((21, 21), sigma=4.0, theta=theta,
                                        lambd=1.0/freq, gamma=0.5, psi=0)
            resp = cv2.filter2D(gray, cv2.CV_32F, kernel)
            features.extend([float(resp.mean()), float(resp.std())])
    return np.array(features, dtype=np.float32)
    # Output: 4 orientations × 3 frequencies × 2 stats = 24-dim vector
```

### 4.2 HSV Color Features (USED in model)

**Source:** `train_and_evaluate.py` lines 96-115 (approx)

```python
def extract_color_features(image_bgr, bins=12):
    # HSV histogram with 12 bins per channel = 36-dim
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    features = []
    for ch in range(3):  # H, S, V channels
        hist = cv2.calcHist([hsv], [ch], None, [bins],
                            [0, 180] if ch == 0 else [0, 256])
        hist = hist.flatten() / (hist.sum() + 1e-8)
        features.extend(hist.tolist())
    return np.array(features, dtype=np.float32)
    # Output: 3 channels × 12 bins = 36-dim vector
```

### 4.3 LBP Features (EXISTS but NOT USED)

**Source:** `train_and_evaluate.py` lines 117-148

```python
def extract_lbp_features(image_bgr, n_points=24, radius=3):
    """Extract Local Binary Pattern features for fine texture recognition."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (128, 128))
    # Manual LBP implementation (no skimage dependency)
    lbp = np.zeros_like(gray, dtype=np.uint8)
    for i in range(1, gray.shape[0]-1):
        for j in range(1, gray.shape[1]-1):
            center = int(gray[i, j])
            code = 0
            neighbors = [
                gray[i-1, j-1], gray[i-1, j], gray[i-1, j+1],
                gray[i,   j+1],
                gray[i+1, j+1], gray[i+1, j], gray[i+1, j-1],
                gray[i,   j-1],
            ]
            for k, n in enumerate(neighbors):
                if int(n) >= center:
                    code |= (1 << k)
            lbp[i, j] = code % (n_points + 2)
    hist, _ = np.histogram(lbp.flatten(), bins=n_points+2, range=(0, n_points+2))
    hist = hist.astype(np.float32) / (hist.sum() + 1e-8)
    return hist
    # Output: 26-dim vector (n_points+2 = 26 bins)
```

**Why it's not used:** The `make_datasets()` function and `BanknoteDataset.__getitem__()` only extract `color_feat` and `gabor_feat`. LBP is defined but never called during training or inference.

---

## 5. Dataset Structure

### 5.1 Paths

```
ml/datasets/banknote_v1/
├── real/                    ← Source images (9 denominations incl. 200000)
│   ├── 1000/               ← ~600+ images per class
│   ├── 2000/
│   ├── 5000/
│   ├── 10000/
│   ├── 20000/
│   ├── 50000/
│   ├── 100000/
│   ├── 200000/             ← Exists here but EXCLUDED from training
│   └── 500000/
├── print_attack/            ← Attack data (for security training)
├── screen_attack/           ← Attack data (for security training)
├── train/                   ← Legacy split
├── val/                     ← Legacy split
└── metadata.csv
```

Training uses `split_v2/` (auto-generated 80/20 split from `real/`):
```
ml/models/split_v2/
├── train/
│   ├── 1000/    (~480+ images)
│   ├── 2000/    (~480+ images)
│   ├── ... (8 classes, NO 200000)
│   └── 500000/
└── val/
    ├── 1000/    (120 images)
    ├── 2000/    (120 images)
    ├── ... (8 classes)
    └── 500000/  (115 images)
```

### 5.2 Validation Set Per Class (from evaluation_results.json)

| Denomination | Val Samples | Accuracy | Notes |
|-------------|-------------|----------|-------|
| 1000 | 120 | 100% | Brown/tan |
| 2000 | 120 | 100% | Gray-blue |
| 5000 | 119 | 100% | Purple |
| 10000 | 109 | 100% | Red-brown |
| 20000 | 117 | 100% | Deep blue |
| 50000 | 94 | 100% | Pink/rose |
| 100000 | 116 | 100% | Green |
| 500000 | 115 | 100% | Blue-teal |
| **Total** | **910** | **100%** | |

### 5.3 Classes

- **Training/AI model:** 8 classes (1000, 2000, 5000, 10000, 20000, 50000, 100000, 500000)
- **Excluded:** 200000 — "no training data" comment in `ai_classifier.py`, handled by color classifier only
- **Color classifier:** 9 classes (includes 200000)

### 5.4 Data Source

Images extracted from videos using `extract_banknote_frames.py`:
- Input: `input_banknotes_video/` (front & back videos per denomination)
- Augmentation during extraction: horizontal flip, brightness jitter, slight rotation
- Quality filtering: blur score, brightness, contrast thresholds

---

## 6. Model Files

| File | Size | Architecture | Status |
|------|------|-------------|--------|
| `cash_recognition_best.pth` | 51.47 MB | EfficientNet-B3 MultiBranch v2 | Trained, 100% val acc, **NOT used in production pipeline** |
| `banknote_mobilenetv3.pth` | 16.26 MB | MobileNetV3-Large | **Used by production pipeline** |
| `yolo11n.pt` | 5.35 MB | YOLO11n (detection) | Used for Stage 1 |
| `class_mapping.json` | 473 B | Class index mapping | 8 classes |

### 6.1 Checkpoint Format (MultiBranch v2)

```python
checkpoint = {
    "model_state_dict": model.state_dict(),
    "class_to_idx": class_to_idx,
    "idx_to_class": idx_to_class,
    "num_classes": NUM_CLASSES,
    "color_feat_dim": color_dim,   # 36
    "gabor_feat_dim": gabor_dim,   # 24
    "img_size": IMG_SIZE,           # 300
    "arch": "efficientnet_b3_multibranch_v2",
    "epoch": epoch,
    "val_acc": val_acc,
}
```

---

## 7. Evaluation Results & Concerns

### 7.1 Perfect Accuracy Problem

The model achieves **100% accuracy on ALL classes from epoch 1**. This is a strong signal of:

1. **Dataset leakage**: Train and val may contain near-duplicate images (frames from the same video with minor differences)
2. **Overfitting to video source**: All images come from a small number of videos → model memorizes video-specific artifacts
3. **Insufficient diversity**: Real-world conditions (lighting, angles, wear, partial occlusion) are not represented
4. **Color classifier baseline is 13.25%**: `"color_accuracy": 0.1325` — color-only classification on same val set is terrible, which means the CNN is learning something, but 100% is suspicious

### 7.2 Training History Snapshot

```
Epoch 1:  train_loss=1.043, val_loss=0.528 → already 100% val_acc
Epoch 16: train_loss=0.508, val_loss=0.493 → still 100% (after unfreeze)
```

Loss decreasing but accuracy already perfect from epoch 1 — the val set is too easy.

---

## 8. ⚠️ Gotchas & Known Issues

- [x] **[CRITICAL]** Production pipeline loads `banknote_mobilenetv3.pth` (single-branch) while the best trained model is `cash_recognition_best.pth` (multi-branch). The two are architecturally incompatible.
- [x] **[CRITICAL]** 100% val accuracy is likely due to dataset leakage (video frame near-duplicates in train/val). Real-world performance will be lower.
- [x] **[WARNING]** `extract_lbp_features()` exists but is never used in training or inference — potential texture improvement left on the table.
- [x] **[WARNING]** `200000` denomination only handled by color classifier — no AI fallback coverage.
- [x] **[NOTE]** `app/ml/inference/cash_recognition.py` already has `CashRecognitionInference` class that can load and run the MultiBranch v2 model — but `pipeline.py` does not use it.
- [x] **[NOTE]** Feature extraction for color/Gabor runs on **un-augmented** images — color augmentation in transforms doesn't affect the color branch training signal.

---

## 9. Existing Texture/Pattern Features & What Could Be Added

### 9.1 Currently Used

| Feature | Dim | What It Captures | Limitations |
|---------|-----|-----------------|-------------|
| EfficientNet-B3 visual | 1536 | Patterns, numbers, layout, all learned features | Black-box; heavy model |
| HSV Color Histogram | 36 | Color distribution (H, S, V channels) | Sensitive to lighting; no spatial info |
| Gabor Filter Bank | 24 | Oriented texture energy at 3 frequencies | Only global mean+std; no spatial layout; limited orientations |

### 9.2 Available but Unused

| Feature | Dim | What It Could Capture | Implementation Status |
|---------|-----|----------------------|----------------------|
| LBP (Local Binary Pattern) | 26 | Fine micro-texture patterns (paper grain, polymer surface) | Code exists in `train_and_evaluate.py` line 117 |

### 9.3 Potential Additions for Texture/Pattern Improvement

| Feature | Approximate Dim | Captures | Complexity | Banknote Relevance |
|---------|----------------|----------|------------|-------------------|
| **LBP (already coded)** | 26 | Paper/polymer micro-texture | LOW — just wire it in | HIGH — polymer vs paper distinction |
| **Multi-scale LBP** | 78 (3 scales × 26) | Texture at different granularities | LOW | HIGH — guilloche at different scales |
| **Gabor spatial grid** | 96-192 | Regional texture differences (not just global) | MED | HIGH — different zones of banknotes have different patterns |
| **HOG (Histogram of Oriented Gradients)** | 128-256 | Edge orientation distribution, shape structure | LOW | MED — captures security thread, portrait silhouette |
| **Wavelet energy** | 12-24 | Multi-frequency texture decomposition | MED — needs `pywt` | HIGH — security features at specific frequency bands |
| **Edge density map** | 16-32 | Regional edge density (4x4 or 8x8 grid) | LOW | MED — distinguishes fine vs coarse printed areas |
| **GLCM (Gray-Level Co-occurrence Matrix)** | 20 | Texture contrast, correlation, energy, homogeneity | MED | MED — captures repetitive security patterns |
| **Fourier descriptor** | 16-32 | Frequency-domain texture signature | LOW | MED — guilloche pattern periodicity |
| **Color spatial layout** | 48-72 | WHERE colors appear (grid-based color histogram) | LOW | HIGH — front/back color zones differ per denomination |

### 9.4 Recommended Priority

1. **Wire in existing LBP** → adds 26-dim, zero new dependencies, captures micro-texture
2. **Gabor spatial grid** → instead of global mean/std, divide image into 4x4 grid and compute per-cell → captures regional pattern differences
3. **Color spatial layout** → divide image into 3x4 grid, compute color hist per region → captures WHERE colors appear, not just WHAT colors
4. **HOG features** → captures structural edge information that Gabor might miss
5. **Wavelet** → only if above isn't enough (adds dependency)

---

## 10. Checklist cho Implementer

### To fix the production gap:

- [ ] **Option A**: Replace `BanknoteAIClassifier` in `pipeline.py` to use `CashRecognitionInference` from `app/ml/inference/cash_recognition.py` which already supports MultiBranch v2
- [ ] **Option B**: Retrain MobileNetV3 to use the same multi-branch architecture (but defeats the purpose of having a lighter model)
- [ ] **Option C**: Update `ai_classifier.py` to load MultiBranch v2 architecture with color+Gabor features

### To add texture features:

- [ ] Add `lbp_feat_dim` parameter to `build_model()` — create a 4th branch (`self.lbp_branch`)
- [ ] Update `BanknoteDataset.__getitem__()` to extract and return LBP features
- [ ] Update `forward()` to accept 4 inputs: `(image, color_feat, gabor_feat, lbp_feat)`
- [ ] Update fused_dim: `1536 + 64 + 64 + 64 = 1728`
- [ ] Update all inference code (`test_banknote_camera.py`, `cash_recognition.py`) to extract and pass LBP
- [ ] Update checkpoint format to include `lbp_feat_dim`

### To fix dataset leakage:

- [ ] Split by VIDEO (not by frame) — all frames from one video go to either train OR val, never both
- [ ] Add images from different cameras, lighting, angles
- [ ] Test on truly unseen images (not from training videos)

### Env vars / Config:

- [ ] No new env vars needed for model changes
- [ ] Model path configured in `pipeline.py` `__init__` — path `model_dir` parameter

---

## 11. Nguồn

| # | File | Mô tả | Lines |
|---|------|-------|-------|
| 1 | `train_and_evaluate.py` | Main training script — MultiBranch EfficientNet-B3 | 1-730+ |
| 2 | `app/engine/ai_classifier.py` | Production MobileNetV3 classifier | 1-180 |
| 3 | `app/engine/pipeline.py` | Pipeline orchestrator | 1-310+ |
| 4 | `app/ml/inference/cash_recognition.py` | Unified inference (v1+v2 support) | 1-260+ |
| 5 | `ml/models/evaluation_results_v2.json` | Eval: 100% acc, 910 samples | — |
| 6 | `ml/models/class_mapping.json` | 8 classes mapping | — |
| 7 | `test_banknote_camera.py` | Camera test with MultiBranch | 1-450+ |
| 8 | `app/ml/banknote/train_classifier.py` | Alternative EfficientNetV2-S training | 1-180+ |
| 9 | `extract_banknote_frames.py` | Video → frame extraction pipeline | 1-540+ |
