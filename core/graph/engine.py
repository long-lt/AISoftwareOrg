"""
core/graph/engine.py
LangGraph workflow engine — Human-in-the-Loop Checkpoint (Task 17).

Graph structure:
    checkpoint → dev → reviewer ──(approved)──→ qa ──(pass)──→ END
                              └──(rejected)──→ fix ──→ checkpoint → dev
                                                      └──(fail+max)──→ END
"""

import asyncio
import logging
import os
from pathlib import Path
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)

from .state import TaskStatus, WorkflowState
from agents import AgentTask, DevAgent, GitAgent, QAAgent, ReviewerAgent
from memory import MemoryManager
from core.messaging import AgentMessage, MessageBus
from core.skills.registry import SkillRegistry
from system.learning.checkpoint_store import CheckpointStore

# Khởi tạo các singleton services
memory_manager = MemoryManager()
skill_registry = SkillRegistry()
checkpoint_store = CheckpointStore()
message_bus = MessageBus()

# Default checkpoint timeout
_DEFAULT_CHECKPOINT_WAIT = 300  # 5 minutes


def _get_checkpoint_max_wait() -> int:
    """Đọc max_wait_seconds từ env hoặc SQLite system_settings."""
    # 1. Env var takes priority
    env_val = os.getenv("CHECKPOINT_MAX_WAIT_SECONDS")
    if env_val:
        try:
            return max(30, int(env_val))
        except ValueError:
            pass

    # 2. SQLite system_settings
    db_path = Path(__file__).resolve().parents[2] / "workspace" / "jobs.sqlite3"
    if db_path.exists():
        import sqlite3
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT value FROM system_settings WHERE key = 'checkpoint_max_wait_seconds'"
                ).fetchone()
                if row and row["value"]:
                    return max(30, int(row["value"]))
        except Exception:
            pass

    return _DEFAULT_CHECKPOINT_WAIT


def needs_human_approval(state: WorkflowState) -> bool:
    """Kiểm tra xem task có cần người duyệt trước khi tiếp tục không.

    Các trường hợp cần duyệt:
        1. task_desc chứa "delete" — nguy hiểm, cần confirm trước khi code
        2. fix_attempts >= 2 — đã fix 2 lần vẫn fail, cần human decision
        3. status == AWAITING_APPROVAL — đã từng bị checkpoint chặn

    Returns:
        True nếu cần chờ người duyệt, False nếu tự động tiếp tục.
    """
    task_desc = (state.get("task_desc") or "").lower()
    fix_attempts = state.get("fix_attempts", 0)

    if any(kw in task_desc for kw in ["delete", "drop ", "xoá", "xóa", "xoa"]):
        return True
    if fix_attempts >= 2:
        return True
    return False


# ---------------------------------------------------------------------------
# Node factories — nhận use_docker để truyền xuống QAAgent
# ---------------------------------------------------------------------------

def _git_enabled(enable_git: bool | None) -> bool:
    if enable_git is not None:
        return enable_git
    return os.getenv("ENABLE_GIT_INTEGRATION", "false").lower() == "true"


async def git_node(
    state: WorkflowState,
    repo_path: str | Path | None = None,
) -> WorkflowState:
    """Commit generated code to a local AI task branch after QA passes."""
    if state.get("test_result") != "pass":
        return state

    code = state.get("current_code") or ""
    if not code.strip():
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error": "Git integration skipped: no generated code to commit",
            "logs": state["logs"] + ["[Git] failed: no generated code"],
        }

    repo = Path(repo_path or os.getenv("REPO_PATH", ".")).resolve()
    agent = GitAgent(repo_path=repo)
    branch = await agent.create_branch(state["task_id"])
    file_path = f"generated/{_safe_filename(state['task_id'])}.py"
    message = f"feat: {state['task_desc'][:50]} [AI-generated]"
    commit = await agent.commit_code(file_path=file_path, code=code, message=message)

    return {
        **state,
        "git_branch": branch,
        "git_commit": commit,
        "logs": state["logs"] + [f"[Git] committed {file_path} to {branch} ({commit})"],
    }


