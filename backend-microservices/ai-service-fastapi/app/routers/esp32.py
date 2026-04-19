"""ESP32 Integration API — Thin router delegating to service modules."""

import hmac
import logging
from collections import deque
from datetime import datetime, timezone

import httpx
from app.config import settings
from app.database import get_db
from app.engine.camera_capture import get_camera_capture
from app.engine.esp32_device_store import (
    MAX_LOGS_PER_DEVICE, build_device_response, esp32_devices, seed_default_devices,
)
from app.schemas.esp32 import (
    CashPaymentRequest, ESP32CheckInRequest, ESP32CheckOutRequest,
    ESP32Response, ESP32VerifySlotRequest,
)
from app.schemas.esp32_device import (
    ESP32AckResponse, ESP32DeviceListResponse, ESP32DeviceLogsResponse,
    ESP32HeartbeatRequest, ESP32LogRequest, ESP32RegisterRequest, LogEntry,
)
from app.services.esp32_checkin_service import process_checkin
from app.services.esp32_checkout_service import process_checkout
from app.services.esp32_helpers import TEST_IMAGES_DIR
from app.services.esp32_payment_service import process_cash_payment
from app.services.esp32_verify_service import process_verify_slot
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def verify_device_token(x_device_token: str = Header(default="")) -> None:
    expected = settings.ESP32_DEVICE_TOKEN
    if not x_device_token or not hmac.compare_digest(x_device_token, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing device token.")


router = APIRouter(
    prefix="/ai/parking/esp32", tags=["esp32"],
    dependencies=[Depends(verify_device_token)],
)

# ── Core flow endpoints (delegate to service modules) ────────────────────── #


@router.post("/check-in/", response_model=ESP32Response)
async def esp32_check_in(payload: ESP32CheckInRequest, db: Session = Depends(get_db)):
    return await process_checkin(payload, db)


@router.post("/check-out/", response_model=ESP32Response)
async def esp32_check_out(payload: ESP32CheckOutRequest, db: Session = Depends(get_db)):
    return await process_checkout(payload, db)


@router.post("/verify-slot/", response_model=ESP32Response)
async def esp32_verify_slot(payload: ESP32VerifySlotRequest, db: Session = Depends(get_db)):
    return await process_verify_slot(payload, db)


@router.get("/pending-qr/")
async def esp32_pending_qr(status: str = "not_checked_in") -> dict:
    """Trả QR data + booking_id của booking mới nhất theo status cho ESP32 vật lý.

    Cho phép ESP32 tự pull QR giống Unity sim — tránh phải cắm QR scanner khi demo.
    - status=not_checked_in → dùng cho check-in button
    - status=checked_in     → dùng cho check-out button
    """
    url = f"{settings.BOOKING_SERVICE_URL}/bookings/"
    headers = {"X-Gateway-Secret": settings.GATEWAY_SECRET, "X-User-ID": "system"}
    params = {"check_in_status": status, "limit": 1, "ordering": "-created_at"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"booking-service error: {resp.text[:120]}",
                )
            results = resp.json().get("results", [])
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"booking-service unreachable: {exc}")

    if not results:
        raise HTTPException(status_code=404, detail=f"No {status} bookings available")

    b = results[0]
    car_slot = b.get("carSlot") or {}
    return {
        "booking_id": b.get("id"),
        "qr_data": b.get("qrCodeData") or b.get("qr_code_data") or "",
        "slot_code": car_slot.get("code") if isinstance(car_slot, dict) else None,
        "zone_id": car_slot.get("zoneId") if isinstance(car_slot, dict) else None,
        "license_plate": (b.get("vehicle") or {}).get("licensePlate"),
    }


@router.post("/cash-payment/", response_model=ESP32Response)
async def esp32_cash_payment(payload: CashPaymentRequest, db: Session = Depends(get_db)):
    return await process_cash_payment(payload, db)


# ── Status endpoint ──────────────────────────────────────────────────────── #


