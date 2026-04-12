"""
Pipeline Orchestrator — Hybrid MVP (Color-First + AI Fallback).

Pipeline flow:
  Stage 0: Preprocessing (quality gate + white balance)
  Stage 1: Banknote Detection (YOLOv8n / full-image fallback)
  Stage 2A: Color-Based Denomination (HSV)
  Dynamic Confidence Check → PASS → Final Output
                           → FAIL → Stage 2B: AI Classifier (MobileNetV3)
  Final Decision
"""

import os
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

from app.engine.preprocessing import preprocess, QualityResult, QualityStatus
from app.engine.detector import BanknoteDetector, DetectionResult as DetResult
from app.engine.color_classifier import (
    classify_by_color,
    meets_threshold,
    ColorClassification,
)
from app.engine.ai_classifier import BanknoteAIClassifier, AIClassification, DENOMINATION_CLASSES

logger = logging.getLogger(__name__)


class PipelineDecision(str, Enum):
    """Final decision of the pipeline."""
    ACCEPT = "accept"
    LOW_CONFIDENCE = "low_confidence"
    NO_BANKNOTE = "no_banknote"
    BAD_QUALITY = "bad_quality"
    ERROR = "error"


class ClassificationMethod(str, Enum):
    """Which method produced the final result."""
    COLOR = "color"
    AI_FALLBACK = "ai_fallback"
    NONE = "none"


@dataclass
class PipelineResult:
    """Complete result from the banknote recognition pipeline."""
    decision: PipelineDecision
    denomination: Optional[str] = None
    confidence: float = 0.0
    method: ClassificationMethod = ClassificationMethod.NONE
    quality_result: Optional[QualityResult] = None
    detection_result: Optional[DetResult] = None
    color_result: Optional[ColorClassification] = None
    ai_result: Optional[AIClassification] = None
    all_probabilities: Optional[dict[str, float]] = None
    processing_time_ms: float = 0.0
    stages_executed: list[str] = field(default_factory=list)
    message: str = ""


_pipeline_singleton: Optional["BanknoteRecognitionPipeline"] = None


def get_banknote_pipeline(model_dir: str = "/app/ml/models") -> "BanknoteRecognitionPipeline":
    """Get or create the singleton BanknoteRecognitionPipeline.

    Args:
        model_dir: Directory containing model weight files.

    Returns:
        Shared BanknoteRecognitionPipeline instance.
    """
    global _pipeline_singleton
    if _pipeline_singleton is None:
        _pipeline_singleton = BanknoteRecognitionPipeline(model_dir=model_dir)
    return _pipeline_singleton


