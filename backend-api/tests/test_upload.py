"""
Upload endpoint tests: path validation, traversal, file write, token enforcement.
"""
import os
from pathlib import Path

import pytest

from app import upload_token
from app.config import settings

pytestmark = pytest.mark.asyncio

AUTH = {"vendor_session": "test-vendor-session-token"}


# ── /upload/request ───────────────────────────────────────────────────────────

async def test_request_upload_success(client, mock_auth_standard, fake_clock):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "load.py"},
                             cookies=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "upload_token" in data
    assert "expires_at" in data


async def test_request_upload_forbidden_directory(client, mock_auth_standard, fake_clock):
    """vendor_standard cannot access target_files."""
    resp = await client.post("/upload/request",
                             json={"directory": "target_files", "filename": "data.csv"},
                             cookies=AUTH)
    assert resp.status_code == 403


async def test_request_upload_premium_can_access_target_files(
    client, mock_auth_premium, fake_clock
):
    resp = await client.post("/upload/request",
                             json={"directory": "target_files", "filename": "data.csv"},
                             cookies=AUTH)
    assert resp.status_code == 200


async def test_request_upload_disallowed_extension(client, mock_auth_standard, fake_clock):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "virus.exe"},
                             cookies=AUTH)
    assert resp.status_code == 400


async def test_request_upload_empty_filename(client, mock_auth_standard, fake_clock):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": ""},
                             cookies=AUTH)
    assert resp.status_code == 400


async def test_request_upload_path_traversal_literal(client, mock_auth_standard, fake_clock):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "../../../etc/passwd"},
                             cookies=AUTH)
    # Either sanitized to valid name or rejected
    assert resp.status_code in (200, 400, 403)
    if resp.status_code == 200:
        # If somehow passed, token path must still be inside staging root
        token = resp.json()["upload_token"]
        payload = upload_token.consume(token)
        staging = Path(settings.IDMC_STAGING_ROOT).resolve()
        assert Path(payload["path"]).resolve().is_relative_to(staging) or \
               str(Path(payload["path"]).resolve()).startswith(str(staging))


async def test_request_upload_path_traversal_encoded(client, mock_auth_standard, fake_clock):
    for malicious in ["..%2Fetc%2Fpasswd", "..%252F..%252Fetc", "%2e%2e%2fpasswd"]:
        resp = await client.post("/upload/request",
                                 json={"directory": "pm_scripts", "filename": malicious},
                                 cookies=AUTH)
        assert resp.status_code in (200, 400, 403)
        if resp.status_code == 200:
            token = resp.json()["upload_token"]
            payload = upload_token.consume(token)
            staging = str(Path(settings.IDMC_STAGING_ROOT).resolve())
            assert str(Path(payload["path"]).resolve()).startswith(staging)


async def test_request_upload_no_auth(client, fake_clock):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "file.py"})
    assert resp.status_code == 401


async def test_request_upload_expired_session(client, mock_auth_expired, fake_clock):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "file.py"},
                             cookies=AUTH)
    assert resp.status_code == 401


async def test_request_upload_admin_jwt_rejected(client, mock_auth_admin_jwt, fake_clock):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "file.py"},
                             cookies=AUTH)
    assert resp.status_code == 403


# ── /upload/{token} ───────────────────────────────────────────────────────────

async def test_execute_upload_success(client, mock_auth_standard, fake_clock, tmp_staging):
    # Get token
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "script.py"},
                             cookies=AUTH)
    assert resp.status_code == 200
    token = resp.json()["upload_token"]

    # Upload
    content = b"print('hello')"
    put_resp = await client.put(f"/upload/{token}", content=content)
    assert put_resp.status_code == 200
    assert put_resp.json()["uploaded"] is True
    assert put_resp.json()["path"] == "script.py"

    # File must exist on disk
    assert (tmp_staging / "pm_scripts" / "script.py").read_bytes() == content


async def test_execute_upload_single_use(client, mock_auth_standard, fake_clock, tmp_staging):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "once.py"},
                             cookies=AUTH)
    token = resp.json()["upload_token"]

    r1 = await client.put(f"/upload/{token}", content=b"data")
    assert r1.status_code == 200

    r2 = await client.put(f"/upload/{token}", content=b"data2")
    assert r2.status_code == 401


async def test_execute_upload_invalid_token(client, fake_clock, tmp_staging):
    r = await client.put("/upload/badtoken", content=b"data")
    assert r.status_code == 401


async def test_execute_upload_expired_token(client, mock_auth_standard, fake_clock, tmp_staging):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "late.py"},
                             cookies=AUTH)
    token = resp.json()["upload_token"]
    fake_clock.advance(minutes=61)
    r = await client.put(f"/upload/{token}", content=b"data")
    assert r.status_code == 401


async def test_execute_upload_file_too_large(client, mock_auth_standard, fake_clock, tmp_staging):
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "big.py"},
                             cookies=AUTH)
    token = resp.json()["upload_token"]
    # Fake the content-length header to exceed limit without sending huge body
    r = await client.put(
        f"/upload/{token}",
        content=b"x",
        headers={"Content-Length": str(settings.MAX_UPLOAD_BYTES + 1)},
    )
    assert r.status_code == 413


async def test_execute_upload_atomic_write(client, mock_auth_standard, fake_clock, tmp_staging):
    """No .tmp_ partial file should remain after a successful upload."""
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "atomic.py"},
                             cookies=AUTH)
    token = resp.json()["upload_token"]
    await client.put(f"/upload/{token}", content=b"data")

    # No temp files remaining
    tmp_files = list((tmp_staging / "pm_scripts").glob(".tmp_upload_*"))
    assert tmp_files == []


async def test_response_contains_no_full_path(client, mock_auth_standard, fake_clock, tmp_staging):
    """Error and success responses must not expose the full filesystem path."""
    resp = await client.post("/upload/request",
                             json={"directory": "pm_scripts", "filename": "pathtest.py"},
                             cookies=AUTH)
    token = resp.json()["upload_token"]
    r = await client.put(f"/upload/{token}", content=b"data")
    # The 'path' field in the response should be filename only
    assert "/" not in r.json()["path"]
    assert "\\" not in r.json()["path"]
    assert settings.IDMC_STAGING_ROOT not in r.text


async def test_concurrent_uploads(client, mock_auth_standard, fake_clock, tmp_staging):
    """Two simultaneous uploads must both succeed without corruption."""
    import asyncio

    async def upload_one(filename: str, content: bytes):
        resp = await client.post("/upload/request",
                                 json={"directory": "pm_scripts", "filename": filename},
                                 cookies=AUTH)
        token = resp.json()["upload_token"]
        r = await client.put(f"/upload/{token}", content=content)
        return r.status_code, content

    results = await asyncio.gather(
        upload_one("concurrent_a.py", b"content_a"),
        upload_one("concurrent_b.py", b"content_b"),
    )
    for status_code, content in results:
        assert status_code == 200

    assert (tmp_staging / "pm_scripts" / "concurrent_a.py").read_bytes() == b"content_a"
    assert (tmp_staging / "pm_scripts" / "concurrent_b.py").read_bytes() == b"content_b"
