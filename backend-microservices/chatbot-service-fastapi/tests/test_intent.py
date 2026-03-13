"""
Unit tests for 🔥 Improvement 2.1: Intent value objects & schema-driven entity requirements.
"""

import pytest

from app.domain.value_objects.intent import Intent


class TestIntentEnum:

    def test_all_intents_exist(self):
        expected = [
            "greeting", "goodbye", "check_availability", "book_slot", "rebook_previous",
            "cancel_booking", "check_in", "check_out", "my_bookings",
            "current_parking", "pricing", "help", "feedback", "handoff", "unknown",
        ]
        for val in expected:
            intent = Intent(val)
            assert intent.value == val

    def test_high_stakes_intents(self):
        """book_slot, cancel_booking, check_out should be high stakes."""
        assert Intent.BOOK_SLOT.is_high_stakes is True
        assert Intent.CANCEL_BOOKING.is_high_stakes is True
        assert Intent.CHECK_OUT.is_high_stakes is True

    def test_non_high_stakes(self):
        """greeting, help should NOT be high stakes."""
        assert Intent.GREETING.is_high_stakes is False
        assert Intent.HELP.is_high_stakes is False
        assert Intent.MY_BOOKINGS.is_high_stakes is False

    def test_book_slot_required_entities(self):
        """book_slot only requires vehicle_type (start_time/end_time default in ActionService)."""
        required = Intent.BOOK_SLOT.required_entities
        assert "vehicle_type" in required
        assert len(required) == 1

    def test_cancel_required_entities(self):
        """cancel_booking requires no explicit entities (booking resolved from user history)."""
        required = Intent.CANCEL_BOOKING.required_entities
        assert required == []

    def test_greeting_no_required(self):
        """greeting requires no entities."""
        assert Intent.GREETING.required_entities == []

    def test_invalid_intent_raises(self):
        with pytest.raises(ValueError):
            Intent("nonexistent_intent")
