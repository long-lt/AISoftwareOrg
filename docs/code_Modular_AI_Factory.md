Dưới đây là bộ code **Modular AI Factory skeleton** để đưa repo từ `Flutter AI Factory` sang kiến trúc **AI Factory tổng quát**, nhưng **không phá pipeline Flutter hiện tại**.

Mục tiêu của bộ này:

```text
AI Factory Core
├── Workflow Registry
├── Module Registry
├── Pipeline Builder
├── Module Contract
└── Stack Resolver

Modules
├── mobile.flutter
├── frontend.react
├── frontend.nextjs
├── backend.fastapi
└── database.supabase
```

---

# 1. Tạo thư mục mới

Tạo các thư mục:

```bash
mkdir -p factory_core
mkdir -p modules/mobile/flutter
mkdir -p modules/frontend/react
mkdir -p modules/frontend/nextjs
mkdir -p modules/backend/fastapi
mkdir -p modules/database/supabase
mkdir -p workflows
```

---

# 2. File `factory_core/types.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


ProjectType = Literal[
    "mobile_app",
    "web_app",
    "backend_api",
    "fullstack_saas",
    "admin_dashboard",
    "cli_tool",
    "automation_worker",
    "ai_agent_system",
    "docs_only",
]

ModuleType = Literal[
    "common",
    "mobile",
    "frontend",
    "backend",
    "database",
    "feature",
    "deployment",
    "quality",
    "export",
]


@dataclass(slots=True)
class FactoryRequest:
    name: str
    description: str
    project_type: ProjectType
    targets: list[str] = field(default_factory=list)
    stack: dict[str, str] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)
    slug: str = ""


@dataclass(slots=True)
class ModuleSpec:
    id: str
    name: str
    type: ModuleType
    supported_project_types: list[str]
    required_inputs: list[str] = field(default_factory=list)
    produced_outputs: list[str] = field(default_factory=list)
    quality_commands: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowPhase:
    id: str
    module: str | None = None
    modules: list[str] = field(default_factory=list)
    required: bool = True


@dataclass(slots=True)
class WorkflowSpec:
    id: str
    name: str
    description: str = ""
    phases: list[WorkflowPhase] = field(default_factory=list)


@dataclass(slots=True)
class PipelineStep:
    phase_id: str
    module_id: str
    module_type: str
    module_name: str
    required_inputs: list[str]
    produced_outputs: list[str]
    quality_commands: list[str]


@dataclass(slots=True)
class PipelinePlan:
    request: FactoryRequest
    workflow: WorkflowSpec
    steps: list[PipelineStep]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": {
                "name": self.request.name,
                "slug": self.request.slug,
                "description": self.request.description,
                "project_type": self.request.project_type,
                "targets": self.request.targets,
                "stack": self.request.stack,
                "features": self.request.features,
            },
            "workflow": {
                "id": self.workflow.id,
                "name": self.workflow.name,
                "description": self.workflow.description,
            },
            "steps": [
                {
                    "phase_id": step.phase_id,
                    "module_id": step.module_id,
                    "module_type": step.module_type,
                    "module_name": step.module_name,
                    "required_inputs": step.required_inputs,
                    "produced_outputs": step.produced_outputs,
                    "quality_commands": step.quality_commands,
                }
                for step in self.steps
            ],
        }
