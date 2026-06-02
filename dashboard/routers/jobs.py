"""
dashboard/routers/jobs.py
Router for Flutter Generation Jobs, cancel/download actions and files browser.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from dashboard.database import (
    GENERATED_APPS_DIR,
    delete_job_record,
    list_jobs,
    get_job,
    list_job_logs,
    phase_status,
    request_job_cancellation,
    _upsert_job,
    slugify,
)
from dashboard.queue_manager import (
    _enqueue_thread,
    _enqueue_rq,
    QUEUE_BACKEND,
)

router = APIRouter()
CODE_ALLOWED_ROOTS = {"source", "docs", "backend"}
CODE_MAX_FILE_BYTES = 512_000


class GenerateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    platform: str = "android,ios"
    style: str = "modern"
    backend: str = "none"
    features: str = ""
    slug: str = ""


@router.get("")
def get_all_jobs() -> list[dict[str, Any]]:
    return list_jobs()


@router.get("/{slug}")
def get_single_job(slug: str) -> dict[str, Any]:
    job = get_job(slug)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{slug}/phases")
def get_job_phases(slug: str) -> dict[str, str]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return phase_status(slug)


@router.delete("/{slug}")
def delete_single_job(slug: str, purge: bool = Query(False)) -> dict[str, Any]:
    if not delete_job_record(slug):
        raise HTTPException(status_code=404, detail=f"Job '{slug}' không tồn tại")
    purged_path = None
    if purge:
        app_dir = GENERATED_APPS_DIR / slug
        if app_dir.exists():
            shutil.rmtree(app_dir, ignore_errors=True)
            purged_path = str(app_dir)
    return {"deleted": slug, "purged": purge, "purged_path": purged_path}


@router.post("/{slug}/cancel")
def cancel_single_job(slug: str) -> dict[str, Any]:
    if not request_job_cancellation(slug):
        existing = get_job(slug)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Job '{slug}' không tồn tại")
        raise HTTPException(
            status_code=409,
            detail=(
                f"Job '{slug}' đang ở trạng thái '{existing['status']}' "
                "— không thể huỷ (chỉ queued/running mới huỷ được)"
            ),
        )
    return {"slug": slug, "status": "cancel_requested", "cancel_requested": True}


@router.get("/{slug}/logs")
def get_job_logs(
    slug: str,
    phase: str | None = Query(default=None),
    level: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list_job_logs(slug, phase=phase, level=level)


@router.post("", status_code=202)
def create_generation_job(payload: GenerateRequest) -> dict[str, Any]:
    slug = payload.slug or slugify(payload.name)
    features = [f.strip() for f in payload.features.split(",") if f.strip()]
    if not features:
        features = ["todo", "dashboard", "settings"]

    app_dir = GENERATED_APPS_DIR / slug
    _upsert_job(
        slug=slug,
        name=payload.name,
        description=payload.description,
        status="queued",
        features=features,
        app_dir=app_dir,
    )

    job_payload = {
        "name": payload.name,
        "description": payload.description,
        "platform": payload.platform,
        "style": payload.style,
        "backend": payload.backend,
        "features": features,
        "slug": slug,
    }

    if QUEUE_BACKEND == "rq":
        try:
            _enqueue_rq(job_payload, slug)
        except Exception as error:
            _upsert_job(
                slug=slug,
                name=payload.name,
                description=payload.description,
                status="failed",
                features=features,
                app_dir=app_dir,
                error=f"Queue enqueue failed: {error}",
            )
    else:
        _enqueue_thread(job_payload, slug)

    job = get_job(slug)
    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create job")
    return job


@router.get("/{slug}/download")
def download_job_source(slug: str):
    job = get_job(slug)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    export_path = job.get("export_path")
    if not export_path or not Path(export_path).exists():
        raise HTTPException(status_code=404, detail="Source code export is not ready")
    return FileResponse(
        export_path,
        filename=Path(export_path).name,
        media_type="application/zip",
    )


@router.get("/{slug}/code/tree")
def get_job_code_tree(slug: str) -> list[dict[str, Any]]:
    app_dir = GENERATED_APPS_DIR / slug
    if not app_dir.exists():
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    result = []
    for root_dir_name in sorted(CODE_ALLOWED_ROOTS):
        target_path = app_dir / root_dir_name
        if not target_path.exists():
            continue
        for path in sorted(target_path.rglob("*")):
            # Skip hidden files/dirs, and lock files
            if any(part.startswith(".") for part in path.relative_to(app_dir).parts):
                continue
            if "pubspec.lock" in path.name:
                continue
            
            rel_path = path.relative_to(app_dir)
            is_dir = path.is_dir()
            result.append({
                "path": str(rel_path),
                "name": path.name,
                "isDir": is_dir,
                "size": path.stat().st_size if not is_dir else None
            })
    return result


def _resolve_allowed_code_file(app_dir: Path, requested_path: str) -> Path:
    try:
        base_dir = app_dir.resolve()
        target_file = (app_dir / requested_path).resolve()
        relative_path = target_file.relative_to(base_dir)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid path") from exc

    parts = relative_path.parts
    if not parts or parts[0] not in CODE_ALLOWED_ROOTS:
        raise HTTPException(status_code=403, detail="Access denied")
    if any(part.startswith(".") for part in parts):
        raise HTTPException(status_code=403, detail="Access denied")
    return target_file


@router.get("/{slug}/code/file")
def get_job_code_file(slug: str, path: str) -> dict[str, Any]:
    app_dir = GENERATED_APPS_DIR / slug
    if not app_dir.exists():
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    target_file = _resolve_allowed_code_file(app_dir, path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if target_file.stat().st_size > CODE_MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File is too large to read")

    try:
        content = target_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary files are not readable as text")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "path": path,
        "content": content
    }
