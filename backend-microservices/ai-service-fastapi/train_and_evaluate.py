#!/usr/bin/env python3
"""
ParkSmart AI - Multi-Feature Banknote Recognition Training v2.

Architecture: EfficientNet-B3 (300x300) + Color Branch + Texture Branch
Features learned:
  1. HOA VAN  - Patterns via EfficientNet deep features + Gabor textures
  2. SO IN    - Numbers printed via high-res 300x300 details
  3. BO CUC   - Layout/composition via global average + spatial pooling
  4. MAU SAC  - HSV color histogram branch (36 bins)
  5. CHI TIET - Denomination-specific features fused from all branches

Usage:
    python train_and_evaluate.py
    python train_and_evaluate.py --epochs 80 --batch-size 24
    python train_and_evaluate.py --eval-only
    python train_and_evaluate.py --enhanced --epochs 60 --batch-size 16
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

BASE_DIR    = Path(__file__).parent
DATASET_DIR = BASE_DIR / "ml" / "datasets" / "banknote_v1" / "real"
OUTPUT_DIR  = BASE_DIR / "ml" / "models"
SPLIT_DIR   = OUTPUT_DIR / "split_v2"

ACTIVE_CLASSES = ["1000","2000","5000","10000","20000","50000","100000","500000"]
NUM_CLASSES    = len(ACTIVE_CLASSES)
IMG_SIZE       = 300   # High enough to read printed numbers + patterns

# Denomination-specific visual characteristics (for reporting only)
DENOM_FEATURES = {
    "1000":   "Brown/tan | Portrait on front | Simple pattern | Thua Thien Hue landscape",
    "2000":   "Gray-blue  | Portrait on front | Fine cross-hatch | Nam Dinh textile",
    "5000":   "Purple     | Portrait on front | Geometric pattern | Hydroelectric plant",
    "10000":  "Red-brown  | Portrait on front | Dense guilloche | Oil rig",
    "20000":  "Deep blue  | Portrait on front | Security thread | Hoi An ancient town",
    "50000":  "Pink/rose  | Portrait on front | Complex pattern | Hue Citadel",
    "100000": "Green      | Portrait on front | Fine security features | Ha Long Bay",
    "500000": "Blue-teal  | Portrait on front | Hologram strip | Phong Nha cave",
}

#  Color Signatures (HSV) for fast fallback 
COLOR_SIGNATURES = {
    "1000":   [(10,30,40,220,90,255)],
    "2000":   [(90,135,25,180,80,240)],
    "5000":   [(120,160,45,255,55,225)],
    "10000":  [(0,15,90,255,90,255),(160,180,90,255,90,255)],
    "20000":  [(100,130,70,255,55,215)],
    "50000":  [(0,20,70,255,100,255),(148,180,70,255,100,255)],
    "100000": [(38,82,45,255,55,215)],
    "500000": [(92,128,55,255,75,225)],
}


#  Gabor Texture Feature Extractor 

def extract_gabor_features(image_bgr: np.ndarray, n_orient: int = 4, n_freq: int = 3) -> np.ndarray:
    """Extract Gabor filter bank features for texture/pattern recognition.

    Captures hoa van (patterns) at multiple orientations and spatial frequencies.
    Orientations: 0, 45, 90, 135 degrees
    Frequencies: fine (numbers/text), medium (guilloche), coarse (layout)

    Args:
        image_bgr: Input image BGR.
        n_orient: Number of orientations.
        n_freq: Number of spatial frequencies.

    Returns:
        1D feature vector (n_orient * n_freq * 2) - mean+std per filter response.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    gray = cv2.resize(gray, (128, 128))
    features = []
    freqs = [0.1, 0.3, 0.5][:n_freq]
    thetas = [i * np.pi / n_orient for i in range(n_orient)]
    for freq in freqs:
        for theta in thetas:
            kernel = cv2.getGaborKernel((21, 21), sigma=4.0, theta=theta,
                                        lambd=1.0/freq, gamma=0.5, psi=0)
            resp = cv2.filter2D(gray, cv2.CV_32F, kernel)
            features.extend([float(resp.mean()), float(resp.std())])
    return np.array(features, dtype=np.float32)


def extract_color_features(image_bgr: np.ndarray, bins: int = 12) -> np.ndarray:
    """Extract HSV color histogram features.

    Args:
        image_bgr: Input image BGR.
        bins: Bins per channel.

    Returns:
        Normalized histogram feature vector (bins*3).
    """
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    feats = []
    ranges = [(0, 180), (0, 256), (0, 256)]
    for ch, (lo, hi) in enumerate(ranges):
        hist = cv2.calcHist([hsv], [ch], None, [bins], [lo, hi]).flatten()
        hist = hist / (hist.sum() + 1e-8)
        feats.extend(hist.tolist())
    return np.array(feats, dtype=np.float32)