```

---

# 3. File `factory_core/module_registry.py`

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from factory_core.types import ModuleSpec


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODULES_DIR = ROOT_DIR / "modules"


class ModuleRegistryError(RuntimeError):
    pass


class ModuleRegistry:
    def __init__(self, modules_dir: Path | None = None) -> None:
        self.modules_dir = modules_dir or DEFAULT_MODULES_DIR
        self._modules: dict[str, ModuleSpec] = {}

    def load(self) -> None:
        self._modules.clear()

        if not self.modules_dir.exists():
            return

        for module_yaml in self.modules_dir.rglob("module.yaml"):
            spec = self._load_module_yaml(module_yaml)
            if spec.id in self._modules:
                raise ModuleRegistryError(f"Duplicate module id: {spec.id}")
            self._modules[spec.id] = spec

    def all(self) -> list[ModuleSpec]:
        if not self._modules:
            self.load()
        return list(self._modules.values())

    def get(self, module_id: str) -> ModuleSpec:
        if not self._modules:
            self.load()

        try:
            return self._modules[module_id]
        except KeyError as exc:
            raise ModuleRegistryError(f"Unknown module: {module_id}") from exc

    def exists(self, module_id: str) -> bool:
        if not self._modules:
            self.load()
        return module_id in self._modules

    def by_type(self, module_type: str) -> list[ModuleSpec]:
        return [module for module in self.all() if module.type == module_type]

    def supported_by_project_type(self, project_type: str) -> list[ModuleSpec]:
        return [
            module
            for module in self.all()
            if project_type in module.supported_project_types
        ]

    def _load_module_yaml(self, path: Path) -> ModuleSpec:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        required_fields = ["id", "name", "type", "supported_project_types"]
        missing = [field for field in required_fields if not raw.get(field)]
        if missing:
            raise ModuleRegistryError(f"{path} missing required fields: {missing}")

        return ModuleSpec(
            id=str(raw["id"]),
            name=str(raw["name"]),
            type=str(raw["type"]),
            supported_project_types=list(raw.get("supported_project_types", [])),
            required_inputs=list(raw.get("required_inputs", [])),
            produced_outputs=list(raw.get("produced_outputs", [])),
            quality_commands=list(raw.get("quality_commands", [])),
            dependencies=list(raw.get("dependencies", [])),
            path=path.parent,
            metadata={k: v for k, v in raw.items() if k not in {
                "id",
                "name",
                "type",
                "supported_project_types",
                "required_inputs",
                "produced_outputs",
                "quality_commands",
                "dependencies",
            }},
        )


_default_registry: ModuleRegistry | None = None


def get_module_registry() -> ModuleRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ModuleRegistry()
        _default_registry.load()
    return _default_registry
```

---

# 4. File `factory_core/workflow_registry.py`

```python
from __future__ import annotations

from pathlib import Path

import yaml

from factory_core.types import WorkflowPhase, WorkflowSpec


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_WORKFLOWS_DIR = ROOT_DIR / "workflows"


class WorkflowRegistryError(RuntimeError):
    pass


class WorkflowRegistry:
    def __init__(self, workflows_dir: Path | None = None) -> None:
        self.workflows_dir = workflows_dir or DEFAULT_WORKFLOWS_DIR
        self._workflows: dict[str, WorkflowSpec] = {}

    def load(self) -> None:
        self._workflows.clear()

        if not self.workflows_dir.exists():
            return

        for workflow_yaml in self.workflows_dir.glob("*.yaml"):
            spec = self._load_workflow_yaml(workflow_yaml)
            if spec.id in self._workflows:
                raise WorkflowRegistryError(f"Duplicate workflow id: {spec.id}")
            self._workflows[spec.id] = spec

    def all(self) -> list[WorkflowSpec]:
        if not self._workflows:
            self.load()
        return list(self._workflows.values())

    def get(self, workflow_id: str) -> WorkflowSpec:
        if not self._workflows:
            self.load()

        try:
            return self._workflows[workflow_id]
        except KeyError as exc:
            raise WorkflowRegistryError(f"Unknown workflow: {workflow_id}") from exc

    def _load_workflow_yaml(self, path: Path) -> WorkflowSpec:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        if not raw.get("id"):
            raise WorkflowRegistryError(f"{path} missing workflow id")

        phases = []
        for phase in raw.get("phases", []):
            phases.append(
                WorkflowPhase(
                    id=str(phase["id"]),
                    module=phase.get("module"),
                    modules=list(phase.get("modules", [])),
                    required=bool(phase.get("required", True)),
                )
            )

        return WorkflowSpec(
            id=str(raw["id"]),
            name=str(raw.get("name", raw["id"])),
            description=str(raw.get("description", "")),
            phases=phases,
        )


_default_registry: WorkflowRegistry | None = None


def get_workflow_registry() -> WorkflowRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = WorkflowRegistry()
        _default_registry.load()
    return _default_registry
```

---

# 5. File `factory_core/stack_resolver.py`

