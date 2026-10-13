"""
Injectable clock — production code calls now() everywhere; tests replace it.

now()     → always returns a timezone-aware UTC datetime.
now_naive() → strips tz for SQLAlchemy/SQLite column storage.
"""
from datetime import datetime, timezone
from typing import Callable

_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


def now() -> datetime:
    """Return current UTC time, always timezone-aware."""
    dt = _provider()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def now_naive() -> datetime:
    """Return current UTC time without tzinfo, for DB column storage."""
    return now().replace(tzinfo=None)


def set_provider(fn: Callable[[], datetime]) -> None:
    global _provider
    _provider = fn


def reset_provider() -> None:
    global _provider
    _provider = lambda: datetime.now(timezone.utc)