def extract_lbp_features(image_bgr: np.ndarray, n_points: int = 24, radius: int = 3) -> np.ndarray:
    """Extract Local Binary Pattern features for fine texture (hoa van) recognition.

    Args:
        image_bgr: Input image BGR.
        n_points: LBP circular neighbourhood points.
        radius: LBP radius.

    Returns:
        Normalized LBP histogram (n_points+2 bins).
    """
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


def color_predict(image_bgr: np.ndarray) -> tuple[str, float]:
    """Quick HSV color-based denomination prediction (demo fallback).

    Args:
        image_bgr: Input image BGR.

    Returns:
        (denomination_str, confidence_0_to_1)
    """
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    scores: dict[str, float] = {}
    for denom, ranges in COLOR_SIGNATURES.items():
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for h0,h1,s0,s1,v0,v1 in ranges:
            mask = cv2.bitwise_or(mask,
                cv2.inRange(hsv, np.array([h0,s0,v0]), np.array([h1,s1,v1])))
        scores[denom] = float(np.count_nonzero(mask)) / mask.size
    best = max(scores, key=lambda k: scores[k])
    return best, scores[best] / (sum(scores.values()) + 1e-8)


#  Dataset Preparation 


def _extract_source_id(filename: str) -> str:
    """Extract source video/image ID from augmented filename.

    Augmented files have patterns like: 1000_front_20260315_001_hflip.jpg
    Source ID = everything before the augmentation suffix.
    """
    stem = Path(filename).stem
    # Remove known augmentation suffixes
    for suffix in ("_hflip", "_bright", "_rot", "_blur", "_noise", "_orig"):
        stem = stem.replace(suffix, "")
    return stem


def prepare_split(source_dir: Path, split_dir: Path, val_ratio: float = 0.2, seed: int = 42) -> dict:
    """Stratified split: 80% train / 20% val per denomination.

    Args:
        source_dir: Root dir with per-denomination sub-dirs.
        split_dir: Output dir - will contain train/ and val/.
        val_ratio: Fraction for validation.
        seed: Random seed.

    Returns:
        Stats dict {"train": N, "val": N, "skipped": N}.
    """
    rng = np.random.default_rng(seed)
    stats = {"train": 0, "val": 0, "skipped": 0}
    if split_dir.exists():
        shutil.rmtree(split_dir)
    logger.info("Preparing stratified split -> %s", split_dir)
    for denom in ACTIVE_CLASSES:
        src = source_dir / denom
        if not src.exists():
            logger.warning("  Missing: %s VND", denom); stats["skipped"] += 1; continue
        all_files = sorted(f for f in src.iterdir()
                           if f.suffix.lower() in {".jpg", ".jpeg", ".png"})
        if len(all_files) < 10:
            logger.warning("  %s VND: only %d images - skipped", denom, len(all_files))
            stats["skipped"] += 1; continue
        train_cls_dir = split_dir / "train" / denom
        val_cls_dir = split_dir / "val" / denom
        train_cls_dir.mkdir(parents=True, exist_ok=True)
        val_cls_dir.mkdir(parents=True, exist_ok=True)
        # Group by source to prevent data leakage
        from collections import defaultdict
        groups: dict[str, list[Path]] = defaultdict(list)
        for f in all_files:
            sid = _extract_source_id(f.name)
            groups[sid].append(f)
        # Split by groups, not individual files
        group_keys = sorted(groups.keys())
        rng.shuffle(group_keys)
        n_val_groups = max(1, int(len(group_keys) * val_ratio))
        val_groups = set(group_keys[:n_val_groups])
        n_train = n_val = 0
        for sid, files in groups.items():
            target = val_cls_dir if sid in val_groups else train_cls_dir
            for f in files:
                shutil.copy2(f, target / f.name)
            if sid in val_groups:
                n_val += len(files)
            else:
                n_train += len(files)
        stats["train"] += n_train
        stats["val"]   += n_val
        logger.info("  %6s VND -> %d train + %d val (%d source groups)", denom, n_train, n_val, len(group_keys))
    logger.info("  Total: %d train, %d val", stats["train"], stats["val"])
    return stats


#  Multi-Feature Model 

def build_model(n_classes: int, color_feat_dim: int, gabor_feat_dim: int):
    """Build multi-branch banknote recognition model.

    Architecture:
        Branch 1 (Visual):   EfficientNet-B3 backbone -> 1536-dim features
                             Learns: hoa van, so in, bo cuc, chi tiet
        Branch 2 (Color):    FC(color_feats) -> 64-dim
                             Learns: mau sac dac trung tung menh gia
        Branch 3 (Texture):  FC(gabor_feats) -> 64-dim
                             Learns: hoa van, kien truc soi
        Fusion:              Concat(1536+64+64) -> Dropout -> FC(n_classes)

    Args:
        n_classes: Number of denomination classes.
        color_feat_dim: Dimension of color feature vector.
        gabor_feat_dim: Dimension of Gabor feature vector.

    Returns:
        nn.Module: Multi-branch model.
    """
    import timm
    import torch
    import torch.nn as nn

    class MultiBranchBanknoteNet(nn.Module):
        def __init__(self):
            super().__init__()
            # Branch 1: Visual (EfficientNet-B3, 300x300) - learns patterns/numbers/layout
            self.backbone = timm.create_model(
                "efficientnet_b3", pretrained=True, num_classes=0,
                global_pool="avg",
            )
            vis_dim = self.backbone.num_features  # 1536

            # Branch 2: Color histogram features (mau sac)
            self.color_branch = nn.Sequential(
                nn.Linear(color_feat_dim, 128),
                nn.BatchNorm1d(128),
                nn.GELU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.GELU(),
            )

            # Branch 3: Texture/Gabor features (hoa van)
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
            vis    = self.backbone(image)          # (B, 1536)
            color  = self.color_branch(color_feat)  # (B, 64)
            texture = self.texture_branch(gabor_feat)  # (B, 64)
            fused  = torch.cat([vis, color, texture], dim=1)  # (B, 1664)
            return self.classifier(fused)

    return MultiBranchBanknoteNet()


