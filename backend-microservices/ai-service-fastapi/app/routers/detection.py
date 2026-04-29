"""
Detection endpoints — license plate, banknote recognition (Hybrid MVP).
Uses the engine/ pipeline for banknote detection.
"""

import logging
import os
import time
import uuid

from app.config import settings
from app.database import get_db
from app.models.ai import PredictionLog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ai/detect", tags=["detection"])
logger = logging.getLogger(__name__)

# ── Lazy-loaded pipeline singleton ──────────────
_pipeline = None

# ── Plate pipeline singleton ──────────────────────
_plate_pipeline_singleton = None


def _get_pipeline():
    """Lazy-init the banknote recognition pipeline."""
    global _pipeline
    if _pipeline is None:
        from app.engine.pipeline import BanknoteRecognitionPipeline

        model_dir = settings.ML_MODELS_DIR
        if settings.BANKNOTE_MODEL_PATH:
            model_dir = os.path.dirname(settings.BANKNOTE_MODEL_PATH)
        _pipeline = BanknoteRecognitionPipeline(model_dir=model_dir)
    return _pipeline


def _get_plate_pipeline():
    """Get or create the singleton plate recognition pipeline."""
    global _plate_pipeline_singleton
    if _plate_pipeline_singleton is None:
        from app.engine.plate_pipeline import get_plate_pipeline

        _plate_pipeline_singleton = get_plate_pipeline(
            model_path=settings.PLATE_MODEL_PATH
        )
    return _plate_pipeline_singleton


@router.post("/license-plate/")
async def detect_license_plate(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Detect and OCR license plates using YOLOv8 finetune + TrOCR pipeline."""
    start_time = time.time()

    try:
        contents = await image.read()
        pipeline = _get_plate_pipeline()
        result = pipeline.process(contents)

        processing_time = time.time() - start_time

        # Build detections list for backward compatibility
        detections = []
        if result.plate_text:
            bbox = []
            if result.detection_result and result.detection_result.box:
                b = result.detection_result.box
                bbox = [b.x1, b.y1, b.x2, b.y2]
            detections.append(
                {
                    "plate_text": result.plate_text,
                    "confidence": round(result.confidence, 3),
                    "bbox": bbox,
                }
            )

        try:
            log = PredictionLog(
                id=str(uuid.uuid4()),
                prediction_type="license_plate",
                input_data={"filename": image.filename},
                output_data={
                    "plate_text": result.plate_text,
                    "decision": result.decision,
                    "confidence": result.confidence,
                },
                confidence=result.confidence,
                model_version="yolov8_finetune_v1m",
                processing_time=processing_time,
            )
            db.add(log)
            db.commit()
        except Exception as db_err:
            logger.warning(f"Failed to log plate prediction: {db_err}")

        return {
            "plate_text": result.plate_text,
            "decision": result.decision,
            "confidence": round(result.confidence, 3),
            "detection_confidence": round(result.detection_confidence, 3),
            "detections": detections,
            "processing_time": processing_time,
            "model_version": "yolov8_finetune_v1m",
            "warning": result.warning,
            "message": result.message,
        }

    except Exception as e:
        logger.error(f"License plate detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/banknote/")
async def detect_banknote(
    image: UploadFile = File(...),
    mode: str = Query("full", pattern="^(full|fast)$"),
    db: Session = Depends(get_db),
):
    """
    Vietnamese banknote recognition using Hybrid MVP pipeline.

    Pipeline stages:
      Stage 0: Preprocessing (quality gate + white balance)
      Stage 1: Banknote Detection (YOLOv8n / fallback)
      Stage 2A: Color-Based Denomination (HSV)
      Dynamic Check → PASS → result, FAIL → Stage 2B AI Fallback

    Query params:
      mode: "full" (default) or "fast" (color-only, ~3ms)
    """
    start_time = time.time()

    temp_filename = f"temp_banknote_{int(time.time())}_{image.filename}"
    full_path = os.path.join(settings.MEDIA_ROOT, temp_filename)

    try:
        contents = await image.read()

        # Validate file type
        content_type = image.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        with open(full_path, "wb") as f:
            f.write(contents)

        import cv2

        img = cv2.imread(full_path)
        if img is None:
            raise HTTPException(status_code=400, detail="Cannot read image file")

        # Run pipeline
        pipeline = _get_pipeline()
        if mode == "fast":
            result = pipeline.process_fast(img)
        else:
            result = pipeline.process(img)

        processing_time = time.time() - start_time

        # Build response
        response_data = {
            "decision": result.decision.value,
            "denomination": result.denomination,
            "confidence": round(result.confidence, 4),
            "method": result.method.value,
            "quality": (
                {
                    "blurScore": round(result.quality_result.blur_score, 2),
                    "exposureScore": round(result.quality_result.exposure_score, 2),
                    "status": result.quality_result.status.value,
                    "message": result.quality_result.message,
                }
                if result.quality_result
                else None
            ),
            "detection": (
                {
                    "found": result.detection_result.found,
                    "confidence": (
                        round(result.detection_result.box.confidence, 4)
                        if result.detection_result and result.detection_result.box
                        else 0
                    ),
                    "message": result.detection_result.message,
                }
                if result.detection_result
                else None
            ),
            "allProbabilities": (
                {k: round(v, 4) for k, v in result.all_probabilities.items()}
                if result.all_probabilities
                else None
            ),
            "stagesExecuted": result.stages_executed,
            "processingTimeMs": round(result.processing_time_ms, 2),
            "processingTime": round(processing_time, 4),
            "message": result.message,
            "pipelineVersion": "hybrid-mvp-v1",
        }

        # Log to database
        try:
            log = PredictionLog(
                id=str(uuid.uuid4()),
                prediction_type="banknote_recognition",
                input_data={"image": temp_filename, "mode": mode},
                output_data=response_data,
                confidence=result.confidence,
                model_version="hybrid-mvp-v1",
                processing_time=processing_time,
            )
            db.add(log)
            db.commit()
        except Exception as db_err:
            logger.warning(f"Failed to log prediction: {db_err}")

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Banknote recognition error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(full_path):
            os.remove(full_path)
