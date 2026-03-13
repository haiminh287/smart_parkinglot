"""
Stage 0 — Preprocessing: Quality Gate + White Balance Correction.

Tasks:
  1. White Balance via LAB equalization (fix ambient light shift)
  2. Blur detection via Laplacian variance
  3. Exposure check via mean brightness
"""

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np


class QualityStatus(str, Enum):
    """Image quality status."""
    OK = "ok"
    BLURRY = "blurry"
    OVEREXPOSED = "overexposed"
    UNDEREXPOSED = "underexposed"
    BAD_QUALITY = "bad_quality"


@dataclass
class QualityResult:
    """Result of the quality gate check."""
    blur_score: float
    exposure_score: float
    status: QualityStatus
    message: str


# ── Thresholds ──────────────────────────────────

BLUR_THRESHOLD = 50.0          # Laplacian variance below this → blurry
EXPOSURE_LOW_THRESHOLD = 40.0  # Mean brightness below this → underexposed
EXPOSURE_HIGH_THRESHOLD = 220.0  # Mean brightness above this → overexposed


def white_balance(img: np.ndarray) -> np.ndarray:
    """
    Apply white balance correction using LAB equalization.
    Fixes HSV color shifts caused by warm/cool ambient lighting.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    lab[:, :, 0] = cv2.equalizeHist(l_channel)
    corrected = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return corrected


def compute_blur_score(img: np.ndarray) -> float:
    """
    Compute blur score using Laplacian variance.
    Higher value = sharper image, lower = blurry.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def compute_exposure_score(img: np.ndarray) -> float:
    """
    Compute exposure score as mean brightness of the image.
    Returns value between 0 (black) and 255 (white).
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    return float(np.mean(gray))


def check_quality(img: np.ndarray) -> QualityResult:
    """
    Run the full quality gate check: blur + exposure.
    Returns QualityResult with status and scores.
    """
    blur_score = compute_blur_score(img)
    exposure_score = compute_exposure_score(img)

    if blur_score < BLUR_THRESHOLD:
        return QualityResult(
            blur_score=blur_score,
            exposure_score=exposure_score,
            status=QualityStatus.BLURRY,
            message=f"Image too blurry (score={blur_score:.1f}, threshold={BLUR_THRESHOLD})",
        )

    if exposure_score < EXPOSURE_LOW_THRESHOLD:
        return QualityResult(
            blur_score=blur_score,
            exposure_score=exposure_score,
            status=QualityStatus.UNDEREXPOSED,
            message=f"Image underexposed (brightness={exposure_score:.1f})",
        )

    if exposure_score > EXPOSURE_HIGH_THRESHOLD:
        return QualityResult(
            blur_score=blur_score,
            exposure_score=exposure_score,
            status=QualityStatus.OVEREXPOSED,
            message=f"Image overexposed (brightness={exposure_score:.1f})",
        )

    return QualityResult(
        blur_score=blur_score,
        exposure_score=exposure_score,
        status=QualityStatus.OK,
        message="Image quality is acceptable",
    )


def preprocess(img: np.ndarray) -> tuple[np.ndarray, QualityResult]:
    """
    Full Stage 0 pipeline:
      1. Check quality (blur + exposure)
      2. Apply white balance correction
    Returns (corrected_image, quality_result).
    """
    quality = check_quality(img)
    corrected = white_balance(img)
    return corrected, quality
