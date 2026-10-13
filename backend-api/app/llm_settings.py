"""
LLM settings store.
Settings are persisted to an encrypted JSON file (Fernet, keyed from
ADMIN_SESSION_SECRET via SHA-256).  Falls back to env vars on first run.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


DEFAULTS = {
    "provider": "anthropic",
    "model": "claude-opus-4-8",
    "api_key": "",
    "max_context_tokens": 80000,
    "azure_endpoint": "",
    "azure_deployment": "",
}


def _fernet() -> Fernet:
    secret = os.environ.get("ADMIN_SESSION_SECRET", "fallback-dev-secret-32-bytes!!")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _settings_path() -> Path:
    return Path(os.environ.get("LLM_SETTINGS_PATH", "/tmp/llm-settings.enc"))


def load() -> dict:
    """Return current settings, merging env vars as defaults."""
    base = {
        "provider": os.environ.get("LLM_PROVIDER", DEFAULTS["provider"]),
        "model": os.environ.get("LLM_MODEL", DEFAULTS["model"]),
        "api_key": os.environ.get("LLM_API_KEY", DEFAULTS["api_key"]),
        "max_context_tokens": int(os.environ.get("LLM_MAX_CONTEXT_TOKENS", DEFAULTS["max_context_tokens"])),
        "azure_endpoint": os.environ.get("LLM_AZURE_ENDPOINT", DEFAULTS["azure_endpoint"]),
        "azure_deployment": os.environ.get("LLM_AZURE_DEPLOYMENT", DEFAULTS["azure_deployment"]),
    }
    p = _settings_path()
    if p.exists():
        try:
            decrypted = _fernet().decrypt(p.read_bytes())
            stored = json.loads(decrypted)
            base.update(stored)
        except (InvalidToken, Exception):
            pass
    return base


def save(settings: dict) -> None:
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _fernet().encrypt(json.dumps(settings).encode())
    p.write_bytes(encrypted)


def masked_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "••••••••"
    return api_key[:4] + "••••••••" + api_key[-4:]
