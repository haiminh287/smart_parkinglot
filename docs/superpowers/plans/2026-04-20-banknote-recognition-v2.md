# Banknote Recognition v2 — AI Agent Handoff Plan

> **For AI Agent (GitHub Copilot / Cursor / etc.):** This plan is self-contained. Execute tasks sequentially. Each task has copy-paste ready code, exact commands, and verification steps. Check off `- [ ]` when done.

**Goal:** Nâng accuracy nhận diện mệnh giá tiền Việt Nam từ ~89% (MobileNetV3) lên **≥99% precision** với rejection logic, dùng **EfficientNetV2-S + albumentations + TTA**.

**Platform:** Windows 11, Git Bash shell, GPU GTX 1650 4GB, PyTorch 1.13+CUDA 11.6

**Working directory:** `C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/`

---

## Prerequisites

Before starting, verify these are true:

```bash
# 1. AI service venv exists
ls backend-microservices/ai-service-fastapi/venv/Scripts/python.exe

# 2. CUDA available
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe -c "import torch; print('CUDA:', torch.cuda.is_available(), 'Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"

# 3. Dataset videos present
ls backend-microservices/ai-service-fastapi/input_banknotes_video/*.mp4 | wc -l
# Expected: 18 (9 denominations × 2 sides)

# 4. Existing dataset
ls backend-microservices/ai-service-fastapi/ml/datasets/banknote_v1/real/1000/*.jpg | wc -l
# Expected: ~600-1200

# 5. Model dir writable
touch backend-microservices/ai-service-fastapi/ml/models/.write_test && rm backend-microservices/ai-service-fastapi/ml/models/.write_test && echo "OK"
```

Nếu bất kỳ check nào fail → STOP và báo user trước khi proceed.

---

## Spec Summary (Context)

- **Input:** Ảnh tờ tiền VN từ camera Unity simulator / ESP32 / FE upload
- **Output:** `{decision: "accept"|"reject", denomination: "50000"|null, confidence: 0.0-1.0}`
- **9 classes:** 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000 VND
- **Rejection logic:** Nếu model không đủ tự tin, trả REJECT thay vì đoán bừa — user scan lại
- **Target:** precision ≥99.5%, accept rate 85-90%, latency <200ms với TTA ×5

Design full: `docs/superpowers/specs/2026-04-20-banknote-recognition-v2-design.md`

---

## Task 1: Install dependencies

**Risk:** Low. Chỉ thêm packages vào venv, không đụng code.

**Files:**
- Modify: `backend-microservices/ai-service-fastapi/requirements.txt`

- [ ] **Step 1.1: Thêm vào `requirements.txt`**

Append 4 dòng này vào cuối file `backend-microservices/ai-service-fastapi/requirements.txt`:

```
albumentations==1.3.1
scikit-learn==1.3.2
matplotlib==3.7.3
seaborn==0.13.0
```

- [ ] **Step 1.2: Install**

```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe -m pip install albumentations==1.3.1 scikit-learn==1.3.2 matplotlib==3.7.3 seaborn==0.13.0
```

**Expected:** `Successfully installed albumentations-1.3.1 scikit-learn-1.3.2 matplotlib-3.7.3 seaborn-0.13.0`

**If error "No matching distribution":** Thử `albumentations==1.4.0` (Python 3.10 compat), các package khác giữ nguyên.

- [ ] **Step 1.3: Verify import**

```bash
venv/Scripts/python.exe -c "import albumentations as A; import sklearn; import matplotlib; import seaborn; print('albumentations', A.__version__); print('All imports OK')"
```

**Expected:** `albumentations 1.3.1` + `All imports OK`

- [ ] **Step 1.4: Commit**

```bash
cd ../.. # Back to repo root
git add backend-microservices/ai-service-fastapi/requirements.txt
git commit -m "chore(ai): add albumentations + sklearn + matplotlib cho banknote v2"
```

---

## Task 2: Re-extract 200k videos để tăng số frame

**Context:** 200k hiện có 382 frames (1/3 các lớp khác). Video `200000_front.mp4` + `200000_back.mp4` đã có sẵn, chỉ cần extract lại.

**Risk:** Low. Chỉ xoá + regenerate frames trong `ml/datasets/banknote_v1/real/200000/`.

- [ ] **Step 2.1: Check extract script có flag gì**

```bash
cd backend-microservices/ai-service-fastapi
grep -E "argparse|add_argument" extract_banknote_frames.py | head -10
```

Ghi lại các flags support (e.g. `--input`, `--fps`, `--denom`).

- [ ] **Step 2.2: Backup frames 200k hiện tại**

```bash
mkdir -p ml/datasets/banknote_v1/_backup_200k
cp ml/datasets/banknote_v1/real/200000/*.jpg ml/datasets/banknote_v1/_backup_200k/ 2>/dev/null || true
ls ml/datasets/banknote_v1/_backup_200k | wc -l
# Expected: ~382
```

- [ ] **Step 2.3: Xoá 200k hiện tại**

```bash
rm ml/datasets/banknote_v1/real/200000/*.jpg
ls ml/datasets/banknote_v1/real/200000/ | wc -l
# Expected: 0
```

- [ ] **Step 2.4: Re-run extract**

```bash
venv/Scripts/python.exe extract_banknote_frames.py
```

Script mặc định quét tất cả MP4 trong `input_banknotes_video/`. 200k sẽ được process trở lại.

- [ ] **Step 2.5: Verify frame count tăng**

```bash
ls ml/datasets/banknote_v1/real/200000/*.jpg | wc -l
# Target: ≥ 500 (gấp đôi 382)
```

