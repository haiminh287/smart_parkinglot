#!/usr/bin/env python3
"""
Cash Recognition Training Pipeline — ParkSmart AI.

Trains a ResNet50 model to classify Vietnamese banknote denominations.
Supports 9 denominations with data augmentation, learning rate scheduling,
and early stopping.

Dataset structure expected:
    train_dir/
        1000/
            img001.jpg
            img002.jpg
        2000/
            ...
        500000/
            ...

Usage:
    python -m app.ml.training.train_cash_recognition \\
        --train-dir ./ml/datasets/banknote_v1/real \\
        --val-dir ./ml/datasets/banknote_v1_val/real \\
        --output-dir ./ml/models \\
        --epochs 50 \\
        --batch-size 32

Author: ParkSmart AI Team
"""

import argparse
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# 9 Vietnamese banknote denominations
DENOMINATION_CLASSES: list[str] = [
    "1000", "2000", "5000", "10000", "20000",
    "50000", "100000", "200000", "500000",
]

NUM_CLASSES = len(DENOMINATION_CLASSES)


def split_dataset(
    source_dir: str,
    train_dir: str,
    val_dir: str,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> dict[str, int]:
    """Split a flat dataset into train/val directories.

    Args:
        source_dir: Root directory with per-denomination subdirs.
        train_dir: Output train directory.
        val_dir: Output validation directory.
        val_ratio: Fraction of images for validation.
        seed: Random seed for reproducibility.

    Returns:
        Dictionary with split statistics.
    """
    rng = np.random.default_rng(seed)
    stats: dict[str, int] = {"train": 0, "val": 0}

    for denom in DENOMINATION_CLASSES:
        src_path = Path(source_dir) / denom
        if not src_path.exists():
            logger.warning("Missing denomination folder: %s", src_path)
            continue

        images = sorted([
            f for f in src_path.iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
        ])

        if len(images) == 0:
            logger.warning("No images in %s", src_path)
            continue

        # Shuffle and split
        indices = rng.permutation(len(images))
        n_val = max(1, int(len(images) * val_ratio))
        val_indices = indices[:n_val]
        train_indices = indices[n_val:]

        # Copy files
        train_denom_dir = Path(train_dir) / denom
        val_denom_dir = Path(val_dir) / denom
        train_denom_dir.mkdir(parents=True, exist_ok=True)
        val_denom_dir.mkdir(parents=True, exist_ok=True)

        for idx in train_indices:
            shutil.copy2(images[idx], train_denom_dir / images[idx].name)
            stats["train"] += 1

        for idx in val_indices:
            shutil.copy2(images[idx], val_denom_dir / images[idx].name)
            stats["val"] += 1

        logger.info(
            "  %s: %d train, %d val",
            denom, len(train_indices), len(val_indices),
        )

    logger.info("Split complete: %d train, %d val", stats["train"], stats["val"])
    return stats


def train_cash_recognition(
    train_dir: str,
    val_dir: Optional[str] = None,
    output_dir: str = "./ml/models",
    epochs: int = 50,
    batch_size: int = 32,
    lr: float = 1e-4,
    patience: int = 10,
    img_size: int = 224,
    freeze_backbone: bool = True,
    unfreeze_at_epoch: int = 10,
) -> tuple[Any, dict[str, list[float]]]:
    """Train a ResNet50 cash recognition model.

    Uses transfer learning from ImageNet pretrained weights.
    Implements:
    - Data augmentation (rotation, flip, color jitter, perspective)
    - Learning rate scheduling (CosineAnnealing)
    - Early stopping with patience
    - Best model checkpoint saving

    Args:
        train_dir: Directory with training images (per-class subdirs).
        val_dir: Directory with validation images. If None, splits from train.
        output_dir: Directory to save trained model and metrics.
        epochs: Maximum training epochs.
        batch_size: Batch size for training.
        lr: Initial learning rate.
        patience: Early stopping patience.
        img_size: Input image size (square).
        freeze_backbone: Whether to freeze backbone initially.
        unfreeze_at_epoch: Epoch at which to unfreeze backbone.

    Returns:
        Tuple of (model, history dict with train/val loss and accuracy).
    """
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader
    from torchvision import datasets, models, transforms

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("🚀 Training on device: %s", device)

    os.makedirs(output_dir, exist_ok=True)

    # ── Auto-split if no val_dir ──
    if val_dir is None or not os.path.exists(val_dir):
        logger.info("No val_dir provided. Auto-splitting 80/20...")
        auto_train = os.path.join(output_dir, "_auto_split", "train")
        auto_val = os.path.join(output_dir, "_auto_split", "val")
        split_dataset(train_dir, auto_train, auto_val, val_ratio=0.2)
        train_dir = auto_train
        val_dir = auto_val

    # ── Data Augmentation ──
    train_transforms = transforms.Compose([
        transforms.Resize((img_size + 32, img_size + 32)),
        transforms.RandomCrop(img_size),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomRotation(15),
        transforms.RandomPerspective(distortion_scale=0.2, p=0.3),
        transforms.ColorJitter(
            brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1,
        ),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.15)),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])

    # ── Datasets ──
    train_dataset = datasets.ImageFolder(train_dir, transform=train_transforms)
    val_dataset = datasets.ImageFolder(val_dir, transform=val_transforms)

    # Verify class mapping matches expected
    logger.info("Class mapping: %s", train_dataset.class_to_idx)
    logger.info("Train: %d images, Val: %d images", len(train_dataset), len(val_dataset))

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=2, pin_memory=True, drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=2, pin_memory=True,
    )

    # ── Model: ResNet50 with transfer learning ──
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)

    # Replace final FC layer for our 9 classes
    num_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.4),
        nn.Linear(num_features, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(0.2),
        nn.Linear(512, NUM_CLASSES),
    )

    # Freeze backbone initially
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False
        for param in model.fc.parameters():
            param.requires_grad = True
        logger.info("🔒 Backbone frozen. Training classifier head only.")

    model = model.to(device)

    # ── Loss, Optimizer, Scheduler ──
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr, weight_decay=1e-4,
    )
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=10, T_mult=2,
    )

    # ── Training Loop ──
    history: dict[str, list[float]] = {
        "train_loss": [],
        "val_loss": [],
        "train_acc": [],
        "val_acc": [],
        "lr": [],
    }

    best_val_acc: float = 0.0
    best_val_loss: float = float("inf")
    patience_counter: int = 0
    best_model_path = os.path.join(output_dir, "cash_recognition_best.pth")

    for epoch in range(epochs):
        start_time = time.time()

        # Unfreeze backbone at specified epoch
        if freeze_backbone and epoch == unfreeze_at_epoch:
            logger.info("🔓 Unfreezing backbone at epoch %d", epoch)
            for param in model.parameters():
                param.requires_grad = True
            # Reset optimizer for all parameters
            optimizer = optim.AdamW(
                model.parameters(), lr=lr * 0.1, weight_decay=1e-4,
            )
            scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
                optimizer, T_0=10, T_mult=2,
            )

        # ── Train phase ──
        model.train()
        running_loss: float = 0.0
        correct: int = 0
        total: int = 0

        for batch_idx, (inputs, labels) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        train_loss = running_loss / total
        train_acc = correct / total

        # ── Validation phase ──
        model.eval()
        val_running_loss: float = 0.0
        val_correct: int = 0
        val_total: int = 0

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)

                val_running_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

        val_loss = val_running_loss / val_total if val_total > 0 else float("inf")
        val_acc = val_correct / val_total if val_total > 0 else 0.0

        # Step scheduler
        scheduler.step()
        current_lr = optimizer.param_groups[0]["lr"]

        # Record history
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)
        history["lr"].append(current_lr)

        elapsed = time.time() - start_time

        logger.info(
            "Epoch %d/%d [%.1fs] — "
            "Train: loss=%.4f acc=%.4f | "
            "Val: loss=%.4f acc=%.4f | "
            "LR=%.6f",
            epoch + 1, epochs, elapsed,
            train_loss, train_acc,
            val_loss, val_acc,
            current_lr,
        )

        # ── Save best model ──
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_val_loss = val_loss
            patience_counter = 0

            torch.save({
                "epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_acc": val_acc,
                "val_loss": val_loss,
                "class_to_idx": train_dataset.class_to_idx,
                "classes": DENOMINATION_CLASSES,
            }, best_model_path)

            logger.info("💾 Saved best model: val_acc=%.4f", val_acc)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(
                    "⏹️ Early stopping at epoch %d (patience=%d)",
                    epoch + 1, patience,
                )
                break

    # ── Save final model and metadata ──
    final_model_path = os.path.join(output_dir, "cash_recognition_final.pth")
    torch.save(model.state_dict(), final_model_path)

    # Save training history
    history_path = os.path.join(output_dir, "training_history.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    # Save class mapping
    mapping_path = os.path.join(output_dir, "class_mapping.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump({
            "class_to_idx": train_dataset.class_to_idx,
            "idx_to_class": {v: k for k, v in train_dataset.class_to_idx.items()},
            "classes": DENOMINATION_CLASSES,
        }, f, indent=2)

    logger.info("=" * 60)
    logger.info("✅ TRAINING COMPLETE")
    logger.info("  Best val_acc: %.4f | Best val_loss: %.4f", best_val_acc, best_val_loss)
    logger.info("  Best model: %s", best_model_path)
    logger.info("  Final model: %s", final_model_path)
    logger.info("  History: %s", history_path)
    logger.info("  Class mapping: %s", mapping_path)
    logger.info("=" * 60)

    return model, history


