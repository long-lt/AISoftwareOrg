from __future__ import annotations

from typing import Any

from dashboard.database import list_job_logs, write_job_log as _write_job_log


def write_job_log(job_slug: str, phase: str | None, level: str, message: str) -> dict[str, Any]:
    return _write_job_log(job_slug, phase=phase, level=level, message=message)


def tail_job_logs(
    job_slug: str,
    *,
    phase: str | None = None,
    level: str | None = None,
) -> list[dict[str, Any]]:
    return list_job_logs(job_slug, phase=phase, level=level)
