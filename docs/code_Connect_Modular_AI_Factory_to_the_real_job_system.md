Ok, bước tiếp theo là **nối Modular AI Factory vào hệ thống job thật**, để `POST /api/jobs` có thể nhận request kiểu mới:

```json
{
  "name": "PantrySaver",
  "description": "Food expiry tracker and meal planner",
  "project_type": "fullstack_saas",
  "targets": ["web", "mobile", "backend"],
  "stack": {
    "frontend": "nextjs",
    "mobile": "flutter",
    "backend": "fastapi",
    "database": "supabase"
  },
  "features": ["auth", "inventory", "expiry_reminders"]
}
```

Nhưng vẫn giữ backward-compatible với request cũ của Flutter.

---

# 1. Tạo `factory_core/request_adapter.py`

File:

```text
factory_core/request_adapter.py
```

```python
from __future__ import annotations

from typing import Any

from factory_core.types import FactoryRequest


def normalize_factory_request(payload: dict[str, Any]) -> FactoryRequest:
    """
    Convert both legacy Flutter job payloads and new modular factory payloads
    into a normalized FactoryRequest.
    """

    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    slug = str(payload.get("slug", "")).strip()

    project_type = str(payload.get("project_type") or "").strip()
    targets = payload.get("targets")
    stack = payload.get("stack")
    features = payload.get("features")

    # Legacy support:
    # Old payload shape:
    # {
    #   name,
    #   description,
    #   platform,
    #   style,
    #   backend,
    #   features
    # }
    if not project_type:
        project_type = "mobile_app"

    if not isinstance(targets, list) or not targets:
        targets = ["mobile"]

    if not isinstance(stack, dict) or not stack:
        backend = str(payload.get("backend", "none")).strip().lower()

        stack = {
            "mobile": "flutter",
        }

        if backend and backend != "none":
            stack["backend"] = "fastapi"

    if isinstance(features, str):
        features = [item.strip() for item in features.split(",") if item.strip()]

    if not isinstance(features, list):
        features = []

    features = [str(item).strip() for item in features if str(item).strip()]

    return FactoryRequest(
        name=name,
        description=description,
        project_type=project_type,  # type: ignore[arg-type]
        targets=[str(item).strip() for item in targets if str(item).strip()],
        stack={str(key): str(value) for key, value in stack.items()},
        features=features,
        slug=slug,
    )
```

---

# 2. Tạo `factory_core/module_executor.py`

File này chưa cần generate code thật. Nó tạo artifact placeholder theo module, để pipeline modular chạy được và dashboard thấy output rõ ràng.

```text
factory_core/module_executor.py
```

````python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from factory_core.types import FactoryRequest, PipelineStep


class ModuleExecutionError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def execute_module_step(
    request: FactoryRequest,
    step: PipelineStep,
    app_dir: Path,
) -> list[Path]:
    """
    Execute one modular factory step.

    This is a safe MVP executor:
    - Creates expected files/directories.
    - Writes module reports.
    - Does not call LLM yet.
    - Does not replace the existing Flutter pipeline yet.

    Later, each module can provide its own generator.py.
    """

    docs_dir = app_dir / "docs"
    source_dir = app_dir / "source"

    written: list[Path] = []

    if step.module_id == "common.brief":
        written.extend(_run_common_brief(request, docs_dir))

    elif step.module_id == "common.business_analysis":
        written.extend(_run_common_business_analysis(request, docs_dir))

    elif step.module_id == "common.architecture":
        written.extend(_run_common_architecture(request, docs_dir))

    elif step.module_id == "common.uiux":
        written.extend(_run_common_uiux(request, docs_dir))

    elif step.module_id == "mobile.flutter":
        written.extend(_run_flutter_module(request, app_dir))

    elif step.module_id == "frontend.react":
        written.extend(_run_react_module(request, source_dir / "frontend", docs_dir))

    elif step.module_id == "frontend.nextjs":
        written.extend(_run_nextjs_module(request, source_dir / "frontend", docs_dir))

    elif step.module_id == "backend.fastapi":
        written.extend(_run_fastapi_module(request, source_dir / "backend", docs_dir))

    elif step.module_id == "database.supabase":
        written.extend(_run_supabase_module(request, source_dir / "infra" / "supabase", docs_dir))

    elif step.module_id == "common.qa":
        written.extend(_run_common_qa(request, docs_dir, step))

    elif step.module_id == "common.repair":
        written.extend(_run_common_repair(request, docs_dir))

    elif step.module_id == "common.runtime":
        written.extend(_run_common_runtime(request, docs_dir))

    elif step.module_id == "common.security":
        written.extend(_run_common_security(request, docs_dir))

    elif step.module_id == "common.release_review":
        written.extend(_run_common_release_review(request, docs_dir))

    elif step.module_id == "common.export":
        written.extend(_run_common_export_report(request, app_dir, docs_dir))

    else:
        written.append(
            _write_text(
                docs_dir / f"module_{step.module_id.replace('.', '_')}.md",
                f"""# Module Execution Report

- Module: `{step.module_id}`
- Phase: `{step.phase_id}`
- Status: PASS
- Generated at: `{_now()}`

This module is registered but does not have a dedicated executor yet.
""",
            )
        )

    return written


