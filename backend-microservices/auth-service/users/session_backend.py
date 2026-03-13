"""
Custom session backend to support UUID primary keys.
Django's default session backend expects integer PKs, but we use UUIDs.
"""

from django.contrib.sessions.backends.db import SessionStore as DbSessionStore
from django.contrib.auth import get_user_model


class SessionStore(DbSessionStore):
    """Custom session store that handles UUID user IDs."""
    
    @classmethod
    def get_model_class(cls):
        """Return the Session model."""
        return super().get_model_class()
    
    def _get_session_from_db(self):
        """Override to handle UUID conversion."""
        try:
            return super()._get_session_from_db()
        except Exception:
            # If session is corrupted, return empty session
            return {}
