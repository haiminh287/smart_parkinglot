"""
AI Service SQLAlchemy models — table names match Django tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, DateTime, JSON
from sqlalchemy.dialects.mysql import CHAR

from app.database import Base


class CameraFeed(Base):
    __tablename__ = "api_camerafeed"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(CHAR(36), nullable=False, index=True)
    frame_url = Column(Text, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
    detections = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class PredictionLog(Base):
    __tablename__ = "api_predictionlog"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prediction_type = Column(String(50), nullable=False, index=True)
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=False, index=True)
    processing_time = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "api_modelversion"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_type = Column(String(50), nullable=False)
    version = Column(String(50), nullable=False)
    file_path = Column(Text, default="")
    status = Column(String(20), default="training")  # training, testing, production, archived

    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    map50 = Column(Float, nullable=True)
    map50_95 = Column(Float, nullable=True)

    training_params = Column(JSON, default=dict)
    notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
