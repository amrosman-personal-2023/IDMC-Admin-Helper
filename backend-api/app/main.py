from contextlib import asynccontextmanager
from typing import List

from fastapi import Cookie, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from app.config import load_required_settings, settings
from app.deps import require_vendor
from app.routers import logs, operations, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_required_settings()
    yield


app = FastAPI(title="IDMC Backend API", lifespan=lifespan)

app.include_router(upload.router)
app.include_router(operations.router)
app.include_router(logs.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/portal/config")
async def portal_config(claims: dict = Depends(require_vendor)):
    """
    Return the directories and operations permitted for the authenticated vendor's role.
    The frontend uses this to render only what the vendor is allowed to access.
    """
    role = claims.get("role", "")
    directories = settings.allowed_paths.get(role, [])

    operations_list = [
        {"name": name, "description": f"Run {name}"}
        for name, op in settings.operations.items()
        if role in op.get("roles", [])
    ]

    return {
        "role": role,
        "directories": directories,
        "operations": operations_list,
    }


# ── Admin: allowed file extensions ───────────────────────────────────────────
# These endpoints require the admin_session cookie forwarded from the SPA.
# Validation is delegated to the auth service via the same cookie-based pattern.

async def require_admin_session(admin_session: str = Cookie(default=None)):
    """Validate admin_session cookie against the auth service."""
    import httpx
    if not admin_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="admin session required")
    try:
        async with httpx.AsyncClient(base_url=settings.AUTH_SERVICE_URL, timeout=5.0) as c:
            resp = await c.post("/admin/auth/validate",
                                cookies={"admin_session": admin_session})
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="auth service unavailable")
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="invalid admin session")
    return resp.json()


@app.get("/admin/extensions")
async def get_extensions(admin=Depends(require_admin_session)):
    """Return the current list of allowed upload file extensions."""
    return {"extensions": sorted(settings.ALLOWED_EXTENSIONS)}


class ExtensionsUpdate(BaseModel):
    extensions: List[str]


@app.put("/admin/extensions")
async def update_extensions(
    body: ExtensionsUpdate,
    admin=Depends(require_admin_session),
):
    """
    Replace the allowed extensions list.
    Each extension must start with a dot and contain only safe characters.
    Changes take effect immediately for all subsequent upload requests.
    """
    import re
    valid_ext = re.compile(r'^\.[a-zA-Z0-9]{1,16}$')
    cleaned = set()
    for ext in body.extensions:
        ext = ext.strip().lower()
        if not valid_ext.match(ext):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid extension: {ext!r}. Must start with a dot and contain only alphanumeric characters."
            )
        cleaned.add(ext)

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one extension is required."
        )

    settings.ALLOWED_EXTENSIONS = frozenset(cleaned)
    return {"extensions": sorted(settings.ALLOWED_EXTENSIONS)}
