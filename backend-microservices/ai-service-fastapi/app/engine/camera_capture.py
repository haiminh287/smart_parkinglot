"""
Camera Capture Module — Capture frames from IP cameras.

Supports:
  - MJPEG streams (DroidCam / IP Webcam)
  - RTSP streams (security cameras)
  - HTTP snapshot URLs

Usage:
    capture = CameraCapture()
    frame = await capture.capture_frame("http://192.168.100.130:4747/video")
"""

import asyncio
import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── RTSP / EZVIZ requires TCP transport via FFMPEG ───────────────────────── #
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

# Default timeout for camera operations (seconds)
DEFAULT_TIMEOUT_S = 10
MAX_RETRIES = 3
RETRY_DELAY_S = 0.5


class CameraCaptureError(Exception):
    """Raised when camera capture fails."""


class CameraCapture:
    """Capture frames from IP cameras via OpenCV.

    Supports MJPEG, RTSP, and HTTP snapshot sources.
    Thread-safe: each capture opens/releases its own VideoCapture.
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT_S) -> None:
        self._timeout = timeout

    async def capture_frame(
        self,
        stream_url: str,
        retries: int = MAX_RETRIES,
    ) -> np.ndarray:
        """Capture a single frame from the camera stream.

        Args:
            stream_url: Camera URL (MJPEG, RTSP, or HTTP snapshot).
            retries: Number of retry attempts on failure.

        Returns:
            BGR numpy array of the captured frame.

        Raises:
            CameraCaptureError: If capture fails after all retries.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, retries + 1):
            try:
                frame = await asyncio.get_event_loop().run_in_executor(
                    None, self._capture_sync, stream_url
                )
                logger.info(
                    "Camera capture success: %s (attempt %d, shape=%s)",
                    stream_url, attempt, frame.shape,
                )
                return frame
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Camera capture attempt %d/%d failed for %s: %s",
                    attempt, retries, stream_url, exc,
                )
                if attempt < retries:
                    await asyncio.sleep(RETRY_DELAY_S)

        raise CameraCaptureError(
            f"Failed to capture frame from {stream_url} after {retries} attempts: {last_error}"
        )

    def _capture_sync(self, stream_url: str) -> np.ndarray:
        """Synchronous capture — runs in thread executor.

        Uses CAP_FFMPEG backend for RTSP streams (required for EZVIZ cameras).
        """
        # Use FFMPEG backend for RTSP to support TCP transport
        if stream_url.startswith("rtsp://"):
            cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            cap.release()
            raise CameraCaptureError(f"Cannot open camera stream: {stream_url}")

        try:
            # Set timeout via properties
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(self._timeout * 1000))
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(self._timeout * 1000))

            # Grab a few frames to get a fresh one (skip buffered frames)
            for _ in range(3):
                cap.grab()

            ret, frame = cap.read()
            if not ret or frame is None:
                raise CameraCaptureError(
                    f"Failed to read frame from {stream_url}"
                )
            return frame
        finally:
            cap.release()

    async def capture_frame_bytes(
        self,
        stream_url: str,
        retries: int = MAX_RETRIES,
    ) -> bytes:
        """Capture a frame and return as JPEG bytes.

        Args:
            stream_url: Camera URL.
            retries: Number of retry attempts.

        Returns:
            JPEG-encoded bytes of the captured frame.

        Raises:
            CameraCaptureError: If capture or encoding fails.
        """
        frame = await self.capture_frame(stream_url, retries=retries)
        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not success:
            raise CameraCaptureError("Failed to encode frame as JPEG")
        return buffer.tobytes()


    async def scan_qr_loop(
        self,
        stream_url: str,
        qr_reader: object,
        timeout_s: float = 30.0,
        interval_s: float = 0.5,
    ) -> tuple[np.ndarray, str]:
        """Continuously capture frames and scan for QR code until found or timeout.

        Opens the camera stream once and keeps reading frames,
        trying to decode QR from each frame.

        Args:
            stream_url: Camera stream URL.
            qr_reader: QRReader instance with read_from_frame(frame) method.
            timeout_s: Max seconds to keep scanning.
            interval_s: Delay between frame captures.

        Returns:
            Tuple of (frame with QR, decoded QR text).

        Raises:
            CameraCaptureError: If camera cannot be opened or timeout.
        """
        result = await asyncio.get_event_loop().run_in_executor(
            None, self._scan_qr_loop_sync, stream_url, qr_reader,
            timeout_s, interval_s,
        )
        return result

    def _scan_qr_loop_sync(
        self,
        stream_url: str,
        qr_reader: object,
        timeout_s: float,
        interval_s: float,
    ) -> tuple[np.ndarray, str]:
        """Synchronous QR scan loop — runs in thread executor."""
        if stream_url.startswith("rtsp://"):
            cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(stream_url)

        if not cap.isOpened():
            cap.release()
            raise CameraCaptureError(
                f"Cannot open QR camera stream: {stream_url}"
            )

        start = time.time()
        frame_count = 0
        try:
            while (time.time() - start) < timeout_s:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(interval_s)
                    continue

                frame_count += 1
                # Try to decode QR from this frame
                qr_text = qr_reader.read_from_frame(frame)  # type: ignore[attr-defined]
                if qr_text:
                    elapsed = time.time() - start
                    logger.info(
                        "QR found after %.1fs (%d frames): %s",
                        elapsed, frame_count, qr_text[:80],
                    )
                    return frame, qr_text

                if frame_count % 10 == 0:
                    logger.debug(
                        "QR scan: %d frames, %.1fs elapsed, no QR yet...",
                        frame_count, time.time() - start,
                    )
                time.sleep(interval_s)
        finally:
            cap.release()

        raise CameraCaptureError(
            f"QR scan timeout ({timeout_s}s, {frame_count} frames). "
            "Vui lòng đưa mã QR vào trước camera."
        )


# Singleton instance
_camera_capture: Optional[CameraCapture] = None


def get_camera_capture(timeout: float = DEFAULT_TIMEOUT_S) -> CameraCapture:
    """Get or create the singleton CameraCapture instance.

    Args:
        timeout: Timeout in seconds for camera operations.

    Returns:
        CameraCapture singleton.
    """
    global _camera_capture
    if _camera_capture is None:
        _camera_capture = CameraCapture(timeout=timeout)
    return _camera_capture
