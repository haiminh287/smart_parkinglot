"""
Unit tests for 🔥 Improvement 2.5: Proactive cooldown + priority value objects.
"""

import pytest

from app.domain.value_objects.proactive import NotificationPriority, CooldownConfig


class TestNotificationPriority:

    def test_priority_values(self):
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.MEDIUM.value == "medium"
        assert NotificationPriority.LOW.value == "low"


class TestCooldownConfig:

    def test_default_cooldowns(self):
        config = CooldownConfig()
        assert config.HIGH_PRIORITY_COOLDOWN == 5
        assert config.MEDIUM_PRIORITY_COOLDOWN == 30
        assert config.LOW_PRIORITY_COOLDOWN == 120

    def test_get_cooldown_high(self):
        config = CooldownConfig()
        assert config.get_cooldown(NotificationPriority.HIGH) == 5

    def test_get_cooldown_medium(self):
        config = CooldownConfig()
        assert config.get_cooldown(NotificationPriority.MEDIUM) == 30

    def test_get_cooldown_low(self):
        config = CooldownConfig()
        assert config.get_cooldown(NotificationPriority.LOW) == 120

    def test_user_active_suppress(self):
        config = CooldownConfig()
        assert config.USER_ACTIVE_SUPPRESS_MINUTES == 5

    def test_max_per_hour(self):
        config = CooldownConfig()
        assert config.MAX_PER_HOUR == 5

    def test_custom_config(self):
        config = CooldownConfig(
            HIGH_PRIORITY_COOLDOWN=2,
            MEDIUM_PRIORITY_COOLDOWN=10,
            LOW_PRIORITY_COOLDOWN=60,
            MAX_PER_HOUR=3,
        )
        assert config.get_cooldown(NotificationPriority.HIGH) == 2
        assert config.MAX_PER_HOUR == 3
