"""
FastAPI dependency helpers for authentication and role enforcement.
"""
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import clock
from app.config import settings
from app.database import get_db
from app.models import Session as SessionModel
from app.security import safe_decode_jwt, sha256_hex

AUTH_FAILED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="authentication failed")
FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail="forbidden")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _resolve_session(token: str, db: AsyncSession) -> dict:
    """Decode JWT and verify corresponding session record is valid."""
    claims = safe_decode_jwt(token)
    if not claims:
        raise AUTH_FAILED
    token_hash = sha256_hex(token)
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if not session or session.invalidated:
        raise AUTH_FAILED
    now = clock.now_naive()
    if session.expires_at < now:
        raise AUTH_FAILED
    # Update last_active_at
    session.last_active_at = now
    await db.commit()
    return claims


async def require_admin(
    request: Request,
    admin_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not admin_session:
        raise AUTH_FAILED
    claims = await _resolve_session(admin_session, db)
    if claims.get("role") != "admin":
        raise FORBIDDEN
    return claims


async def require_vendor_jwt(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise AUTH_FAILED
    token = authorization.removeprefix("Bearer ").strip()
    claims = await _resolve_session(token, db)
    role = claims.get("role", "")
    if role == "admin":
        raise FORBIDDEN
    if not role.startswith("vendor"):
        raise AUTH_FAILED
    return claims
