"""
Model metrics & prediction log endpoints.
"""

from datetime import date, datetime
from typing import Optional

from app.database import get_db
from app.models.ai import ModelVersion, PredictionLog
from app.schemas.ai import MetricsResponse, ModelVersionResponse, PredictionLogResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ai/models", tags=["models"])

# Secondary router for parking detection history
parking_router = APIRouter(prefix="/ai/parking", tags=["parking"])

# Prediction types that correspond to ANPR detection actions
_DETECTION_PRED_TYPES = [
    "plate_scan",
    "check_in_success",
    "check_in_failure",
    "check_out_success",
    "check_out_failure",
]

_ACTION_MAP = {
    "plate_scan": "scan",
    "check_in_success": "check_in",
    "check_in_failure": "check_in",
    "check_out_success": "check_out",
    "check_out_failure": "check_out",
}


@router.get("/metrics/", response_model=MetricsResponse)
async def get_metrics(db: Session = Depends(get_db)):
    """Get metrics for all AI models."""
    lp_count = (
        db.query(PredictionLog)
        .filter(PredictionLog.prediction_type == "license_plate")
        .count()
    )

    cash_count = (
        db.query(PredictionLog)
        .filter(PredictionLog.prediction_type == "cash_recognition")
        .count()
    )

    cash_model = (
        db.query(ModelVersion)
        .filter(ModelVersion.model_type == "cash_recognition")
        .order_by(ModelVersion.created_at.desc())
        .first()
    )

    bn_count = (
        db.query(PredictionLog)
        .filter(PredictionLog.prediction_type == "banknote_recognition")
        .count()
    )

    return MetricsResponse(
        license_plate={
            "version": "yolov8n",
            "type": "pre-trained",
            "description": "YOLOv8 pre-trained on COCO dataset",
            "total_predictions": lp_count,
        },
        cash_recognition={
            "version": "resnet50_v1",
            "type": "custom-trained",
            "description": "ResNet50 trained on Vietnamese cash dataset",
            "accuracy": (
                float(cash_model.accuracy)
                if cash_model and cash_model.accuracy
                else 0.0
            ),
            "total_predictions": cash_count,
        },
        banknote_recognition={
            "version": "bank-grade-v1",
            "type": "multi-stage-pipeline",
            "description": "EfficientNetV2-S + YOLOv8 + Siamese + OneClass",
            "stages": [
                "Quality Gate",
                "Detector (YOLOv8)",
                "Classifier (EfficientNetV2-S)",
                "Temperature Scaling",
                "Security (Siamese+OneClass)",
                "Decision Policy",
            ],
            "total_predictions": bn_count,
        },
    )


@router.get("/predictions/", response_model=list[PredictionLogResponse])
async def list_predictions(
    prediction_type: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List prediction logs."""
    query = db.query(PredictionLog)
    if prediction_type:
        query = query.filter(PredictionLog.prediction_type == prediction_type)

    predictions = (
        query.order_by(PredictionLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return predictions


@router.get("/versions/", response_model=list[ModelVersionResponse])
async def list_model_versions(
    model_type: str = None,
    db: Session = Depends(get_db),
):
    """List model versions."""
    query = db.query(ModelVersion)
    if model_type:
        query = query.filter(ModelVersion.model_type == model_type)

    versions = query.order_by(ModelVersion.created_at.desc()).all()
    return versions


@parking_router.get("/detections/")
async def list_detections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    plate_text: Optional[str] = Query(None, description="LIKE search on plate text"),
    date_from: Optional[date] = Query(None, description="Filter from date (ISO)"),
    date_to: Optional[date] = Query(None, description="Filter to date (ISO)"),
    action: Optional[str] = Query(None, description="scan, check_in, or check_out"),
    db: Session = Depends(get_db),
):
    """List ANPR detection history with plate images and bbox data."""
    query = db.query(PredictionLog).filter(
        PredictionLog.prediction_type.in_(_DETECTION_PRED_TYPES)
    )

    if action:
        action_types = [k for k, v in _ACTION_MAP.items() if v == action]
        if action_types:
            query = query.filter(PredictionLog.prediction_type.in_(action_types))

    if date_from:
        query = query.filter(
            PredictionLog.created_at >= datetime.combine(date_from, datetime.min.time())
        )

    if date_to:
        query = query.filter(
            PredictionLog.created_at <= datetime.combine(date_to, datetime.max.time())
        )

    if plate_text:
        query = query.filter(
            cast(PredictionLog.output_data, String).like(f"%{plate_text}%")
        )

    total = query.count()
    rows = (
        query.order_by(PredictionLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    results = [_map_detection_row(row) for row in rows]
    return {"total": total, "page": page, "page_size": page_size, "results": results}


def _map_detection_row(row: PredictionLog) -> dict:
    """Map a PredictionLog row to detection response dict."""
    output = row.output_data or {}
    input_data = row.input_data or {}
    image_path = output.get("image_path")
    return {
        "id": row.id,
        "plate_text": output.get("plate_text") or input_data.get("ocr_plate", ""),
        "confidence": row.confidence,
        "decision": output.get("decision") or output.get("plate_result", ""),
        "image_url": f"/ai/images/{image_path}" if image_path else None,
        "bbox": output.get("bbox"),
        "camera_id": input_data.get("camera_id"),
        "action": _ACTION_MAP.get(row.prediction_type, row.prediction_type),
        "prediction_type": row.prediction_type,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "processing_time_ms": (
            round(row.processing_time * 1000, 1) if row.processing_time else None
        ),
    }
