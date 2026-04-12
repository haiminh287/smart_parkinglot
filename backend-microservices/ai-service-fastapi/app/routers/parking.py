"""
Parking Check-in / Check-out via AI License Plate Recognition.

Flow:
  POST /ai/parking/scan-plate/
    → Detect + OCR plate from image
    → Return plate text + confidence

  POST /ai/parking/check-in/
    → QR data (booking_id + user_id) + plate image

  POST /ai/parking/detect-occupancy/
    → Camera image + slot bboxes JSON
    → Detect vehicle occupancy via YOLO11n (or OpenCV fallback)
    → Verify booking is valid & within time window
    → OCR plate, compare with booking.vehicle_license_plate
    → Call booking-service checkin API
    → Broadcast realtime update
    → Return result

  POST /ai/parking/check-out/
    → booking_id + plate image
    → OCR plate, verify match
    → Call booking-service checkout API
    → Broadcast realtime update
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from typing import Optional

import cv2
import httpx
import numpy as np
from app.config import settings
from app.database import get_db
from app.engine.plate_pipeline import PlateReadDecision, get_plate_pipeline
from app.engine.slot_detection import SlotBbox as _SlotBbox
from app.engine.slot_detection import get_slot_detector
from app.models.ai import PredictionLog
from app.schemas.ai import OccupancyDetectionResponse
from app.utils.image_utils import save_annotated_plate_image, save_debug_image, save_plate_image
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ai/parking", tags=["parking"])
logger = logging.getLogger(__name__)

# ── Model path ────────────────────────────────────────────────────────────── #
_MODEL_PATH = settings.PLATE_MODEL_PATH

BOOKING_SERVICE_URL = settings.BOOKING_SERVICE_URL
REALTIME_SERVICE_URL = settings.REALTIME_SERVICE_URL
GATEWAY_SECRET = settings.GATEWAY_SECRET


# ── Helpers ──────────────────────────────────────────────────────────────── #


def _plate_pipeline():
    return get_plate_pipeline(model_path=_MODEL_PATH)


def _normalize_plate(text: str) -> str:
    """Normalize plate to uppercase, alphanumeric only."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _plates_match(ocr_plate: str, booking_plate: str, strict: bool = False) -> bool:
    """
    Compare OCR plate with booking plate.
    Keeps only alphanumeric characters — ignores all separators (-, ., spaces, etc.).
    """
    a = _normalize_plate(ocr_plate)
    b = _normalize_plate(booking_plate)
    return a == b


def _extract_bbox(result) -> Optional[dict]:
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


