"""
FastAPI dependency: extract vendor_session cookie and validate it via auth service.
"""
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status

from app.auth_client import validate_vendor_jwt

AUTH_FAILED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="authentication failed")


async def require_vendor(
    vendor_session: Optional[str] = Cookie(default=None),
) -> dict:
    if not vendor_session:
        raise AUTH_FAILED
    return await validate_vendor_jwt(vendor_session)
