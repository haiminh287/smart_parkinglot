"""
Cash Payment Session Manager — Track running total of cash inserted.

In production, this should use Redis for persistence across restarts.
For prototype, uses an in-memory dict with TTL-based cleanup.

Usage:
    session = get_cash_session_manager()
    total = session.add_payment(booking_id, 50000)
    if total >= amount_due:
        session.clear_session(booking_id)
"""

import logging
import time
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Session TTL: 30 minutes
SESSION_TTL_SECONDS = 30 * 60


class CashPaymentSession:
    """Track running total of cash inserted during checkout.

    Attributes:
        booking_id: The booking this session tracks.
        total: Running total of cash inserted.
        denominations: List of denominations inserted.
        created_at: Timestamp when session started.
        updated_at: Timestamp of last update.
    """

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id
        self.total: float = 0.0
        self.denominations: list[int] = []
        self.created_at: float = time.time()
        self.updated_at: float = time.time()

    def add(self, denomination: int) -> float:
        """Add a denomination to the running total.

        Args:
            denomination: Cash denomination value (e.g. 50000).

        Returns:
            Updated running total.
        """
        self.denominations.append(denomination)
        self.total += denomination
        self.updated_at = time.time()
        logger.info(
            "Cash session %s: +%d, total=%d, bills=%s",
            self.booking_id, denomination, self.total, self.denominations,
        )
        return self.total

    @property
    def is_expired(self) -> bool:
        """Check if session has expired (30 min TTL)."""
        return (time.time() - self.updated_at) > SESSION_TTL_SECONDS


class CashSessionManager:
    """Manage cash payment sessions across bookings.

    Thread-safe in-memory session store.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, CashPaymentSession] = {}
        self._lock = threading.Lock()

    def add_payment(self, booking_id: str, denomination: int) -> float:
        """Add a cash payment to a booking's session.

        Creates a new session if one doesn't exist.

        Args:
            booking_id: Booking UUID.
            denomination: Cash denomination value.

        Returns:
            Updated running total.
        """
        with self._lock:
            self._cleanup_expired()
            session = self._sessions.get(booking_id)
            if session is None or session.is_expired:
                session = CashPaymentSession(booking_id)
                self._sessions[booking_id] = session
            return session.add(denomination)

    def get_total(self, booking_id: str) -> float:
        """Get current running total for a booking.

        Args:
            booking_id: Booking UUID.

        Returns:
            Current running total, or 0 if no session.
        """
        with self._lock:
            session = self._sessions.get(booking_id)
            if session and not session.is_expired:
                return session.total
            return 0.0

    def get_session(self, booking_id: str) -> Optional[CashPaymentSession]:
        """Get the cash session for a booking.

        Args:
            booking_id: Booking UUID.

        Returns:
            CashPaymentSession or None.
        """
        with self._lock:
            session = self._sessions.get(booking_id)
            if session and not session.is_expired:
                return session
            return None

    def clear_session(self, booking_id: str) -> None:
        """Clear a booking's cash session (after payment complete).

        Args:
            booking_id: Booking UUID.
        """
        with self._lock:
            self._sessions.pop(booking_id, None)
            logger.info("Cash session cleared: %s", booking_id)

    def _cleanup_expired(self) -> None:
        """Remove expired sessions. Must hold lock."""
        expired = [bid for bid, s in self._sessions.items() if s.is_expired]
        for bid in expired:
            del self._sessions[bid]
        if expired:
            logger.info("Cleaned up %d expired cash sessions", len(expired))


# Singleton
_session_manager: Optional[CashSessionManager] = None


def get_cash_session_manager() -> CashSessionManager:
    """Get or create the singleton CashSessionManager.

    Returns:
        CashSessionManager singleton.
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = CashSessionManager()
    return _session_manager
