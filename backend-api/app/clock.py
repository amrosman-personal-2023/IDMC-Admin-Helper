from datetime import datetime, timezone
from typing import Callable

_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


def now() -> datetime:
    dt = _provider()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def now_naive() -> datetime:
    return now().replace(tzinfo=None)


def set_provider(fn: Callable[[], datetime]) -> None:
    global _provider
    _provider = fn


def reset_provider() -> None:
    global _provider
    _provider = lambda: datetime.now(timezone.utc)