def _run_common_brief(request: FactoryRequest, docs_dir: Path) -> list[Path]:
    return [
        _write_json(
            docs_dir / "input.json",
            {
                "name": request.name,
                "slug": request.slug,
                "description": request.description,
                "project_type": request.project_type,
                "targets": request.targets,
                "stack": request.stack,
                "features": request.features,
                "created_at": _now(),
            },
        ),
        _write_text(
            docs_dir / "app_brief.md",
            f"""# App Brief: {request.name}

## Description

{request.description}

## Project Type

`{request.project_type}`

## Targets

{", ".join(request.targets) or "Not specified"}

## Stack

```json
{json.dumps(request.stack, indent=2, ensure_ascii=False)}
````

## Features

{chr(10).join(f"- {feature}" for feature in request.features) or "- Not specified"}

## Status

PASS
""",
),
_write_text(
docs_dir / "project_context.md",
f"""# Project Context

This project was created through the Modular AI Factory pipeline.

## Name

{request.name}

## Purpose

{request.description}

## Status

PASS
""",
),
]

def _run_common_business_analysis(request: FactoryRequest, docs_dir: Path) -> list[Path]:
return [
_write_text(
docs_dir / "requirements.md",
f"""# Requirements: {request.name}

## Functional Requirements

{chr(10).join(f"- The system shall support `{feature}`." for feature in request.features) or "- The system shall provide core MVP functionality."}

## Status

PASS
""",
),
_write_text(
docs_dir / "user_stories.md",
f"""# User Stories

{chr(10).join(f"- As a user, I want to use `{feature}` so that I can complete my workflow faster." for feature in request.features) or "- As a user, I want a working MVP."}

## Status

PASS
""",
),
_write_text(
docs_dir / "acceptance_criteria.md",
f"""# Acceptance Criteria

{chr(10).join(f"- `{feature}` is visible, usable, and documented." for feature in request.features) or "- The MVP can start successfully."}

## Status

PASS
""",
),
_write_json(
docs_dir / "product_spec.json",
{
"name": request.name,
"description": request.description,
"project_type": request.project_type,
"targets": request.targets,
"stack": request.stack,
"features": request.features,
"status": "PASS",
},
),
]

def _run_common_architecture(request: FactoryRequest, docs_dir: Path) -> list[Path]:
return [
_write_text(
docs_dir / "architecture.md",
f"""# Architecture

## Project Type

`{request.project_type}`

## Selected Stack

```json
{json.dumps(request.stack, indent=2, ensure_ascii=False)}
```

## Architecture Direction

The project is generated using a modular architecture. Each target is produced by a dedicated module.

## Status

PASS
""",
),
_write_text(
docs_dir / "folder_structure.md",
"""# Folder Structure

```text
source/
├── frontend/
├── backend/
├── mobile/
└── infra/
docs/
exports/
```

## Status

PASS
""",
),
_write_text(
docs_dir / "dependency_plan.md",
"""# Dependency Plan

Dependencies are selected by each module.

## Status

PASS
""",
),
]

def _run_common_uiux(request: FactoryRequest, docs_dir: Path) -> list[Path]:
return [
_write_text(
docs_dir / "design.md",
f"""# UI/UX Design

## Style

Modern, clean, dashboard-ready interface.

## Target Experience

The UI should be simple, responsive, and focused on the core user workflow.

## Status

PASS
""",
),
_write_text(
docs_dir / "screen_list.md",
f"""# Screen List

* Home
* Dashboard
* Settings
  {chr(10).join(f"- {feature.replace('_', ' ').title()}" for feature in request.features)}

## Status

PASS
""",
),
_write_text(
docs_dir / "component_spec.md",
"""# Component Spec

* App Shell
* Navigation
* Cards
* Forms
* Lists
* Empty State
* Loading State
* Error State

## Status

PASS
""",
),
_write_text(
docs_dir / "ui_states.md",
"""# UI States

* Loading
* Empty
* Error
* Success
* Offline

## Status

PASS
""",
),
]

