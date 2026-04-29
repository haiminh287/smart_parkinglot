"""
ESP32 Check-in business logic.

Extracted from ``app/routers/esp32.py`` — the full gate-in check-in flow.
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
    ESP32CheckInRequest,
    ESP32Response,
    GateEvent,
)
from app.services.esp32_helpers import (
    TEST_IMAGES_DIR,
    broadcast_gate_event,
    broadcast_unity_spawn,
    call_booking_checkin,
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


async def process_checkin(
    payload: ESP32CheckInRequest,
    db: Session,
) -> ESP32Response:
    """ESP32 gate-in check-in flow.

    Flow:
      1. ESP32 button pressed → triggers this endpoint
      2. Open QR camera, capture frame, decode QR
      3. Fetch booking → validate status + time window
      4. Open plate camera (try real RTSP → fallback to test image)
      5. OCR plate → compare with booking plate
      6. Call booking-service checkin API
      7. Return barrier_action=open
    """
    t0 = time.time()
    gate_id = payload.gate_id

    # Auto-register this ESP32 so it appears in /devices list
    auto_register_device(gate_id)

    # ── Step 1: Get QR data (direct or camera scan) ────────────────── #
    qr_text: str = ""
    booking_id: str = ""
    user_id: str = "system"

    if payload.qr_data:
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
        booking = await get_booking(booking_id, user_id)
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

    # Check payment for online bookings
    payment_method = booking.get("paymentMethod", booking.get("payment_method", ""))
    if payment_method == "online":
        is_paid = await check_payment_status(booking)
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
    booking_plate = normalize_plate(booking_plate_raw)

    # --- Capture plate from virtual ANPR camera (or fallback) ---
    _virtual_cam_id = "virtual-anpr-entry"
    plate_image_bytes: bytes | None = None
    plate_from_real_camera = False

    # Try virtual camera first
    with _buffer_lock:
        _vf = _virtual_frame_buffer.get(_virtual_cam_id)
    if _vf and (time.monotonic() - _vf.timestamp) < _STALE_THRESHOLD:
        plate_image_bytes = _vf.jpeg_data
        plate_from_real_camera = True
        logger.info("CHECK-IN: Using virtual camera frame from %s", _virtual_cam_id)
    else:
        # Fallback: try real RTSP camera — với timeout 4s để ESP32 (30s timeout)
        # không bị chờ vô vọng khi RTSP URL default không reachable.
        import asyncio

        plate_url = payload.plate_camera_url or get_camera_url("plate")
        if plate_url and not plate_url.startswith(("rtsp://user:password@",)):
            try:
                capture = get_camera_capture()
                frame = await asyncio.wait_for(
                    capture.capture_frame(plate_url, retries=1),
                    timeout=4.0,
                )
                _, buf = cv2.imencode(".jpg", frame)
                plate_image_bytes = buf.tobytes()
                plate_from_real_camera = True
                logger.info("CHECK-IN: Captured plate from real camera: %s", plate_url)
            except (asyncio.TimeoutError, Exception) as exc:
                logger.warning(
                    "CHECK-IN: Real plate camera failed/timeout: %s — using test image",
                    exc,
                )
        else:
            logger.info("CHECK-IN: No usable plate camera URL — skipping to test image")

        if plate_image_bytes is None:
            _static_plate_img = TEST_IMAGES_DIR / "51A-224.56.jpg"
            if _static_plate_img.exists():
                plate_image_bytes = _static_plate_img.read_bytes()
                logger.info("CHECK-IN: Fallback to static plate image")

    # Save plate image to disk for records
    saved_path: Optional[str] = None
    if plate_image_bytes:
        saved_path = save_plate_image(plate_image_bytes, booking_id, "checkin")
        if saved_path:
            logger.info("CHECK-IN: Plate image saved to %s", saved_path)

    # ── Step 4: OCR plate & compare ──────────────────────────────────── #
    ocr_plate = ""
    plate_confidence = 0.0

    # Fast-path: không có camera thực → skip OCR hoàn toàn (không cần verify
    # plate match vì đã rõ không có ảnh thật). Tiết kiệm 15-25s EasyOCR.
    if plate_image_bytes and not plate_from_real_camera:
        logger.info("CHECK-IN: Test image mode — skip plate OCR (save ~20s)")
        ocr_plate = normalize_plate(booking_plate) if booking_plate else ""
        plate_confidence = 0.0
    elif plate_image_bytes:
        pipeline = plate_pipeline()
        plate_result = pipeline.process(
            plate_image_bytes,
            debug_id=booking_id[:8] if booking_id else "",
        )

        if plate_result.decision in [
            PlateReadDecision.NOT_FOUND,
            PlateReadDecision.BLURRY,
        ]:
            if plate_from_real_camera:
                log_prediction(
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
            ocr_plate = normalize_plate(plate_result.plate_text)
            plate_confidence = plate_result.confidence

            # Only enforce plate match when using REAL camera
            if (
                plate_from_real_camera
                and booking_plate
                and not plates_match(ocr_plate, booking_plate)
            ):
                log_prediction(
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
    checkin_resp = await call_booking_checkin(booking_id, user_id)
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

    checkin_data = (
        checkin_resp.get("data", {}) if isinstance(checkin_resp, dict) else {}
    )
    booking_data = checkin_data.get("booking", checkin_data)

    # Update slot status using latest booking-service response (fallback prefetch).
    slot_id = booking_data.get("slotId", booking_data.get("slot_id")) or booking.get(
        "slotId", booking.get("slot_id")
    )
    if slot_id:
        await update_slot_status(str(slot_id), "occupied")

    proc_time = (time.time() - t0) * 1000
    log_prediction(
        db,
        "esp32_checkin_success",
        {"booking_id": booking_id, "ocr": ocr_plate, "gate_id": gate_id},
        {"match": True, "barrier": "open"},
        plate_confidence,
        proc_time / 1000,
    )

    # Broadcast event
    await broadcast_gate_event(
        "gate.check_in",
        {
            "booking_id": booking_id,
            "gate_id": gate_id,
            "plate": ocr_plate,
            "message": "Check-in thành công",
        },
    )

    # Broadcast Unity vehicle spawn command
    car_slot_info = booking_data.get("carSlot") or booking_data.get("car_slot") or {}
    spawned_slot_code = (
        car_slot_info.get("code") if isinstance(car_slot_info, dict) else None
    )
    if not spawned_slot_code:
        _bk_car_slot = booking.get("carSlot") or booking.get("car_slot") or {}
        spawned_slot_code = (
            _bk_car_slot.get("code", "") if isinstance(_bk_car_slot, dict) else ""
        ) or "A-01"
    vehicle_info = booking.get("vehicle", {})
    spawned_vehicle_type = (
        vehicle_info.get("vehicleType") or vehicle_info.get("vehicle_type") or "Car"
    )
    await broadcast_unity_spawn(
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
