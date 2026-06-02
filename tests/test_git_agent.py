"""
Tests for Phase 8 Task 8 — Git Integration.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
import sys

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from agents import GitAgent
from core.graph.state import TaskStatus


def _run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test User"], repo)
    (repo / "README.md").write_text("# test repo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], repo)
    _run(["git", "commit", "-m", "init"], repo)
    return repo


def test_git_agent_creates_branch_and_commit(tmp_path):
    repo = _init_repo(tmp_path)
    agent = GitAgent(repo_path=repo)

    async def run_test():
        branch = await agent.create_branch("task-123")
        commit = await agent.commit_code(
            file_path="generated/task-123.py",
            code="def answer() -> int:\n    return 42\n",
            message="feat: task-123 [AI-generated]",
        )
        return branch, commit

    branch, commit = asyncio.run(run_test())

    assert branch == "ai-agent/task-123"
    assert len(commit) >= 7
    assert (repo / "generated" / "task-123.py").read_text(encoding="utf-8").startswith("def answer")
    assert _run(["git", "branch", "--show-current"], repo) == branch
    assert _run(["git", "log", "-1", "--pretty=%s"], repo) == "feat: task-123 [AI-generated]"


def test_git_agent_rejects_unsafe_file_path(tmp_path):
    repo = _init_repo(tmp_path)
    agent = GitAgent(repo_path=repo)

    async def run_test():
        await agent.commit_code("../escape.py", "bad", "bad")

    try:
        asyncio.run(run_test())
    except ValueError as exc:
        assert "repo" in str(exc).lower()
        return

    raise AssertionError("Expected ValueError for path outside repo")


def test_git_node_commits_passed_workflow_state(tmp_path):
    repo = _init_repo(tmp_path)

    from core.graph.engine import git_node

    state = {
        "task_id": "task-456",
        "task_desc": "Viết hàm answer trả về 42",
        "current_code": "def answer() -> int:\n    return 42\n",
        "previous_code": None,
        "review_result": "approved",
        "test_result": "pass",
        "fix_attempts": 0,
        "max_attempts": 1,
        "status": TaskStatus.DONE,
        "logs": [],
        "error": None,
        "cp_id": None,
        "human_decision": None,
    }

    final_state = asyncio.run(git_node(state, repo_path=repo))

    assert final_state["git_branch"] == "ai-agent/task-456"
    assert final_state["git_commit"]
    assert any("[Git] committed" in log for log in final_state["logs"])
    assert (repo / "generated" / "task-456.py").exists()


def main():
    print("Running git integration tests")
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        test_git_agent_creates_branch_and_commit(Path(tmp))
    with TemporaryDirectory() as tmp:
        test_git_agent_rejects_unsafe_file_path(Path(tmp))
    with TemporaryDirectory() as tmp:
        test_git_node_commits_passed_workflow_state(Path(tmp))
    print("All git integration tests passed")


if __name__ == "__main__":
    main()
