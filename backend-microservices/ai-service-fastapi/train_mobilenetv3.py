#!/usr/bin/env python3
"""
Train MobileNetV3-Large for Vietnamese Banknote Classification.

Saves model.state_dict() as ml/models/banknote_mobilenetv3.pth
Compatible with app/engine/ai_classifier.py.

Class order: ["1000","2000","5000","10000","20000","50000","100000","500000"] (8 classes)
Note: 200000 excluded — no training data (only .gitkeep in real/200000/)

Usage:
    python train_mobilenetv3.py

Dataset: ml/models/split/train/  (8 denominations, ~3659 images)
         ml/models/split/val/    (8 denominations, ~917 images)
Output:  ml/models/banknote_mobilenetv3.pth
"""

import logging
import os
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────── #
BASE_DIR  = Path(__file__).resolve().parent
TRAIN_DIR = BASE_DIR / "ml" / "models" / "split" / "train"
VAL_DIR   = BASE_DIR / "ml" / "models" / "split" / "val"
OUTPUT    = BASE_DIR / "ml" / "models" / "banknote_mobilenetv3.pth"

# ── Class order MUST match ai_classifier.py DENOMINATION_CLASSES ── #
DENOMINATION_CLASSES = [
    "1000", "2000", "5000", "10000", "20000",
    "50000", "100000", "500000",
]
NUM_CLASSES  = len(DENOMINATION_CLASSES)
CLASS_TO_IDX = {c: i for i, c in enumerate(DENOMINATION_CLASSES)}

# ── Hyperparams ────────────────────────────────────────────── #
EPOCHS     = 25
BATCH_SIZE = 16
LR         = 1e-3
IMG_SIZE   = 224


def remap_targets(dataset, class_to_idx_target):
    """Remap ImageFolder's alphabetical indices → DENOMINATION_CLASSES order."""
    img_c2i = dataset.class_to_idx
    remap = {}
    for cls_name, folder_idx in img_c2i.items():
        if cls_name in class_to_idx_target:
            remap[folder_idx] = class_to_idx_target[cls_name]
        else:
            logger.warning(f"  Skipping unknown class '{cls_name}'")
    return remap


def apply_remap(dataset, remap):
    """Apply index remapping to dataset.samples and dataset.targets in-place."""
    new_samples, new_targets = [], []
    for path, old_idx in dataset.samples:
        if old_idx in remap:
            new_idx = remap[old_idx]
            new_samples.append((path, new_idx))
            new_targets.append(new_idx)
    dataset.samples = new_samples
    dataset.targets = new_targets
    return dataset


def main():
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, WeightedRandomSampler
    from torchvision import datasets, models, transforms

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device:    {device}")
    logger.info(f"Train dir: {TRAIN_DIR}")
    logger.info(f"Val dir:   {VAL_DIR}")
    logger.info(f"Output:    {OUTPUT}")
    logger.info(f"Classes:   {DENOMINATION_CLASSES}")

    # ── Transforms ──────────────────────────────────── #
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
        transforms.RandomCrop(IMG_SIZE),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.15),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    # ── Load datasets ────────────────────────────────── #
    train_ds = datasets.ImageFolder(str(TRAIN_DIR), transform=train_tf)
    val_ds   = datasets.ImageFolder(str(VAL_DIR),   transform=val_tf)

    remap_train = remap_targets(train_ds, CLASS_TO_IDX)
    remap_val   = remap_targets(val_ds,   CLASS_TO_IDX)

    train_ds = apply_remap(train_ds, remap_train)
    val_ds   = apply_remap(val_ds,   remap_val)

    logger.info(f"Train: {len(train_ds)} images, Val: {len(val_ds)} images")

    # Per-class counts
    per_class = {}
    for _, lbl in train_ds.samples:
        per_class[lbl] = per_class.get(lbl, 0) + 1
    for i, c in enumerate(DENOMINATION_CLASSES):
        logger.info(f"  [{i}] {c:>8}: {per_class.get(i, 0)} train images")

    # ── WeightedRandomSampler ─────────────────────────── #
    sample_weights = [1.0 / max(per_class.get(lbl, 1), 1) for _, lbl in train_ds.samples]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler, num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,   num_workers=0)

    # ── Model ─────────────────────────────────────────── #
    logger.info("Loading MobileNetV3-Large (ImageNet weights)...")
    model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.IMAGENET1K_V1)
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, NUM_CLASSES)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    # ── Training loop ──────────────────────────────────── #
    best_val_acc = 0.0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"\nStarting training — {EPOCHS} epochs on {device}...\n")

    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()

        # --- Train ---
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        for batch_idx, (inputs, labels) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            out  = model(inputs)
            loss = criterion(out, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item() * inputs.size(0)
            _, pred = out.max(1)
            total   += labels.size(0)
            correct += pred.eq(labels).sum().item()

            if (batch_idx + 1) % 100 == 0:
                logger.info(f"  E{epoch:02d} [{batch_idx+1}/{len(train_loader)}] "
                            f"avg_loss={total_loss/total:.4f}")

        train_acc = correct / total if total > 0 else 0.0

        # --- Validate ---
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                out = model(inputs)
                _, pred = out.max(1)
                val_total   += labels.size(0)
                val_correct += pred.eq(labels).sum().item()

        val_acc = val_correct / val_total if val_total > 0 else 0.0
        scheduler.step()

        elapsed = time.time() - t0
        logger.info(f"Epoch {epoch:02d}/{EPOCHS} [{elapsed:.0f}s]  "
                    f"train={train_acc:.4f}  val={val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), str(OUTPUT))
            logger.info(f"  ✅ Saved best → val_acc={val_acc:.4f}")

    logger.info(f"\n{'='*50}")
    logger.info(f"Training complete. Best val_acc={best_val_acc:.4f}")
    logger.info(f"Model saved: {OUTPUT}")

    # ── Sanity check ─────────────────────────────────── #
    logger.info("\nVerifying saved model loads correctly...")
    m2 = models.mobilenet_v3_large(weights=None)
    m2.classifier[-1] = nn.Linear(m2.classifier[-1].in_features, NUM_CLASSES)
    state = torch.load(str(OUTPUT), map_location="cpu", weights_only=True)
    m2.load_state_dict(state)
    m2.eval()
    logger.info(f"✅ Model verified — {NUM_CLASSES} classes, compatible with ai_classifier.py")


if __name__ == "__main__":
    main()
