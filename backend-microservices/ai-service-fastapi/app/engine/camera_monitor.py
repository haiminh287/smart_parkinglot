"""
Camera Monitor Worker — Periodically scan cameras and detect slot occupancy.

Runs as a background asyncio task inside the FastAPI application.
Fetches camera→slot mappings from parking-service, captures frames,
runs slot detection, and pushes status updates via realtime-service.

Usage (in main.py lifespan):
    from app.engine.camera_monitor import start_camera_monitor, stop_camera_monitor

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await start_camera_monitor()
        yield
        await stop_camera_monitor()
"""

import asyncio
import logging
from typing import Optional

import httpx

from app.config import settings
from app.engine.camera_capture import get_camera_capture, CameraCaptureError
from app.engine.slot_detection import SlotBbox, get_slot_detector
from app.schemas.ai import OccupancyDetectionResponse

logger = logging.getLogger(__name__)

# Configuration
SCAN_INTERVAL_S = 30  # Seconds between full scans
GATEWAY_SECRET = settings.GATEWAY_SECRET
PARKING_SERVICE_URL = settings.PARKING_SERVICE_URL
REALTIME_SERVICE_URL = settings.REALTIME_SERVICE_URL

_monitor_task: Optional[asyncio.Task] = None
_running = False


async def start_camera_monitor() -> None:
    """Start the background camera monitor task.

    Safe to call multiple times — only one task will run.
    """
    global _monitor_task, _running

    if _monitor_task is not None and not _monitor_task.done():
        logger.info("Camera monitor already running.")
        return

    _running = True
    _monitor_task = asyncio.create_task(_monitor_loop())
    logger.info("Camera monitor started (interval=%ds).", SCAN_INTERVAL_S)


async def stop_camera_monitor() -> None:
    """Stop the background camera monitor task gracefully."""
    global _monitor_task, _running

    _running = False
    if _monitor_task is not None:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
        _monitor_task = None
    logger.info("Camera monitor stopped.")


async def _monitor_loop() -> None:
    """Main monitoring loop — runs until stopped."""
    while _running:
        try:
            await _scan_all_cameras()
        except Exception as exc:
            logger.error("Camera monitor scan failed: %s", exc, exc_info=True)
        await asyncio.sleep(SCAN_INTERVAL_S)


async def _scan_all_cameras() -> None:
    """Fetch active cameras, capture frames, detect slots, push updates."""
    cameras = await _fetch_active_cameras()
    if not cameras:
        logger.debug("No active cameras to scan.")
        return

    capture = get_camera_capture()
    detector = get_slot_detector()

    for camera in cameras:
        camera_id = camera.get("id", "unknown")
        stream_url = camera.get("streamUrl") or camera.get("stream_url", "")
        if not stream_url:
            continue

        # Get slots with bounding boxes for this camera
        slots = await _fetch_camera_slots(camera_id)
        if not slots:
            continue

        # Capture frame
        try:
            frame = await capture.capture_frame(stream_url)
        except CameraCaptureError as exc:
            logger.warning("Failed to capture from camera %s: %s", camera_id, exc)
            continue

        # Detect occupancy — YOLO inference is CPU-bound; run in thread pool
        loop = asyncio.get_event_loop()
        result: OccupancyDetectionResponse = await loop.run_in_executor(
            None, detector.detect_occupancy, frame, slots, str(camera_id)
        )

        # Push updates for changed slots
        await _push_slot_updates(result)


async def _fetch_active_cameras() -> list[dict]:
    """Fetch active cameras from parking-service.

    Returns:
        List of camera dicts with id, streamUrl, zoneId.
    """
    url = f"{PARKING_SERVICE_URL}/parking/cameras/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params={"status": "online"})
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", data) if isinstance(data, dict) else data
    except Exception as exc:
        logger.warning("Failed to fetch cameras: %s", exc)
    return []


async def _fetch_camera_slots(camera_id: str) -> list[SlotBbox]:
    """Fetch slots monitored by a specific camera from parking-service.

    Args:
        camera_id: Camera UUID.

    Returns:
        List of SlotBbox objects with bounding box coordinates.
    """
    url = f"{PARKING_SERVICE_URL}/parking/slots/"
    headers = {"X-Gateway-Secret": GATEWAY_SECRET}
    params = {"camera_id": camera_id}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = data.get("results", data) if isinstance(data, dict) else data

            slot_bboxes: list[SlotBbox] = []
            for slot in results:
                x1 = slot.get("x1")
                y1 = slot.get("y1")
                x2 = slot.get("x2")
                y2 = slot.get("y2")
                if all(v is not None for v in [x1, y1, x2, y2]):
                    slot_bboxes.append(SlotBbox(
                        slot_id=str(slot.get("id", "")),
                        slot_code=slot.get("code", ""),
                        zone_id=str(slot.get("zone", slot.get("zoneId", ""))),
                        x1=int(x1),
                        y1=int(y1),
                        x2=int(x2),
                        y2=int(y2),
                    ))
            return slot_bboxes
    except Exception as exc:
        logger.warning("Failed to fetch slots for camera %s: %s", camera_id, exc)
    return []


async def _push_slot_updates(result: OccupancyDetectionResponse) -> None:
    """Push slot status updates to parking-service and realtime-service.

    Only updates slots whose detected status is known and confidence is sufficient.

    Args:
        result: OccupancyDetectionResponse with per-slot results.
    """
    headers = {"X-Gateway-Secret": GATEWAY_SECRET, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for slot_result in result.slots:
            if slot_result.status == "unknown":
                continue
            if slot_result.confidence < 0.6:
                continue

            new_status = slot_result.status  # already a string: "available" or "occupied"

            # Update parking-service slot status
            if new_status == 'available':
                try:
                    check_resp = await client.get(
                        f"{PARKING_SERVICE_URL}/parking/slots/{slot_result.slot_id}/",
                        headers=headers,
                    )
                    if check_resp.status_code == 200:
                        if check_resp.json().get('status') == 'reserved':
                            logger.debug(
                                "Skipping camera update: slot %s is reserved",
                                slot_result.slot_code
                            )
                            continue
                except Exception:
                    pass  # If fetch fails, allow the update

            try:
                resp = await client.patch(
                    f"{PARKING_SERVICE_URL}/parking/slots/{slot_result.slot_id}/update-status/",
                    headers=headers,
                    json={"status": new_status},
                )
                if resp.status_code not in (200, 204):
                    logger.debug(
                        "Slot %s status update returned %d",
                        slot_result.slot_code, resp.status_code,
                    )
            except Exception as exc:
                logger.warning("Failed to update slot %s: %s", slot_result.slot_code, exc)

            # Broadcast via realtime-service
            try:
                await client.post(
                    f"{REALTIME_SERVICE_URL}/api/broadcast/slot-status/",
                    headers=headers,
                    json={
                        "slotId": slot_result.slot_id,
                        "zoneId": slot_result.zone_id,
                        "status": new_status,
                        "confidence": slot_result.confidence,
                        "source": "ai_detection",
                    },
                )
            except Exception as exc:
                logger.debug("Failed to broadcast slot update: %s", exc)
