"""Banknote v2 inference — EfficientNetV2-S + TTA + precision-first rejection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import torch
import torch.nn as nn
from app.ml.augmentations import build_tta_transforms
from torchvision.models import efficientnet_v2_s

logger = logging.getLogger(__name__)

DENOMINATION_CLASSES: list[str] = [
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
NUM_CLASSES = len(DENOMINATION_CLASSES)

# Approved thresholds from Task 7 review.
ACCEPT_HIGH_CONF = 0.85
ACCEPT_HIGH_MARGIN = 0.25
ACCEPT_LOW_CONF = 0.80
ACCEPT_LOW_MARGIN = 0.40


class CashResult(NamedTuple):
    decision: str  # "accept" | "reject"
    denomination: str | None
    confidence: float
    top1_conf: float
    margin: float
    all_probabilities: dict[str, float]


class CashRecognitionInference:
    """EfficientNetV2-S + TTA x5 banknote classifier with rejection logic."""

    def __init__(self, model_path: str) -> None:
        self.model_path = Path(model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Cash recognition model not found: {self.model_path}"
            )

        model = efficientnet_v2_s(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, NUM_CLASSES)
        model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model = model.to(self.device).eval()
        self.tta_transforms = build_tta_transforms()

        logger.info(
            "Loaded banknote v2 (EfficientNetV2-S) from %s on %s",
            self.model_path,
            self.device,
        )

    def predict(self, image_bgr: np.ndarray) -> CashResult:
        """Predict with TTA x5 and return accept/reject decision."""
        img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        all_probs: list[np.ndarray] = []

        with torch.no_grad():
            for transform in self.tta_transforms:
                tensor = transform(image=img_rgb)["image"].unsqueeze(0).to(self.device)
                logits = self.model(tensor)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
                all_probs.append(probs)

        avg_probs = np.mean(all_probs, axis=0)
        top1_idx = int(np.argmax(avg_probs))
        top1_conf = float(avg_probs[top1_idx])
        sorted_probs = np.sort(avg_probs)
        top2_conf = float(sorted_probs[-2])
        margin = top1_conf - top2_conf

        all_probabilities = {
            DENOMINATION_CLASSES[idx]: float(prob) for idx, prob in enumerate(avg_probs)
        }

        if top1_conf >= ACCEPT_HIGH_CONF and margin >= ACCEPT_HIGH_MARGIN:
            return CashResult(
                "accept",
                DENOMINATION_CLASSES[top1_idx],
                top1_conf,
                top1_conf,
                margin,
                all_probabilities,
            )

        if top1_conf >= ACCEPT_LOW_CONF and margin >= ACCEPT_LOW_MARGIN:
            return CashResult(
                "accept",
                DENOMINATION_CLASSES[top1_idx],
                top1_conf,
                top1_conf,
                margin,
                all_probabilities,
            )

        return CashResult(
            "reject", None, top1_conf, top1_conf, margin, all_probabilities
        )
