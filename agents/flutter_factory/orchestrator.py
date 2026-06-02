from __future__ import annotations

import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from config.settings import AppSettings
from agents.flutter_factory.architect_agent import write_architect_documents
from agents.flutter_factory.ba_agent import write_ba_documents
from agents.flutter_factory.backend_agent import write_backend_source
from agents.flutter_factory.dev_agent import write_flutter_source
from agents.flutter_factory.qa_agent import run_qa_checks
from agents.flutter_factory.refactor_agent import run_refactor
from agents.flutter_factory.reviewer_agent import write_review_documents
from agents.flutter_factory.runtime_agent import run_runtime_verification
from agents.flutter_factory.security_agent import write_security_documents
from agents.flutter_factory.uiux_agent import write_uiux_documents
from dashboard.database import get_job, is_cancel_requested
from dashboard.services.phase_service import (
    cancel_phase,
    fail_phase,
    pass_phase,
    start_phase,
)


@dataclass(frozen=True)
class PipelineResult:
    written_paths: list[Path]
    export_path: Path | None = None


class JobCancelledError(RuntimeError):
    """Raised when a queued/running generation job has been cancelled."""


def _job_slug(app_input: dict[str, Any]) -> str:
    return str(app_input.get("slug") or "").strip()


def _can_record_job(slug: str) -> bool:
    return bool(slug and get_job(slug) is not None)


def _check_cancellation(slug: str) -> None:
    if slug and is_cancel_requested(slug):
        raise JobCancelledError(f"Job '{slug}' was cancelled")


def _relative_outputs(paths: list[Path], app_dir: Path) -> list[str]:
    outputs: list[str] = []
    for path in paths:
        try:
            outputs.append(str(path.relative_to(app_dir)))
        except ValueError:
            outputs.append(str(path))
    return outputs


def _run_recorded_phase(
    app_input: dict[str, Any],
    app_dir: Path,
    phase: str,
    operation: Callable[[], list[Path]],
) -> list[Path]:
    slug = _job_slug(app_input)
    should_record = _can_record_job(slug)
    _check_cancellation(slug)
    if should_record:
        start_phase(slug, phase)
    try:
        paths = operation()
        _check_cancellation(slug)
    except JobCancelledError as exc:
        if should_record:
            cancel_phase(slug, phase, str(exc))
        raise
    except Exception as exc:
        if should_record:
            fail_phase(slug, phase, str(exc))
        raise
    if should_record:
        pass_phase(slug, phase, output_files=_relative_outputs(paths, app_dir))
    return paths


