"""
Training endpoints — trigger model training using BackgroundTasks (BUG FIX: no threading.Thread).
"""

import os
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.models.ai import ModelVersion
from app.schemas.ai import BanknoteTrainRequest

router = APIRouter(prefix="/ai/train", tags=["training"])
logger = logging.getLogger(__name__)


def _train_banknote_background(data_dir: str, output_dir: str,
                                epochs_classifier: int, epochs_siamese: int,
                                epochs_oneclass: int, batch_size: int,
                                lr: float, use_mlflow: bool):
    """Run bank-grade pipeline training in background."""
    try:
        logger.info("🚀 Starting bank-grade pipeline training...")

        from app.ml.banknote.train_classifier import train as train_classifier
        logger.info("📚 Stage 1: Training EfficientNetV2-S classifier...")
        train_classifier(
            data_dir=data_dir, output_dir=output_dir,
            epochs=epochs_classifier, batch_size=batch_size,
            lr=lr, use_mlflow=use_mlflow,
        )

        from app.ml.banknote.train_security import train_siamese, train_oneclass
        logger.info("🔗 Stage 2: Training Siamese network...")
        train_siamese(data_dir=data_dir, output_dir=output_dir,
                      epochs=epochs_siamese, batch_size=batch_size)

        logger.info("🛡️ Stage 3: Training OneClass anomaly detector...")
        train_oneclass(data_dir=data_dir, output_dir=output_dir,
                       epochs=epochs_oneclass, batch_size=batch_size)

        db = SessionLocal()
        try:
            version = ModelVersion(
                id=str(uuid.uuid4()),
                model_type="banknote_recognition",
                version="bank-grade-v1",
                file_path=output_dir,
                status="production",
                training_params={
                    "epochs_classifier": epochs_classifier,
                    "epochs_siamese": epochs_siamese,
                    "epochs_oneclass": epochs_oneclass,
                    "batch_size": batch_size,
                    "lr": lr,
                    "mlflow": use_mlflow,
                },
            )
            db.add(version)
            db.commit()
        finally:
            db.close()

        logger.info("✅ Bank-grade pipeline training COMPLETE")
    except Exception as e:
        logger.error(f"❌ Banknote training failed: {e}", exc_info=True)


@router.post("/banknote/")
async def train_banknote_model(
    payload: BanknoteTrainRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger bank-grade banknote pipeline training in background."""
    if not os.path.exists(payload.data_dir):
        raise HTTPException(
            status_code=400, detail=f"Dataset directory not found: {payload.data_dir}"
        )

    output_dir = settings.ML_MODELS_DIR
    os.makedirs(output_dir, exist_ok=True)

    background_tasks.add_task(
        _train_banknote_background,
        data_dir=payload.data_dir,
        output_dir=output_dir,
        epochs_classifier=payload.epochs_classifier,
        epochs_siamese=payload.epochs_siamese,
        epochs_oneclass=payload.epochs_oneclass,
        batch_size=payload.batch_size,
        lr=payload.lr,
        use_mlflow=payload.mlflow,
    )

    return {
        "status": "training_started",
        "message": "Bank-grade pipeline training started in background",
        "stages": ["classifier (EfficientNetV2-S)", "siamese", "oneclass"],
        "parameters": payload.model_dump(),
    }
