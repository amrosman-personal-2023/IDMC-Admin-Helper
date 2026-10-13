"""
Script execution endpoint:
  POST /operations/run  — validate JWT, look up operation, spawn subprocess
"""
import asyncio
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import clock
from app.config import settings
from app.deps import require_vendor
from app.logger import log_event

router = APIRouter()

# Minimal clean environment — no parent env vars leak through
_CLEAN_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "en_US.UTF-8",
}


class RunRequest(BaseModel):
    operation_name: str


@router.post("/operations/run")
async def run_operation(
    body: RunRequest,
    claims: dict = Depends(require_vendor),
):
    role = claims.get("role", "")
    vendor_id = claims.get("vendor_id")

    op = settings.operations.get(body.operation_name)
    if op is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="operation not found")

    allowed_roles = op.get("roles", [])
    if role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="operation not permitted for your role")

    script_path = op["script"]
    start_ms = time.monotonic()

    try:
        proc = await asyncio.create_subprocess_exec(
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_CLEAN_ENV,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=settings.SCRIPT_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await asyncio.wait_for(proc.communicate(), timeout=5.0)
            except asyncio.TimeoutError:
                pass   # process or its children still alive; move on
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            log_event("script_timeout", vendor_id=vendor_id,
                      operation_name=body.operation_name,
                      duration_ms=duration_ms,
                      timestamp=clock.now_naive().isoformat())
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                                detail="operation timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="operation failed")

    duration_ms = int((time.monotonic() - start_ms) * 1000)
    exit_code = proc.returncode
    output = (stdout + stderr).decode(errors="replace")

    log_event("script_execution", vendor_id=vendor_id,
              operation_name=body.operation_name,
              exit_code=exit_code,
              duration_ms=duration_ms,
              timestamp=clock.now_naive().isoformat())

    return {
        "operation": body.operation_name,
        "exit_code": exit_code,
        "output": output[:4096],   # cap output returned to client
        "duration_ms": duration_ms,
    }
