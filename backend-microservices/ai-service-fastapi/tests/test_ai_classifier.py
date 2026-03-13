"""
Tests for Stage 2B — AI Classifier (ai_classifier.py).
"""

import numpy as np
import cv2
import pytest

from app.engine.ai_classifier import (
    BanknoteAIClassifier,
    AIClassification,
    DENOMINATION_CLASSES,
    INPUT_SIZE,
)


def make_image(h: int = 100, w: int = 100, hue: int = 55) -> np.ndarray:
    """Create a coloured test image."""
    hsv = np.full((h, w, 3), [hue, 200, 200], dtype=np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


class TestBanknoteAIClassifier:
    """Tests for AI classifier (stub mode — no trained model)."""

    def test_init_no_model(self):
        classifier = BanknoteAIClassifier(model_path=None)
        assert classifier._model is None

    def test_init_invalid_path(self):
        classifier = BanknoteAIClassifier(model_path="/nonexistent/model.pth")
        assert classifier._model is None

    def test_stub_classify_returns_result(self):
        classifier = BanknoteAIClassifier(model_path=None)
        img = make_image()
        result = classifier.classify(img)
        assert isinstance(result, AIClassification)
        assert result.denomination is not None
        assert result.denomination in DENOMINATION_CLASSES

    def test_stub_confidence_moderate(self):
        """Stub should return moderate confidence (not too high)."""
        classifier = BanknoteAIClassifier(model_path=None)
        img = make_image()
        result = classifier.classify(img)
        assert 0.0 < result.confidence <= 0.6

    def test_stub_all_probabilities_populated(self):
        classifier = BanknoteAIClassifier(model_path=None)
        img = make_image()
        result = classifier.classify(img)
        assert len(result.all_probabilities) == len(DENOMINATION_CLASSES)
        for denom in DENOMINATION_CLASSES:
            assert denom in result.all_probabilities

    def test_empty_image_returns_empty(self):
        classifier = BanknoteAIClassifier(model_path=None)
        result = classifier.classify(np.array([], dtype=np.uint8))
        assert result.denomination is None
        assert result.confidence == 0.0

    def test_stub_message_mentions_stub(self):
        classifier = BanknoteAIClassifier(model_path=None)
        img = make_image()
        result = classifier.classify(img)
        assert "stub" in result.message.lower()


class TestDenominationClasses:
    def test_nine_classes(self):
        assert len(DENOMINATION_CLASSES) == 9

    def test_all_valid_denominations(self):
        expected = {"1000", "2000", "5000", "10000", "20000", "50000", "100000", "200000", "500000"}
        assert set(DENOMINATION_CLASSES) == expected

    def test_input_size(self):
        assert INPUT_SIZE == (224, 224)