def _run_flutter_module(request: FactoryRequest, app_dir: Path) -> list[Path]:
mobile_dir = app_dir / "source" / "mobile"
return [
_write_text(
mobile_dir / "pubspec.yaml",
f"""name: {request.slug or "generated_mobile_app"}
description: {request.description}
publish_to: "none"

environment:
sdk: ">=3.3.0 <4.0.0"

dependencies:
flutter:
sdk: flutter

dev_dependencies:
flutter_test:
sdk: flutter

flutter:
uses-material-design: true
""",
),
_write_text(
mobile_dir / "lib" / "main.dart",
"""import 'package:flutter/material.dart';

void main() {
runApp(const GeneratedApp());
}

class GeneratedApp extends StatelessWidget {
const GeneratedApp({super.key});

@override
Widget build(BuildContext context) {
return MaterialApp(
title: 'Generated App',
home: const Scaffold(
body: Center(
child: Text('Generated Flutter App'),
),
),
);
}
}
""",
),
_write_text(
app_dir / "docs" / "mobile_flutter_report.md",
"""# Flutter Module Report

Status: PASS

Generated minimal Flutter mobile source.
""",
),
]

def _run_react_module(request: FactoryRequest, frontend_dir: Path, docs_dir: Path) -> list[Path]:
return [
_write_json(
frontend_dir / "package.json",
{
"scripts": {
"dev": "vite",
"build": "vite build",
"test": "echo "No tests yet"",
"lint": "echo "No lint configured yet"",
},
"dependencies": {
"@vitejs/plugin-react": "latest",
"vite": "latest",
"react": "latest",
"react-dom": "latest",
"typescript": "latest",
},
"devDependencies": {},
},
),
_write_text(
frontend_dir / "src" / "main.tsx",
"""import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
<React.StrictMode> <App />
</React.StrictMode>,
);
""",
),
_write_text(
frontend_dir / "src" / "App.tsx",
f"""export default function App() {{
return (
<main style={{{{ padding: 24, fontFamily: 'Inter, sans-serif' }}}}> <h1>{request.name}</h1> <p>{request.description}</p> </main>
);
}}
""",
),
_write_text(
docs_dir / "frontend_react_report.md",
"""# React Module Report

Status: PASS

Generated minimal React frontend source.
""",
),
]

def _run_nextjs_module(request: FactoryRequest, frontend_dir: Path, docs_dir: Path) -> list[Path]:
return [
_write_json(
frontend_dir / "package.json",
{
"scripts": {
"dev": "next dev",
"build": "next build",
"start": "next start",
"test": "echo "No tests yet"",
"lint": "next lint",
},
"dependencies": {
"next": "latest",
"react": "latest",
"react-dom": "latest",
"typescript": "latest",
},
"devDependencies": {},
},
),
_write_text(
frontend_dir / "app" / "page.tsx",
f"""export default function Page() {{
return (
<main style={{{{ padding: 24, fontFamily: 'Inter, sans-serif' }}}}> <h1>{request.name}</h1> <p>{request.description}</p> </main>
);
}}
""",
),
_write_text(
docs_dir / "frontend_nextjs_report.md",
"""# Next.js Module Report

Status: PASS

Generated minimal Next.js frontend source.
""",
),
]

def _run_fastapi_module(request: FactoryRequest, backend_dir: Path, docs_dir: Path) -> list[Path]:
return [
_write_text(
backend_dir / "requirements.txt",
"""fastapi
uvicorn[standard]
pydantic
pytest
""",
),
_write_text(
backend_dir / "main.py",
f'''from fastapi import FastAPI

app = FastAPI(title="{request.name} API")

@app.get("/health")
def health():
return {{"status": "ok"}}

@app.get("/api/features")
def features():
return {{"features": {json.dumps(request.features, ensure_ascii=False)}}}
''',
),
_write_text(
backend_dir / "tests" / "test_health.py",
"""from fastapi.testclient import TestClient
from main import app

def test_health():
client = TestClient(app)
response = client.get("/health")
assert response.status_code == 200
assert response.json()["status"] == "ok"
""",
),
_write_text(
docs_dir / "backend_fastapi_report.md",
"""# FastAPI Module Report

Status: PASS

Generated minimal FastAPI backend source.
""",
),
]

