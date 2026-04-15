"""
ESP32 Integration API — Autonomous check-in / check-out / slot verification.

Endpoints:
  POST /ai/parking/esp32/check-in/     — Gate-in: QR scan + plate OCR + barrier
  POST /ai/parking/esp32/check-out/    — Gate-out: QR + plate + payment check + barrier
  POST /ai/parking/esp32/verify-slot/  — Slot-level: QR scan + booking→slot match
  POST /ai/parking/esp32/cash-payment/ — Cash inserted → AI detect → accumulate
  GET  /ai/parking/esp32/status/       — Health + camera status check

Camera behaviour:
  • If qr_camera_url / plate_camera_url provided AND reachable → capture live frame
  • Otherwise → fallback to test images in /app/app/images/ for plate OCR
  • QR data may be supplied directly via qr_data field (ESP32 scans QR itself)

ESP32 ↔ Arduino communication:
  ESP32 reads barrier_action from response:
    "open"  → UART send "OPEN_1" (entry) or "OPEN_2" (exit)
    "close" → UART send "CLOSE_1" / "CLOSE_2"
"""

import hmac
import json
import logging
import random
import time
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import cv2
import httpx
import numpy as np
from app.config import settings
from app.database import get_db
from app.engine.camera_capture import CameraCaptureError, get_camera_capture
from app.engine.plate_pipeline import PlateReadDecision, get_plate_pipeline
from app.engine.qr_reader import QRPayload, QRReadError, get_qr_reader
from app.models.ai import PredictionLog
from app.routers.camera import _STALE_THRESHOLD, _buffer_lock, _virtual_frame_buffer
from app.schemas.base import CamelModel
from app.schemas.esp32_device import (
    ESP32AckResponse,
    ESP32DeviceListResponse,
    ESP32DeviceLogsResponse,
    ESP32DeviceResponse,
    ESP32HeartbeatRequest,
    ESP32LogRequest,
    ESP32RegisterRequest,
    LogEntry,
)
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def verify_device_token(
    x_device_token: str = Header(default=""),
) -> None:
    expected = settings.ESP32_DEVICE_TOKEN
    if not x_device_token or not hmac.compare_digest(x_device_token, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing device token.")


router = APIRouter(
    prefix="/ai/parking/esp32",
    tags=["esp32"],
    dependencies=[Depends(verify_device_token)],
)

# ── Constants ────────────────────────────────────────────────────────────── #

BOOKING_SERVICE_URL = settings.BOOKING_SERVICE_URL
PARKING_SERVICE_URL = settings.PARKING_SERVICE_URL
REALTIME_SERVICE_URL = settings.REALTIME_SERVICE_URL
GATEWAY_SECRET = settings.GATEWAY_SECRET

DEVICE_OFFLINE_TIMEOUT_S = 30  # Device considered offline after this many seconds
MAX_LOGS_PER_DEVICE = 100  # Circular buffer size per device

# ── In-Memory Device Store ───────────────────────────────────────────────── #
# Structure: { device_id: { "ip": str, "firmware": str, "status": str,
#   "gpio_config": dict|None, "registered_at": datetime, "last_seen": datetime,
#   "wifi_rssi": int|None, "logs": deque[dict] } }
_esp32_devices: dict[str, dict] = {}

_MODEL_PATH = settings.PLATE_MODEL_PATH

CHECK_IN_EARLY_MINUTES = 15  # Allow 15 min early check-in


def seed_default_devices() -> None:
    """Pre-populate the in-memory ESP32 device registry with default gate devices.

    Called once at application startup so the admin ESP32 management page
    always shows the two gate controllers even before the physical ESP32
    boards send their first HTTP request.
    """
    now = datetime.now(timezone.utc)
    defaults = [
        {
            "device_id": "GATE-IN-01",
            "ip": "192.168.100.194",
            "firmware": "v1.0.0-parksmart",
            "status": "ready",
            "gpio_config": {"checkInPin": 4, "checkOutPin": 5},
        },
        {
            "device_id": "GATE-OUT-01",
            "ip": "192.168.100.194",
            "firmware": "v1.0.0-parksmart",
            "status": "ready",
            "gpio_config": {"checkInPin": 4, "checkOutPin": 5},
        },
    ]
    for d in defaults:
        did = d["device_id"]
        if did in _esp32_devices:
            continue
        logs: deque = deque(maxlen=MAX_LOGS_PER_DEVICE)
        logs.append(
            {
                "timestamp": now,
                "level": "info",
                "message": f"Device {did} pre-registered by AI Service startup.",
            }
        )
        _esp32_devices[did] = {
            "ip": d["ip"],
            "firmware": d["firmware"],
            "status": d["status"],
            "gpio_config": d["gpio_config"],
            "registered_at": now,
            "last_seen": now,
            "wifi_rssi": -45,
            "logs": logs,
        }
        logger.info("ESP32 pre-seeded at startup: %s", did)


def _auto_register_device(gate_id: str) -> None:
    """Auto-register or refresh an ESP32 device when it calls check-in/check-out.

    This ensures devices show up in the /devices list even if the ESP32
    firmware never calls the explicit /register endpoint.  If the device
    already exists, only ``last_seen`` and ``status`` are updated.
    """
    now = datetime.now(timezone.utc)
    device = _esp32_devices.get(gate_id)
    if device is not None:
        # Already registered — just refresh heartbeat
        device["last_seen"] = now
        device["status"] = "ready"
        return

    # First time seeing this gate_id — create minimal entry
    _esp32_devices[gate_id] = {
        "ip": "auto-detected",
        "firmware": "auto-registered",
        "status": "ready",
        "gpio_config": None,
        "registered_at": now,
        "last_seen": now,
        "wifi_rssi": None,
        "logs": deque(maxlen=MAX_LOGS_PER_DEVICE),
    }
    logger.info("ESP32 auto-registered via gate activity: device_id=%s", gate_id)


QR_SCAN_TIMEOUT_S = 30  # Seconds to wait for user to show QR code

# Path to test images — auto-detect local vs Docker
_LOCAL_IMAGES = Path(__file__).resolve().parent.parent / "images"
_DOCKER_IMAGES = Path("/app/app/images")
TEST_IMAGES_DIR = _LOCAL_IMAGES if _LOCAL_IMAGES.exists() else _DOCKER_IMAGES

# Directory to save captured plate images
PLATE_CAPTURES_DIR = _LOCAL_IMAGES

# Shared image save utility
from app.utils.image_utils import save_plate_image as _shared_save_plate_image

# ── Default Camera URLs (from env via Settings) ─────────────────────────── #
DEFAULT_QR_CAMERA_URL = f"{settings.CAMERA_DROIDCAM_URL}/video"
DEFAULT_PLATE_CAMERA_URL = settings.CAMERA_RTSP_URL


# ── Enums ────────────────────────────────────────────────────────────────── #


class BarrierAction(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    NO_ACTION = "no_action"


class GateEvent(str, Enum):
    CHECK_IN_SUCCESS = "check_in_success"
    CHECK_IN_FAILED = "check_in_failed"
    CHECK_OUT_SUCCESS = "check_out_success"
    CHECK_OUT_AWAITING_PAYMENT = "check_out_awaiting_payment"
    CHECK_OUT_FAILED = "check_out_failed"
    VERIFY_SLOT_SUCCESS = "verify_slot_success"
    VERIFY_SLOT_FAILED = "verify_slot_failed"


# ── Request / Response Schemas ───────────────────────────────────────────── #


class ESP32CheckInRequest(BaseModel):
    """Request from ESP32 gate-in device.

    QR data can be provided directly (ESP32 scans QR itself) or the
    server can capture from a QR camera.  Similarly for the plate image.
    """

    gate_id: str = Field(..., description="Unique gate identifier, e.g. GATE-IN-01")
    qr_data: Optional[str] = Field(
        None,
        description='QR data scanned by ESP32, JSON string: {"booking_id":"...","user_id":"..."}',
    )
    qr_camera_url: Optional[str] = Field(
        None, description="QR camera stream URL (override)"
    )
    plate_camera_url: Optional[str] = Field(
        None, description="Plate camera stream URL (override)"
    )
    request_id: Optional[str] = Field(None, description="Idempotency key (UUID)")


class ESP32CheckOutRequest(BaseModel):
    """Request from ESP32 gate-out device."""

    gate_id: str = Field(..., description="Unique gate identifier, e.g. GATE-OUT-01")
    qr_data: Optional[str] = Field(
        None,
        description='QR data scanned by ESP32, JSON string: {"booking_id":"...","user_id":"..."}',
    )
    qr_camera_url: Optional[str] = Field(None, description="QR camera stream URL")
    plate_camera_url: Optional[str] = Field(None, description="Plate camera stream URL")
    request_id: Optional[str] = Field(None, description="Idempotency key (UUID)")


class ESP32VerifySlotRequest(BaseModel):
    """Request from ESP32 slot-level device."""

    slot_code: str = Field(..., description="Physical slot code, e.g. A-01")
    zone_id: str = Field(..., description="Zone UUID where the slot is located")
    gate_id: str = Field(..., description="Slot gate identifier, e.g. SLOT-GATE-01")
    qr_data: Optional[str] = Field(None, description="QR data from ESP32")
    qr_camera_url: Optional[str] = Field(None, description="QR camera URL at slot")
    request_id: Optional[str] = Field(None, description="Idempotency key")


class CashPaymentRequest(BaseModel):
    """Request when cash is inserted at exit gate."""

    booking_id: str = Field(..., description="Booking UUID")
    image_base64: Optional[str] = Field(
        None, description="Base64-encoded image of cash"
    )
    camera_url: Optional[str] = Field(None, description="Cash slot camera URL")
    gate_id: str = Field(..., description="Gate identifier")
    request_id: Optional[str] = Field(None, description="Idempotency key")


class ESP32Response(CamelModel):
    """Standard response for ESP32 endpoints."""

    success: bool
    event: GateEvent
    barrier_action: BarrierAction
    message: str
    gate_id: str
    booking_id: Optional[str] = None
    plate_text: Optional[str] = None
    amount_due: Optional[float] = None
    amount_paid: Optional[float] = None
    processing_time_ms: float = 0.0
    plate_image_url: Optional[str] = None
    details: Optional[dict] = None


# ── Helpers ──────────────────────────────────────────────────────────────── #


def _plate_pipeline():
    """Get the plate recognition pipeline singleton."""
    return get_plate_pipeline(model_path=_MODEL_PATH)


def _normalize_plate(text: str) -> str:
    """Normalize plate to uppercase, alphanumeric only."""
    import re

    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _plates_match(ocr_plate: str, booking_plate: str) -> bool:
    """Compare OCR plate with booking plate (fuzzy match).

    OCR results may have minor errors (e.g. '5' read as '6', 'A' as '4').
    Allow up to 2 character differences for plates of similar length.
    """
    a = _normalize_plate(ocr_plate)
    b = _normalize_plate(booking_plate)

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


def _normalize_uuid(raw_id: str) -> str:
    """Ensure UUID is in dashed format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."""
    clean = raw_id.replace("-", "")
    try:
        return str(uuid.UUID(clean))
    except ValueError:
        return raw_id


async def _get_booking(booking_id: str, user_id: str) -> dict:
    """Fetch booking details from booking-service."""
    booking_id = _normalize_uuid(booking_id)
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


async def _call_booking_checkin(booking_id: str, user_id: str) -> dict:
    """Call booking-service checkin endpoint."""
    booking_id = _normalize_uuid(booking_id)
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/checkin/"
    headers = {
        "X-Gateway-Secret": GATEWAY_SECRET,
        "X-User-ID": user_id,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers)
        return {"status_code": resp.status_code, "data": resp.json()}


async def _call_booking_checkout(booking_id: str, user_id: str) -> dict:
    """Call booking-service checkout endpoint."""
    booking_id = _normalize_uuid(booking_id)
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/checkout/"
    headers = {
        "X-Gateway-Secret": GATEWAY_SECRET,
        "X-User-ID": user_id,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers)
        return {"status_code": resp.status_code, "data": resp.json()}


async def _get_booking_by_slot(slot_id: str) -> Optional[dict]:
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


async def _update_slot_status(slot_id: str, new_status: str) -> bool:
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


async def _broadcast_gate_event(event: str, data: dict) -> None:
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


async def _broadcast_unity_spawn(
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


def _save_plate_image(
    image_bytes: bytes,
    booking_id: str,
    action: str = "checkin",
) -> Optional[str]:
    """Save captured plate image to disk for records.

    Delegates to shared utility. Returns filename or None.
    """
    return _shared_save_plate_image(image_bytes, action=action, identifier=booking_id)


def _get_camera_url(camera_type: str = "qr") -> str:
    """Return the hardcoded camera URL for the given type.

    Args:
        camera_type: 'qr' or 'plate'.

    Returns:
        Camera stream URL.
    """
    if camera_type == "plate":
        return DEFAULT_PLATE_CAMERA_URL
    return DEFAULT_QR_CAMERA_URL


def _get_test_image_bytes(plate_hint: Optional[str] = None) -> Optional[bytes]:
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


async def _capture_plate_image(
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
    test_bytes = _get_test_image_bytes(plate_hint=plate_hint)
    if test_bytes:
        logger.info("Using test image for plate OCR (no camera available)")
        return test_bytes, False

    logger.warning("No camera and no test images available for plate OCR")
    return None, False


def _parse_qr_data(qr_data_str: str) -> dict:
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


def _log_prediction(
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


async def _check_payment_status(booking: dict) -> bool:
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


# ── ESP32 CHECK-IN ENDPOINT ──────────────────────────────────────────────── #


@router.post("/check-in/", response_model=ESP32Response)
async def esp32_check_in(
    payload: ESP32CheckInRequest,
    db: Session = Depends(get_db),
) -> ESP32Response:
    """ESP32 gate-in check-in flow.

    Flow:
      1. ESP32 button pressed → triggers this endpoint
      2. Open QR camera (real camera), capture frame, decode QR
      3. Fetch booking → validate status + time window
      4. Open plate camera (try real RTSP → fallback to test image)
      5. OCR plate → compare with booking plate
      6. Call booking-service checkin API
      7. Return barrier_action=open → ESP32 sends "OPEN_1" via UART to Arduino

    Args:
        payload: ESP32 check-in request with gate_id.
        db: Database session.

    Returns:
        ESP32Response with barrier action and booking details.
    """
    t0 = time.time()
    gate_id = payload.gate_id

    # Auto-register this ESP32 so it appears in /devices list
    _auto_register_device(gate_id)

    # ── Step 1: Get QR data (direct or camera scan) ────────────────── #
    qr_text: str = ""
    booking_id: str = ""
    user_id: str = "system"

    if payload.qr_data:
        # QR data provided directly (web frontend or ESP32 self-scan) — skip camera
        qr_text = payload.qr_data.strip()
        logger.info("CHECK-IN: QR data provided directly: %s", qr_text[:80])
        try:
            qr_payload_parsed = QRPayload.from_json(qr_text)
            booking_id = qr_payload_parsed.booking_id
            user_id = qr_payload_parsed.user_id
            logger.info(
                "CHECK-IN: QR parsed → booking=%s, user=%s", booking_id, user_id
            )
        except QRReadError as exc:
            logger.warning("CHECK-IN: QR parse failed: %s", exc)
            return ESP32Response(
                success=False,
                event=GateEvent.CHECK_IN_FAILED,
                barrier_action=BarrierAction.CLOSE,
                message=f"❌ QR không hợp lệ: {exc}",
                gate_id=gate_id,
                processing_time_ms=(time.time() - t0) * 1000,
            )
    else:
        # No QR data and no camera available in simulation mode
        logger.warning("CHECK-IN: No qr_data provided and no camera available")
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_IN_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message="❌ Thiếu QR data. Vui lòng cung cấp qr_data trong request.",
            gate_id=gate_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # ── Step 2: Fetch booking & validate ─────────────────────────────── #
    try:
        booking = await _get_booking(booking_id, user_id)
    except HTTPException as exc:
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_IN_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ Booking không hợp lệ: {exc.detail}",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Validate booking status
    check_in_status = booking.get("checkInStatus", booking.get("check_in_status", ""))
    if check_in_status != "not_checked_in":
        status_map = {
            "checked_in": "đã check-in rồi",
            "checked_out": "đã check-out rồi",
            "cancelled": "đã bị huỷ",
            "no_show": "đã bị đánh dấu no-show",
        }
        msg = status_map.get(check_in_status, f"trạng thái: {check_in_status}")
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_IN_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ Booking {msg}. Không thể check-in.",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Validate time window — allow 15 min early
    import dateutil.parser as dp

    try:
        start_time = dp.parse(booking.get("startTime", booking.get("start_time", "")))
        now = datetime.now(tz=timezone.utc)
        earliest = start_time - timedelta(minutes=CHECK_IN_EARLY_MINUTES)
        if now < earliest:
            remaining = int((earliest - now).total_seconds() / 60)
            return ESP32Response(
                success=False,
                event=GateEvent.CHECK_IN_FAILED,
                barrier_action=BarrierAction.CLOSE,
                message=f"❌ Chưa đến giờ check-in. Còn {remaining} phút.",
                gate_id=gate_id,
                booking_id=booking_id,
                processing_time_ms=(time.time() - t0) * 1000,
            )
    except Exception:
        pass  # Skip time check if parse fails

    # Check payment for online bookings
    payment_method = booking.get("paymentMethod", booking.get("payment_method", ""))
    if payment_method == "online":
        is_paid = await _check_payment_status(booking)
        if not is_paid:
            return ESP32Response(
                success=False,
                event=GateEvent.CHECK_IN_FAILED,
                barrier_action=BarrierAction.CLOSE,
                message="❌ Booking chưa thanh toán. Vui lòng thanh toán trước.",
                gate_id=gate_id,
                booking_id=booking_id,
                processing_time_ms=(time.time() - t0) * 1000,
            )

    # ── Step 3: Capture plate image ── #
    vehicle_info = booking.get("vehicle", {})
    booking_plate_raw = (
        vehicle_info.get("licensePlate", "")
        or booking.get("vehicleLicensePlate", "")
        or booking.get("vehicle_license_plate", "")
    )
    booking_plate = _normalize_plate(booking_plate_raw)

    # --- Capture plate from virtual ANPR camera (or fallback) ---
    _virtual_cam_id = "virtual-anpr-entry"
    plate_image_bytes: bytes | None = None
    plate_from_real_camera = False

    # Try virtual camera first
    with _buffer_lock:
        _vf = _virtual_frame_buffer.get(_virtual_cam_id)
    if _vf and (time.monotonic() - _vf.timestamp) < _STALE_THRESHOLD:
        plate_image_bytes = _vf.jpeg_data
        plate_from_real_camera = (
            True  # treat virtual camera as "real" for plate matching
        )
        logger.info("CHECK-IN: Using virtual camera frame from %s", _virtual_cam_id)
    else:
        # Fallback: try real RTSP camera
        plate_url = payload.plate_camera_url or _get_camera_url("plate")
        try:
            capture = get_camera_capture()
            frame = await capture.capture_frame(plate_url, retries=1)
            _, buf = cv2.imencode(".jpg", frame)
            plate_image_bytes = buf.tobytes()
            plate_from_real_camera = True
            logger.info("CHECK-IN: Captured plate from real camera: %s", plate_url)
        except Exception as exc:
            logger.warning(
                "CHECK-IN: Real plate camera failed: %s — using test image", exc
            )
            _static_plate_img = _LOCAL_IMAGES / "51A-224.56.jpg"
            if _static_plate_img.exists():
                plate_image_bytes = _static_plate_img.read_bytes()
                logger.info("CHECK-IN: Fallback to static plate image")

    # Save plate image to disk for records
    saved_path: Optional[str] = None
    if plate_image_bytes:
        saved_path = _save_plate_image(plate_image_bytes, booking_id, "checkin")
        if saved_path:
            logger.info("CHECK-IN: Plate image saved to %s", saved_path)

    # ── Step 4: OCR plate & compare ──────────────────────────────────── #

    ocr_plate = ""
    plate_confidence = 0.0

    if plate_image_bytes:
        pipeline = _plate_pipeline()
        plate_result = pipeline.process(plate_image_bytes, debug_id=booking_id[:8] if booking_id else "")

        if plate_result.decision in [
            PlateReadDecision.NOT_FOUND,
            PlateReadDecision.BLURRY,
        ]:
            # Only block if from real camera; test images may not have a plate
            if plate_from_real_camera:
                _log_prediction(
                    db,
                    "esp32_checkin_plate_fail",
                    {"booking_id": booking_id, "decision": plate_result.decision},
                    {},
                    0.0,
                    time.time() - t0,
                )
                return ESP32Response(
                    success=False,
                    event=GateEvent.CHECK_IN_FAILED,
                    barrier_action=BarrierAction.CLOSE,
                    message="❌ Không đọc được biển số xe. Vui lòng tiến gần camera.",
                    gate_id=gate_id,
                    booking_id=booking_id,
                    processing_time_ms=(time.time() - t0) * 1000,
                )
            else:
                logger.info(
                    "Plate read failed on test image — skipping plate verification"
                )
        else:
            ocr_plate = _normalize_plate(plate_result.plate_text)
            plate_confidence = plate_result.confidence

            # Only enforce plate match when using REAL camera
            if (
                plate_from_real_camera
                and booking_plate
                and not _plates_match(ocr_plate, booking_plate)
            ):
                _log_prediction(
                    db,
                    "esp32_checkin_plate_mismatch",
                    {
                        "booking_id": booking_id,
                        "ocr": ocr_plate,
                        "booking": booking_plate,
                    },
                    {"match": False},
                    plate_confidence,
                    time.time() - t0,
                )
                return ESP32Response(
                    success=False,
                    event=GateEvent.CHECK_IN_FAILED,
                    barrier_action=BarrierAction.CLOSE,
                    message=f"❌ Biển số không khớp! Đọc: {ocr_plate}, Đăng ký: {booking_plate}",
                    gate_id=gate_id,
                    booking_id=booking_id,
                    plate_text=ocr_plate,
                    processing_time_ms=(time.time() - t0) * 1000,
                )
            elif not plate_from_real_camera:
                logger.info(
                    "Plate mismatch skipped (test image): OCR=%s, booking=%s",
                    ocr_plate,
                    booking_plate,
                )
    else:
        logger.info("Plate check skipped (no image available)")

    # ── Step 5: Call booking-service checkin ──────────────────────────── #
    checkin_resp = await _call_booking_checkin(booking_id, user_id)
    if checkin_resp["status_code"] not in (200, 201):
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_IN_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ Lỗi check-in: {checkin_resp['data']}",
            gate_id=gate_id,
            booking_id=booking_id,
            plate_text=ocr_plate,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Update slot status to occupied
    slot_id = booking.get("slotId", booking.get("slot_id"))
    if slot_id:
        await _update_slot_status(str(slot_id), "occupied")

    proc_time = (time.time() - t0) * 1000
    _log_prediction(
        db,
        "esp32_checkin_success",
        {"booking_id": booking_id, "ocr": ocr_plate, "gate_id": gate_id},
        {"match": True, "barrier": "open"},
        plate_confidence,
        proc_time / 1000,
    )

    # Broadcast event
    await _broadcast_gate_event(
        "gate.check_in",
        {
            "booking_id": booking_id,
            "gate_id": gate_id,
            "plate": ocr_plate,
            "message": "Check-in thành công",
        },
    )

    # Broadcast Unity vehicle spawn command
    checkin_data = (
        checkin_resp.get("data", {}) if isinstance(checkin_resp, dict) else {}
    )
    booking_data = checkin_data.get("booking", checkin_data)
    car_slot_info = booking_data.get("carSlot") or booking_data.get("car_slot") or {}
    spawned_slot_code = (
        car_slot_info.get("code") if isinstance(car_slot_info, dict) else None
    )
    if not spawned_slot_code:
        _bk_car_slot = booking.get("carSlot") or booking.get("car_slot") or {}
        spawned_slot_code = (_bk_car_slot.get("code", "") if isinstance(_bk_car_slot, dict) else "") or "A-01"
    vehicle_info = booking.get("vehicle", {})
    spawned_vehicle_type = (
        vehicle_info.get("vehicleType") or vehicle_info.get("vehicle_type") or "Car"
    )
    await _broadcast_unity_spawn(
        booking_id=booking_id,
        plate=ocr_plate or booking_plate or "",
        slot_code=spawned_slot_code,
        vehicle_type=spawned_vehicle_type,
        qr_data=qr_text,
    )

    display_plate = ocr_plate or booking_plate or "(không rõ)"
    return ESP32Response(
        success=True,
        event=GateEvent.CHECK_IN_SUCCESS,
        barrier_action=BarrierAction.OPEN,
        message=f"✅ Check-in thành công! Biển số: {display_plate}",
        gate_id=gate_id,
        booking_id=booking_id,
        plate_text=ocr_plate or booking_plate,
        processing_time_ms=proc_time,
        plate_image_url=f"/ai/images/{Path(saved_path).name}" if saved_path else None,
        details=checkin_resp["data"],
    )


# ── ESP32 CHECK-OUT ENDPOINT ─────────────────────────────────────────────── #


@router.post("/check-out/", response_model=ESP32Response)
async def esp32_check_out(
    payload: ESP32CheckOutRequest,
    db: Session = Depends(get_db),
) -> ESP32Response:
    """ESP32 gate-out check-out flow with PAYMENT ENFORCEMENT.

    Flow:
      1. Get QR data (from payload or camera)
      2. Validate booking status == checked_in
      3. Capture plate → OCR → verify match (fallback to test image)
      4. Check payment_status == completed
         - If not paid → AWAITING_PAYMENT (barrier stays closed)
      5. Call booking-service checkout
      6. Release slot → barrier OPEN
         ESP32 reads barrier_action and sends OPEN_2 via UART to Arduino

    Args:
        payload: ESP32 check-out request.
        db: Database session.

    Returns:
        ESP32Response with barrier action. Barrier ONLY opens if paid.
    """
    t0 = time.time()
    gate_id = payload.gate_id

    # Auto-register this ESP32 so it appears in /devices list
    _auto_register_device(gate_id)

    # ── Step 1: Get QR data (direct or camera scan) ────────────────── #
    qr_text: str = ""
    booking_id: str = ""
    user_id: str = "system"

    if payload.qr_data:
        # QR data provided directly — skip camera
        qr_text = payload.qr_data.strip()
        logger.info("CHECK-OUT: QR data provided directly: %s", qr_text[:80])
        try:
            qr_payload_parsed = QRPayload.from_json(qr_text)
            booking_id = qr_payload_parsed.booking_id
            user_id = qr_payload_parsed.user_id
            logger.info(
                "CHECK-OUT: QR parsed → booking=%s, user=%s", booking_id, user_id
            )
        except QRReadError as exc:
            logger.warning("CHECK-OUT: QR parse failed: %s", exc)
            return ESP32Response(
                success=False,
                event=GateEvent.CHECK_OUT_FAILED,
                barrier_action=BarrierAction.CLOSE,
                message=f"❌ QR không hợp lệ: {exc}",
                gate_id=gate_id,
                processing_time_ms=(time.time() - t0) * 1000,
            )
    else:
        # No QR data and no camera available in simulation mode
        logger.warning("CHECK-OUT: No qr_data provided and no camera available")
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_OUT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message="❌ Thiếu QR data. Vui lòng cung cấp qr_data trong request.",
            gate_id=gate_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # ── Step 2: Fetch booking ────────────────────────────────────────── #
    try:
        booking = await _get_booking(booking_id, user_id)
    except HTTPException as exc:
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_OUT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ {exc.detail}",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    check_in_status = booking.get("checkInStatus", booking.get("check_in_status", ""))
    if check_in_status != "checked_in":
        status_map = {
            "not_checked_in": "chưa check-in",
            "checked_out": "đã check-out rồi",
            "cancelled": "đã bị huỷ",
            "no_show": "no-show",
        }
        msg = status_map.get(check_in_status, f"trạng thái: {check_in_status}")
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_OUT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ Booking {msg}.",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # ── Step 3: Plate verification ── #
    vehicle_info = booking.get("vehicle", {})
    booking_plate_raw = (
        vehicle_info.get("licensePlate", "")
        or booking.get("vehicleLicensePlate", "")
        or booking.get("vehicle_license_plate", "")
    )
    booking_plate = _normalize_plate(booking_plate_raw)

    # --- Capture plate from virtual ANPR camera (or fallback) ---
    _virtual_cam_id = "virtual-anpr-exit"
    plate_image_bytes: bytes | None = None
    plate_from_real_camera = False

    # Try virtual camera first
    with _buffer_lock:
        _vf = _virtual_frame_buffer.get(_virtual_cam_id)
    if _vf and (time.monotonic() - _vf.timestamp) < _STALE_THRESHOLD:
        plate_image_bytes = _vf.jpeg_data
        plate_from_real_camera = (
            True  # treat virtual camera as "real" for plate matching
        )
        logger.info("CHECK-OUT: Using virtual camera frame from %s", _virtual_cam_id)
    else:
        # Fallback: try real RTSP camera
        plate_url = payload.plate_camera_url or _get_camera_url("plate")
        try:
            capture = get_camera_capture()
            frame = await capture.capture_frame(plate_url, retries=1)
            _, buf = cv2.imencode(".jpg", frame)
            plate_image_bytes = buf.tobytes()
            plate_from_real_camera = True
            logger.info("CHECK-OUT: Captured plate from real camera: %s", plate_url)
        except Exception as exc:
            logger.warning(
                "CHECK-OUT: Real plate camera failed: %s — using test image", exc
            )
            _static_plate_img = _LOCAL_IMAGES / "51A-224.56.jpg"
            if _static_plate_img.exists():
                plate_image_bytes = _static_plate_img.read_bytes()
                logger.info("CHECK-OUT: Fallback to static plate image")

    # Save plate image to disk for records
    saved_path: Optional[str] = None
    if plate_image_bytes:
        saved_path = _save_plate_image(plate_image_bytes, booking_id, "checkout")
        if saved_path:
            logger.info("CHECK-OUT: Plate image saved to %s", saved_path)

    ocr_plate = ""
    plate_confidence = 0.0

    if plate_image_bytes:
        pipeline = _plate_pipeline()
        plate_result = pipeline.process(plate_image_bytes, debug_id=booking_id[:8] if booking_id else "")

        if plate_result.decision not in [
            PlateReadDecision.NOT_FOUND,
            PlateReadDecision.BLURRY,
        ]:
            ocr_plate = _normalize_plate(plate_result.plate_text)
            plate_confidence = plate_result.confidence

            # Only enforce plate match when using REAL camera
            if (
                plate_from_real_camera
                and booking_plate
                and not _plates_match(ocr_plate, booking_plate)
            ):
                return ESP32Response(
                    success=False,
                    event=GateEvent.CHECK_OUT_FAILED,
                    barrier_action=BarrierAction.CLOSE,
                    message=f"❌ Biển số không khớp! Đọc: {ocr_plate}, Đăng ký: {booking_plate}",
                    gate_id=gate_id,
                    booking_id=booking_id,
                    plate_text=ocr_plate,
                    processing_time_ms=(time.time() - t0) * 1000,
                )
            elif not plate_from_real_camera:
                logger.info(
                    "CHECK-OUT: Plate mismatch skipped (test image): OCR=%s, booking=%s",
                    ocr_plate,
                    booking_plate,
                )
    else:
        logger.info("Plate check skipped at checkout (no image available)")

    # ── Step 4: PAYMENT ENFORCEMENT ──────────────────────────────────── #
    is_paid = await _check_payment_status(booking)
    booking_price = float(booking.get("price", 0))

    if not is_paid:
        _log_prediction(
            db,
            "esp32_checkout_awaiting_payment",
            {"booking_id": booking_id, "gate_id": gate_id},
            {"paid": False, "amount": booking_price},
            0.0,
            time.time() - t0,
        )
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_OUT_AWAITING_PAYMENT,
            barrier_action=BarrierAction.CLOSE,
            message=f"⏳ Vui lòng thanh toán {booking_price:,.0f}đ trước khi ra.",
            gate_id=gate_id,
            booking_id=booking_id,
            plate_text=ocr_plate or booking_plate,
            amount_due=booking_price,
            amount_paid=0.0,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # ── Step 5: Call booking-service checkout ─────────────────────────── #
    checkout_resp = await _call_booking_checkout(booking_id, user_id)
    if checkout_resp["status_code"] not in (200, 201):
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_OUT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ Lỗi checkout: {checkout_resp['data']}",
            gate_id=gate_id,
            booking_id=booking_id,
            plate_text=ocr_plate or booking_plate,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Step 6: Release slot
    slot_id = booking.get("slotId", booking.get("slot_id"))
    if slot_id:
        await _update_slot_status(str(slot_id), "available")

    checkout_data = checkout_resp["data"]
    total_amount = float(
        checkout_data.get("totalAmount", checkout_data.get("total_amount", 0))
    )
    late_fee = float(checkout_data.get("lateFee", checkout_data.get("late_fee", 0)))

    proc_time = (time.time() - t0) * 1000
    _log_prediction(
        db,
        "esp32_checkout_success",
        {"booking_id": booking_id, "ocr": ocr_plate, "gate_id": gate_id},
        {"paid": True, "total": total_amount, "late_fee": late_fee},
        plate_confidence,
        proc_time / 1000,
    )

    await _broadcast_gate_event(
        "gate.check_out",
        {
            "booking_id": booking_id,
            "gate_id": gate_id,
            "plate": ocr_plate or booking_plate,
            "total_amount": total_amount,
            "message": "Check-out thành công",
        },
    )

    msg = f"✅ Check-out thành công! Biển số: {ocr_plate or booking_plate}"
    if late_fee > 0:
        msg += f"\n⚠️ Phí phạt quá giờ: {late_fee:,.0f}đ"
    msg += f"\nTổng: {total_amount:,.0f}đ"

    return ESP32Response(
        success=True,
        event=GateEvent.CHECK_OUT_SUCCESS,
        barrier_action=BarrierAction.OPEN,
        message=msg,
        gate_id=gate_id,
        booking_id=booking_id,
        plate_text=ocr_plate or booking_plate,
        amount_due=total_amount,
        amount_paid=total_amount,
        processing_time_ms=proc_time,
        plate_image_url=f"/ai/images/{Path(saved_path).name}" if saved_path else None,
        details=checkout_data,
    )


# ── ESP32 VERIFY-SLOT ENDPOINT ───────────────────────────────────────────── #


@router.post("/verify-slot/", response_model=ESP32Response)
async def esp32_verify_slot(
    payload: ESP32VerifySlotRequest,
    db: Session = Depends(get_db),
) -> ESP32Response:
    """Verify that a vehicle at a parking slot matches the booking.

    Flow:
      1. ESP32 button at slot → capture QR from driver's phone
      2. Decode QR → get booking_id
      3. Fetch booking → check booking.slot_code == physical slot_code
      4. Return match/mismatch

    Args:
        payload: Slot verification request.
        db: Database session.

    Returns:
        ESP32Response indicating match or mismatch.
    """
    t0 = time.time()
    gate_id = payload.gate_id
    slot_code = payload.slot_code
    zone_id = payload.zone_id

    # Auto-register this ESP32 so it appears in /devices list
    _auto_register_device(gate_id)

    # Get QR data (direct or camera scan)
    booking_id: Optional[str] = None
    user_id: Optional[str] = None

    if payload.qr_data:
        # QR data provided directly — skip camera
        qr_text = payload.qr_data.strip()
        logger.info("VERIFY-SLOT: QR data provided directly: %s", qr_text[:80])
        try:
            qr_payload = QRPayload.from_json(qr_text)
            booking_id = qr_payload.booking_id
            user_id = qr_payload.user_id
            logger.info(
                "VERIFY-SLOT: QR parsed → booking=%s, user=%s", booking_id, user_id
            )
        except QRReadError as exc:
            logger.warning("VERIFY-SLOT: QR parse failed: %s", exc)
            return ESP32Response(
                success=False,
                event=GateEvent.VERIFY_SLOT_FAILED,
                barrier_action=BarrierAction.CLOSE,
                message=f"❌ QR không hợp lệ: {exc}",
                gate_id=gate_id,
                processing_time_ms=(time.time() - t0) * 1000,
            )
    else:
        # No QR data and no camera available in simulation mode
        logger.warning("VERIFY-SLOT: No qr_data provided and no camera available")
        return ESP32Response(
            success=False,
            event=GateEvent.VERIFY_SLOT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message="❌ Thiếu QR data. Vui lòng cung cấp qr_data trong request.",
            gate_id=gate_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Fetch booking
    try:
        booking = await _get_booking(booking_id, user_id)
    except HTTPException as exc:
        return ESP32Response(
            success=False,
            event=GateEvent.VERIFY_SLOT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ {exc.detail}",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Verify booking is checked-in
    check_in_status = booking.get("checkInStatus", booking.get("check_in_status", ""))
    if check_in_status != "checked_in":
        return ESP32Response(
            success=False,
            event=GateEvent.VERIFY_SLOT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message="❌ Booking chưa check-in hoặc đã hoàn thành.",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Verify slot match
    car_slot = booking.get("carSlot") or booking.get("car_slot") or {}
    booking_slot = (car_slot.get("code", "") if isinstance(car_slot, dict) else "") or booking.get("slotCode", booking.get("slot_code", ""))
    booking_zone = (car_slot.get("zoneId", "") if isinstance(car_slot, dict) else "") or booking.get("zoneId", booking.get("zone_id", ""))

    slot_match = booking_slot.upper().strip() == slot_code.upper().strip()
    zone_match = str(booking_zone) == str(zone_id)

    if not slot_match or not zone_match:
        _log_prediction(
            db,
            "esp32_verify_slot_mismatch",
            {
                "booking_id": booking_id,
                "physical_slot": slot_code,
                "booking_slot": booking_slot,
            },
            {"match": False},
            0.0,
            time.time() - t0,
        )
        return ESP32Response(
            success=False,
            event=GateEvent.VERIFY_SLOT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ Sai ô đậu! Đặt: {booking_slot}, Thực tế: {slot_code}. Vui lòng di chuyển đúng ô.",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
            details={"booking_slot": booking_slot, "physical_slot": slot_code},
        )

    proc_time = (time.time() - t0) * 1000
    _log_prediction(
        db,
        "esp32_verify_slot_success",
        {"booking_id": booking_id, "slot": slot_code},
        {"match": True},
        1.0,
        proc_time / 1000,
    )

    return ESP32Response(
        success=True,
        event=GateEvent.VERIFY_SLOT_SUCCESS,
        barrier_action=BarrierAction.OPEN,
        message=f"✅ Đúng ô đậu {slot_code}. Chào mừng!",
        gate_id=gate_id,
        booking_id=booking_id,
        processing_time_ms=proc_time,
    )


# ── CASH PAYMENT ENDPOINT ────────────────────────────────────────────────── #


@router.post("/cash-payment/", response_model=ESP32Response)
async def esp32_cash_payment(
    payload: CashPaymentRequest,
    db: Session = Depends(get_db),
) -> ESP32Response:
    """Process cash payment at exit gate.

    Each call represents one banknote insertion.
    Uses Redis to track running total for the booking.

    Flow:
      1. Capture cash image from camera
      2. AI detect denomination
      3. Add to running total (Redis session)
      4. If total >= amount_due → mark payment completed → open barrier
      5. Else → return remaining amount

    Args:
        payload: Cash payment request with booking_id.
        db: Database session.

    Returns:
        ESP32Response with payment progress and barrier action.
    """
    t0 = time.time()
    gate_id = payload.gate_id
    booking_id = payload.booking_id

    # Fetch booking to get amount
    try:
        booking = await _get_booking(booking_id, "system")
    except HTTPException as exc:
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_OUT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message=f"❌ {exc.detail}",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    amount_due = float(booking.get("price", 0))

    # Capture or decode cash image
    capture = get_camera_capture()
    cash_image_bytes: Optional[bytes] = None

    if payload.camera_url:
        try:
            cash_image_bytes = await capture.capture_frame_bytes(payload.camera_url)
        except CameraCaptureError as exc:
            return ESP32Response(
                success=False,
                event=GateEvent.CHECK_OUT_FAILED,
                barrier_action=BarrierAction.CLOSE,
                message=f"❌ Lỗi camera tiền: {exc}",
                gate_id=gate_id,
                booking_id=booking_id,
                processing_time_ms=(time.time() - t0) * 1000,
            )
    elif payload.image_base64:
        import base64

        try:
            cash_image_bytes = base64.b64decode(payload.image_base64)
        except Exception:
            return ESP32Response(
                success=False,
                event=GateEvent.CHECK_OUT_FAILED,
                barrier_action=BarrierAction.CLOSE,
                message="❌ Base64 ảnh không hợp lệ.",
                gate_id=gate_id,
                booking_id=booking_id,
                processing_time_ms=(time.time() - t0) * 1000,
            )

    if not cash_image_bytes:
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_OUT_FAILED,
            barrier_action=BarrierAction.CLOSE,
            message="❌ Không có ảnh tiền mặt.",
            gate_id=gate_id,
            booking_id=booking_id,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Detect denomination using banknote pipeline
    try:
        from app.engine.pipeline import PipelineDecision, get_banknote_pipeline

        # Convert bytes to numpy array for pipeline
        nparr = np.frombuffer(cash_image_bytes, np.uint8)
        cash_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if cash_img is None:
            raise ValueError("Cannot decode cash image bytes")

        bnk_pipeline = get_banknote_pipeline()
        result = bnk_pipeline.process(cash_img)
        denomination = (
            int(result.denomination)
            if result.denomination and result.decision == PipelineDecision.ACCEPT
            else 0
        )
    except Exception as exc:
        logger.warning("Cash detection failed: %s", exc)
        denomination = 0

    if denomination <= 0:
        return ESP32Response(
            success=False,
            event=GateEvent.CHECK_OUT_AWAITING_PAYMENT,
            barrier_action=BarrierAction.CLOSE,
            message="❌ Không nhận diện được tiền. Vui lòng thử lại.",
            gate_id=gate_id,
            booking_id=booking_id,
            amount_due=amount_due,
            amount_paid=0.0,
            processing_time_ms=(time.time() - t0) * 1000,
        )

    # Track running total in-memory (Redis would be better in production)
    # For prototype, use a simple dict
    from app.engine.cash_session import get_cash_session_manager

    session_mgr = get_cash_session_manager()
    new_total = session_mgr.add_payment(booking_id, denomination)

    remaining = max(0, amount_due - new_total)
    proc_time = (time.time() - t0) * 1000

    _log_prediction(
        db,
        "esp32_cash_payment",
        {
            "booking_id": booking_id,
            "denomination": denomination,
            "running_total": new_total,
        },
        {"amount_due": amount_due, "remaining": remaining},
        1.0,
        proc_time / 1000,
    )

    if new_total >= amount_due:
        # Payment complete — mark in booking service
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.patch(
                    f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/",
                    headers={
                        "X-Gateway-Secret": GATEWAY_SECRET,
                        "X-User-ID": "system",
                        "Content-Type": "application/json",
                    },
                    json={"payment_status": "completed"},
                )
        except Exception as exc:
            logger.warning("Failed to update payment status: %s", exc)

        change = new_total - amount_due
        session_mgr.clear_session(booking_id)

        msg = f"✅ Thanh toán tiền mặt hoàn tất! Tổng: {new_total:,.0f}đ"
        if change > 0:
            msg += f"\n💰 Tiền thừa: {change:,.0f}đ"

        return ESP32Response(
            success=True,
            event=GateEvent.CHECK_OUT_SUCCESS,
            barrier_action=BarrierAction.OPEN,
            message=msg,
            gate_id=gate_id,
            booking_id=booking_id,
            amount_due=amount_due,
            amount_paid=new_total,
            processing_time_ms=proc_time,
            details={"denomination": denomination, "change": change},
        )

    # Still needs more cash
    return ESP32Response(
        success=False,
        event=GateEvent.CHECK_OUT_AWAITING_PAYMENT,
        barrier_action=BarrierAction.CLOSE,
        message=f"💵 Đã nhận {denomination:,.0f}đ. Tổng: {new_total:,.0f}đ / {amount_due:,.0f}đ. Còn thiếu: {remaining:,.0f}đ",
        gate_id=gate_id,
        booking_id=booking_id,
        amount_due=amount_due,
        amount_paid=new_total,
        processing_time_ms=proc_time,
        details={
            "denomination": denomination,
            "running_total": new_total,
            "remaining": remaining,
        },
    )


# ── STATUS ENDPOINT ──────────────────────────────────────────────────────── #


@router.get("/status/")
async def esp32_status() -> dict:
    """Health check + camera connectivity + test images status.

    Returns:
        Status of cameras, test images, and service health.
    """
    cameras_status: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{PARKING_SERVICE_URL}/parking/cameras/",
                headers={"X-Gateway-Secret": GATEWAY_SECRET},
            )
            if resp.status_code == 200:
                data = resp.json()
                cameras = data.get("results", data) if isinstance(data, dict) else data
                capture = get_camera_capture()
                for cam in cameras:
                    stream = cam.get("streamUrl") or cam.get("stream_url") or ""
                    name = cam.get("name", "unknown")
                    reachable = False
                    if stream:
                        try:
                            await capture.capture_frame(stream, retries=1)
                            reachable = True
                        except Exception:
                            pass
                    cameras_status.append(
                        {
                            "name": name,
                            "url": stream,
                            "reachable": reachable,
                        }
                    )
    except Exception as exc:
        logger.warning("Failed to check cameras: %s", exc)

    test_images: list[str] = []
    if TEST_IMAGES_DIR.exists():
        test_images = [
            f.name
            for f in TEST_IMAGES_DIR.glob("*")
            if f.suffix.lower() in (".jpg", ".jpeg", ".png")
        ]

    return {
        "status": "healthy",
        "service": "esp32-integration",
        "cameras": cameras_status,
        "test_images": test_images,
        "test_images_dir": str(TEST_IMAGES_DIR),
        "fallback_mode": (
            len(cameras_status) == 0 or all(not c["reachable"] for c in cameras_status)
        ),
    }


# ══════════════════════════════════════════════════════════════════════════ #
#  ESP32 Device Management — Registration, Heartbeat, Logs                  #
# ══════════════════════════════════════════════════════════════════════════ #


def _is_device_online(device: dict) -> bool:
    """Check if a device is online based on last_seen timestamp."""
    elapsed = (datetime.now(timezone.utc) - device["last_seen"]).total_seconds()
    return elapsed <= DEVICE_OFFLINE_TIMEOUT_S


def _build_device_response(device_id: str, device: dict) -> ESP32DeviceResponse:
    """Build an ESP32DeviceResponse from the internal device dict."""
    return ESP32DeviceResponse(
        device_id=device_id,
        ip=device["ip"],
        firmware=device["firmware"],
        status=device["status"],
        gpio_config=device.get("gpio_config"),
        registered_at=device["registered_at"],
        last_seen=device["last_seen"],
        is_online=_is_device_online(device),
        wifi_rssi=device.get("wifi_rssi"),
        log_count=len(device.get("logs", [])),
    )


# ── POST /register — ESP32 registers on boot ────────────────────────────── #


@router.post(
    "/register",
    response_model=ESP32AckResponse,
    summary="ESP32 registers itself on boot",
)
async def esp32_register(body: ESP32RegisterRequest) -> ESP32AckResponse:
    """Called by ESP32 when it boots up and connects to WiFi.

    Stores the device in the in-memory registry. If the device_id already
    exists, its info is updated (re-registration after reboot).
    """
    now = datetime.now(timezone.utc)
    gpio_dict = body.gpio_config.model_dump() if body.gpio_config else None

    _esp32_devices[body.device_id] = {
        "ip": body.ip,
        "firmware": body.firmware,
        "status": "ready",
        "gpio_config": gpio_dict,
        "registered_at": now,
        "last_seen": now,
        "wifi_rssi": None,
        "logs": _esp32_devices.get(body.device_id, {}).get(
            "logs", deque(maxlen=MAX_LOGS_PER_DEVICE)
        ),
    }

    logger.info(
        "ESP32 registered: device_id=%s ip=%s firmware=%s",
        body.device_id,
        body.ip,
        body.firmware,
    )
    return ESP32AckResponse(
        success=True,
        message=f"Device '{body.device_id}' registered successfully.",
    )


# ── POST /heartbeat — ESP32 periodic keepalive ──────────────────────────── #


@router.post(
    "/heartbeat",
    response_model=ESP32AckResponse,
    summary="ESP32 periodic heartbeat",
)
async def esp32_heartbeat(body: ESP32HeartbeatRequest) -> ESP32AckResponse:
    """Called periodically by ESP32 (e.g. every 10s) to report it's alive."""
    device = _esp32_devices.get(body.device_id)
    if device is None:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{body.device_id}' not registered. Call /register first.",
        )

    device["last_seen"] = datetime.now(timezone.utc)
    device["status"] = body.status
    if body.wifi_rssi is not None:
        device["wifi_rssi"] = body.wifi_rssi

    return ESP32AckResponse(success=True, message="Heartbeat received.")


# ── POST /log — ESP32 sends log messages ────────────────────────────────── #


@router.post(
    "/log",
    response_model=ESP32AckResponse,
    summary="ESP32 sends a log message",
)
async def esp32_log(body: ESP32LogRequest) -> ESP32AckResponse:
    """Store a log entry from the ESP32 in a circular buffer (last N entries)."""
    device = _esp32_devices.get(body.device_id)
    if device is None:
        # Auto-register with minimal info so logs aren't lost
        _esp32_devices[body.device_id] = {
            "ip": "unknown",
            "firmware": "unknown",
            "status": "unknown",
            "gpio_config": None,
            "registered_at": datetime.now(timezone.utc),
            "last_seen": datetime.now(timezone.utc),
            "wifi_rssi": None,
            "logs": deque(maxlen=MAX_LOGS_PER_DEVICE),
        }
        device = _esp32_devices[body.device_id]

    device["last_seen"] = datetime.now(timezone.utc)
    device["logs"].append(
        {
            "timestamp": datetime.now(timezone.utc),
            "level": body.level,
            "message": body.message,
        }
    )

    log_fn = {
        "debug": logger.debug,
        "info": logger.info,
        "warn": logger.warning,
        "error": logger.error,
    }.get(body.level, logger.info)
    log_fn("ESP32 [%s] %s", body.device_id, body.message)

    return ESP32AckResponse(success=True, message="Log recorded.")


# ── GET /devices — Frontend: list all registered ESP32 devices ───────────── #


@router.get(
    "/devices",
    response_model=ESP32DeviceListResponse,
    summary="List all registered ESP32 devices",
)
async def esp32_list_devices() -> ESP32DeviceListResponse:
    """Return all registered ESP32 devices with current online/offline status.

    Requires gateway auth (called by the frontend, not by ESP32 directly).
    """
    devices = [_build_device_response(did, dev) for did, dev in _esp32_devices.items()]
    return ESP32DeviceListResponse(count=len(devices), devices=devices)


# ── GET /devices/{device_id}/logs — Frontend: get logs for one device ────── #


@router.get(
    "/devices/{device_id}/logs",
    response_model=ESP32DeviceLogsResponse,
    summary="Get logs for a specific ESP32 device",
)
async def esp32_device_logs(device_id: str) -> ESP32DeviceLogsResponse:
    """Return the last N log entries for the given device.

    Requires gateway auth (called by the frontend, not by ESP32 directly).
    """
    device = _esp32_devices.get(device_id)
    if device is None:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{device_id}' not found.",
        )

    logs = [
        LogEntry(
            timestamp=entry["timestamp"],
            level=entry["level"],
            message=entry["message"],
        )
        for entry in device["logs"]
    ]
    return ESP32DeviceLogsResponse(
        device_id=device_id,
        count=len(logs),
        logs=logs,
    )
