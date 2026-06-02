from __future__ import annotations

from pathlib import Path
from typing import Any

from dashboard.database import (
    finish_phase as _finish_phase,
    list_job_phases,
    start_phase as _start_phase,
)
from dashboard.services.job_log_service import write_job_log
from workflows.phase_registry import get_phase_contract


def _normalize_outputs(output_files: list[str | Path] | tuple[str | Path, ...] | None) -> list[str]:
    return [str(path) for path in (output_files or [])]


def get_phase_list(job_slug: str) -> list[dict[str, Any]]:
    return list_job_phases(job_slug)


def start_phase(job_slug: str, phase: str) -> None:
    contract = get_phase_contract(phase)
    _start_phase(job_slug, contract.id)
    write_job_log(job_slug, contract.id, "info", f"Started {contract.id}")


def pass_phase(
    job_slug: str,
    phase: str,
    *,
    output_files: list[str | Path] | tuple[str | Path, ...] | None = None,
    logs_path: str | Path | None = None,
) -> None:
    contract = get_phase_contract(phase)
    outputs = _normalize_outputs(output_files)
    _finish_phase(
        job_slug,
        contract.id,
        "passed",
        output_files=outputs,
        logs_path=str(logs_path) if logs_path is not None else None,
    )
    write_job_log(job_slug, contract.id, "info", f"Passed {contract.id}")


def fail_phase(
    job_slug: str,
    phase: str,
    error: str,
    *,
    output_files: list[str | Path] | tuple[str | Path, ...] | None = None,
    logs_path: str | Path | None = None,
) -> None:
    contract = get_phase_contract(phase)
    outputs = _normalize_outputs(output_files)
    _finish_phase(
        job_slug,
        contract.id,
        "failed",
        error=error,
        output_files=outputs,
        logs_path=str(logs_path) if logs_path is not None else None,
    )
    write_job_log(job_slug, contract.id, "error", error)


def skip_phase(job_slug: str, phase: str, reason: str = "") -> None:
    contract = get_phase_contract(phase)
    _finish_phase(job_slug, contract.id, "skipped", error=reason or None)
    write_job_log(job_slug, contract.id, "warning", reason or f"Skipped {contract.id}")


def cancel_phase(job_slug: str, phase: str, reason: str = "Job was cancelled") -> None:
    contract = get_phase_contract(phase)
    _finish_phase(job_slug, contract.id, "cancelled", error=reason)
    write_job_log(job_slug, contract.id, "warning", reason)
