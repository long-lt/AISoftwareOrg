"""
agents/git_agent.py
Git Agent: create task branches and commit generated code.

This agent never pushes. Pull requests are intentionally a separate critical
operation so workflows can prepare local commits without publishing anything.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from system.rbac import Permission, require_permission

from agents.base import AgentResult, AgentTask, BaseAgent


class GitAgent(BaseAgent):
    """Manage local Git operations for generated task code."""

    def __init__(self, repo_path: str | Path):
        super().__init__(name="GitAgent", role="DevOps Engineer")
        self.repo = Path(repo_path).resolve()

    async def run(self, task: AgentTask) -> AgentResult:
        """Default action for GitAgent."""
        return AgentResult(success=True, output=str(self.repo), reason="GitAgent ready")

    @require_permission(Permission.WRITE)
    async def create_branch(self, task_id: str) -> str:
        """Create and check out an AI task branch."""
        branch = f"ai-agent/{_safe_ref_part(task_id)}"
        current = await self._git("branch", "--show-current")
        if current.strip() == branch:
            return branch

        existing = await self._git("branch", "--list", branch)
        if existing.strip():
            await self._git("checkout", branch)
        else:
            await self._git("checkout", "-b", branch)
        return branch

    @require_permission(Permission.WRITE)
    async def commit_code(self, file_path: str, code: str, message: str) -> str:
        """Write generated code, stage it, and create a local commit."""
        target = self._resolve_repo_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")

        rel_path = target.relative_to(self.repo).as_posix()
        await self._git("add", rel_path)
        await self._git("commit", "-m", message)
        return (await self._git("rev-parse", "--short", "HEAD")).strip()

    @require_permission(Permission.CRITICAL)
    async def create_pr(self, title: str, body: str) -> str:
        """Placeholder for future GitHub PR integration."""
        raise NotImplementedError("PR creation is not implemented in local GitAgent")

    async def _git(self, *args: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(self.repo),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} failed: {stderr.decode('utf-8', errors='replace').strip()}"
            )
        return stdout.decode("utf-8", errors="replace").strip()

    def _resolve_repo_path(self, file_path: str) -> Path:
        target = (self.repo / file_path).resolve()
        try:
            target.relative_to(self.repo)
        except ValueError as exc:
            raise ValueError(f"File path must stay inside repo: {file_path}") from exc
        return target


def _safe_ref_part(value: str) -> str:
    safe = []
    for char in value.strip():
        if char.isalnum() or char in {"-", "_", "."}:
            safe.append(char)
        else:
            safe.append("-")
    result = "".join(safe).strip(".-/")
    return result or "task"
