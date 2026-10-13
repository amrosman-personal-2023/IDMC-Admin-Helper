"""
Short-lived, single-use, path-scoped upload tokens.

Token payload (JSON, HMAC-SHA256 signed):
  { "vendor_id": int, "role": str, "path": str, "exp": int, "jti": str }

The token is Base64url(payload) + "." + Base64url(HMAC-SHA256(secret, payload_bytes)).
We don't use JWT here to keep this layer independent of the JWT signing key.
"""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from typing import Optional

from app import clock
from app.config import settings

_USED: dict[str, bool] = {}   # jti → True; cleared on restart (acceptable for single-host)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


def _sign(payload_bytes: bytes) -> str:
    return _b64url(
        hmac.new(settings.UPLOAD_TOKEN_SECRET.encode(), payload_bytes, hashlib.sha256).digest()
    )


def issue(vendor_id: int, role: str, abs_path: str) -> str:
    exp = clock.now() + timedelta(minutes=settings.UPLOAD_TOKEN_EXPIRE_MINUTES)
    payload = {
        "vendor_id": vendor_id,
        "role": role,
        "path": abs_path,
        "exp": int(exp.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    payload_b64 = _b64url(payload_bytes)
    sig = _sign(payload_bytes)
    return f"{payload_b64}.{sig}"


def consume(token: str) -> Optional[dict]:
    """
    Validate and consume the token (mark used).
    Returns the payload dict on success, None on any failure.
    """
    try:
        payload_b64, sig = token.rsplit(".", 1)
    except ValueError:
        return None

    try:
        payload_bytes = _b64url_decode(payload_b64)
    except Exception:
        return None

    expected_sig = _sign(payload_bytes)
    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        payload = json.loads(payload_bytes)
    except Exception:
        return None

    now_ts = int(clock.now().timestamp())
    if payload.get("exp", 0) < now_ts:
        return None

    jti = payload.get("jti", "")
    if not jti or jti in _USED:
        return None

    _USED[jti] = True
    return payload


def clear_used() -> None:
    """Test helper — reset the used-token store."""
    _USED.clear()
