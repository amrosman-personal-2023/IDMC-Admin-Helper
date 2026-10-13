"""
Admin authentication: login, logout, JWT validation.
No TOTP — password only.
"""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import audit, clock
from app.config import settings
from app.database import get_db
from app.models import Admin, AdminAttempt, Session as SessionModel
from app.security import issue_jwt, safe_decode_jwt, sha256_hex, verify_password

router = APIRouter(prefix="/admin/auth")

AUTH_FAILED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="authentication failed")
LOCKED = HTTPException(status_code=status.HTTP_423_LOCKED,
                       detail="authentication failed")

COOKIE_NAME = "admin_session"


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _failure_count(db: AsyncSession, admin_id: int, since) -> int:
    result = await db.execute(
        select(AdminAttempt).where(
            AdminAttempt.admin_id == admin_id,
            AdminAttempt.success == False,  # noqa: E712
            AdminAttempt.attempted_at >= since,
        )
    )
    return len(result.scalars().all())


# ── Login ─────────────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    now = clock.now_naive()
    ip = _client_ip(request)
    lockout_cutoff = now - timedelta(minutes=settings.ADMIN_LOCKOUT_MINUTES)

    result = await db.execute(select(Admin).where(Admin.username == body.username))
    admin = result.scalar_one_or_none()

    async def record_failure(admin_id: Optional[int]) -> None:
        if admin_id:
            db.add(AdminAttempt(admin_id=admin_id, attempted_at=now, success=False,
                                failure_reason="auth_failed"))
            await audit.write(db, "admin_login_failure", admin_id, "admin",
                              source_ip=ip,
                              action_detail={"username_hash": sha256_hex(body.username)})
            await db.commit()

    if admin is None or not admin.active:
        verify_password("dummy", "$2b$12$aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        await record_failure(None)
        raise AUTH_FAILED

    failure_count = await _failure_count(db, admin.id, lockout_cutoff)
    if failure_count >= settings.ADMIN_LOCKOUT_ATTEMPTS:
        await record_failure(admin.id)
        raise LOCKED

    if not verify_password(body.password, admin.bcrypt_password_hash):
        await record_failure(admin.id)
        raise AUTH_FAILED

    now_utc = clock.now()
    exp_utc = now_utc + timedelta(hours=settings.JWT_ADMIN_EXPIRE_HOURS)
    exp = now + timedelta(hours=settings.JWT_ADMIN_EXPIRE_HOURS)  # naive for DB
    token = issue_jwt({
        "sub": str(admin.id),
        "admin_id": admin.id,
        "role": "admin",
        "iat": int(now_utc.timestamp()),
        "exp": int(exp_utc.timestamp()),
    })

    token_hash = sha256_hex(token)
    db.add(SessionModel(
        session_token_hash=token_hash,
        subject_id=admin.id,
        subject_type="admin",
        role="admin",
        created_at=now,
        last_active_at=now,
        expires_at=exp,
        invalidated=False,
        source_ip=ip,
    ))
    db.add(AdminAttempt(admin_id=admin.id, attempted_at=now, success=True))
    await audit.write(db, "admin_login_success", admin.id, "admin",
                      source_ip=ip,
                      action_detail={"session_token_hash": token_hash})
    await db.commit()

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=int(settings.JWT_ADMIN_EXPIRE_HOURS * 3600),
    )
    return {"logged_in": True, "expires_at": exp.isoformat()}


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def admin_logout(
    response: Response,
    admin_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if admin_session:
        token_hash = sha256_hex(admin_session)
        result = await db.execute(
            select(SessionModel).where(SessionModel.session_token_hash == token_hash)
        )
        session = result.scalar_one_or_none()
        if session and not session.invalidated:
            session.invalidated = True
            await db.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"logged_out": True}


# ── Validate — reads the HttpOnly cookie directly ────────────────────────────

@router.post("/validate")
async def validate_admin_token(
    admin_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the SPA with an empty body.  The admin_session HttpOnly cookie
    is forwarded automatically by the browser (credentials:'include').
    JavaScript never has access to the token value.
    """
    if not admin_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session")
    claims = safe_decode_jwt(admin_session)
    if not claims or claims.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    token_hash = sha256_hex(admin_session)
    now = clock.now_naive()
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if not session or session.invalidated or session.expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")
    return {
        "valid": True,
        "admin_id": claims.get("admin_id"),
        "role": "admin",
        "expires_at": session.expires_at.isoformat(),
    }
