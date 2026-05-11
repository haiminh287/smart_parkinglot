"""
License Plate OCR Engine.

Priority order:
  1. TrOCR  — Microsoft transformer OCR, best for Vietnamese 2-row plates
  2. EasyOCR — fallback if TrOCR not available or fails
  3. Tesseract — last resort

Post-processing:
  - Vietnamese plate format validation: e.g. 51A-224.56 / 30K-123.45 / 29B1-123.45
  - Blur / quality detection before OCR
  - Confidence scoring with uncertainty warnings
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Vietnamese license plate patterns
# --------------------------------------------------------------------------- #
# Two-row plate: 51A / 224.56 → normalize to 51A-224.56
# Standard:  \d{2}[A-Z]\d?-\d{3}\.\d{2}   e.g.  51A-224.56, 30K1-123.45
# Motorbike: same pattern on two rows
PLATE_PATTERNS = [
    # Full standard: 51A-224.56
    re.compile(r"^(\d{2}[A-Z]\d?)[.\-\s]?(\d{3}[.\-]\d{2})$"),
    # Without separator: 51A22456
    re.compile(r"^(\d{2}[A-Z]\d?)(\d{5})$"),
    # Special series: 51A-12345
    re.compile(r"^(\d{2}[A-Z]\d?)[.\-\s]?(\d{5})$"),
]


def _normalize_plate(raw: str) -> str:
    """Clean OCR artifacts and normalize to standard format."""
    # Remove spaces, lowercase O→0, I→1, common OCR errors
    text = raw.upper().strip()
    text = text.replace(" ", "").replace("\n", "").replace("\t", "")
    # Strip leading non-alphanumeric chars (TrOCR sometimes prepends : ; , etc.)
    text = re.sub(r"^[^A-Z0-9]+", "", text)
    # Normalize OCR misread of separator (* is never valid, must be -)
    text = text.replace("*", "-")
    # Normalize digit-lookalike letters in province code (first 2 chars only)
    if len(text) >= 2:
        prov_digit_map = {
            "O": "0",
            "Q": "0",
            "I": "1",
            "L": "1",
            "Z": "2",
            "S": "5",
            "G": "6",
            "B": "8",
        }
        province = "".join(prov_digit_map.get(c, c) for c in text[:2])
        text = province + text[2:]
    # OCR common substitutions on plates
    ocr_map = {
        "O": "0",
        "Q": "0",
        "D": "0",
        "I": "1",
        "L": "1",
        "Z": "2",
        "S": "5",
        "$": "5",
        "G": "6",
        "B": "8",
    }
    # Only apply digit-area substitutions (after the letter portion)
    # Find letter prefix (2 digits + 1-2 letters)
    m = re.match(r"^(\d{2}[A-Z]{1,2}\d?)", text)
    if m:
        prefix = m.group(1)
        rest = text[len(prefix) :]
        # In the number area, apply OCR map
        cleaned_rest = ""
        for ch in rest:
            cleaned_rest += ocr_map.get(ch, ch)
        text = prefix + cleaned_rest
    return text


def _validate_plate(text: str) -> Tuple[bool, str]:
    """
    Validate and reformat plate text.
    Returns (is_valid, normalized_plate).
    """
    text = _normalize_plate(text)
    for pat in PLATE_PATTERNS:
        m = pat.match(text)
        if m:
            prefix, number = m.group(1), m.group(2)
            # Reformat number: ensure xxx.xx
            number_clean = re.sub(r"[.\-]", "", number)
            if len(number_clean) == 5:
                formatted = f"{prefix}-{number_clean[:3]}.{number_clean[3:]}"
                return True, formatted
            elif len(number_clean) == 4:
                formatted = f"{prefix}-{number_clean}"
                return True, formatted
    return False, text


# --------------------------------------------------------------------------- #
# Blur / quality detection
# --------------------------------------------------------------------------- #
def _laplacian_variance(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _is_blurry(img: np.ndarray, threshold: float = 80.0) -> bool:
    return _laplacian_variance(img) < threshold


# --------------------------------------------------------------------------- #
# Pre-processing for better OCR
# --------------------------------------------------------------------------- #
def _preprocess_plate(img: np.ndarray) -> np.ndarray:
    """Enhance plate image for OCR: resize, CLAHE, denoise, binarize."""
    h, w = img.shape[:2]
    target_h = 64
    scale = target_h / h
    new_w = int(w * scale)
    resized = cv2.resize(img, (new_w, target_h), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def _scale_for_trocr(img: np.ndarray) -> np.ndarray:
    """
    Scale plate image to TrOCR-friendly size.
    TrOCR works well at ~200px height with clear characters.
    """
    h, w = img.shape[:2]
    if h < 50:
        scale = max(3, 100 // h)
        img = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_LANCZOS4)
    return img


# --------------------------------------------------------------------------- #
# Result dataclass
# --------------------------------------------------------------------------- #
@dataclass
class OCRResult:
    text: str  # e.g. "51A-224.56"
    raw_texts: List[str]  # all candidate texts from OCR
    confidence: float  # 0.0 – 1.0
    is_valid_format: bool
    is_blurry: bool
    blur_score: float  # Laplacian variance (higher = sharper)
    method: str  # "trocr" / "easyocr" / "tesseract" / "none"
    warning: Optional[str] = None
    candidates: List[dict] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# OCR runners
# --------------------------------------------------------------------------- #
_trocr_model = None
_trocr_processor = None
_easy_ocr = None


def _get_trocr():
    """Lazy-load TrOCR model (microsoft/trocr-base-printed)."""
    global _trocr_model, _trocr_processor
    if _trocr_model is None:
        try:
            import torch  # noqa: F401
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel

            logger.info("Loading TrOCR model...")
            _trocr_processor = TrOCRProcessor.from_pretrained(
                "microsoft/trocr-base-printed",
                use_fast=True,
            )
            _trocr_model = VisionEncoderDecoderModel.from_pretrained(
                "microsoft/trocr-base-printed"
            )
            _trocr_model.eval()
            logger.info("✅ TrOCR loaded")
        except ImportError:
            logger.warning("⚠️  transformers not installed — TrOCR unavailable")
        except Exception as e:
            logger.warning(f"⚠️  TrOCR load error: {e}")
    return _trocr_processor, _trocr_model


def _run_trocr(img_bgr: np.ndarray) -> List[Tuple[str, float]]:
    """
    Run TrOCR on a BGR plate crop.
    TrOCR doesn't provide per-token confidence; use 0.90 as proxy for a read result.
    """
    processor, model = _get_trocr()
    if processor is None or model is None:
        return []
    try:
        import torch
        from PIL import Image

        img_scaled = _scale_for_trocr(img_bgr)
        rgb = cv2.cvtColor(img_scaled, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated_ids = model.generate(pixel_values, max_new_tokens=20)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[
            0
        ].strip()

        if text:
            logger.debug(f"TrOCR raw: {text!r}")
            return [(text, 0.90)]
        return []
    except Exception as e:
        logger.warning(f"TrOCR inference error: {e}")
        return []


def _get_easy_ocr():
    global _easy_ocr
    if _easy_ocr is None:
        try:
            import easyocr

            _easy_ocr = easyocr.Reader(["en"], gpu=False, verbose=False)
            logger.info("✅ EasyOCR loaded")
        except ImportError:
            logger.warning("⚠️  EasyOCR not installed")
    return _easy_ocr


def _run_easyocr(img_bgr: np.ndarray) -> List[Tuple[str, float]]:
    reader = _get_easy_ocr()
    if reader is None:
        return []
    try:
        results = reader.readtext(img_bgr, detail=1, paragraph=False)
        return [(r[1], float(r[2])) for r in results]
    except Exception as e:
        logger.warning(f"EasyOCR error: {e}")
        return []


def _run_tesseract(img_binary: np.ndarray) -> List[Tuple[str, float]]:
    try:
        import pytesseract

        config = "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        text = pytesseract.image_to_string(img_binary, config=config).strip()
        if text:
            return [(text, 0.5)]
    except Exception as e:
        logger.warning(f"Tesseract error: {e}")
    return []


# --------------------------------------------------------------------------- #
# Main OCR function
# --------------------------------------------------------------------------- #
def read_plate_text(plate_img: np.ndarray) -> OCRResult:
    """
    Read text from a cropped license plate image (BGR numpy array).

    Pipeline:
      1. TrOCR (Transformer OCR) — best for small/2-row Vietnamese plates
      2. EasyOCR — fallback
      3. Tesseract — last resort
    """
    blur_score = _laplacian_variance(plate_img)
    is_blurry_flag = blur_score < 80.0

    all_candidates: List[Tuple[str, float]] = []
    method = "none"

    # ---- 1. TrOCR (primary) ----
    trocr_results = _run_trocr(plate_img)
    if trocr_results:
        all_candidates.extend(trocr_results)
        method = "trocr"
        logger.info(f"TrOCR results: {trocr_results}")

    # ---- 2. EasyOCR (fallback) ----
    if not all_candidates:
        easy_results = _run_easyocr(plate_img)
        if easy_results:
            all_candidates.extend(easy_results)
            method = "easyocr"
            logger.info(f"EasyOCR results: {easy_results}")

    # ---- 3. Tesseract (last resort) ----
    if not all_candidates:
        processed_binary = _preprocess_plate(plate_img)
        tess_results = _run_tesseract(processed_binary)
        if tess_results:
            all_candidates.extend(tess_results)
            method = "tesseract"

    # ---- No results ----
    if not all_candidates:
        warning = "Không thể đọc biển số xe. "
        if is_blurry_flag:
            warning += (
                f"Ảnh quá mờ (blur_score={blur_score:.1f}). Vui lòng chụp lại rõ hơn."
            )
        else:
            warning += "Không tìm thấy ký tự nào trên biển số."
        return OCRResult(
            text="",
            raw_texts=[],
            confidence=0.0,
            is_valid_format=False,
            is_blurry=is_blurry_flag,
            blur_score=blur_score,
            method="none",
            warning=warning,
        )

    # ---- Validate ----
    raw_texts = [c[0] for c in all_candidates]

    # Try combined text first
    combined_text = "".join(raw_texts).upper().strip()
    is_valid, formatted = _validate_plate(combined_text)

    # If combined fails, try each candidate individually
    best_conf = 0.0
    if not is_valid:
        for raw_text, conf in sorted(all_candidates, key=lambda x: x[1], reverse=True):
            v, f = _validate_plate(raw_text)
            if v:
                is_valid, formatted = True, f
                best_conf = conf
                break

    avg_conf = (
        best_conf
        if best_conf > 0
        else (sum(c[1] for c in all_candidates) / len(all_candidates))
    )

    # ---- Build warning ----
    warning = None
    if is_blurry_flag:
        warning = f"Ảnh mờ (blur_score={blur_score:.1f}) — kết quả có thể không chính xác. Vui lòng chụp lại."
    elif avg_conf < 0.6:
        warning = f"Độ tin cậy thấp ({avg_conf:.0%}) — vui lòng xác nhận lại biển số."
    if not is_valid:
        note = f" Định dạng biển số không hợp lệ: '{formatted}'"
        warning = (
            (warning + note)
            if warning
            else f"Định dạng biển số không nhận ra: '{formatted}'. Vui lòng nhập thủ công."
        )

    return OCRResult(
        text=formatted,
        raw_texts=raw_texts,
        confidence=min(avg_conf, 1.0),
        is_valid_format=is_valid,
        is_blurry=is_blurry_flag,
        blur_score=blur_score,
        method=method,
        warning=warning,
        candidates=[{"text": t, "confidence": c} for t, c in all_candidates],
    )
