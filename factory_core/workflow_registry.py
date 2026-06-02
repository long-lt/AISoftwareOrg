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
