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
import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
from app.config import settings
from app.engine.camera_capture import CameraCaptureError, get_camera_capture
from app.engine.plate_pipeline import get_plate_pipeline
from app.engine.qr_reader import QRReadError, get_qr_reader
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/cameras", tags=["cameras"])

# ── Default camera config (from env via Settings) ────────────────────────── #
DEFAULT_PLATE_CAMERA_URL = settings.CAMERA_RTSP_URL
DEFAULT_QR_CAMERA_URL = f"{settings.CAMERA_DROIDCAM_URL}/video"

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

# ── Virtual cameras (frames pushed from Unity) ───────────────────────────── #


@dataclass
class VirtualFrame:
    jpeg_data: bytes
    timestamp: float  # time.monotonic()
    camera_id: str


_virtual_frame_buffer: dict[str, VirtualFrame] = {}
_buffer_lock = threading.Lock()
_STALE_THRESHOLD = 30  # seconds

VIRTUAL_CAMERAS = [
    {
        "id": "virtual-f1-overview",
        "name": "Floor 1 Overview (Virtual)",
        "zone": "Floor 1",
        "floor": 1,
        "type": "virtual",
        "description": "Tổng quan tầng 1 — giám sát tất cả ô đỗ xe",
    },
    {
        "id": "virtual-f2-overview",
        "name": "Floor 2 Overview (Virtual)",
        "zone": "Floor 2",
        "floor": 2,
        "type": "virtual",
        "description": "Tổng quan tầng 2 — giám sát tất cả ô đỗ xe",
    },
    {
        "id": "virtual-gate-in",
        "name": "Entry Gate (Virtual)",
        "zone": "Cổng vào",
        "floor": 1,
        "type": "virtual",
        "description": "Camera ảo cổng vào — giám sát xe check-in",
    },
    {
        "id": "virtual-gate-out",
        "name": "Exit Gate (Virtual)",
        "zone": "Cổng ra",
        "floor": 1,
        "type": "virtual",
        "description": "Camera ảo cổng ra — giám sát xe check-out",
    },
    {
        "id": "virtual-zone-south",
        "name": "Zone South (Virtual)",
        "zone": "South",
        "floor": 1,
        "type": "virtual",
        "description": "Camera ảo khu vực phía Nam — giám sát ô đỗ xe",
    },
    {
        "id": "virtual-zone-north",
        "name": "Zone North (Virtual)",
        "zone": "North",
        "floor": 1,
        "type": "virtual",
        "description": "Camera ảo khu vực phía Bắc — giám sát ô đỗ xe",
    },
    {
        "id": "virtual-anpr-entry",
        "name": "ANPR Entry (Virtual)",
        "zone": "Cổng vào",
        "floor": 1,
        "type": "virtual",
        "description": "Camera ANPR ảo cổng vào — nhận diện biển số xe vào",
    },
    {
        "id": "virtual-anpr-exit",
        "name": "ANPR Exit (Virtual)",
        "zone": "Cổng ra",
        "floor": 1,
        "type": "virtual",
        "description": "Camera ANPR ảo cổng ra — nhận diện biển số xe ra",
    },
]

_VALID_VIRTUAL_IDS = {cam["id"] for cam in VIRTUAL_CAMERAS}