async def _call_booking_checkin(
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


async def _call_booking_checkout(
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


async def _get_booking(booking_id: str, user_id: str) -> dict:
    """Fetch booking details from booking-service."""
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


def _log_prediction(
    db: Session,
    pred_type: str,
    input_data: dict,
    output_data: dict,
    confidence: float,
    proc_time: float,
):
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


# ── Endpoints ─────────────────────────────────────────────────────────────── #


@router.post("/scan-plate/")
async def scan_plate(
    image: UploadFile = File(..., description="Ảnh xe hoặc biển số xe"),
    db: Session = Depends(get_db),
):
    """
    Chỉ detect + OCR biển số — không cần QR hay booking.
    Dùng để test pipeline hoặc preview trước khi check-in.
    """
    contents = await image.read()
    pipeline = _plate_pipeline()
    result = pipeline.process(contents)

    # Save image and extract bbox
    filename = save_plate_image(contents, action="scan", identifier=str(uuid.uuid4()))
    plate_image_url = f"/ai/images/{filename}" if filename else None
    bbox = _extract_bbox(result)

    # Save annotated image with bbox overlay
    annotated_image_url = None
    if bbox and result.plate_text:
        ann_file = save_annotated_plate_image(
            contents, bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"],
            result.plate_text, result.confidence, action="scan",
        )
        if ann_file:
            annotated_image_url = f"/ai/images/{ann_file}"

    # Always save to debug folder
    save_debug_image(
        contents, action="scan", plate_text=result.plate_text,
        confidence=result.confidence, bbox=bbox, decision=result.decision,
    )

    output_data = {
        "plate_text": result.plate_text,
        "decision": result.decision,
        "confidence": result.confidence,
    }
    if filename:
        output_data["image_path"] = filename
    if bbox:
        output_data["bbox"] = bbox

    _log_prediction(
        db,
        "plate_scan",
        {"filename": image.filename},
        output_data,
        result.confidence,
        result.processing_time_ms / 1000,
    )

    return {
        "plate_text": result.plate_text,
        "decision": result.decision,
        "confidence": round(result.confidence, 3),
        "detection_confidence": round(result.detection_confidence, 3),
        "is_blurry": result.ocr_result.is_blurry if result.ocr_result else False,
        "blur_score": (
            round(result.ocr_result.blur_score, 1) if result.ocr_result else 0.0
        ),
        "ocr_method": result.ocr_result.method if result.ocr_result else "none",
        "raw_candidates": result.ocr_result.candidates if result.ocr_result else [],
        "warning": result.warning,
        "message": result.message,
        "processing_time_ms": round(result.processing_time_ms, 1),
        "plate_image_url": plate_image_url,
        "annotated_image_url": annotated_image_url,
        "bbox": bbox,
    }


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
    booking = await _get_booking(booking_id, user_id)

    # 3. Validate booking status
    # Booking service returns CamelCase keys (checkInStatus, startTime, etc.)
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
        # Allow check-in from 15 min before start_time
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
    pipeline = _plate_pipeline()
    plate_result = pipeline.process(contents)

    # Save image and extract bbox
    filename = save_plate_image(contents, action="checkin", identifier=booking_id)
    plate_image_url = f"/ai/images/{filename}" if filename else None
    bbox = _extract_bbox(plate_result)

    # Save annotated image with bbox overlay
    annotated_image_url = None
    if bbox and plate_result.plate_text:
        ann_file = save_annotated_plate_image(
            contents, bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"],
            plate_result.plate_text, plate_result.confidence,
            action="checkin", identifier=booking_id,
        )
        if ann_file:
            annotated_image_url = f"/ai/images/{ann_file}"

    # Always save to debug folder
    save_debug_image(
        contents, action="checkin", plate_text=plate_result.plate_text,
        confidence=plate_result.confidence, bbox=bbox, decision=plate_result.decision,
    )

    # Booking service returns vehicle as nested object with licensePlate
    vehicle_info = booking.get("vehicle", {})
    booking_plate = _normalize_plate(
        vehicle_info.get("licensePlate", "") or booking.get("vehicle_license_plate", "")
    )

    # 6. Check plate match
    if plate_result.decision in [PlateReadDecision.NOT_FOUND, PlateReadDecision.BLURRY]:
        fail_output = {"plate_result": plate_result.decision}
        if filename:
            fail_output["image_path"] = filename
        _log_prediction(
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

    ocr_plate = _normalize_plate(plate_result.plate_text)
    plate_match = _plates_match(ocr_plate, booking_plate)

    if not plate_match:
        mismatch_output = {"match": False}
        if filename:
            mismatch_output["image_path"] = filename
        if bbox:
            mismatch_output["bbox"] = bbox
        _log_prediction(
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
    checkin_resp = await _call_booking_checkin(booking_id, user_id, GATEWAY_SECRET)

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
    _log_prediction(
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
    booking = await _get_booking(booking_id, user_id)

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
    pipeline = _plate_pipeline()
    plate_result = pipeline.process(contents)

    # Save image and extract bbox
    filename = save_plate_image(contents, action="checkout", identifier=booking_id)
    plate_image_url = f"/ai/images/{filename}" if filename else None
    bbox = _extract_bbox(plate_result)

    # Save annotated image with bbox overlay
    annotated_image_url = None
    if bbox and plate_result.plate_text:
        ann_file = save_annotated_plate_image(
            contents, bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"],
            plate_result.plate_text, plate_result.confidence,
            action="checkout", identifier=booking_id,
        )
        if ann_file:
            annotated_image_url = f"/ai/images/{ann_file}"

    # Always save to debug folder
    save_debug_image(
        contents, action="checkout", plate_text=plate_result.plate_text,
        confidence=plate_result.confidence, bbox=bbox, decision=plate_result.decision,
    )

    # Booking service returns vehicle as nested object with licensePlate
    vehicle_info = booking.get("vehicle", {})
    booking_plate = _normalize_plate(
        vehicle_info.get("licensePlate", "") or booking.get("vehicle_license_plate", "")
    )

    # 5. Check plate match
    if plate_result.decision in [PlateReadDecision.NOT_FOUND, PlateReadDecision.BLURRY]:
        fail_output = {"plate_result": plate_result.decision}
        if filename:
            fail_output["image_path"] = filename
        _log_prediction(
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

    ocr_plate = _normalize_plate(plate_result.plate_text)
    plate_match = _plates_match(ocr_plate, booking_plate)

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
        _log_prediction(
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
    checkout_resp = await _call_booking_checkout(booking_id, user_id, GATEWAY_SECRET)

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
    _log_prediction(
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


@router.post("/detect-occupancy/", response_model=OccupancyDetectionResponse)
async def detect_parking_occupancy(
    image: UploadFile = File(..., description="Ảnh bãi xe từ camera"),
    camera_id: str = Form(..., description="Camera ID"),
    slots: str = Form(
        ...,
        description=(
            "JSON list of slot bboxes: "
            '[{"slot_id":"...","slot_code":"...","zone_id":"...",'
            '"x1":0,"y1":0,"x2":100,"y2":100}]'
        ),
    ),
):
    """
    Detect vehicle occupancy for parking slots in a camera frame.

    Uses YOLO11n if model is loaded, falls back to OpenCV edge/contour analysis.
    Slots are defined by bounding boxes (pixel coordinates) in the uploaded image.
    """
    # Parse and validate slots JSON
    try:
        slots_data = json.loads(slots)
        if not isinstance(slots_data, list):
            raise ValueError("slots must be a JSON array")
        slot_list = [
            _SlotBbox(
                slot_id=str(s["slot_id"]),
                slot_code=str(s["slot_code"]),
                zone_id=str(s["zone_id"]),
                x1=int(s["x1"]),
                y1=int(s["y1"]),
                x2=int(s["x2"]),
                y2=int(s["y2"]),
            )
            for s in slots_data
        ]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid slots JSON: {exc}")

    # Decode image
    contents = await image.read()
    img_array = np.frombuffer(contents, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail="Cannot decode image file")

    # Run detection in thread pool (YOLO/OpenCV are sync/CPU-bound)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, get_slot_detector().detect_occupancy, frame, slot_list, camera_id
    )
    return result
    return result
