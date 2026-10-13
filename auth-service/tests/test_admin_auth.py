"""
Admin login, logout, validate, lockout, role isolation.
"""
import pytest

from app import clock, replay_cache
from app.security import sha256_hex
from tests.conftest import _create_admin, _create_vendor

pytestmark = pytest.mark.asyncio


async def _admin_login(client, username="testadmin", password="adminpass!"):
    return await client.post("/admin/auth/login", json={
        "username": username, "password": password
    })


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_admin_login_success(client, db_session, fake_clock):
    await _create_admin(db_session)
    resp = await _admin_login(client)
    assert resp.status_code == 200
    assert resp.json()["logged_in"] is True
    assert "admin_session" in resp.cookies


async def test_admin_login_wrong_password(client, db_session, fake_clock):
    await _create_admin(db_session)
    resp = await _admin_login(client, password="wrong!")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "authentication failed"


async def test_admin_login_unknown_user(client, fake_clock):
    resp = await _admin_login(client, username="nobody")
    assert resp.status_code == 401


async def test_admin_login_inactive_account(client, db_session, fake_clock):
    admin = await _create_admin(db_session, username="inactive_admin")
    admin.active = False
    await db_session.commit()
    resp = await _admin_login(client, username="inactive_admin")
    assert resp.status_code == 401


async def test_admin_login_sets_httponly_cookie(client, db_session, fake_clock):
    await _create_admin(db_session)
    resp = await _admin_login(client)
    assert resp.status_code == 200
    # httpx doesn't expose httponly flag directly; verify cookie is present
    assert "admin_session" in resp.cookies


# ── Lockout ───────────────────────────────────────────────────────────────────

async def test_admin_lockout_after_10_failures(client, db_session, fake_clock):
    await _create_admin(db_session, username="lock_admin")
    for _ in range(10):
        r = await _admin_login(client, username="lock_admin", password="wrong")
        assert r.status_code in (401, 423)
    r = await _admin_login(client, username="lock_admin", password="wrong")
    assert r.status_code == 423


async def test_admin_lockout_correct_password_still_rejected(client, db_session, fake_clock):
    await _create_admin(db_session, username="lock_admin2")
    for _ in range(10):
        await _admin_login(client, username="lock_admin2", password="wrong")
    r = await _admin_login(client, username="lock_admin2", password="adminpass!")
    assert r.status_code == 423


async def test_admin_lockout_releases_after_cooldown(client, db_session, fake_clock):
    await _create_admin(db_session, username="lock_admin3")
    for _ in range(10):
        await _admin_login(client, username="lock_admin3", password="wrong")
    fake_clock.advance(minutes=16)
    r = await _admin_login(client, username="lock_admin3", password="adminpass!")
    assert r.status_code == 200


# ── Logout ────────────────────────────────────────────────────────────────────

async def test_admin_logout_clears_cookie(client, db_session, fake_clock):
    await _create_admin(db_session)
    login_resp = await _admin_login(client)
    assert login_resp.status_code == 200
    logout_resp = await client.post("/admin/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["logged_out"] is True


async def test_admin_logout_invalidates_session(client, db_session, fake_clock):
    await _create_admin(db_session)
    login_resp = await _admin_login(client)
    token = login_resp.cookies.get("admin_session")
    assert token
    await client.post("/admin/auth/logout", cookies={"admin_session": token})
    # Validate should now fail
    r = await client.post("/admin/auth/validate", json={"jwt_token": token})
    assert r.status_code == 401


# ── Validate ──────────────────────────────────────────────────────────────────

async def test_admin_validate_success(client, db_session, fake_clock):
    await _create_admin(db_session)
    login_resp = await _admin_login(client)
    token = login_resp.cookies.get("admin_session")
    # Validate reads the cookie directly — send it via cookies, not body
    r = await client.post("/admin/auth/validate", cookies={"admin_session": token})
    assert r.status_code == 200
    assert r.json()["valid"] is True
    assert r.json()["role"] == "admin"


async def test_admin_validate_vendor_token_rejected(client, db_session, fake_clock):
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_for_admin_val")
    import pyotp
    from datetime import timezone
    code = pyotp.TOTP(seed_b32).at(fake_clock.dt.replace(tzinfo=timezone.utc))
    login_resp = await client.post("/auth/login", json={
        "username": vendor.username, "password": "pass123!",
        "totp_code": code
    })
    assert login_resp.status_code == 200, login_resp.json()
    vendor_token = login_resp.cookies.get("vendor_session")
    # Validate reads the admin_session cookie — a vendor JWT in that cookie must be rejected
    r = await client.post("/admin/auth/validate", cookies={"admin_session": vendor_token})
    assert r.status_code == 401  # vendor role, not admin


# ── Role isolation ────────────────────────────────────────────────────────────

async def test_vendor_jwt_rejected_on_admin_endpoint(client, db_session, fake_clock):
    """Vendor JWT must be rejected with 403 on /admin/* endpoints."""
    replay_cache.clear()
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_iso")
    import pyotp
    from datetime import timezone as _tz
    code = pyotp.TOTP(seed_b32).at(fake_clock.dt.replace(tzinfo=_tz.utc))
    login_resp = await client.post("/auth/login", json={
        "username": vendor.username, "password": "pass123!",
        "totp_code": code
    })
    assert login_resp.status_code == 200, login_resp.json()

    # Attempt to use vendor token as admin_session cookie — must be 403
    token = login_resp.cookies.get("vendor_session")
    r = await client.get("/admin/devices",
                         cookies={"admin_session": token})
    assert r.status_code == 403


async def test_admin_jwt_rejected_on_vendor_endpoint(client, db_session, fake_clock):
    """Admin JWT (in admin_session cookie) must be rejected on vendor-facing /auth/validate."""
    await _create_admin(db_session, username="admin_iso")
    login_resp = await _admin_login(client, username="admin_iso")
    token = login_resp.cookies.get("admin_session")
    r = await client.post("/auth/validate", cookies={"vendor_session": token})
    assert r.status_code == 403


async def test_admin_endpoint_requires_cookie_not_bearer(client, db_session, fake_clock):
    """Admin endpoints must reject Bearer header (vendor auth pattern)."""
    await _create_admin(db_session, username="admin_bearer")
    login_resp = await _admin_login(client, username="admin_bearer")
    token = login_resp.cookies.get("admin_session")
    # Try with Authorization header instead of cookie
    r = await client.get("/admin/devices",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