#  Enhanced MobileNetV3 Model 

def build_enhanced_model(n_classes: int, gabor_dim: int = 24, lbp_dim: int = 10, edge_dim: int = 36):
    """Build MobileNetV3-Large multi-branch model with texture features.

    Architecture:
        Branch 1: MobileNetV3-Large backbone -> 960-dim
        Branch 2: Gabor texture features -> 48-dim
        Branch 3: LBP micro-texture features -> 32-dim
        Branch 4: Edge structural features -> 48-dim
        Fusion: concat(960+48+32+48=1088) -> FC(256) -> FC(n_classes)
    """
    import torch
    import torch.nn as nn
    from torchvision.models import (MobileNet_V3_Large_Weights,
                                    mobilenet_v3_large)

    class EnhancedBanknoteNet(nn.Module):
        def __init__(self):
            super().__init__()
            backbone = mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.DEFAULT)
            self.features = backbone.features
            self.pool = nn.AdaptiveAvgPool2d(1)
            vis_dim = 960

            self.gabor_branch = nn.Sequential(
                nn.Linear(gabor_dim, 48), nn.BatchNorm1d(48), nn.ReLU(True), nn.Dropout(0.2))
            self.lbp_branch = nn.Sequential(
                nn.Linear(lbp_dim, 32), nn.BatchNorm1d(32), nn.ReLU(True), nn.Dropout(0.2))
            self.edge_branch = nn.Sequential(
                nn.Linear(edge_dim, 48), nn.BatchNorm1d(48), nn.ReLU(True), nn.Dropout(0.2))

            fused_dim = vis_dim + 48 + 32 + 48  # 1088
            self.classifier = nn.Sequential(
                nn.Dropout(0.3),
                nn.Linear(fused_dim, 256), nn.BatchNorm1d(256), nn.ReLU(True),
                nn.Dropout(0.2),
                nn.Linear(256, n_classes),
            )

        def forward(self, image, gabor_feat, lbp_feat, edge_feat):
            x = self.features(image)
            x = self.pool(x).flatten(1)
            g = self.gabor_branch(gabor_feat)
            l = self.lbp_branch(lbp_feat)
            e = self.edge_branch(edge_feat)
            fused = torch.cat([x, g, l, e], dim=1)
            return self.classifier(fused)

    return EnhancedBanknoteNet()


#  Enhanced Dataset 

def make_enhanced_datasets(train_dir: Path, val_dir: Path, img_size: int = 224):
    """Create datasets for enhanced MobileNetV3 training with texture features."""
    from app.engine.feature_extractors import (extract_edge_features,
                                               extract_gabor_features,
                                               extract_lbp_features)
    from PIL import Image
    from torch.utils.data import Dataset
    from torchvision import transforms

    train_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.5, hue=0.1),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.0)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.1),
    ])

    val_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    class EnhancedBanknoteDataset(Dataset):
        def __init__(self, root: Path, transform):
            self.transform = transform
            self.samples = []
            self.classes = sorted([d.name for d in root.iterdir() if d.is_dir()])
            self.class_to_idx = {c: i for i, c in enumerate(self.classes)}
            for cls_dir in root.iterdir():
                if cls_dir.is_dir() and cls_dir.name in self.class_to_idx:
                    for img_path in cls_dir.iterdir():
                        if img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                            self.samples.append((img_path, self.class_to_idx[cls_dir.name]))

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            import torch
            path, label = self.samples[idx]
            pil = Image.open(str(path)).convert("RGB")
            img_tensor = self.transform(pil)

            # Feature extraction from BGR image (no augmentation on features)
            bgr = cv2.imread(str(path))
            if bgr is None:
                bgr = np.zeros((128, 128, 3), dtype=np.uint8)
            bgr_resized = cv2.resize(bgr, (128, 128))

            gabor = torch.tensor(extract_gabor_features(bgr_resized), dtype=torch.float32)
            lbp = torch.tensor(extract_lbp_features(bgr_resized), dtype=torch.float32)
            edge = torch.tensor(extract_edge_features(bgr_resized), dtype=torch.float32)
            return img_tensor, gabor, lbp, edge, torch.tensor(label, dtype=torch.long)

    train_ds = EnhancedBanknoteDataset(train_dir, train_tf)
    val_ds = EnhancedBanknoteDataset(val_dir, val_tf)
    return train_ds, val_ds, train_ds.classes, train_ds.class_to_idx