```python
from __future__ import annotations

from factory_core.types import FactoryRequest


class StackResolverError(RuntimeError):
    pass


STACK_MODULE_MAP: dict[str, dict[str, str]] = {
    "mobile": {
        "flutter": "mobile.flutter",
    },
    "frontend": {
        "react": "frontend.react",
        "nextjs": "frontend.nextjs",
    },
    "backend": {
        "fastapi": "backend.fastapi",
    },
    "database": {
        "supabase": "database.supabase",
    },
}


def resolve_selected_module(selector: str, request: FactoryRequest) -> str:
    """
    Resolve workflow placeholders such as:
    - mobile.selected
    - frontend.selected
    - backend.selected
    - database.selected
    """

    if not selector.endswith(".selected"):
        return selector

    category = selector.split(".", 1)[0]
    selected_stack = request.stack.get(category)

    if not selected_stack:
        raise StackResolverError(
            f"Workflow requires '{category}.selected', but request.stack['{category}'] is missing"
        )

    category_map = STACK_MODULE_MAP.get(category)
    if not category_map:
        raise StackResolverError(f"No stack map configured for category: {category}")

    module_id = category_map.get(selected_stack)
    if not module_id:
        raise StackResolverError(
            f"Unsupported {category} stack '{selected_stack}'. "
            f"Supported: {sorted(category_map.keys())}"
        )

    return module_id
```

---

# 6. File `factory_core/pipeline_builder.py`

```python
from __future__ import annotations

from factory_core.module_registry import ModuleRegistry, get_module_registry
from factory_core.stack_resolver import resolve_selected_module
from factory_core.types import FactoryRequest, PipelinePlan, PipelineStep
from factory_core.workflow_registry import WorkflowRegistry, get_workflow_registry


class PipelineBuilderError(RuntimeError):
    pass


class PipelineBuilder:
    def __init__(
        self,
        module_registry: ModuleRegistry | None = None,
        workflow_registry: WorkflowRegistry | None = None,
    ) -> None:
        self.module_registry = module_registry or get_module_registry()
        self.workflow_registry = workflow_registry or get_workflow_registry()

    def build(self, request: FactoryRequest) -> PipelinePlan:
        workflow = self.workflow_registry.get(request.project_type)

        steps: list[PipelineStep] = []

        for phase in workflow.phases:
            module_ids: list[str] = []

            if phase.module:
                module_ids.append(resolve_selected_module(phase.module, request))

            for module_id in phase.modules:
                module_ids.append(resolve_selected_module(module_id, request))

            if not module_ids and phase.required:
                raise PipelineBuilderError(f"Phase '{phase.id}' has no module")

            for module_id in module_ids:
                module = self.module_registry.get(module_id)

                if request.project_type not in module.supported_project_types:
                    raise PipelineBuilderError(
                        f"Module '{module.id}' does not support project type '{request.project_type}'"
                    )

                steps.append(
                    PipelineStep(
                        phase_id=phase.id,
                        module_id=module.id,
                        module_type=module.type,
                        module_name=module.name,
                        required_inputs=module.required_inputs,
                        produced_outputs=module.produced_outputs,
                        quality_commands=module.quality_commands,
                    )
                )

        return PipelinePlan(
            request=request,
            workflow=workflow,
            steps=steps,
        )
```

---

# 7. File `factory_core/__init__.py`

```python
from factory_core.pipeline_builder import PipelineBuilder
from factory_core.types import FactoryRequest, PipelinePlan, PipelineStep

__all__ = [
    "FactoryRequest",
    "PipelineBuilder",
    "PipelinePlan",
    "PipelineStep",
]
```

---

# 8. Module Flutter: `modules/mobile/flutter/module.yaml`

```yaml
id: mobile.flutter
name: Flutter Mobile App Module
type: mobile

supported_project_types:
  - mobile_app
  - fullstack_saas

required_inputs:
  - docs/product_spec.json
  - docs/architecture.md
  - docs/design.md
  - docs/api_contract.md

produced_outputs:
  - source/mobile/pubspec.yaml
  - source/mobile/lib/main.dart
  - source/mobile/lib/app.dart
  - source/mobile/lib/core/
  - source/mobile/lib/features/

quality_commands:
  - flutter pub get
  - dart format --set-exit-if-changed .
  - flutter analyze
  - flutter test
  - flutter build web

dependencies: []

default_template: flutter_clean_architecture
```

---

# 9. Module React: `modules/frontend/react/module.yaml`

```yaml
id: frontend.react
name: React Frontend Module
type: frontend

supported_project_types:
  - web_app
  - admin_dashboard
  - fullstack_saas

required_inputs:
  - docs/product_spec.json
  - docs/design.md
  - docs/api_contract.md

produced_outputs:
  - source/frontend/package.json
  - source/frontend/src/main.tsx
  - source/frontend/src/App.tsx
  - source/frontend/src/features/
  - source/frontend/src/shared/

quality_commands:
  - npm install
  - npm run lint
  - npm run build
  - npm test

dependencies: []

default_template: react_dashboard
```

---

