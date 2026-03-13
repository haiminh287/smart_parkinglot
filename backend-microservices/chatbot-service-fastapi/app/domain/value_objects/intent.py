"""
Domain Value Objects — Intent Enum.

15 intent types covering all parking chatbot capabilities.
"""

from enum import Enum


class Intent(str, Enum):
    GREETING = "greeting"
    GOODBYE = "goodbye"
    CHECK_AVAILABILITY = "check_availability"
    BOOK_SLOT = "book_slot"
    REBOOK_PREVIOUS = "rebook_previous"
    CANCEL_BOOKING = "cancel_booking"
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    MY_BOOKINGS = "my_bookings"
    CURRENT_PARKING = "current_parking"
    PRICING = "pricing"
    HELP = "help"
    FEEDBACK = "feedback"
    HANDOFF = "handoff"
    UNKNOWN = "unknown"

    @property
    def is_high_stakes(self) -> bool:
        """Intents that modify data and require higher confidence."""
        return self in [
            Intent.BOOK_SLOT,
            Intent.CANCEL_BOOKING,
            Intent.CHECK_OUT,
        ]

    @property
    def required_entities(self) -> list[str]:
        """
        Schema-driven entity requirements per intent.
        Used for entity_completeness scoring in hybrid confidence.

        book_slot only requires vehicle_type — start_time/end_time
        default to now / +1h in ActionService if not provided.
        """
        mapping: dict[str, list[str]] = {
            "book_slot": ["vehicle_type"],
            "rebook_previous": [],
            "cancel_booking": [],
            "check_in": [],
            "check_out": [],
            "check_availability": ["vehicle_type"],
            "my_bookings": [],
            "current_parking": [],
            "pricing": [],
            "greeting": [],
            "goodbye": [],
            "help": [],
            "feedback": [],
            "handoff": [],
            "unknown": [],
        }
        return mapping.get(self.value, [])
