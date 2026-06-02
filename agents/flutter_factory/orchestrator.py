from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

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


@dataclass(frozen=True)
class PipelineResult:
    written_paths: list[Path]
    export_path: Path | None = None


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
    rules_path = Path(__file__).resolve().parents[1] / "config" / "rules.yaml"
    if not rules_path.exists():
        return 2
    text = rules_path.read_text(encoding="utf-8")
    match = re.search(r"max_repair_attempts:\s*(\d+)", text)
    if not match:
        return 2
    return max(0, int(match.group(1)))


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

    # Flutter web build — chỉ chạy 1 lần sau khi repair loop kết thúc
    written_paths.extend(run_qa_checks(app_input, docs_dir, source_dir, include_release_build=True))
    events.append(
        {
            "attempt": "final",
            "phase": "release_build",
            "result": _read_status(docs_dir / "production_qa_report.md"),
            "detail": "Flutter web release build after repair loop.",
        }
    )

    written_paths.extend(run_runtime_verification(app_input, docs_dir, source_dir))
    events.append(
        {
            "attempt": "final",
            "phase": "runtime",
            "result": _read_status(docs_dir / "runtime_report.md"),
            "detail": "Runtime smoke after repair loop.",
        }
    )
    written_paths.extend(
        write_security_documents(app_input, docs_dir, source_dir, source_dir.parent / "backend")
    )
    events.append(
        {
            "attempt": "final",
            "phase": "security",
            "result": _read_status(docs_dir / "security_report.md"),
            "detail": "Security/Release gate after runtime.",
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
    }
    return not any(part in excluded_parts for part in path.parts)


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
""",
        encoding="utf-8",
    )

    return [archive_path, report_path]


def run_full_pipeline(app_input: dict[str, Any], app_dir: Path) -> PipelineResult:
    docs_dir = app_dir / "docs"
    source_dir = app_dir / "source"
    backend_dir = app_dir / "backend"
    written_paths: list[Path] = []

    written_paths.extend(write_ba_documents(app_input, docs_dir))
    written_paths.extend(write_backend_source(app_input, docs_dir, backend_dir))
    written_paths.extend(write_architect_documents(app_input, docs_dir))
    written_paths.extend(write_uiux_documents(app_input, docs_dir))
    written_paths.extend(write_flutter_source(app_input, docs_dir, source_dir))
    written_paths.extend(
        _run_repair_loop(
            app_input,
            docs_dir,
            source_dir,
            max_attempts=_configured_max_repair_attempts(),
        )
    )
    written_paths.extend(write_review_documents(app_input, docs_dir, source_dir))

    gate_error = _pipeline_gate_error(docs_dir)
    if gate_error:
        raise RuntimeError(gate_error)

    export_paths = export_source_archive(app_input, app_dir)
    written_paths.extend(export_paths)

    return PipelineResult(written_paths=written_paths, export_path=export_paths[0])