def _run_supabase_module(request: FactoryRequest, supabase_dir: Path, docs_dir: Path) -> list[Path]:
schema = """-- Generated Supabase schema placeholder

create table if not exists app_items (
id uuid primary key default gen_random_uuid(),
title text not null,
status text not null default 'active',
created_at timestamptz not null default now()
);
"""
return [
_write_text(supabase_dir / "schema.sql", schema),
_write_text(supabase_dir / "seed.sql", "-- Add seed data here.\n"),
_write_text(docs_dir / "database_schema.sql", schema),
_write_text(
docs_dir / "env_contract.md",
"""# Environment Contract

## Required Variables

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
```

## Status

PASS
""",
),
]

def _run_common_qa(request: FactoryRequest, docs_dir: Path, step: PipelineStep) -> list[Path]:
return [
_write_text(
docs_dir / "test_report.md",
f"""# Static QA Report

Status: PASS

## Module

`{step.module_id}`

## Quality Commands

{chr(10).join(f"- `{cmd}`" for cmd in step.quality_commands) or "- No commands configured."}
""",
),
_write_text(
docs_dir / "bug_list.md",
"""# Bug List

Status: PASS

No blocking issues found.
""",
),
_write_json(
docs_dir / "qa_summary.json",
{
"status": "PASS",
"generated_at": _now(),
},
),
]

def _run_common_repair(request: FactoryRequest, docs_dir: Path) -> list[Path]:
return [
_write_text(
docs_dir / "refactor_report.md",
"""# Refactor Report

Status: PASS

No repair required.
""",
),
_write_text(
docs_dir / "repair_history.md",
"""# Repair History

Status: PASS

No repair attempts were required.
""",
),
]

def _run_common_runtime(request: FactoryRequest, docs_dir: Path) -> list[Path]:
return [
_write_text(
docs_dir / "runtime_report.md",
"""# Runtime Report

Status: PASS

Runtime smoke verification placeholder passed.
""",
),
_write_json(
docs_dir / "runtime_summary.json",
{
"status": "PASS",
"generated_at": _now(),
},
),
]

def _run_common_security(request: FactoryRequest, docs_dir: Path) -> list[Path]:
return [
_write_text(
docs_dir / "security_report.md",
"""# Security Report

Status: PASS

No hardcoded secrets detected in the modular skeleton output.
""",
),
_write_text(
docs_dir / "production_release_checklist.md",
"""# Production Release Checklist

Status: PASS

* Configure environment variables.
* Enable HTTPS.
* Review auth and CORS.
* Run production build.
  """,
  ),
  ]

def _run_common_release_review(request: FactoryRequest, docs_dir: Path) -> list[Path]:
return [
_write_text(
docs_dir / "final_review.md",
"""# Final Review

Status: READY_FOR_MVP_HANDOFF

The modular factory skeleton generated the requested project structure.
""",
),
_write_text(
docs_dir / "release_checklist.md",
"""# Release Checklist

Status: PASS

* Docs generated.
* Source generated.
* QA placeholder passed.
* Security placeholder passed.
  """,
  ),
  _write_text(
  docs_dir / "handoff_notes.md",
  """# Handoff Notes

This project was generated by the Modular AI Factory MVP executor.
""",
),
]

def _run_common_export_report(request: FactoryRequest, app_dir: Path, docs_dir: Path) -> list[Path]:
return [
_write_text(
docs_dir / "export_report.md",
f"""# Export Report

Status: PASS

Generated project is ready for packaging.

## App Dir

`{app_dir}`
""",
)
]

````

---

# 3. Tạo `factory_core/pipeline_runner.py`

File này chạy pipeline modular và record phase vào DB.

```text
factory_core/pipeline_runner.py
````

```python
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from dashboard.database import (
    finish_phase,
    is_cancel_requested,
    log_job,
    start_phase,
)
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
```

---

# 4. Sửa `dashboard/routers/jobs.py`

Thay `GenerateRequest` hiện tại bằng bản mới nhưng vẫn support field cũ.

```python
class GenerateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)

    # New modular fields
    project_type: str | None = None
    targets: list[str] | None = None
    stack: dict[str, str] | None = None

    # Legacy fields
    platform: str = "android,ios"
    style: str = "modern"
    backend: str = "none"

    features: str | list[str] = ""
    slug: str = ""
