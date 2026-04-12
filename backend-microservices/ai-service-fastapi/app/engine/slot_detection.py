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
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.config import settings
from app.schemas.ai import OccupancyDetectionResponse, SlotOccupancyResult

logger = logging.getLogger(__name__)

# Vehicle class IDs in COCO dataset (used by YOLO11n)
VEHICLE_CLASS_IDS = frozenset({2, 3, 5, 7})  # car, motorcycle, bus, truck


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
        self._yolo_model = self._load_yolo()

    def _load_yolo(self):
        """Load YOLO model for vehicle detection.

        Load order:
          1. Configured path from settings (stable for Docker/local overrides)
          2. Ultralytics auto-download using `YOLO("yolo11n.pt")`
          3. OpenCV fallback (None)
        """
        configured_path = Path(settings.YOLO_PARKING_MODEL_PATH)

        try:
            from ultralytics import YOLO
        except Exception as exc:
            logger.warning(
                "YOLO import unavailable, using OpenCV fallback: %s", exc
            )
            return None

        if configured_path.exists():
            try:
                logger.info(
                    "Loading YOLO parking model from configured path: %s",
                    configured_path,
                )
                return YOLO(str(configured_path))
            except Exception as exc:
                logger.warning(
                    "Failed to load YOLO from configured path %s: %s",
                    configured_path,
                    exc,
                )

        logger.info(
            "Configured YOLO path not found (%s). Triggering ultralytics auto-download with yolo11n.pt",
            configured_path,
        )
        try:
            auto_model = YOLO("yolo11n.pt")
            logger.info("YOLO auto-download/load succeeded with yolo11n.pt")
        except Exception as exc:
            logger.warning(
                "YOLO auto-download failed, using OpenCV fallback: %s", exc
            )
            return None

        self._sync_downloaded_weights(auto_model, configured_path)
        return auto_model

    def _sync_downloaded_weights(self, model, target_path: Path) -> None:
        """Best-effort sync downloaded weights to configured path for stable next startup."""
        try:
            source = self._resolve_downloaded_weights_path(model)
            if source is None or not source.exists():
                logger.info(
                    "YOLO source weights path not found after auto-download; keeping runtime model only"
                )
                return

            target_path.parent.mkdir(parents=True, exist_ok=True)

            if source.resolve() == target_path.resolve():
                logger.info("YOLO weights already at configured path: %s", target_path)
                return

            shutil.copy2(source, target_path)
            logger.info("Synced YOLO weights to configured path: %s", target_path)
        except Exception as exc:
            logger.warning(
                "Failed to sync auto-downloaded YOLO weights to %s: %s",
                target_path,
                exc,
            )

    @staticmethod
    def _resolve_downloaded_weights_path(model) -> Optional[Path]:
        """Resolve local weight file path from ultralytics model object."""
        candidates = [
            getattr(model, "ckpt_path", None),
            getattr(getattr(model, "model", None), "ckpt_path", None),
            getattr(getattr(model, "model", None), "pt_path", None),
            "yolo11n.pt",
        ]

        for candidate in candidates:
            if not candidate:
                continue
            path = Path(str(candidate))
            if path.exists() and path.is_file():
                return path
        return None

    def _compute_iou(self, box_a: tuple, box_b: tuple) -> float:
        """Compute Intersection-over-Union for two bboxes (x1, y1, x2, y2)."""
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        return inter / (area_a + area_b - inter)

    def _detect_with_yolo(
        self, frame: np.ndarray, slots: list
    ) -> list[SlotOccupancyResult]:
        """Run YOLO inference and match vehicles to parking slots via IoU."""
        raw = self._yolo_model(frame, verbose=False)[0]
        vehicle_boxes = [
            (
                int(b.xyxy[0][0]),
                int(b.xyxy[0][1]),
                int(b.xyxy[0][2]),
                int(b.xyxy[0][3]),
            )
            for b in raw.boxes
            if int(b.cls[0]) in VEHICLE_CLASS_IDS
            and float(b.conf[0]) >= settings.YOLO_PARKING_CONF_THRESHOLD
        ]

        results: list[SlotOccupancyResult] = []
        for slot in slots:
            slot_box = (slot.x1, slot.y1, slot.x2, slot.y2)
            best_iou = max(
                (self._compute_iou(slot_box, vb) for vb in vehicle_boxes),
                default=0.0,
            )
            is_occupied = best_iou >= settings.YOLO_PARKING_IOU_THRESHOLD
            confidence = round(best_iou if is_occupied else 1.0 - best_iou, 3)
            results.append(
                SlotOccupancyResult(
                    slot_id=slot.slot_id,
                    slot_code=slot.slot_code,
                    zone_id=slot.zone_id,
                    status="occupied" if is_occupied else "available",
                    confidence=confidence,
                    method="yolo11n_iou",
                )
            )
        return results

    def detect_occupancy(
        self,
        frame: np.ndarray,
        slots: list[SlotBbox],
        camera_id: str = "unknown",
    ) -> OccupancyDetectionResponse:
        """Detect vehicle occupancy for all slots in a camera frame.

        Uses YOLO11n if loaded. Falls back to OpenCV edge/contour/color analysis.

        Args:
            frame: BGR numpy array from camera.
            slots: List of slot bounding boxes.
            camera_id: Camera identifier for logging.

        Returns:
            OccupancyDetectionResponse with per-slot status.
        """
        t0 = time.time()

        # Primary: YOLO detection
        slot_results: Optional[list[SlotOccupancyResult]] = None
        detection_method = "opencv_fallback"

        if self._yolo_model is not None:
            try:
                slot_results = self._detect_with_yolo(frame, slots)
                detection_method = "yolo11n"
            except Exception as exc:
                logger.warning("YOLO detection failed, falling back to OpenCV: %s", exc)

        # Fallback: OpenCV edge/contour/color analysis
        if slot_results is None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            slot_results = []
            for slot_bbox in slots:
                try:
                    r = self._detect_single_slot(gray, frame, slot_bbox)
                    slot_results.append(
                        SlotOccupancyResult(
                            slot_id=r.slot_id,
                            slot_code=r.slot_code,
                            zone_id=r.zone_id,
                            status=r.status.value,
                            confidence=r.confidence,
                            method=r.method,
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "Slot detection failed for %s: %s", slot_bbox.slot_code, exc
                    )
                    slot_results.append(
                        SlotOccupancyResult(
                            slot_id=slot_bbox.slot_id,
                            slot_code=slot_bbox.slot_code,
                            zone_id=slot_bbox.zone_id,
                            status="unknown",
                            confidence=0.0,
                            method="error",
                        )
                    )

        total_time_ms = (time.time() - t0) * 1000
        total_available = sum(1 for r in slot_results if r.status == "available")
        total_occupied = sum(1 for r in slot_results if r.status == "occupied")

        logger.info(
            "Frame detection for camera %s: %d slots (%d available, %d occupied) in %.1fms via %s",
            camera_id, len(slot_results), total_available, total_occupied,
            total_time_ms, detection_method,
        )

        return OccupancyDetectionResponse(
            camera_id=camera_id,
            total_slots=len(slot_results),
            total_available=total_available,
            total_occupied=total_occupied,
            detection_method=detection_method,
            processing_time_ms=round(total_time_ms, 1),
            slots=slot_results,
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
