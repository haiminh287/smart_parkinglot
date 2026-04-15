"""Shared helpers and constants for parking sub-routers."""

import logging
import re
import uuid
from typing import Optional

import httpx
from app.config import settings
from app.engine.plate_pipeline import get_plate_pipeline
from app.models.ai import PredictionLog
from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────── #
_MODEL_PATH = settings.PLATE_MODEL_PATH
BOOKING_SERVICE_URL = settings.BOOKING_SERVICE_URL
REALTIME_SERVICE_URL = settings.REALTIME_SERVICE_URL
GATEWAY_SECRET = settings.GATEWAY_SECRET


# ── Helpers ──────────────────────────────────────────────────────────────── #


def plate_pipeline():
    """Return the pre-warmed plate-detection pipeline."""
    return get_plate_pipeline(model_path=_MODEL_PATH)


def normalize_plate(text: str) -> str:
    """Normalize plate to uppercase, alphanumeric only."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def plates_match(ocr_plate: str, booking_plate: str, strict: bool = False) -> bool:
    """
    Compare OCR plate with booking plate.
    Keeps only alphanumeric characters — ignores all separators (-, ., spaces, etc.).
    """
    a = normalize_plate(ocr_plate)
    b = normalize_plate(booking_plate)
    return a == b


def extract_bbox(result) -> Optional[dict]:
    """Extract bounding box dict from PlatePipelineResult if available."""
    det = result.detection_result
    if det and det.box:
        return {
            "x1": det.box.x1,
            "y1": det.box.y1,
            "x2": det.box.x2,
            "y2": det.box.y2,
            "confidence": round(det.box.confidence, 4),
        }
    return None


async def call_booking_checkin(
    booking_id: str, user_id: str, gateway_secret: str
) -> dict:
    """Call booking-service checkin endpoint."""
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/checkin/"
    headers = {
        "X-Gateway-Secret": gateway_secret,
        "X-User-ID": user_id,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers)
        return {"status_code": resp.status_code, "data": resp.json()}


async def call_booking_checkout(
    booking_id: str, user_id: str, gateway_secret: str
) -> dict:
    """Call booking-service checkout endpoint."""
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/checkout/"
    headers = {
        "X-Gateway-Secret": gateway_secret,
        "X-User-ID": user_id,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers)
        return {"status_code": resp.status_code, "data": resp.json()}


async def get_booking(booking_id: str, user_id: str) -> dict:
    """Fetch booking details from booking-service."""
    # Normalize to dashed UUID format
    clean = booking_id.replace("-", "")
    try:
        booking_id = str(uuid.UUID(clean))
    except ValueError:
        pass
    url = f"{BOOKING_SERVICE_URL}/bookings/{booking_id}/"
    headers = {
        "X-Gateway-Secret": GATEWAY_SECRET,
        "X-User-ID": user_id,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Booking không tồn tại hoặc không có quyền truy cập. (booking_id={booking_id})",
            )
        return resp.json()


def log_prediction(
    db: Session,
    pred_type: str,
    input_data: dict,
    output_data: dict,
    confidence: float,
    proc_time: float,
):
    """Persist a prediction log entry (fire-and-forget, logs warning on failure)."""
    try:
        log = PredictionLog(
            id=str(uuid.uuid4()),
            prediction_type=pred_type,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            model_version="license-plate-finetune-v1m",
            processing_time=proc_time,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log prediction: {e}")
