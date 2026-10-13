"""
Admin Log Analyser endpoints.
All require admin_session cookie (validated via auth service).
All file paths are guarded inside one of the configured log roots (log_paths.yaml).
"""
import json
import os
import time
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import llm_client, llm_settings
from app.config import settings

router = APIRouter(prefix="/admin")

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def _infer_service(path: str) -> str:
    """Return the label of the log root that contains this path."""
    resolved = str(Path(path).resolve())
    for root in settings.log_roots:
        root_resolved = str(Path(root["path"]).resolve())
        if resolved.startswith(root_resolved):
            return root["label"]
    return "IDMC — Unknown Service"


def _guard(path: str) -> Path:
    """Resolve path and confirm it sits inside at least one configured log root."""
    target = Path(path).resolve()
    for root in settings.log_roots:
        root_resolved = Path(root["path"]).resolve()
        if str(target).startswith(str(root_resolved)):
            return target
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="path is outside all configured log roots")


async def _require_admin(admin_session: Optional[str] = Cookie(default=None)):
    import httpx
    if not admin_session:
        raise HTTPException(status_code=401, detail="admin session required")
    try:
        async with httpx.AsyncClient(base_url=settings.AUTH_SERVICE_URL, timeout=5.0) as c:
            resp = await c.post("/admin/auth/validate",
                                cookies={"admin_session": admin_session})
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="auth service unavailable")
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="invalid admin session")
    return resp.json()


# ── Directory tree ────────────────────────────────────────────────────────────

@router.get("/logs/tree")
async def log_tree(
    path: Optional[str] = Query(default=None),
    admin=Depends(_require_admin),
):
    # No path → return the list of configured log roots for the FileTree to display
    if path is None:
        return {
            "roots": [
                {"name": r["name"], "label": r["label"], "path": r["path"]}
                for r in settings.log_roots
            ]
        }

    target = _guard(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="path not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="path is not a directory")

    entries = []
    try:
        items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        for item in items:
            try:
                stat = item.stat()
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "file" if item.is_file() else "dir",
                    "size_bytes": stat.st_size if item.is_file() else None,
                    "modified_at": stat.st_mtime,
                })
            except OSError:
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="permission denied")

    return {"path": str(target), "entries": entries}


# ── File content ──────────────────────────────────────────────────────────────

