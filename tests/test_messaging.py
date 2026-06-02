"""
Tests for Phase 8 Task 9 — Inter-Agent Communication.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.messaging import AgentMessage, MessageBus
from core.graph.state import TaskStatus


def test_message_bus_send_receive():
    async def run_test():
        bus = MessageBus()
        sent = await bus.send(
            AgentMessage(
                from_agent="DevAgent",
                to_agent="ReviewerAgent",
                content="Need clarification",
            )
        )
        received = await bus.receive("ReviewerAgent", timeout=0.1)
        return sent, received

    sent, received = asyncio.run(run_test())

    assert received is not None
    assert received.id == sent.id
    assert received.from_agent == "DevAgent"
    assert received.to_agent == "ReviewerAgent"
    assert received.content == "Need clarification"


def test_message_bus_timeout_returns_none():
    async def run_test():
        bus = MessageBus()
        return await bus.receive("DevAgent", timeout=0.01)

    assert asyncio.run(run_test()) is None


def test_message_bus_isolates_messages_by_task_scope():
    async def run_test():
        bus = MessageBus()
        task_a = await bus.send(
            AgentMessage(
                from_agent="DevAgent",
                to_agent="ReviewerAgent",
                content="task-a message",
                task_id="task-a",
            )
        )
        task_b = await bus.send(
            AgentMessage(
                from_agent="DevAgent",
                to_agent="ReviewerAgent",
                content="task-b message",
                task_id="task-b",
            )
        )

        received_b = await bus.receive("ReviewerAgent", timeout=0.1, task_id="task-b")
        received_a = await bus.receive("ReviewerAgent", timeout=0.1, task_id="task-a")
        global_message = await bus.receive("ReviewerAgent", timeout=0.01)
        return task_a, task_b, received_a, received_b, global_message

    task_a, task_b, received_a, received_b, global_message = asyncio.run(run_test())

    assert received_a is not None
    assert received_b is not None
    assert received_a.id == task_a.id
    assert received_b.id == task_b.id
    assert received_a.task_id == "task-a"
    assert received_b.task_id == "task-b"
    assert global_message is None


def test_message_bus_isolates_messages_by_workflow_scope():
    async def run_test():
        bus = MessageBus()
        await bus.send(
            AgentMessage(
                from_agent="PlannerAgent",
                to_agent="DevAgent",
                content="workflow-1 task",
                workflow_id="workflow-1",
            )
        )
        await bus.send(
            AgentMessage(
                from_agent="PlannerAgent",
                to_agent="DevAgent",
                content="workflow-2 task",
                workflow_id="workflow-2",
            )
        )

        workflow_2 = await bus.receive("DevAgent", timeout=0.1, workflow_id="workflow-2")
        workflow_1 = await bus.receive("DevAgent", timeout=0.1, workflow_id="workflow-1")
        return workflow_1, workflow_2

    workflow_1, workflow_2 = asyncio.run(run_test())

    assert workflow_1 is not None
    assert workflow_2 is not None
    assert workflow_1.content == "workflow-1 task"
    assert workflow_2.content == "workflow-2 task"


def test_dev_reviewer_clarification_node_logs_exchange():
    from core.graph.engine import reviewer_clarification_node

    state = {
        "task_id": "msg-001",
        "task_desc": "Viết hàm add",
        "current_code": "def add(a, b):\n    return a - b\n",
        "previous_code": None,
        "review_result": "rejected: wrong operator",
        "test_result": "fail: Expected 5, got -1",
        "fix_attempts": 1,
        "max_attempts": 3,
        "status": TaskStatus.FIXING,
        "logs": [],
        "error": None,
        "cp_id": None,
        "human_decision": None,
        "git_branch": None,
        "git_commit": None,
    }

    final_state = asyncio.run(reviewer_clarification_node(state))

    assert final_state["reviewer_feedback"]
    assert "wrong operator" in final_state["reviewer_feedback"]
    assert any("[Dev→Reviewer] clarification request" in log for log in final_state["logs"])
    assert any("[Reviewer→Dev] feedback" in log for log in final_state["logs"])


def main():
    print("Running messaging tests")
    test_message_bus_send_receive()
    test_message_bus_timeout_returns_none()
    test_message_bus_isolates_messages_by_task_scope()
    test_message_bus_isolates_messages_by_workflow_scope()
    test_dev_reviewer_clarification_node_logs_exchange()
    print("All messaging tests passed")


if __name__ == "__main__":
    main()
