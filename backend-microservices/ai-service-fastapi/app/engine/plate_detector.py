"""
License Plate Detector — YOLOv8 (finetune-v1m).

Detects license plate region in the image and returns cropped plate + bounding box.
Falls back to full-image if model unavailable.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PlateBox:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


@dataclass
class PlateDetectionResult:
    found: bool
    box: Optional[PlateBox]
    cropped: Optional[np.ndarray]   # BGR cropped plate region
    message: str


class LicensePlateDetector:
    """YOLOv8-based license plate detector."""

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        if model_path and os.path.exists(model_path):
            self._load(model_path)
        else:
            logger.warning(f"⚠️  Plate model not found at {model_path!r} — using full-image fallback")

    def _load(self, path: str) -> None:
        try:
            from ultralytics import YOLO
            self._model = YOLO(path)
            logger.info(f"✅ License plate YOLO model loaded from {path}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load plate YOLO model: {e}")
            self._model = None

    def detect(self, img: np.ndarray, conf_threshold: float = 0.25) -> PlateDetectionResult:
        """Detect license plate region in image."""
        if self._model is not None:
            return self._detect_yolo(img, conf_threshold)
        return self._fallback(img)

    def _detect_yolo(self, img: np.ndarray, conf_threshold: float) -> PlateDetectionResult:
        try:
            results = self._model(img, verbose=False, conf=conf_threshold)
            best_box: Optional[PlateBox] = None
            best_conf = 0.0

            for result in results:
                for box in result.boxes:
                    conf = float(box.conf[0])
                    if conf > best_conf:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        # Clamp to image bounds
                        h, w = img.shape[:2]
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)
                        best_box = PlateBox(x1=x1, y1=y1, x2=x2, y2=y2, confidence=conf)
                        best_conf = conf

            if best_box is None:
                return PlateDetectionResult(
                    found=False, box=None, cropped=None,
                    message=f"No license plate detected (threshold={conf_threshold})"
                )

            cropped = img[best_box.y1:best_box.y2, best_box.x1:best_box.x2]
            return PlateDetectionResult(
                found=True, box=best_box, cropped=cropped,
                message=f"Plate detected (conf={best_conf:.2f})"
            )
        except Exception as e:
            logger.error(f"YOLO detection error: {e}", exc_info=True)
            return self._fallback(img)

    def _fallback(self, img: np.ndarray) -> PlateDetectionResult:
        """Return full image as fallback (no YOLO model)."""
        h, w = img.shape[:2]
        return PlateDetectionResult(
            found=True,
            box=PlateBox(x1=0, y1=0, x2=w, y2=h, confidence=0.0),
            cropped=img.copy(),
            message="Fallback: no YOLO model — using full image"
        )
