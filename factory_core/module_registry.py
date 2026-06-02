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