#  Multi-Feature Dataset 

def make_datasets(train_dir: Path, val_dir: Path, img_size: int):
    """Create datasets that return (image, color_feat, gabor_feat, label).

    Args:
        train_dir: Training data directory.
        val_dir: Validation data directory.
        img_size: Square image size.

    Returns:
        (train_dataset, val_dataset, class_to_idx)
    """
    import torch
    from PIL import Image
    from torch.utils.data import Dataset
    from torchvision import transforms

    # Strong augment: force model to learn structure, not just appearance
    train_tf = transforms.Compose([
        transforms.Resize((img_size + 40, img_size + 40)),
        transforms.RandomCrop(img_size),
        transforms.RandomHorizontalFlip(0.5),
        transforms.RandomVerticalFlip(0.3),
        transforms.RandomRotation(25),
        transforms.RandomPerspective(distortion_scale=0.2, p=0.4),
        transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.35),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
        transforms.RandomErasing(p=0.20, scale=(0.02, 0.15)),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
    ])

    # build class_to_idx from sorted ACTIVE_CLASSES present in train_dir
    present = sorted([d.name for d in train_dir.iterdir() if d.is_dir()])
    class_to_idx = {c: i for i, c in enumerate(present)}

    class BanknoteDataset(Dataset):
        def __init__(self, root: Path, tf, augment: bool):
            self.samples = []
            self.tf = tf
            self.augment = augment
            for cls_dir in sorted(root.iterdir()):
                if not cls_dir.is_dir(): continue
                label = class_to_idx.get(cls_dir.name)
                if label is None: continue
                for f in cls_dir.iterdir():
                    if f.suffix.lower() in {".jpg",".jpeg",".png"}:
                        self.samples.append((f, label))

        def __len__(self): return len(self.samples)

        def __getitem__(self, idx):
            path, label = self.samples[idx]
            # Load image
            pil = Image.open(str(path)).convert("RGB")
            img_tensor = self.tf(pil)

            # Load as BGR for OpenCV feature extraction (no augment for features)
            bgr = cv2.imread(str(path))
            if bgr is None:
                bgr = np.zeros((128, 128, 3), dtype=np.uint8)
            bgr = cv2.resize(bgr, (300, 300))

            color_feat = torch.tensor(extract_color_features(bgr), dtype=torch.float32)
            gabor_feat = torch.tensor(extract_gabor_features(bgr), dtype=torch.float32)
            return img_tensor, color_feat, gabor_feat, torch.tensor(label, dtype=torch.long)

    train_ds = BanknoteDataset(train_dir, train_tf, augment=True)
    val_ds   = BanknoteDataset(val_dir,   val_tf,   augment=False)
    return train_ds, val_ds, class_to_idx


#  Enhanced Training 

