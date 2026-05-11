"""POST /check-in/ — QR + plate verification, then booking-service checkin."""

import json
import time

from app.database import get_db
from app.engine.plate_pipeline import PlateReadDecision
from app.utils.image_utils import (
    save_annotated_plate_image,
    save_debug_image,
    save_plate_image,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .helpers import (
    GATEWAY_SECRET,
    call_booking_checkin,
    extract_bbox,
    get_booking,
    log_prediction,
    normalize_plate,
    plate_pipeline,
    plates_match,
)

router = APIRouter()


@router.post("/check-in/")
async def check_in(
    image: UploadFile = File(..., description="Ảnh biển số xe"),
    qr_data: str = Form(
        ..., description='JSON từ QR code: {"booking_id":"...","user_id":"..."}'
    ),
    db: Session = Depends(get_db),
):
    """
    Check-in quy trình:
    1. Parse QR data → lấy booking_id, user_id
    2. Fetch booking → kiểm tra trạng thái, thời gian hợp lệ
    3. OCR biển số từ ảnh
    4. So khớp biển số OCR với booking.vehicle_license_plate
    5. Gọi booking-service checkin API
    6. Trả kết quả + thông báo realtime
    """
    t0 = time.time()

    # 1. Parse QR
    try:
        qr_info = json.loads(qr_data)
        booking_id = qr_info.get("booking_id") or qr_info.get("id")
        user_id = qr_info.get("user_id") or qr_info.get("userId")
        if not booking_id or not user_id:
            raise ValueError("Missing booking_id or user_id")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"❌ QR code không hợp lệ: {e}. QR phải chứa booking_id và user_id.",
        )

    # 2. Fetch booking
    booking = await get_booking(booking_id, user_id)

    # 3. Validate booking status
    check_in_status = booking.get("checkInStatus", booking.get("check_in_status", ""))
    if check_in_status not in ["not_checked_in"]:
        status_map = {
            "checked_in": "đã được check-in rồi",
            "checked_out": "đã được check-out rồi",
            "cancelled": "đã bị huỷ",
            "no_show": "đã bị đánh dấu no-show",
        }
        msg = status_map.get(
            check_in_status, f"trạng thái không hợp lệ: {check_in_status}"
        )
        raise HTTPException(
            status_code=400, detail=f"❌ Booking này {msg}. Không thể check-in."
        )

    # 4. Validate time window — allow 15 min early, no limit late
    from datetime import datetime, timedelta, timezone

    import dateutil.parser as dp

    try:
        start_time = dp.parse(booking.get("startTime", booking.get("start_time", "")))
        now = datetime.now(tz=timezone.utc)
        earliest = start_time - timedelta(minutes=15)
        if now < earliest:
            remaining = int((earliest - now).total_seconds() / 60)
            raise HTTPException(
                status_code=400,
                detail=f"❌ Chưa đến giờ check-in. Còn {remaining} phút nữa mới được vào "
                f"(bắt đầu: {start_time.strftime('%H:%M %d/%m/%Y')}).",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # If time parse fails, skip time check

    # 5. OCR plate
    contents = await image.read()
    pipeline = plate_pipeline()
    plate_result = pipeline.process(contents)

    # Save image and extract bbox
    filename = save_plate_image(contents, action="checkin", identifier=booking_id)
    plate_image_url = f"/ai/images/{filename}" if filename else None
    bbox = extract_bbox(plate_result)

    # Save annotated image with bbox overlay
    annotated_image_url = None
    if bbox and plate_result.plate_text:
        ann_file = save_annotated_plate_image(
            contents,
            bbox["x1"],
            bbox["y1"],
            bbox["x2"],
            bbox["y2"],
            plate_result.plate_text,
            plate_result.confidence,
            action="checkin",
            identifier=booking_id,
        )
        if ann_file:
            annotated_image_url = f"/ai/images/{ann_file}"

    # Always save to debug folder
    save_debug_image(
        contents,
        action="checkin",
        plate_text=plate_result.plate_text,
        confidence=plate_result.confidence,
        bbox=bbox,
        decision=plate_result.decision,
    )

    # Booking service returns vehicle as nested object with licensePlate
    vehicle_info = booking.get("vehicle", {})
    booking_plate = normalize_plate(
        vehicle_info.get("licensePlate", "") or booking.get("vehicle_license_plate", "")
    )

    # 6. Check plate match
    if plate_result.decision in [PlateReadDecision.NOT_FOUND, PlateReadDecision.BLURRY]:
        fail_output = {"plate_result": plate_result.decision}
        if filename:
            fail_output["image_path"] = filename
        log_prediction(
            db,
            "check_in_failure",
            {"booking_id": booking_id, "reason": "plate_not_readable"},
            fail_output,
            0.0,
            time.time() - t0,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "plate_unreadable",
                "message": plate_result.warning
                or "❌ Không đọc được biển số xe. Vui lòng chụp lại.",
                "decision": plate_result.decision,
                "blur_score": (
                    plate_result.ocr_result.blur_score if plate_result.ocr_result else 0
                ),
            },
        )

    ocr_plate = normalize_plate(plate_result.plate_text)
    plate_match = plates_match(ocr_plate, booking_plate)

    if not plate_match:
        mismatch_output = {"match": False}
        if filename:
            mismatch_output["image_path"] = filename
        if bbox:
            mismatch_output["bbox"] = bbox
        log_prediction(
            db,
            "check_in_failure",
            {
                "booking_id": booking_id,
                "ocr_plate": ocr_plate,
                "booking_plate": booking_plate,
            },
            mismatch_output,
            plate_result.confidence,
            time.time() - t0,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "plate_mismatch",
                "message": (
                    f"❌ Biển số xe không khớp!\n"
                    f"   Đọc được từ ảnh: {ocr_plate or '(không đọc được)'}\n"
                    f"   Đã đăng ký trong booking: {booking_plate}\n"
                    f"   Vui lòng kiểm tra lại xe hoặc liên hệ nhân viên."
                ),
                "ocr_plate": ocr_plate,
                "booking_plate": booking_plate,
                "ocr_confidence": plate_result.confidence,
                "ocr_warning": plate_result.warning,
            },
        )

    # 7. Call booking-service checkin
    checkin_resp = await call_booking_checkin(booking_id, user_id, GATEWAY_SECRET)

    if checkin_resp["status_code"] not in [200, 201]:
        raise HTTPException(
            status_code=checkin_resp["status_code"],
            detail=f"❌ Lỗi check-in từ booking service: {checkin_resp['data']}",
        )

    proc_time = time.time() - t0
    success_output = {"booking_plate": booking_plate, "match": True}
    if filename:
        success_output["image_path"] = filename
    if bbox:
        success_output["bbox"] = bbox
    log_prediction(
        db,
        "check_in_success",
        {"booking_id": booking_id, "ocr_plate": ocr_plate},
        success_output,
        plate_result.confidence,
        proc_time,
    )

    return {
        "success": True,
        "message": f"✅ Check-in thành công! Biển số: {ocr_plate}",
        "booking_id": booking_id,
        "plate_text": ocr_plate,
        "booking_plate": booking_plate,
        "plate_match": True,
        "ocr_confidence": round(plate_result.confidence, 3),
        "ocr_warning": plate_result.warning,
        "booking": checkin_resp["data"],
        "processing_time_ms": round(proc_time * 1000, 1),
        "plate_image_url": plate_image_url,
        "annotated_image_url": annotated_image_url,
        "bbox": bbox,
    }
