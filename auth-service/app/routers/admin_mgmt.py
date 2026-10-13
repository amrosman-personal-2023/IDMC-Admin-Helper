"""
Admin management endpoints: vendors, devices, sessions, audit log.
All require role=admin JWT via the admin_session cookie.
"""
import csv
import io
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import audit, clock
from app.config import settings
from app.database import get_db
from app.deps import require_admin
from app.models import (
    AuditLog, Device, EnrollmentToken, Session as SessionModel, Vendor
)
from app.security import generate_secure_token, hash_password, sha256_hex

router = APIRouter(prefix="/admin")


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    from sqlalchemy import func
    from app.models import Admin
    now = clock.now_naive()
    cutoff_24h = now - timedelta(hours=24)

    # Active vendors
    active_vendors = (await db.execute(
        select(func.count()).select_from(Vendor).where(Vendor.active == True)  # noqa: E712
    )).scalar_one()

    # Enrolled (non-revoked) devices
    enrolled_devices = (await db.execute(
        select(func.count()).select_from(Device).where(Device.revoked == False)  # noqa: E712
    )).scalar_one()

    # Active sessions
    active_sessions = (await db.execute(
        select(func.count()).select_from(SessionModel).where(
            SessionModel.invalidated == False,  # noqa: E712
            SessionModel.expires_at > now,
        )
    )).scalar_one()

    # Audit events in last 24 h
    audit_events_24h = (await db.execute(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.timestamp >= cutoff_24h
        )
    )).scalar_one()

    # Recent 20 audit rows
    recent_result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(20)
    )
    recent = recent_result.scalars().all()

    return {
        "active_vendors": active_vendors,
        "enrolled_devices": enrolled_devices,
        "active_sessions": active_sessions,
        "audit_events_24h": audit_events_24h,
        "recent_audit": [
            {
                "id": r.id,
                "event_type": r.event_type,
                "subject_id": r.subject_id,
                "subject_type": r.subject_type,
                "vendor_id": r.vendor_id,
                "timestamp": r.timestamp.isoformat(),
                "source_ip": r.source_ip,
                "action_detail": r.action_detail,
            }
            for r in recent
        ],
    }


# ── Vendors ───────────────────────────────────────────────────────────────────

