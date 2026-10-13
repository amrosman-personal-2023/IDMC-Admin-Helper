"""
RFC 6238 TOTP generation and window acceptance tests.
"""
from datetime import datetime, timezone

import pytest

from app.security import verify_totp_with_seed_b32
from tests.conftest import _RFC6238_SEED_B32


def test_rfc6238_reference_vectors(rfc6238_vector):
    seed_b32 = rfc6238_vector["seed_b32"]
    ts = rfc6238_vector["timestamp"]
    expected = rfc6238_vector["expected"]
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    # window=0 to test exact match
    assert verify_totp_with_seed_b32(seed_b32, expected, dt, window=0), \
        f"Vector ts={ts} expected {expected}"


def test_totp_window_accepts_minus_one():
    import pyotp, math
    seed_b32 = _RFC6238_SEED_B32
    totp = pyotp.TOTP(seed_b32)
    # Generate code for T-1
    base_ts = 1111111111
    prev_ts = base_ts - 30
    code = totp.at(prev_ts)
    dt = datetime.fromtimestamp(base_ts, tz=timezone.utc)
    assert verify_totp_with_seed_b32(seed_b32, code, dt, window=1)


def test_totp_window_accepts_plus_one():
    import pyotp
    seed_b32 = _RFC6238_SEED_B32
    totp = pyotp.TOTP(seed_b32)
    base_ts = 1111111111
    next_ts = base_ts + 30
    code = totp.at(next_ts)
    dt = datetime.fromtimestamp(base_ts, tz=timezone.utc)
    assert verify_totp_with_seed_b32(seed_b32, code, dt, window=1)


def test_totp_window_rejects_t_minus_3():
    import pyotp
    seed_b32 = _RFC6238_SEED_B32
    totp = pyotp.TOTP(seed_b32)
    base_ts = 1111111111
    old_ts = base_ts - 90  # T-3
    code = totp.at(old_ts)
    dt = datetime.fromtimestamp(base_ts, tz=timezone.utc)
    assert not verify_totp_with_seed_b32(seed_b32, code, dt, window=1)


def test_totp_wrong_code_rejected():
    dt = datetime.fromtimestamp(1111111111, tz=timezone.utc)
    assert not verify_totp_with_seed_b32(_RFC6238_SEED_B32, "000000", dt, window=1)
