#!/usr/bin/env python3
"""
EfficientNetV2-S Classifier — Bank-Grade Banknote Recognition.

Stage 1 of the bank-grade pipeline:
  1. EfficientNetV2-S Classifier (this file)
  2. Siamese Network for pair verification
  3. OneClass SVM for anomaly/fake detection

Trains an EfficientNetV2-S model for 9 Vietnamese denominations.

Author: ParkSmart AI Team
"""

import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

DENOMINATION_CLASSES: list[str] = [
    "1000", "2000", "5000", "10000", "20000",
    "50000", "100000", "200000", "500000",
]

NUM_CLASSES = len(DENOMINATION_CLASSES)


def train(
    data_dir: str,
    output_dir: str,
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 3e-4,
    use_mlflow: bool = False,
    img_size: int = 300,
) -> None:
    """Train EfficientNetV2-S classifier for banknote denomination.

    Args:
        data_dir: Root directory with per-denomination subdirectories.
        output_dir: Directory to save model checkpoint.
        epochs: Number of training epochs.
        batch_size: Training batch size.
        lr: Initial learning rate.
        use_mlflow: Whether to log metrics to MLflow.
        img_size: Input image size for EfficientNetV2-S.
    """
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader
    from torchvision import datasets, models, transforms

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("🚀 EfficientNetV2-S training on: %s", device)

    os.makedirs(output_dir, exist_ok=True)

    # ── Transforms ──
    train_transforms = transforms.Compose([
        transforms.Resize((img_size + 32, img_size + 32)),
        transforms.RandomCrop(img_size),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(20),
        transforms.RandomPerspective(distortion_scale=0.3, p=0.4),
        transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.15),
        transforms.RandomGrayscale(p=0.1),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.2)),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    # ── Build train/val from single directory ──
    # Expects: data_dir/real/1000/, data_dir/real/2000/ etc.
    real_dir = os.path.join(data_dir, "real")
    if not os.path.exists(real_dir):
        real_dir = data_dir  # fallback if no "real" subdir

    full_dataset = datasets.ImageFolder(real_dir, transform=train_transforms)
    n_val = max(1, int(len(full_dataset) * 0.2))
    n_train = len(full_dataset) - n_val

    train_dataset, val_dataset_raw = torch.utils.data.random_split(
        full_dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42),
    )

    # Apply val transforms to val split
    val_dataset_raw.dataset = datasets.ImageFolder(real_dir, transform=val_transforms)

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=2, pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset_raw, batch_size=batch_size, shuffle=False,
        num_workers=2, pin_memory=True,
    )

    logger.info("Train: %d images, Val: %d images", n_train, n_val)

    # ── Model ──
    model = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.IMAGENET1K_V1)

    # Replace classifier
    in_features = model.classifier[-1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(in_features, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(0.2),
        nn.Linear(512, NUM_CLASSES),
    )
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_acc: float = 0.0

    for epoch in range(epochs):
        start = time.time()

        # Train
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            out = model(inputs)
            loss = criterion(out, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item() * inputs.size(0)
            _, pred = out.max(1)
            total += labels.size(0)
            correct += pred.eq(labels).sum().item()

        train_acc = correct / total if total > 0 else 0

        # Validate
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                out = model(inputs)
                _, pred = out.max(1)
                val_total += labels.size(0)
                val_correct += pred.eq(labels).sum().item()

        val_acc = val_correct / val_total if val_total > 0 else 0
        scheduler.step()

        elapsed = time.time() - start
        logger.info(
            "Epoch %d/%d [%.1fs] train_acc=%.4f val_acc=%.4f",
            epoch + 1, epochs, elapsed, train_acc, val_acc,
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_path = os.path.join(output_dir, "efficientnet_classifier.pth")
            torch.save({
                "model_state_dict": model.state_dict(),
                "class_to_idx": full_dataset.class_to_idx,
                "val_acc": val_acc,
                "epoch": epoch + 1,
            }, save_path)
            logger.info("💾 Saved classifier: val_acc=%.4f", val_acc)

    logger.info("✅ EfficientNetV2-S training complete. Best val_acc=%.4f", best_val_acc)
