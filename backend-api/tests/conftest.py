"""
Shared test fixtures for the Backend API.

- tmp_staging:    temp directory tree mirroring IDMC production path structure
- client:         AsyncClient wired to the app with auth service mocked
- mock_auth:      respx mock that stubs POST /auth/validate
- fake_clock:     injectable datetime
- stub_scripts:   creates executable stub shell scripts in a temp dir
"""
import os
import stat
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Callable

import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient, ASGITransport, Response

# ── Required env vars — set before app import ────────────────────────────────
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth-service-test")
os.environ.setdefault("UPLOAD_TOKEN_SECRET", "test-upload-secret-32bytes-xxxxxx")

# These two are set per-test via the tmp_staging fixture
os.environ.setdefault("IDMC_STAGING_ROOT", "/tmp/idmc_test_staging")
os.environ.setdefault("ALLOWED_PATHS_CONFIG",
    str(Path(__file__).parent.parent / "config" / "paths.yaml"))
os.environ.setdefault("OPERATIONS_CONFIG",
    str(Path(__file__).parent.parent / "config" / "operations.yaml"))

from app import clock, upload_token
from app.config import settings, load_required_settings
from app.main import app

load_required_settings()


# ── Fake clock ────────────────────────────────────────────────────────────────

class FakeClock:
    def __init__(self, initial: datetime):
        self._dt = initial

    @property
    def dt(self) -> datetime:
        return self._dt

    def advance(self, **kwargs) -> None:
        from datetime import timedelta
        self._dt = self._dt + timedelta(**kwargs)

    def __call__(self) -> datetime:
        return self._dt


@pytest.fixture
def fake_clock():
    fc = FakeClock(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    clock.set_provider(fc)
    yield fc
    clock.reset_provider()


# ── Temp staging directory ────────────────────────────────────────────────────

SUBDIRS = ["pm_scripts", "source_files", "parameter_files", "target_files"]


@pytest.fixture
def tmp_staging(tmp_path: Path) -> Path:
    """
    Create a temp directory tree that mirrors production IDMC path structure.
    Override settings.IDMC_STAGING_ROOT for the duration of the test.
    """
    staging = tmp_path / "idmc_staging"
    for sub in SUBDIRS:
        (staging / sub).mkdir(parents=True)
    original = settings.IDMC_STAGING_ROOT
    settings.IDMC_STAGING_ROOT = str(staging)
    yield staging
    settings.IDMC_STAGING_ROOT = original
    upload_token.clear_used()


# ── Stub shell scripts ────────────────────────────────────────────────────────

@pytest.fixture
def stub_scripts(tmp_path: Path):
    """
    Returns a factory: make_script(name, exit_code, output) -> abs_path str.
    Scripts are created in a temp dir and registered in settings.operations.
    """
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    original_ops = dict(settings.operations)

    def make_script(op_name: str, exit_code: int = 0,
                    output: str = "ok", roles=None) -> str:
        if roles is None:
            roles = ["vendor_standard", "vendor_premium"]
        path = script_dir / f"{op_name}.sh"
        path.write_text(textwrap.dedent(f"""\
            #!/usr/bin/env sh
            echo '{output}'
            exit {exit_code}
        """))
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        settings.operations[op_name] = {"script": str(path), "roles": roles}
        return str(path)

    yield make_script
    settings.operations = original_ops


# ── HTTP client with mocked auth service ─────────────────────────────────────

def _vendor_claims(vendor_id: int = 1, role: str = "vendor_standard") -> dict:
    return {"valid": True, "vendor_id": vendor_id, "role": role,
            "expires_at": "2026-01-01T13:00:00"}


@pytest_asyncio.fixture
async def client(tmp_staging) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the ASGI app; auth service is NOT called for real."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=True,
    ) as ac:
        yield ac


@pytest.fixture
def auth_ok(vendor_id: int = 1, role: str = "vendor_standard"):
    """
    Context manager: mock POST /auth/validate to return success for the
    given vendor_id and role.  Usage:

        with auth_ok_for(1, "vendor_premium"):
            resp = await client.post(...)
    """
    def auth_ok_for(vid: int = 1, r: str = "vendor_standard"):
        return respx.mock(base_url="http://auth-service-test").post(
            "/auth/validate"
        ).mock(return_value=Response(200, json=_vendor_claims(vid, r)))

    return auth_ok_for


# Convenience: a pre-configured respx mock for standard vendor
@pytest.fixture
def mock_auth_standard():
    with respx.mock(base_url="http://auth-service-test") as rx:
        rx.post("/auth/validate").mock(
            return_value=Response(200, json=_vendor_claims(1, "vendor_standard"))
        )
        yield rx


@pytest.fixture
def mock_auth_premium():
    with respx.mock(base_url="http://auth-service-test") as rx:
        rx.post("/auth/validate").mock(
            return_value=Response(200, json=_vendor_claims(1, "vendor_premium"))
        )
        yield rx


@pytest.fixture
def mock_auth_expired():
    with respx.mock(base_url="http://auth-service-test") as rx:
        rx.post("/auth/validate").mock(return_value=Response(401))
        yield rx


@pytest.fixture
def mock_auth_admin_jwt():
    """Simulates auth service returning 403 because an admin JWT was submitted."""
    with respx.mock(base_url="http://auth-service-test") as rx:
        rx.post("/auth/validate").mock(return_value=Response(403))
        yield rx
