#!/usr/bin/env python3
"""Train EfficientNetV2-S cho banknote classifier v2 - precision-first.

Input:  ml/models/split/train/{class}/ + ml/models/split/val/{class}/
Output: ml/models/banknote_effv2s.pth (state_dict)
        ml/models/training_history_v2.json

Config:
    - Backbone: EfficientNetV2-S pretrained ImageNet
    - Optimizer: AdamW lr=3e-4 wd=1e-4
    - Scheduler: CosineAnnealingLR T_max=50
    - Loss: CrossEntropyLoss label_smoothing=0.1 + class_weights
    - Sampler: WeightedRandomSampler (can class 200k)
    - Precision: fp16 AMP (tiet kiem VRAM GTX 1650 4GB)
    - Early stop: patience=8 epoch khong cai thien val_loss

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
from app.ml.augmentations import build_train_transform, build_val_transform
from torch.cuda.amp import GradScaler, autocast
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision.models import EfficientNet_V2_S_Weights, efficientnet_v2_s

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# -- Paths ---------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent
TRAIN_DIR = BASE_DIR / "ml" / "models" / "split" / "train"
VAL_DIR = BASE_DIR / "ml" / "models" / "split" / "val"
OUTPUT = BASE_DIR / "ml" / "models" / "banknote_effv2s.pth"
HISTORY = BASE_DIR / "ml" / "models" / "training_history_v2.json"

DENOMINATIONS = [
    "1000",
    "2000",
    "5000",
    "10000",
    "20000",
    "50000",
    "100000",
    "200000",
    "500000",
]
NUM_CLASSES = len(DENOMINATIONS)
CLASS_TO_IDX = {c: i for i, c in enumerate(DENOMINATIONS)}

# -- Hyperparams --------------------------------------------- #
EPOCHS_OLD = 50  # legacy
BATCH_SIZE = 6  # fp32 on GTX 1650 4GB (AMP unstable với torch 1.13 cu116)
ACCUM_STEPS = 1  # no accumulation
EPOCHS = 25  # bớt từ 50 xuống 25 — đủ hội tụ + còn early stop patience 5
LR = 1e-4  # giảm từ 3e-4 → 1e-4 tránh NaN với fp16 AMP + weighted loss
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.1
EARLY_STOP_PATIENCE = 5  # giảm xuống 5 phù hợp với 25 epochs
# Windows + PyTorch CUDA dễ gặp WinError 1455 khi worker spawn/import torch.
# Dùng 0 worker để ổn định huấn luyện trong môi trường hiện tại.
NUM_WORKERS = 0
SEED = 42
# 200k co index 7 trong DENOMINATIONS, weight 1.3x de bu class imbalance
CLASS_WEIGHTS = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.3, 1.0]


class BanknoteDataset(Dataset):
    """Folder-based dataset. Loads JPG voi cv2 (BGR->RGB) de khop albumentations."""

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
    """Can class: moi sample weight = (1/class_count) * CLASS_WEIGHTS[idx]."""
    counts = Counter(lbl for _, lbl in dataset.samples)
    weights = [(1.0 / counts[lbl]) * CLASS_WEIGHTS[lbl] for _, lbl in dataset.samples]
    return WeightedRandomSampler(weights, num_samples=len(dataset), replacement=True)


def main() -> None:
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # -- Dataset + DataLoader --
    train_ds = BanknoteDataset(TRAIN_DIR, build_train_transform())
    val_ds = BanknoteDataset(VAL_DIR, build_val_transform())
    logger.info("Train: %d samples, Val: %d samples", len(train_ds), len(val_ds))

    if len(train_ds) == 0 or len(val_ds) == 0:
        raise RuntimeError("Empty dataset! Chay split_dataset_v2.py truoc.")

    sampler = build_weighted_sampler(train_ds)
    use_pin_memory = device.type == "cuda"

    train_loader = DataLoader(
        train_ds,
        batch_size=BATCH_SIZE,
        sampler=sampler,
        num_workers=NUM_WORKERS,
        pin_memory=use_pin_memory,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=BATCH_SIZE * 2,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=use_pin_memory,
    )

    # -- Model --
    model = efficientnet_v2_s(weights=EfficientNet_V2_S_Weights.IMAGENET1K_V1)
    in_feats = model.classifier[1].in_features  # 1280
    model.classifier[1] = nn.Linear(in_feats, NUM_CLASSES)
    model = model.to(device)

    # -- Loss / Optimizer / Scheduler --
    # fp16 AMP có thể NaN với weighted loss + label_smoothing → dùng CE thuần,
    # class imbalance đã handle bằng WeightedRandomSampler
    criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
    optimizer = AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY, eps=1e-6)
    scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS)

    # -- Training loop --
    best_val_loss = float("inf")
    patience_counter = 0
    history: dict[str, list[float]] = {
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": [],
    }

    for epoch in range(1, EPOCHS + 1):
        t_start = time.time()

        # Train — fp32 (AMP unstable với torch 1.13 + GTX 1650)
        model.train()
        tr_loss_sum, tr_correct, tr_total = 0.0, 0, 0
        for step, (imgs, labels) in enumerate(train_loader):
            imgs = imgs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            tr_loss_sum += loss.item() * imgs.size(0)
            tr_correct += (out.argmax(1) == labels).sum().item()
            tr_total += imgs.size(0)
            if (step + 1) % 200 == 0:
                logger.info("  batch %d/%d loss=%.4f", step + 1, len(train_loader), loss.item())
        tr_loss = tr_loss_sum / tr_total if tr_total > 0 else float("nan")
        tr_acc = tr_correct / tr_total if tr_total > 0 else 0.0

        # Val
        model.eval()
        val_loss_sum, val_correct, val_total = 0.0, 0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs = imgs.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)
                out = model(imgs)
                loss = criterion(out, labels)
                val_loss_sum += loss.item() * imgs.size(0)
                val_correct += (out.argmax(1) == labels).sum().item()
                val_total += imgs.size(0)
        val_loss = val_loss_sum / val_total if val_total > 0 else float("nan")
        val_acc = val_correct / val_total if val_total > 0 else 0.0

        scheduler.step()
        history["train_loss"].append(tr_loss)
        history["train_acc"].append(tr_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        dt = time.time() - t_start
        logger.info(
            "Epoch %d/%d [%.0fs] train_loss=%.4f train_acc=%.4f val_loss=%.4f val_acc=%.4f",
            epoch,
            EPOCHS,
            dt,
            tr_loss,
            tr_acc,
            val_loss,
            val_acc,
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), OUTPUT)
            logger.info("  Saved best model (val_loss=%.4f)", val_loss)
        else:
            patience_counter += 1
            if patience_counter >= EARLY_STOP_PATIENCE:
                logger.info(
                    "Early stop at epoch %d (patience %d)", epoch, EARLY_STOP_PATIENCE
                )
                break

    HISTORY.write_text(json.dumps(history, indent=2))
    logger.info("Done. Best val_loss=%.4f, weights=%s", best_val_loss, OUTPUT)


if __name__ == "__main__":
    main()
