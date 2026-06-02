"""
workflows/dev_pipeline.py
Entry point chính để chạy một task qua toàn bộ pipeline:
    Dev → Reviewer → QA → Fix (loop)

Usage đơn giản nhất:
    from workflows.dev_pipeline import run_task
    result = asyncio.run(run_task("Viết API GET /users trả về danh sách users"))
"""

import uuid
import asyncio
from datetime import datetime
from typing import Optional

from core.graph.engine import create_workflow
from core.graph.state import WorkflowState, TaskStatus
from memory import MemoryManager
from core.logging import AgentLogger
from system.learning import ExperienceExtractor, ApprovalQueue


# Khởi tạo MemoryManager, AgentLogger, và ApprovalQueue
memory_manager = MemoryManager()
agent_logger = AgentLogger(echo=False)
experience_extractor = ExperienceExtractor()
approval_queue = ApprovalQueue()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_task(
    description: str,
    task_id: Optional[str] = None,
    max_attempts: int = 3,
    use_docker: bool = False,
    enable_git: bool | None = None,
) -> WorkflowState:
    """Chạy một task qua pipeline Dev → Reviewer → QA → Fix.

    Args:
        description:  Mô tả task rõ ràng.
        task_id:      ID duy nhất. Auto-generate nếu không truyền.
        max_attempts: Số lần tối đa fix lỗi trước khi dừng. Default 3.
        use_docker:   True = Docker sandbox. False = local sandbox (dev/test).

    Returns:
        WorkflowState cuối cùng.
        → state["test_result"] == "pass"  : thành công
        → state["test_result"].startswith("fail") : thất bại
    """
    tid = task_id or str(uuid.uuid4())[:8]
    started_at = datetime.now()

    initial_state: WorkflowState = {
        "task_id":       tid,
        "task_desc":     description.strip(),
        "current_code":  None,
        "previous_code": None,
        "review_result": None,
        "test_result":   None,
        "fix_attempts":  0,
        "max_attempts":  max_attempts,
        "status":        TaskStatus.PENDING,
        "logs":          [f"[Pipeline] task={tid} started={started_at.isoformat()}"],
        "error":         None,
        "cp_id":         None,
        "human_decision": None,
        "git_branch":    None,
        "git_commit":    None,
        "reviewer_feedback": None,
    }

    workflow = create_workflow(use_docker=use_docker, enable_git=enable_git)

    try:
        final_state = await workflow.ainvoke(initial_state)
    except Exception as e:
        return {
            **initial_state,
            "status": TaskStatus.FAILED,
            "error":  str(e),
            "logs":   initial_state["logs"] + [f"[Pipeline] CRASHED: {e}"],
        }

    # Xác định status cuối
    final_status = (
        TaskStatus.DONE
        if final_state.get("test_result") == "pass"
        else TaskStatus.FAILED
    )

    elapsed = (datetime.now() - started_at).total_seconds()

    # Ghi lại kinh nghiệm vào Memory
    await memory_manager.record_task_outcome(
        task_id=final_state["task_id"],
        task_desc=final_state["task_desc"],
        success=(final_status == TaskStatus.DONE),
        output=final_state.get("current_code", ""),
        logs=final_state.get("logs", []),
        fix_attempts=final_state.get("fix_attempts", 0),
        review_result=final_state.get("review_result"),
        test_result=final_state.get("test_result"),
    )

    # Trích xuất experience nếu task phải fix → gửi vào ApprovalQueue chờ duyệt
    experience = experience_extractor.extract(final_state)
    if experience:
        approval_queue.submit(experience)

    # Ghi log kết quả pipeline
    await agent_logger.log_workflow_state(final_state)

    return {
        **final_state,
        "status": final_status,
        "logs": final_state["logs"] + [
            f"[Pipeline] done status={final_status.value} "
            f"elapsed={elapsed:.1f}s attempts={final_state.get('fix_attempts', 0)}"
        ],
    }


def run_task_sync(
    description: str,
    task_id: Optional[str] = None,
    max_attempts: int = 3,
    use_docker: bool = False,
    enable_git: bool | None = None,
) -> WorkflowState:
    """Synchronous wrapper — dùng trong scripts, CLI, và jupyter notebook."""
    return asyncio.run(run_task(description, task_id, max_attempts, use_docker, enable_git))


def print_result(state: WorkflowState) -> None:
    """In kết quả workflow ra terminal theo format dễ đọc."""
    is_done = state.get("test_result") == "pass"
    icon = "✅" if is_done else "❌"
    status = state.get("status", "unknown")
    task_desc = (state.get("task_desc") or "").split("\n")[0][:80]

    print(f"\n{'='*60}")
    print(f"{icon}  TASK: {task_desc}")
    print(f"   ID: {state.get('task_id')}  |  Status: {status}")
    print(f"{'='*60}")
    print(f"   fix_attempts : {state.get('fix_attempts', 0)}/{state.get('max_attempts', 3)}")
    print(f"   test_result  : {state.get('test_result', 'N/A')}")
    print(f"   review_result: {(state.get('review_result') or 'N/A')[:80]}")

    if state.get("error"):
        print(f"\n⚠️  SYSTEM ERROR: {state['error']}")

    if state.get("git_branch"):
        print(f"\nGit: {state.get('git_branch')} @ {state.get('git_commit')}")

    print(f"\n📜 LOGS:")
    for log in state.get("logs", []):
        print(f"   {log}")

    code_body = state.get("current_code") or ""
    if code_body:
        preview = code_body[:800] + ("\n...(truncated)" if len(code_body) > 800 else "")
        print(f"\n📄 FINAL CODE:\n{'-'*40}\n{preview}\n{'-'*40}")
