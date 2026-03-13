"""
Parking Check-in / Check-out via AI License Plate Recognition.

Flow:
  POST /ai/parking/scan-plate/
    → Detect + OCR plate from image
    → Return plate text + confidence

  POST /ai/parking/check-in/
    → QR data (booking_id + user_id) + plate image
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

import json
import logging
import os
import time
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.engine.plate_pipeline import get_plate_pipeline, PlateReadDecision
from app.models.ai import PredictionLog

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
    """Normalize plate to uppercase, no spaces."""
    return text.upper().replace(' ', '').replace('\t', '').strip()


def _plates_match(ocr_plate: str, booking_plate: str, strict: bool = False) -> bool:
    """
    Compare OCR plate with booking plate.
    Non-strict: ignore separators (-, .) and spaces.
    """
    a = re.sub(r'[\s.\-]', '', ocr_plate.upper())
    b = re.sub(r'[\s.\-]', '', booking_plate.upper())
    return a == b


import re


async def _call_booking_checkin(booking_id: str, user_id: str, gateway_secret: str) -> dict:
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


async def _call_booking_checkout(booking_id: str, user_id: str, gateway_secret: str) -> dict:
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
                detail=f"Booking không tồn tại hoặc không có quyền truy cập. (booking_id={booking_id})"
            )
        return resp.json()


def _log_prediction(db: Session, pred_type: str, input_data: dict, output_data: dict,
                    confidence: float, proc_time: float):
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

    _log_prediction(
        db, "plate_scan",
        {"filename": image.filename},
        {
            "plate_text": result.plate_text,
            "decision": result.decision,
            "confidence": result.confidence,
        },
        result.confidence,
        result.processing_time_ms / 1000,
    )

    return {
        "plate_text": result.plate_text,
        "decision": result.decision,
        "confidence": round(result.confidence, 3),
        "detection_confidence": round(result.detection_confidence, 3),
        "is_blurry": result.ocr_result.is_blurry if result.ocr_result else False,
        "blur_score": round(result.ocr_result.blur_score, 1) if result.ocr_result else 0.0,
        "ocr_method": result.ocr_result.method if result.ocr_result else "none",
        "raw_candidates": result.ocr_result.candidates if result.ocr_result else [],
        "warning": result.warning,
        "message": result.message,
        "processing_time_ms": round(result.processing_time_ms, 1),
    }


@router.post("/check-in/")
async def check_in(
    image: UploadFile = File(..., description="Ảnh biển số xe"),
    qr_data: str = Form(..., description='JSON từ QR code: {"booking_id":"...","user_id":"..."}'),
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
            detail=f"❌ QR code không hợp lệ: {e}. QR phải chứa booking_id và user_id."
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
        msg = status_map.get(check_in_status, f"trạng thái không hợp lệ: {check_in_status}")
        raise HTTPException(
            status_code=400,
            detail=f"❌ Booking này {msg}. Không thể check-in."
        )

    # 4. Validate time window — allow 15 min early, no limit late
    from datetime import datetime, timezone, timedelta
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
                       f"(bắt đầu: {start_time.strftime('%H:%M %d/%m/%Y')})."
            )
    except HTTPException:
        raise
    except Exception:
        pass  # If time parse fails, skip time check

    # 5. OCR plate
    contents = await image.read()
    pipeline = _plate_pipeline()
    plate_result = pipeline.process(contents)

    # Booking service returns vehicle as nested object with licensePlate
    vehicle_info = booking.get("vehicle", {})
    booking_plate = _normalize_plate(
        vehicle_info.get("licensePlate", "") or booking.get("vehicle_license_plate", "")
    )

    # 6. Check plate match
    if plate_result.decision in [PlateReadDecision.NOT_FOUND, PlateReadDecision.BLURRY]:
        _log_prediction(db, "check_in_failed",
                        {"booking_id": booking_id, "reason": "plate_not_readable"},
                        {"plate_result": plate_result.decision}, 0.0,
                        time.time() - t0)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "plate_unreadable",
                "message": plate_result.warning or "❌ Không đọc được biển số xe. Vui lòng chụp lại.",
                "decision": plate_result.decision,
                "blur_score": plate_result.ocr_result.blur_score if plate_result.ocr_result else 0,
            }
        )

    ocr_plate = _normalize_plate(plate_result.plate_text)
    plate_match = _plates_match(ocr_plate, booking_plate)

    if not plate_match:
        _log_prediction(db, "check_in_plate_mismatch",
                        {"booking_id": booking_id, "ocr_plate": ocr_plate, "booking_plate": booking_plate},
                        {"match": False}, plate_result.confidence, time.time() - t0)
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
            }
        )

    # 7. Call booking-service checkin
    checkin_resp = await _call_booking_checkin(booking_id, user_id, GATEWAY_SECRET)

    if checkin_resp["status_code"] not in [200, 201]:
        raise HTTPException(
            status_code=checkin_resp["status_code"],
            detail=f"❌ Lỗi check-in từ booking service: {checkin_resp['data']}"
        )

    proc_time = time.time() - t0
    _log_prediction(db, "check_in_success",
                    {"booking_id": booking_id, "ocr_plate": ocr_plate},
                    {"booking_plate": booking_plate, "match": True},
                    plate_result.confidence, proc_time)

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
    }


@router.post("/check-out/")
async def check_out(
    image: UploadFile = File(..., description="Ảnh biển số xe"),
    qr_data: str = Form(..., description='JSON từ QR code: {"booking_id":"...","user_id":"..."}'),
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
        raise HTTPException(
            status_code=400,
            detail=f"❌ QR code không hợp lệ: {e}"
        )

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
            detail=f"❌ Booking này {msg}. Chỉ có thể check-out khi đang ở trạng thái checked_in."
        )

    # 3.5 Payment enforcement — barrier MUST NOT open without payment
    payment_status = booking.get("paymentStatus", booking.get("payment_status", "pending"))
    payment_method = booking.get("paymentMethod", booking.get("payment_method", "online"))
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
            }
        )

    # 4. OCR plate
    contents = await image.read()
    pipeline = _plate_pipeline()
    plate_result = pipeline.process(contents)

    # Booking service returns vehicle as nested object with licensePlate
    vehicle_info = booking.get("vehicle", {})
    booking_plate = _normalize_plate(
        vehicle_info.get("licensePlate", "") or booking.get("vehicle_license_plate", "")
    )

    # 5. Check plate match
    if plate_result.decision in [PlateReadDecision.NOT_FOUND, PlateReadDecision.BLURRY]:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "plate_unreadable",
                "message": plate_result.warning or "❌ Không đọc được biển số xe.",
                "decision": plate_result.decision,
            }
        )

    ocr_plate = _normalize_plate(plate_result.plate_text)
    plate_match = _plates_match(ocr_plate, booking_plate)

    if not plate_match:
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
            }
        )

    # 6. Call booking-service checkout
    checkout_resp = await _call_booking_checkout(booking_id, user_id, GATEWAY_SECRET)

    if checkout_resp["status_code"] not in [200, 201]:
        raise HTTPException(
            status_code=checkout_resp["status_code"],
            detail=f"❌ Lỗi check-out từ booking service: {checkout_resp['data']}"
        )

    proc_time = time.time() - t0
    _log_prediction(db, "check_out_success",
                    {"booking_id": booking_id, "ocr_plate": ocr_plate},
                    {"booking_plate": booking_plate},
                    plate_result.confidence, proc_time)

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
    }
