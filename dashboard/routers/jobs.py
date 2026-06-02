"""
dashboard/routers/jobs.py
Router for Flutter Generation Jobs, cancel/download actions and files browser.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from dashboard.routers.auth import require_auth, require_role
from dashboard.database import (
    GENERATED_APPS_DIR,
    list_jobs,
    get_job,
    phase_status,
    list_job_phases,
    list_phase_attempts,
    _upsert_job,
    slugify,
    _connect,
)
from dashboard.queue_manager import (
    _enqueue_thread,
    _enqueue_rq,
    QUEUE_BACKEND,
)

router = APIRouter()


class GenerateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)

    # New modular fields
    project_type: str | None = None
    targets: list[str] | None = None
    stack: dict[str, str] | None = None

    # Legacy fields
    platform: str = "android,ios"
    style: str = "modern"
    backend: str = "none"

    features: str | list[str] = ""
    slug: str = ""


@router.get("")
def get_all_jobs(_auth: dict = Depends(require_auth)) -> list[dict[str, Any]]:
    return list_jobs()


@router.get("/{slug}")
def get_single_job(slug: str, _auth: dict = Depends(require_auth)) -> dict[str, Any]:
    job = get_job(slug)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{slug}/phases")
def get_job_phases(
    slug: str,
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list_job_phases(slug)


@router.get("/{slug}/phase-status")
def get_job_phase_status(
    slug: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, str]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return phase_status(slug)


@router.get("/{slug}/phase-attempts")
def get_job_phase_attempts(
    slug: str,
    phase: str | None = None,
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list_phase_attempts(slug, phase)


@router.delete("/{slug}")
def delete_single_job(
    slug: str,
    purge: bool = Query(False),
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM jobs WHERE slug = ?", (slug,))
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404, detail=f"Job '{slug}' không tồn tại"
            )
    purged_path = None
    if purge:
        app_dir = GENERATED_APPS_DIR / slug
        if app_dir.exists():
            shutil.rmtree(app_dir, ignore_errors=True)
            purged_path = str(app_dir)
    return {"deleted": slug, "purged": purge, "purged_path": purged_path}


@router.post("/{slug}/cancel")
def cancel_single_job(
    slug: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    from dashboard.database import request_job_cancellation, get_job
    
    existing = get_job(slug)
    if existing is None:
        raise HTTPException(
            status_code=404, detail=f"Job '{slug}' không tồn tại"
        )
        
    success = request_job_cancellation(slug)
    if not success:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Job '{slug}' đang ở trạng thái '{existing['status']}' "
                "— không thể huỷ (chỉ queued/running mới huỷ được)"
            ),
        )
    return {
        "slug": slug,
        "status": "cancel_requested",
        "cancel_requested": True,
    }


@router.post("", status_code=202)
def create_generation_job(payload: GenerateRequest, _auth: dict = Depends(require_auth)) -> dict[str, Any]:
    from factory_core.request_adapter import normalize_factory_request

    raw_payload = payload.model_dump()
    factory_request = normalize_factory_request(raw_payload)

    slug = factory_request.slug or slugify(factory_request.name)
    factory_request.slug = slug

    features = factory_request.features
    if not features:
        features = ["todo", "dashboard", "settings"]
        factory_request.features = features

    app_dir = GENERATED_APPS_DIR / slug

    _upsert_job(
        slug=slug,
        name=factory_request.name,
        description=factory_request.description,
        status="queued",
        features=features,
        app_dir=app_dir,
    )

    job_payload = {
        "name": factory_request.name,
        "description": factory_request.description,
        "project_type": factory_request.project_type,
        "targets": factory_request.targets,
        "stack": factory_request.stack,
        "features": factory_request.features,
        "slug": slug,

        # Keep legacy compatibility
        "platform": raw_payload.get("platform", "android,ios"),
        "style": raw_payload.get("style", "modern"),
        "backend": raw_payload.get("backend", "none"),
    }

    if QUEUE_BACKEND == "rq":
        try:
            _enqueue_rq(job_payload, slug)
        except Exception as error:
            _upsert_job(
                slug=slug,
                name=factory_request.name,
                description=factory_request.description,
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


@router.get("/{slug}/logs")
def get_job_logs_endpoint(
    slug: str,
    phase: str | None = Query(None),
    level: str | None = Query(None),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    from dashboard.services.job_log_service import tail_job_logs
    return tail_job_logs(slug, phase=phase, level=level)


@router.get("/{slug}/download")
def download_job_source(
    slug: str,
    _auth: dict = Depends(require_auth),
):
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
def get_job_code_tree(
    slug: str,
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    app_dir = GENERATED_APPS_DIR / slug
    if not app_dir.exists():
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    result = []
    allowed_roots = ["source", "docs"]
    for root_dir_name in allowed_roots:
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


@router.get("/{slug}/code/file")
def get_job_code_file(
    slug: str,
    path: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    app_dir = GENERATED_APPS_DIR / slug
    if not app_dir.exists():
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Whitelist path check
    parts = Path(path).parts
    if not parts or parts[0] not in ["source", "docs"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only source/ and docs/ files are permitted."
        )
    
    # Safety check: prevent directory traversal
    try:
        target_file = (app_dir / path).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")
        
    if not str(target_file).startswith(str(app_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    # Limit maximum file size (500KB)
    if target_file.stat().st_size > 500 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large (exceeds 500KB limit)"
        )
        
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