# 10. Module Next.js: `modules/frontend/nextjs/module.yaml`

```yaml
id: frontend.nextjs
name: Next.js Frontend Module
type: frontend

supported_project_types:
  - web_app
  - admin_dashboard
  - fullstack_saas

required_inputs:
  - docs/product_spec.json
  - docs/design.md
  - docs/api_contract.md

produced_outputs:
  - source/frontend/package.json
  - source/frontend/app/
  - source/frontend/components/
  - source/frontend/lib/

quality_commands:
  - npm install
  - npm run lint
  - npm run build
  - npm test

dependencies: []

default_template: nextjs_saas
```

---

# 11. Module FastAPI: `modules/backend/fastapi/module.yaml`

```yaml
id: backend.fastapi
name: FastAPI Backend Module
type: backend

supported_project_types:
  - backend_api
  - fullstack_saas
  - mobile_app

required_inputs:
  - docs/product_spec.json
  - docs/api_contract.md
  - docs/data_model.json

produced_outputs:
  - source/backend/requirements.txt
  - source/backend/main.py
  - source/backend/app/
  - source/backend/tests/

quality_commands:
  - python -m compileall source/backend
  - ruff check source/backend
  - pytest source/backend/tests

dependencies: []

default_template: fastapi_service
```

---

# 12. Module Supabase: `modules/database/supabase/module.yaml`

```yaml
id: database.supabase
name: Supabase Database Module
type: database

supported_project_types:
  - fullstack_saas
  - mobile_app
  - web_app

required_inputs:
  - docs/product_spec.json
  - docs/data_model.json

produced_outputs:
  - source/infra/supabase/schema.sql
  - source/infra/supabase/seed.sql
  - docs/database_schema.sql
  - docs/env_contract.md

quality_commands:
  - echo "Supabase schema validation placeholder"

dependencies: []

default_template: supabase_project
```

---

# 13. Workflow Mobile App: `workflows/mobile_app.yaml`

```yaml
id: mobile_app
name: Mobile App Workflow
description: Generate a mobile application with optional backend/database support.

phases:
  - id: 01_create_brief
    module: common.brief

  - id: 02_business_analysis
    module: common.business_analysis

  - id: 03_architecture_design
    module: common.architecture

  - id: 04_uiux_design
    module: common.uiux

  - id: 05_mobile_generation
    module: mobile.selected

  - id: 06_static_qa
    module: common.qa

  - id: 07_repair_loop
    module: common.repair

  - id: 08_runtime_test
    module: common.runtime

  - id: 09_security_audit
    module: common.security

  - id: 10_release_review
    module: common.release_review

  - id: 11_export_package
    module: common.export
```

---

# 14. Workflow Fullstack SaaS: `workflows/fullstack_saas.yaml`

```yaml
id: fullstack_saas
name: Fullstack SaaS Workflow
description: Generate a fullstack SaaS product with frontend, backend, database, QA, security, and export.

phases:
  - id: 01_create_brief
    module: common.brief

  - id: 02_business_analysis
    module: common.business_analysis

  - id: 03_system_architecture
    module: common.architecture

  - id: 04_database_design
    module: database.selected

  - id: 05_backend_generation
    module: backend.selected

  - id: 06_frontend_generation
    module: frontend.selected

  - id: 07_static_qa
    module: common.qa

  - id: 08_repair_loop
    module: common.repair

  - id: 09_runtime_test
    module: common.runtime

  - id: 10_security_audit
    module: common.security

  - id: 11_release_review
    module: common.release_review

  - id: 12_export_package
    module: common.export
```

---

# 15. Tạo Common Modules để workflow không lỗi

Tạo thư mục:

```bash
mkdir -p modules/common/brief
mkdir -p modules/common/business_analysis
mkdir -p modules/common/architecture
mkdir -p modules/common/uiux
mkdir -p modules/common/qa
mkdir -p modules/common/repair
mkdir -p modules/common/runtime
mkdir -p modules/common/security
mkdir -p modules/common/release_review
mkdir -p modules/common/export
```

## `modules/common/brief/module.yaml`

```yaml
id: common.brief
name: Project Brief Module
type: common

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system
  - docs_only

required_inputs: []

produced_outputs:
  - docs/input.json
  - docs/app_brief.md
  - docs/project_context.md

quality_commands: []
dependencies: []
```

## `modules/common/business_analysis/module.yaml`