@router.get("/logs/file")
async def log_file(
    path: str = Query(...),
    admin=Depends(_require_admin),
):
    target = _guard(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="file not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="path is not a file")

    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        raise HTTPException(status_code=413,
                            detail=f"File too large ({size:,} bytes). Maximum is 10 MB.")

    raw = target.read_bytes()
    encoding = "utf-8"
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = raw.decode("latin-1")
            encoding = "latin-1"
        except Exception:
            raise HTTPException(status_code=422, detail="file is not readable as text")

    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    service = _infer_service(str(target))

    return {
        "path": str(target),
        "content": content,
        "lines": lines,
        "size_bytes": size,
        "service": service,
        "directory": str(target.parent),
        "encoding": encoding,
        "sensitive": llm_client.is_sensitive(content),
    }


# ── LLM — initial analysis ────────────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    file_path: str
    content: str
    service: str
    directory: str
    lines: int = 0
    size_bytes: int = 0


@router.post("/logs/analyse")
async def analyse_log(body: AnalyseRequest, admin=Depends(_require_admin)):
    cfg = llm_settings.load()
    system_prompt, _ = llm_client.build_system_prompt(
        file_path=body.file_path,
        service=body.service,
        directory=body.directory,
        size_bytes=body.size_bytes,
        lines=body.lines,
        content=body.content,
        max_tokens=cfg.get("max_context_tokens", 80000),
    )

    async def event_stream():
        async for delta in llm_client.stream_llm(
            messages=[{"role": "user", "content": "Please analyse this log file."}],
            system_prompt=system_prompt,
        ):
            yield f"data: {json.dumps({'delta': delta})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── LLM — chat ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    messages: List[dict]
    context: AnalyseRequest


@router.post("/logs/chat")
async def chat_log(body: ChatRequest, admin=Depends(_require_admin)):
    cfg = llm_settings.load()
    system_prompt, _ = llm_client.build_system_prompt(
        file_path=body.context.file_path,
        service=body.context.service,
        directory=body.context.directory,
        size_bytes=body.context.size_bytes,
        lines=body.context.lines,
        content=body.context.content,
        max_tokens=cfg.get("max_context_tokens", 80000),
    )

    async def event_stream():
        async for delta in llm_client.stream_llm(
            messages=body.messages,
            system_prompt=system_prompt,
        ):
            yield f"data: {json.dumps({'delta': delta})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── LLM settings ──────────────────────────────────────────────────────────────

class LlmSettingsUpdate(BaseModel):
    provider: str
    model: str
    api_key: str
    max_context_tokens: int
    azure_endpoint: Optional[str] = ""
    azure_deployment: Optional[str] = ""


@router.get("/llm/settings")
async def get_llm_settings(admin=Depends(_require_admin)):
    cfg = llm_settings.load()
    return {
        "provider": cfg.get("provider", "anthropic"),
        "model": cfg.get("model", "claude-opus-4-8"),
        "api_key_masked": llm_settings.masked_key(cfg.get("api_key", "")),
        "max_context_tokens": cfg.get("max_context_tokens", 80000),
        "azure_endpoint": cfg.get("azure_endpoint", ""),
        "azure_deployment": cfg.get("azure_deployment", ""),
    }


@router.put("/llm/settings")
async def update_llm_settings(body: LlmSettingsUpdate, admin=Depends(_require_admin)):
    if body.provider not in ("anthropic", "openai", "azure_openai", "gemini"):
        raise HTTPException(status_code=422, detail="provider must be anthropic, openai, azure_openai, or gemini")
    if not 1000 <= body.max_context_tokens <= 200000:
        raise HTTPException(status_code=422, detail="max_context_tokens must be between 1,000 and 200,000")

    # "__keep__" is the sentinel sent by the frontend when the API key field is left blank.
    # In that case, keep the previously stored key instead of overwriting it.
    existing = llm_settings.load()
    submitted_key = body.api_key.strip()
    if submitted_key in ("", "__keep__"):
        api_key = existing.get("api_key", "")
    else:
        api_key = submitted_key

    if not api_key:
        raise HTTPException(status_code=422,
                            detail="No API key is stored. Enter a key to save settings.")

    cfg = {
        "provider": body.provider,
        "model": body.model.strip(),
        "api_key": api_key,
        "max_context_tokens": body.max_context_tokens,
        "azure_endpoint": (body.azure_endpoint or "").strip(),
        "azure_deployment": (body.azure_deployment or "").strip(),
    }
    llm_settings.save(cfg)

    return {
        "provider": cfg["provider"],
        "model": cfg["model"],
        "api_key_masked": llm_settings.masked_key(cfg["api_key"]),
        "max_context_tokens": cfg["max_context_tokens"],
        "azure_endpoint": cfg["azure_endpoint"],
        "azure_deployment": cfg["azure_deployment"],
    }


@router.post("/llm/test")
async def test_llm_connection(admin=Depends(_require_admin)):
    start = time.monotonic()
    result = ""
    try:
        async for delta in llm_client.stream_llm(
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            system_prompt="You are a test assistant. Reply with exactly: OK",
        ):
            result += delta

        latency_ms = int((time.monotonic() - start) * 1000)

        # stream_llm never raises — it yields error messages prefixed with "[LLM ERROR]"
        if result.startswith("[LLM ERROR]"):
            error_text = result.removeprefix("[LLM ERROR]").strip()
            return {"success": False, "latency_ms": latency_ms, "error": error_text}

        return {"success": True, "latency_ms": latency_ms, "response": result.strip()[:50]}
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {"success": False, "latency_ms": latency_ms, "error": str(exc)}