def train_enhanced(train_dir: Path, val_dir: Path, output_dir: Path,
                   epochs: int = 60, batch_size: int = 16, lr: float = 3e-4,
                   patience: int = 15, unfreeze_at: int = 10) -> dict:
    """Train enhanced MobileNetV3 multi-branch model."""
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training enhanced model on {device}")

    train_ds, val_ds, classes, class_to_idx = make_enhanced_datasets(train_dir, val_dir)
    n_classes = len(classes)
    logger.info(f"Classes: {classes}, Train: {len(train_ds)}, Val: {len(val_ds)}")

    if len(train_ds) == 0:
        raise RuntimeError("No training data found")

    # Class weights for imbalanced data
    counts = torch.zeros(n_classes)
    for _, _, _, _, label in train_ds:
        counts[label] += 1
    weights = 1.0 / (counts + 1e-8)
    weights = weights / weights.sum() * n_classes

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_dl = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    model = build_enhanced_model(n_classes)

    # Freeze backbone initially
    for name, p in model.named_parameters():
        if "features" in name:
            p.requires_grad = False

    criterion = nn.CrossEntropyLoss(weight=weights.to(device))
    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    model.to(device)

    best_val_acc = 0.0
    no_improve = 0
    history = {"train_loss": [], "val_loss": [], "val_acc": []}

    for epoch in range(epochs):
        # Unfreeze backbone after unfreeze_at epochs
        if epoch == unfreeze_at:
            logger.info(f"Epoch {epoch}: Unfreezing backbone")
            for p in model.parameters():
                p.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=lr * 0.1, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs - epoch)

        # Train
        model.train()
        total_loss = 0
        for img, gabor, lbp, edge, label in train_dl:
            img, gabor, lbp, edge, label = img.to(device), gabor.to(device), lbp.to(device), edge.to(device), label.to(device)
            optimizer.zero_grad()
            out = model(img, gabor, lbp, edge)
            loss = criterion(out, label)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()

        avg_train_loss = total_loss / max(len(train_dl), 1)
        scheduler.step()

        # Validate
        model.eval()
        val_loss, correct, total = 0, 0, 0
        with torch.no_grad():
            for img, gabor, lbp, edge, label in val_dl:
                img, gabor, lbp, edge, label = img.to(device), gabor.to(device), lbp.to(device), edge.to(device), label.to(device)
                out = model(img, gabor, lbp, edge)
                val_loss += criterion(out, label).item()
                correct += (out.argmax(1) == label).sum().item()
                total += label.size(0)

        val_acc = correct / max(total, 1)
        avg_val_loss = val_loss / max(len(val_dl), 1)
        history["train_loss"].append(avg_train_loss)
        history["val_loss"].append(avg_val_loss)
        history["val_acc"].append(val_acc)

        logger.info(f"Epoch {epoch+1}/{epochs} — loss: {avg_train_loss:.4f}, val_loss: {avg_val_loss:.4f}, val_acc: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            no_improve = 0
            # Save checkpoint
            output_dir.mkdir(parents=True, exist_ok=True)
            save_path = output_dir / "banknote_enhanced_v3.pth"
            torch.save({
                "model_type": "enhanced_mobilenetv3",
                "model_state_dict": model.state_dict(),
                "class_to_idx": class_to_idx,
                "idx_to_class": {v: k for k, v in class_to_idx.items()},
                "num_classes": n_classes,
                "best_val_acc": best_val_acc,
                "epoch": epoch + 1,
                "gabor_dim": 24,
                "lbp_dim": 10,
                "edge_dim": 36,
            }, str(save_path))
            logger.info(f"Saved best model: val_acc={best_val_acc:.4f}")
        else:
            no_improve += 1
            if no_improve >= patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break

    return {
        "best_val_acc": best_val_acc,
        "epochs_trained": len(history["train_loss"]),
        "classes": classes,
        "model_path": str(output_dir / "banknote_enhanced_v3.pth"),
        "history": history,
    }


#  Training 

def train(train_dir: Path, val_dir: Path, output_dir: Path,
          epochs: int = 80, batch_size: int = 24, lr: float = 3e-4,
          patience: int = 15, unfreeze_at: int = 15) -> dict:
    """Train multi-branch model with GPU acceleration.

    Args:
        train_dir: Training images (per-class subdirs).
        val_dir: Validation images.
        output_dir: Model output directory.
        epochs: Max epochs.
        batch_size: Images per batch (24 for 4GB VRAM with EfficientNet-B3).
        lr: Initial learning rate.
        patience: Early stopping patience.
        unfreeze_at: Epoch to unfreeze EfficientNet backbone.

    Returns:
        Training history dict.
    """
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s  (torch %s)", device, torch.__version__)
    if device.type == "cuda":
        logger.info("GPU: %s  |  VRAM: %.0f MB",
                    torch.cuda.get_device_name(0),
                    torch.cuda.get_device_properties(0).total_memory/1e6)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Probe feature dims from a sample image
    sample_bgr = np.zeros((300,300,3), dtype=np.uint8)
    color_dim  = len(extract_color_features(sample_bgr))
    gabor_dim  = len(extract_gabor_features(sample_bgr))
    logger.info("Feature dims: color=%d, gabor=%d", color_dim, gabor_dim)

    # Datasets
    train_ds, val_ds, class_to_idx = make_datasets(train_dir, val_dir, IMG_SIZE)
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    n_classes = len(class_to_idx)
    logger.info("Classes: %s", class_to_idx)
    logger.info("Sizes: %d train, %d val", len(train_ds), len(val_ds))

    # Class-balanced weights
    counts  = np.bincount([s[1] for s in train_ds.samples])
    weights = torch.tensor(1.0/(counts+1e-8), dtype=torch.float32)
    weights = weights / weights.sum() * len(weights)

    pin = device.type == "cuda"
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=0, pin_memory=pin)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=pin)

    # Model
    logger.info("Building MultiBranch EfficientNet-B3...")
    model = build_model(n_classes, color_dim, gabor_dim)

    # Freeze backbone initially
    for name, p in model.named_parameters():
        if "backbone" in name:
            p.requires_grad = False
    logger.info("Backbone frozen - warming up color+texture+classifier heads for %d epochs", unfreeze_at)

    model = model.to(device)

    criterion = nn.CrossEntropyLoss(weight=weights.to(device), label_smoothing=0.1)
    trainable = filter(lambda p: p.requires_grad, model.parameters())
    optimizer = optim.AdamW(trainable, lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)

    history   = {"train_loss":[], "val_loss":[], "train_acc":[], "val_acc":[], "lr":[]}
    best_acc  = 0.0; patience_ct = 0
    best_path = output_dir / "cash_recognition_best.pth"

    logger.info("=" * 72)
    logger.info("  epochs=%d | batch=%d | img=%dx%d | lr=%.1e | unfreeze_at=%d",
                epochs, batch_size, IMG_SIZE, IMG_SIZE, lr, unfreeze_at)
    logger.info("  Model: EfficientNet-B3 + Color branch + Gabor texture branch")
    logger.info("=" * 72)

    for epoch in range(epochs):
        t0 = time.time()

        # Unfreeze backbone
        if epoch == unfreeze_at:
            logger.info("Epoch %d: Unfreezing EfficientNet backbone", epoch+1)
            for p in model.parameters(): p.requires_grad = True
            # Reduce batch size for full fine-tuning (4GB VRAM constraint)
            ft_batch = max(8, batch_size // 3)
            logger.info("  Reducing batch size: %d -> %d to fit VRAM", batch_size, ft_batch)
            torch.cuda.empty_cache()
            train_dl = DataLoader(train_ds, batch_size=ft_batch, shuffle=True,  num_workers=0, pin_memory=pin)
            val_dl   = DataLoader(val_ds,   batch_size=ft_batch, shuffle=False, num_workers=0, pin_memory=pin)
            optimizer = optim.AdamW(model.parameters(), lr=lr*0.1, weight_decay=1e-4)
            scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)
            patience_ct = 0  # Reset patience to give full fine-tuning a fair chance

        # Train
        model.train(); tl=tc=tt=0
        for imgs, col_f, gab_f, labels in train_dl:
            imgs   = imgs.to(device)
            col_f  = col_f.to(device)
            gab_f  = gab_f.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            out  = model(imgs, col_f, gab_f)
            loss = criterion(out, labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            tl += loss.item()*imgs.size(0)
            tc += out.argmax(1).eq(labels).sum().item()
            tt += labels.size(0)

        # Validate
        model.eval(); vl=vc=vt=0
        with torch.no_grad():
            for imgs, col_f, gab_f, labels in val_dl:
                imgs   = imgs.to(device); col_f=col_f.to(device)
                gab_f  = gab_f.to(device); labels=labels.to(device)
                out  = model(imgs, col_f, gab_f)
                loss = criterion(out, labels)
                vl += loss.item()*imgs.size(0)
                vc += out.argmax(1).eq(labels).sum().item()
                vt += labels.size(0)

        atl=tl/tt; ata=tc/tt
        avl=vl/vt if vt else float("inf")
        ava=vc/vt if vt else 0.0
        scheduler.step(); cur_lr=optimizer.param_groups[0]["lr"]
        history["train_loss"].append(atl); history["val_loss"].append(avl)
        history["train_acc"].append(ata);  history["val_acc"].append(ava)
        history["lr"].append(cur_lr)

        trend=""
        if len(history["val_acc"])>1:
            d=ava-history["val_acc"][-2]
            trend=" up" if d>0.001 else (" down" if d<-0.001 else " same")
        logger.info("Epoch %2d/%d [%3.0fs] Train loss=%.4f acc=%5.1f%% | Val loss=%.4f acc=%5.1f%%%s | LR=%.2e",
                    epoch+1, epochs, time.time()-t0, atl, ata*100, avl, ava*100, trend, cur_lr)

        if ava > best_acc:
            best_acc=ava; patience_ct=0
            torch.save({"epoch":epoch+1,"model_state_dict":model.state_dict(),
                        "optimizer_state_dict":optimizer.state_dict(),
                        "val_acc":ava,"val_loss":avl,
                        "class_to_idx":class_to_idx,"idx_to_class":idx_to_class,
                        "classes":ACTIVE_CLASSES,"num_classes":n_classes,
                        "color_feat_dim":color_dim,"gabor_feat_dim":gabor_dim,
                        "img_size":IMG_SIZE,
                        "arch":"efficientnet_b3_multibranch_v2"}, str(best_path))
            logger.info("  Saved best model -> val_acc=%.1f%%", ava*100)
        else:
            patience_ct += 1
            if patience_ct >= patience:
                logger.info("Early stopping at epoch %d  (best=%.1f%%)", epoch+1, best_acc*100)
                break

    (output_dir/"training_history_v2.json").write_text(
        json.dumps(history, indent=2), encoding="utf-8")
    (output_dir/"class_mapping.json").write_text(
        json.dumps({"class_to_idx":class_to_idx,"idx_to_class":idx_to_class,
                    "classes":ACTIVE_CLASSES}, indent=2), encoding="utf-8")

    logger.info("TRAINING COMPLETE - best val_acc = %.1f%%", best_acc*100)
    return history


#  Evaluation 

def evaluate(model_path: Path, val_dir: Path) -> dict:
    """Full evaluation with per-class metrics, confusion matrix, color accuracy.

    Args:
        model_path: Path to best .pth checkpoint.
        val_dir: Validation directory (per-class subdirs).

    Returns:
        Evaluation results dict.
    """
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Loading: %s", model_path)
    ckpt  = torch.load(str(model_path), map_location=device, weights_only=False)
    c2i   = ckpt["class_to_idx"]
    i2c   = {v:k for k,v in c2i.items()}
    nc    = len(c2i)
    cdim  = ckpt.get("color_feat_dim", 36)
    gdim  = ckpt.get("gabor_feat_dim", 24)
    isz   = ckpt.get("img_size", IMG_SIZE)

    model = build_model(nc, cdim, gdim)
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(device).eval()

    _, val_ds, _ = make_datasets(val_dir.parent/"train", val_dir, isz)
    val_dl = DataLoader(val_ds, batch_size=24, shuffle=False, num_workers=0)
    logger.info("Val classes: %s", c2i)

    all_p=[]; all_l=[]
    with torch.no_grad():
        for imgs, col_f, gab_f, labels in val_dl:
            out = model(imgs.to(device), col_f.to(device), gab_f.to(device))
            all_p.extend(out.argmax(1).cpu().tolist())
            all_l.extend(labels.tolist())
    preds=np.array(all_p); labels=np.array(all_l)
    overall=float(np.mean(preds==labels))

    cm=np.zeros((nc,nc),dtype=int)
    for t,p in zip(labels,preds): cm[t][p]+=1

    per_class=[]
    for ci in range(nc):
        cname=i2c.get(ci,str(ci)); n=int(np.sum(labels==ci)); tp=cm[ci][ci]
        fp=int(np.sum(cm[:,ci]))-tp; fn=int(np.sum(cm[ci,:]))-tp
        acc=tp/n if n>0 else 0.0
        prec=tp/(tp+fp) if (tp+fp)>0 else 0.0
        rec=tp/(tp+fn) if (tp+fn)>0 else 0.0
        f1=2*prec*rec/(prec+rec) if (prec+rec)>0 else 0.0
        row=cm[ci].copy(); row[ci]=0; mx=int(np.argmax(row))
        per_class.append({"denomination":f"{cname} VND","total":n,"correct":int(tp),
                           "accuracy":acc,"precision":prec,"recall":rec,"f1":f1,
                           "most_confused_with":f"{i2c.get(mx,'?')} VND","confusion_count":int(row[mx]),
                           "features":DENOM_FEATURES.get(cname,"")})

    logger.info("Testing color fallback recognition...")
    ch=ct=0
    for ci in range(nc):
        cname=i2c.get(ci,str(ci)); d=val_dir/cname
        if not d.exists(): continue
        for p in list(d.glob("*.jpg"))[:50]:
            img=cv2.imread(str(p))
            if img is None: continue
            pred,_=color_predict(img)
            if pred==cname: ch+=1
            ct+=1

    results={"overall_accuracy":overall,"total_samples":len(all_l),"per_class":per_class,
             "color_accuracy":ch/ct if ct else 0.0,"color_samples_tested":ct,
             "confusion_matrix":cm.tolist(),"class_order":[i2c.get(i,str(i)) for i in range(nc)],
             "best_epoch":ckpt.get("epoch","?"),"arch":ckpt.get("arch","unknown")}
    _print_report(results)
    out=model_path.parent/"evaluation_results_v2.json"
    out.write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding="utf-8")
    logger.info("Results saved: %s", out)
    return results


