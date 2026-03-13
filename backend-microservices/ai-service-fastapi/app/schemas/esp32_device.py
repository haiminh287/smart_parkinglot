"""
Pydantic v2 schemas for ESP32 device registration, heartbeat, and log endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import CamelModel


# ── Request Schemas ──────────────────────────────────────────────────────── #


class GPIOConfig(CamelModel):
    """GPIO pin configuration for an ESP32 gate controller."""
    check_in_pin: Optional[int] = Field(None, description="GPIO pin for check-in button")
    check_out_pin: Optional[int] = Field(None, description="GPIO pin for check-out button")


class ESP32RegisterRequest(BaseModel):
    """ESP32 registers itself when it boots up."""
    device_id: str = Field(..., min_length=1, max_length=64, description="Unique device ID, e.g. gate-1")
    ip: str = Field(..., description="Device IP address on local network")
    firmware: str = Field("1.0", description="Firmware version string")
    gpio_config: Optional[GPIOConfig] = Field(None, description="GPIO pin mapping")


class ESP32HeartbeatRequest(BaseModel):
    """ESP32 sends periodic heartbeat to report it's alive."""
    device_id: str = Field(..., min_length=1, max_length=64, description="Unique device ID")
    status: str = Field("ready", description="Device status: ready, busy, error")
    wifi_rssi: Optional[int] = Field(None, description="WiFi signal strength in dBm")


class ESP32LogRequest(BaseModel):
    """ESP32 sends a log message."""
    device_id: str = Field(..., min_length=1, max_length=64, description="Unique device ID")
    level: str = Field("info", description="Log level: debug, info, warn, error")
    message: str = Field(..., max_length=500, description="Log message text")


# ── Response Schemas ─────────────────────────────────────────────────────── #


class LogEntry(CamelModel):
    """Single log entry from an ESP32 device."""
    timestamp: datetime
    level: str
    message: str


class ESP32DeviceResponse(CamelModel):
    """Represents a registered ESP32 device."""
    device_id: str
    ip: str
    firmware: str
    status: str
    gpio_config: Optional[dict] = None
    registered_at: datetime
    last_seen: datetime
    is_online: bool
    wifi_rssi: Optional[int] = None
    log_count: int = 0


class ESP32DeviceListResponse(CamelModel):
    """List of all registered ESP32 devices."""
    count: int
    devices: list[ESP32DeviceResponse]


class ESP32DeviceLogsResponse(CamelModel):
    """Log entries for a specific ESP32 device."""
    device_id: str
    count: int
    logs: list[LogEntry]


class ESP32AckResponse(CamelModel):
    """Simple acknowledgement response for ESP32 POST endpoints."""
    success: bool
    message: str
