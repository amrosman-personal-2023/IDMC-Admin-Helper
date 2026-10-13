"""
Admin management: vendor CRUD, device registry, sessions, audit log.
"""
import pytest
from sqlalchemy import select

from app import clock, replay_cache
from app.models import Device, Session as SessionModel, Vendor
from app.security import sha256_hex
from tests.conftest import _create_admin, _create_vendor

pytestmark = pytest.mark.asyncio


async def _login_admin(client, db_session):
    admin = await _create_admin(db_session, username=f"mgmt_admin_{id(client)}")
    resp = await client.post("/admin/auth/login",
                             json={"username": admin.username, "password": "adminpass!"})
    assert resp.status_code == 200
    return resp.cookies.get("admin_session")


# ── Vendor management ─────────────────────────────────────────────────────────

async def test_create_vendor(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    r = await client.post("/admin/vendors",
                          json={"username": "newvendor", "password": "pw1!", "role": "vendor_standard"},
                          cookies={"admin_session": cookie})
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "newvendor"
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert data["qr_data_uri"].startswith("data:image/png;base64,")


async def test_create_vendor_duplicate_username(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    payload = {"username": "dupvendor", "password": "pw1!", "role": "vendor_standard"}
    r1 = await client.post("/admin/vendors", json=payload, cookies={"admin_session": cookie})
    assert r1.status_code == 200
    r2 = await client.post("/admin/vendors", json=payload, cookies={"admin_session": cookie})
    assert r2.status_code == 409


async def test_deactivate_vendor_sets_inactive(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    vendor, _, _, _, _ = await _create_vendor(db_session, username="v_deact")
    r = await client.post(f"/admin/vendors/{vendor.id}/deactivate",
                          cookies={"admin_session": cookie})
    assert r.status_code == 200
    await db_session.refresh(vendor)
    assert vendor.active is False


async def test_deactivate_vendor_revokes_all_devices(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    vendor, device, _, _, _ = await _create_vendor(db_session, username="v_deact2")
    r = await client.post(f"/admin/vendors/{vendor.id}/deactivate",
                          cookies={"admin_session": cookie})
    assert r.status_code == 200
    data = r.json()
    assert data["devices_revoked"] >= 1
    await db_session.refresh(device)
    assert device.revoked is True


async def test_deactivate_vendor_invalidates_sessions(client, db_session, fake_clock):
    """Vendor deactivation must invalidate active sessions atomically."""
    replay_cache.clear()
    cookie = await _login_admin(client, db_session)
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_deact3")

    # Vendor logs in
    import pyotp
    from datetime import timezone
    code = pyotp.TOTP(seed_b32).at(fake_clock.dt.replace(tzinfo=timezone.utc))
    login_resp = await client.post("/auth/login", json={
        "username": vendor.username, "password": "pass123!",
        "totp_code": code
    })
    assert login_resp.status_code == 200
    token = login_resp.cookies.get("vendor_session")

    # Admin deactivates
    r = await client.post(f"/admin/vendors/{vendor.id}/deactivate",
                          cookies={"admin_session": cookie})
    assert r.status_code == 200
    assert r.json()["sessions_invalidated"] >= 1

    # Vendor session now invalid
    val = await client.post("/auth/validate", cookies={"vendor_session": token})
    assert val.status_code == 401


async def test_deactivate_vendor_atomicity(client, db_session, fake_clock):
    """After deactivation: vendor inactive AND device revoked — both in same state."""
    cookie = await _login_admin(client, db_session)
    vendor, device, _, _, _ = await _create_vendor(db_session, username="v_atomic")
    await client.post(f"/admin/vendors/{vendor.id}/deactivate",
                      cookies={"admin_session": cookie})
    await db_session.refresh(vendor)
    await db_session.refresh(device)
    assert vendor.active is False
    assert device.revoked is True


# ── Device registry ───────────────────────────────────────────────────────────

async def test_revoke_device(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    vendor, device, _, uuid, _ = await _create_vendor(db_session, username="v_rev")
    r = await client.post("/admin/devices/revoke",
                          json={"device_uuid": uuid, "vendor_id": vendor.id},
                          cookies={"admin_session": cookie})
    assert r.status_code == 200
    assert r.json()["revoked"] is True
    await db_session.refresh(device)
    assert device.revoked is True


async def test_revoke_unknown_device(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    vendor, _, _, _, _ = await _create_vendor(db_session, username="v_rev2")
    r = await client.post("/admin/devices/revoke",
                          json={"device_uuid": "nonexistent-uuid", "vendor_id": vendor.id},
                          cookies={"admin_session": cookie})
    assert r.status_code == 404


async def test_list_devices_all(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    vendor, _, _, _, _ = await _create_vendor(db_session, username="v_list")
    r = await client.get("/admin/devices", cookies={"admin_session": cookie})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


async def test_list_devices_filtered_by_vendor(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    vendor, _, _, _, _ = await _create_vendor(db_session, username="v_listf")
    r = await client.get(f"/admin/devices?vendor_id={vendor.id}",
                         cookies={"admin_session": cookie})
    assert r.status_code == 200
    for d in r.json():
        assert d["vendor_id"] == vendor.id


async def test_reissue_enrollment_link(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    vendor, _, _, _, _ = await _create_vendor(db_session, username="v_reissue")
    r = await client.post("/admin/enrollment-links",
                          json={"vendor_id": vendor.id},
                          cookies={"admin_session": cookie})
    assert r.status_code == 200
    data = r.json()
    assert data["vendor_id"] == vendor.id
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert data["qr_data_uri"].startswith("data:image/png;base64,")


# ── Sessions ──────────────────────────────────────────────────────────────────

async def test_list_active_sessions(client, db_session, fake_clock):
    replay_cache.clear()
    cookie = await _login_admin(client, db_session)
    # Admin session itself should appear
    r = await client.get("/admin/sessions", cookies={"admin_session": cookie})
    assert r.status_code == 200
    sessions = r.json()
    assert isinstance(sessions, list)
    assert any(s["role"] == "admin" for s in sessions)


async def test_force_expire_session(client, db_session, fake_clock):
    replay_cache.clear()
    cookie = await _login_admin(client, db_session)

    # Vendor logs in
    vendor, _, seed_b32, uuid, _ = await _create_vendor(db_session, username="v_fexp")
    import pyotp
    from datetime import timezone
    code = pyotp.TOTP(seed_b32).at(fake_clock.dt.replace(tzinfo=timezone.utc))
    login_resp = await client.post("/auth/login", json={
        "username": vendor.username, "password": "pass123!",
        "totp_code": code
    })
    assert login_resp.status_code == 200
    vendor_token = login_resp.cookies.get("vendor_session")

    # Find vendor session ID
    sessions_resp = await client.get("/admin/sessions", cookies={"admin_session": cookie})
    vendor_session = next(
        (s for s in sessions_resp.json() if s["role"].startswith("vendor")), None
    )
    assert vendor_session is not None

    # Force expire
    r = await client.post(f"/admin/sessions/{vendor_session['id']}/expire",
                          cookies={"admin_session": cookie})
    assert r.status_code == 200
    assert r.json()["expired"] is True

    # Vendor token now invalid
    val = await client.post("/auth/validate", cookies={"vendor_session": vendor_token})
    assert val.status_code == 401


async def test_force_expire_nonexistent_session(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    r = await client.post("/admin/sessions/99999/expire",
                          cookies={"admin_session": cookie})
    assert r.status_code == 404


# ── Audit log ─────────────────────────────────────────────────────────────────

async def test_audit_log_returns_results(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    r = await client.get("/admin/audit", cookies={"admin_session": cookie})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert "page" in data


async def test_audit_log_filter_by_vendor_id(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    vendor, _, _, _, _ = await _create_vendor(db_session, username="v_audit")
    r = await client.get(f"/admin/audit?vendor_id={vendor.id}",
                         cookies={"admin_session": cookie})
    assert r.status_code == 200
    for row in r.json()["results"]:
        assert row["vendor_id"] == vendor.id


async def test_audit_log_filter_by_event_type(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    r = await client.get("/admin/audit?event_type=admin_login_success",
                         cookies={"admin_session": cookie})
    assert r.status_code == 200
    for row in r.json()["results"]:
        assert row["event_type"] == "admin_login_success"


async def test_audit_log_pagination(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    r = await client.get("/admin/audit?page=1&page_size=2",
                         cookies={"admin_session": cookie})
    assert r.status_code == 200
    data = r.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["results"]) <= 2


async def test_audit_log_csv_export(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    r = await client.get("/admin/audit",
                         headers={"accept": "text/csv"},
                         cookies={"admin_session": cookie})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("id,event_type")


async def test_audit_log_date_filter(client, db_session, fake_clock):
    cookie = await _login_admin(client, db_session)
    r = await client.get(
        "/admin/audit?date_from=2026-01-01T00:00:00&date_to=2026-12-31T23:59:59",
        cookies={"admin_session": cookie}
    )
    assert r.status_code == 200


# ── Endpoint guards ───────────────────────────────────────────────────────────

async def test_admin_endpoints_reject_unauthenticated(client):
    r = await client.get("/admin/devices")
    assert r.status_code == 401

    r = await client.get("/admin/sessions")
    assert r.status_code == 401

    r = await client.get("/admin/audit")
    assert r.status_code == 401
