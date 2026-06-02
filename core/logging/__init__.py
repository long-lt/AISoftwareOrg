"""
core/logging/__init__.py
Structured logging system for AI Software Org.

Usage:
    from core.logging import AgentLogger, LogLevel

    logger = AgentLogger()                          # file-based default
    await logger.log_action("task-1", "DevAgent", "code_generated", {...}, "success")
    entries = await logger.query(task_id="task-1")
"""

from .agent_logger import AgentLogger, LogEntry, LogLevel, compute_entry_hash

__all__ = [
    "AgentLogger",
    "LogEntry",
    "LogLevel",
    "compute_entry_hash",
]
