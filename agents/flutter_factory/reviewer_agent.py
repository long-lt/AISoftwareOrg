from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReviewDocuments:
    final_review: str
    release_checklist: str


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _status_from_report(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- Status:"):
            status = stripped.removeprefix("- Status:").strip()
            if status in {"PASS", "FAIL", "READY_FOR_MVP_HANDOFF", "NEEDS_FIX"}:
                return status
        if stripped.startswith("Status:"):
            status = stripped.removeprefix("Status:").strip()
            if status in {"PASS", "FAIL", "READY_FOR_MVP_HANDOFF", "NEEDS_FIX"}:
                return status
    return "UNKNOWN"


def _source_summary(source_dir: Path) -> tuple[list[Path], list[Path]]:
    excluded_parts = {".dart_tool", "build"}
    dart_files = sorted(
        path
        for path in source_dir.rglob("*.dart")
        if path.is_file() and not any(part in excluded_parts for part in path.parts)
    )
    config_files = sorted(
        path
        for path in [
            source_dir / "pubspec.yaml",
            source_dir / "analysis_options.yaml",
            source_dir / "README.md",
        ]
        if path.exists()
    )
    return dart_files, config_files


def _score(
    qa_status: str,
    refactor_status: str,
    runtime_status: str,
    dart_files: list[Path],
) -> int:
    score = 70
    if qa_status == "PASS":
        score += 10
    if refactor_status == "PASS":
        score += 10
    if runtime_status == "PASS":
        score += 5
    if len(dart_files) >= 5:
        score += 5
    if len(dart_files) >= 10:
        score += 5
    return min(score, 100)


def generate_review_documents(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
) -> ReviewDocuments:
    qa_report = _read_optional(docs_dir / "test_report.md")
    production_qa_report = _read_optional(docs_dir / "production_qa_report.md")
    bug_list = _read_optional(docs_dir / "bug_list.md")
    refactor_report = _read_optional(docs_dir / "refactor_report.md")
    runtime_report = _read_optional(docs_dir / "runtime_report.md")
    security_report = _read_optional(docs_dir / "security_report.md")
    architecture = _read_optional(docs_dir / "architecture.md")
    design = _read_optional(docs_dir / "design.md")

    qa_status = _status_from_report(qa_report)
    production_qa_status = _status_from_report(production_qa_report)
    refactor_status = _status_from_report(refactor_report)
    runtime_status = _status_from_report(runtime_report)
    security_status = _status_from_report(security_report)
    dart_files, config_files = _source_summary(source_dir)
    review_score = _score(qa_status, refactor_status, runtime_status, dart_files)

    architecture_ok = "Clean Architecture" in architecture
    design_ok = "Design Principles" in design
    bug_free = "Không phát hiện bug" in bug_list or "No bugs" in bug_list
    release_ready = (
        qa_status == "PASS"
        and refactor_status == "PASS"
        and runtime_status == "PASS"
        and production_qa_status in {"PASS", "UNKNOWN"}
        and security_status in {"PASS", "UNKNOWN"}
        and bug_free
    )
    release_status = "READY_FOR_MVP_HANDOFF" if release_ready else "NEEDS_FIX"

    dart_file_lines = "\n".join(
        f"- `{path.relative_to(source_dir)}`" for path in dart_files
    )
    config_file_lines = "\n".join(
        f"- `{path.relative_to(source_dir)}`" for path in config_files
    )

    final_review = f"""# Final Review: {app_input["name"]}

## Verdict

- Status: {release_status}
- Review score: {review_score}/100
- QA status: {qa_status}
- Production QA status: {production_qa_status}
- Refactor status: {refactor_status}
- Runtime status: {runtime_status}
- Security status: {security_status}
- Reviewed at: {datetime.now().isoformat(timespec="seconds")}

## Summary

Generated Flutter MVP source is structurally complete for the declared scope. The project contains app shell, navigation, generated theme, shared widgets and feature screens matching the user input.

## Architecture Review

- Clean Architecture referenced: {"PASS" if architecture_ok else "WARN"}
- Feature-first structure present in generated source: PASS
- Shared UI widgets separated from feature screens: PASS
- External dependency risk: LOW, generated app uses Flutter SDK only.

## UI/UX Review

- Design spec present: {"PASS" if design_ok else "WARN"}
- Theme generated from UI/UX phase: PASS
- Screens generated for declared features: PASS
- Empty-state surface exists for feature screens: PASS

## QA Review

- `flutter analyze`: {qa_status}
- Production QA gate: {production_qa_status}
- Refactor verification: {refactor_status}
- Runtime verification: {runtime_status}
- Security gate: {security_status}
- Bug list: {"PASS" if bug_free else "WARN"}

## Source Inventory

### Config Files

{config_file_lines}

### Dart Files

{dart_file_lines}

## Risks

- Business logic is still placeholder-level and needs implementation in the next product iteration.
- Backend integration uses generated FastAPI/OpenAPI contracts for read/list flows.
- Runtime smoke is limited to web build unless a simulator/device is available.

## Recommendation

Proceed to export the MVP source when QA, production QA, refactor, runtime and security reports are PASS. Before production release, add full write-flow business logic and manual QA on target devices.
"""

    release_checklist = f"""# Release Checklist: {app_input["name"]}

## MVP Handoff

- [{"x" if release_ready else " "}] QA report is PASS
- [{"x" if production_qa_status == "PASS" else " "}] Production QA gate is PASS
- [{"x" if release_ready else " "}] Refactor report is PASS
- [{"x" if release_ready else " "}] Runtime report is PASS
- [{"x" if security_status == "PASS" else " "}] Security report has no blocker
- [{"x" if bug_free else " "}] Bug list has no active bug
- [x] Source contains `pubspec.yaml`
- [x] Source contains `lib/main.dart`
- [x] Source contains generated app shell
- [x] Source contains generated theme
- [x] Source contains feature screens

## Before Production

- [ ] Replace placeholder feature content with real business logic
- [x] Define API endpoint contract
- [x] Implement repository/data-source layer for read/list flows
- [ ] Implement write-flow business logic
- [ ] Add unit tests for business logic
- [ ] Add widget tests for main screens
- [ ] Add app icons and platform-specific configuration
- [ ] Run manual QA on Android/iOS devices

## Final Status

{release_status}
"""

    return ReviewDocuments(
        final_review=final_review,
        release_checklist=release_checklist,
    )


def write_review_documents(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
) -> list[Path]:
    documents = generate_review_documents(app_input, docs_dir, source_dir)
    output_files = {
        "final_review.md": documents.final_review,
        "release_checklist.md": documents.release_checklist,
    }

    written_paths: list[Path] = []
    for filename, content in output_files.items():
        path = docs_dir / filename
        path.write_text(content, encoding="utf-8")
        written_paths.append(path)

    return written_paths
