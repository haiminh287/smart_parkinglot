"""
Camera Streaming Router — Live snapshot & MJPEG stream for frontend monitoring.

Endpoints:
  GET /ai/cameras/snapshot     — Returns a single JPEG frame from a camera
  GET /ai/cameras/stream       — Returns MJPEG stream (multipart) for live viewing
  GET /ai/cameras/list         — Returns configured cameras

The default camera is the EZVIZ plate-reading camera.
These endpoints bypass gateway auth to allow frontend <img> tags to load them.
"""

import asyncio
import logging
import time
from typing import Optional

import cv2

from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse

from app.engine.camera_capture import get_camera_capture, CameraCaptureError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/cameras", tags=["cameras"])

# ── Default camera config ────────────────────────────────────────────────── #
DEFAULT_PLATE_CAMERA_URL = "rtsp://admin:XGIMBN@192.168.100.23:554/ch1/main"
DEFAULT_QR_CAMERA_URL = "http://192.168.100.130:4747/video"

CAMERAS = [
    {
        "id": "plate-camera-ezviz",
        "name": "Camera Biển Số (EZVIZ)",
        "zone": "Cổng vào",
        "floor": 1,
        "type": "plate",
        "stream_url": DEFAULT_PLATE_CAMERA_URL,
        "description": "Camera EZVIZ đọc biển số xe tại cổng check-in/check-out",
    },
    {
        "id": "qr-camera-droidcam",
        "name": "Camera QR Code (DroidCam)",
        "zone": "Cổng vào",
        "floor": 1,
        "type": "qr",
        "stream_url": DEFAULT_QR_CAMERA_URL,
        "description": "Camera DroidCam quét mã QR check-in/check-out",
    },
]


@router.get("/list")
async def list_cameras():
    """Return configured cameras (safe — no credentials in response)."""
    return [
        {
            "id": cam["id"],
            "name": cam["name"],
            "zone": cam["zone"],
            "floor": cam["floor"],
            "type": cam["type"],
            "description": cam["description"],
            "snapshotUrl": f"/ai/cameras/snapshot?camera_id={cam['id']}",
            "streamUrl": f"/ai/cameras/stream?camera_id={cam['id']}",
        }
        for cam in CAMERAS
    ]


def _resolve_camera_url(
    camera_id: Optional[str] = None,
    url: Optional[str] = None,
) -> str:
    """Resolve camera_id or direct URL to a stream URL.

    Priority: explicit *url* > *camera_id* lookup > default camera.
    """
    if url:
        return url
    if camera_id:
        for cam in CAMERAS:
            if cam["id"] == camera_id:
                return cam["stream_url"]
    return DEFAULT_PLATE_CAMERA_URL


@router.get("/snapshot")
async def camera_snapshot(
    camera_id: Optional[str] = Query(None, description="Camera ID"),
    url: Optional[str] = Query(None, description="Direct camera URL (RTSP/HTTP)"),
):
    """Return a single JPEG frame from the specified camera."""
    stream_url = _resolve_camera_url(camera_id, url)
    capture = get_camera_capture(timeout=8)
    try:
        jpeg_bytes = await capture.capture_frame_bytes(stream_url, retries=2)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    except CameraCaptureError as exc:
        logger.warning("Snapshot failed for %s: %s", camera_id or "default", exc)
        return Response(content=b"", status_code=503)


@router.get("/stream")
async def camera_stream(
    camera_id: Optional[str] = Query(None, description="Camera ID"),
    url: Optional[str] = Query(None, description="Direct camera URL (RTSP/HTTP)"),
    fps: int = Query(5, ge=1, le=30, description="Target FPS"),
):
    """Return an MJPEG stream (multipart/x-mixed-replace) for live viewing.

    The browser can use this URL directly in an <img> tag.
    Accepts either a known *camera_id* or an arbitrary *url* to proxy.
    """
    stream_url = _resolve_camera_url(camera_id, url)
    interval = 1.0 / fps

    async def generate():
        capture = get_camera_capture(timeout=8)
        while True:
            t0 = time.monotonic()
            try:
                jpeg_bytes = await capture.capture_frame_bytes(stream_url, retries=1)
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + jpeg_bytes
                    + b"\r\n"
                )
            except CameraCaptureError:
                # Skip frame on error, wait and retry
                await asyncio.sleep(1)
                continue
            elapsed = time.monotonic() - t0
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store",
            "Connection": "keep-alive",
        },
    )
