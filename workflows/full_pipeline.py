"""
workflows/full_pipeline.py
Pipeline đầy đủ Phase 2: User input → PM → Planner → Dev loop(s).

Flow:
    user_requirement
        → PMAgent     (viết spec + task list)
        → PlannerAgent (thiết kế architecture + dev tasks)
        → [DevPipeline × n] (chạy từng dev task qua Dev→Review→QA→Fix loop)
        → FullPipelineResult

Usage:
    from workflows.full_pipeline import run_full_pipeline
    result = asyncio.run(run_full_pipeline("tôi muốn một REST API quản lý todo list"))
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from agents import AgentTask, PMAgent, PlannerAgent
from core.graph.state     import WorkflowState, TaskStatus
from .dev_pipeline        import run_task, print_result


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class FullPipelineResult:
    """Kết quả toàn bộ pipeline từ requirement đến code."""
    requirement:  str
    pm_spec:      Optional[dict]         = None   # Output của PMAgent
    plan:         Optional[dict]         = None   # Output của PlannerAgent
    task_results: list[WorkflowState]    = field(default_factory=list)
    errors:       list[str]              = field(default_factory=list)
    started_at:   str                    = field(default_factory=lambda: datetime.now().isoformat())
    finished_at:  Optional[str]          = None

    @property
    def success(self) -> bool:
        if not self.task_results:
            return False
        return all(r.get("test_result") == "pass" for r in self.task_results)

    @property
    def summary(self) -> str:
        total  = len(self.task_results)
        passed = sum(1 for r in self.task_results if r.get("test_result") == "pass")
        return f"{passed}/{total} tasks passed"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_full_pipeline(
    requirement: str,
    max_attempts: int = 3,
    use_docker:   bool = False,
    parallel:     bool = False,   # Phase 5 feature — keep False for now
) -> FullPipelineResult:
    """Chạy toàn bộ pipeline từ requirement đến code.

    Args:
        requirement:  Yêu cầu từ user (có thể mơ hồ).
        max_attempts: Số lần fix tối đa cho mỗi dev task.
        use_docker:   True = Docker sandbox, False = local.
        parallel:     Chạy dev tasks song song (Phase 5). Giữ False ở Phase 2.
    """
    result = FullPipelineResult(requirement=requirement)

    print(f"\n{'='*60}")
    print(f"🚀  FULL PIPELINE")
    print(f"{'='*60}")
    print(f"   Requirement: {requirement[:120]}")
    print(f"{'─'*60}")

    # ── Step 1: PM Agent ────────────────────────────────────────────────────
    print(f"\n  📋  STEP 1/3 — PM Agent: Phân tích yêu cầu...")
    pm_agent  = PMAgent()
    pm_task   = AgentTask(id="pm-001", description=requirement)
    pm_result = await pm_agent.run(pm_task)

    if not pm_result.success:
        result.errors.append(f"PMAgent failed: {pm_result.reason}")
        result.finished_at = datetime.now().isoformat()
        print(f"  ❌  PM Agent thất bại: {pm_result.reason}")
        return result

    try:
        result.pm_spec = json.loads(pm_result.output)
        feature_name = result.pm_spec.get('feature_name', '?')
        n_tasks = len(result.pm_spec.get("tasks", []))
        print(f"  ✅  Project: {feature_name}")
        print(f"      {n_tasks} tasks identified")
        print(f"      {result.pm_spec.get('one_line_summary', '')[:100]}")
    except json.JSONDecodeError:
        result.errors.append("PMAgent output không phải JSON hợp lệ")
        result.finished_at = datetime.now().isoformat()
        return result

    # ── Step 2: Planner Agent ───────────────────────────────────────────────
    print(f"\n  🏗️   STEP 2/3 — Planner Agent: Thiết kế kiến trúc...")
    planner_agent  = PlannerAgent()
    planner_task   = AgentTask(
        id="planner-001",
        description=requirement,
        context=pm_result.output,
    )
    planner_result = await planner_agent.run(planner_task)

    if not planner_result.success:
        result.errors.append(f"PlannerAgent failed: {planner_result.reason}")
        result.finished_at = datetime.now().isoformat()
        print(f"  ❌  Planner Agent thất bại: {planner_result.reason}")
        return result

    try:
        result.plan = json.loads(planner_result.output)
        dev_tasks   = result.plan.get("dev_tasks", [])
        stack       = result.plan.get("tech_stack", {})
        print(f"  ✅  Architecture: {result.plan.get('architecture_pattern', '?')}")
        print(f"      Stack: {stack.get('language','?')} / {stack.get('framework','?')} / {stack.get('database','?')}")
        print(f"      {len(dev_tasks)} dev tasks planned")
    except json.JSONDecodeError:
        result.errors.append("PlannerAgent output không phải JSON hợp lệ")
        result.finished_at = datetime.now().isoformat()
        return result

    # ── Step 3: Dev Pipeline cho từng task ──────────────────────────────────
    dev_tasks = result.plan.get("dev_tasks", [])
    if not dev_tasks:
        result.errors.append("Planner không tạo được dev tasks")
        result.finished_at = datetime.now().isoformat()
        return result

    print(f"\n{'─'*60}")
    print(f"  💻  STEP 3/3 — Dev Pipeline: {len(dev_tasks)} tasks")
    print(f"{'─'*60}")

    if parallel:
        from core.graph.orchestrator import create_master_workflow

        master_workflow = create_master_workflow()
        master_initial_state: dict = {
            "requirement": requirement,
            "pm_spec": result.pm_spec,
            "plan": result.plan,
            "tasks": dev_tasks,
            "results": [],
            "error": None,
            "logs": [f"[Master] Parallel execution starting with {len(dev_tasks)} tasks"],
            "max_attempts": max_attempts,
            "use_docker": use_docker,
        }

        master_final_state = await master_workflow.ainvoke(master_initial_state)

        if master_final_state.get("error"):
            result.errors.append(str(master_final_state["error"]))

        result.task_results = master_final_state.get("results", [])
    else:
        for i, dev_task in enumerate(dev_tasks):
            task_title = dev_task.get('title', '?')
            task_id = dev_task.get('id', '?')
            print(f"\n  [{i+1}/{len(dev_tasks)}] {task_title}  ({task_id})")
            print(f"  {dev_task.get('description', '')[:100]}")
            print(f"  {'─'*50}")

            task_result = await _run_dev_task(dev_task, max_attempts, use_docker)
            result.task_results.append(task_result)

            icon = "✅" if task_result.get("test_result") == "pass" else "❌"
            test_result = task_result.get('test_result', 'unknown')
            fix_count = task_result.get('fix_attempts', 0)
            elapsed = task_result.get('logs', [])[-1] if task_result.get('logs') else ''
            print(f"  {icon}  Done — test: {test_result}  (fix attempts: {fix_count})")

    result.finished_at = datetime.now().isoformat()

    print(f"\n{'='*60}")
    summary_icon = "✅" if result.success else "❌"
    print(f"{summary_icon}  PIPELINE COMPLETE — {result.summary}")
    print(f"   Errors: {len(result.errors)}")
    if result.success:
        print(f"   All tasks passed!")
    print(f"{'='*60}")

    return result


async def _run_dev_task(
    dev_task:     dict,
    max_attempts: int,
    use_docker:   bool,
) -> WorkflowState:
    """Chạy một dev task qua Dev→Review→QA→Fix pipeline."""
    # Kết hợp title + description + implementation_notes thành prompt đầy đủ
    description_parts = [dev_task.get("title", "")]
    if dev_task.get("description"):
        description_parts.append(dev_task["description"])
    if dev_task.get("implementation_notes"):
        description_parts.append(
            f"Implementation notes: {dev_task['implementation_notes']}"
        )

    full_description = "\n\n".join(filter(None, description_parts))

    return await run_task(
        description  = full_description,
        task_id      = dev_task.get("id", "dev-unknown"),
        max_attempts = max_attempts,
        use_docker   = use_docker,
    )


def print_full_result(result: FullPipelineResult) -> None:
    """In kết quả toàn bộ pipeline theo format đẹp."""
    icon = "✅" if result.success else "❌"
    print(f"\n{'='*60}")
    print(f"{icon}  FULL PIPELINE RESULT")
    print(f"{'='*60}")
    print(f"   Requirement : {result.requirement[:80]}")
    print(f"   Summary     : {result.summary}")
    print(f"   Started     : {result.started_at}")
    print(f"   Finished    : {result.finished_at}")

    if result.pm_spec:
        print(f"\n📋 PM SPEC:")
        print(f"   Feature : {result.pm_spec.get('feature_name')}")
        print(f"   Summary : {result.pm_spec.get('one_line_summary')}")
        tasks = result.pm_spec.get("tasks", [])
        for t in tasks:
            print(f"   [{t['id']}] {t['title']}")

    if result.plan:
        stack = result.plan.get("tech_stack", {})
        print(f"\n🏗️  ARCHITECTURE:")
        print(f"   Pattern : {result.plan.get('architecture_pattern')}")
        print(f"   Stack   : {stack.get('framework')} + {stack.get('database')}")
        models = result.plan.get("data_models", [])
        if models:
            print(f"   Models  : {', '.join(m['name'] for m in models)}")

    print(f"\n💻 DEV TASKS ({len(result.task_results)}):")
    for state in result.task_results:
        icon2 = "✅" if state.get("test_result") == "pass" else "❌"
        print(f"   {icon2} [{state.get('task_id')}] "
              f"test={state.get('test_result', 'N/A')} "
              f"attempts={state.get('fix_attempts', 0)}")

    if result.errors:
        print(f"\n⚠️  ERRORS:")
        for err in result.errors:
            print(f"   - {err}")
