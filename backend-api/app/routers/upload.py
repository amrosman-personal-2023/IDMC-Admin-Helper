"""
File upload endpoints:
  POST /upload/request  — validate JWT + path, issue upload token
  PUT  /upload/{token}  — consume token, write file atomically
"""
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi import UploadFile, File
from pydantic import BaseModel

from app import clock, upload_token
from app.config import settings
from app.deps import require_vendor
from app.logger import log_event
from app.sanitize import sanitize_filename

router = APIRouter()


def _resolve_and_guard(directory: str, filename: str) -> Path:
    """
    Build the target path from directory + filename, canonicalize it,
    and confirm it stays inside IDMC_STAGING_ROOT.
    Raises 400 on traversal attempt.
    """
    staging = Path(settings.IDMC_STAGING_ROOT).resolve()
    target = (staging / directory / filename).resolve()
    if not str(target).startswith(str(staging) + os.sep) and target != staging:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="invalid path")
    return target


def _check_extension(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{suffix or '(none)'}' is not permitted. "
                   f"Allowed extensions: {allowed}",
        )


# ── Request upload token ──────────────────────────────────────────────────────

class UploadRequestBody(BaseModel):
    directory: str
    filename: str


@router.post("/upload/request")
async def request_upload(
    body: UploadRequestBody,
    claims: dict = Depends(require_vendor),
):
    role = claims.get("role", "")
    vendor_id = claims.get("vendor_id")

    # Check directory is in vendor's allowed list
    allowed_dirs = settings.allowed_paths.get(role, [])
    if body.directory not in allowed_dirs:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="directory not permitted for your role")

    # Sanitize filename
    safe_name = sanitize_filename(body.filename)
    if not safe_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="invalid filename")

    _check_extension(safe_name)

    # Resolve and guard path
    target = _resolve_and_guard(body.directory, safe_name)

    token = upload_token.issue(vendor_id, role, str(target))
    exp = clock.now_naive()
    from datetime import timedelta
    exp = exp + timedelta(minutes=settings.UPLOAD_TOKEN_EXPIRE_MINUTES)

    log_event("upload_token_issued", vendor_id=vendor_id, role=role,
              directory=body.directory, filename=safe_name)

    return {"upload_token": token, "expires_at": exp.isoformat()}


# ── Execute upload ────────────────────────────────────────────────────────────

@router.put("/upload/{token}")
async def execute_upload(
    token: str,
    request: Request,
):
    payload = upload_token.consume(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="upload token invalid or expired")

    vendor_id = payload["vendor_id"]
    abs_path = Path(payload["path"])

    # Re-verify the resolved path is still inside staging root (defence in depth)
    staging = Path(settings.IDMC_STAGING_ROOT).resolve()
    if not str(abs_path).startswith(str(staging) + os.sep):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="invalid path")

    # Enforce file size before reading
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="file too large")

    body = await request.body()
    if len(body) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="file too large")

    # Ensure parent directory exists
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file in same directory, then rename
    try:
        fd, tmp_path = tempfile.mkstemp(dir=abs_path.parent, prefix=".tmp_upload_")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(body)
            os.replace(tmp_path, abs_path)   # atomic on POSIX; best-effort on Windows
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError as exc:
        log_event("upload_error", vendor_id=vendor_id, filename=abs_path.name,
                  error="write_failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="upload failed")

    file_size = len(body)
    log_event("file_upload", vendor_id=vendor_id, filename=abs_path.name,
              file_size_bytes=file_size, timestamp=clock.now_naive().isoformat())

    return {"uploaded": True, "path": abs_path.name}
