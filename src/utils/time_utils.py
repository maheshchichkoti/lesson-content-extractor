"""Common time utilities for timezone-aware timestamps."""

from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["utc_now", "utc_now_iso"]


def utc_now() -> datetime:
    """Return the current UTC time as an aware ``datetime`` instance."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 formatted string."""
    return utc_now().isoformat()