#  Report 

def _print_report(r: dict) -> None:
    W=74
    print("\n"+"="*W)
    print("  MULTI-FEATURE BANKNOTE RECOGNITION - EVALUATION REPORT v2")
    print("="*W)
    print(f"  Architecture           : {r.get('arch','?')}")
    print(f"  Overall Model Accuracy : {r['overall_accuracy']*100:6.2f}%")
    print(f"  Color Fallback Acc     : {r['color_accuracy']*100:6.2f}%  ({r['color_samples_tested']} samples)")
    print(f"  Total Val Samples      : {r['total_samples']}")
    print(f"  Best Checkpoint Epoch  : {r['best_epoch']}")
    print()
    print("  Features learned per denomination:")
    for row in r["per_class"]:
        print(f"    {row['denomination']:<12}: {row.get('features','')}")
    print()
    print(f"  {'Denomination':<13} {'Acc':>6}  {'Prec':>6}  {'Recall':>7}  {'F1':>6}  Confused With")
    print("  "+"-"*(W-2))
    for row in sorted(r["per_class"],key=lambda x:x["accuracy"]):
        confused=(f"<- {row['most_confused_with']} ({row['confusion_count']}x)" if row["confusion_count"]>0 else "")
        st="[OK] " if row["accuracy"]>=0.90 else ("[WRN]" if row["accuracy"]>=0.75 else "[ERR]")
        print(f"  {st} {row['denomination']:<11} {row['accuracy']*100:>5.1f}%  "
              f"{row['precision']*100:>5.1f}%  {row['recall']*100:>6.1f}%  {row['f1']*100:>5.1f}%  {confused}")
    print()
    print("  Confusion Matrix (rows=actual, cols=predicted):")
    order=r["class_order"]; cm=np.array(r["confusion_matrix"])
    print("            "+"".join(f"{c:>8}" for c in order))
    for i,cls in enumerate(order):
        print(f"  {cls:>8}  "+"".join(
            f"[{cm[i][j]}]".rjust(8) if i==j else str(cm[i][j]).rjust(8)
            for j in range(len(order))))
    print()
    print("="*W)
    print("  DATA ANALYSIS & RECOMMENDATIONS")
    print("="*W)
    weak=[x for x in r["per_class"] if x["accuracy"]<0.85]
    strong=[x for x in r["per_class"] if x["accuracy"]>=0.90]
    if weak:
        print(f"\n  {len(weak)} denomination(s) below 85%:\n")
        for row in sorted(weak,key=lambda x:x["accuracy"]):
            print(f"  [FAIL] {row['denomination']:<13}: {row['accuracy']*100:.1f}%")
            print(f"     Features: {row.get('features','')}")
            print(f"     -> Add 200+ images with: varied lighting, angles 0/45/90 deg,")
            print(f"        close-ups of the denomination number and specific patterns")
            if row["confusion_count"]>3:
                print(f"     -> Confused with {row['most_confused_with']} ({row['confusion_count']}x)")
                print(f"        Add close-up shots highlighting distinguishing features")
            print()
    else:
        print("\n  All denominations >= 85%!")
    print("  Strong performers (>=90%):")
    for row in sorted(strong,key=lambda x:-x["accuracy"]):
        print(f"  [PASS] {row['denomination']:<13}: {row['accuracy']*100:.1f}%")
    print()
    print("  Missing denomination:")
    print("  [MISS] 200,000 VND - only 1 image (brown/orange, buu chinh/post office theme)")
    print("     -> Record 10-15s video (front+back) -> extract_banknote_frames.py -> retrain")
    ovr=r["overall_accuracy"]
    status=("PRODUCTION READY" if ovr>=0.95 else
            "DEMO READY" if ovr>=0.90 else
            "DEMO ACCEPTABLE (add more data)" if ovr>=0.80 else "NEEDS MORE DATA")
    print(f"\n  Status: {status}  ({ovr*100:.1f}%)")
    print("="*W)


