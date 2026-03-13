"""
QR Code Reader Module — Decode QR codes from camera frames.

Supports:
  - Reading from numpy arrays (camera frames)
  - Reading from raw image bytes
  - Multiple QR codes in one frame (returns first valid)
  - JSON payload parsing for ParkSmart booking QR codes

QR Data Format:
  {
    "booking_id": "uuid",
    "user_id": "uuid",
    "vehicle_license_plate": "51A-224.56",
    "slot_code": "A-01"
  }
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class QRReadError(Exception):
    """Raised when QR reading fails."""


@dataclass
class QRPayload:
    """Parsed QR code data from a ParkSmart booking QR."""

    raw_text: str
    booking_id: str
    user_id: str
    vehicle_license_plate: Optional[str] = None
    slot_code: Optional[str] = None

    @classmethod
    def from_json(cls, raw_text: str) -> "QRPayload":
        """Parse QR code text into QRPayload.

        Supports two formats:
          1. JSON: {"booking_id":"uuid","user_id":"uuid",...}
          2. Plain booking ID string (UUID or any ID)

        When only booking_id is available, user_id defaults to "system"
        for inter-service lookups.

        Args:
            raw_text: Raw text from QR code.

        Returns:
            Parsed QRPayload instance.

        Raises:
            QRReadError: If text is empty or JSON is invalid.
        """
        text = raw_text.strip()
        if not text:
            raise QRReadError("QR code text is empty")

        # Try JSON first
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                booking_id = (
                    data.get("booking_id")
                    or data.get("id")
                    or data.get("bookingId")
                )
                user_id = data.get("user_id") or data.get("userId") or "system"

                if not booking_id:
                    raise QRReadError(
                        "QR JSON missing booking_id. "
                        f"Got keys: {list(data.keys())}"
                    )

                return cls(
                    raw_text=raw_text,
                    booking_id=str(booking_id),
                    user_id=str(user_id),
                    vehicle_license_plate=data.get("vehicle_license_plate") or data.get("licensePlate"),
                    slot_code=data.get("slot_code") or data.get("slotCode"),
                )
        except json.JSONDecodeError:
            pass  # Not JSON — treat as plain booking ID

        # Plain text = booking ID only
        logger.info("QR contains plain booking ID: %s", text[:80])
        return cls(
            raw_text=raw_text,
            booking_id=text,
            user_id="system",
        )


class QRReader:
    """Read and decode QR codes from images using OpenCV.

    Uses cv2.QRCodeDetector for QR decoding — no external dependencies needed.
    Falls back to multi-detector if single detection fails.
    """

    def __init__(self) -> None:
        self._detector = cv2.QRCodeDetector()

    def read_from_frame(self, frame: np.ndarray) -> Optional[str]:
        """Read QR code text from a BGR numpy array.

        Args:
            frame: BGR image (numpy array) from camera capture.

        Returns:
            Decoded QR text, or None if no QR found.
        """
        if frame is None or frame.size == 0:
            return None

        # Try single QR detection first
        text, points, _ = self._detector.detectAndDecode(frame)
        if text and text.strip():
            logger.info("QR detected (single): %s", text[:80])
            return text.strip()

        # Try with grayscale + enhanced contrast
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.equalizeHist(gray)
        text, points, _ = self._detector.detectAndDecode(enhanced)
        if text and text.strip():
            logger.info("QR detected (enhanced): %s", text[:80])
            return text.strip()

        # Try multi-QR detector as fallback
        try:
            multi_detector = cv2.QRCodeDetectorAruco()
            retval, decoded_info, points, _ = multi_detector.detectAndDecodeMulti(frame)
            if retval and decoded_info:
                for info in decoded_info:
                    if info and info.strip():
                        logger.info("QR detected (multi): %s", info[:80])
                        return info.strip()
        except AttributeError:
            # QRCodeDetectorAruco not available in older OpenCV versions
            pass

        return None

    def read_from_bytes(self, img_bytes: bytes) -> Optional[str]:
        """Read QR code from raw image bytes.

        Args:
            img_bytes: JPEG/PNG image bytes.

        Returns:
            Decoded QR text, or None if no QR found.
        """
        arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None
        return self.read_from_frame(frame)

    def read_booking_qr(self, frame: np.ndarray) -> QRPayload:
        """Read and parse a ParkSmart booking QR code from a camera frame.

        Args:
            frame: BGR image from camera.

        Returns:
            Parsed QRPayload with booking_id, user_id, etc.

        Raises:
            QRReadError: If no QR found or data is invalid.
        """
        text = self.read_from_frame(frame)
        if not text:
            raise QRReadError(
                "Không tìm thấy QR code trong ảnh. "
                "Vui lòng đặt mã QR vào trước camera."
            )
        return QRPayload.from_json(text)

    def read_booking_qr_from_bytes(self, img_bytes: bytes) -> QRPayload:
        """Read and parse a ParkSmart booking QR code from image bytes.

        Args:
            img_bytes: JPEG/PNG image bytes.

        Returns:
            Parsed QRPayload.

        Raises:
            QRReadError: If no QR found or data is invalid.
        """
        text = self.read_from_bytes(img_bytes)
        if not text:
            raise QRReadError("Không tìm thấy QR code trong ảnh.")
        return QRPayload.from_json(text)


# Singleton
_qr_reader: Optional[QRReader] = None


def get_qr_reader() -> QRReader:
    """Get or create the singleton QRReader instance.

    Returns:
        QRReader singleton.
    """
    global _qr_reader
    if _qr_reader is None:
        _qr_reader = QRReader()
    return _qr_reader
