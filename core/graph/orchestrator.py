"""
core/graph/orchestrator.py
Master Orchestrator — Điều phối PM -> Planner -> Parallel Dev Tasks (Phase 5).

Sử dụng cơ chế Send của LangGraph để fan-out các dev tasks.
"""

import json
from typing import Any, List
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from .state import MasterWorkflowState, TaskStatus, WorkflowState
from .engine import create_workflow
from agents import AgentTask, PMAgent, PlannerAgent


# ---------------------------------------------------------------------------
# Master Nodes
# ---------------------------------------------------------------------------

async def pm_node(state: MasterWorkflowState) -> MasterWorkflowState:
    """PM Agent viết spec. Skip nếu đã có pm_spec (pre-computed từ full_pipeline)."""
    if state.get("pm_spec") is not None:
        return state

    agent = PMAgent()
    task = AgentTask(id="pm-master", description=state["requirement"])
    result = await agent.run(task)

    if not result.success:
        return {**state, "error": f"PM Failed: {result.reason}", "logs": state["logs"] + ["[PM] Failed"]}

    try:
        spec = json.loads(result.output)
        return {
            **state,
            "pm_spec": spec,
            "logs": state["logs"] + [f"[PM] Spec created: {spec.get('feature_name')}"]
        }
    except json.JSONDecodeError:
        return {**state, "error": "PM output invalid JSON", "logs": state["logs"] + ["[PM] JSON Error"]}


async def planner_node(state: MasterWorkflowState) -> MasterWorkflowState:
    """Planner Agent thiết kế architecture và chia nhỏ tasks. Skip nếu đã có plan."""
    if state.get("error"):
        return state
    if state.get("plan") is not None:
        return state

    agent = PlannerAgent()
    context = json.dumps(state["pm_spec"])
    task = AgentTask(id="planner-master", description=state["requirement"], context=context)
    result = await agent.run(task)

    if not result.success:
        return {**state, "error": f"Planner Failed: {result.reason}", "logs": state["logs"] + ["[Planner] Failed"]}

    try:
        plan = json.loads(result.output)
        tasks = plan.get("dev_tasks", [])
        return {
            **state,
            "plan": plan,
            "tasks": tasks,
            "logs": state["logs"] + [f"[Planner] Plan created: {len(tasks)} tasks"]
        }
    except json.JSONDecodeError:
        return {**state, "error": "Planner output invalid JSON", "logs": state["logs"] + ["[Planner] JSON Error"]}


async def sub_task_wrapper(state: dict) -> dict:
    """Node này chạy một dev_pipeline cho một sub-task.

    Nó nhận input là một dev_task dict (từ Send).
    Nếu workflow crash, trả về failed state thay vì propagate exception.
    """
    dev_task = state["task"]
    max_attempts = state.get("max_attempts", 3)
    use_docker = state.get("use_docker", False)

    # Chuẩn bị description từ task dict
    desc = f"{dev_task.get('title', '')}\n\n{dev_task.get('description', '')}"
    if dev_task.get("implementation_notes"):
        desc += f"\n\nNotes: {dev_task['implementation_notes']}"

    task_id = dev_task.get("id", "sub-task")

    # Chạy dev_pipeline trực tiếp qua graph engine
    workflow = create_workflow(use_docker=use_docker)
    initial_sub_state = {
        "task_id": task_id,
        "task_desc": desc,
        "max_attempts": max_attempts,
        "fix_attempts": 0,
        "status": TaskStatus.FIXING,  # Bắt đầu từ checkpoint/fixing
        "logs": [],
    }

    try:
        final_state = await workflow.ainvoke(initial_sub_state)
    except Exception as exc:
        # Workflow crash → trả về failed state để master graph không crash theo
        final_state = {
            **initial_sub_state,
            "status": TaskStatus.FAILED,
            "error": f"Sub-task crashed: {exc}",
            "test_result": f"fail: {exc}",
            "logs": initial_sub_state["logs"] + [f"[Sub-task] CRASHED: {exc}"],
        }

    # Trả về kết quả để master graph tổng hợp vào 'results'
    return {"results": [final_state]}


# ---------------------------------------------------------------------------
# Routing Logic
# ---------------------------------------------------------------------------

def spawn_parallel_tasks(state: MasterWorkflowState):
    """Conditional edge: Fan-out sang nhiều sub_task_wrapper nodes."""
    if state.get("error"):
        return "error_log"
    if not state.get("tasks"):
        return END

    return [
        Send("run_sub_task", {
            "task": t,
            "max_attempts": state.get("max_attempts", 3),
            "use_docker": state.get("use_docker", False),
        })
        for t in state["tasks"]
    ]


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

def create_master_workflow():
    """Tạo orchestrator graph.

    Flow:
        pm → planner → [parallel sub-tasks] → END
              └─(error)──→ error_log → END
    """
    builder = StateGraph(MasterWorkflowState)

    async def error_log_node(state: MasterWorkflowState) -> MasterWorkflowState:
        """Log error trước khi kết thúc."""
        error = state.get("error", "unknown error")
        return {**state, "logs": state["logs"] + [f"[Master] ERROR: {error}"]}

    builder.add_node("pm", pm_node)
    builder.add_node("planner", planner_node)
    builder.add_node("run_sub_task", sub_task_wrapper)
    builder.add_node("error_log", error_log_node)

    builder.set_entry_point("pm")
    builder.add_conditional_edges(
        "pm",
        lambda s: "error_log" if s.get("error") else "planner",
        {"planner": "planner", "error_log": "error_log"},
    )
    builder.add_edge("error_log", END)

    # Fan-out: Planner -> parallel sub-tasks (or error_log on failure)
    builder.add_conditional_edges(
        "planner",
        spawn_parallel_tasks,
        {"run_sub_task": "run_sub_task", "error_log": "error_log", END: END},
    )

    # Các sub-tasks sau khi xong sẽ tự động hội tụ (join)
    # vì kết quả của chúng đều ghi vào 'results' (Annotated[list, add])
    builder.add_edge("run_sub_task", END)

    return builder.compile()
