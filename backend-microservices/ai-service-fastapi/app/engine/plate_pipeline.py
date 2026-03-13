"""
License Plate Recognition Pipeline.

Full flow:
  1. YOLO detect plate region
  2. Blur / quality check
  3. OCR read text (TrOCR → EasyOCR → Tesseract)
  4. Format validation & normalization
  5. Return structured result with confidence + warnings
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

import cv2
import numpy as np

from app.engine.plate_detector import LicensePlateDetector, PlateDetectionResult
from app.engine.plate_ocr import read_plate_text, OCRResult

logger = logging.getLogger(__name__)


class PlateReadDecision(str, Enum):
    SUCCESS = "success"               # plate read, format valid, high confidence
    LOW_CONFIDENCE = "low_confidence" # plate read but low confidence
    INVALID_FORMAT = "invalid_format" # text read but fails plate format
    BLURRY = "blurry"                 # image too blurry to read
    NOT_FOUND = "not_found"           # YOLO could not find a plate
    ERROR = "error"


@dataclass
class PlatePipelineResult:
    decision: PlateReadDecision
    plate_text: str                   # e.g. "51A-224.56" (empty if not found)
    confidence: float                 # 0.0–1.0
    detection_confidence: float       # YOLO confidence
    ocr_result: Optional[OCRResult]
    detection_result: Optional[PlateDetectionResult]
    warning: Optional[str]
    message: str
    processing_time_ms: float = 0.0


class PlatePipeline:
    """
    End-to-end license plate recognition pipeline.
    Singleton: loaded once, reused across requests.
    """

    def __init__(self, model_path: Optional[str] = None):
        self._detector = LicensePlateDetector(model_path=model_path)
        logger.info("PlatePipeline initialized")

    def process(self, img_bytes: bytes) -> PlatePipelineResult:
        """
        Process raw image bytes, return plate recognition result.
        """
        import time
        t0 = time.time()

        # Decode image
        try:
            arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Cannot decode image")
        except Exception as e:
            return PlatePipelineResult(
                decision=PlateReadDecision.ERROR,
                plate_text="", confidence=0.0,
                detection_confidence=0.0,
                ocr_result=None, detection_result=None,
                warning=None,
                message=f"Lỗi đọc ảnh: {e}",
                processing_time_ms=(time.time() - t0) * 1000,
            )

        # Stage 1: Detect plate region
        det = self._detector.detect(img, conf_threshold=0.20)
        if not det.found or det.cropped is None:
            return PlatePipelineResult(
                decision=PlateReadDecision.NOT_FOUND,
                plate_text="", confidence=0.0,
                detection_confidence=0.0,
                ocr_result=None, detection_result=det,
                warning="⚠️ Không tìm thấy biển số xe trong ảnh. Vui lòng chụp rõ biển số.",
                message="No plate region detected",
                processing_time_ms=(time.time() - t0) * 1000,
            )

        plate_img = det.cropped

        # Stage 2: OCR
        ocr = read_plate_text(plate_img)

        elapsed_ms = (time.time() - t0) * 1000

        # Stage 3: Decide result
        det_conf = det.box.confidence if det.box else 0.0

        if ocr.is_blurry and ocr.confidence < 0.4:
            return PlatePipelineResult(
                decision=PlateReadDecision.BLURRY,
                plate_text=ocr.text,
                confidence=ocr.confidence,
                detection_confidence=det_conf,
                ocr_result=ocr, detection_result=det,
                warning=ocr.warning or "⚠️ Ảnh biển số quá mờ. Vui lòng chụp lại gần hơn và rõ hơn.",
                message="Image too blurry for reliable OCR",
                processing_time_ms=elapsed_ms,
            )

        if not ocr.text:
            return PlatePipelineResult(
                decision=PlateReadDecision.NOT_FOUND,
                plate_text="",
                confidence=0.0,
                detection_confidence=det_conf,
                ocr_result=ocr, detection_result=det,
                warning=ocr.warning or "⚠️ Không đọc được ký tự biển số. Vui lòng chụp lại.",
                message="OCR returned no text",
                processing_time_ms=elapsed_ms,
            )

        if not ocr.is_valid_format:
            return PlatePipelineResult(
                decision=PlateReadDecision.INVALID_FORMAT,
                plate_text=ocr.text,
                confidence=ocr.confidence,
                detection_confidence=det_conf,
                ocr_result=ocr, detection_result=det,
                warning=ocr.warning or f"⚠️ Định dạng biển số không hợp lệ: '{ocr.text}'",
                message="Plate text does not match Vietnamese plate format",
                processing_time_ms=elapsed_ms,
            )

        if ocr.confidence < 0.55:
            return PlatePipelineResult(
                decision=PlateReadDecision.LOW_CONFIDENCE,
                plate_text=ocr.text,
                confidence=ocr.confidence,
                detection_confidence=det_conf,
                ocr_result=ocr, detection_result=det,
                warning=ocr.warning or f"⚠️ Độ tin cậy thấp ({ocr.confidence:.0%}). Biển số đọc được: {ocr.text} — vui lòng xác nhận.",
                message="Low confidence read",
                processing_time_ms=elapsed_ms,
            )

        return PlatePipelineResult(
            decision=PlateReadDecision.SUCCESS,
            plate_text=ocr.text,
            confidence=ocr.confidence,
            detection_confidence=det_conf,
            ocr_result=ocr, detection_result=det,
            warning=ocr.warning,  # may still have blur warning with valid read
            message=f"Biển số xe: {ocr.text}",
            processing_time_ms=elapsed_ms,
        )


# ------------ Singleton accessor ------------------------------------------ #
_pipeline_instance: Optional[PlatePipeline] = None


def get_plate_pipeline(model_path: Optional[str] = None) -> PlatePipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = PlatePipeline(model_path=model_path)
    return _pipeline_instance
