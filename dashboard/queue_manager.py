"""
dashboard/queue_manager.py
Job Queue Management (Thread-based & Redis Queue) and Worker Runner.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import AppSettings
from agents.flutter_factory.orchestrator import JobCancelledError
from dashboard.database import (
    GENERATED_APPS_DIR,
    _upsert_job,
    is_cancel_requested,
    initialize_job_phases,
)
from dashboard.services.phase_service import cancel_phase, fail_phase, pass_phase, start_phase
from workflows.flutter_mvp import run_flutter_mvp_pipeline
from factory_core.request_adapter import normalize_factory_request
from factory_core.pipeline_runner import (
    ModularPipelineCancelled,
    run_modular_pipeline,
)

logger = logging.getLogger(__name__)
settings = AppSettings()

QUEUE_BACKEND = os.getenv("JOB_QUEUE_BACKEND", "thread").strip().lower()
REDIS_URL = settings.redis_url
RQ_QUEUE_NAME = os.getenv("RQ_QUEUE_NAME", "flutter_ai_factory")
FACTORY_PIPELINE_MODE = os.getenv("FACTORY_PIPELINE_MODE", "modular").strip().lower()


def build_app_input(
    name: str,
    description: str,
    platform: str,
    style: str,
    backend: str,
    features: list[str],
    slug: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "platform": platform,
        "style": style,
        "backend": backend,
        "features": features,
        "slug": slug,
    }


def write_app_brief(app_input: dict[str, Any], docs_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    app_brief = f"""# App Brief

## Thông Tin Chung
- Tên app: {app_input["name"]}
- Slug: `{app_input["slug"]}`
- Platform: {app_input["platform"]}
- Style UI: {app_input["style"]}
- Backend: {app_input["backend"]}
- Ngày tạo: {datetime.now().isoformat()}

## Mô Tả
{app_input["description"]}

## Tính Năng Chính
"""
    for feature in app_input["features"]:
        app_brief += f"- {feature}\n"

    (docs_dir / "app_brief.md").write_text(app_brief, encoding="utf-8")
    
    (docs_dir / "input.json").write_text(
        json.dumps(app_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    
    (docs_dir / "project_context.md").write_text(
        f"""# Project Context

## Product

- Name: {app_input["name"]}
- Slug: `{app_input["slug"]}`
- Backend: {app_input["backend"]}

## Description

{app_input["description"]}
""",
        encoding="utf-8",
    )
    
    (docs_dir / "initial_constraints.md").write_text(
        f"""# Initial Constraints

- Platform: {app_input["platform"]}
- UI style: {app_input["style"]}
- Backend: {app_input["backend"]}
- Features: {", ".join(app_input["features"])}
""",
        encoding="utf-8",
    )


def _run_flutter_job(payload: dict[str, Any], slug: str) -> None:
    features = payload["features"]
    app_dir = GENERATED_APPS_DIR / slug
    docs_dir = app_dir / "docs"
    source_dir = app_dir / "source"
    brief_phase_started = False

    try:
        if is_cancel_requested(slug):
            raise JobCancelledError(f"Job '{slug}' was cancelled before start")

        _upsert_job(
            slug=slug,
            name=payload["name"],
            description=payload["description"],
            features=features,
            status="running",
            app_dir=app_dir,
        )

        app_dir.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)

        initialize_job_phases(slug)

        if is_cancel_requested(slug):
            raise JobCancelledError(f"Job '{slug}' was cancelled before brief generation")

        start_phase(slug, "01_create_brief")
        brief_phase_started = True

        app_input = build_app_input(
            name=payload["name"],
            description=payload["description"],
            platform=payload.get("platform", "android,ios"),
            style=payload.get("style", "modern"),
            backend=payload.get("backend", "none"),
            features=features,
            slug=slug,
        )

        write_app_brief(app_input, docs_dir)

        pass_phase(
            slug,
            "01_create_brief",
            output_files=[
                "docs/input.json",
                "docs/app_brief.md",
                "docs/project_context.md",
                "docs/initial_constraints.md",
            ],
        )

        if is_cancel_requested(slug):
            raise JobCancelledError(f"Job '{slug}' was cancelled before pipeline execution")

        if FACTORY_PIPELINE_MODE == "modular":
            factory_request = normalize_factory_request(payload)
            factory_request.slug = slug

            result = run_modular_pipeline(factory_request, app_dir)

            export_path = result["export_path"]

        else:
            result = run_flutter_mvp_pipeline(payload, app_dir)

            export_path = result.export_path

        if is_cancel_requested(slug):
            raise JobCancelledError(f"Job '{slug}' was cancelled before completion")

        _upsert_job(
            slug=slug,
            name=payload["name"],
            description=payload["description"],
            features=features,
            status="succeeded",
            app_dir=app_dir,
            export_path=export_path,
        )

    except (JobCancelledError, ModularPipelineCancelled) as error:
        if brief_phase_started:
            try:
                finish_phase(slug, "01_create_brief", "cancelled", error=str(error))
            except Exception:
                pass

        _upsert_job(
            slug=slug,
            name=payload["name"],
            description=payload["description"],
            features=features,
            status="cancelled",
            app_dir=app_dir,
            error=str(error),
            cancel_requested=False,
        )

    except Exception as error:
        _upsert_job(
            slug=slug,
            name=payload["name"],
            description=payload["description"],
            status="failed",
            features=features,
            app_dir=app_dir,
            error=f"{error}\n{traceback.format_exc()}",
        )


def _enqueue_thread(payload: dict[str, Any], slug: str) -> None:
    thread = threading.Thread(
        target=_run_flutter_job,
        args=(payload, slug),
        daemon=True,
    )
    thread.start()


def _enqueue_rq(payload: dict[str, Any], slug: str) -> str:
    try:
        from redis import Redis
        from rq import Queue
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "RQ backend requires `redis` and `rq` packages."
        ) from error

    redis_connection = Redis.from_url(REDIS_URL)
    queue = Queue(RQ_QUEUE_NAME, connection=redis_connection)
    job = queue.enqueue(
        "dashboard.queue_manager.run_generation_job_payload",
        payload,
        slug,
        job_timeout="30m",
        result_ttl=86400,
        failure_ttl=86400,
    )
    return job.id


def run_generation_job_payload(payload: dict[str, Any], slug: str) -> None:
    _run_flutter_job(payload, slug)