```yaml
id: common.business_analysis
name: Business Analysis Module
type: common

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system
  - docs_only

required_inputs:
  - docs/app_brief.md

produced_outputs:
  - docs/requirements.md
  - docs/user_stories.md
  - docs/acceptance_criteria.md
  - docs/product_spec.json

quality_commands: []
dependencies: []
```

## `modules/common/architecture/module.yaml`

```yaml
id: common.architecture
name: Architecture Module
type: common

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system
  - docs_only

required_inputs:
  - docs/product_spec.json

produced_outputs:
  - docs/architecture.md
  - docs/folder_structure.md
  - docs/dependency_plan.md

quality_commands: []
dependencies: []
```

## `modules/common/uiux/module.yaml`

```yaml
id: common.uiux
name: UI UX Design Module
type: common

supported_project_types:
  - mobile_app
  - web_app
  - fullstack_saas
  - admin_dashboard

required_inputs:
  - docs/product_spec.json
  - docs/architecture.md

produced_outputs:
  - docs/design.md
  - docs/screen_list.md
  - docs/component_spec.md
  - docs/ui_states.md

quality_commands: []
dependencies: []
```

## `modules/common/qa/module.yaml`

```yaml
id: common.qa
name: Static QA Module
type: quality

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system

required_inputs:
  - source/

produced_outputs:
  - docs/test_report.md
  - docs/bug_list.md
  - docs/qa_summary.json

quality_commands: []
dependencies: []
```

## `modules/common/repair/module.yaml`

```yaml
id: common.repair
name: Repair Loop Module
type: quality

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system

required_inputs:
  - docs/bug_list.md
  - source/

produced_outputs:
  - docs/refactor_report.md
  - docs/repair_history.md

quality_commands: []
dependencies: []
```

## `modules/common/runtime/module.yaml`

```yaml
id: common.runtime
name: Runtime Verification Module
type: quality

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system

required_inputs:
  - source/

produced_outputs:
  - docs/runtime_report.md
  - docs/runtime_summary.json

quality_commands: []
dependencies: []
```

## `modules/common/security/module.yaml`

```yaml
id: common.security
name: Security Audit Module
type: quality

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system

required_inputs:
  - source/

produced_outputs:
  - docs/security_report.md
  - docs/env_contract.md
  - docs/production_release_checklist.md

quality_commands: []
dependencies: []
```

## `modules/common/release_review/module.yaml`

```yaml
id: common.release_review
name: Release Review Module
type: quality

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system
  - docs_only

required_inputs:
  - docs/test_report.md
  - docs/security_report.md

produced_outputs:
  - docs/final_review.md
  - docs/release_checklist.md
  - docs/handoff_notes.md

quality_commands: []
dependencies: []
```

## `modules/common/export/module.yaml`

```yaml
id: common.export
name: Export Package Module
type: export

supported_project_types:
  - mobile_app
  - web_app
  - backend_api
  - fullstack_saas
  - admin_dashboard
  - cli_tool
  - automation_worker
  - ai_agent_system
  - docs_only

required_inputs:
  - source/
  - docs/

produced_outputs:
  - exports/source.zip
  - docs/export_report.md

quality_commands: []
dependencies: []
```

---

# 16. Test nhanh Pipeline Builder

Tạo file:

```text
tests/test_modular_factory.py
```

```python
from factory_core import FactoryRequest, PipelineBuilder


def test_build_mobile_flutter_pipeline():
    request = FactoryRequest(
        name="PantrySaver",
        slug="pantry-saver",
        description="Food expiry tracker and meal planner",
        project_type="mobile_app",
        targets=["mobile"],
        stack={
            "mobile": "flutter",
        },
        features=["inventory", "expiry_reminders", "meal_planner"],
    )

    plan = PipelineBuilder().build(request)

    assert plan.workflow.id == "mobile_app"
    assert any(step.module_id == "mobile.flutter" for step in plan.steps)
    assert any(step.module_id == "common.qa" for step in plan.steps)
    assert any(step.module_id == "common.export" for step in plan.steps)


def test_build_fullstack_saas_pipeline():
    request = FactoryRequest(
        name="AISaaS",
        slug="ai-saas",
        description="Fullstack SaaS with web dashboard and backend API",
        project_type="fullstack_saas",
        targets=["web", "backend"],
        stack={
            "frontend": "nextjs",
            "backend": "fastapi",
            "database": "supabase",
        },
        features=["auth", "dashboard", "billing"],
    )

    plan = PipelineBuilder().build(request)

    module_ids = [step.module_id for step in plan.steps]

    assert plan.workflow.id == "fullstack_saas"
    assert "frontend.nextjs" in module_ids
    assert "backend.fastapi" in module_ids
    assert "database.supabase" in module_ids
    assert "common.security" in module_ids
    assert "common.export" in module_ids


def test_pipeline_plan_to_dict():
    request = FactoryRequest(
        name="Backend API",
        slug="backend-api",
        description="Simple backend API",
        project_type="fullstack_saas",
        targets=["web", "backend"],
        stack={
            "frontend": "react",
            "backend": "fastapi",
            "database": "supabase",
        },
        features=["auth"],
    )

    plan = PipelineBuilder().build(request)
    payload = plan.to_dict()

    assert payload["project"]["name"] == "Backend API"
    assert payload["workflow"]["id"] == "fullstack_saas"
    assert len(payload["steps"]) > 0
```

