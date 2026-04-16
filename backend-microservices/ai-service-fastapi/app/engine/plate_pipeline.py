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
from datetime import datetime
from enum import Enum
from typing import Optional, List

import cv2
import numpy as np

from app.engine.plate_detector import LicensePlateDetector, PlateDetectionResult
from app.engine.plate_ocr import read_plate_text, OCRResult
from app.config import settings

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
        self._debug_dir = os.path.join(settings.MEDIA_ROOT, "plate_debug")
        logger.info("PlatePipeline initialized")

    def _save_debug_step(self, img: np.ndarray, debug_id: str, step: int, label: str) -> None:
        if not settings.DEBUG or img is None:
            return
        try:
            os.makedirs(self._debug_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"{ts}_{debug_id}" if debug_id else ts
            filename = f"{prefix}_step{step}_{label}.jpg"
            filepath = os.path.join(self._debug_dir, filename)
            cv2.imwrite(filepath, img)
            logger.debug("Debug image saved: %s", filepath)
        except Exception as e:
            logger.warning("Failed to save debug image step%d_%s: %s", step, label, e)

    def process(self, img_bytes: bytes, debug_id: str = "") -> PlatePipelineResult:
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

        # Debug step 0: original image
        self._save_debug_step(img, debug_id, 0, "original")

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

        # Debug step 1: YOLO detection visualization
        if settings.DEBUG and det.box:
            det_vis = img.copy()
            b = det.box
            cv2.rectangle(det_vis, (b.x1, b.y1), (b.x2, b.y2), (0, 255, 0), 2)
            cv2.putText(det_vis, f"plate {b.confidence:.2f}", (b.x1, b.y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            self._save_debug_step(det_vis, debug_id, 1, "yolo_detect")

        # Debug step 2: cropped plate
        self._save_debug_step(plate_img, debug_id, 2, "plate_crop")

        # Stage 2: OCR
        ocr = read_plate_text(plate_img)

        # Debug step 3: pre-processed grayscale version of plate
        if settings.DEBUG and plate_img is not None:
            try:
                gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                self._save_debug_step(enhanced, debug_id, 3, "preprocess")
            except Exception:
                pass

        elapsed_ms = (time.time() - t0) * 1000

        # Stage 3: Decide result
        det_conf = det.box.confidence if det.box else 0.0

        # Debug step 4: result annotation (prepared before returning)
        def _save_result_debug(decision_text: str, plate_text: str, conf: float) -> None:
            if not settings.DEBUG or det.box is None:
                return
            try:
                res_vis = img.copy()
                b = det.box
                cv2.rectangle(res_vis, (b.x1, b.y1), (b.x2, b.y2), (0, 255, 0), 2)
                label = f"{plate_text} ({conf:.0%}) [{decision_text}]"
                cv2.putText(res_vis, label, (b.x1, b.y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                self._save_debug_step(res_vis, debug_id, 4, "result")
            except Exception:
                pass

        if ocr.is_blurry and ocr.confidence < 0.4:
            _save_result_debug("blurry", ocr.text, ocr.confidence)
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
            _save_result_debug("no_text", "", 0.0)
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
            _save_result_debug("invalid_fmt", ocr.text, ocr.confidence)
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
            _save_result_debug("low_conf", ocr.text, ocr.confidence)
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

        _save_result_debug("success", ocr.text, ocr.confidence)
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
