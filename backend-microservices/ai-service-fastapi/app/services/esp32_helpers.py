"""
Shared helper functions for ESP32 gate endpoints.

Extracted from ``app/routers/esp32.py`` so that the router module stays
thin (endpoint handlers only) and helpers can be unit-tested in isolation.

All functions that were previously prefixed with ``_`` are now public.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx
from app.config import settings
from app.engine.camera_capture import CameraCaptureError, get_camera_capture
from app.engine.plate_pipeline import PlateReadDecision, get_plate_pipeline
from app.models.ai import PredictionLog
from app.routers.camera import _STALE_THRESHOLD, _buffer_lock, _virtual_frame_buffer
from app.utils.image_utils import save_plate_image as _shared_save_plate_image
from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────── #

BOOKING_SERVICE_URL = settings.BOOKING_SERVICE_URL
PARKING_SERVICE_URL = settings.PARKING_SERVICE_URL
REALTIME_SERVICE_URL = settings.REALTIME_SERVICE_URL
GATEWAY_SECRET = settings.GATEWAY_SECRET

_MODEL_PATH = settings.PLATE_MODEL_PATH

CHECK_IN_EARLY_MINUTES = 15  # Allow 15 min early check-in

QR_SCAN_TIMEOUT_S = 30  # Seconds to wait for user to show QR code

# Path to test images — auto-detect local vs Docker
_LOCAL_IMAGES = Path(__file__).resolve().parent.parent / "images"
_DOCKER_IMAGES = Path("/app/app/images")
TEST_IMAGES_DIR = _LOCAL_IMAGES if _LOCAL_IMAGES.exists() else _DOCKER_IMAGES

# Directory to save captured plate images
PLATE_CAPTURES_DIR = _LOCAL_IMAGES

# ── Default Camera URLs (from env via Settings) ─────────────────────────── #
DEFAULT_QR_CAMERA_URL = f"{settings.CAMERA_DROIDCAM_URL}/video"
DEFAULT_PLATE_CAMERA_URL = settings.CAMERA_RTSP_URL


# ── Helpers ──────────────────────────────────────────────────────────────── #


def plate_pipeline():
    """Get the plate recognition pipeline singleton."""
    return get_plate_pipeline(model_path=_MODEL_PATH)


def normalize_plate(text: str) -> str:
    """Normalize plate to uppercase, alphanumeric only."""
    import re

    return re.sub(r"[^A-Z0-9]", "", text.upper())


def plates_match(ocr_plate: str, booking_plate: str) -> bool:
    """Compare OCR plate with booking plate (fuzzy match).

    OCR results may have minor errors (e.g. '5' read as '6', 'A' as '4').
    Allow up to 2 character differences for plates of similar length.
    """
    a = normalize_plate(ocr_plate)
    b = normalize_plate(booking_plate)

    # Exact match
    if a == b:
        return True

    # Length difference > 2 → definitely different plates
    if abs(len(a) - len(b)) > 2:
        return False

    # Simple character-level diff (Hamming-like for same length, edit distance for different)
    if len(a) == len(b):
        diffs = sum(1 for x, y in zip(a, b) if x != y)
        return diffs <= 3

    # Different lengths — use subsequence ratio
    from difflib import SequenceMatcher

    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio >= 0.70


def normalize_uuid(raw_id: str) -> str:
    """Ensure UUID is in dashed format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."""
    clean = raw_id.replace("-", "")
    try:
        return str(uuid.UUID(clean))
    except ValueError:
        return raw_id


async def get_booking(booking_id: str, user_id: str) -> dict:
    """Fetch booking details from booking-service."""
    booking_id = normalize_uuid(booking_id)
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET, "X-User-ID": user_id}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Booking không tồn tại hoặc không có quyền. (booking_id={booking_id})",
            )
        return resp.json()


async def call_booking_checkin(booking_id: str, user_id: str) -> dict:
    """Call booking-service checkin endpoint."""
    booking_id = normalize_uuid(booking_id)
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/checkin/"
    headers = {
        "X-Gateway-Secret": GATEWAY_SECRET,
        "X-User-ID": user_id,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers)
        return {"status_code": resp.status_code, "data": resp.json()}


async def call_booking_checkout(booking_id: str, user_id: str) -> dict:
    """Call booking-service checkout endpoint."""
    booking_id = normalize_uuid(booking_id)
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/checkout/"
    headers = {
        "X-Gateway-Secret": GATEWAY_SECRET,
        "X-User-ID": user_id,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers)
        return {"status_code": resp.status_code, "data": resp.json()}


async def get_booking_by_slot(slot_id: str) -> Optional[dict]:
    """Get active booking for a specific slot from booking-service."""
    url = f"{BOOKING_SERVICE_URL}/bookings/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET, "X-User-ID": "system"}
    params = {"slot_id": slot_id, "check_in_status": "checked_in"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                return results[0] if results else None
        except Exception as exc:
            logger.warning("Failed to fetch booking by slot: %s", exc)
    return None


async def update_slot_status(slot_id: str, new_status: str) -> bool:
    """Update slot status in parking-service."""
    url = f"{PARKING_SERVICE_URL}/parking/slots/{slot_id}/update-status/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.patch(url, headers=headers, json={"status": new_status})
            return resp.status_code in (200, 204)
        except Exception as exc:
            logger.warning("Failed to update slot status: %s", exc)
    return False


async def broadcast_gate_event(event: str, data: dict) -> None:
    """Broadcast gate event via realtime-service."""
    url = f"{REALTIME_SERVICE_URL}/api/broadcast/notification/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(
                url,
                headers=headers,
                json={
                    "type": event,
                    "message": data.get("message", ""),
                    "data": data,
                },
            )
        except Exception as exc:
            logger.warning("Failed to broadcast gate event: %s", exc)


async def broadcast_unity_spawn(
    booking_id: str,
    plate: str,
    slot_code: str,
    vehicle_type: str,
    qr_data: str,
) -> None:
    """Broadcast unity.spawn_vehicle command to Unity via realtime service."""
    url = f"{REALTIME_SERVICE_URL}/api/broadcast/unity-command/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(
                url,
                headers=headers,
                json={
                    "type": "unity.spawn_vehicle",
                    "data": {
                        "booking_id": booking_id,
                        "plate": plate,
                        "slot_code": slot_code,
                        "vehicle_type": vehicle_type,
                        "qr_data": qr_data,
                    },
                },
            )
            logger.info(
                "Broadcast unity.spawn_vehicle: booking=%s plate=%s slot=%s",
                booking_id,
                plate,
                slot_code,
            )
        except Exception as exc:
            logger.warning("Failed to broadcast unity spawn: %s", exc)


async def broadcast_unity_depart(booking_id: str, plate: str) -> None:
    """Broadcast unity.depart_vehicle → Unity gọi StartDeparture cho xe biển số này."""
    url = f"{REALTIME_SERVICE_URL}/api/broadcast/unity-command/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(
                url,
                headers=headers,
                json={
                    "type": "unity.depart_vehicle",
                    "data": {"booking_id": booking_id, "plate": plate},
                },
            )
            logger.info("Broadcast unity.depart_vehicle: booking=%s plate=%s", booking_id, plate)
        except Exception as exc:
            logger.warning("Failed to broadcast unity depart: %s", exc)


def save_plate_image(
    image_bytes: bytes,
    booking_id: str,
    action: str = "checkin",
) -> Optional[str]:
    """Save captured plate image to disk for records.

    Delegates to shared utility. Returns filename or None.
    """
    return _shared_save_plate_image(image_bytes, action=action, identifier=booking_id)


def get_camera_url(camera_type: str = "qr") -> str:
    """Return the hardcoded camera URL for the given type.

    Args:
        camera_type: 'qr' or 'plate'.

    Returns:
        Camera stream URL.
    """
    if camera_type == "plate":
        return DEFAULT_PLATE_CAMERA_URL
    return DEFAULT_QR_CAMERA_URL


def get_test_image_bytes(plate_hint: Optional[str] = None) -> Optional[bytes]:
    """Load a test image from the images folder.

    If plate_hint is provided, tries to find an image whose filename
    contains part of the plate text (e.g. "51A-224.56.jpg" for plate "51A-224.56").
    Falls back to random choice if no match found.

    Returns:
        JPEG bytes of a test image, or None if no images found.
    """
    if not TEST_IMAGES_DIR.exists():
        logger.warning("Test images directory not found: %s", TEST_IMAGES_DIR)
        return None

    images = list(TEST_IMAGES_DIR.glob("*.jpg")) + list(TEST_IMAGES_DIR.glob("*.png"))
    if not images:
        logger.warning("No test images found in %s", TEST_IMAGES_DIR)
        return None

    chosen = None
    if plate_hint:
        # Normalise hint: remove dots, dashes, spaces for fuzzy match
        hint_clean = (
            plate_hint.replace("-", "").replace(".", "").replace(" ", "").upper()
        )
        for img in images:
            stem_clean = (
                img.stem.replace("-", "").replace(".", "").replace(" ", "").upper()
            )
            if hint_clean in stem_clean or stem_clean in hint_clean:
                chosen = img
                logger.info(
                    "Test image matched plate hint '%s': %s", plate_hint, img.name
                )
                break

    if chosen is None:
        chosen = random.choice(images)
        logger.info("Using random test image: %s", chosen.name)

    return chosen.read_bytes()


async def capture_plate_image(
    camera_url: Optional[str],
    plate_hint: Optional[str] = None,
) -> tuple[Optional[bytes], bool]:
    """Capture plate image from camera or fall back to test image.

    Args:
        camera_url: Camera stream URL, or None to use test image.
        plate_hint: Expected plate text to help select matching test image.

    Returns:
        Tuple of (JPEG bytes or None, is_from_real_camera).
    """
    # Try live camera first
    if camera_url:
        capture = get_camera_capture()
        try:
            frame_bytes = await capture.capture_frame_bytes(camera_url, retries=1)
            logger.info("Captured plate image from camera: %s", camera_url)
            return frame_bytes, True
        except CameraCaptureError as exc:
            logger.warning(
                "Camera %s unreachable, falling back to test image: %s",
                camera_url,
                exc,
            )

    # Fallback to test image
    test_bytes = get_test_image_bytes(plate_hint=plate_hint)
    if test_bytes:
        logger.info("Using test image for plate OCR (no camera available)")
        return test_bytes, False

    logger.warning("No camera and no test images available for plate OCR")
    return None, False


def parse_qr_data(qr_data_str: str) -> dict:
    """Parse QR data — supports JSON or plain booking ID.

    Args:
        qr_data_str: QR string (JSON or plain booking ID).

    Returns:
        Dict with booking_id and user_id.

    Raises:
        ValueError: If QR data is empty or invalid.
    """
    text = qr_data_str.strip()
    if not text:
        raise ValueError("QR data is empty")

    # Try JSON first
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            booking_id = (
                data.get("booking_id") or data.get("id") or data.get("bookingId")
            )
            user_id = data.get("user_id") or data.get("userId") or "system"
            if not booking_id:
                raise ValueError(
                    f"QR JSON missing booking_id. Keys: {list(data.keys())}"
                )
            return {"booking_id": str(booking_id), "user_id": str(user_id)}
    except json.JSONDecodeError:
        pass

    # Plain text = booking ID
    return {"booking_id": text, "user_id": "system"}


def log_prediction(
    db: Session,
    pred_type: str,
    input_data: dict,
    output_data: dict,
    confidence: float,
    proc_time: float,
) -> None:
    """Log prediction to database."""
    try:
        log = PredictionLog(
            id=str(uuid.uuid4()),
            prediction_type=pred_type,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            model_version="esp32-integration-v1",
            processing_time=proc_time,
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to log prediction: %s", exc)


async def check_payment_status(booking: dict) -> bool:
    """Check if booking payment is completed.

    Args:
        booking: Booking data dict from booking-service.

    Returns:
        True if payment is completed or payment method is on_exit.
    """
    payment_status = booking.get(
        "paymentStatus", booking.get("payment_status", "pending")
    )
    payment_method = booking.get(
        "paymentMethod", booking.get("payment_method", "online")
    )

    # On-exit payment is verified at checkout time
    if payment_method == "on_exit":
        return True

    return payment_status == "completed"
    return payment_status == "completed"
