"""
Vendor authentication: login, enrollment, JWT validation.
"""
import base64
import hashlib
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import audit, clock, replay_cache
from app.config import settings
from app.database import get_db
from app.models import AuthAttempt, Device, EnrollmentToken, Session as SessionModel, Vendor
from app.security import (
    constant_eq, generate_secure_token, generate_totp_seed, hash_password,
    issue_jwt, safe_decode_jwt, sha256_hex, verify_password, verify_totp_with_seed_b32,
)

router = APIRouter()

AUTH_FAILED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="authentication failed")
LOCKED = HTTPException(status_code=status.HTTP_423_LOCKED,
                       detail="authentication failed")


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _seed_to_b32(seed_bytes: bytes) -> str:
    return base64.b32encode(seed_bytes).decode()


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str
    # device_uuid removed — Google Authenticator does not register a device UUID.
    # The vendor's single non-revoked device record is looked up by vendor_id only.


VENDOR_COOKIE = "vendor_session"

@router.post("/auth/login")
async def vendor_login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    now = clock.now_naive()
    ip = _client_ip(request)

    result = await db.execute(select(Vendor).where(Vendor.username == body.username))
    vendor = result.scalar_one_or_none()

    lockout_cutoff = now - timedelta(minutes=settings.VENDOR_LOCKOUT_MINUTES)

    async def record_failure(vendor_id: Optional[int], reason: str) -> None:
        if vendor_id:
            db.add(AuthAttempt(
                vendor_id=vendor_id,
                attempted_at=now,
                success=False,
                failure_reason="auth_failed",
            ))
            await audit.write(db, "vendor_login_failure", vendor_id, "vendor",
                              source_ip=ip, vendor_id=vendor_id,
                              action_detail={"attempt_count": await _failure_count(db, vendor_id, lockout_cutoff)})
            await db.commit()

    if vendor is None or not vendor.active:
        verify_password("dummy", "$2b$12$aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        await record_failure(None, "unknown_vendor")
        raise AUTH_FAILED

    failure_count = await _failure_count(db, vendor.id, lockout_cutoff)
    if failure_count >= settings.VENDOR_LOCKOUT_ATTEMPTS:
        await record_failure(vendor.id, "locked")
        raise LOCKED

    password_ok = verify_password(body.password, vendor.bcrypt_password_hash)

    if not password_ok:
        await record_failure(vendor.id, "bad_password")
        raise AUTH_FAILED

    # Password correct. If no TOTP code supplied yet, tell the client to prompt for it.
    # This is NOT counted as a failure — the password was correct.
    if not body.totp_code:
        return {"totp_required": True}

    # Full authentication: find the vendor's active (non-revoked) device.
    dev_result = await db.execute(
        select(Device).where(
            Device.vendor_id == vendor.id,
            Device.revoked == False,  # noqa: E712
        ).order_by(Device.enrolled_at.desc()).limit(1)
    )
    device = dev_result.scalar_one_or_none()
    device_ok = device is not None

    totp_ok = False
    if device_ok:
        seed_b32 = _decrypt_seed(device.totp_seed_hash)
        if seed_b32:
            totp_now = clock.now()
            replayed = replay_cache.is_replayed(vendor.id, body.totp_code, totp_now.timestamp())
            totp_ok = (not replayed) and verify_totp_with_seed_b32(
                seed_b32, body.totp_code, totp_now, settings.TOTP_WINDOW
            )

    if not (device_ok and totp_ok):
        await record_failure(vendor.id, "bad_totp")
        raise AUTH_FAILED

    now_utc = clock.now()
    exp_utc = now_utc + timedelta(minutes=settings.JWT_VENDOR_EXPIRE_MINUTES)
    exp = now + timedelta(minutes=settings.JWT_VENDOR_EXPIRE_MINUTES)
    token = issue_jwt({
        "sub": str(vendor.id),
        "vendor_id": vendor.id,
        "role": vendor.role,
        "iat": int(now_utc.timestamp()),
        "exp": int(exp_utc.timestamp()),
    })

    token_hash = sha256_hex(token)
    db.add(SessionModel(
        session_token_hash=token_hash,
        subject_id=vendor.id,
        subject_type="vendor",
        role=vendor.role,
        created_at=now,
        last_active_at=now,
        expires_at=exp,
        invalidated=False,
        source_ip=ip,
    ))
    db.add(AuthAttempt(
        vendor_id=vendor.id,
        attempted_at=now,
        success=True,
        failure_reason=None,
    ))
    device.last_used_at = now
    await audit.write(db, "vendor_login_success", vendor.id, "vendor",
                      source_ip=ip, vendor_id=vendor.id,
                      action_detail={"session_token_hash": token_hash})
    await db.commit()

    response.set_cookie(
        key=VENDOR_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=int(settings.JWT_VENDOR_EXPIRE_MINUTES * 60),
    )
    return {"expires_at": exp.isoformat()}


async def _failure_count(db: AsyncSession, vendor_id: int, since) -> int:
    result = await db.execute(
        select(AuthAttempt).where(
            AuthAttempt.vendor_id == vendor_id,
            AuthAttempt.success == False,  # noqa: E712
            AuthAttempt.attempted_at >= since,
        )
    )
    return len(result.scalars().all())


def _decrypt_seed(totp_seed_hash: str) -> Optional[str]:
    """
    In this implementation totp_seed_hash IS the Fernet-encrypted seed_b32,
    stored under the column name used in the design doc.
    This avoids adding a separate column while satisfying the security model.
    The 'hash' column is reused as encrypted storage; the name is kept for
    schema compatibility with the design doc. Real deployments should rename it.
    """
    from app.seed_crypto import decrypt_seed
    return decrypt_seed(totp_seed_hash)


# ── Enrollment ────────────────────────────────────────────────────────────────

class EnrollRequest(BaseModel):
    enrollment_token: str
    # device_uuid removed — Google Authenticator enrollment is triggered by the
    # admin scanning a QR code; no device UUID is registered.


@router.post("/enroll")
async def enroll(body: EnrollRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Google Authenticator enrollment flow:
    1. Admin calls POST /admin/vendors to create a vendor.
    2. The response includes an enrollment_token (single-use, 24 h TTL).
    3. Admin calls this endpoint with that token.
    4. Server generates a TOTP seed, stores it encrypted, and returns:
       - otpauth_uri: the otpauth:// URI to encode as a QR code
       - qr_data_uri: a ready-to-display data:image/png;base64,... QR image
    5. Admin displays the QR code to the vendor (or emails the otpauth URI).
    6. Vendor scans with Google Authenticator — no custom app needed.
    """
    now = clock.now_naive()
    ip = _client_ip(request)

    token_hash = sha256_hex(body.enrollment_token)
    result = await db.execute(
        select(EnrollmentToken).where(EnrollmentToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if token_record is None or token_record.used or token_record.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="enrollment token invalid or expired")

    # Look up vendor username for the otpauth label
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == token_record.vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="vendor not found")

    # Generate TOTP seed
    seed_bytes = generate_totp_seed()
    seed_b32 = base64.b32encode(seed_bytes).decode()

    # Encrypt seed for storage — never stored in plaintext
    from app.seed_crypto import encrypt_seed
    seed_enc = encrypt_seed(seed_b32)

    # Use a fixed placeholder UUID — device binding is not used with Google Authenticator
    placeholder_uuid = "google-authenticator"
    uuid_hash = sha256_hex(placeholder_uuid)

    # Single transaction: create device record, mark token used
    token_record.used = True
    token_record.used_at = now
    db.add(Device(
        vendor_id=token_record.vendor_id,
        uuid_hash=uuid_hash,
        totp_seed_hash=seed_enc,
        enrolled_at=now,
        revoked=False,
    ))
    await audit.write(db, "enrollment", token_record.vendor_id, "vendor",
                      source_ip=ip, vendor_id=token_record.vendor_id,
                      action_detail={"token_hash": token_hash, "method": "google_authenticator"})
    await db.commit()

    # Build otpauth:// URI and QR code — returned once, never stored
    from app.qr import otpauth_uri, qr_data_uri
    uri = otpauth_uri(vendor.username, seed_b32)
    return {
        "enrolled": True,
        "otpauth_uri": uri,
        "qr_data_uri": qr_data_uri(uri),
    }


# ── Validate — reads the HttpOnly vendor_session cookie ──────────────────────

@router.post("/auth/validate")
async def validate_vendor_token(
    vendor_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the SPA with an empty body. The vendor_session HttpOnly cookie
    is forwarded automatically by the browser (credentials:'include').
    """
    if not vendor_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session")
    claims = safe_decode_jwt(vendor_session)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    role = claims.get("role", "")
    if role == "admin" or not role.startswith("vendor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    token_hash = sha256_hex(vendor_session)
    now = clock.now_naive()
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if not session or session.invalidated or session.expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")
    return {
        "valid": True,
        "vendor_id": claims.get("vendor_id"),
        "role": claims.get("role"),
        "expires_at": session.expires_at.isoformat(),
    }


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/auth/logout")
async def vendor_logout(
    response: Response,
    vendor_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if vendor_session:
        token_hash = sha256_hex(vendor_session)
        result = await db.execute(
            select(SessionModel).where(SessionModel.session_token_hash == token_hash)
        )
        session = result.scalar_one_or_none()
        if session and not session.invalidated:
            session.invalidated = True
            await db.commit()
    response.delete_cookie(VENDOR_COOKIE)
    return {"logged_out": True}


# ── Renew ─────────────────────────────────────────────────────────────────────

class RenewRequest(BaseModel):
    totp_code: str


@router.post("/auth/renew")
async def vendor_renew(
    body: RenewRequest,
    request: Request,
    response: Response,
    vendor_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not vendor_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session")
    claims = safe_decode_jwt(vendor_session)
    if not claims or not claims.get("role", "").startswith("vendor"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")

    token_hash = sha256_hex(vendor_session)
    now = clock.now_naive()
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if not session or session.invalidated or session.expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")

    vendor_id = claims.get("vendor_id")

    # Verify TOTP
    dev_result = await db.execute(
        select(Device).where(
            Device.vendor_id == vendor_id,
            Device.revoked == False,  # noqa: E712
        ).order_by(Device.enrolled_at.desc()).limit(1)
    )
    device = dev_result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no device")

    seed_b32 = _decrypt_seed(device.totp_seed_hash)
    if not seed_b32:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid device")

    totp_now = clock.now()
    replayed = replay_cache.is_replayed(vendor_id, body.totp_code, totp_now.timestamp())
    totp_ok = (not replayed) and verify_totp_with_seed_b32(
        seed_b32, body.totp_code, totp_now, settings.TOTP_WINDOW
    )
    if not totp_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication failed")

    # Issue fresh token with new expiry
    now_utc = clock.now()
    exp_utc = now_utc + timedelta(minutes=settings.JWT_VENDOR_EXPIRE_MINUTES)
    exp = now + timedelta(minutes=settings.JWT_VENDOR_EXPIRE_MINUTES)
    new_token = issue_jwt({
        "sub": str(vendor_id),
        "vendor_id": vendor_id,
        "role": claims.get("role"),
        "iat": int(now_utc.timestamp()),
        "exp": int(exp_utc.timestamp()),
    })
    new_token_hash = sha256_hex(new_token)

    # Invalidate old session, create new one
    session.invalidated = True
    db.add(SessionModel(
        session_token_hash=new_token_hash,
        subject_id=vendor_id,
        subject_type="vendor",
        role=claims.get("role"),
        created_at=now,
        last_active_at=now,
        expires_at=exp,
        invalidated=False,
        source_ip=_client_ip(request),
    ))
    await db.commit()

    response.set_cookie(
        key=VENDOR_COOKIE,
        value=new_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=int(settings.JWT_VENDOR_EXPIRE_MINUTES * 60),
    )
    return {"expires_at": exp.isoformat()}
