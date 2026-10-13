import os
import sys


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"FATAL: required environment variable {name!r} is not set", file=sys.stderr)
        sys.exit(1)
    return val


class Settings:
    DB_URL: str = os.environ.get("DB_URL", "sqlite+aiosqlite:///./dev.db")
    JWT_SIGNING_KEY: str = ""
    JWT_PUBLIC_KEY: str = ""
    ADMIN_API_KEY: str = ""
    ADMIN_SESSION_SECRET: str = ""
    ENROLLMENT_LINK_BASE_URL: str = os.environ.get(
        "ENROLLMENT_LINK_BASE_URL", "http://localhost:8000/enroll"
    )
    JWT_ALGORITHM: str = "RS256"
    JWT_VENDOR_EXPIRE_MINUTES: int = 30
    JWT_ADMIN_EXPIRE_HOURS: int = 8
    ADMIN_SESSION_INACTIVITY_MINUTES: int = 30
    VENDOR_LOCKOUT_ATTEMPTS: int = 5
    VENDOR_LOCKOUT_MINUTES: int = 10
    ADMIN_LOCKOUT_ATTEMPTS: int = 10
    ADMIN_LOCKOUT_MINUTES: int = 15
    ENROLLMENT_TOKEN_EXPIRE_HOURS: int = 24
    TOTP_WINDOW: int = 1  # ±1 step


settings = Settings()


def load_required_settings() -> None:
    settings.JWT_SIGNING_KEY = _require("JWT_SIGNING_KEY")
    settings.JWT_PUBLIC_KEY = _require("JWT_PUBLIC_KEY")
    settings.ADMIN_API_KEY = _require("ADMIN_API_KEY")
    settings.ADMIN_SESSION_SECRET = _require("ADMIN_SESSION_SECRET")
