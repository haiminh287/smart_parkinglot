"""
Pydantic schemas for AI service.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel
from app.schemas.base import CamelModel


class DetectionResult(CamelModel):
    plate_text: Optional[str] = None
    confidence: float
    bbox: list[float] = []


class LicensePlateResponse(CamelModel):
    detections: list[DetectionResult]
    processing_time: float
    model_version: str


class CashRecognitionResponse(CamelModel):
    denomination: str
    confidence: float
    all_probabilities: dict[str, float]
    processing_time: float
    model_version: str


# ── Banknote Hybrid MVP Response ────────────────

class BanknoteQualityInfo(CamelModel):
    blur_score: float
    exposure_score: float
    status: str
    message: str = ""


class BanknoteDetectionInfo(CamelModel):
    found: bool
    confidence: float = 0.0
    message: str = ""


class BanknoteRecognitionResponse(CamelModel):
    """Response from the banknote recognition pipeline (Hybrid MVP)."""
    decision: str  # accept, low_confidence, no_banknote, bad_quality, error
    denomination: Optional[str] = None
    confidence: float
    method: str = "none"  # color, ai_fallback, none
    quality: Optional[BanknoteQualityInfo] = None
    detection: Optional[BanknoteDetectionInfo] = None
    all_probabilities: Optional[dict[str, float]] = None
    stages_executed: list[str] = []
    processing_time_ms: float = 0.0
    processing_time: float = 0.0
    message: str = ""
    pipeline_version: str = "hybrid-mvp-v1"


class TrainRequest(CamelModel):
    train_dir: str = "./datasets/cash/train"
    val_dir: str = "./datasets/cash/val"
    epochs: int = 50
    batch_size: int = 32
    lr: float = 0.001


class BanknoteTrainRequest(CamelModel):
    data_dir: str = "./cash_dataset"
    epochs_classifier: int = 100
    epochs_siamese: int = 50
    epochs_oneclass: int = 30
    batch_size: int = 32
    lr: float = 0.0003
    mlflow: bool = False


class TrainResponse(CamelModel):
    status: str
    message: str
    parameters: dict[str, Any] = {}


class PredictionLogResponse(CamelModel):
    id: str
    prediction_type: str
    input_data: dict
    output_data: dict
    confidence: Optional[float] = None
    model_version: str
    processing_time: float
    created_at: Optional[datetime] = None


class ModelVersionResponse(CamelModel):
    id: str
    model_type: str
    version: str
    status: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None
    training_params: dict = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MetricsResponse(CamelModel):
    license_plate: dict
    cash_recognition: dict
    banknote_recognition: dict
