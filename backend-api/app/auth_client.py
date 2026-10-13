"""
HTTP client for the Auth Service /auth/validate endpoint.
Forwards the vendor_session HttpOnly cookie from the browser request so the
auth service can validate it — no token is passed in the request body.
"""
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.config import settings

_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(base_url=settings.AUTH_SERVICE_URL, timeout=5.0)
    return _client


async def validate_vendor_jwt(vendor_session_cookie: str) -> dict:
    """
    Call Auth Service POST /auth/validate, forwarding the vendor_session cookie.
    The auth service reads the cookie directly — no token in the body.
    """
    try:
        resp = await get_client().post(
            "/auth/validate",
            cookies={"vendor_session": vendor_session_cookie},
        )
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="auth service unavailable")

    if resp.status_code == 403:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="authentication failed")
    return resp.json()
