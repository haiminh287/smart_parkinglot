"""POST /check-out/ — QR + plate verification, then booking-service checkout."""

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
    call_booking_checkout,
    extract_bbox,
    get_booking,
    log_prediction,
    normalize_plate,
    plate_pipeline,
    plates_match,
)

router = APIRouter()


@router.post("/check-out/")
async def check_out(
    image: UploadFile = File(..., description="Ảnh biển số xe"),
    qr_data: str = Form(
        ..., description='JSON từ QR code: {"booking_id":"...","user_id":"..."}'
    ),
    db: Session = Depends(get_db),
):
    """
    Check-out quy trình:
    1. Parse QR data
    2. Fetch booking → kiểm tra trạng thái checked_in
    3. OCR biển số, so khớp
    4. Gọi booking-service checkout API
    5. Trả kết quả với tổng tiền, phí phạt nếu có
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
        raise HTTPException(status_code=400, detail=f"❌ QR code không hợp lệ: {e}")

    # 2. Fetch booking
    booking = await get_booking(booking_id, user_id)

    # 3. Validate status (booking service returns CamelCase keys)
    check_in_status = booking.get("checkInStatus", booking.get("check_in_status", ""))
    if check_in_status != "checked_in":
        status_map = {
            "not_checked_in": "chưa check-in",
            "checked_out": "đã được check-out rồi",
            "cancelled": "đã bị huỷ",
            "no_show": "đã bị đánh dấu no-show",
        }
        msg = status_map.get(check_in_status, f"trạng thái: {check_in_status}")
        raise HTTPException(
            status_code=400,
            detail=f"❌ Booking này {msg}. Chỉ có thể check-out khi đang ở trạng thái checked_in.",
        )

    # 3.5 Payment enforcement — barrier MUST NOT open without payment
    payment_status = booking.get(
        "paymentStatus", booking.get("payment_status", "pending")
    )
    payment_method = booking.get(
        "paymentMethod", booking.get("payment_method", "online")
    )
    if payment_method != "on_exit" and payment_status != "completed":
        booking_price = float(booking.get("price", 0))
        raise HTTPException(
            status_code=402,
            detail={
                "error": "payment_required",
                "message": (
                    f"⏳ Chưa thanh toán! Vui lòng thanh toán "
                    f"{booking_price:,.0f}đ trước khi check-out."
                ),
                "amount_due": booking_price,
                "payment_status": payment_status,
            },
        )

    # 4. OCR plate
    contents = await image.read()
    pipeline = plate_pipeline()
    plate_result = pipeline.process(contents)

    # Save image and extract bbox
    filename = save_plate_image(contents, action="checkout", identifier=booking_id)
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
            action="checkout",
            identifier=booking_id,
        )
        if ann_file:
            annotated_image_url = f"/ai/images/{ann_file}"

    # Always save to debug folder
    save_debug_image(
        contents,
        action="checkout",
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

    # 5. Check plate match
    if plate_result.decision in [PlateReadDecision.NOT_FOUND, PlateReadDecision.BLURRY]:
        fail_output = {"plate_result": plate_result.decision}
        if filename:
            fail_output["image_path"] = filename
        log_prediction(
            db,
            "check_out_failure",
            {"booking_id": booking_id, "reason": "plate_not_readable"},
            fail_output,
            0.0,
            time.time() - t0,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "plate_unreadable",
                "message": plate_result.warning or "❌ Không đọc được biển số xe.",
                "decision": plate_result.decision,
            },
        )

    ocr_plate = normalize_plate(plate_result.plate_text)
    plate_match = plates_match(ocr_plate, booking_plate)

    if not plate_match:
        mismatch_output = {
            "match": False,
            "ocr_plate": ocr_plate,
            "booking_plate": booking_plate,
        }
        if filename:
            mismatch_output["image_path"] = filename
        if bbox:
            mismatch_output["bbox"] = bbox
        log_prediction(
            db,
            "check_out_failure",
            {"booking_id": booking_id, "ocr_plate": ocr_plate},
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
                    f"   Đọc được: {ocr_plate}\n"
                    f"   Đã đăng ký: {booking_plate}"
                ),
                "ocr_plate": ocr_plate,
                "booking_plate": booking_plate,
            },
        )

    # 6. Call booking-service checkout
    checkout_resp = await call_booking_checkout(booking_id, user_id, GATEWAY_SECRET)

    if checkout_resp["status_code"] not in [200, 201]:
        raise HTTPException(
            status_code=checkout_resp["status_code"],
            detail=f"❌ Lỗi check-out từ booking service: {checkout_resp['data']}",
        )

    proc_time = time.time() - t0
    checkout_output = {"booking_plate": booking_plate}
    if filename:
        checkout_output["image_path"] = filename
    if bbox:
        checkout_output["bbox"] = bbox
    log_prediction(
        db,
        "check_out_success",
        {"booking_id": booking_id, "ocr_plate": ocr_plate},
        checkout_output,
        plate_result.confidence,
        proc_time,
    )

    checkout_data = checkout_resp["data"]
    late_fee = checkout_data.get("late_fee", 0)
    total_amount = checkout_data.get("total_amount", 0)

    msg = f"✅ Check-out thành công! Biển số: {ocr_plate}"
    if late_fee and float(late_fee) > 0:
        msg += f"\n⚠️ Phí phạt quá giờ: {float(late_fee):,.0f}đ"
    if total_amount:
        msg += f"\nTổng tiền: {float(total_amount):,.0f}đ"

    return {
        "success": True,
        "message": msg,
        "booking_id": booking_id,
        "plate_text": ocr_plate,
        "booking_plate": booking_plate,
        "plate_match": True,
        "ocr_confidence": round(plate_result.confidence, 3),
        "ocr_warning": plate_result.warning,
        "booking": checkout_data,
        "processing_time_ms": round(proc_time * 1000, 1),
        "plate_image_url": plate_image_url,
        "annotated_image_url": annotated_image_url,
        "bbox": bbox,
    }
