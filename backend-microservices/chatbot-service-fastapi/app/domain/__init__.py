"""
Domain Layer — re-exports canonical value objects.

The single source of truth for Intent lives in
``app.domain.value_objects.intent.Intent`` (15 intents, GOODBYE included).
This module re-exports it for convenience only.
"""

from app.domain.value_objects.intent import Intent  # noqa: F401

__all__ = ["Intent"]