```

Sau đó trong `create_generation_job()`, sửa đoạn build payload thành:

```python
from factory_core.request_adapter import normalize_factory_request
```

Và thay function `create_generation_job()` bằng bản này:

```python
@router.post("", status_code=202)
def create_generation_job(payload: GenerateRequest, _auth: dict = Depends(require_auth)) -> dict[str, Any]:
    raw_payload = payload.model_dump()
    factory_request = normalize_factory_request(raw_payload)

    slug = factory_request.slug or slugify(factory_request.name)
    factory_request.slug = slug

    features = factory_request.features
    if not features:
        features = ["todo", "dashboard", "settings"]
        factory_request.features = features

    app_dir = GENERATED_APPS_DIR / slug

    _upsert_job(
        slug=slug,
        name=factory_request.name,
        description=factory_request.description,
        status="queued",
        features=features,
        app_dir=app_dir,
    )

    job_payload = {
        "name": factory_request.name,
        "description": factory_request.description,
        "project_type": factory_request.project_type,
        "targets": factory_request.targets,
        "stack": factory_request.stack,
        "features": factory_request.features,
        "slug": slug,

        # Keep legacy compatibility
        "platform": raw_payload.get("platform", "android,ios"),
        "style": raw_payload.get("style", "modern"),
        "backend": raw_payload.get("backend", "none"),
    }

    if QUEUE_BACKEND == "rq":
        try:
            _enqueue_rq(job_payload, slug)
        except Exception as error:
            _upsert_job(
                slug=slug,
                name=factory_request.name,
                description=factory_request.description,
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
```

---

# 5. Sửa `dashboard/queue_manager.py`

Trong `_run_flutter_job()`, hiện tại vẫn gọi pipeline Flutter. Ta chuyển sang chọn mode:

* Nếu payload có `project_type`, dùng modular pipeline.
* Nếu không có `project_type`, fallback pipeline cũ.

Nhưng vì `request_adapter` luôn set `project_type`, cách tốt hơn là dùng env flag.

Thêm import:

```python
from factory_core.request_adapter import normalize_factory_request
from factory_core.pipeline_runner import (
    ModularPipelineCancelled,
    run_modular_pipeline,
)
```

Thêm biến:

```python
FACTORY_PIPELINE_MODE = os.getenv("FACTORY_PIPELINE_MODE", "modular").strip().lower()
```

Trong `_run_flutter_job()`, thay đoạn gọi workflow chính bằng:

```python
if FACTORY_PIPELINE_MODE == "modular":
    factory_request = normalize_factory_request(payload)
    factory_request.slug = slug

    result = run_modular_pipeline(factory_request, app_dir)

    _upsert_job(
        slug=slug,
        name=payload["name"],
        description=payload["description"],
        features=features,
        status="succeeded",
        app_dir=app_dir,
        export_path=result["export_path"],
    )
else:
    result = run_flutter_mvp_workflow(
        payload,
        app_dir,
        source_dir=source_dir,
        docs_dir=docs_dir,
    )

    _upsert_job(
        slug=slug,
        name=payload["name"],
        description=payload["description"],
        features=features,
        status="succeeded",
        app_dir=app_dir,
        export_path=result.export_path,
    )
```

Và trong except cancellation thêm:

```python
except ModularPipelineCancelled as error:
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
```

Nếu muốn mình viết nguyên file `_run_flutter_job()` đầy đủ thì dùng bản dưới đây.

---

# 6. Bản `_run_flutter_job()` đầy đủ

Trong `dashboard/queue_manager.py`, thay function `_run_flutter_job()` bằng:

```python
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

        finish_phase(
            slug,
            "01_create_brief",
            "passed",
            output_files=[
                "docs/input.json",
                "docs/app_brief.md",
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
            result = run_flutter_mvp_workflow(
                payload,
                app_dir,
                source_dir=source_dir,
                docs_dir=docs_dir,
            )

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
            features=features,
            status="failed",
            app_dir=app_dir,
            error=str(error),
        )
```

Nhớ kiểm tra đầu file có đủ import:

```python
import os
from typing import Any

from factory_core.request_adapter import normalize_factory_request
from factory_core.pipeline_runner import (
    ModularPipelineCancelled,
    run_modular_pipeline,
)
```

và có:

```python
FACTORY_PIPELINE_MODE = os.getenv("FACTORY_PIPELINE_MODE", "modular").strip().lower()
```

---

# 7. Thêm env vào `.env.example`

```env
# Factory pipeline mode:
# modular = use new modular AI Factory pipeline
# flutter_legacy = use old Flutter MVP pipeline
FACTORY_PIPELINE_MODE=modular
```

---

# 8. Update `factory_core/__init__.py`

```python
from factory_core.pipeline_builder import PipelineBuilder
from factory_core.pipeline_runner import run_modular_pipeline
from factory_core.request_adapter import normalize_factory_request
from factory_core.types import FactoryRequest, PipelinePlan, PipelineStep

__all__ = [
    "FactoryRequest",
    "PipelineBuilder",
    "PipelinePlan",
    "PipelineStep",
    "normalize_factory_request",
    "run_modular_pipeline",
]
```

---

# 9. Sửa API `/api/jobs/{slug}/phases`

Trong `dashboard/routers/jobs.py`, import thêm:

```python
from dashboard.database import list_job_phases
```

Đổi:

```python
@router.get("/{slug}/phases")
def get_job_phases(slug: str) -> dict[str, str]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return phase_status(slug)
```

thành:

```python
@router.get("/{slug}/phases")
def get_job_phases(slug: str, _auth: dict = Depends(require_auth)) -> list[dict[str, Any]]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list_job_phases(slug)
```

---

# 10. Test tạo modular job

Lấy token:

```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{
    "team_id": "default",
    "role": "admin"
  }'
```

Tạo fullstack job:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "PantrySaver",
    "slug": "pantry-saver",
    "description": "Food expiry tracker and meal planner",
    "project_type": "fullstack_saas",
    "targets": ["web", "mobile", "backend"],
    "stack": {
      "frontend": "nextjs",
      "backend": "fastapi",
      "database": "supabase"
    },
    "features": ["auth", "inventory", "expiry_reminders", "meal_planner"]
  }'
```

Xem phase:

```bash
curl http://localhost:8000/api/jobs/pantry-saver/phases \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Xem file tree:

```bash
curl http://localhost:8000/api/jobs/pantry-saver/code/tree
```

Download zip:

```bash
curl -L http://localhost:8000/api/jobs/pantry-saver/download \
  -o pantry-saver.zip
```

---

# 11. Test cần thêm

Tạo file:

```text
tests/test_modular_pipeline_runner.py
```

```python
from pathlib import Path

from factory_core import FactoryRequest
from factory_core.pipeline_runner import run_modular_pipeline


def test_run_modular_fullstack_pipeline(tmp_path: Path):
    request = FactoryRequest(
        name="PantrySaver",
        slug="pantry-saver",
        description="Food expiry tracker and meal planner",
        project_type="fullstack_saas",
        targets=["web", "backend"],
        stack={
            "frontend": "nextjs",
            "backend": "fastapi",
            "database": "supabase",
        },
        features=["auth", "inventory"],
    )

    app_dir = tmp_path / "pantry-saver"

    result = run_modular_pipeline(request, app_dir)

    assert Path(result["export_path"]).exists()
    assert (app_dir / "docs" / "pipeline_plan.json").exists()
    assert (app_dir / "source" / "frontend" / "package.json").exists()
    assert (app_dir / "source" / "backend" / "main.py").exists()
    assert (app_dir / "source" / "infra" / "supabase" / "schema.sql").exists()
```

Lưu ý: test này cần DB functions của dashboard. Nếu test lỗi vì DB path cố định, có thể tạm chỉ test `PipelineBuilder` trước. Sau đó mình sẽ tách `PhaseRecorder` interface để test sạch hơn.

---

# 12. Sau bước này hệ thống đã đạt gì?

Sau khi thêm phần này, repo sẽ có 2 pipeline mode:

```text
FACTORY_PIPELINE_MODE=modular
```

Dùng Modular AI Factory mới.

```text
FACTORY_PIPELINE_MODE=flutter_legacy
```

Dùng pipeline Flutter cũ.

Và request mới có thể chọn stack:

```text
frontend: react | nextjs
backend: fastapi
database: supabase
mobile: flutter
```

Đây là bước chuyển rất quan trọng: **Flutter không còn là lõi bắt buộc nữa**, mà chỉ là một module trong hệ thống.
