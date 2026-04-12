"""
Stage 2B — AI Fallback Classifier (MobileNetV3-Large).

Triggered when colour-based detection confidence is below the dynamic threshold.
Classifies cropped banknote into 9 Vietnamese denominations.

For MVP: if the model weights file is not available, returns a low-confidence
placeholder result so the pipeline never crashes.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from app.engine.feature_extractors import (EDGE_DIM, GABOR_DIM, LBP_DIM,
                                           TOTAL_FEATURE_DIM,
                                           extract_edge_features,
                                           extract_gabor_features,
                                           extract_lbp_features)

logger = logging.getLogger(__name__)

# 9 Vietnamese banknote denominations
DENOMINATION_CLASSES: list[str] = [
    "1000", "2000", "5000", "10000", "20000",
    "50000", "100000", "500000",
]
# NOTE: 200000 excluded from AI model (no training data) — handled by color classifier

# Input size for MobileNetV3-Large
INPUT_SIZE = (224, 224)
ENHANCED_INPUT_SIZE = (224, 224)


def build_enhanced_model(n_classes: int):
    """Build MobileNetV3-Large multi-branch model with texture features."""
    import torch
    import torch.nn as nn
    from torchvision.models import mobilenet_v3_large

    class EnhancedBanknoteNet(nn.Module):
        def __init__(self):
            super().__init__()
            # Branch 1: CNN backbone (MobileNetV3-Large)
            backbone = mobilenet_v3_large(weights=None)
            # Remove classifier, keep features
            self.features = backbone.features
            self.pool = nn.AdaptiveAvgPool2d(1)
            vis_dim = 960  # MobileNetV3-Large feature dim

            # Branch 2: Gabor texture features
            self.gabor_branch = nn.Sequential(
                nn.Linear(GABOR_DIM, 48),
                nn.BatchNorm1d(48),
                nn.ReLU(inplace=True),
                nn.Dropout(0.2),
            )

            # Branch 3: LBP micro-texture features
            self.lbp_branch = nn.Sequential(
                nn.Linear(LBP_DIM, 32),
                nn.BatchNorm1d(32),
                nn.ReLU(inplace=True),
                nn.Dropout(0.2),
            )

            # Branch 4: Edge structural features
            self.edge_branch = nn.Sequential(
                nn.Linear(EDGE_DIM, 48),
                nn.BatchNorm1d(48),
                nn.ReLU(inplace=True),
                nn.Dropout(0.2),
            )

            # Fusion classifier
            fused_dim = vis_dim + 48 + 32 + 48  # 1088
            self.classifier = nn.Sequential(
                nn.Dropout(0.3),
                nn.Linear(fused_dim, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(inplace=True),
                nn.Dropout(0.2),
                nn.Linear(256, n_classes),
            )

        def forward(self, image, gabor_feat, lbp_feat, edge_feat):
            # CNN branch
            x = self.features(image)
            x = self.pool(x).flatten(1)  # (B, 960)
            # Texture branches
            g = self.gabor_branch(gabor_feat)  # (B, 48)
            l = self.lbp_branch(lbp_feat)      # (B, 32)
            e = self.edge_branch(edge_feat)    # (B, 48)
            # Fusion
            fused = torch.cat([x, g, l, e], dim=1)  # (B, 1088)
            return self.classifier(fused)

    return EnhancedBanknoteNet()


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
        self._enhanced = False
        if model_path:
            self._try_load_model(model_path)

    def _try_load_model(self, model_path: str) -> None:
        """Try to load the PyTorch model."""
        try:
            import torch
            from torchvision.models import mobilenet_v3_large

            self._device = torch.device("cpu")
            checkpoint = torch.load(model_path, map_location=self._device, weights_only=False)

            # Detect model type from checkpoint
            if isinstance(checkpoint, dict) and "model_type" in checkpoint:
                # Enhanced multi-branch model
                model = build_enhanced_model(len(DENOMINATION_CLASSES))
                model.load_state_dict(checkpoint["model_state_dict"])
                model.eval()
                model.to(self._device)
                self._model = model
                self._enhanced = True
                logger.info("Loaded enhanced multi-branch banknote model")
            else:
                # Legacy MobileNetV3 model
                model = mobilenet_v3_large(weights=None)
                model.classifier[-1] = torch.nn.Linear(
                    model.classifier[-1].in_features, len(DENOMINATION_CLASSES)
                )
                if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                    model.load_state_dict(checkpoint["model_state_dict"])
                else:
                    model.load_state_dict(checkpoint)
                model.eval()
                model.to(self._device)
                self._model = model
                self._enhanced = False
                logger.info("Loaded legacy MobileNetV3 banknote model")
        except Exception as e:
            logger.warning(f"Could not load banknote AI model: {e}")
            self._model = None
            self._enhanced = False

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

            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            img_resized = cv2.resize(img_rgb, INPUT_SIZE)

            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            tensor = transform(img_resized).unsqueeze(0).to(self._device)

            with torch.no_grad():
                if self._enhanced:
                    # Extract texture features
                    gabor = torch.tensor(extract_gabor_features(img_bgr), dtype=torch.float32).unsqueeze(0).to(self._device)
                    lbp = torch.tensor(extract_lbp_features(img_bgr), dtype=torch.float32).unsqueeze(0).to(self._device)
                    edge = torch.tensor(extract_edge_features(img_bgr), dtype=torch.float32).unsqueeze(0).to(self._device)
                    outputs = self._model(tensor, gabor, lbp, edge)
                else:
                    outputs = self._model(tensor)
                probs = torch.softmax(outputs, dim=1)[0]

            all_probs = {
                DENOMINATION_CLASSES[i]: float(probs[i])
                for i in range(len(DENOMINATION_CLASSES))
            }
            best_idx = int(probs.argmax())
            best_denom = DENOMINATION_CLASSES[best_idx]
            best_conf = float(probs[best_idx])

            method_name = "enhanced" if self._enhanced else "mobilenetv3"
            return AIClassification(
                denomination=best_denom,
                confidence=best_conf,
                all_probabilities=all_probs,
                message=f"AI ({method_name}): {best_denom} VND with {best_conf:.1%} confidence",
            )

        except Exception as e:
            logger.error(f"Model inference error: {e}", exc_info=True)
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
