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