@router.get("/status/")
async def esp32_status() -> dict:
    """Health check + camera connectivity + test images status."""
    cameras_status: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.PARKING_SERVICE_URL}/parking/cameras/",
                headers={"X-Gateway-Secret": settings.GATEWAY_SECRET},
            )
            if resp.status_code == 200:
                data = resp.json()
                cameras = data.get("results", data) if isinstance(data, dict) else data
                capture = get_camera_capture()
                for cam in cameras:
                    stream = cam.get("streamUrl") or cam.get("stream_url") or ""
                    reachable = False
                    if stream:
                        try:
                            await capture.capture_frame(stream, retries=1)
                            reachable = True
                        except Exception:
                            pass
                    cameras_status.append({"name": cam.get("name", "unknown"), "url": stream, "reachable": reachable})
    except Exception as exc:
        logger.warning("Failed to check cameras: %s", exc)

    test_images = [f.name for f in TEST_IMAGES_DIR.glob("*") if f.suffix.lower() in (".jpg", ".jpeg", ".png")] if TEST_IMAGES_DIR.exists() else []
    return {
        "status": "healthy", "service": "esp32-integration",
        "cameras": cameras_status, "test_images": test_images,
        "test_images_dir": str(TEST_IMAGES_DIR),
        "fallback_mode": len(cameras_status) == 0 or all(not c["reachable"] for c in cameras_status),
    }


# ── Device management endpoints ──────────────────────────────────────────── #


@router.post("/register", response_model=ESP32AckResponse)
async def esp32_register(body: ESP32RegisterRequest) -> ESP32AckResponse:
    """ESP32 registers itself on boot."""
    now = datetime.now(timezone.utc)
    gpio_dict = body.gpio_config.model_dump() if body.gpio_config else None
    existing_logs = esp32_devices.get(body.device_id, {}).get("logs", deque(maxlen=MAX_LOGS_PER_DEVICE))
    esp32_devices[body.device_id] = {
        "ip": body.ip, "firmware": body.firmware, "status": "ready",
        "gpio_config": gpio_dict, "registered_at": now, "last_seen": now,
        "wifi_rssi": None, "logs": existing_logs,
    }
    logger.info("ESP32 registered: device_id=%s ip=%s", body.device_id, body.ip)
    return ESP32AckResponse(success=True, message=f"Device '{body.device_id}' registered successfully.")


@router.post("/heartbeat", response_model=ESP32AckResponse)
async def esp32_heartbeat(body: ESP32HeartbeatRequest) -> ESP32AckResponse:
    """ESP32 periodic keepalive."""
    device = esp32_devices.get(body.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Device '{body.device_id}' not registered.")
    device["last_seen"] = datetime.now(timezone.utc)
    device["status"] = body.status
    if body.wifi_rssi is not None:
        device["wifi_rssi"] = body.wifi_rssi
    return ESP32AckResponse(success=True, message="Heartbeat received.")


@router.post("/log", response_model=ESP32AckResponse)
async def esp32_log(body: ESP32LogRequest) -> ESP32AckResponse:
    """Store a log entry from the ESP32."""
    device = esp32_devices.get(body.device_id)
    if device is None:
        now = datetime.now(timezone.utc)
        esp32_devices[body.device_id] = {
            "ip": "unknown", "firmware": "unknown", "status": "unknown",
            "gpio_config": None, "registered_at": now, "last_seen": now,
            "wifi_rssi": None, "logs": deque(maxlen=MAX_LOGS_PER_DEVICE),
        }
        device = esp32_devices[body.device_id]
    device["last_seen"] = datetime.now(timezone.utc)
    device["logs"].append({"timestamp": datetime.now(timezone.utc), "level": body.level, "message": body.message})
    log_fn = {"debug": logger.debug, "info": logger.info, "warn": logger.warning, "error": logger.error}.get(body.level, logger.info)
    log_fn("ESP32 [%s] %s", body.device_id, body.message)
    return ESP32AckResponse(success=True, message="Log recorded.")


@router.get("/devices", response_model=ESP32DeviceListResponse)
async def esp32_list_devices() -> ESP32DeviceListResponse:
    """List all registered ESP32 devices."""
    devices = [build_device_response(did, dev) for did, dev in esp32_devices.items()]
    return ESP32DeviceListResponse(count=len(devices), devices=devices)


@router.get("/devices/{device_id}/logs", response_model=ESP32DeviceLogsResponse)
async def esp32_device_logs(device_id: str) -> ESP32DeviceLogsResponse:
    """Get logs for a specific ESP32 device."""
    device = esp32_devices.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")
    logs = [LogEntry(timestamp=e["timestamp"], level=e["level"], message=e["message"]) for e in device["logs"]]
    return ESP32DeviceLogsResponse(device_id=device_id, count=len(logs), logs=logs)
