"""
ESP32 Check-out business logic.

Extracted from ``app/routers/esp32.py`` — the full gate-out check-out flow
with payment enforcement.
"""

import logging
import time
from pathlib import Path
from typing import Optional

import cv2
from app.engine.camera_capture import get_camera_capture
from app.engine.esp32_device_store import auto_register_device
from app.engine.plate_pipeline import PlateReadDecision
from app.engine.qr_reader import QRPayload, QRReadError
from app.routers.camera import _STALE_THRESHOLD, _buffer_lock, _virtual_frame_buffer
from app.schemas.esp32 import (
    BarrierAction,
    ESP32CheckOutRequest,
    ESP32Response,
    GateEvent,
)
from app.services.esp32_helpers import (
    TEST_IMAGES_DIR,
    broadcast_gate_event,
    broadcast_unity_depart,
    call_booking_checkout,
    check_payment_status,
    get_booking,
    get_camera_url,
    log_prediction,
    normalize_plate,
    plate_pipeline,
    plates_match,
    save_plate_image,
    update_slot_status,
)
from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def process_checkout(
    payload: ESP32CheckOutRequest,
    db: Session,
) -> ESP32Response:
    """ESP32 gate-out check-out flow with PAYMENT ENFORCEMENT.

    Flow:
      1. Get QR data (from payload or camera)
      2. Validate booking status == checked_in
      3. Capture plate → OCR → verify match
      4. Check payment_status == completed
      5. Call booking-service checkout
      6. Release slot → barrier OPEN
    """
    t0 = time.time()
    gate_id = payload.gate_id

    auto_register_device(gate_id)

    # ── Step 1: Get QR data ────────────────────────────────────────── #
    qr_text: str = ""
    booking_id: str = ""
    user_id: str = "system"

    if payload.qr_data:
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
        booking = await get_booking(booking_id, user_id)
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
    booking_plate = normalize_plate(booking_plate_raw)

    _virtual_cam_id = "virtual-anpr-exit"
    plate_image_bytes: bytes | None = None
    plate_from_real_camera = False

    with _buffer_lock:
        _vf = _virtual_frame_buffer.get(_virtual_cam_id)
    if _vf and (time.monotonic() - _vf.timestamp) < _STALE_THRESHOLD:
        plate_image_bytes = _vf.jpeg_data
        plate_from_real_camera = True
        logger.info("CHECK-OUT: Using virtual camera frame from %s", _virtual_cam_id)
    else:
        plate_url = payload.plate_camera_url or get_camera_url("plate")
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
            _static_plate_img = TEST_IMAGES_DIR / "51A-224.56.jpg"
            if _static_plate_img.exists():
                plate_image_bytes = _static_plate_img.read_bytes()
                logger.info("CHECK-OUT: Fallback to static plate image")

    saved_path: Optional[str] = None
    if plate_image_bytes:
        saved_path = save_plate_image(plate_image_bytes, booking_id, "checkout")
        if saved_path:
            logger.info("CHECK-OUT: Plate image saved to %s", saved_path)

    ocr_plate = ""
    plate_confidence = 0.0

    if plate_image_bytes:
        pipeline_inst = plate_pipeline()
        plate_result = pipeline_inst.process(
            plate_image_bytes,
            debug_id=booking_id[:8] if booking_id else "",
        )

        if plate_result.decision not in [
            PlateReadDecision.NOT_FOUND,
            PlateReadDecision.BLURRY,
        ]:
            ocr_plate = normalize_plate(plate_result.plate_text)
            plate_confidence = plate_result.confidence

            if (
                plate_from_real_camera
                and booking_plate
                and not plates_match(ocr_plate, booking_plate)
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
    is_paid = await check_payment_status(booking)
    booking_price = float(booking.get("price", 0))

    if not is_paid:
        log_prediction(
            db,
            "esp32_checkout_awaiting_payment",
            {"booking_id": booking_id, "gate_id": gate_id},
            {"paid": False, "amount": booking_price},
            0.0,
            time.time() - t0,
        )
        # Broadcast Unity để hiện popup MoMo QR + cash banknote
        await broadcast_gate_event(
            "unity.awaiting_payment",
            {
                "booking_id": booking_id,
                "plate": ocr_plate or booking_plate,
                "amount_due": booking_price,
                "gate_id": gate_id,
                "message": f"Thanh toán {booking_price:,.0f}đ để ra bãi",
            },
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
    checkout_resp = await call_booking_checkout(booking_id, user_id)
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
        await update_slot_status(str(slot_id), "available")

    checkout_data = checkout_resp["data"]
    total_amount = float(
        checkout_data.get("totalAmount", checkout_data.get("total_amount", 0))
    )
    late_fee = float(checkout_data.get("lateFee", checkout_data.get("late_fee", 0)))

    proc_time = (time.time() - t0) * 1000
    log_prediction(
        db,
        "esp32_checkout_success",
        {"booking_id": booking_id, "ocr": ocr_plate, "gate_id": gate_id},
        {"paid": True, "total": total_amount, "late_fee": late_fee},
        plate_confidence,
        proc_time / 1000,
    )

    await broadcast_gate_event(
        "gate.check_out",
        {
            "booking_id": booking_id,
            "gate_id": gate_id,
            "plate": ocr_plate or booking_plate,
            "total_amount": total_amount,
            "message": "Check-out thành công",
        },
    )

    # Unity listens to unity.depart_vehicle → StartDeparture cho xe này.
    await broadcast_unity_depart(booking_id, ocr_plate or booking_plate)

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