def main() -> None:
    """CLI entry point for cash recognition training."""
    parser = argparse.ArgumentParser(
        description="ParkSmart AI — Cash Recognition Model Training",
    )
    parser.add_argument(
        "--train-dir", required=True,
        help="Directory with training images (per-class subdirs)",
    )
    parser.add_argument(
        "--val-dir", default=None,
        help="Directory with validation images. Auto-splits if not provided.",
    )
    parser.add_argument(
        "--output-dir", default="./ml/models",
        help="Directory to save model checkpoints (default: ./ml/models)",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument(
        "--no-freeze", action="store_true",
        help="Don't freeze backbone (train all layers from start)",
    )
    parser.add_argument(
        "--unfreeze-at", type=int, default=10,
        help="Epoch to unfreeze backbone (default: 10)",
    )
    parser.add_argument(
        "--split-only", action="store_true",
        help="Only split dataset, don't train",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.split_only:
        auto_train = os.path.join(args.output_dir, "split", "train")
        auto_val = os.path.join(args.output_dir, "split", "val")
        split_dataset(args.train_dir, auto_train, auto_val)
        return

    train_cash_recognition(
        train_dir=args.train_dir,
        val_dir=args.val_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
        img_size=args.img_size,
        freeze_backbone=not args.no_freeze,
        unfreeze_at_epoch=args.unfreeze_at,
    )


if __name__ == "__main__":
    main()
