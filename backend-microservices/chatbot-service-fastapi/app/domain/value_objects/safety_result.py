"""
🔥 CẢI TIẾN 2.3: SafetyResult — trả reason code thay vì bool.

SafetyResult(ok, code, hint, details) → FE, logging, analytics đều hưởng lợi.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SafetyCode(str, Enum):
    """Machine-readable safety violation codes."""
    OK = "OK"
    SLOT_NOT_AVAILABLE = "SLOT_NOT_AVAILABLE"
    DOUBLE_BOOKING = "DOUBLE_BOOKING"
    OUT_OF_OPERATING_HOURS = "OUT_OF_OPERATING_HOURS"
    VEHICLE_NOT_FOUND = "VEHICLE_NOT_FOUND"
    BOOKING_NOT_FOUND = "BOOKING_NOT_FOUND"
    ALREADY_CHECKED_IN = "ALREADY_CHECKED_IN"
    NOT_CHECKED_IN = "NOT_CHECKED_IN"
    BOOKING_EXPIRED = "BOOKING_EXPIRED"
    MAX_BOOKINGS_REACHED = "MAX_BOOKINGS_REACHED"
    INVALID_TIME_RANGE = "INVALID_TIME_RANGE"


@dataclass
class SafetyResult:
    """
    Result of safety validation.

    ok=True  → safe to proceed
    ok=False → blocked, with machine code + human hint + extra details
    """
    ok: bool = True
    code: SafetyCode = SafetyCode.OK
    hint: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def safe(cls) -> "SafetyResult":
        return cls(ok=True, code=SafetyCode.OK)

    @classmethod
    def blocked(cls, code: SafetyCode, hint: str, **details: Any) -> "SafetyResult":
        return cls(ok=False, code=code, hint=hint, details=details)
