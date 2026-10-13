import os
import sys
from pathlib import Path
from typing import Dict, List

import yaml


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"FATAL: required environment variable {name!r} is not set", file=sys.stderr)
        sys.exit(1)
    return val


class Settings:
    AUTH_SERVICE_URL: str = ""
    IDMC_STAGING_ROOT: str = ""
    ALLOWED_PATHS_CONFIG: str = ""
    OPERATIONS_CONFIG: str = ""
    LOG_PATHS_CONFIG: str = ""
    UPLOAD_TOKEN_SECRET: str = ""

    # Derived at load time
    allowed_paths: Dict[str, List[str]] = {}
    operations: Dict[str, dict] = {}
    log_roots: List[dict] = []

    MAX_UPLOAD_BYTES: int = 500 * 1024 * 1024   # 500 MB
    UPLOAD_TOKEN_EXPIRE_MINUTES: int = 60
    SCRIPT_TIMEOUT_SECONDS: int = 120

    ALLOWED_EXTENSIONS: frozenset = frozenset({
        ".py", ".sh", ".sql", ".csv", ".txt", ".xml", ".json",
        ".yaml", ".yml", ".properties", ".conf", ".cfg",
    })


settings = Settings()


def load_required_settings() -> None:
    settings.AUTH_SERVICE_URL = _require("AUTH_SERVICE_URL")
    settings.IDMC_STAGING_ROOT = _require("IDMC_STAGING_ROOT")
    settings.ALLOWED_PATHS_CONFIG = _require("ALLOWED_PATHS_CONFIG")
    settings.OPERATIONS_CONFIG = _require("OPERATIONS_CONFIG")
    settings.LOG_PATHS_CONFIG = _require("LOG_PATHS_CONFIG")
    settings.UPLOAD_TOKEN_SECRET = _require("UPLOAD_TOKEN_SECRET")

    _load_yaml_configs()


def _load_yaml_configs() -> None:
    paths_file = Path(settings.ALLOWED_PATHS_CONFIG)
    if not paths_file.exists():
        print(f"FATAL: ALLOWED_PATHS_CONFIG file not found: {paths_file}", file=sys.stderr)
        sys.exit(1)
    with paths_file.open() as f:
        settings.allowed_paths = yaml.safe_load(f) or {}

    ops_file = Path(settings.OPERATIONS_CONFIG)
    if not ops_file.exists():
        print(f"FATAL: OPERATIONS_CONFIG file not found: {ops_file}", file=sys.stderr)
        sys.exit(1)
    with ops_file.open() as f:
        settings.operations = yaml.safe_load(f) or {}

    log_paths_file = Path(settings.LOG_PATHS_CONFIG)
    if not log_paths_file.exists():
        print(f"FATAL: LOG_PATHS_CONFIG file not found: {log_paths_file}", file=sys.stderr)
        sys.exit(1)
    with log_paths_file.open() as f:
        data = yaml.safe_load(f) or {}
    settings.log_roots = data.get("roots", [])
