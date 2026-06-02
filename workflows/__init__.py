"""
workflows package exports.

Keep heavy workflow imports lazy so lightweight modules such as
`workflows.phase_registry` do not pull in dashboard/orchestrator dependencies.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "run_task",
    "run_task_sync",
    "print_result",
    "run_full_pipeline",
    "print_full_result",
    "FullPipelineResult",
    "run_flutter_mvp_pipeline",
    "PipelineResult",
]


def __getattr__(name: str) -> Any:
    if name in {"run_task", "run_task_sync", "print_result"}:
        from . import dev_pipeline

        return getattr(dev_pipeline, name)
    if name in {"run_full_pipeline", "print_full_result", "FullPipelineResult"}:
        from . import full_pipeline

        return getattr(full_pipeline, name)
    if name in {"run_flutter_mvp_pipeline", "PipelineResult"}:
        from . import flutter_mvp

        return getattr(flutter_mvp, name)
    raise AttributeError(f"module 'workflows' has no attribute {name!r}")
