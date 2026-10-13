"""
Symmetric encryption for TOTP seeds at rest.
Uses Fernet (AES-128-CBC + HMAC-SHA256) keyed from ADMIN_SESSION_SECRET.
The encrypted blob is stored in the totp_seed_hash column (base64url string).
"""
import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    from app.config import settings
    # Derive a 32-byte key from ADMIN_SESSION_SECRET via SHA-256
    raw_key = hashlib.sha256(settings.ADMIN_SESSION_SECRET.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(raw_key)
    return Fernet(fernet_key)


def encrypt_seed(seed_b32: str) -> str:
    token = _fernet().encrypt(seed_b32.encode())
    return token.decode()


def decrypt_seed(encrypted: str) -> Optional[str]:
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except Exception:
        return None
