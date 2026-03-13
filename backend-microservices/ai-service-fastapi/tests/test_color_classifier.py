"""
Tests for Stage 2A — Color-Based Denomination (color_classifier.py).
"""

import numpy as np
import cv2
import pytest

from app.engine.color_classifier import (
    compute_hue_histogram,
    score_denomination,
    classify_by_color,
    meets_threshold,
    ColorClassification,
    DenominationGroup,
    DENOMINATION_COLOR_MAP,
    SAFE_THRESHOLD,
    DANGER_THRESHOLD,
)


def make_colored_image(hue: int, saturation: int = 200, value: int = 200,
                       h: int = 100, w: int = 100) -> np.ndarray:
    """Create a solid-colour BGR image with specified HSV hue."""
    hsv_img = np.full((h, w, 3), [hue, saturation, value], dtype=np.uint8)
    bgr_img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
    return bgr_img


class TestHueHistogram:
    def test_returns_180_bins(self):
        img = make_colored_image(hue=60)
        hist = compute_hue_histogram(img)
        assert len(hist) == 180

    def test_normalized(self):
        img = make_colored_image(hue=60)
        hist = compute_hue_histogram(img)
        total = hist.sum()
        assert abs(total - 1.0) < 0.01

    def test_dominant_hue_matches(self):
        img = make_colored_image(hue=55)
        hist = compute_hue_histogram(img)
        dominant = int(np.argmax(hist))
        assert abs(dominant - 55) <= 2  # Allow small OpenCV rounding


class TestScoreDenomination:
    def test_perfect_match(self):
        """Histogram concentrated at a single hue → high score for matching denom."""
        hist = np.zeros(180)
        hist[55] = 1.0  # All weight at hue 55 (green → 100000)
        score = score_denomination(hist, [(55, 15)])
        assert score > 0.8

    def test_no_match(self):
        """Histogram far from the denomination's hue range → low score."""
        hist = np.zeros(180)
        hist[0] = 1.0  # All at red
        score = score_denomination(hist, [(110, 10)])  # Blue range
        assert score < 0.1

    def test_wrap_around(self):
        """Test hue ranges that wrap around 0/180 (e.g., 200000 VND red)."""
        hist = np.zeros(180)
        hist[175] = 0.5
        hist[3] = 0.5  # Red wraps around
        score = score_denomination(hist, [(5, 10)])
        assert score > 0.3


class TestClassifyByColor:
    def test_green_image_classified_as_100000(self):
        """Pure green should match 100000 VND (safe group)."""
        img = make_colored_image(hue=55, saturation=200)
        result = classify_by_color(img)
        assert result.denomination == "100000"
        assert result.group == DenominationGroup.SAFE

    def test_empty_image_returns_none(self):
        result = classify_by_color(np.array([], dtype=np.uint8))
        assert result.denomination is None
        assert result.confidence == 0.0

    def test_all_scores_populated(self):
        img = make_colored_image(hue=55)
        result = classify_by_color(img)
        assert len(result.all_scores) == 9  # 9 denominations

    def test_confidence_between_0_and_1(self):
        img = make_colored_image(hue=110)
        result = classify_by_color(img)
        assert 0.0 <= result.confidence <= 1.0

    def test_dominant_hue_populated(self):
        img = make_colored_image(hue=110)
        result = classify_by_color(img)
        assert result.dominant_hue >= 0


class TestMeetsThreshold:
    def test_safe_group_above_threshold(self):
        c = ColorClassification(
            denomination="100000", confidence=0.80,
            dominant_hue=55, group=DenominationGroup.SAFE,
            all_scores={}, message="",
        )
        assert meets_threshold(c) is True

    def test_safe_group_below_threshold(self):
        c = ColorClassification(
            denomination="100000", confidence=0.50,
            dominant_hue=55, group=DenominationGroup.SAFE,
            all_scores={}, message="",
        )
        assert meets_threshold(c) is False

    def test_danger_group_above_threshold(self):
        c = ColorClassification(
            denomination="20000", confidence=0.95,
            dominant_hue=110, group=DenominationGroup.DANGER,
            all_scores={}, message="",
        )
        assert meets_threshold(c) is True

    def test_danger_group_below_threshold(self):
        c = ColorClassification(
            denomination="20000", confidence=0.80,
            dominant_hue=110, group=DenominationGroup.DANGER,
            all_scores={}, message="",
        )
        assert meets_threshold(c) is False

    def test_no_group_returns_false(self):
        c = ColorClassification(
            denomination=None, confidence=0.99,
            dominant_hue=0, group=None,
            all_scores={}, message="",
        )
        assert meets_threshold(c) is False
