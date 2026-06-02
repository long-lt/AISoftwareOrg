"""
sandbox/aio_sandbox.py
AioSandbox: Docker-based isolated sandbox — dùng cho production.

Mỗi task chạy trong một container Docker riêng biệt:
- Không có internet (network_mode: none)
- Giới hạn RAM và CPU
- File system bị cô lập
- Container tự xóa sau khi xong (--rm)
"""

import asyncio
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from .sandbox import CommandResult, Sandbox


class DockerNotAvailableError(RuntimeError):
    """Raised when Docker daemon is not reachable."""
    pass


class AioSandbox(Sandbox):
    """Docker-based sandbox with full isolation.

    Mỗi lần gọi run_command, code được mount vào container
    Python:3.11-slim và chạy trong môi trường hoàn toàn cô lập.

    Resources:
        - RAM: 512MB (configurable)
        - CPU: 1 core (configurable)
        - Network: disabled (network_mode=none)
        - Auto-cleanup: container bị xóa sau khi chạy xong

    Usage:
        async with AioSandbox() as sb:
            result = await sb.run_command("python3 script.py")
            print(result.output)
    """

    DEFAULT_IMAGE = "python:3.11-slim"
    DEFAULT_MEM_LIMIT = "512m"
    DEFAULT_CPU_LIMIT = "1.0"

    def __init__(
        self,
        sandbox_id: Optional[str] = None,
        image: str = DEFAULT_IMAGE,
        mem_limit: str = DEFAULT_MEM_LIMIT,
        cpu_limit: str = DEFAULT_CPU_LIMIT,
        network_disabled: bool = True,
        read_only: bool = True,
    ):
        super().__init__(sandbox_id or str(uuid.uuid4())[:8])
        self.image = image
        self.mem_limit = mem_limit
        self.cpu_limit = cpu_limit
        self.network_disabled = network_disabled
        self.read_only = read_only
        self._files: dict[str, str] = {}   # path → content, để mount vào container
        self._workdir = Path(tempfile.mkdtemp(prefix=f"aiorg-sandbox-{sandbox_id or 'anon'}_"))
        self._owns_workdir = True

    async def _check_docker(self) -> None:
        """Verify Docker daemon is running."""
        proc = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise DockerNotAvailableError(
                "Docker daemon is not running. "
                "Start Docker Desktop or run: sudo systemctl start docker"
            )

    async def run_command(self, command: str, timeout: int = 60) -> CommandResult:
        """Run command inside an isolated Docker container.

        Args:
            command: Shell command to run inside the container. Must pass sanitization.
            timeout: Timeout in seconds (default 60).

        Returns:
            CommandResult with stdout, stderr, exit_code.

        Raises:
            ValueError: If command contains unsafe patterns.
        """
        self.sanitize_command(command)
        await self._check_docker()
        self._flush_staged_files()

        # Build docker run command
        docker_cmd = [
            "docker", "run",
            "--rm",                               # Auto-remove container
            "--name", f"aiorg-sandbox-{self._id}-{uuid.uuid4().hex[:6]}",
            "--memory", self.mem_limit,           # RAM limit
            "--cpus", self.cpu_limit,             # CPU limit
            "-v", f"{self._workdir}:/workspace:rw",
            "--workdir", "/workspace",
        ]

        # Read-only filesystem for security (except /workspace and /tmp)
        if self.read_only:
            docker_cmd += ["--read-only", "--tmpfs", "/tmp"]

        # Disable network for security
        if self.network_disabled:
            docker_cmd += ["--network", "none"]

        docker_cmd += [self.image, "/bin/sh", "-c", command]

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
                stderr=f"Container timed out after {timeout}s",
                exit_code=-1,
                success=False,
            )

    async def run_python(self, code: str, timeout: int = 60) -> CommandResult:
        """Convenience: write code to /workspace/main.py and run it.

        Args:
            code: Python source code to execute.
            timeout: Timeout in seconds.

        Returns:
            CommandResult with execution output.
        """
        await self.write_file("main.py", code)
        return await self.run_command("python3 /workspace/main.py", timeout=timeout)

    async def write_file(self, path: str, content: str) -> None:
        """Stage a file to be written to the workdir before next run_command."""
        self._files[path] = content

    async def read_file(self, path: str) -> str:
        """Read a file from the sandbox workdir (host filesystem)."""
        target = Path(path) if Path(path).is_absolute() else self._workdir / path
        if not target.exists():
            raise FileNotFoundError(f"File '{path}' not found in sandbox workdir.")
        return target.read_text(encoding="utf-8")

    async def cleanup(self) -> None:
        """Remove the temporary workdir."""
        self._files.clear()
        if self._owns_workdir and self._workdir.exists():
            shutil.rmtree(str(self._workdir), ignore_errors=True)
            self._owns_workdir = False

    def _flush_staged_files(self) -> None:
        """Write all staged files to the workdir so Docker can volume-mount them."""
        for path, content in self._files.items():
            target = self._workdir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        self._files.clear()

    @classmethod
    async def is_docker_available(cls) -> bool:
        """Check if Docker daemon is reachable."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return proc.returncode == 0
        except FileNotFoundError:
            return False
