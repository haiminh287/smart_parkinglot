"""
ESP32 Cash-payment business logic.

Extracted from ``app/routers/esp32.py`` — banknote detection + running total.
"""

import base64
import logging
import time
from typing import Optional

import cv2
import httpx
import numpy as np
from app.config import settings
from app.engine.camera_capture import CameraCaptureError, get_camera_capture
from app.engine.cash_session import get_cash_session_manager
from app.engine.pipeline import PipelineDecision, get_banknote_pipeline
from app.schemas.esp32 import (
    BarrierAction,
    CashPaymentRequest,
    ESP32Response,
    GateEvent,
)
from app.services.esp32_helpers import get_booking, log_prediction
from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BOOKING_SERVICE_URL = settings.BOOKING_SERVICE_URL
GATEWAY_SECRET = settings.GATEWAY_SECRET


async def process_cash_payment(
    payload: CashPaymentRequest,
    db: Session,
) -> ESP32Response:
    """Process cash payment at exit gate.

    Each call represents one banknote insertion.
    Uses Redis-like session to track running total for the booking.

    Flow:
      1. Capture cash image from camera
      2. AI detect denomination
      3. Add to running total
      4. If total >= amount_due → mark payment completed → open barrier
      5. Else → return remaining amount
    """
    t0 = time.time()
    gate_id = payload.gate_id
    booking_id = payload.booking_id

    # Fetch booking to get amount
    try:
        booking = await get_booking(booking_id, "system")
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

    # Track running total via session manager
    session_mgr = get_cash_session_manager()
    new_total = session_mgr.add_payment(booking_id, denomination)

    remaining = max(0, amount_due - new_total)
    proc_time = (time.time() - t0) * 1000

    log_prediction(
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
        message=(
            f"💵 Đã nhận {denomination:,.0f}đ. "
            f"Tổng: {new_total:,.0f}đ / {amount_due:,.0f}đ. "
            f"Còn thiếu: {remaining:,.0f}đ"
        ),
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
