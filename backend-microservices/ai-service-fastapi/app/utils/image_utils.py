"""
Shared image utility functions for plate capture storage.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"
DEBUG_DIR = IMAGES_DIR / "debug"


def save_plate_image(
    image_bytes: bytes,
    action: str,
    identifier: str = "",
) -> Optional[str]:
    """Save plate image to disk and return filename.

    Args:
        image_bytes: JPEG bytes of plate image.
        action: Action label (scan, checkin, checkout).
        identifier: Booking ID or request identifier.

    Returns:
        Saved filename, or None if save failed.
    """
    try:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_id = identifier[:8] if identifier else "unknown"
        filename = f"plate_{action}_{short_id}_{timestamp}.jpg"
        filepath = IMAGES_DIR / filename
        filepath.write_bytes(image_bytes)
        logger.info("Plate image saved: %s (%d bytes)", filename, len(image_bytes))
        return filename
    except Exception as exc:
        logger.warning("Failed to save plate image: %s", exc)
        return None


def save_annotated_plate_image(
    image_bytes: bytes,
    x1: int, y1: int, x2: int, y2: int,
    plate_text: str,
    confidence: float,
    action: str = "scan",
    identifier: str = "",
) -> Optional[str]:
    """Draw bbox + label on image and save to IMAGES_DIR with 'annotated_' prefix."""
    try:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{plate_text} ({confidence:.0%})"
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(label, font, 0.7, 2)
        cv2.rectangle(img, (x1, y1 - th - 10), (x1 + tw, y1), (0, 255, 0), -1)
        cv2.putText(img, label, (x1, y1 - 5), font, 0.7, (0, 0, 0), 2)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_id = identifier[:8] if identifier else "unknown"
        filename = f"annotated_{action}_{short_id}_{timestamp}.jpg"
        filepath = IMAGES_DIR / filename
        cv2.imwrite(str(filepath), img)
        logger.info("Annotated image saved: %s", filename)
        return filename
    except Exception as exc:
        logger.warning("Failed to save annotated image: %s", exc)
        return None


def save_debug_image(
    image_bytes: bytes,
    action: str,
    plate_text: str = "",
    confidence: float = 0.0,
    bbox: Optional[dict] = None,
    decision: str = "unknown",
) -> Optional[str]:
    """Save every detection attempt (success or failure) to debug folder."""
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        if bbox:
            color = (0, 255, 0) if decision == "success" else (0, 0, 255)
            cv2.rectangle(img, (bbox["x1"], bbox["y1"]), (bbox["x2"], bbox["y2"]), color, 2)

        label = f"{decision} | {plate_text or 'N/A'} ({confidence:.0%})"
        cv2.putText(img, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"debug_{action}_{decision}_{timestamp}.jpg"
        filepath = DEBUG_DIR / filename
        cv2.imwrite(str(filepath), img)
        logger.debug("Debug image saved: %s", filename)
        return filename
    except Exception as exc:
        logger.warning("Failed to save debug image: %s", exc)
        return None
