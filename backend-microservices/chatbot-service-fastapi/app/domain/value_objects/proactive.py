"""
🔥 CẢI TIẾN 2.5: Notification Priority & Cooldown — tránh spam user.

priority: HIGH / MEDIUM / LOW
cooldown: per user, per event_type
suppression: nếu user vừa active
"""

from enum import Enum
from dataclasses import dataclass


class NotificationPriority(str, Enum):
    HIGH = "high"       # slot maintenance, booking expired
    MEDIUM = "medium"   # no check-in reminder, conflict
    LOW = "low"         # weather, tips, suggestions


@dataclass
class CooldownConfig:
    """Per-event-type cooldown rules."""
    # Default cooldowns in minutes
    DEFAULT_COOLDOWN_MINUTES: int = 30
    HIGH_PRIORITY_COOLDOWN: int = 5     # HIGH: allow re-notify quickly
    MEDIUM_PRIORITY_COOLDOWN: int = 30  # MEDIUM: 30 min gap
    LOW_PRIORITY_COOLDOWN: int = 120    # LOW: 2 hour gap

    # Suppress if user had activity within N minutes
    USER_ACTIVE_SUPPRESS_MINUTES: int = 5

    # Max notifications per user per hour
    MAX_PER_HOUR: int = 5

    def get_cooldown(self, priority: NotificationPriority) -> int:
        """Get cooldown in minutes based on priority."""
        mapping = {
            NotificationPriority.HIGH: self.HIGH_PRIORITY_COOLDOWN,
            NotificationPriority.MEDIUM: self.MEDIUM_PRIORITY_COOLDOWN,
            NotificationPriority.LOW: self.LOW_PRIORITY_COOLDOWN,
        }
        return mapping.get(priority, self.DEFAULT_COOLDOWN_MINUTES)
