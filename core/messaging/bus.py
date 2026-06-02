"""
Simple in-memory message bus for inter-agent communication.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class AgentMessage:
    """One message passed between agents."""

    from_agent: str
    to_agent: str
    content: str
    task_id: str | None = None
    workflow_id: str | None = None
    reply_to: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MessageBus:
    """In-memory async message bus keyed by workflow/task scope and receiver."""

    def __init__(self):
        self._queues: dict[tuple[str, str], asyncio.Queue[AgentMessage]] = {}

    @staticmethod
    def _scope_key(
        agent_name: str,
        *,
        task_id: str | None = None,
        workflow_id: str | None = None,
    ) -> tuple[str, str]:
        scope = workflow_id or task_id or "global"
        return scope, agent_name

    async def send(self, message: AgentMessage) -> AgentMessage:
        """Send a message to the receiver queue."""
        key = self._scope_key(
            message.to_agent,
            task_id=message.task_id,
            workflow_id=message.workflow_id,
        )
        queue = self._queues.setdefault(key, asyncio.Queue())
        await queue.put(message)
        return message

    async def receive(
        self,
        agent_name: str,
        timeout: float = 5.0,
        *,
        task_id: str | None = None,
        workflow_id: str | None = None,
    ) -> AgentMessage | None:
        """Receive the next message for an agent, or None on timeout."""
        key = self._scope_key(agent_name, task_id=task_id, workflow_id=workflow_id)
        queue = self._queues.setdefault(key, asyncio.Queue())
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