def _read_status(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith("- Status:"):
            return stripped.removeprefix("- Status:").strip()
        if stripped.startswith("Status:"):
            return stripped.removeprefix("Status:").strip()
    return "UNKNOWN"


def _configured_max_repair_attempts() -> int:
    return max(0, AppSettings().max_repair_attempts)


def _write_repair_history(
    app_input: dict[str, Any],
    docs_dir: Path,
    events: list[dict[str, str]],
    max_attempts: int,
) -> Path:
    status = "PASS" if not any(event["result"] == "FAIL" for event in events[-3:]) else "FAIL"
    event_text = "\n".join(
        f"- Attempt {event['attempt']} `{event['phase']}`: {event['result']} - {event['detail']}"
        for event in events
    )
    if not event_text:
        event_text = "- Không cần repair attempt."
    report = f"""# Repair History: {app_input["name"]}

## Tổng Quan

- Status: {status}
- Max repair attempts: {max_attempts}
- Generated at: {datetime.now().isoformat(timespec="seconds")}

## Attempts

{event_text}
"""
    path = docs_dir / "repair_history.md"
    path.write_text(report, encoding="utf-8")
    return path


def _run_repair_loop(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
    max_attempts: int,
) -> list[Path]:
    """Run QA + refactor loop until QA passes or attempts exhausted.
    Returns paths from QA checks and refactor runs (excluding runtime/security)."""
    written_paths: list[Path] = []
    events: list[dict[str, str]] = []

    for attempt in range(max_attempts + 1):
        written_paths.extend(run_qa_checks(app_input, docs_dir, source_dir, include_release_build=False))
        qa_status = _read_status(docs_dir / "test_report.md")
        production_qa_status = _read_status(docs_dir / "production_qa_report.md")
        qa_passed = qa_status == "PASS" and production_qa_status == "PASS"
        events.append(
            {
                "attempt": str(attempt),
                "phase": "qa",
                "result": "PASS" if qa_passed else "FAIL",
                "detail": f"test_report={qa_status}, production_qa_report={production_qa_status}",
            }
        )
        if qa_passed:
            break
        if attempt >= max_attempts:
            break
        written_paths.extend(run_refactor(app_input, docs_dir, source_dir))
        refactor_status = _read_status(docs_dir / "refactor_report.md")
        events.append(
            {
                "attempt": str(attempt + 1),
                "phase": "refactor",
                "result": refactor_status,
                "detail": "Refactor Agent ran from QA bug list.",
            }
        )

    if not (docs_dir / "refactor_report.md").exists():
        written_paths.extend(run_refactor(app_input, docs_dir, source_dir))
        events.append(
            {
                "attempt": "final",
                "phase": "refactor",
                "result": _read_status(docs_dir / "refactor_report.md"),
                "detail": "Final formatting and analyze verification.",
            }
        )

    written_paths.append(_write_repair_history(app_input, docs_dir, events, max_attempts))
    return written_paths


def _pipeline_gate_error(docs_dir: Path) -> str | None:
    checks = {
        "qa": _read_status(docs_dir / "test_report.md"),
        "production_qa": _read_status(docs_dir / "production_qa_report.md"),
        "repair": _read_status(docs_dir / "repair_history.md"),
        "refactor": _read_status(docs_dir / "refactor_report.md"),
        "runtime": _read_status(docs_dir / "runtime_report.md"),
        "security": _read_status(docs_dir / "security_report.md"),
        "reviewer": _read_status(docs_dir / "final_review.md"),
    }
    passed = (
        checks["qa"] == "PASS"
        and checks["production_qa"] == "PASS"
        and checks["repair"] == "PASS"
        and checks["refactor"] == "PASS"
        and checks["runtime"] == "PASS"
        and checks["security"] == "PASS"
        and checks["reviewer"] == "READY_FOR_MVP_HANDOFF"
    )
    if passed:
        return None
    return "Quality gates failed after repair loop: " + ", ".join(
        f"{name}={status}" for name, status in checks.items()
    )


def _should_include_export_file(path: Path) -> bool:
    excluded_parts = {
        ".dart_tool",
        "build",
        ".idea",
        ".vscode",
        ".git",
        "node_modules",
        "__pycache__",
    }
    excluded_names = {
        ".env",
        ".env.local",
        ".env.production",
        ".DS_Store",
        "Thumbs.db",
    }
    if any(part in excluded_parts for part in path.parts):
        return False
    if any(part in excluded_names for part in path.parts):
        return False
    return path.suffix.lower() != ".log"


def export_source_archive(app_input: dict[str, Any], app_dir: Path) -> list[Path]:
    slug = str(app_input["slug"])
    source_dir = app_dir / "source"
    backend_dir = app_dir / "backend"
    docs_dir = app_dir / "docs"
    exports_dir = app_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    if not source_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy source dir: {source_dir}")

    archive_path = exports_dir / f"{slug}_source.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file() and _should_include_export_file(path.relative_to(source_dir)):
                archive.write(path, Path("source") / path.relative_to(source_dir))

        if backend_dir.exists():
            for path in sorted(backend_dir.rglob("*")):
                if path.is_file() and _should_include_export_file(path.relative_to(backend_dir)):
                    archive.write(path, Path("backend") / path.relative_to(backend_dir))

        for filename in [
            "app_brief.md",
            "requirements.md",
            "product_spec.json",
            "data_model.json",
            "user_flows.md",
            "acceptance_tests.md",
            "non_functional_requirements.md",
            "openapi.yaml",
            "database_schema.sql",
            "backend_report.md",
            "frontend_integration_report.md",
            "architecture.md",
            "design.md",
            "test_report.md",
            "production_qa_report.md",
            "refactor_report.md",
            "repair_history.md",
            "runtime_report.md",
            "security_report.md",
            "deployment_plan.md",
            "env_contract.md",
            "production_release_checklist.md",
            "final_review.md",
            "release_checklist.md",
        ]:
            doc_path = docs_dir / filename
            if doc_path.exists():
                archive.write(doc_path, Path("docs") / filename)

        for filename in ["README.md", ".env.example"]:
            root_file = app_dir / filename
            if root_file.exists() and _should_include_export_file(Path(filename)):
                archive.write(root_file, filename)

    report_path = docs_dir / "export_report.md"
    report_path.write_text(
        f"""# Export Report: {app_input["name"]}

## Output

- Archive: `{archive_path}`
- Created at: {datetime.now().isoformat(timespec="seconds")}

## Included

- Flutter source under `source/`
- Backend source under `backend/` nếu đã sinh
- Key handoff docs under `docs/`

## Excluded

- `.dart_tool/`
- `build/`
- IDE metadata
- Git metadata
- `.env` secrets
- `*.log`
""",
        encoding="utf-8",
    )

    return [archive_path, report_path]


def run_full_pipeline(app_input: dict[str, Any], app_dir: Path) -> PipelineResult:
    docs_dir = app_dir / "docs"
    source_dir = app_dir / "source"
    backend_dir = app_dir / "backend"
    written_paths: list[Path] = []

    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "02_business_analysis",
            lambda: write_ba_documents(app_input, docs_dir),
        )
    )
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "03_backend_design",
            lambda: write_backend_source(app_input, docs_dir, backend_dir),
        )
    )
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "04_architecture_design",
            lambda: write_architect_documents(app_input, docs_dir),
        )
    )
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "05_uiux_design",
            lambda: write_uiux_documents(app_input, docs_dir),
        )
    )
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "06_flutter_dev",
            lambda: write_flutter_source(app_input, docs_dir, source_dir),
        )
    )
    # 07: Static QA (first pass, before repair loop)
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "07_static_qa",
            lambda: run_qa_checks(app_input, docs_dir, source_dir, include_release_build=False),
        )
    )

    # 08: Repair loop (QA + refactor cycle)
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "08_refactor_repair",
            lambda: _run_repair_loop(
                app_input,
                docs_dir,
                source_dir,
                max_attempts=_configured_max_repair_attempts(),
            ),
        )
    )

    # 07b: Release build (after repair loop)
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "07_static_qa",
            lambda: run_qa_checks(app_input, docs_dir, source_dir, include_release_build=True),
        )
    )

    # 09: Runtime verification
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "09_runtime_test",
            lambda: run_runtime_verification(app_input, docs_dir, source_dir),
        )
    )

    # 10: Security audit
    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "10_security_audit",
            lambda: write_security_documents(app_input, docs_dir, source_dir, source_dir.parent / "backend"),
        )
    )

    written_paths.extend(
        _run_recorded_phase(
            app_input,
            app_dir,
            "11_release_review",
            lambda: write_review_documents(app_input, docs_dir, source_dir),
        )
    )

    gate_error = _pipeline_gate_error(docs_dir)
    if gate_error:
        raise RuntimeError(gate_error)

    export_paths = _run_recorded_phase(
        app_input,
        app_dir,
        "12_export_package",
        lambda: export_source_archive(app_input, app_dir),
    )
    written_paths.extend(export_paths)

    return PipelineResult(written_paths=written_paths, export_path=export_paths[0])
