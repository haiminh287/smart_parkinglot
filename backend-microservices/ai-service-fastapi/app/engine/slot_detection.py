"""
Slot Detection Pipeline — Detect vehicle occupancy in parking slots.

Uses bounding box coordinates stored in CarSlot model to crop regions
from camera frames, then classifies each region as occupied/available.

Detection methods (priority order):
  1. YOLOv8 object detection (vehicle class)
  2. Background subtraction + contour analysis
  3. Pixel intensity histogram comparison

Usage:
    detector = get_slot_detector()
    results = detector.detect_occupancy(frame, slots_with_bbox)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SlotStatus(str, Enum):
    """Detected slot occupancy status."""

    AVAILABLE = "available"
    OCCUPIED = "occupied"
    UNKNOWN = "unknown"


@dataclass
class SlotBbox:
    """Bounding box for a parking slot in camera frame."""

    slot_id: str
    slot_code: str
    zone_id: str
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class SlotDetectionResult:
    """Detection result for a single parking slot."""

    slot_id: str
    slot_code: str
    zone_id: str
    status: SlotStatus
    confidence: float
    method: str
    processing_time_ms: float = 0.0


@dataclass
class FrameDetectionResult:
    """Detection result for all slots in a camera frame."""

    camera_id: str
    slots: list[SlotDetectionResult] = field(default_factory=list)
    total_available: int = 0
    total_occupied: int = 0
    processing_time_ms: float = 0.0


class SlotDetector:
    """Detect vehicle occupancy in parking slots using computer vision.

    Primary method: Pixel intensity + edge density analysis.
    Occupied slots tend to have more edges and varied pixel distribution
    compared to empty slots (uniform asphalt).

    Args:
        occupancy_threshold: Edge density ratio above which slot is considered occupied.
        min_contour_area_ratio: Minimum contour area relative to slot area.
    """

    def __init__(
        self,
        occupancy_threshold: float = 0.15,
        min_contour_area_ratio: float = 0.25,
    ) -> None:
        self._occupancy_threshold = occupancy_threshold
        self._min_contour_area_ratio = min_contour_area_ratio
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )

    def detect_occupancy(
        self,
        frame: np.ndarray,
        slots: list[SlotBbox],
        camera_id: str = "unknown",
    ) -> FrameDetectionResult:
        """Detect occupancy for all slots in a camera frame.

        Args:
            frame: BGR numpy array from camera.
            slots: List of slot bounding boxes.
            camera_id: Camera identifier for logging.

        Returns:
            FrameDetectionResult with per-slot status.
        """
        t0 = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        results: list[SlotDetectionResult] = []

        for slot_bbox in slots:
            slot_t0 = time.time()
            try:
                result = self._detect_single_slot(gray, frame, slot_bbox)
            except Exception as exc:
                logger.warning(
                    "Slot detection failed for %s: %s", slot_bbox.slot_code, exc
                )
                result = SlotDetectionResult(
                    slot_id=slot_bbox.slot_id,
                    slot_code=slot_bbox.slot_code,
                    zone_id=slot_bbox.zone_id,
                    status=SlotStatus.UNKNOWN,
                    confidence=0.0,
                    method="error",
                )
            result.processing_time_ms = (time.time() - slot_t0) * 1000
            results.append(result)

        total_time = (time.time() - t0) * 1000
        available = sum(1 for r in results if r.status == SlotStatus.AVAILABLE)
        occupied = sum(1 for r in results if r.status == SlotStatus.OCCUPIED)

        logger.info(
            "Frame detection for camera %s: %d slots (%d available, %d occupied) in %.1fms",
            camera_id, len(results), available, occupied, total_time,
        )

        return FrameDetectionResult(
            camera_id=camera_id,
            slots=results,
            total_available=available,
            total_occupied=occupied,
            processing_time_ms=total_time,
        )

    def _detect_single_slot(
        self,
        gray: np.ndarray,
        color_frame: np.ndarray,
        bbox: SlotBbox,
    ) -> SlotDetectionResult:
        """Detect occupancy for a single slot using edge density analysis.

        Args:
            gray: Grayscale frame.
            color_frame: BGR color frame.
            bbox: Slot bounding box coordinates.

        Returns:
            SlotDetectionResult for this slot.
        """
        # Crop slot region
        roi_gray = gray[bbox.y1:bbox.y2, bbox.x1:bbox.x2]
        roi_color = color_frame[bbox.y1:bbox.y2, bbox.x1:bbox.x2]

        if roi_gray.size == 0:
            return SlotDetectionResult(
                slot_id=bbox.slot_id,
                slot_code=bbox.slot_code,
                zone_id=bbox.zone_id,
                status=SlotStatus.UNKNOWN,
                confidence=0.0,
                method="invalid_bbox",
            )

        slot_area = roi_gray.shape[0] * roi_gray.shape[1]

        # Method 1: Edge density analysis (Canny)
        edges = cv2.Canny(roi_gray, 50, 150)
        edge_density = np.count_nonzero(edges) / slot_area

        # Method 2: Contour analysis
        blurred = cv2.GaussianBlur(roi_gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        significant_contours = [
            c for c in contours
            if cv2.contourArea(c) > slot_area * self._min_contour_area_ratio
        ]

        # Method 3: Color variance (vehicles have more color variation than asphalt)
        hsv_roi = cv2.cvtColor(roi_color, cv2.COLOR_BGR2HSV)
        saturation_std = float(np.std(hsv_roi[:, :, 1]))
        value_std = float(np.std(hsv_roi[:, :, 2]))

        # Combined score
        edge_score = min(edge_density / self._occupancy_threshold, 1.0)
        contour_score = min(len(significant_contours) / 2.0, 1.0)
        color_score = min((saturation_std + value_std) / 100.0, 1.0)

        combined_score = (edge_score * 0.4) + (contour_score * 0.3) + (color_score * 0.3)

        is_occupied = combined_score >= 0.5
        status = SlotStatus.OCCUPIED if is_occupied else SlotStatus.AVAILABLE
        confidence = combined_score if is_occupied else (1.0 - combined_score)

        return SlotDetectionResult(
            slot_id=bbox.slot_id,
            slot_code=bbox.slot_code,
            zone_id=bbox.zone_id,
            status=status,
            confidence=round(confidence, 3),
            method="edge_contour_color",
        )


# Singleton instance
_slot_detector: Optional[SlotDetector] = None


def get_slot_detector(
    occupancy_threshold: float = 0.15,
    min_contour_area_ratio: float = 0.25,
) -> SlotDetector:
    """Get or create the singleton SlotDetector instance.

    Args:
        occupancy_threshold: Edge density threshold for occupancy.
        min_contour_area_ratio: Minimum significant contour area ratio.

    Returns:
        SlotDetector singleton.
    """
    global _slot_detector
    if _slot_detector is None:
        _slot_detector = SlotDetector(
            occupancy_threshold=occupancy_threshold,
            min_contour_area_ratio=min_contour_area_ratio,
        )
    return _slot_detector