async def reviewer_clarification_node(
    state: WorkflowState,
    bus: MessageBus | None = None,
) -> WorkflowState:
    """Let Dev ask Reviewer for feedback before a retry."""
    if state.get("fix_attempts", 0) <= 0:
        return state

    active_bus = bus or message_bus
    reasons = []
    if state.get("review_result"):
        reasons.append(str(state["review_result"]))
    if state.get("test_result") and state["test_result"] != "pass":
        reasons.append(str(state["test_result"]))

    request_content = (
        "Before retrying, please clarify the highest-priority fix. "
        + " | ".join(reasons)
    )
    request = await active_bus.send(
        AgentMessage(
            from_agent="DevAgent",
            to_agent="ReviewerAgent",
            content=request_content,
            task_id=state["task_id"],
        )
    )

    feedback = _build_reviewer_feedback(state)
    await active_bus.send(
        AgentMessage(
            from_agent="ReviewerAgent",
            to_agent="DevAgent",
            content=feedback,
            task_id=state["task_id"],
            reply_to=request.id,
        )
    )
    reply = await active_bus.receive("DevAgent", timeout=0.1, task_id=state["task_id"])
    feedback_text = reply.content if reply else feedback

    return {
        **state,
        "reviewer_feedback": feedback_text,
        "logs": state["logs"] + [
            f"[Dev→Reviewer] clarification request ({request.id})",
            f"[Reviewer→Dev] feedback: {feedback_text[:120]}",
        ],
    }


def _build_reviewer_feedback(state: WorkflowState) -> str:
    review = state.get("review_result") or ""
    test = state.get("test_result") or ""
    if review.startswith("rejected"):
        return f"Focus on reviewer issue first: {review}"
    if test and test != "pass":
        return f"Focus on failing QA assertion first: {test}"
    return "Retry with the smallest code change that satisfies the original task."


def _safe_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in value)
    return safe.strip(".-/") or "task"


