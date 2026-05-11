"""
Pydantic v2 schemas for ESP32 gate check-in / check-out / verify-slot / cash-payment.

These are the *request* and *response* models exchanged between the physical
ESP32 boards (or Unity simulator) and the AI service.  Device-management
schemas live in ``esp32_device.py``.
"""

from enum import Enum
from typing import Optional

from app.schemas.base import CamelModel
from pydantic import BaseModel, Field

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


# ── Request Schemas ──────────────────────────────────────────────────────── #


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
    # User-selected denomination (VND, e.g. 50000). Khi set → bỏ qua AI
    # scan ảnh, cộng trực tiếp vào running total.
    denomination: Optional[int] = Field(
        None, description="User-selected denomination (VND); skips AI when set"
    )


# ── Response Schema ──────────────────────────────────────────────────────── #


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
