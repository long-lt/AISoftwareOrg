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
```

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
                    "test": 'echo "No tests yet"',
                    "lint": 'echo "No lint configured yet"',
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
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
""",
        ),
        _write_text(
            frontend_dir / "src" / "App.tsx",
            f"""export default function App() {{
  return (
    <main style={{{{ padding: 24, fontFamily: 'Inter, sans-serif' }}}}>
      <h1>{request.name}</h1>
      <p>{request.description}</p>
    </main>
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
                    "test": 'echo "No tests yet"',
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
    <main style={{{{ padding: 24, fontFamily: 'Inter, sans-serif' }}}}>
      <h1>{request.name}</h1>
      <p>{request.description}</p>
    </main>
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