@router.get("/vendors")
async def list_vendors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    from sqlalchemy import func
    result = await db.execute(
        select(Vendor).order_by(Vendor.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    vendors = result.scalars().all()

    # Device count per vendor
    rows = []
    for v in vendors:
        count = (await db.execute(
            select(func.count()).select_from(Device).where(Device.vendor_id == v.id)
        )).scalar_one()
        rows.append({
            "id": v.id,
            "username": v.username,
            "role": v.role,
            "created_at": v.created_at.isoformat(),
            "active": v.active,
            "device_count": count,
        })
    return rows


class CreateVendorRequest(BaseModel):
    username: str
    password: str
    role: str = "vendor_standard"


@router.post("/vendors")
async def create_vendor(
    body: CreateVendorRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    now = clock.now_naive()
    # Check username unique
    existing = await db.execute(select(Vendor).where(Vendor.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists")

    vendor = Vendor(
        username=body.username,
        bcrypt_password_hash=hash_password(body.password),
        role=body.role,
        created_at=now,
        active=True,
    )
    db.add(vendor)
    await db.flush()  # get vendor.id

    raw_token = generate_secure_token(32)
    token_hash = sha256_hex(raw_token)
    expires_at = now + timedelta(hours=settings.ENROLLMENT_TOKEN_EXPIRE_HOURS)
    db.add(EnrollmentToken(
        token_hash=token_hash,
        vendor_id=vendor.id,
        expires_at=expires_at,
        used=False,
    ))
    await audit.write(db, "vendor_created", admin_claims["admin_id"], "admin",
                      source_ip=_client_ip(request),
                      vendor_id=vendor.id,
                      action_detail={"username": body.username, "role": body.role})
    await db.commit()

    # Immediately enroll using the token — generate seed + QR code in one step.
    # The admin shows the QR code to the vendor; vendor scans with Google Authenticator.
    from app.qr import otpauth_uri, qr_data_uri
    from app.seed_crypto import encrypt_seed
    from app.security import generate_totp_seed
    import base64 as _b64

    seed_bytes = generate_totp_seed()
    seed_b32 = _b64.b32encode(seed_bytes).decode()
    seed_enc = encrypt_seed(seed_b32)
    placeholder_uuid = "google-authenticator"
    uuid_hash = sha256_hex(placeholder_uuid)

    # Mark token used and create device in the same transaction
    token_record_result = await db.execute(
        select(EnrollmentToken).where(EnrollmentToken.token_hash == token_hash)
    )
    token_rec = token_record_result.scalar_one()
    token_rec.used = True
    token_rec.used_at = clock.now_naive()
    from app.models import Device as DeviceModel
    db.add(DeviceModel(
        vendor_id=vendor.id,
        uuid_hash=uuid_hash,
        totp_seed_hash=seed_enc,
        enrolled_at=clock.now_naive(),
        revoked=False,
    ))
    await db.commit()

    uri = otpauth_uri(vendor.username, seed_b32)
    return {
        "vendor_id": vendor.id,
        "username": vendor.username,
        "role": vendor.role,
        "otpauth_uri": uri,
        "qr_data_uri": qr_data_uri(uri),
    }


@router.post("/vendors/{vendor_id}/deactivate")
async def deactivate_vendor(
    vendor_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    now = clock.now_naive()
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vendor not found")

    # Atomic: deactivate vendor, revoke all devices, invalidate all sessions
    vendor.active = False

    dev_result = await db.execute(select(Device).where(Device.vendor_id == vendor_id))
    devices = dev_result.scalars().all()
    revoked_count = 0
    for device in devices:
        if not device.revoked:
            device.revoked = True
            device.revoked_at = now
            revoked_count += 1

    sess_result = await db.execute(
        select(SessionModel).where(
            and_(
                SessionModel.subject_id == vendor_id,
                SessionModel.subject_type == "vendor",
                SessionModel.invalidated == False,  # noqa: E712
            )
        )
    )
    sessions = sess_result.scalars().all()
    invalidated_count = 0
    for session in sessions:
        session.invalidated = True
        invalidated_count += 1

    await audit.write(db, "vendor_deactivation", admin_claims["admin_id"], "admin",
                      source_ip=_client_ip(request),
                      vendor_id=vendor_id,
                      action_detail={
                          "devices_revoked": revoked_count,
                          "sessions_invalidated": invalidated_count,
                      })
    await db.commit()
    return {
        "vendor_id": vendor_id,
        "deactivated": True,
        "devices_revoked": revoked_count,
        "sessions_invalidated": invalidated_count,
    }


# ── Devices ───────────────────────────────────────────────────────────────────

class RevokeDeviceRequest(BaseModel):
    device_uuid: str
    vendor_id: int


@router.post("/devices/revoke")
async def revoke_device(
    body: RevokeDeviceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    now = clock.now_naive()
    uuid_hash = sha256_hex(body.device_uuid)
    result = await db.execute(
        select(Device).where(
            Device.vendor_id == body.vendor_id,
            Device.uuid_hash == uuid_hash,
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")
    device.revoked = True
    device.revoked_at = now
    await audit.write(db, "device_revocation", admin_claims["admin_id"], "admin",
                      source_ip=_client_ip(request),
                      vendor_id=body.vendor_id,
                      device_uuid_hash=uuid_hash,
                      action_detail={"device_id": device.id})
    await db.commit()
    return {"device_id": device.id, "revoked": True}


@router.get("/devices")
async def list_devices(
    vendor_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    query = select(Device)
    if vendor_id is not None:
        query = query.where(Device.vendor_id == vendor_id)
    result = await db.execute(query)
    devices = result.scalars().all()
    return [
        {
            "id": d.id,
            "vendor_id": d.vendor_id,
            "uuid_hash_suffix": d.uuid_hash[-8:],
            "enrolled_at": d.enrolled_at.isoformat(),
            "revoked": d.revoked,
            "revoked_at": d.revoked_at.isoformat() if d.revoked_at else None,
            "last_used_at": d.last_used_at.isoformat() if d.last_used_at else None,
        }
        for d in devices
    ]


class ReissueEnrollmentRequest(BaseModel):
    vendor_id: int


@router.post("/enrollment-links")
async def reissue_enrollment_link(
    body: ReissueEnrollmentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    now = clock.now_naive()
    result = await db.execute(select(Vendor).where(Vendor.id == body.vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vendor not found")

    # Revoke any existing active device before re-enrolling
    dev_result = await db.execute(
        select(Device).where(Device.vendor_id == body.vendor_id, Device.revoked == False)  # noqa: E712
    )
    for old_device in dev_result.scalars().all():
        old_device.revoked = True
        old_device.revoked_at = now

    # Generate new seed + device record immediately — return QR code to admin
    from app.qr import otpauth_uri, qr_data_uri
    from app.seed_crypto import encrypt_seed
    from app.security import generate_totp_seed
    import base64 as _b64

    seed_bytes = generate_totp_seed()
    seed_b32 = _b64.b32encode(seed_bytes).decode()
    seed_enc = encrypt_seed(seed_b32)
    uuid_hash = sha256_hex("google-authenticator")

    db.add(Device(
        vendor_id=body.vendor_id,
        uuid_hash=uuid_hash,
        totp_seed_hash=seed_enc,
        enrolled_at=now,
        revoked=False,
    ))
    await audit.write(db, "re_enrollment", admin_claims["admin_id"], "admin",
                      source_ip=_client_ip(request),
                      vendor_id=body.vendor_id,
                      action_detail={"method": "google_authenticator"})
    await db.commit()

    uri = otpauth_uri(vendor.username, seed_b32)
    return {
        "vendor_id": body.vendor_id,
        "otpauth_uri": uri,
        "qr_data_uri": qr_data_uri(uri),
    }


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    now = clock.now_naive()
    result = await db.execute(
        select(SessionModel).where(
            SessionModel.invalidated == False,  # noqa: E712
            SessionModel.expires_at > now,
        )
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "subject_id": s.subject_id,
            "subject_type": s.subject_type,
            "role": s.role,
            "created_at": s.created_at.isoformat(),
            "last_active_at": s.last_active_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "source_ip": s.source_ip,
        }
        for s in sessions
    ]


@router.post("/sessions/{session_id}/expire")
async def force_expire_session(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    session.invalidated = True
    await audit.write(db, "force_expire_session", admin_claims["admin_id"], "admin",
                      source_ip=_client_ip(request),
                      action_detail={
                          "target_session_id": session_id,
                          "target_subject_id": session.subject_id,
                          "target_role": session.role,
                      })
    await db.commit()
    return {"session_id": session_id, "expired": True}


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit")
async def get_audit_log(
    request: Request,
    vendor_id: Optional[int] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin_claims: dict = Depends(require_admin),
):
    from datetime import datetime as dt
    filters = []
    if vendor_id is not None:
        filters.append(AuditLog.vendor_id == vendor_id)
    if event_type:
        filters.append(AuditLog.event_type == event_type)
    if date_from:
        filters.append(AuditLog.timestamp >= dt.fromisoformat(date_from))
    if date_to:
        filters.append(AuditLog.timestamp <= dt.fromisoformat(date_to))

    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if filters:
        query = query.where(and_(*filters))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rows = result.scalars().all()

    accept = request.headers.get("accept", "")
    if "text/csv" in accept:
        return _csv_response(rows)

    return {
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": r.id,
                "event_type": r.event_type,
                "subject_id": r.subject_id,
                "subject_type": r.subject_type,
                "vendor_id": r.vendor_id,
                "device_uuid_hash": r.device_uuid_hash,
                "action_detail": r.action_detail,
                "timestamp": r.timestamp.isoformat(),
                "source_ip": r.source_ip,
            }
            for r in rows
        ],
    }


def _csv_response(rows) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "event_type", "subject_id", "subject_type",
                     "vendor_id", "device_uuid_hash", "timestamp", "source_ip"])
    for r in rows:
        writer.writerow([r.id, r.event_type, r.subject_id, r.subject_type,
                         r.vendor_id, r.device_uuid_hash,
                         r.timestamp.isoformat(), r.source_ip])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
