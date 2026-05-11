"""POST /scan-plate/ — Detect + OCR license plate from image."""

import uuid

from app.database import get_db
from app.utils.image_utils import (
    save_annotated_plate_image,
    save_debug_image,
    save_plate_image,
)
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from .helpers import extract_bbox, log_prediction, plate_pipeline

router = APIRouter()


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
    pipeline = plate_pipeline()
    result = pipeline.process(contents)

    # Save image and extract bbox
    filename = save_plate_image(contents, action="scan", identifier=str(uuid.uuid4()))
    plate_image_url = f"/ai/images/{filename}" if filename else None
    bbox = extract_bbox(result)

    # Save annotated image with bbox overlay
    annotated_image_url = None
    if bbox and result.plate_text:
        ann_file = save_annotated_plate_image(
            contents,
            bbox["x1"],
            bbox["y1"],
            bbox["x2"],
            bbox["y2"],
            result.plate_text,
            result.confidence,
            action="scan",
        )
        if ann_file:
            annotated_image_url = f"/ai/images/{ann_file}"

    # Always save to debug folder
    save_debug_image(
        contents,
        action="scan",
        plate_text=result.plate_text,
        confidence=result.confidence,
        bbox=bbox,
        decision=result.decision,
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

    log_prediction(
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