def _build_offline_jpeg() -> bytes:
    """Generate a small 320x240 gray JPEG with 'Camera Offline' text."""
    import numpy as np

    frame = np.full((240, 320, 3), 40, dtype=np.uint8)  # dark gray
    cv2.putText(
        frame,
        "CAMERA OFFLINE",
        (30, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (180, 180, 180),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Unity not running",
        (60, 145),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (120, 120, 120),
        1,
        cv2.LINE_AA,
    )
    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    return buf.tobytes()


_OFFLINE_JPEG: bytes = _build_offline_jpeg()


@router.get("/list")
async def list_cameras():
    """Return configured cameras (safe — no credentials in response)."""
    all_cameras = CAMERAS + VIRTUAL_CAMERAS
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
        for cam in all_cameras
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


@router.post("/frame")
async def receive_frame(
    request: Request,
    x_camera_id: str = Header(..., alias="X-Camera-ID"),
    x_gateway_secret: str = Header(..., alias="X-Gateway-Secret"),
):
    """Receive a JPEG frame from Unity for a virtual camera."""
    if x_gateway_secret != settings.GATEWAY_SECRET:
        raise HTTPException(401, "Invalid gateway secret")
    if x_camera_id not in _VALID_VIRTUAL_IDS:
        raise HTTPException(400, f"Unknown virtual camera: {x_camera_id}")

    body = await request.body()
    if len(body) == 0:
        raise HTTPException(400, "Empty frame data")
    if len(body) > 500_000:
        raise HTTPException(413, "Frame too large (max 500KB)")

    with _buffer_lock:
        _virtual_frame_buffer[x_camera_id] = VirtualFrame(
            jpeg_data=body, timestamp=time.monotonic(), camera_id=x_camera_id
        )

    logger.debug("Received frame from %s: %d bytes", x_camera_id, len(body))
    return {"success": True, "camera_id": x_camera_id, "size": len(body)}


@router.get("/snapshot")
async def camera_snapshot(
    camera_id: Optional[str] = Query(None, description="Camera ID"),
    url: Optional[str] = Query(None, description="Direct camera URL (RTSP/HTTP)"),
):
    """Return a single JPEG frame from the specified camera."""
    if camera_id and camera_id.startswith("virtual-"):
        with _buffer_lock:
            vf = _virtual_frame_buffer.get(camera_id)
        if vf and (time.monotonic() - vf.timestamp) < _STALE_THRESHOLD:
            return Response(
                content=vf.jpeg_data,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        return Response(
            content=_OFFLINE_JPEG,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Camera-Status": "offline",
            },
        )

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


@router.get("/read-plate")
async def read_plate_from_camera(
    camera_id: str = Query(..., description="Virtual camera ID (e.g. virtual-gate-in)"),
):
    """Run license-plate OCR on the latest virtual camera frame.

    Useful for gate cameras where the vehicle plate faces the lens.
    Returns plate text, confidence, and decision from the plate pipeline.
    """
    if not camera_id.startswith("virtual-"):
        raise HTTPException(
            status_code=400, detail="Only virtual cameras are supported"
        )
    with _buffer_lock:
        vf = _virtual_frame_buffer.get(camera_id)
    if not vf or (time.monotonic() - vf.timestamp) >= _STALE_THRESHOLD:
        raise HTTPException(
            status_code=503, detail="No fresh frame available for this camera"
        )
    pipeline = get_plate_pipeline(model_path=settings.PLATE_MODEL_PATH)
    result = pipeline.process(vf.jpeg_data)
    return {
        "camera_id": camera_id,
        "plate_text": result.plate_text,
        "confidence": round(result.confidence, 3),
        "decision": result.decision,
        "processing_time_ms": round(result.processing_time_ms, 1),
        "warning": result.warning,
    }


@router.get("/stream")
async def camera_stream(
    camera_id: Optional[str] = Query(None, description="Camera ID"),
    url: Optional[str] = Query(None, description="Direct camera URL (RTSP/HTTP)"),
    fps: int = Query(5, ge=1, le=30, description="Target FPS"),
):
    """Return an MJPEG stream (multipart/x-mixed-replace) for live viewing.

    The browser can use this URL directly in an <img> tag.
    Accepts either a known *camera_id* or an arbitrary *url* to proxy.
    For virtual cameras, frames are served from the in-memory buffer.
    """
    if camera_id and camera_id.startswith("virtual-"):
        return StreamingResponse(
            _virtual_camera_stream_gen(camera_id, fps),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={
                "Cache-Control": "no-cache, no-store",
                "Connection": "keep-alive",
            },
        )

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
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
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


async def _virtual_camera_stream_gen(camera_id: str, fps: int):
    """Async generator that yields MJPEG frames from the virtual buffer."""
    interval = 1.0 / fps
    while True:
        with _buffer_lock:
            vf = _virtual_frame_buffer.get(camera_id)
        if vf and (time.monotonic() - vf.timestamp) < _STALE_THRESHOLD:
            frame_data = vf.jpeg_data
        else:
            frame_data = _OFFLINE_JPEG
        yield (
            b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n"
        )
        await asyncio.sleep(interval)


@router.get("/scan-qr")
async def scan_qr_from_camera(
    camera_id: Optional[str] = Query(
        "qr-camera-droidcam", description="Camera ID to scan QR from"
    ),
    url: Optional[str] = Query(None, description="Direct camera URL override"),
):
    """Capture one frame from camera and decode QR code. No auth required.

    Frontend polls this every 1-2 seconds while the QR scan modal is open.
    Returns immediately — does NOT wait/loop.

    Returns:
        {"found": bool, "qr_data": str|null, "booking_id": str|null, "error": str|null}
    """
    import json as _json

    # Get frame bytes
    if camera_id and camera_id.startswith("virtual-"):
        with _buffer_lock:
            vf = _virtual_frame_buffer.get(camera_id)
        if not vf or (time.monotonic() - vf.timestamp) > _STALE_THRESHOLD:
            return {
                "found": False,
                "qr_data": None,
                "booking_id": None,
                "error": "No recent virtual frame",
            }
        frame_bytes = vf.jpeg_data
    else:
        cam_url = _resolve_camera_url(camera_id, url)
        capture = get_camera_capture(timeout=5)
        try:
            frame_bytes = await capture.capture_frame_bytes(cam_url, retries=1)
        except CameraCaptureError as exc:
            return {
                "found": False,
                "qr_data": None,
                "booking_id": None,
                "error": str(exc),
            }

    # Decode QR
    qr_reader = get_qr_reader()
    try:
        qr_text = await asyncio.to_thread(qr_reader.read_from_bytes, frame_bytes)
    except Exception as exc:
        return {"found": False, "qr_data": None, "booking_id": None, "error": str(exc)}

    if not qr_text:
        return {"found": False, "qr_data": None, "booking_id": None, "error": None}

    # Parse booking ID
    booking_id = None
    try:
        data = _json.loads(qr_text)
        booking_id = data.get("booking_id") or data.get("id") or data.get("bookingId")
    except Exception:
        booking_id = qr_text.strip()  # Plain text = booking ID

    return {
        "found": True,
        "qr_data": qr_text,
        "booking_id": str(booking_id) if booking_id else None,
        "error": None,
    }