def _make_nodes(use_docker: bool = False, enable_git: bool | None = None):
    """Tạo các node functions với config được inject."""

    async def dev_node(state: WorkflowState) -> WorkflowState:
        """Viết code (lần đầu) hoặc sửa lỗi (retry với đủ context)."""
        agent  = DevAgent()
        attempt = state.get("fix_attempts", 0)

        if attempt == 0:
            # Lần đầu chạy — tìm kiếm kinh nghiệm liên quan từ Memory
            relevant_context = await memory_manager.get_relevant_context(state["task_desc"])

            # Tìm kiếm các Skill hỗ trợ
            skills = skill_registry.get_relevant_skills(state["task_desc"])
            skills_context = skill_registry.format_skills_for_prompt(skills)

            # Gộp lại
            context_parts = []
            if relevant_context:
                context_parts.append(relevant_context)
            if skills_context:
                context_parts.append(skills_context)

            context = "\n\n".join(context_parts) if context_parts else None
        else:
            parts = []
            if state.get("current_code"):
                parts.append(f"CODE HIỆN TẠI (cần sửa):\n{state['current_code']}")
            if state.get("reviewer_feedback"):
                parts.append(f"FEEDBACK TỪ REVIEWER:\n{state['reviewer_feedback']}")
            if state.get("test_result") and state["test_result"] != "pass":
                parts.append(f"LỖI TỪ QA:\n{state['test_result']}")
            if state.get("review_result", "").startswith("rejected"):
                parts.append(f"NHẬN XÉT REVIEWER:\n{state['review_result']}")
            context = "\n\n".join(parts) if parts else None

        task   = AgentTask(id=state["task_id"], description=state["task_desc"], context=context)
        result = await agent.run(task)

        log = (
            f"[Dev] attempt={attempt + 1} | "
            + ("code generated" if result.success else f"failed: {result.reason or ''}")
        )
        return {
            **state,
            "current_code":  result.output if result.success else state.get("current_code", ""),
            "review_result": None,   # Reset — reviewer phải xem lại code mới
            "test_result":   None,   # Reset — QA phải test lại
            "status":        TaskStatus.REVIEW,
            "logs":          state["logs"] + [log],
        }

    async def reviewer_node(state: WorkflowState) -> WorkflowState:
        """Đánh giá chất lượng code."""
        agent  = ReviewerAgent()
        task   = AgentTask(id=state["task_id"], description=state["task_desc"],
                           context=state.get("current_code", ""))
        result = await agent.run(task)

        first_line = (result.reason or "").strip().split("\n")[0]
        log = f"[Reviewer] {result.output} | {first_line[:80]}"

        return {
            **state,
            "review_result": result.output,
            "status": TaskStatus.TESTING if result.output.startswith("approved") else TaskStatus.FIXING,
            "logs":   state["logs"] + [log],
        }

    async def qa_node(state: WorkflowState) -> WorkflowState:
        """Sinh test và chạy trong sandbox."""
        agent  = QAAgent(use_docker=use_docker)
        task   = AgentTask(id=state["task_id"], description=state["task_desc"],
                           context=state.get("current_code", ""))
        result = await agent.run(task)

        test_result = result.output or ("pass" if result.success else "fail: unknown")
        is_pass     = test_result == "pass"
        log         = f"[QA] {test_result[:80]}"

        return {
            **state,
            "test_result": test_result,
            "status":      TaskStatus.DONE if is_pass else TaskStatus.FIXING,
            "logs":        state["logs"] + [log],
        }

    async def fix_node(state: WorkflowState) -> WorkflowState:
        """Tăng fix_attempts, log lý do, chuẩn bị cho dev retry."""
        current_code = state.get("current_code")
        new_attempts = state.get("fix_attempts", 0) + 1
        max_attempts = state.get("max_attempts", 3)

        reasons = []
        if (state.get("review_result") or "").startswith("rejected"):
            reasons.append("reviewer rejected")
        if state.get("test_result") and state["test_result"] != "pass":
            reasons.append("qa failed")

        log = f"[Fix] attempt {new_attempts}/{max_attempts} | {' + '.join(reasons) or 'unknown'}"

        return {
            **state,
            "fix_attempts": new_attempts,
            "previous_code": current_code,
            "status":       TaskStatus.FIXING,
            "logs":         state["logs"] + [log],
        }

    async def checkpoint_node(state: WorkflowState) -> WorkflowState:
        """Kiểm tra xem có cần human approval trước khi dev code không.

        Flow:
            1. Gọi needs_human_approval() để kiểm tra
            2. Nếu không cần → pass through (return state)
            3. Nếu cần → tạo checkpoint entry → poll đến khi có quyết định
            4. Approved → tiếp tục (return state với decision fields)
            5. Rejected → set error, return FAILED state
        """
        if not needs_human_approval(state):
            return state

        cp_reason_parts = []
        task_desc = (state.get("task_desc") or "").lower()
        if "delete" in task_desc or "drop " in task_desc:
            cp_reason_parts.append("Dangerous task keyword detected")
        fix_attempts = state.get("fix_attempts", 0)
        if fix_attempts >= 2:
            cp_reason_parts.append(f"High fix attempts ({fix_attempts})")

        reason = "; ".join(cp_reason_parts) or "Human approval required"
        cp_id = checkpoint_store.submit(
            task_id=state["task_id"],
            task_desc=state.get("task_desc", ""),
            reason=reason,
            fix_attempts=fix_attempts,
        )["id"]

        log_msg = f"[Checkpoint] Awaiting human approval: {reason} (id={cp_id})"
        # Set state to awaiting before polling
        state = {
            **state,
            "status": TaskStatus.AWAITING_APPROVAL,
            "cp_id": cp_id,
            "human_decision": None,
            "logs": state["logs"] + [log_msg],
        }

        # Poll checkpoint store with exponential backoff
        max_wait_seconds = _get_checkpoint_max_wait()
        poll_interval = 1.0  # initial seconds
        max_interval = 15.0  # cap
        elapsed = 0.0

        while elapsed < max_wait_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            poll_interval = min(poll_interval * 1.5, max_interval)
            cp = checkpoint_store.get(cp_id)
            if cp is None:
                continue
            if cp["status"] == "approved":
                return {
                    **state,
                    "status": TaskStatus.FIXING,
                    "human_decision": "approved",
                    "logs": state["logs"] + [
                        f"[Checkpoint] Approved by {cp.get('approved_by', 'human')} (id={cp_id})"
                    ],
                }
            if cp["status"] == "rejected":
                reject_reason = cp.get("rejection_reason") or "No reason given"
                return {
                    **state,
                    "status": TaskStatus.FAILED,
                    "error": f"Human rejected: {reject_reason}",
                    "human_decision": "rejected",
                    "logs": state["logs"] + [
                        f"[Checkpoint] Rejected: {reject_reason} (id={cp_id})"
                    ],
                }

        # Timeout — log warning, auto-reject
        logger.warning("[Checkpoint] Timeout after %ds for checkpoint %s (task=%s)",
                       max_wait_seconds, cp_id, state.get("task_id"))
        return {
            **state,
            "status": TaskStatus.FAILED,
            "error": f"Checkpoint timeout: no human response after {max_wait_seconds}s",
            "human_decision": "timeout",
            "logs": state["logs"] + [
                f"[Checkpoint] TIMEOUT after {max_wait_seconds}s (id={cp_id})"
            ],
        }

    async def workflow_git_node(state: WorkflowState) -> WorkflowState:
        """Optional workflow wrapper around Git integration."""
        if not _git_enabled(enable_git):
            return state
        try:
            return await git_node(state)
        except Exception as exc:
            logger.exception("Git integration failed")
            return {
                **state,
                "status": TaskStatus.FAILED,
                "error": f"Git integration failed: {exc}",
                "logs": state["logs"] + [f"[Git] failed: {exc}"],
            }

    return (
        dev_node,
        reviewer_node,
        qa_node,
        fix_node,
        checkpoint_node,
        workflow_git_node,
        reviewer_clarification_node,
    )


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route_after_reviewer(state: WorkflowState) -> str:
    review = (state.get("review_result") or "").strip().lower()
    return "fix" if review.startswith("rejected") else "qa"


