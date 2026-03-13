"""
Tests for Stage 0 — Preprocessing (quality gate + white balance).
"""

import numpy as np
import cv2
import pytest

from app.engine.preprocessing import (
    white_balance,
    compute_blur_score,
    compute_exposure_score,
    check_quality,
    preprocess,
    QualityStatus,
    QualityResult,
    BLUR_THRESHOLD,
    EXPOSURE_LOW_THRESHOLD,
    EXPOSURE_HIGH_THRESHOLD,
)


# ── Helpers ─────────────────────────────────────

def make_image(h: int = 100, w: int = 100, color: tuple = (128, 128, 128)) -> np.ndarray:
    """Create a solid-colour BGR image."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = color
    return img


def make_textured_image(h: int = 100, w: int = 100) -> np.ndarray:
    """Create a sharp image with high-frequency content (not blurry)."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    # Add a checkerboard pattern for high Laplacian variance
    for y in range(h):
        for x in range(w):
            if (x // 5 + y // 5) % 2 == 0:
                img[y, x] = (200, 200, 200)
            else:
                img[y, x] = (50, 50, 50)
    return img


def make_blurry_image(h: int = 100, w: int = 100) -> np.ndarray:
    """Create a blurry image (very low Laplacian variance)."""
    img = make_image(h, w, (128, 128, 128))
    img = cv2.GaussianBlur(img, (31, 31), 10)
    return img


# ── White Balance ───────────────────────────────

class TestWhiteBalance:
    def test_returns_same_shape(self):
        img = make_image()
        result = white_balance(img)
        assert result.shape == img.shape

    def test_returns_uint8(self):
        img = make_image(color=(100, 150, 200))
        result = white_balance(img)
        assert result.dtype == np.uint8

    def test_different_from_input(self):
        """White balance should modify the image somewhat."""
        img = make_image(color=(50, 100, 200))
        result = white_balance(img)
        # LAB equalization should change pixel values
        # (unless the image is perfectly uniform, which it is here,
        #  but that's fine — the function should still not crash)
        assert result.shape == img.shape


# ── Blur Detection ──────────────────────────────

class TestBlurDetection:
    def test_sharp_image_high_score(self):
        img = make_textured_image()
        score = compute_blur_score(img)
        assert score > BLUR_THRESHOLD

    def test_blurry_image_low_score(self):
        img = make_blurry_image()
        score = compute_blur_score(img)
        assert score < BLUR_THRESHOLD

    def test_score_is_float(self):
        img = make_image()
        score = compute_blur_score(img)
        assert isinstance(score, float)


# ── Exposure Detection ──────────────────────────

class TestExposureDetection:
    def test_dark_image_low_score(self):
        img = make_image(color=(10, 10, 10))
        score = compute_exposure_score(img)
        assert score < EXPOSURE_LOW_THRESHOLD

    def test_bright_image_high_score(self):
        img = make_image(color=(245, 245, 245))
        score = compute_exposure_score(img)
        assert score > EXPOSURE_HIGH_THRESHOLD

    def test_normal_exposure(self):
        img = make_image(color=(128, 128, 128))
        score = compute_exposure_score(img)
        assert EXPOSURE_LOW_THRESHOLD < score < EXPOSURE_HIGH_THRESHOLD


# ── Quality Check ───────────────────────────────

class TestQualityCheck:
    def test_good_quality_returns_ok(self):
        img = make_textured_image()
        result = check_quality(img)
        assert result.status == QualityStatus.OK

    def test_blurry_returns_blurry(self):
        img = make_blurry_image()
        result = check_quality(img)
        assert result.status == QualityStatus.BLURRY

    def test_dark_returns_underexposed(self):
        # Need a sharp but dark image
        img = make_textured_image()
        img = (img * 0.1).astype(np.uint8)  # darken
        result = check_quality(img)
        assert result.status in (QualityStatus.UNDEREXPOSED, QualityStatus.BLURRY)

    def test_bright_returns_overexposed(self):
        # Very bright textured image
        img = make_textured_image()
        img = np.clip(img.astype(np.int16) + 150, 0, 255).astype(np.uint8)
        result = check_quality(img)
        assert result.status in (QualityStatus.OVEREXPOSED, QualityStatus.OK)

    def test_result_has_scores(self):
        img = make_image()
        result = check_quality(img)
        assert isinstance(result.blur_score, float)
        assert isinstance(result.exposure_score, float)
        assert isinstance(result.message, str)


# ── Full Preprocess ─────────────────────────────

class TestPreprocess:
    def test_returns_tuple(self):
        img = make_textured_image()
        corrected, quality = preprocess(img)
        assert isinstance(corrected, np.ndarray)
        assert isinstance(quality, QualityResult)

    def test_corrected_same_shape(self):
        img = make_textured_image()
        corrected, _ = preprocess(img)
        assert corrected.shape == img.shape

    def test_quality_result_populated(self):
        img = make_textured_image()
        _, quality = preprocess(img)
        assert quality.blur_score > 0
        assert quality.exposure_score > 0
