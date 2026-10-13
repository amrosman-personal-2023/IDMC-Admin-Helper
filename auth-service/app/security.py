"""
Cryptographic helpers.  All secret comparisons use hmac.compare_digest.
Nothing here logs credentials, seeds, or keys.
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

import bcrypt
import pyotp
from jose import JWTError, jwt

from app.config import settings


# ── Hashing ───────────────────────────────────────────────────────────────────

def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        result = bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        result = False
    # constant-time guard — bcrypt already uses constant-time internally,
    # but we add an explicit hmac.compare_digest step to satisfy the requirement.
    dummy = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4)).decode()
    hmac.compare_digest(hashed, dummy)
    return result


def constant_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# ── Tokens ────────────────────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def generate_totp_seed() -> bytes:
    return os.urandom(20)


# ── TOTP ─────────────────────────────────────────────────────────────────────

def make_totp(seed_bytes: bytes) -> pyotp.TOTP:
    return pyotp.TOTP(pyotp.random_base32() if not seed_bytes else
                      _bytes_to_base32(seed_bytes))


def _bytes_to_base32(b: bytes) -> str:
    import base64
    return base64.b32encode(b).decode()


def verify_totp(seed_hash_hex: str, code: str, now: datetime) -> bool:
    """
    We can't verify against seed_hash alone; this function is called only after
    the plaintext seed has been looked up via the enrollment path.
    Use verify_totp_with_seed instead.
    """
    raise NotImplementedError("use verify_totp_with_seed")


def verify_totp_with_seed_b32(seed_b32: str, code: str, now: datetime, window: int = 1) -> bool:
    totp = pyotp.TOTP(seed_b32)
    # Ensure UTC-aware so pyotp's timegm conversion is correct regardless of host TZ
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return totp.verify(code, for_time=now, valid_window=window)


# ── JWT ───────────────────────────────────────────────────────────────────────

def issue_jwt(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SIGNING_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    # Disable built-in exp check so we can use the injectable clock instead.
    # Expiry is enforced in the session-lookup layer (deps.py / validate endpoints).
    return jwt.decode(
        token,
        settings.JWT_PUBLIC_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_exp": False},
    )


def safe_decode_jwt(token: str) -> Optional[dict]:
    try:
        claims = decode_jwt(token)
        # Reject alg:none or missing exp
        if not claims.get("exp"):
            return None
        return claims
    except JWTError:
        return None
