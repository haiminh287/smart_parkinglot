"""
Stage 2B — AI Fallback Classifier (MobileNetV3-Large).

Triggered when colour-based detection confidence is below the dynamic threshold.
Classifies cropped banknote into 9 Vietnamese denominations.

For MVP: if the model weights file is not available, returns a low-confidence
placeholder result so the pipeline never crashes.
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

# 9 Vietnamese banknote denominations
DENOMINATION_CLASSES: list[str] = [
    "1000", "2000", "5000", "10000", "20000",
    "50000", "100000", "200000", "500000",
]

# Input size for MobileNetV3-Large
INPUT_SIZE = (224, 224)


@dataclass
class AIClassification:
    """Result of AI-based denomination classification."""
    denomination: Optional[str]
    confidence: float
    all_probabilities: dict[str, float]
    message: str


class BanknoteAIClassifier:
    """
    MobileNetV3-Large classifier for Vietnamese banknotes.
    Falls back to a rule-based stub if model weights are not available.
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._model_path = model_path
        self._device = "cpu"
        if model_path:
            self._try_load_model(model_path)

    def _try_load_model(self, model_path: str) -> None:
        """Try to load the PyTorch model."""
        try:
            import torch
            from torchvision import models

            self._device = "cuda" if torch.cuda.is_available() else "cpu"

            model = models.mobilenet_v3_large(weights=None)
            # Replace classifier head for 9 classes
            model.classifier[-1] = torch.nn.Linear(
                model.classifier[-1].in_features, len(DENOMINATION_CLASSES)
            )
            state_dict = torch.load(model_path, map_location=self._device, weights_only=True)
            model.load_state_dict(state_dict)
            model.eval()
            model.to(self._device)
            self._model = model
            logger.info(f"✅ MobileNetV3 classifier loaded from {model_path}")
        except (ImportError, FileNotFoundError, Exception) as e:
            logger.warning(
                f"⚠️ AI classifier model not available ({e}). "
                f"Using stub fallback."
            )
            self._model = None

    def classify(self, img_bgr: np.ndarray) -> AIClassification:
        """
        Classify a cropped banknote image into denomination.
        Uses MobileNetV3 if available, else returns stub result.
        """
        if img_bgr is None or img_bgr.size == 0:
            return AIClassification(
                denomination=None, confidence=0.0,
                all_probabilities={}, message="Empty image",
            )

        if self._model is not None:
            return self._classify_with_model(img_bgr)
        return self._stub_classify(img_bgr)

    def _classify_with_model(self, img_bgr: np.ndarray) -> AIClassification:
        """Run inference with loaded PyTorch model."""
        try:
            import torch
            from torchvision import transforms

            # Prepare image
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            img_resized = cv2.resize(img_rgb, INPUT_SIZE)

            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ])

            tensor = transform(img_resized).unsqueeze(0).to(self._device)

            with torch.no_grad():
                outputs = self._model(tensor)
                probs = torch.softmax(outputs, dim=1)[0]

            # Build probability dict
            all_probs = {
                DENOMINATION_CLASSES[i]: float(probs[i])
                for i in range(len(DENOMINATION_CLASSES))
            }

            best_idx = int(torch.argmax(probs))
            best_denom = DENOMINATION_CLASSES[best_idx]
            best_conf = float(probs[best_idx])

            return AIClassification(
                denomination=best_denom,
                confidence=best_conf,
                all_probabilities=all_probs,
                message=f"AI classification: {best_denom} VND (conf={best_conf:.3f})",
            )

        except Exception as e:
            logger.error(f"AI classification error: {e}", exc_info=True)
            return self._stub_classify(img_bgr)

    def _stub_classify(self, img_bgr: np.ndarray) -> AIClassification:
        """
        Stub fallback when model is not available.
        Uses basic colour heuristics with lower confidence to indicate
        this is not a trained model result.
        """
        # Simple heuristic: compute dominant hue and make a rough guess
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        h_channel = hsv[:, :, 0]
        hist = cv2.calcHist([h_channel], [0], None, [180], [0, 180]).flatten()
        dominant_hue = float(np.argmax(hist))

        # Rough mapping from hue to denomination (lower confidence than color classifier)
        hue_map = [
            (range(0, 15), "200000"),
            (range(15, 25), "2000"),
            (range(25, 40), "1000"),
            (range(40, 75), "100000"),
            (range(75, 105), "500000"),
            (range(95, 120), "20000"),
            (range(105, 115), "5000"),
            (range(145, 175), "50000"),
            (range(165, 180), "200000"),
        ]

        best_denom = "100000"  # default
        for hue_range, denom in hue_map:
            if int(dominant_hue) in hue_range:
                best_denom = denom
                break

        # Generate probabilities with the stub being less confident
        all_probs = {d: 0.05 for d in DENOMINATION_CLASSES}
        all_probs[best_denom] = 0.50  # Stub gives moderate confidence

        return AIClassification(
            denomination=best_denom,
            confidence=0.50,
            all_probabilities=all_probs,
            message=f"AI stub: {best_denom} VND (hue={dominant_hue:.0f}, no trained model)",
        )
