#!/usr/bin/env python3
"""
Siamese Network + OneClass SVM — Bank-Grade Banknote Security.

Stage 2 & 3 of the bank-grade pipeline:
  2. Siamese Network for pair-wise banknote verification
  3. OneClass SVM for anomaly detection (fake banknote detection)

Author: ParkSmart AI Team
"""

import logging
import os
import pickle
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def train_siamese(
    data_dir: str,
    output_dir: str,
    epochs: int = 20,
    batch_size: int = 16,
    lr: float = 1e-4,
    embedding_dim: int = 128,
    margin: float = 1.0,
) -> None:
    """Train Siamese network for banknote pair verification.

    The Siamese network learns an embedding space where:
    - Same denomination → close embeddings (distance < threshold)
    - Different denomination → far embeddings (distance > threshold)

    This is used for secondary verification after the classifier.

    Args:
        data_dir: Root directory with per-denomination subdirs.
        output_dir: Directory to save model.
        epochs: Number of training epochs.
        batch_size: Batch size.
        lr: Learning rate.
        embedding_dim: Dimension of the embedding vector.
        margin: Contrastive loss margin.
    """
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    from torchvision import datasets, models, transforms
    from PIL import Image

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("🔗 Siamese training on: %s", device)
    os.makedirs(output_dir, exist_ok=True)

    img_size = 224

    transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(0.2, 0.2, 0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    # Load base dataset
    real_dir = os.path.join(data_dir, "real")
    if not os.path.exists(real_dir):
        real_dir = data_dir

    base_dataset = datasets.ImageFolder(real_dir, transform=transform)

    if len(base_dataset) < 10:
        logger.warning("Not enough images for Siamese training (%d). Skipping.", len(base_dataset))
        return

    class SiamesePairDataset(Dataset):
        """Generate positive and negative pairs for contrastive learning."""

        def __init__(self, image_folder: datasets.ImageFolder, n_pairs: int = 5000) -> None:
            self.dataset = image_folder
            self.n_pairs = n_pairs
            self.targets = np.array([s[1] for s in image_folder.samples])
            self.classes = list(set(self.targets))
            self.class_indices: dict[int, list[int]] = {}
            for idx, label in enumerate(self.targets):
                self.class_indices.setdefault(label, []).append(idx)

        def __len__(self) -> int:
            return self.n_pairs

        def __getitem__(self, idx: int) -> tuple:
            rng = np.random.default_rng(idx + int(time.time() * 1000) % 100000)

            if rng.random() < 0.5:
                # Positive pair (same class)
                label = rng.choice(self.classes)
                indices = self.class_indices[label]
                if len(indices) < 2:
                    i1, i2 = indices[0], indices[0]
                else:
                    i1, i2 = rng.choice(indices, size=2, replace=False)
                target = 1.0  # similar
            else:
                # Negative pair (different class)
                c1, c2 = rng.choice(self.classes, size=2, replace=False)
                i1 = rng.choice(self.class_indices[c1])
                i2 = rng.choice(self.class_indices[c2])
                target = 0.0  # dissimilar

            img1, _ = self.dataset[i1]
            img2, _ = self.dataset[i2]
            return img1, img2, torch.tensor(target, dtype=torch.float32)

    class SiameseNetwork(nn.Module):
        """Siamese network with shared ResNet18 backbone."""

        def __init__(self, embedding_dim: int = 128) -> None:
            super().__init__()
            backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
            self.features = nn.Sequential(*list(backbone.children())[:-1])
            self.fc = nn.Sequential(
                nn.Flatten(),
                nn.Linear(512, embedding_dim),
                nn.BatchNorm1d(embedding_dim),
            )

        def forward_one(self, x: torch.Tensor) -> torch.Tensor:
            """Extract embedding for one image."""
            features = self.features(x)
            return self.fc(features)

        def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> tuple:
            """Forward pass for pair."""
            e1 = self.forward_one(x1)
            e2 = self.forward_one(x2)
            return e1, e2

    class ContrastiveLoss(nn.Module):
        """Contrastive loss for Siamese network."""

        def __init__(self, margin: float = 1.0) -> None:
            super().__init__()
            self.margin = margin

        def forward(self, e1: torch.Tensor, e2: torch.Tensor, label: torch.Tensor) -> torch.Tensor:
            dist = torch.nn.functional.pairwise_distance(e1, e2)
            loss = label * dist.pow(2) + (1 - label) * torch.clamp(self.margin - dist, min=0).pow(2)
            return loss.mean()

    pair_dataset = SiamesePairDataset(base_dataset, n_pairs=min(5000, len(base_dataset) * 10))
    loader = DataLoader(pair_dataset, batch_size=batch_size, shuffle=True, num_workers=2)

    model = SiameseNetwork(embedding_dim=embedding_dim).to(device)
    criterion = ContrastiveLoss(margin=margin)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        n_batches = 0

        for img1, img2, target in loader:
            img1, img2, target = img1.to(device), img2.to(device), target.to(device)
            optimizer.zero_grad()
            e1, e2 = model(img1, img2)
            loss = criterion(e1, e2, target)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        avg_loss = total_loss / max(n_batches, 1)
        logger.info("Siamese epoch %d/%d — loss=%.4f", epoch + 1, epochs, avg_loss)

    save_path = os.path.join(output_dir, "siamese_network.pth")
    torch.save(model.state_dict(), save_path)
    logger.info("✅ Siamese network saved: %s", save_path)


def train_oneclass(
    data_dir: str,
    output_dir: str,
    epochs: int = 10,
    batch_size: int = 32,
    nu: float = 0.05,
) -> None:
    """Train OneClass SVM for fake banknote detection.

    Extracts features using pretrained ResNet18, then fits a OneClass SVM.
    The SVM learns the distribution of REAL banknotes, and flags
    anomalies (print attacks, screen attacks) as outliers.

    Args:
        data_dir: Root directory containing 'real/' subdirectory.
        output_dir: Directory to save the trained SVM model.
        epochs: Not used (SVM is non-iterative), kept for API compat.
        batch_size: Batch size for feature extraction.
        nu: OneClass SVM nu parameter (upper bound on fraction of outliers).
    """
    import torch
    from torchvision import datasets, models, transforms
    from torch.utils.data import DataLoader
    from sklearn.svm import OneClassSVM
    from sklearn.preprocessing import StandardScaler

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("🛡️ OneClass SVM training on: %s", device)
    os.makedirs(output_dir, exist_ok=True)

    img_size = 224
    transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    # Only use REAL banknotes for OneClass training
    real_dir = os.path.join(data_dir, "real")
    if not os.path.exists(real_dir):
        real_dir = data_dir

    dataset = datasets.ImageFolder(real_dir, transform=transform)
    if len(dataset) < 10:
        logger.warning("Not enough images for OneClass SVM (%d). Skipping.", len(dataset))
        return

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=2)

    # Feature extraction with ResNet18
    backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    backbone = torch.nn.Sequential(*list(backbone.children())[:-1])
    backbone.eval()
    backbone = backbone.to(device)

    features_list: list[np.ndarray] = []

    with torch.no_grad():
        for inputs, _ in loader:
            inputs = inputs.to(device)
            feats = backbone(inputs).squeeze(-1).squeeze(-1).cpu().numpy()
            features_list.append(feats)

    features = np.concatenate(features_list, axis=0)
    logger.info("Extracted features: shape=%s", features.shape)

    # Scale features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # Train OneClass SVM
    svm = OneClassSVM(kernel="rbf", nu=nu, gamma="scale")
    svm.fit(features_scaled)

    # Save model and scaler
    svm_path = os.path.join(output_dir, "oneclass_svm.pkl")
    scaler_path = os.path.join(output_dir, "oneclass_scaler.pkl")

    with open(svm_path, "wb") as f:
        pickle.dump(svm, f)
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    # Evaluate on training data
    predictions = svm.predict(features_scaled)
    n_inliers = np.sum(predictions == 1)
    n_outliers = np.sum(predictions == -1)
    logger.info(
        "✅ OneClass SVM: %d inliers, %d outliers (%.1f%% inlier rate)",
        n_inliers, n_outliers, 100 * n_inliers / len(predictions),
    )
    logger.info("Saved: %s, %s", svm_path, scaler_path)
