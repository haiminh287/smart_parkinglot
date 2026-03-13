"""
Tests for Stage 1 — Banknote Detection (detector.py).
"""

import numpy as np
import pytest

from app.engine.detector import BanknoteDetector, DetectionResult, DetectionBox


def make_image(h: int = 200, w: int = 300) -> np.ndarray:
    """Create a test BGR image."""
    img = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
    return img


class TestBanknoteDetector:
    """Tests for BanknoteDetector (MVP fallback mode — no YOLO model)."""

    def test_init_no_model(self):
        detector = BanknoteDetector(model_path=None)
        assert detector._model is None

    def test_init_invalid_model_path(self):
        detector = BanknoteDetector(model_path="/nonexistent/model.pt")
        assert detector._model is None

    def test_fallback_detect_returns_full_image(self):
        detector = BanknoteDetector(model_path=None)
        img = make_image(200, 300)
        result = detector.detect(img)

        assert result.found is True
        assert result.cropped is not None
        assert result.cropped.shape == img.shape
        assert result.box is not None
        assert result.box.x1 == 0
        assert result.box.y1 == 0
        assert result.box.x2 == 300
        assert result.box.y2 == 200
        assert result.box.confidence == 1.0

    def test_fallback_message_mentions_fallback(self):
        detector = BanknoteDetector(model_path=None)
        img = make_image()
        result = detector.detect(img)
        assert "fallback" in result.message.lower()

    def test_cropped_is_copy(self):
        """Ensure cropped is a copy, not a reference to the original."""
        detector = BanknoteDetector(model_path=None)
        img = make_image()
        result = detector.detect(img)
        # Modify cropped to ensure it doesn't affect original
        result.cropped[0, 0] = [0, 0, 0]
        # This is a copy check — won't affect original if properly copied
        assert result.cropped is not img


class TestDetectionResult:
    def test_dataclass_fields(self):
        box = DetectionBox(x1=10, y1=20, x2=100, y2=200, confidence=0.95)
        result = DetectionResult(
            found=True,
            box=box,
            cropped=np.zeros((10, 10, 3), dtype=np.uint8),
            message="test",
        )
        assert result.found is True
        assert result.box.confidence == 0.95
        assert result.message == "test"

    def test_not_found(self):
        result = DetectionResult(found=False, box=None, cropped=None, message="no detection")
        assert result.found is False
        assert result.box is None
        assert result.cropped is None
