"""
sandbox/local_sandbox.py
LocalSandbox: chạy lệnh trực tiếp trên máy local — dùng cho dev/debug.
FlutterSandbox: LocalSandbox với whitelist riêng cho Flutter pipeline.

Không có Docker isolation — KHÔNG dùng trên production.
Phù hợp để test nhanh khi đang phát triển.
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

from .sandbox import CommandResult, Sandbox

# Patterns blocked in FlutterSandbox (allows pipe | for Flutter commands)
_FLUTTER_UNSAFE_PATTERNS = [
    "$(",      # Command substitution
    "`",       # Backtick command substitution
    "&&",      # Command chaining
    "||",      # OR chaining
    ";",       # Command separator
    "\n",      # Newline (command injection)
    "\r",      # Carriage return
]


class LocalSandbox(Sandbox):
    """Runs commands directly on the local machine.

    ⚠️  WARNING: No isolation — code runs with full host permissions.
    Use ONLY during local development and testing.
    Use AioSandbox (Docker) for production.
    """

    def __init__(self, sandbox_id: str, workdir: str | None = None):
        super().__init__(sandbox_id)
        if workdir:
            self._workdir = Path(workdir)
            self._workdir.mkdir(parents=True, exist_ok=True)
            self._owns_workdir = False
        else:
            self._workdir = Path(tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id}_"))
            self._owns_workdir = True

    @property
    def workdir(self) -> str:
        return str(self._workdir)

    async def run_command(self, command: str, timeout: int = 60) -> CommandResult:
        """Run shell command in sandbox workdir.

        Args:
            command: Shell command to execute. Must pass sanitization.
            timeout: Timeout in seconds (default 60).

        Returns:
            CommandResult with stdout, stderr, exit_code.

        Raises:
            ValueError: If command contains unsafe patterns.
        """
        self.sanitize_command(command)
        shell = self._get_shell()
        try:
            proc = await asyncio.create_subprocess_exec(
                shell, "-c", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._workdir),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            exit_code = proc.returncode or 0
            return CommandResult(
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=exit_code,
                success=(exit_code == 0),
            )
        except asyncio.TimeoutError:
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                exit_code=-1,
                success=False,
            )

    async def write_file(self, path: str, content: str) -> None:
        """Write a file inside the sandbox workdir."""
        # If relative path, put it inside workdir; if absolute, use as-is
        target = Path(path) if Path(path).is_absolute() else self._workdir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    async def read_file(self, path: str) -> str:
        """Read a file from inside the sandbox workdir."""
        target = Path(path) if Path(path).is_absolute() else self._workdir / path
        return target.read_text(encoding="utf-8")

    async def cleanup(self) -> None:
        """Remove the temporary workdir (if we created it)."""
        if self._owns_workdir and self._workdir.exists():
            shutil.rmtree(str(self._workdir), ignore_errors=True)

    @staticmethod
    def _get_shell() -> str:
        """Detect available shell executable."""
        for shell in ("/bin/zsh", "/bin/bash", "/bin/sh"):
            if os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        found = shutil.which("sh")
        if found:
            return found
        raise RuntimeError("No suitable shell found (zsh/bash/sh).")


class FlutterSandbox(LocalSandbox):
    """LocalSandbox với whitelist riêng cho Flutter pipeline.

    Cho phép pipe (|) để dùng flutter commands kết hợp grep, tail, etc.
    Vẫn chặn các pattern nguy hiểm khác (command substitution, chaining).

    Phù hợp cho QA Agent, Runtime Agent chạy flutter analyze/test/build.
    """

    @staticmethod
    def sanitize_command(command: str) -> str:
        """Sanitize command — cho phép pipe nhưng chặn pattern nguy hiểm."""
        for pattern in _FLUTTER_UNSAFE_PATTERNS:
            if pattern in command:
                raise ValueError(
                    f"Unsafe command pattern detected: {pattern!r} "
                    f"in command: {command[:50]}..."
                )
        return command
