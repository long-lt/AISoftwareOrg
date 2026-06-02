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
)
from dashboard.services.phase_service import cancel_phase, fail_phase, pass_phase, start_phase
from workflows.flutter_mvp import run_flutter_mvp_pipeline

logger = logging.getLogger(__name__)
settings = AppSettings()

QUEUE_BACKEND = os.getenv("JOB_QUEUE_BACKEND", "thread").strip().lower()
REDIS_URL = settings.redis_url
RQ_QUEUE_NAME = os.getenv("RQ_QUEUE_NAME", "ai_software_factory")


def _run_flutter_job(payload: dict[str, Any], slug: str) -> None:
    features = payload["features"]
    app_dir = GENERATED_APPS_DIR / slug
    docs_dir = app_dir / "docs"
    source_dir = app_dir / "source"
    brief_phase_started = False
    brief_phase_completed = False

    try:
        if is_cancel_requested(slug):
            raise JobCancelledError("Job was cancelled before start")

        _upsert_job(
            slug=slug,
            name=payload["name"],
            description=payload["description"],
            status="running",
            features=features,
            app_dir=app_dir,
        )

        # Setup Workspace directories
        docs_dir.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)

        if is_cancel_requested(slug):
            raise JobCancelledError("Job was cancelled")

        start_phase(slug, "01_create_brief")
        brief_phase_started = True
        app_brief = f"""# App Brief

## Thông Tin Chung
- Tên app: {payload["name"]}
- Slug: `{slug}`
- Platform: {payload.get("platform", "android,ios")}
- Style UI: {payload.get("style", "modern")}
- Backend: {payload.get("backend", "none")}
- Ngày tạo: {datetime.now().isoformat()}

## Mô Tả
{payload["description"]}

## Tính Năng Chính
"""
        for feature in features:
            app_brief += f"- {feature}\n"

        (docs_dir / "app_brief.md").write_text(app_brief, encoding="utf-8")
        (docs_dir / "input.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (docs_dir / "project_context.md").write_text(
            f"""# Project Context

## Product

- Name: {payload["name"]}
- Slug: `{slug}`
- Backend: {payload.get("backend", "none")}

## Description

{payload["description"]}
""",
            encoding="utf-8",
        )
        (docs_dir / "initial_constraints.md").write_text(
            f"""# Initial Constraints

- Platform: {payload.get("platform", "android,ios")}
- UI style: {payload.get("style", "modern")}
- Backend: {payload.get("backend", "none")}
- Features: {", ".join(features)}
""",
            encoding="utf-8",
        )
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
        brief_phase_completed = True
        
        # Execute the 12-Phase Pipeline
        if is_cancel_requested(slug):
            raise JobCancelledError("Job was cancelled")
        result = run_flutter_mvp_pipeline(payload, app_dir)

        _upsert_job(
            slug=slug,
            name=payload["name"],
            description=payload["description"],
            status="succeeded",
            features=features,
            app_dir=app_dir,
            export_path=result.export_path,
            error=None,
        )
    except JobCancelledError as error:
        if brief_phase_started and not brief_phase_completed:
            cancel_phase(slug, "01_create_brief", str(error))
        _upsert_job(
            slug=slug,
            name=payload["name"],
            description=payload["description"],
            status="cancelled",
            features=features,
            app_dir=app_dir,
            error=str(error),
        )
    except Exception as error:
        if brief_phase_started and not brief_phase_completed:
            try:
                fail_phase(slug, "01_create_brief", str(error))
            except Exception:
                pass
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