def route_after_qa(state: WorkflowState) -> str:
    if state.get("test_result") == "pass":
        return "git"
    if state.get("fix_attempts", 0) >= state.get("max_attempts", 3):
        return END
    return "fix"


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------

def create_workflow(use_docker: bool = False, enable_git: bool | None = None):
    """Tạo và compile workflow với Human-in-the-Loop Checkpoint (Task 17).

    Graph structure:
        checkpoint (entry) → dev → reviewer ──(approved)──→ qa ──(pass)──→ END
                                   └──(rejected)──→ fix → checkpoint → dev (loop)

    Checkpoint node kiểm tra needs_human_approval() trước mỗi lần dev code.
    Nếu cần duyệt, pipeline pause và poll CheckpointStore đến khi human quyết định.

    Args:
        use_docker: Truyền xuống QAAgent. False = LocalSandbox (dev/test),
                    True = Docker sandbox (production).
    """
    (
        dev_node,
        reviewer_node,
        qa_node,
        fix_node,
        checkpoint_node,
        workflow_git_node,
        clarification_node,
    ) = _make_nodes(
        use_docker,
        enable_git,
    )

    graph = StateGraph(WorkflowState)
    graph.add_node("checkpoint", checkpoint_node)
    graph.add_node("dev",        dev_node)
    graph.add_node("reviewer",   reviewer_node)
    graph.add_node("qa",         qa_node)
    graph.add_node("fix",        fix_node)
    graph.add_node("git",        workflow_git_node)
    graph.add_node("clarification", clarification_node)

    graph.set_entry_point("checkpoint")
    graph.add_edge("checkpoint", "dev")
    graph.add_edge("dev", "reviewer")
    graph.add_conditional_edges("reviewer", route_after_reviewer, {"qa": "qa", "fix": "fix"})
    graph.add_conditional_edges("qa", route_after_qa, {"git": "git", "fix": "fix", END: END})
    graph.add_edge("git", END)
    graph.add_edge("fix", "clarification")
    graph.add_edge("clarification", "checkpoint")

    return graph.compile()
