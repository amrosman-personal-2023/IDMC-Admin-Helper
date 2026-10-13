"""
In-memory TOTP replay cache.
Key: (vendor_id, totp_window_counter).  Value: True.
Windows outside a 3-step range from 'now' are evicted on each check.
"""
import math
from threading import Lock
from typing import Dict, Tuple

_cache: Dict[Tuple[int, int], bool] = {}
_lock = Lock()

STEP_SECONDS = 30


def _counter(ts_seconds: float) -> int:
    return math.floor(ts_seconds / STEP_SECONDS)


def _evict(current_counter: int) -> None:
    stale = [k for k in _cache if abs(k[1] - current_counter) > 3]
    for k in stale:
        del _cache[k]


def is_replayed(vendor_id: int, code: str, ts_seconds: float) -> bool:
    """Return True if this (vendor, counter, code) combination has been seen before."""
    ctr = _counter(ts_seconds)
    key = (vendor_id, ctr, code)
    with _lock:
        _evict(ctr)
        if key in _cache:
            return True
        _cache[key] = True
        return False


def clear() -> None:
    with _lock:
        _cache.clear()
