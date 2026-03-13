"""
Model metrics & prediction log endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai import PredictionLog, ModelVersion
from app.schemas.ai import MetricsResponse, PredictionLogResponse, ModelVersionResponse

router = APIRouter(prefix="/ai/models", tags=["models"])


@router.get("/metrics/", response_model=MetricsResponse)
async def get_metrics(db: Session = Depends(get_db)):
    """Get metrics for all AI models."""
    lp_count = db.query(PredictionLog).filter(
        PredictionLog.prediction_type == "license_plate"
    ).count()

    cash_count = db.query(PredictionLog).filter(
        PredictionLog.prediction_type == "cash_recognition"
    ).count()

    cash_model = (
        db.query(ModelVersion)
        .filter(ModelVersion.model_type == "cash_recognition")
        .order_by(ModelVersion.created_at.desc())
        .first()
    )

    bn_count = db.query(PredictionLog).filter(
        PredictionLog.prediction_type == "banknote_recognition"
    ).count()

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
            "accuracy": float(cash_model.accuracy) if cash_model and cash_model.accuracy else 0.0,
            "total_predictions": cash_count,
        },
        banknote_recognition={
            "version": "bank-grade-v1",
            "type": "multi-stage-pipeline",
            "description": "EfficientNetV2-S + YOLOv8 + Siamese + OneClass",
            "stages": [
                "Quality Gate", "Detector (YOLOv8)", "Classifier (EfficientNetV2-S)",
                "Temperature Scaling", "Security (Siamese+OneClass)", "Decision Policy",
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