class BanknoteRecognitionPipeline:
    """
    Hybrid MVP pipeline for Vietnamese banknote recognition.

    Usage:
        pipeline = BanknoteRecognitionPipeline(model_dir="/app/ml/models")
        result = pipeline.process(image_bgr)
    """

    def __init__(self, model_dir: str = "/app/ml/models"):
        self._model_dir = model_dir

        # Initialize Stage 1: Detector
        yolo_path = os.path.join(model_dir, "banknote_yolov8n.pt")
        self._detector = BanknoteDetector(
            model_path=yolo_path if os.path.exists(yolo_path) else None
        )

        # Initialize Stage 2B: AI Classifier
        ai_path = os.path.join(model_dir, "banknote_mobilenetv3.pth")
        self._ai_classifier = BanknoteAIClassifier(
            model_path=ai_path if os.path.exists(ai_path) else None
        )

        logger.info(
            f"Pipeline initialized (model_dir={model_dir}, "
            f"yolo={'loaded' if self._detector._model else 'fallback'}, "
            f"ai={'loaded' if self._ai_classifier._model else 'stub'})"
        )

    def process(self, img: np.ndarray) -> PipelineResult:
        """
        Run the full hybrid pipeline on an input image.
        """
        start = time.time()
        stages: list[str] = []

        # ── Stage 0: Preprocessing ──────────────────
        stages.append("preprocessing")
        try:
            corrected, quality = preprocess(img)
        except Exception as e:
            logger.error(f"Preprocessing error: {e}", exc_info=True)
            return PipelineResult(
                decision=PipelineDecision.ERROR,
                processing_time_ms=(time.time() - start) * 1000,
                stages_executed=stages,
                message=f"Preprocessing failed: {e}",
            )

        # If quality is too bad, we still try but warn
        if quality.status in (QualityStatus.BLURRY, QualityStatus.UNDEREXPOSED, QualityStatus.OVEREXPOSED):
            logger.warning(f"Quality issue: {quality.message}")

        # ── Stage 1: Banknote Detection ─────────────
        stages.append("detection")
        try:
            detection = self._detector.detect(corrected)
        except Exception as e:
            logger.error(f"Detection error: {e}", exc_info=True)
            return PipelineResult(
                decision=PipelineDecision.ERROR,
                quality_result=quality,
                processing_time_ms=(time.time() - start) * 1000,
                stages_executed=stages,
                message=f"Detection failed: {e}",
            )

        if not detection.found or detection.cropped is None:
            return PipelineResult(
                decision=PipelineDecision.NO_BANKNOTE,
                quality_result=quality,
                detection_result=detection,
                processing_time_ms=(time.time() - start) * 1000,
                stages_executed=stages,
                message="No banknote detected in image",
            )

        cropped = detection.cropped

        # ── Stage 2A: Color-Based Classification ────
        stages.append("color_classification")
        try:
            color_result = classify_by_color(cropped)
        except Exception as e:
            logger.error(f"Color classification error: {e}", exc_info=True)
            color_result = ColorClassification(
                denomination=None, confidence=0.0, dominant_hue=0.0,
                group=None, all_scores={}, message=f"Color classification failed: {e}",
            )

        # ── Dynamic Confidence Check ────────────────
        if meets_threshold(color_result):
            elapsed = (time.time() - start) * 1000
            return PipelineResult(
                decision=PipelineDecision.ACCEPT,
                denomination=color_result.denomination,
                confidence=color_result.confidence,
                method=ClassificationMethod.COLOR,
                quality_result=quality,
                detection_result=detection,
                color_result=color_result,
                all_probabilities=color_result.all_scores,
                processing_time_ms=elapsed,
                stages_executed=stages,
                message=f"Color classification accepted: {color_result.denomination} VND",
            )

        # ── Out-of-vocabulary guard ─────────────────
        # If color detected a denomination the AI model was not trained on,
        # AI fallback will only make the result worse. Trust color instead.
        if (color_result.denomination
                and color_result.denomination not in DENOMINATION_CLASSES):
            elapsed = (time.time() - start) * 1000
            decision = (PipelineDecision.ACCEPT
                        if color_result.confidence >= 0.5
                        else PipelineDecision.LOW_CONFIDENCE)
            return PipelineResult(
                decision=decision,
                denomination=color_result.denomination,
                confidence=color_result.confidence,
                method=ClassificationMethod.COLOR,
                quality_result=quality,
                detection_result=detection,
                color_result=color_result,
                all_probabilities=color_result.all_scores,
                processing_time_ms=elapsed,
                stages_executed=stages,
                message=f"Color-only: {color_result.denomination} VND (not in AI vocabulary)",
            )

        # ── Stage 2B: AI Fallback ───────────────────
        stages.append("ai_fallback")
        try:
            ai_result = self._ai_classifier.classify(cropped)
        except Exception as e:
            logger.error(f"AI classification error: {e}", exc_info=True)
            ai_result = AIClassification(
                denomination=None, confidence=0.0,
                all_probabilities={}, message=f"AI classification failed: {e}",
            )

        # ── Final Decision ──────────────────────────
        elapsed = (time.time() - start) * 1000

        if ai_result.denomination and ai_result.confidence > 0.3:
            decision = PipelineDecision.ACCEPT
            message = f"AI fallback accepted: {ai_result.denomination} VND"
        else:
            decision = PipelineDecision.LOW_CONFIDENCE
            message = "Both color and AI classifiers have low confidence"

        return PipelineResult(
            decision=decision,
            denomination=ai_result.denomination,
            confidence=ai_result.confidence,
            method=ClassificationMethod.AI_FALLBACK,
            quality_result=quality,
            detection_result=detection,
            color_result=color_result,
            ai_result=ai_result,
            all_probabilities=ai_result.all_probabilities,
            processing_time_ms=elapsed,
            stages_executed=stages,
            message=message,
        )

    def process_fast(self, img: np.ndarray) -> PipelineResult:
        """
        Fast mode — skips AI fallback, only uses color classification.
        Average latency: ~3-5ms.
        """
        start = time.time()
        stages: list[str] = []

        # Stage 0
        stages.append("preprocessing")
        corrected, quality = preprocess(img)

        # Stage 1
        stages.append("detection")
        detection = self._detector.detect(corrected)

        if not detection.found or detection.cropped is None:
            return PipelineResult(
                decision=PipelineDecision.NO_BANKNOTE,
                quality_result=quality,
                detection_result=detection,
                processing_time_ms=(time.time() - start) * 1000,
                stages_executed=stages,
                message="No banknote detected in image",
            )

        # Stage 2A only
        stages.append("color_classification")
        color_result = classify_by_color(detection.cropped)

        elapsed = (time.time() - start) * 1000

        if meets_threshold(color_result):
            return PipelineResult(
                decision=PipelineDecision.ACCEPT,
                denomination=color_result.denomination,
                confidence=color_result.confidence,
                method=ClassificationMethod.COLOR,
                quality_result=quality,
                detection_result=detection,
                color_result=color_result,
                all_probabilities=color_result.all_scores,
                processing_time_ms=elapsed,
                stages_executed=stages,
                message=f"Fast mode: {color_result.denomination} VND",
            )

        return PipelineResult(
            decision=PipelineDecision.LOW_CONFIDENCE,
            denomination=color_result.denomination,
            confidence=color_result.confidence,
            method=ClassificationMethod.COLOR,
            quality_result=quality,
            detection_result=detection,
            color_result=color_result,
            all_probabilities=color_result.all_scores,
            processing_time_ms=elapsed,
            stages_executed=stages,
            message="Fast mode: low confidence (AI fallback skipped)",
        )