**If < 500:** Video 200k ngắn hơn các lớp khác. Edit `extract_banknote_frames.py` tăng fps sampling (grep `FRAMES_PER_SECOND` hoặc `frame_step`, giảm `frame_step` 50%) → chạy lại step 2.3 + 2.4.

- [ ] **Step 2.6: Commit (no binary data, chỉ note)**

```bash
git commit --allow-empty -m "data(ai): re-extract 200k frames — $(ls ml/datasets/banknote_v1/real/200000/*.jpg | wc -l) frames"
```

---

## Task 3: Split dataset 80/20

**Files:**
- Create: `backend-microservices/ai-service-fastapi/split_dataset_v2.py`

- [ ] **Step 3.1: Tạo script split**

Tạo file mới `backend-microservices/ai-service-fastapi/split_dataset_v2.py`:

```python
"""Split dataset từ ml/datasets/banknote_v1/real/{class}/ → ml/models/split/{train,val}/{class}/.

80/20 random shuffle, seed=42 để reproducible.

Usage:
    python split_dataset_v2.py
"""
from __future__ import annotations

import random
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC = BASE / "ml" / "datasets" / "banknote_v1" / "real"
DST = BASE / "ml" / "models" / "split"
TRAIN_RATIO = 0.8
SEED = 42

CLASSES = ["1000", "2000", "5000", "10000", "20000", "50000", "100000", "200000", "500000"]


def main() -> None:
    rng = random.Random(SEED)
    for cls in CLASSES:
        src_dir = SRC / cls
        if not src_dir.exists():
            print(f"  SKIP {cls} — source dir missing")
            continue

        images = sorted(src_dir.glob("*.jpg"))
        if not images:
            print(f"  SKIP {cls} — no images")
            continue

        rng.shuffle(images)
        split_idx = int(len(images) * TRAIN_RATIO)

        for subset, imgs in [("train", images[:split_idx]), ("val", images[split_idx:])]:
            dst = DST / subset / cls
            if dst.exists():
                shutil.rmtree(dst)
            dst.mkdir(parents=True, exist_ok=True)
            for img in imgs:
                shutil.copy2(img, dst / img.name)

        print(f"  {cls}: {len(images)} total → train={split_idx} val={len(images)-split_idx}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3.2: Run**

```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe split_dataset_v2.py
```

**Expected output:** 9 dòng, mỗi dòng một class, train ≈ val×4.

- [ ] **Step 3.3: Verify counts**

```bash
for d in 1000 2000 5000 10000 20000 50000 100000 200000 500000; do
  t=$(ls "ml/models/split/train/$d"/*.jpg 2>/dev/null | wc -l)
  v=$(ls "ml/models/split/val/$d"/*.jpg 2>/dev/null | wc -l)
  echo "$d: train=$t val=$v"
done
```

**Success criteria:**
- Mỗi class train ≥ 200
- Mỗi class val ≥ 50
- Ratio train/val ≈ 4:1

- [ ] **Step 3.4: Commit**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/split_dataset_v2.py
git commit -m "feat(ai): add split_dataset_v2.py — 80:20 train/val với seed cố định"
```

---

## Task 4: Tạo augmentations module

**Files:**
- Create: `backend-microservices/ai-service-fastapi/app/ml/augmentations.py`

- [ ] **Step 4.1: Tạo module**

Tạo file mới `backend-microservices/ai-service-fastapi/app/ml/augmentations.py`:

```python
"""Albumentations transforms cho banknote classifier v2.

KHÔNG dùng ElasticTransform / MixUp / heavy RGBShift vì làm biến dạng
số seri + mệnh giá in trên tờ tiền → model học sai pattern.
"""
from __future__ import annotations

import albumentations as A
import cv2
from albumentations.pytorch import ToTensorV2

IMG_SIZE = 224

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_train_transform() -> A.Compose:
    """Training augmentation — mô phỏng điều kiện chụp thực tế."""
    return A.Compose([
        A.RandomResizedCrop(IMG_SIZE, IMG_SIZE, scale=(0.8, 1.0), ratio=(0.9, 1.1)),
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=20, border_mode=cv2.BORDER_REFLECT, p=0.7),
        A.Perspective(scale=(0.02, 0.08), p=0.3),
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.7),
        A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20, val_shift_limit=15, p=0.4),
        A.CLAHE(clip_limit=2.0, p=0.2),
        A.OneOf([
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
            A.MotionBlur(blur_limit=7, p=1.0),
        ], p=0.3),
        A.GaussNoise(var_limit=(10, 40), p=0.3),
        A.CoarseDropout(max_holes=3, max_height=30, max_width=30, p=0.3),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ])


def build_val_transform() -> A.Compose:
    """Val augmentation — deterministic, no random."""
    return A.Compose([
        A.Resize(IMG_SIZE, IMG_SIZE),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ])


def build_tta_transforms() -> list[A.Compose]:
    """TTA — 5 biến thể cho inference, average softmax."""
    base_norm = [
        A.Resize(IMG_SIZE, IMG_SIZE),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ]
    return [
        A.Compose(base_norm),
        A.Compose([A.HorizontalFlip(p=1.0), *base_norm]),
        A.Compose([A.Rotate(limit=(10, 10), p=1.0), *base_norm]),
        A.Compose([A.Rotate(limit=(-10, -10), p=1.0), *base_norm]),
        A.Compose([A.RandomBrightnessContrast(brightness_limit=(0.1, 0.1), contrast_limit=0, p=1.0), *base_norm]),
    ]
```

- [ ] **Step 4.2: Smoke test**

```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe -c "
from app.ml.augmentations import build_train_transform, build_val_transform, build_tta_transforms
import cv2, os
t_train = build_train_transform()
t_val = build_val_transform()
t_tta = build_tta_transforms()
print(f'train transforms: {len(t_train.transforms)}')
print(f'val transforms: {len(t_val.transforms)}')
print(f'tta pipelines: {len(t_tta)}')
# Real image test
sample_dir = 'ml/models/split/train/1000'
img = cv2.imread(os.path.join(sample_dir, os.listdir(sample_dir)[0]))
out = t_train(image=img)['image']
print(f'Train output shape: {out.shape}, dtype: {out.dtype}')
"
```

**Expected:**
```
train transforms: 11
val transforms: 3
tta pipelines: 5
Train output shape: torch.Size([3, 224, 224]), dtype: torch.float32
```

- [ ] **Step 4.3: Commit**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/app/ml/augmentations.py
git commit -m "feat(ai): add albumentations pipelines (train/val/tta) cho banknote v2"
```

---

## Task 5: Viết training script

**Files:**
- Create: `backend-microservices/ai-service-fastapi/train_banknote_v2.py`

- [ ] **Step 5.1: Tạo script**

Tạo file `backend-microservices/ai-service-fastapi/train_banknote_v2.py`:

```python
#!/usr/bin/env python3
"""Train EfficientNetV2-S cho banknote classifier v2 — precision-first.

Input:  ml/models/split/train/{class}/ + ml/models/split/val/{class}/
Output: ml/models/banknote_effv2s.pth (state_dict)
        ml/models/training_history_v2.json

Config:
    - Backbone: EfficientNetV2-S pretrained ImageNet
    - Optimizer: AdamW lr=3e-4 wd=1e-4
    - Scheduler: CosineAnnealingLR T_max=50
    - Loss: CrossEntropyLoss label_smoothing=0.1 + class_weights
    - Sampler: WeightedRandomSampler (cân class 200k)
    - Precision: fp16 AMP (tiết kiệm VRAM GTX 1650 4GB)
    - Early stop: patience=8 epoch không cải thiện val_loss

Usage:
    python train_banknote_v2.py
"""
from __future__ import annotations

import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.amp import GradScaler, autocast
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision.models import EfficientNet_V2_S_Weights, efficientnet_v2_s

from app.ml.augmentations import build_train_transform, build_val_transform

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────── #
BASE_DIR = Path(__file__).resolve().parent
TRAIN_DIR = BASE_DIR / "ml" / "models" / "split" / "train"
VAL_DIR = BASE_DIR / "ml" / "models" / "split" / "val"
OUTPUT = BASE_DIR / "ml" / "models" / "banknote_effv2s.pth"
HISTORY = BASE_DIR / "ml" / "models" / "training_history_v2.json"

DENOMINATIONS = ["1000", "2000", "5000", "10000", "20000", "50000", "100000", "200000", "500000"]
NUM_CLASSES = len(DENOMINATIONS)
CLASS_TO_IDX = {c: i for i, c in enumerate(DENOMINATIONS)}

# ── Hyperparams ────────────────────────────────────────────── #
EPOCHS = 50
BATCH_SIZE = 12
LR = 3e-4
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.1
EARLY_STOP_PATIENCE = 8
NUM_WORKERS = 2
SEED = 42
# 200k có index 7 trong DENOMINATIONS, weight 1.3× để bù class imbalance
CLASS_WEIGHTS = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.3, 1.0]


class BanknoteDataset(Dataset):
    """Folder-based dataset. Loads JPG với cv2 (BGR→RGB) để khớp albumentations."""

    def __init__(self, root: Path, transform: Any) -> None:
        self.samples: list[tuple[Path, int]] = []
        for cls_name, idx in CLASS_TO_IDX.items():
            cls_dir = root / cls_name
            if not cls_dir.exists():
                continue
            for img_path in cls_dir.glob("*.jpg"):
                self.samples.append((img_path, idx))
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        path, label = self.samples[i]
        img = cv2.imread(str(path))
        if img is None:
            raise RuntimeError(f"Cannot read {path}")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        out = self.transform(image=img)["image"]
        return out, label


def build_weighted_sampler(dataset: BanknoteDataset) -> WeightedRandomSampler:
    """Cân class: mỗi sample weight = (1/class_count) * CLASS_WEIGHTS[idx]."""
    counts = Counter(lbl for _, lbl in dataset.samples)
    weights = [
        (1.0 / counts[lbl]) * CLASS_WEIGHTS[lbl]
        for _, lbl in dataset.samples
    ]
    return WeightedRandomSampler(weights, num_samples=len(dataset), replacement=True)


def main() -> None:
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # ── Dataset + DataLoader ──
    train_ds = BanknoteDataset(TRAIN_DIR, build_train_transform())
    val_ds = BanknoteDataset(VAL_DIR, build_val_transform())
    logger.info("Train: %d samples, Val: %d samples", len(train_ds), len(val_ds))

    if len(train_ds) == 0 or len(val_ds) == 0:
        raise RuntimeError("Empty dataset! Chạy split_dataset_v2.py trước.")

    sampler = build_weighted_sampler(train_ds)
    train_loader = DataLoader(
        train_ds, batch_size=BATCH_SIZE, sampler=sampler,
        num_workers=NUM_WORKERS, pin_memory=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=BATCH_SIZE * 2, shuffle=False,
        num_workers=NUM_WORKERS, pin_memory=True,
    )

    # ── Model ──
    model = efficientnet_v2_s(weights=EfficientNet_V2_S_Weights.IMAGENET1K_V1)
    in_feats = model.classifier[1].in_features  # 1280
    model.classifier[1] = nn.Linear(in_feats, NUM_CLASSES)
    model = model.to(device)

    # ── Loss / Optimizer / Scheduler ──
    cls_w = torch.tensor(CLASS_WEIGHTS, dtype=torch.float32, device=device)
    criterion = nn.CrossEntropyLoss(weight=cls_w, label_smoothing=LABEL_SMOOTHING)
    optimizer = AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS)
    scaler = GradScaler("cuda")

    # ── Training loop ──
    best_val_loss = float("inf")
    patience_counter = 0
    history: dict[str, list[float]] = {
        "train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []
    }

    for epoch in range(1, EPOCHS + 1):
        t_start = time.time()

        # Train
        model.train()
        tr_loss_sum, tr_correct, tr_total = 0.0, 0, 0
        for imgs, labels in train_loader:
            imgs = imgs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad()
            with autocast("cuda"):
                out = model(imgs)
                loss = criterion(out, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            tr_loss_sum += loss.item() * imgs.size(0)
            tr_correct += (out.argmax(1) == labels).sum().item()
            tr_total += imgs.size(0)
        tr_loss = tr_loss_sum / tr_total
        tr_acc = tr_correct / tr_total

        # Val
        model.eval()
        val_loss_sum, val_correct, val_total = 0.0, 0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs = imgs.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)
                with autocast("cuda"):
                    out = model(imgs)
                    loss = criterion(out, labels)
                val_loss_sum += loss.item() * imgs.size(0)
                val_correct += (out.argmax(1) == labels).sum().item()
                val_total += imgs.size(0)
        val_loss = val_loss_sum / val_total
        val_acc = val_correct / val_total

        scheduler.step()
        history["train_loss"].append(tr_loss)
        history["train_acc"].append(tr_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        dt = time.time() - t_start
        logger.info(
            "Epoch %d/%d [%.0fs] train_loss=%.4f train_acc=%.4f val_loss=%.4f val_acc=%.4f",
            epoch, EPOCHS, dt, tr_loss, tr_acc, val_loss, val_acc,
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), OUTPUT)
            logger.info("  ✓ Saved best model (val_loss=%.4f)", val_loss)
        else:
            patience_counter += 1
            if patience_counter >= EARLY_STOP_PATIENCE:
                logger.info("Early stop at epoch %d (patience %d)", epoch, EARLY_STOP_PATIENCE)
                break

    HISTORY.write_text(json.dumps(history, indent=2))
    logger.info("Done. Best val_loss=%.4f, weights=%s", best_val_loss, OUTPUT)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5.2: Smoke test (1 epoch)**

Tạm set `EPOCHS = 1` trong file (sửa dòng `EPOCHS = 50` thành `EPOCHS = 1`), chạy:

```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe train_banknote_v2.py
```

**Expected (5-8 phút):**
- Log `Device: cuda`
- Log `Train: XXXX samples, Val: XXXX samples`
- Epoch 1 hoàn thành, val_acc > 0.3
- File `ml/models/banknote_effv2s.pth` được tạo (~80MB)

**If OOM:** Giảm `BATCH_SIZE = 12` → `BATCH_SIZE = 8` trong file.

- [ ] **Step 5.3: Restore `EPOCHS = 50`**

Sửa `EPOCHS = 1` trở lại `EPOCHS = 50`.

- [ ] **Step 5.4: Commit**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/train_banknote_v2.py
git commit -m "feat(ai): EfficientNetV2-S training script + AMP fp16 + weighted sampler"
```

---

## Task 6: Train model (4-5 giờ)

**Risk:** Long-running. Dùng `tee` để log ra file, có thể chạy qua đêm.

- [ ] **Step 6.1: Start training với log**

```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe train_banknote_v2.py 2>&1 | tee ml/models/train_v2.log
```

Hoặc chạy background + monitor:

```bash
nohup venv/Scripts/python.exe train_banknote_v2.py > ml/models/train_v2.log 2>&1 &
tail -f ml/models/train_v2.log
```

- [ ] **Step 6.2: Monitor progress**

Trong terminal khác:

```bash
tail -f backend-microservices/ai-service-fastapi/ml/models/train_v2.log | grep Epoch
```

**Healthy signals:**
- Epoch 1: val_acc ≈ 0.30-0.50
- Epoch 5: val_acc ≈ 0.80+
- Epoch 15: val_acc ≈ 0.95+
- Epoch 30-50: val_acc plateau ≈ 0.97-0.99

**Unhealthy signals → abort:**
- val_loss NaN → giảm LR xuống 1e-4
- val_acc không tăng sau 10 epoch → check dataset split
- OOM → giảm BATCH_SIZE

- [ ] **Step 6.3: Verify output khi xong**

```bash
ls -la backend-microservices/ai-service-fastapi/ml/models/banknote_effv2s.pth
ls -la backend-microservices/ai-service-fastapi/ml/models/training_history_v2.json
# Check best val_loss
grep "Saved best" backend-microservices/ai-service-fastapi/ml/models/train_v2.log | tail -5
```

**Success criteria:**
- `.pth` file ~80MB
- Last "Saved best" có val_loss < 0.15
- Training history JSON có ≥ 30 epoch entries

- [ ] **Step 6.4: Commit log + history (không commit weights)**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/ml/models/training_history_v2.json
git add backend-microservices/ai-service-fastapi/ml/models/train_v2.log
git commit -m "train(ai): banknote v2 training history + log ($(grep -c Epoch backend-microservices/ai-service-fastapi/ml/models/train_v2.log) epochs)"
```

Weights file `.pth` gitignored, không commit.

---

## Task 7: Evaluate model

**Files:**
- Create: `backend-microservices/ai-service-fastapi/eval_banknote_v2.py`

- [ ] **Step 7.1: Tạo eval script**

Tạo `backend-microservices/ai-service-fastapi/eval_banknote_v2.py`:

```python
#!/usr/bin/env python3
"""Evaluate banknote EfficientNetV2-S: accuracy + confusion matrix + precision-at-accept analysis."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader
from torchvision.models import efficientnet_v2_s

from app.ml.augmentations import build_val_transform
from train_banknote_v2 import DENOMINATIONS, NUM_CLASSES, BanknoteDataset

BASE_DIR = Path(__file__).resolve().parent
VAL_DIR = BASE_DIR / "ml" / "models" / "split" / "val"
WEIGHTS = BASE_DIR / "ml" / "models" / "banknote_effv2s.pth"
CM_PNG = BASE_DIR / "ml" / "models" / "confusion_matrix_v2.png"
REPORT_JSON = BASE_DIR / "ml" / "models" / "eval_report_v2.json"


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = efficientnet_v2_s(weights=None)
    in_feats = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_feats, NUM_CLASSES)
    model.load_state_dict(torch.load(WEIGHTS, map_location=device))
    model = model.to(device).eval()

    ds = BanknoteDataset(VAL_DIR, build_val_transform())
    loader = DataLoader(ds, batch_size=24, shuffle=False, num_workers=2, pin_memory=True)
    print(f"Val samples: {len(ds)}")

    all_preds: list[int] = []
    all_labels: list[int] = []
    all_probs: list[np.ndarray] = []

    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            all_preds.extend(probs.argmax(axis=1).tolist())
            all_labels.extend(labels.tolist())
            all_probs.extend(probs.tolist())

    acc = sum(p == l for p, l in zip(all_preds, all_labels)) / len(all_labels)
    print(f"\n== Overall top-1 accuracy: {acc*100:.2f}% ==")

    report = classification_report(
        all_labels, all_preds,
        labels=list(range(NUM_CLASSES)),
        target_names=DENOMINATIONS,
        output_dict=True, zero_division=0,
    )
    print("\n== Per-class metrics ==")
    print(classification_report(
        all_labels, all_preds,
        labels=list(range(NUM_CLASSES)),
        target_names=DENOMINATIONS, zero_division=0,
    ))

    cm = confusion_matrix(all_labels, all_preds, labels=list(range(NUM_CLASSES)))
    plt.figure(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=DENOMINATIONS, yticklabels=DENOMINATIONS)
    plt.xlabel("Predicted"); plt.ylabel("Actual"); plt.title("Banknote v2 — Confusion Matrix")
    plt.tight_layout()
    plt.savefig(CM_PNG, dpi=120)
    print(f"\n✓ Confusion matrix saved: {CM_PNG}")

    # Precision-at-accept với các (conf, margin) threshold
    print("\n== Precision-at-accept với (conf, margin) thresholds ==")
    probs_arr = np.array(all_probs)
    labels_arr = np.array(all_labels)
    preds_arr = probs_arr.argmax(axis=1)

    for conf_t, margin_t in [(0.80, 0.25), (0.85, 0.25), (0.92, 0.25), (0.92, 0.30), (0.95, 0.30)]:
        top1 = probs_arr.max(axis=1)
        sorted_probs = np.sort(probs_arr, axis=1)
        top2 = sorted_probs[:, -2]
        margin = top1 - top2
        accept_mask = (top1 >= conf_t) & (margin >= margin_t)
        n_accept = int(accept_mask.sum())
        if n_accept == 0:
            print(f"  conf≥{conf_t} margin≥{margin_t}: 0 accepts")
            continue
        correct = int((preds_arr[accept_mask] == labels_arr[accept_mask]).sum())
        precision = correct / n_accept
        accept_rate = n_accept / len(labels_arr)
        print(f"  conf≥{conf_t:.2f} margin≥{margin_t:.2f}: accept_rate={accept_rate*100:5.1f}%  precision={precision*100:6.2f}%")

    REPORT_JSON.write_text(json.dumps({
        "overall_accuracy": acc,
        "per_class": report,
        "confusion_matrix": cm.tolist(),
    }, indent=2))
    print(f"\n✓ Report saved: {REPORT_JSON}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7.2: Run eval**

```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe eval_banknote_v2.py
```

**Expected output:**
```
Val samples: ~1800
== Overall top-1 accuracy: 97-99% ==
(per-class report...)
✓ Confusion matrix saved
== Precision-at-accept với thresholds ==
  conf≥0.80 margin≥0.25: accept_rate=93.x%  precision=99.xx%
  conf≥0.92 margin≥0.25: accept_rate=85.x%  precision=99.5+%
```

**Decision point:** Chọn threshold có **precision ≥ 99.5%** và **accept_rate ≥ 80%**. Ghi giá trị `(conf_t, margin_t)` để dùng ở Task 8.

Ví dụ: chọn `(0.92, 0.25)` nếu precision 99.6% và accept 85%.

- [ ] **Step 7.3: Review confusion matrix visually**

Mở file `ml/models/confusion_matrix_v2.png` — verify đường chéo đậm, không có off-diagonal nào > 2%.

**If có class pair confuse > 2%** (e.g. 50k↔500k): Cần train thêm. Quay lại Task 6 với more epochs hoặc thêm augment cho cặp đó.

- [ ] **Step 7.4: Commit**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/eval_banknote_v2.py
git add backend-microservices/ai-service-fastapi/ml/models/eval_report_v2.json
git add backend-microservices/ai-service-fastapi/ml/models/confusion_matrix_v2.png
git commit -m "eval(ai): banknote v2 — accuracy + confusion matrix + precision-at-accept"
```

---

## Task 8: Update inference (TTA + rejection)

**Files:**
- Modify: `backend-microservices/ai-service-fastapi/app/ml/inference/cash_recognition.py`

**Context:** File hiện tại dùng MobileNetV3 arch + confidence threshold 0.6. Thay bằng EfficientNetV2-S + TTA + rejection rules.

- [ ] **Step 8.1: Backup + replace**

```bash
cd backend-microservices/ai-service-fastapi
cp app/ml/inference/cash_recognition.py app/ml/inference/cash_recognition_v1_backup.py
```

Thay thế **toàn bộ** nội dung `app/ml/inference/cash_recognition.py`:

```python
"""Banknote v2 inference — EfficientNetV2-S + TTA + precision-first rejection."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision.models import efficientnet_v2_s

from app.ml.augmentations import build_tta_transforms

logger = logging.getLogger(__name__)

DENOMINATIONS = ["1000", "2000", "5000", "10000", "20000", "50000", "100000", "200000", "500000"]
NUM_CLASSES = len(DENOMINATIONS)

# Rejection thresholds — update theo kết quả Task 7 eval output
# Nếu eval chọn (0.92, 0.25) thì set ACCEPT_HIGH_CONF=0.92 ACCEPT_HIGH_MARGIN=0.25
ACCEPT_HIGH_CONF = 0.92
ACCEPT_HIGH_MARGIN = 0.25
ACCEPT_LOW_CONF = 0.80
ACCEPT_LOW_MARGIN = 0.40


class CashResult(NamedTuple):
    decision: str  # "accept" | "reject"
    denomination: str | None
    confidence: float
    top1_conf: float
    margin: float


class CashRecognitionInference:
    """EfficientNetV2-S + TTA ×5 banknote classifier với precision-first rejection."""

    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model = efficientnet_v2_s(weights=None)
        in_feats = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_feats, NUM_CLASSES)
        model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model = model.to(self.device).eval()
        self.tta = build_tta_transforms()
        logger.info("Loaded banknote v2 (EfficientNetV2-S) from %s", self.model_path)

    def predict(self, image_bgr: np.ndarray) -> CashResult:
        """Predict với TTA ×5 + rejection rules."""
        img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        all_probs: list[np.ndarray] = []
        with torch.no_grad():
            for t in self.tta:
                tensor = t(image=img_rgb)["image"].unsqueeze(0).to(self.device)
                logits = self.model(tensor)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
                all_probs.append(probs)

        avg = np.mean(all_probs, axis=0)
        top1_idx = int(avg.argmax())
        top1_conf = float(avg[top1_idx])
        sorted_probs = np.sort(avg)
        top2_conf = float(sorted_probs[-2])
        margin = top1_conf - top2_conf

        if top1_conf >= ACCEPT_HIGH_CONF and margin >= ACCEPT_HIGH_MARGIN:
            return CashResult("accept", DENOMINATIONS[top1_idx], top1_conf, top1_conf, margin)
        if top1_conf >= ACCEPT_LOW_CONF and margin >= ACCEPT_LOW_MARGIN:
            return CashResult("accept", DENOMINATIONS[top1_idx], top1_conf, top1_conf, margin)
        return CashResult("reject", None, top1_conf, top1_conf, margin)
```

- [ ] **Step 8.2: Update thresholds từ Task 7 eval**

Nếu Task 7 chọn `(0.92, 0.25)` thì giữ nguyên. Nếu chọn khác (e.g. `(0.95, 0.30)`), edit dòng:

```python
ACCEPT_HIGH_CONF = 0.95
ACCEPT_HIGH_MARGIN = 0.30
```

- [ ] **Step 8.3: Smoke test**

```bash
venv/Scripts/python.exe -c "
from app.ml.inference.cash_recognition import CashRecognitionInference
import cv2, os
inf = CashRecognitionInference('ml/models/banknote_effv2s.pth')
for denom in ['1000', '50000', '200000', '500000']:
    sample_dir = f'ml/models/split/val/{denom}'
    img_file = sorted(os.listdir(sample_dir))[0]
    img = cv2.imread(os.path.join(sample_dir, img_file))
    r = inf.predict(img)
    status = '✓' if r.denomination == denom else '✗'
    print(f'{status} Expected={denom} Got={r.denomination} decision={r.decision} conf={r.confidence:.3f} margin={r.margin:.3f}')
"
```

**Expected:** All 4 rows have `✓` (correct prediction), decision=accept, conf > 0.90.

- [ ] **Step 8.4: Commit**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/app/ml/inference/cash_recognition.py
git add backend-microservices/ai-service-fastapi/app/ml/inference/cash_recognition_v1_backup.py
git commit -m "feat(ai): banknote inference v2 — EfficientNetV2-S + TTA ×5 + rejection"
```

---

## Task 9: Update pipeline để map CashResult → PipelineResult

**Files:**
- Modify: `backend-microservices/ai-service-fastapi/app/engine/pipeline.py`

- [ ] **Step 9.1: Đọc code hiện tại**

```bash
cd backend-microservices/ai-service-fastapi
grep -n "cash_recognition\|CashRecognition\|_ai_classify\|ai_fallback" app/engine/pipeline.py | head -20
```

Tìm đoạn gọi `cash_inference.predict(...)` hoặc `_ai_classify(...)`. Đọc 20 dòng xung quanh.

- [ ] **Step 9.2: Sửa return path**

Tìm đoạn tương tự:

```python
# OLD pattern:
cls_result = self.cash_inference.predict(image)
if cls_result.confidence > 0.6:
    return PipelineResult(
        decision=PipelineDecision.ACCEPT,
        denomination=cls_result.denomination,
        ...
    )
```

Thay bằng:

```python
# NEW pattern — trust CashResult.decision
cls_result = self.cash_inference.predict(image)
if cls_result.decision == "accept":
    return PipelineResult(
        decision=PipelineDecision.ACCEPT,
        denomination=cls_result.denomination,
        confidence=cls_result.confidence,
        method=ClassificationMethod.AI_FALLBACK,
        message=f"AI nhận diện: {int(cls_result.denomination):,} VND",
    )
else:
    return PipelineResult(
        decision=PipelineDecision.LOW_CONFIDENCE,
        denomination=None,
        confidence=cls_result.confidence,
        method=ClassificationMethod.AI_FALLBACK,
        message="Không đủ tự tin — vui lòng chụp lại ảnh rõ hơn",
    )
```

**Note:** Field names của `PipelineResult` có thể khác (e.g. `decision` → `status`). Đọc class definition trong cùng file để match đúng signature.

- [ ] **Step 9.3: Smoke test full pipeline**

```bash
venv/Scripts/python.exe -c "
from app.engine.pipeline import BanknoteRecognitionPipeline
import cv2, os
p = BanknoteRecognitionPipeline(model_dir='ml/models')
for denom in ['100000', '200000', '500000']:
    sample_dir = f'ml/models/split/val/{denom}'
    img = cv2.imread(os.path.join(sample_dir, sorted(os.listdir(sample_dir))[0]))
    r = p.process(img)
    print(f'Expected={denom} → decision={r.decision} denom={r.denomination} conf={r.confidence}')
"
```

**Expected:** Cả 3 lớp → decision=ACCEPT, denom khớp, conf > 0.90.

- [ ] **Step 9.4: Commit**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/app/engine/pipeline.py
git commit -m "feat(ai): pipeline dùng CashResult.decision thay vì hardcoded threshold"
```

---

## Task 10: Deploy — wire model path qua env

**Files:**
- Modify: `backend-microservices/.env`
- Modify: `backend-microservices/ai-service-fastapi/app/config.py`
- Modify: `backend-microservices/ai-service-fastapi/app/routers/detection.py`

- [ ] **Step 10.1: Thêm env var**

Edit `backend-microservices/.env`, thêm ở cuối:

```
BANKNOTE_MODEL_PATH=C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main/backend-microservices/ai-service-fastapi/ml/models/banknote_effv2s.pth
```

- [ ] **Step 10.2: Thêm field vào config**

Edit `backend-microservices/ai-service-fastapi/app/config.py`, thêm sau dòng `ML_MODELS_DIR`:

```python
BANKNOTE_MODEL_PATH: str = ""
```

- [ ] **Step 10.3: Sửa detection.py dùng env var**

Edit `backend-microservices/ai-service-fastapi/app/routers/detection.py`, tìm hàm `_get_cash_inference`:

```python
# OLD:
def _get_cash_inference():
    global _cash_inference
    if _cash_inference is None:
        from app.ml.inference.cash_recognition import CashRecognitionInference
        model_path = os.path.join(settings.ML_MODELS_DIR, "cash_recognition_best.pth")
        _cash_inference = CashRecognitionInference(model_path=model_path)
    return _cash_inference
```

Thay bằng:

```python
def _get_cash_inference():
    global _cash_inference
    if _cash_inference is None:
        from app.ml.inference.cash_recognition import CashRecognitionInference
        model_path = (
            settings.BANKNOTE_MODEL_PATH
            or os.path.join(settings.ML_MODELS_DIR, "banknote_effv2s.pth")
        )
        _cash_inference = CashRecognitionInference(model_path=model_path)
    return _cash_inference
```

- [ ] **Step 10.4: Kill old uvicorn + restart với env mới**

```bash
# Kill tất cả uvicorn đang chạy cho ai-service
powershell -Command "Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*uvicorn*app.main*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }"

# Wait port clear
sleep 3

# Start với env mới
cd backend-microservices/ai-service-fastapi
set -a && source ../.env && set +a
venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8009 > /tmp/ai.log 2>&1 &

# Wait 30s cho pre-warm
sleep 30

# Verify health
curl -sS http://localhost:8009/health/
```

**Expected:** `{"status":"healthy",...}`

- [ ] **Step 10.5: Verify model v2 loaded**

```bash
grep -i "Loaded banknote v2\|EfficientNetV2-S" /tmp/ai.log | head -3
```

**Expected:** `Loaded banknote v2 (EfficientNetV2-S) from ...banknote_effv2s.pth`

- [ ] **Step 10.6: End-to-end API test**

```bash
SAMPLE=$(ls backend-microservices/ai-service-fastapi/ml/models/split/val/500000/*.jpg | head -1)
curl -sS -m 15 -H "X-Gateway-Secret: gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE" -H "X-User-ID: system" \
  -F "image=@$SAMPLE" \
  "http://localhost:8009/ai/detect/banknote/?mode=full" | python -c "
import json,sys
d=json.load(sys.stdin)
print(f'decision={d.get(\"decision\")} denom={d.get(\"denomination\")} conf={d.get(\"confidence\"):.3f}')"
```

**Expected:** `decision=accept denom=500000 conf=0.9+`

- [ ] **Step 10.7: Commit**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/app/config.py
git add backend-microservices/ai-service-fastapi/app/routers/detection.py
# Không commit .env (gitignored)
git commit -m "feat(ai): deploy banknote v2 via BANKNOTE_MODEL_PATH env"
```

---

## Task 11: Final sanity test + rollback docs

- [ ] **Step 11.1: Test 30 ảnh random toàn dataset**

```bash
cd backend-microservices/ai-service-fastapi
venv/Scripts/python.exe -c "
from app.ml.inference.cash_recognition import CashRecognitionInference
import cv2, os, random
random.seed(42)
inf = CashRecognitionInference('ml/models/banknote_effv2s.pth')
val_dir = 'ml/models/split/val'
total, accept, correct_at_accept = 0, 0, 0
for cls in sorted(os.listdir(val_dir)):
    files = os.listdir(os.path.join(val_dir, cls))
    for f in random.sample(files, min(3, len(files))):
        img = cv2.imread(os.path.join(val_dir, cls, f))
        r = inf.predict(img)
        total += 1
        if r.decision == 'accept':
            accept += 1
            if r.denomination == cls:
                correct_at_accept += 1
accept_rate = accept / total * 100
precision = correct_at_accept / max(accept, 1) * 100
print(f'Total: {total}, Accept: {accept} ({accept_rate:.1f}%), Precision at accept: {precision:.2f}%')
"
```

**Acceptance criteria:**
- Accept rate: 80-95%
- Precision at accept: **≥ 99%**

**If precision < 99%:** Tăng threshold `ACCEPT_HIGH_CONF` trong `cash_recognition.py` từ 0.92 → 0.95 → retest.

- [ ] **Step 11.2: Benchmark inference time**

```bash
venv/Scripts/python.exe -c "
from app.ml.inference.cash_recognition import CashRecognitionInference
import cv2, time, os
inf = CashRecognitionInference('ml/models/banknote_effv2s.pth')
img_path = os.path.join('ml/models/split/val/100000', sorted(os.listdir('ml/models/split/val/100000'))[0])
img = cv2.imread(img_path)
for _ in range(3): inf.predict(img)  # warmup
t = time.time()
for _ in range(10): inf.predict(img)
dt = (time.time() - t) / 10 * 1000
print(f'Mean inference time (TTA ×5): {dt:.1f}ms')
"
```

**Expected:** < 200ms

- [ ] **Step 11.3: Tạo rollback docs**

Tạo file `backend-microservices/ai-service-fastapi/ml/models/README.md`:

```markdown
# Banknote Model History

## v2 (current) — EfficientNetV2-S
- Weights: `banknote_effv2s.pth`
- Architecture: EfficientNetV2-S (22M params)
- Training: 50 epochs max, AMP fp16, batch 12, albumentations
- 9 classes: 1k/2k/5k/10k/20k/50k/100k/200k/500k VND
- Inference: TTA ×5 + rejection (conf ≥ 0.92 AND margin ≥ 0.25)
- Expected: val accuracy ~98-99%, precision at accept ≥ 99.5%

## v1 (backup) — MobileNetV3-Large
- Weights: `banknote_mobilenetv3.pth` (giữ làm fallback)
- Accuracy: ~89%
- Inference code backup: `app/ml/inference/cash_recognition_v1_backup.py`

## Rollback to v1

```bash
# 1. Revert inference code
cp app/ml/inference/cash_recognition_v1_backup.py app/ml/inference/cash_recognition.py

# 2. Update env
# Edit .env: BANKNOTE_MODEL_PATH=.../banknote_mobilenetv3.pth

# 3. Restart uvicorn
# (see Task 10 Step 10.4)
```
```

- [ ] **Step 11.4: Final commit**

```bash
cd ../..
git add backend-microservices/ai-service-fastapi/ml/models/README.md
git commit -m "docs(ai): banknote v2 deployment success + rollback procedure"
```

---

## Summary — Tasks Completed

Khi xong:

- [x] Task 1: Install deps
- [x] Task 2: Re-extract 200k → ≥500 frames
- [x] Task 3: Split dataset 80/20
- [x] Task 4: Augmentations module
- [x] Task 5: Training script
- [x] Task 6: Train 50 epochs (~5h)
- [x] Task 7: Eval + confusion matrix + precision-at-accept
- [x] Task 8: TTA + rejection inference
- [x] Task 9: Wire pipeline
- [x] Task 10: Deploy via env
- [x] Task 11: Sanity test + rollback docs

**Success criteria (must all be true):**
- Val top-1 accuracy ≥ 98%
- Precision at accept ≥ 99.5%
- Accept rate 80-95% (10-20% reject)
- Inference latency < 200ms
- No confusion pair > 2% off-diagonal in confusion matrix
- AI service health OK sau deploy

**Rollback trigger:** Nếu bất kỳ criteria nào fail → rollback v1 per README.md

---

## Troubleshooting

### CUDA OOM
- Giảm `BATCH_SIZE` 12 → 8 trong `train_banknote_v2.py`
- Tắt các app khác đang dùng GPU (Chrome hw accel, games)

### val_loss NaN từ epoch 1
- Giảm `LR` 3e-4 → 1e-4
- Check ảnh có bị corrupt: `find ml/datasets/banknote_v1/real -name "*.jpg" -size 0`

### Training quá chậm (> 10 phút/epoch)
- Check `NUM_WORKERS` = 2 (không tăng vì Windows slower)
- Check GPU utilization: `nvidia-smi` — phải > 80%

### Confusion pair > 2%
- Cặp 50k↔500k: augment color jitter mạnh hơn (2 lớp này khác biệt chủ yếu ở màu)
- Cặp 10k↔100k: augment rotation nhẹ hơn (khác biệt ở số in)

### API return 500 sau deploy
- Check uvicorn log: `tail /tmp/ai.log`
- Nếu thấy "state_dict missing keys" → model architecture mismatch → check class PATH trong cash_recognition.py
