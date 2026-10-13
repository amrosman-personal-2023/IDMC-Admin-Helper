"""
Vendor login, enrollment, JWT validation, lockout, replay protection.
"""
import base64
from datetime import datetime, timedelta, timezone

import pyotp
import pytest
import pytest_asyncio

from app import clock, replay_cache
from app.security import sha256_hex, issue_jwt
from tests.conftest import _create_vendor, _create_admin


pytestmark = pytest.mark.asyncio


async def _login(client, username, password, totp_code, device_uuid=None):
    # device_uuid is no longer used — Google Authenticator enrollment removes it
    return await client.post("/auth/login", json={
        "username": username,
        "password": password,
        "totp_code": totp_code,
    })


def _current_totp(seed_b32: str, dt: datetime) -> str:
    return pyotp.TOTP(seed_b32).at(dt.replace(tzinfo=timezone.utc))


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_vendor_login_success(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, device, seed_b32, uuid, _ = await _create_vendor(db_session)
    code = _current_totp(seed_b32, fake_clock.dt)
    resp = await _login(client, vendor.username, "pass123!", code, uuid)
    assert resp.status_code == 200
    data = resp.json()
    assert "expires_at" in data
    # Session token is in the HttpOnly cookie, not the response body
    assert "vendor_session" in resp.cookies


async def test_vendor_login_wrong_password(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, device, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_wp")
    code = _current_totp(seed_b32, fake_clock.dt)
    resp = await _login(client, vendor.username, "wrong!", code, uuid)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "authentication failed"


async def test_vendor_login_wrong_totp(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, _, uuid, _ = await _create_vendor(db_session, username="v_wt")
    resp = await _login(client, vendor.username, "pass123!", "000000", uuid)
    assert resp.status_code == 401


async def test_vendor_login_unknown_username(client, fake_clock):
    resp = await _login(client, "nobody", "pass123!", "000000")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "authentication failed"


async def test_vendor_login_inactive_vendor(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_inactive")
    vendor.active = False
    await db_session.commit()
    code = _current_totp(seed_b32, fake_clock.dt)
    resp = await _login(client, vendor.username, "pass123!", code, uuid)
    assert resp.status_code == 401


async def test_vendor_login_revoked_device(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, device, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_revoked")
    device.revoked = True
    await db_session.commit()
    code = _current_totp(seed_b32, fake_clock.dt)
    resp = await _login(client, vendor.username, "pass123!", code, uuid)
    assert resp.status_code == 401


async def test_vendor_login_no_enrolled_device(client, db_session, fake_clock):
    """Vendor with no enrolled device cannot log in even with correct password."""
    replay_cache.clear()
    # Create vendor but skip device creation — no enrolled device
    from app.models import Vendor as VendorModel
    from app.security import hash_password
    now = fake_clock()
    v = VendorModel(username="v_nodevice", bcrypt_password_hash=hash_password("pass123!"),
                    role="vendor_standard", created_at=now, active=True)
    db_session.add(v)
    await db_session.commit()
    resp = await _login(client, "v_nodevice", "pass123!", "000000")
    assert resp.status_code == 401


# ── Error message uniformity ──────────────────────────────────────────────────

async def test_auth_failure_same_message_for_all_failure_modes(client, db_session, fake_clock):
    """All failure paths return identical error message."""
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_msg")
    code = _current_totp(seed_b32, fake_clock.dt)

    r1 = await _login(client, "nobody", "x", "000000")
    r2 = await _login(client, vendor.username, "wrong", code, uuid)
    r3 = await _login(client, vendor.username, "pass123!", "000000", uuid)

    assert r1.json()["detail"] == r2.json()["detail"] == r3.json()["detail"] == "authentication failed"


# ── Lockout ───────────────────────────────────────────────────────────────────

async def test_vendor_lockout_after_5_failures(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, _, uuid, _ = await _create_vendor(db_session, username="v_lock")
    for _ in range(5):
        r = await _login(client, vendor.username, "wrong", "000000", uuid)
        assert r.status_code in (401, 423)
    # 6th attempt should be locked
    r = await _login(client, vendor.username, "wrong", "000000", uuid)
    assert r.status_code == 423


async def test_vendor_lockout_correct_totp_still_rejected_during_lockout(
    client, db_session, fake_clock
):
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_lock2")
    for _ in range(5):
        await _login(client, vendor.username, "wrong", "000000", uuid)
    code = _current_totp(seed_b32, fake_clock.dt)
    r = await _login(client, vendor.username, "pass123!", code, uuid)
    assert r.status_code == 423


async def test_vendor_lockout_releases_after_cooldown(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_lock3")
    for _ in range(5):
        await _login(client, vendor.username, "wrong", "000000", uuid)
    # Advance clock past lockout window
    fake_clock.advance(minutes=11)
    replay_cache.clear()
    code = _current_totp(seed_b32, fake_clock.dt)
    r = await _login(client, vendor.username, "pass123!", code, uuid)
    assert r.status_code == 200


# ── Replay protection ─────────────────────────────────────────────────────────

async def test_totp_replay_rejected(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_replay")
    code = _current_totp(seed_b32, fake_clock.dt)
    r1 = await _login(client, vendor.username, "pass123!", code, uuid)
    assert r1.status_code == 200
    # Same code again — replay
    r2 = await _login(client, vendor.username, "pass123!", code, uuid)
    assert r2.status_code == 401


# ── Enrollment ────────────────────────────────────────────────────────────────

async def test_enrollment_success(client, db_session, fake_clock):
    """Enrollment now returns an otpauth URI + QR code data URI instead of a raw seed."""
    vendor, _, _, _, raw_token = await _create_vendor(db_session, username="v_enroll")
    resp = await client.post("/enroll", json={"enrollment_token": raw_token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["enrolled"] is True
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert "v_enroll" in data["otpauth_uri"]
    assert data["qr_data_uri"].startswith("data:image/png;base64,")


async def test_enrollment_single_use(client, db_session, fake_clock):
    vendor, _, _, _, raw_token = await _create_vendor(db_session, username="v_enroll2")
    r1 = await client.post("/enroll", json={"enrollment_token": raw_token})
    assert r1.status_code == 200
    r2 = await client.post("/enroll", json={"enrollment_token": raw_token})
    assert r2.status_code == 400


async def test_enrollment_expired_token(client, db_session, fake_clock):
    vendor, _, _, _, raw_token = await _create_vendor(db_session, username="v_enroll3")
    fake_clock.advance(hours=25)
    resp = await client.post("/enroll", json={"enrollment_token": raw_token})
    assert resp.status_code == 400


async def test_enrollment_unknown_token(client, fake_clock):
    resp = await client.post("/enroll", json={"enrollment_token": "totally-unknown-token"})
    assert resp.status_code == 400


# ── JWT validation ────────────────────────────────────────────────────────────

async def test_validate_valid_vendor_token(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_val")
    code = _current_totp(seed_b32, fake_clock.dt)
    login_resp = await _login(client, vendor.username, "pass123!", code, uuid)
    token = login_resp.cookies.get("vendor_session")
    r = await client.post("/auth/validate", cookies={"vendor_session": token})
    assert r.status_code == 200
    assert r.json()["valid"] is True
    assert r.json()["role"].startswith("vendor")


async def test_validate_admin_token_rejected_on_vendor_endpoint(client, db_session, fake_clock):
    """Admin JWT placed in vendor_session cookie must be rejected."""
    admin = await _create_admin(db_session)
    resp = await client.post("/admin/auth/login", json={
        "username": admin.username, "password": "adminpass!"
    })
    admin_token = resp.cookies.get("admin_session")
    r = await client.post("/auth/validate", cookies={"vendor_session": admin_token})
    assert r.status_code == 403


async def test_validate_expired_vendor_token(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_exp")
    code = _current_totp(seed_b32, fake_clock.dt)
    login_resp = await _login(client, vendor.username, "pass123!", code, uuid)
    token = login_resp.cookies.get("vendor_session")
    fake_clock.advance(minutes=35)
    r = await client.post("/auth/validate", cookies={"vendor_session": token})
    assert r.status_code == 401


async def test_validate_alg_none_rejected(client):
    """JWT with alg:none must not be accepted."""
    import json as json_mod
    import base64 as b64
    header = b64.urlsafe_b64encode(
        json_mod.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = b64.urlsafe_b64encode(
        json_mod.dumps({"sub": "1", "role": "vendor_standard", "vendor_id": 1,
                        "exp": 9999999999}).encode()
    ).rstrip(b"=").decode()
    fake_token = f"{header}.{payload}."
    r = await client.post("/auth/validate", cookies={"vendor_session": fake_token})
    assert r.status_code == 401


async def test_validate_invalidated_session(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_inv")
    code = _current_totp(seed_b32, fake_clock.dt)
    login_resp = await _login(client, vendor.username, "pass123!", code, uuid)
    token = login_resp.cookies.get("vendor_session")

    from sqlalchemy import select
    from app.models import Session as SessionModel
    result = await db_session.execute(
        select(SessionModel).where(SessionModel.session_token_hash == sha256_hex(token))
    )
    s = result.scalar_one()
    s.invalidated = True
    await db_session.commit()

    r = await client.post("/auth/validate", cookies={"vendor_session": token})
    assert r.status_code == 401