---

# 17. Thêm API để dashboard xem modules/workflows

Tạo file:

```text
dashboard/routers/factory.py
```

```python
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from dashboard.routers.auth import require_auth
from factory_core import FactoryRequest, PipelineBuilder
from factory_core.module_registry import get_module_registry
from factory_core.workflow_registry import get_workflow_registry


router = APIRouter()


class BuildPipelineRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    project_type: str = "mobile_app"
    targets: list[str] = []
    stack: dict[str, str] = {}
    features: list[str] = []
    slug: str = ""


@router.get("/factory/modules")
def list_factory_modules(_auth: dict = Depends(require_auth)) -> list[dict[str, Any]]:
    modules = get_module_registry().all()
    return [
        {
            "id": module.id,
            "name": module.name,
            "type": module.type,
            "supported_project_types": module.supported_project_types,
            "required_inputs": module.required_inputs,
            "produced_outputs": module.produced_outputs,
            "quality_commands": module.quality_commands,
            "dependencies": module.dependencies,
            "path": str(module.path) if module.path else None,
            "metadata": module.metadata,
        }
        for module in modules
    ]


@router.get("/factory/workflows")
def list_factory_workflows(_auth: dict = Depends(require_auth)) -> list[dict[str, Any]]:
    workflows = get_workflow_registry().all()
    return [
        {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "phases": [
                {
                    "id": phase.id,
                    "module": phase.module,
                    "modules": phase.modules,
                    "required": phase.required,
                }
                for phase in workflow.phases
            ],
        }
        for workflow in workflows
    ]


@router.post("/factory/pipeline/preview")
def preview_pipeline(
    payload: BuildPipelineRequest,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    request = FactoryRequest(
        name=payload.name,
        description=payload.description,
        project_type=payload.project_type,  # type: ignore[arg-type]
        targets=payload.targets,
        stack=payload.stack,
        features=payload.features,
        slug=payload.slug,
    )

    plan = PipelineBuilder().build(request)
    return plan.to_dict()
```

---

# 18. Include router vào `dashboard/app.py`

Trong `dashboard/app.py`, import thêm:

```python
from dashboard.routers import factory
```

Và include:

```python
app.include_router(factory.router, prefix="/api", tags=["factory"])
```

Nếu file đang include router kiểu này:

```python
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
```

thì thêm bên dưới là được.

---

# 19. Chạy test

```bash
make setup
pytest tests/test_modular_factory.py
```

Test API:

```bash
curl -X GET http://localhost:8000/api/factory/modules \
  -H "Authorization: Bearer <TOKEN>"
```

Preview fullstack pipeline:

```bash
curl -X POST http://localhost:8000/api/factory/pipeline/preview \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
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

---

# 20. Ý nghĩa sau khi thêm bộ này

Sau khi thêm code trên, repo sẽ có nền modular thật sự:

```text
factory_core/
├── types.py
├── module_registry.py
├── workflow_registry.py
├── stack_resolver.py
└── pipeline_builder.py

modules/
├── common/
├── mobile/flutter/
├── frontend/react/
├── frontend/nextjs/
├── backend/fastapi/
└── database/supabase/

workflows/
├── mobile_app.yaml
└── fullstack_saas.yaml
```

Lúc này `Flutter` không còn là core nữa. Nó chỉ là:

```text
modules/mobile/flutter
```

Bước tiếp theo mới là nối `PipelineBuilder` vào `POST /api/jobs`, để request kiểu mới có thể tự chọn:

```text
mobile.flutter
frontend.nextjs
backend.fastapi
database.supabase
```

thay vì hard-code `run_flutter_mvp_workflow()`.
