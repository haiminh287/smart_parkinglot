"""
ESP32 Verify-slot business logic.

Extracted from ``app/routers/esp32.py`` — slot-level QR verification.
"""

import logging
import time
from typing import Optional

from app.engine.esp32_device_store import auto_register_device
from app.engine.qr_reader import QRPayload, QRReadError
from app.schemas.esp32 import (
    BarrierAction,
    ESP32Response,
    ESP32VerifySlotRequest,
    GateEvent,
)
from app.services.esp32_helpers import get_booking, log_prediction
from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def process_verify_slot(
    payload: ESP32VerifySlotRequest,
    db: Session,
) -> ESP32Response:
    """Verify that a vehicle at a parking slot matches the booking.

    Flow:
      1. ESP32 button at slot → capture QR from driver's phone
      2. Decode QR → get booking_id
      3. Fetch booking → check booking.slot_code == physical slot_code
      4. Return match/mismatch
    """
    t0 = time.time()
    gate_id = payload.gate_id
    slot_code = payload.slot_code
    zone_id = payload.zone_id

    auto_register_device(gate_id)

    # Get QR data
    booking_id: Optional[str] = None
    user_id: Optional[str] = None

    if payload.qr_data:
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
        booking = await get_booking(booking_id, user_id)
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
    booking_slot = (
        car_slot.get("code", "") if isinstance(car_slot, dict) else ""
    ) or booking.get("slotCode", booking.get("slot_code", ""))
    booking_zone = (
        car_slot.get("zoneId", "") if isinstance(car_slot, dict) else ""
    ) or booking.get("zoneId", booking.get("zone_id", ""))

    slot_match = booking_slot.upper().strip() == slot_code.upper().strip()
    zone_match = str(booking_zone) == str(zone_id)

    if not slot_match or not zone_match:
        log_prediction(
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
    log_prediction(
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
