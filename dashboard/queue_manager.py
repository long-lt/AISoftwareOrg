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
from dashboard.database import (
    GENERATED_APPS_DIR,
    _upsert_job,
    _quality_gate_status,
)
from workflows.flutter_mvp import run_flutter_mvp_pipeline

logger = logging.getLogger(__name__)
settings = AppSettings()

QUEUE_BACKEND = os.getenv("JOB_QUEUE_BACKEND", "thread").strip().lower()
REDIS_URL = settings.redis_url
RQ_QUEUE_NAME = "flutter_ai_factory"


def _run_flutter_job(payload: dict[str, Any], slug: str) -> None:
    features = payload["features"]
    app_dir = GENERATED_APPS_DIR / slug
    docs_dir = app_dir / "docs"
    source_dir = app_dir / "source"

    try:
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
        
        # Execute the 12-Phase Pipeline
        result = run_flutter_mvp_pipeline(payload, app_dir)

        quality_passed, quality_error = _quality_gate_status(app_dir)
        _upsert_job(
            slug=slug,
            name=payload["name"],
            description=payload["description"],
            status="succeeded" if quality_passed else "failed",
            features=features,
            app_dir=app_dir,
            export_path=result.export_path,
            error=quality_error,
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
