"""
Stage 1 — Banknote Detection (YOLOv8n).

Detects banknote region in the image and crops it.
For MVP: if no YOLO model file is available, returns the full image
as a "detected banknote" (confidence 1.0).
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

import logging

logger = logging.getLogger(__name__)


@dataclass
class DetectionBox:
    """Bounding box of a detected banknote."""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


@dataclass
class DetectionResult:
    """Result of banknote detection stage."""
    found: bool
    box: Optional[DetectionBox]
    cropped: Optional[np.ndarray]
    message: str


class BanknoteDetector:
    """
    YOLOv8n-based banknote detector.
    Falls back to full-image detection when model file is not available.
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._model_path = model_path
        if model_path:
            self._try_load_model(model_path)

    def _try_load_model(self, model_path: str) -> None:
        """Try to load YOLOv8 model, log warning if unavailable."""
        try:
            from ultralytics import YOLO
            self._model = YOLO(model_path)
            logger.info(f"✅ YOLOv8 banknote detector loaded from {model_path}")
        except (ImportError, FileNotFoundError, Exception) as e:
            logger.warning(
                f"⚠️ YOLOv8 model not available ({e}). "
                f"Using full-image fallback detection."
            )
            self._model = None

    def detect(self, img: np.ndarray, confidence_threshold: float = 0.5) -> DetectionResult:
        """
        Detect banknote in the image.

        If YOLOv8 model is loaded, uses it for detection.
        Otherwise, returns the full image as a detected banknote (MVP fallback).
        """
        if self._model is not None:
            return self._detect_with_yolo(img, confidence_threshold)
        return self._fallback_detect(img)

    def _detect_with_yolo(self, img: np.ndarray, confidence_threshold: float) -> DetectionResult:
        """Detect using loaded YOLO model."""
        try:
            results = self._model(img, verbose=False)
            if not results or len(results) == 0:
                return DetectionResult(
                    found=False, box=None, cropped=None,
                    message="No banknote detected by YOLO",
                )

            # Get best detection
            best_box = None
            best_conf = 0.0
            for result in results:
                for box in result.boxes:
                    conf = float(box.conf[0])
                    if conf > best_conf and conf >= confidence_threshold:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        best_box = DetectionBox(x1=x1, y1=y1, x2=x2, y2=y2, confidence=conf)
                        best_conf = conf

            if best_box is None:
                return DetectionResult(
                    found=False, box=None, cropped=None,
                    message=f"No detection above threshold ({confidence_threshold})",
                )

            # Crop the detected banknote region
            h, w = img.shape[:2]
            x1 = max(0, best_box.x1)
            y1 = max(0, best_box.y1)
            x2 = min(w, best_box.x2)
            y2 = min(h, best_box.y2)
            cropped = img[y1:y2, x1:x2]

            return DetectionResult(
                found=True,
                box=best_box,
                cropped=cropped,
                message=f"Banknote detected (conf={best_conf:.3f})",
            )

        except Exception as e:
            logger.error(f"YOLO detection error: {e}", exc_info=True)
            return self._fallback_detect(img)

    def _fallback_detect(self, img: np.ndarray) -> DetectionResult:
        """
        MVP fallback: treat the entire image as a banknote.
        In production, this should be replaced with a trained YOLO model.
        """
        h, w = img.shape[:2]
        box = DetectionBox(x1=0, y1=0, x2=w, y2=h, confidence=1.0)
        return DetectionResult(
            found=True,
            box=box,
            cropped=img.copy(),
            message="Full-image fallback detection (no YOLO model)",
        )