#  CLI 

def main() -> None:
    ap=argparse.ArgumentParser(description="ParkSmart Multi-Feature Banknote Training v2")
    ap.add_argument("--epochs",      type=int,   default=80)
    ap.add_argument("--batch-size",  type=int,   default=24)
    ap.add_argument("--lr",          type=float, default=3e-4)
    ap.add_argument("--patience",    type=int,   default=15)
    ap.add_argument("--unfreeze-at", type=int,   default=15)
    ap.add_argument("--data-dir",    default=str(DATASET_DIR))
    ap.add_argument("--output-dir",  default=str(OUTPUT_DIR))
    ap.add_argument("--eval-only",   action="store_true")
    ap.add_argument("--enhanced",    action="store_true",
                    help="Train enhanced MobileNetV3 model with texture features (Gabor+LBP+Edge)")
    args=ap.parse_args()

    data_dir=Path(args.data_dir); output_dir=Path(args.output_dir)
    split_dir=SPLIT_DIR; best_path=output_dir/"cash_recognition_best.pth"

    print("\n"+"="*72)
    print("  ParkSmart AI - Multi-Feature Banknote Recognition v2")
    print("="*72)
    print(f"  Architecture: EfficientNet-B3 ({IMG_SIZE}x{IMG_SIZE}) + Color + Gabor Texture")
    print(f"  Features:     Hoa van | So in | Bo cuc | Mau sac | Chi tiet dac trung")
    print(f"  Data dir :    {data_dir}")
    print(f"  Output dir:   {output_dir}")
    print(f"  Classes  :    {ACTIVE_CLASSES}")
    print(f"  Excluded :    200000 VND (only 1 image)")
    print()

    if not args.eval_only:
        print("--- STEP 1: Data Split ---")
        stats=prepare_split(data_dir, split_dir)
        if stats["train"]==0:
            logger.error("No training data found: %s", data_dir); sys.exit(1)

        if args.enhanced:
            print("\n--- STEP 2: Enhanced MobileNetV3 Multi-Branch Training ---")
            logger.info("=== ENHANCED MobileNetV3 Multi-Branch Training ===")
            result = train_enhanced(
                train_dir=split_dir / "train",
                val_dir=split_dir / "val",
                output_dir=output_dir,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
            )
            logger.info(f"Enhanced training complete: val_acc={result['best_val_acc']:.4f}")
            logger.info(f"Model saved to: {result['model_path']}")
        else:
            print("\n--- STEP 2: Multi-Feature GPU Training ---")
            train(train_dir=split_dir/"train", val_dir=split_dir/"val",
                  output_dir=output_dir, epochs=args.epochs, batch_size=args.batch_size,
                  lr=args.lr, patience=args.patience, unfreeze_at=args.unfreeze_at)

    if not args.enhanced:
        print("\n--- STEP 3: Evaluation ---")
        if not best_path.exists():
            logger.error("No model: %s - run training first", best_path); sys.exit(1)
        evaluate(model_path=best_path, val_dir=split_dir/"val")

if __name__=="__main__":
    main()

    if not args.enhanced:
        print("\n--- STEP 3: Evaluation ---")
        if not best_path.exists():
            logger.error("No model: %s - run training first", best_path); sys.exit(1)
        evaluate(model_path=best_path, val_dir=split_dir/"val")

if __name__=="__main__":
    main()
