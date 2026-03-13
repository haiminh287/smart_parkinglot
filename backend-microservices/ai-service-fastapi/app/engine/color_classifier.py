"""
Stage 2A — Color-Based Denomination Detection (HSV Histogram).

Uses the dominant hue of the cropped banknote to classify denomination.
Each Vietnamese banknote has a distinctive dominant colour.

Denomination → Dominant Hue Ranges (OpenCV H: 0-179):
  - 1000 VND  : Yellow-Green   (25-40)
  - 2000 VND  : Brown-Olive    (15-25)
  - 5000 VND  : Blue-Gray      (95-115)
  - 10000 VND : Yellow-Brown   (18-30)
  - 20000 VND : Blue           (100-120)
  - 50000 VND : Pink-Purple    (145-175)
  - 100000 VND: Green          (40-75)
  - 200000 VND: Red-Brown      (0-15 or 165-179)
  - 500000 VND: Cyan-Blue      (80-105)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np


class DenominationGroup(str, Enum):
    """Group determines confidence threshold."""
    SAFE = "safe"       # Distinctive colours → threshold 0.75
    DANGER = "danger"   # Overlapping colours → threshold 0.90


@dataclass
class ColorClassification:
    """Result of color-based denomination classification."""
    denomination: Optional[str]
    confidence: float
    dominant_hue: float
    group: Optional[DenominationGroup]
    all_scores: dict[str, float]
    message: str


# ── Vietnamese Banknote Color Map ───────────────
# Each entry: denomination → (hue_center, hue_range, group)
# hue_range is the ± tolerance around hue_center

DENOMINATION_COLOR_MAP: dict[str, tuple[list[tuple[int, int]], DenominationGroup]] = {
    "1000":   ([(32, 8)], DenominationGroup.DANGER),
    "2000":   ([(20, 5)], DenominationGroup.DANGER),
    "5000":   ([(105, 10)], DenominationGroup.DANGER),
    "10000":  ([(24, 6)], DenominationGroup.DANGER),
    "20000":  ([(110, 10)], DenominationGroup.DANGER),
    "50000":  ([(160, 15)], DenominationGroup.DANGER),
    "100000": ([(55, 15)], DenominationGroup.SAFE),
    "200000": ([(5, 10), (172, 8)], DenominationGroup.SAFE),  # wraps around 0/180
    "500000": ([(92, 12)], DenominationGroup.DANGER),
}

# ── Thresholds ──────────────────────────────────

SAFE_THRESHOLD = 0.75
DANGER_THRESHOLD = 0.90


def compute_hue_histogram(img_bgr: np.ndarray) -> np.ndarray:
    """
    Compute the hue histogram of a BGR image.
    Returns a 180-bin normalized histogram.
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    h_channel = hsv[:, :, 0]

    # Filter out low-saturation pixels (grey/white/black) which are not useful
    s_channel = hsv[:, :, 1]
    mask = s_channel > 30  # Only consider sufficiently saturated pixels

    if np.count_nonzero(mask) < 100:
        # Not enough coloured pixels — use all pixels
        mask = None

    hist = cv2.calcHist(
        [h_channel], [0], mask.astype(np.uint8) * 255 if mask is not None else None,
        [180], [0, 180],
    )
    hist = hist.flatten()

    # Normalize
    total = hist.sum()
    if total > 0:
        hist = hist / total

    return hist


def score_denomination(hist: np.ndarray, hue_centers: list[tuple[int, int]]) -> float:
    """
    Score how well a hue histogram matches a denomination's expected hue range.
    Returns a score between 0 and 1.
    """
    total = 0.0
    for center, radius in hue_centers:
        low = center - radius
        high = center + radius

        if low < 0:
            # Wrap around: e.g. hue 175 ± 10 → [165..179] + [0..5]
            score = float(hist[max(0, low + 180):180].sum() + hist[0:high + 1].sum())
        elif high >= 180:
            score = float(hist[low:180].sum() + hist[0:high - 180 + 1].sum())
        else:
            score = float(hist[low:high + 1].sum())

        total += score

    return min(total, 1.0)


def classify_by_color(img_bgr: np.ndarray) -> ColorClassification:
    """
    Classify a cropped banknote image by its dominant colour (HSV histogram).

    Returns ColorClassification with denomination, confidence, and all scores.
    """
    if img_bgr is None or img_bgr.size == 0:
        return ColorClassification(
            denomination=None, confidence=0.0, dominant_hue=0.0,
            group=None, all_scores={}, message="Empty image",
        )

    hist = compute_hue_histogram(img_bgr)
    dominant_hue = float(np.argmax(hist))

    # Score each denomination
    scores: dict[str, float] = {}
    for denom, (hue_centers, _group) in DENOMINATION_COLOR_MAP.items():
        scores[denom] = score_denomination(hist, hue_centers)

    if not scores:
        return ColorClassification(
            denomination=None, confidence=0.0, dominant_hue=dominant_hue,
            group=None, all_scores=scores, message="No denominations configured",
        )

    # Find best match
    best_denom = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_denom]
    best_group = DENOMINATION_COLOR_MAP[best_denom][1]

    return ColorClassification(
        denomination=best_denom,
        confidence=best_score,
        dominant_hue=dominant_hue,
        group=best_group,
        all_scores=scores,
        message=f"Color match: {best_denom} VND (conf={best_score:.3f}, hue={dominant_hue:.0f})",
    )


def meets_threshold(classification: ColorClassification) -> bool:
    """
    Check if color classification confidence meets the dynamic threshold
    for the denomination's group.
    """
    if classification.group is None or classification.denomination is None:
        return False

    threshold = (
        SAFE_THRESHOLD if classification.group == DenominationGroup.SAFE
        else DANGER_THRESHOLD
    )
    return classification.confidence >= threshold
