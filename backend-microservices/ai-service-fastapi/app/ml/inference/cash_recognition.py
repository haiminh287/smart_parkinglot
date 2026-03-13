"""
Cash Recognition Inference — Multi-arch Vietnamese banknote classifier.

Auto-detects model architecture from checkpoint:
  - v2 (EfficientNet-B3 + Color + Gabor branches) — arch = "efficientnet_b3_multibranch_v2"
  - v1 (ResNet50)                                  — legacy checkpoints (no arch key)

Used by the /ai/detect/cash/ endpoint.

Author: ParkSmart AI Team
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Root of ai-service-fastapi (train_and_evaluate.py lives here)
_SERVICE_ROOT = str(Path(__file__).resolve().parents[3])

# 9 Vietnamese banknote denominations
DENOMINATION_CLASSES: list[str] = [
    "1000", "2000", "5000", "10000", "20000",
    "50000", "100000", "200000", "500000",
]

INPUT_SIZE_V1 = 224  # ResNet50 v1
INPUT_SIZE_V2 = 300  # EfficientNet-B3 v2


class CashRecognitionInference:
    """Inference wrapper for Vietnamese banknote recognition.

    Supports two architectures, auto-detected from checkpoint:
      - v2: EfficientNet-B3 + Color (HSV) + Gabor texture branches
            (arch = "efficientnet_b3_multibranch_v2")
      - v1: ResNet50 (legacy, no arch key in checkpoint)

    Attributes:
        model_path: Path to the trained .pth model file.
        arch: Architecture string detected from checkpoint.
    """

    def __init__(self, model_path: str) -> None:
        """Initialize the inference engine.

        Args:
            model_path: Absolute path to the trained model checkpoint (.pth).

        Raises:
            FileNotFoundError: If model_path does not exist.
            ImportError: If PyTorch is not installed.
        """
        self._model = None
        self._device = "cpu"
        self._class_to_idx: dict[str, int] = {}
        self._idx_to_class: dict[int, str] = {}
        self._arch: str = "resnet50"
        self._input_size: int = INPUT_SIZE_V1
        self._color_dim: int = 0
        self._gabor_dim: int = 0
        # v2 feature extractors (set after import)
        self._extract_color = None
        self._extract_gabor = None

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Cash recognition model not found: {model_path}. "
                f"Train the model first using /ai/train/cash/ endpoint."
            )

        self._load_model(model_path)

    def _load_model(self, model_path: str) -> None:
        """Load model from checkpoint, auto-detecting v1/v2 architecture."""
        import torch
        import torch.nn as nn

        self._device = "cuda" if torch.cuda.is_available() else "cpu"

        checkpoint = torch.load(model_path, map_location=self._device, weights_only=False)

        if not (isinstance(checkpoint, dict) and "model_state_dict" in checkpoint):
            raise ValueError(f"Invalid checkpoint format: {model_path}")

        state_dict      = checkpoint["model_state_dict"]
        self._class_to_idx = checkpoint.get("class_to_idx", {})
        self._arch      = checkpoint.get("arch", "resnet50")
        self._input_size = checkpoint.get("img_size", INPUT_SIZE_V1)

        if self._class_to_idx:
            self._idx_to_class = {v: k for k, v in self._class_to_idx.items()}
        else:
            self._idx_to_class = {i: c for i, c in enumerate(DENOMINATION_CLASSES)}

        num_classes = len(self._idx_to_class)

        if self._arch == "efficientnet_b3_multibranch_v2":
            self._load_v2(checkpoint, state_dict, num_classes)
        else:
            self._load_v1(state_dict, num_classes)

        logger.info(
            "✅ CashRecognitionInference loaded: arch=%s  classes=%d  device=%s  img=%dx%d",
            self._arch, num_classes, self._device, self._input_size, self._input_size,
        )

    # ------------------------------------------------------------------
    # V2 — EfficientNet-B3 + Color + Gabor branches
    # ------------------------------------------------------------------

    def _load_v2(self, checkpoint: dict, state_dict: dict, num_classes: int) -> None:
        """Load multi-branch EfficientNet-B3 v2 model."""
        # Add service root to path so we can import train_and_evaluate
        if _SERVICE_ROOT not in sys.path:
            sys.path.insert(0, _SERVICE_ROOT)

        from train_and_evaluate import build_model, extract_color_features, extract_gabor_features  # noqa: E501

        self._color_dim = checkpoint.get("color_feat_dim", 36)
        self._gabor_dim = checkpoint.get("gabor_feat_dim", 24)
        self._extract_color = extract_color_features
        self._extract_gabor = extract_gabor_features

        model = build_model(num_classes, self._color_dim, self._gabor_dim)
        model.load_state_dict(state_dict)
        model.eval()
        model.to(self._device)
        self._model = model

    # ------------------------------------------------------------------
    # V1 — ResNet50 (legacy)
    # ------------------------------------------------------------------

    def _load_v1(self, state_dict: dict, num_classes: int) -> None:
        """Load legacy ResNet50 v1 model."""
        import torch.nn as nn
        from torchvision import models

        self._input_size = INPUT_SIZE_V1
        model = models.resnet50(weights=None)
        num_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(num_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes),
        )
        model.load_state_dict(state_dict)
        model.eval()
        model.to(self._device)
        self._model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, image_path: str) -> dict:
        """Predict the denomination of a banknote image.

        Args:
            image_path: Path to the image file (jpg/png/bmp).

        Returns:
            Dictionary with keys:
                - denomination: Predicted denomination string (e.g. "50000").
                - confidence: Confidence score (0.0–1.0).
                - all_probabilities: Dict of denomination → probability.
                - arch: Architecture used for inference.

        Raises:
            ValueError: If image cannot be read.
            RuntimeError: If model is not loaded.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        return self.predict_from_array(img)

    def predict_from_array(self, img_bgr: np.ndarray) -> dict:
        """Predict denomination from a BGR numpy array.

        Args:
            img_bgr: BGR image as numpy array (any size; will be resized).

        Returns:
            Same format as predict().
        """
        if self._model is None:
            raise RuntimeError("Model not loaded.")

        if self._arch == "efficientnet_b3_multibranch_v2":
            return self._predict_v2(img_bgr)
        return self._predict_v1(img_bgr)

    # ------------------------------------------------------------------
    # Internal inference helpers
    # ------------------------------------------------------------------

    def _predict_v2(self, img_bgr: np.ndarray) -> dict:
        """Run inference using EfficientNet-B3 multi-branch model (v2)."""
        import torch
        from torchvision import transforms

        sz = self._input_size  # 300
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (sz, sz))

        # Visual tensor
        tfm = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std =[0.229, 0.224, 0.225]),
        ])
        img_t = tfm(img_resized).unsqueeze(0).to(self._device)

        # Hand-crafted features (operated on BGR resized image)
        img_bgr_resized = cv2.resize(img_bgr, (sz, sz))
        col_f = torch.tensor(
            self._extract_color(img_bgr_resized), dtype=torch.float32
        ).unsqueeze(0).to(self._device)
        gab_f = torch.tensor(
            self._extract_gabor(img_bgr_resized), dtype=torch.float32
        ).unsqueeze(0).to(self._device)

        with torch.no_grad():
            outputs = self._model(img_t, col_f, gab_f)
            probs   = torch.softmax(outputs, dim=1)[0]

        return self._build_result(probs)

    def _predict_v1(self, img_bgr: np.ndarray) -> dict:
        """Run inference using legacy ResNet50 model (v1)."""
        import torch
        from torchvision import transforms

        sz = self._input_size  # 224
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (sz, sz))

        tfm = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std =[0.229, 0.224, 0.225]),
        ])
        tensor = tfm(img_resized).unsqueeze(0).to(self._device)

        with torch.no_grad():
            outputs = self._model(tensor)
            probs   = torch.softmax(outputs, dim=1)[0]

        return self._build_result(probs)

    def _build_result(self, probs) -> dict:
        """Build prediction result dict from probability tensor."""
        import torch

        all_probabilities: dict[str, float] = {}
        for idx in range(len(probs)):
            denom = self._idx_to_class.get(idx, str(idx))
            all_probabilities[denom] = round(float(probs[idx]), 4)

        best_idx   = int(torch.argmax(probs))
        best_denom = self._idx_to_class.get(best_idx, str(best_idx))
        best_conf  = float(probs[best_idx])

        return {
            "denomination":     best_denom,
            "confidence":       round(best_conf, 4),
            "all_probabilities": all_probabilities,
            "arch":             self._arch,
        }
