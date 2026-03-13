"""
Unit tests for 🔥 Improvement 2.4: Memory anti-noise rules.

Tests:
  - _should_update() returns False for noisy events
  - _should_update() returns True for valid updates
"""

import pytest

from app.application.services.memory_service import MemoryService


class TestMemoryAntiNoise:
    """Test the _should_update() anti-noise rules."""

    def _make_service(self) -> MemoryService:
        """Create MemoryService without DB (uses _should_update logic only)."""
        return MemoryService(db=None, user_id="test-user")

    def test_skip_if_too_few_turns(self):
        """Should skip if conversation has fewer than MIN_CONVERSATION_TURNS."""
        svc = self._make_service()
        result = svc._should_update(
            intent="book_slot",
            action_result={"status": "ok"},
            conversation_turns=1,
        )
        assert result is False

    def test_allow_sufficient_turns(self):
        """Should allow if enough turns."""
        svc = self._make_service()
        result = svc._should_update(
            intent="book_slot",
            action_result={"status": "ok"},
            conversation_turns=5,
        )
        assert result is True

    def test_skip_if_action_failed(self):
        """Should skip if action_result status is 'error'."""
        svc = self._make_service()
        result = svc._should_update(
            intent="book_slot",
            action_result={"status": "error", "error": "timeout"},
            conversation_turns=5,
        )
        assert result is False

    def test_skip_system_cancel(self):
        """Should skip cancel if system-initiated."""
        svc = self._make_service()
        result = svc._should_update(
            intent="cancel_booking",
            action_result={"status": "ok", "cancel_source": "system"},
            conversation_turns=5,
        )
        assert result is False

    def test_allow_user_cancel(self):
        """Should allow cancel if user-initiated."""
        svc = self._make_service()
        result = svc._should_update(
            intent="cancel_booking",
            action_result={"status": "ok", "cancel_source": "user"},
            conversation_turns=5,
        )
        assert result is True

    def test_skip_very_short_booking(self):
        """Should skip cancel of booking created < 5 minutes ago."""
        from datetime import datetime, timedelta
        svc = self._make_service()
        # Booking created 2 minutes ago → too short
        recent = (datetime.utcnow() - timedelta(minutes=2)).isoformat()
        result = svc._should_update(
            intent="cancel_booking",
            action_result={"status": "ok", "booking_created_at": recent, "cancel_source": "user"},
            conversation_turns=5,
        )
        assert result is False

    def test_allow_normal_duration_booking(self):
        """Should allow cancel of booking created > 5 minutes ago."""
        from datetime import datetime, timedelta
        svc = self._make_service()
        old = (datetime.utcnow() - timedelta(minutes=60)).isoformat()
        result = svc._should_update(
            intent="cancel_booking",
            action_result={"status": "ok", "booking_created_at": old, "cancel_source": "user"},
            conversation_turns=5,
        )
        assert result is True

    def test_no_action_status_passes_through(self):
        """Greeting/help with 'no_action' status are allowed (not 'error')."""
        svc = self._make_service()
        result = svc._should_update(
            intent="greeting",
            action_result={"status": "no_action"},
            conversation_turns=5,
        )
        # no_action ≠ error → memory update is allowed
        assert result is True
