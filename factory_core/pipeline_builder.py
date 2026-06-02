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
