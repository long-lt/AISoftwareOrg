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
