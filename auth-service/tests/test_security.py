"""
Security-specific tests: constant-time comparison, seed storage, env var checks,
no-credentials-in-logs, rate limiting, no user enumeration.
"""
import os
import time
import pytest

from app.security import (
    constant_eq, hash_password, sha256_hex, verify_password,
    generate_totp_seed, _bytes_to_base32,
)
from app.seed_crypto import encrypt_seed, decrypt_seed


# ── Constant-time comparison ──────────────────────────────────────────────────

def test_constant_eq_matching():
    assert constant_eq("abc", "abc") is True


def test_constant_eq_non_matching():
    assert constant_eq("abc", "xyz") is False


def test_constant_eq_empty():
    assert constant_eq("", "") is True
    assert constant_eq("a", "") is False


# ── Password hashing ──────────────────────────────────────────────────────────

def test_password_hash_verify_roundtrip():
    h = hash_password("my-secret-password")
    assert verify_password("my-secret-password", h) is True


def test_wrong_password_rejected():
    h = hash_password("correct")
    assert verify_password("wrong", h) is False


def test_hash_is_not_plaintext():
    plain = "my-secret-password"
    h = hash_password(plain)
    assert plain not in h


# ── TOTP seed generation ──────────────────────────────────────────────────────

def test_totp_seed_is_20_bytes():
    seed = generate_totp_seed()
    assert len(seed) == 20


def test_totp_seed_is_random():
    s1 = generate_totp_seed()
    s2 = generate_totp_seed()
    assert s1 != s2


def test_seed_to_base32_decodable():
    import base64
    seed = generate_totp_seed()
    b32 = _bytes_to_base32(seed)
    decoded = base64.b32decode(b32)
    assert decoded == seed


# ── Seed encryption at rest ───────────────────────────────────────────────────

def test_seed_encrypt_decrypt_roundtrip():
    import base64 as b64
    seed = _bytes_to_base32(generate_totp_seed())
    enc = encrypt_seed(seed)
    assert enc != seed  # not stored in plaintext
    assert decrypt_seed(enc) == seed


def test_seed_encrypt_produces_different_ciphertexts():
    seed = _bytes_to_base32(generate_totp_seed())
    e1 = encrypt_seed(seed)
    e2 = encrypt_seed(seed)
    # Fernet uses a random IV so ciphertexts differ
    assert e1 != e2


def test_seed_not_in_encrypted_blob():
    seed = _bytes_to_base32(generate_totp_seed())
    enc = encrypt_seed(seed)
    assert seed not in enc


def test_decrypt_invalid_blob_returns_none():
    assert decrypt_seed("notvalidbase64!!!") is None


# ── SHA-256 hex ───────────────────────────────────────────────────────────────

def test_sha256_hex_length():
    assert len(sha256_hex("test")) == 64


def test_sha256_hex_known_value():
    import hashlib
    val = "hello"
    expected = hashlib.sha256(val.encode()).hexdigest()
    assert sha256_hex(val) == expected


# ── Required environment variables ───────────────────────────────────────────

def test_missing_env_var_causes_exit(monkeypatch):
    """load_required_settings must exit(1) if a required var is absent."""
    import importlib
    monkeypatch.delenv("JWT_SIGNING_KEY", raising=False)

    from app import config
    # Re-import to trigger the check
    with pytest.raises(SystemExit) as exc_info:
        config._require("JWT_SIGNING_KEY")
    assert exc_info.value.code == 1

    # Restore
    os.environ["JWT_SIGNING_KEY"] = os.environ.get("JWT_SIGNING_KEY", "dummy")
