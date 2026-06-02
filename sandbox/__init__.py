"""
sandbox/__init__.py
Public API cho sandbox module.

Cách dùng:
    from sandbox import AioSandbox, get_sandbox

    # Production (Docker required — default)
    async with AioSandbox() as sb:
        result = await sb.run_python("print('hello from container')")

    # Development only — explicit opt-in, no isolation
    async with LocalSandbox() as sb:
        result = await sb.run_command("python3 -c 'print(42)'")
"""

import logging
import os
import uuid
import warnings

from .aio_sandbox import AioSandbox, DockerNotAvailableError
from .local_sandbox import LocalSandbox, FlutterSandbox
from .sandbox import CommandResult, Sandbox

logger = logging.getLogger(__name__)


def get_sandbox(use_docker: bool | None = None, **kwargs) -> Sandbox:
    """Factory: trả về sandbox phù hợp với môi trường.

    Args:
        use_docker:
            - None (default) → auto-detect Docker, fail hard if not available
            - True → AioSandbox (Docker), raise DockerNotAvailableError if unavailable
            - False → LocalSandbox (⚠️ no isolation, dev only)
        **kwargs: Forwarded to the sandbox constructor.

    Returns:
        A Sandbox instance ready to use as async context manager.

    Raises:
        RuntimeError: If use_docker=False and ALLOW_LOCAL_SANDBOX is not "true".
    """
    # Enforce production safety: disallow LocalSandbox unless explicitly allowed
    if use_docker is False and os.getenv("ALLOW_LOCAL_SANDBOX", "false").lower() != "true":
        raise RuntimeError(
            "LocalSandbox is disabled in production. "
            "Set ALLOW_LOCAL_SANDBOX=true to enable for development."
        )

    sandbox_id = kwargs.pop("sandbox_id", str(uuid.uuid4())[:8])

    if use_docker is None:
        use_docker = True

    if use_docker:
        return AioSandbox(sandbox_id=sandbox_id, **kwargs)

    warnings.warn(
        "LocalSandbox: code chạy trực tiếp trên HOST — không có isolation.\n"
        "  Dùng Docker sandbox cho production:\n"
        "    get_sandbox(use_docker=True)  hoặc  AioSandbox()",
        RuntimeWarning,
        stacklevel=2,
    )
    logger.warning("LocalSandbox được dùng — KHÔNG AN TOÀN cho production")
    return LocalSandbox(sandbox_id=sandbox_id, **kwargs)



__all__ = [
    "Sandbox",
    "CommandResult",
    "LocalSandbox",
    "FlutterSandbox",
    "AioSandbox",
    "DockerNotAvailableError",
    "get_sandbox",
]
