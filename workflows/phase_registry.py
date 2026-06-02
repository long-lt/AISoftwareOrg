from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseContract:
    id: str
    name: str
    agent: str
    required_inputs: tuple[str, ...]
    required_outputs: tuple[str, ...]
    aliases: tuple[str, ...] = ()


PIPELINE_PHASES: tuple[PhaseContract, ...] = (
    PhaseContract(
        id="01_create_brief",
        name="Create Project Brief",
        agent="brief_agent",
        required_inputs=(),
        required_outputs=(
            "docs/input.json",
            "docs/app_brief.md",
            "docs/project_context.md",
            "docs/initial_constraints.md",
        ),
        aliases=("create",),
    ),
    PhaseContract(
        id="02_business_analysis",
        name="Business Analysis",
        agent="ba_agent",
        required_inputs=(
            "docs/input.json",
            "docs/app_brief.md",
            "docs/project_context.md",
            "docs/initial_constraints.md",
        ),
        required_outputs=(
            "docs/requirements.md",
            "docs/user_stories.md",
            "docs/feature_list.md",
            "docs/acceptance_criteria.md",
            "docs/product_spec.json",
            "docs/non_functional_requirements.md",
        ),
        aliases=("ba",),
    ),
    PhaseContract(
        id="03_backend_design",
        name="Backend Design",
        agent="backend_agent",
        required_inputs=(
            "docs/product_spec.json",
            "docs/requirements.md",
            "docs/acceptance_criteria.md",
        ),
        required_outputs=(
            "docs/api_contract.md",
            "docs/openapi.yaml",
            "docs/database_schema.sql",
            "docs/data_model.json",
            "docs/backend_strategy.md",
            "docs/env_contract.md",
        ),
        aliases=("backend",),
    ),
    PhaseContract(
        id="04_architecture_design",
        name="Architecture Design",
        agent="architect_agent",
        required_inputs=(
            "docs/product_spec.json",
            "docs/api_contract.md",
            "docs/data_model.json",
            "docs/backend_strategy.md",
        ),
        required_outputs=(
            "docs/architecture.md",
            "docs/folder_structure.md",
            "docs/state_management.md",
            "docs/navigation_map.md",
            "docs/api_strategy.md",
            "docs/database_strategy.md",
            "docs/dependency_plan.md",
        ),
        aliases=("architect", "architecture"),
    ),
    PhaseContract(
        id="05_uiux_design",
        name="UI/UX Design",
        agent="uiux_agent",
        required_inputs=(
            "docs/product_spec.json",
            "docs/user_stories.md",
            "docs/navigation_map.md",
            "docs/architecture.md",
        ),
        required_outputs=(
            "docs/design.md",
            "docs/screen_list.md",
            "docs/component_spec.md",
            "docs/theme_config.dart",
            "docs/interaction_flow.md",
            "docs/ui_states.md",
        ),
        aliases=("uiux",),
    ),
    PhaseContract(
        id="06_flutter_dev",
        name="Flutter Development",
        agent="dev_agent",
        required_inputs=(
            "docs/product_spec.json",
            "docs/architecture.md",
            "docs/folder_structure.md",
            "docs/state_management.md",
            "docs/navigation_map.md",
            "docs/design.md",
            "docs/screen_list.md",
            "docs/component_spec.md",
            "docs/theme_config.dart",
            "docs/api_contract.md",
        ),
        required_outputs=(
            "source/pubspec.yaml",
            "source/lib/main.dart",
            "source/lib/app.dart",
            "source/lib/core",
            "source/lib/features",
            "source/lib/shared",
            "source/test",
        ),
        aliases=("dev",),
    ),
    PhaseContract(
        id="07_static_qa",
        name="Static QA",
        agent="qa_agent",
        required_inputs=(
            "source",
            "docs/architecture.md",
            "docs/acceptance_criteria.md",
        ),
        required_outputs=(
            "docs/test_report.md",
            "docs/bug_list.md",
            "docs/static_analysis.log",
            "docs/qa_summary.json",
        ),
        aliases=("qa",),
    ),
    PhaseContract(
        id="08_refactor_repair",
        name="Refactor Repair",
        agent="refactor_agent",
        required_inputs=(
            "docs/bug_list.md",
            "docs/test_report.md",
            "docs/static_analysis.log",
            "source",
        ),
        required_outputs=(
            "docs/refactor_report.md",
            "docs/repair_history.md",
            "docs/changed_files.md",
            "source",
        ),
        aliases=("refactor", "repair"),
    ),
    PhaseContract(
        id="09_runtime_test",
        name="Runtime Test",
        agent="runtime_agent",
        required_inputs=(
            "source",
            "docs/navigation_map.md",
            "docs/screen_list.md",
            "docs/acceptance_criteria.md",
        ),
        required_outputs=(
            "docs/runtime_report.md",
            "docs/runtime_smoke.log",
            "docs/runtime_summary.json",
        ),
        aliases=("runtime",),
    ),
    PhaseContract(
        id="10_security_audit",
        name="Security Audit",
        agent="security_agent",
        required_inputs=(
            "source",
            "backend",
            "docs/api_contract.md",
            "docs/env_contract.md",
            "docs/database_schema.sql",
        ),
        required_outputs=(
            "docs/security_report.md",
            "docs/privacy_review.md",
            "docs/deployment_plan.md",
            "docs/production_release_checklist.md",
        ),
        aliases=("security",),
    ),
    PhaseContract(
        id="11_release_review",
        name="Release Review",
        agent="reviewer_agent",
        required_inputs=(
            "docs/test_report.md",
            "docs/runtime_report.md",
            "docs/security_report.md",
            "docs/requirements.md",
            "docs/acceptance_criteria.md",
            "source",
            "backend",
        ),
        required_outputs=(
            "docs/final_review.md",
            "docs/release_checklist.md",
            "docs/handoff_notes.md",
        ),
        aliases=("reviewer",),
    ),
    PhaseContract(
        id="12_export_package",
        name="Export Package",
        agent="export_agent",
        required_inputs=(
            "source",
            "backend",
            "docs",
            "docs/final_review.md",
            "docs/release_checklist.md",
        ),
        required_outputs=(
            "exports/{slug}_source.zip",
            "docs/export_report.md",
        ),
        aliases=("export",),
    ),
)

PHASE_IDS = tuple(phase.id for phase in PIPELINE_PHASES)
_PHASE_BY_ID = {phase.id: phase for phase in PIPELINE_PHASES}
_ALIAS_TO_ID = {
    alias: phase.id
    for phase in PIPELINE_PHASES
    for alias in phase.aliases
}


def canonical_phase_id(phase: str) -> str:
    return _ALIAS_TO_ID.get(phase, phase)


def get_phase_contract(phase: str) -> PhaseContract:
    phase_id = canonical_phase_id(phase)
    try:
        return _PHASE_BY_ID[phase_id]
    except KeyError as exc:
        raise ValueError(f"Unknown pipeline phase: {phase}") from exc


def phase_progress_percent(phase: str) -> int:
    phase_id = canonical_phase_id(phase)
    index = PHASE_IDS.index(phase_id) + 1
    return round(index / len(PHASE_IDS) * 100)
