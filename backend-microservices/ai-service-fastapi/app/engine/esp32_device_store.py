"""
In-memory ESP32 device registry.

Stores device info (IP, firmware, status, GPIO config, logs) for all
registered ESP32 boards.  Populated at startup by ``seed_default_devices()``
and kept current by heartbeat / auto-registration during gate activity.
"""

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from app.schemas.esp32_device import ESP32DeviceResponse

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────── #

DEVICE_OFFLINE_TIMEOUT_S = 30  # Device considered offline after this many seconds
MAX_LOGS_PER_DEVICE = 100  # Circular buffer size per device

# ── In-Memory Device Store ───────────────────────────────────────────────── #
# Structure: { device_id: { "ip": str, "firmware": str, "status": str,
#   "gpio_config": dict|None, "registered_at": datetime, "last_seen": datetime,
#   "wifi_rssi": int|None, "logs": deque[dict] } }
esp32_devices: dict[str, dict] = {}


def seed_default_devices() -> None:
    """Pre-populate the in-memory ESP32 device registry with default gate devices.

    Called once at application startup so the admin ESP32 management page
    always shows the two gate controllers even before the physical ESP32
    boards send their first HTTP request.
    """
    now = datetime.now(timezone.utc)
    defaults = [
        {
            "device_id": "GATE-IN-01",
            "ip": "192.168.100.194",
            "firmware": "v1.0.0-parksmart",
            "status": "ready",
            "gpio_config": {"checkInPin": 4, "checkOutPin": 5},
        },
        {
            "device_id": "GATE-OUT-01",
            "ip": "192.168.100.194",
            "firmware": "v1.0.0-parksmart",
            "status": "ready",
            "gpio_config": {"checkInPin": 4, "checkOutPin": 5},
        },
    ]
    for d in defaults:
        did = d["device_id"]
        if did in esp32_devices:
            continue
        logs: deque = deque(maxlen=MAX_LOGS_PER_DEVICE)
        logs.append(
            {
                "timestamp": now,
                "level": "info",
                "message": f"Device {did} pre-registered by AI Service startup.",
            }
        )
        esp32_devices[did] = {
            "ip": d["ip"],
            "firmware": d["firmware"],
            "status": d["status"],
            "gpio_config": d["gpio_config"],
            "registered_at": now,
            "last_seen": now,
            "wifi_rssi": -45,
            "logs": logs,
        }
        logger.info("ESP32 pre-seeded at startup: %s", did)


def auto_register_device(gate_id: str) -> None:
    """Auto-register or refresh an ESP32 device when it calls check-in/check-out.

    This ensures devices show up in the /devices list even if the ESP32
    firmware never calls the explicit /register endpoint.  If the device
    already exists, only ``last_seen`` and ``status`` are updated.
    """
    now = datetime.now(timezone.utc)
    device = esp32_devices.get(gate_id)
    if device is not None:
        # Already registered — just refresh heartbeat
        device["last_seen"] = now
        device["status"] = "ready"
        return

    # First time seeing this gate_id — create minimal entry
    esp32_devices[gate_id] = {
        "ip": "auto-detected",
        "firmware": "auto-registered",
        "status": "ready",
        "gpio_config": None,
        "registered_at": now,
        "last_seen": now,
        "wifi_rssi": None,
        "logs": deque(maxlen=MAX_LOGS_PER_DEVICE),
    }
    logger.info("ESP32 auto-registered via gate activity: device_id=%s", gate_id)


def is_device_online(device: dict) -> bool:
    """Check if a device is online based on last_seen timestamp."""
    elapsed = (datetime.now(timezone.utc) - device["last_seen"]).total_seconds()
    return elapsed <= DEVICE_OFFLINE_TIMEOUT_S


def build_device_response(device_id: str, device: dict) -> ESP32DeviceResponse:
    """Build an ESP32DeviceResponse from the internal device dict."""
    return ESP32DeviceResponse(
        device_id=device_id,
        ip=device["ip"],
        firmware=device["firmware"],
        status=device["status"],
        gpio_config=device.get("gpio_config"),
        registered_at=device["registered_at"],
        last_seen=device["last_seen"],
        is_online=is_device_online(device),
        wifi_rssi=device.get("wifi_rssi"),
        log_count=len(device.get("logs", [])),
    )
