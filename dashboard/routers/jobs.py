"""
dashboard/routers/jobs.py
Router for Flutter Generation Jobs, cancel/download actions and files browser.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from dashboard.database import (
    GENERATED_APPS_DIR,
    list_jobs,
    get_job,
    phase_status,
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
def cancel_single_job(slug: str) -> dict[str, Any]:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE jobs SET status = 'cancelled', updated_at = ? "
            "WHERE slug = ? AND status IN ('queued', 'running')",
            (datetime.now(timezone.utc).isoformat(), slug),
        )
        if cur.rowcount == 0:
            existing = get_job(slug)
            if existing is None:
                raise HTTPException(
                    status_code=404, detail=f"Job '{slug}' không tồn tại"
                )
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Job '{slug}' đang ở trạng thái '{existing['status']}' "
                    "— không thể huỷ (chỉ queued/running mới huỷ được)"
                ),
            )
    return {"slug": slug, "status": "cancelled"}


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
def get_job_code_file(slug: str, path: str) -> dict[str, Any]:
    app_dir = GENERATED_APPS_DIR / slug
    if not app_dir.exists():
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Safety check: prevent directory traversal
    try:
        target_file = (app_dir / path).resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")
        
    if not str(target_file).startswith(str(app_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
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
