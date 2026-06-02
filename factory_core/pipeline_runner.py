from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from dashboard.database import (
    finish_phase,
    is_cancel_requested,
    write_job_log,
    start_phase,
)

def log_job(slug: str, level: str, message: str, phase: str | None = None) -> None:
    try:
        write_job_log(slug, phase=phase, level=level, message=message)
    except Exception:
        pass
from factory_core.module_executor import execute_module_step
from factory_core.pipeline_builder import PipelineBuilder
from factory_core.types import FactoryRequest, PipelinePlan


class ModularPipelineCancelled(RuntimeError):
    pass


class ModularPipelineError(RuntimeError):
    pass


def _relative_paths(paths: list[Path], app_dir: Path) -> list[str]:
    result: list[str] = []
    for path in paths:
        try:
            result.append(str(path.relative_to(app_dir)))
        except ValueError:
            result.append(str(path))
    return result


def _should_include_export_file(path: Path) -> bool:
    denied_parts = {
        ".git",
        ".dart_tool",
        "build",
        "node_modules",
        "__pycache__",
        ".idea",
        ".vscode",
    }
    denied_names = {
        ".env",
        ".env.local",
        ".env.production",
        ".DS_Store",
        "Thumbs.db",
    }

    if any(part in denied_parts for part in path.parts):
        return False

    if any(part in denied_names for part in path.parts):
        return False

    if path.suffix.lower() in {".log", ".key", ".pem", ".sqlite", ".sqlite3", ".db"}:
        return False

    return True


def export_modular_project_archive(request: FactoryRequest, app_dir: Path) -> Path:
    exports_dir = app_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    slug = request.slug or request.name.lower().replace(" ", "-")
    archive_path = exports_dir / f"{slug}_source.zip"

    include_roots = ["source", "docs"]

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for root_name in include_roots:
            root = app_dir / root_name
            if not root.exists():
                continue

            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue

                relative = path.relative_to(app_dir)
                if _should_include_export_file(relative):
                    archive.write(path, relative)

        for root_file_name in ["README.md", ".env.example"]:
            root_file = app_dir / root_file_name
            if root_file.exists() and _should_include_export_file(Path(root_file_name)):
                archive.write(root_file, root_file_name)

    return archive_path


def run_modular_pipeline(
    request: FactoryRequest,
    app_dir: Path,
    *,
    plan: PipelinePlan | None = None,
) -> dict[str, Any]:
    app_dir.mkdir(parents=True, exist_ok=True)

    if not request.slug:
        request.slug = request.name.lower().replace(" ", "-")

    pipeline_plan = plan or PipelineBuilder().build(request)

    plan_path = app_dir / "docs" / "pipeline_plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        __import__("json").dumps(pipeline_plan.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    log_job(request.slug, "info", "Starting modular pipeline", phase=None)

    written_paths: list[Path] = [plan_path]

    for step in pipeline_plan.steps:
        if is_cancel_requested(request.slug):
            finish_phase(request.slug, step.phase_id, "cancelled", error="Job cancelled by user")
            raise ModularPipelineCancelled(f"Job '{request.slug}' was cancelled")

        start_phase(request.slug, step.phase_id)
        log_job(request.slug, "info", f"Running module {step.module_id}", phase=step.phase_id)

        try:
            step_paths = execute_module_step(request, step, app_dir)
            written_paths.extend(step_paths)

            finish_phase(
                request.slug,
                step.phase_id,
                "passed",
                output_files=_relative_paths(step_paths, app_dir),
            )

            log_job(request.slug, "info", f"Module {step.module_id} passed", phase=step.phase_id)

        except Exception as exc:
            finish_phase(
                request.slug,
                step.phase_id,
                "failed",
                error=str(exc),
            )
            log_job(request.slug, "error", f"Module {step.module_id} failed: {exc}", phase=step.phase_id)
            raise ModularPipelineError(str(exc)) from exc

    archive_path = export_modular_project_archive(request, app_dir)

    return {
        "written_paths": [str(path) for path in written_paths],
        "export_path": str(archive_path),
        "pipeline_plan": pipeline_plan.to_dict(),
    }
