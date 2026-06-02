"""
End-to-end pipeline test with mocked LLM clients.

This verifies Dev -> Reviewer -> QA workflow behavior without calling a real
LLM API, so the test can run in CI without credentials or network access.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from tests.fixtures.mock_llm import create_mock_client


DEV_RESPONSES = {
    "mock_add_numbers": (
        "def mock_add_numbers(a: int, b: int) -> int:\n"
        "    \"\"\"Return the sum of two integers.\"\"\"\n"
        "    if not isinstance(a, int) or not isinstance(b, int):\n"
        "        raise ValueError(\"a and b must be integers\")\n"
        "    return a + b\n"
    ),
}

REVIEWER_RESPONSES = {
    "mock_add_numbers": "APPROVED: Code is correct, typed, and validates inputs.",
}

QA_RESPONSES = {
    "mock_add_numbers": (
        "assert mock_add_numbers(2, 3) == 5, \"Expected 2 + 3 to equal 5\"\n"
        "assert mock_add_numbers(-1, 1) == 0, \"Expected -1 + 1 to equal 0\"\n"
        "try:\n"
        "    mock_add_numbers(\"2\", 3)\n"
        "except ValueError:\n"
        "    pass\n"
        "else:\n"
        "    raise AssertionError(\"Expected ValueError for non-integer input\")\n"
        "print(\"QA_RESULT: PASS\")\n"
    ),
}


class NoopMemoryManager:
    async def get_relevant_context(self, current_task_desc: str, limit: int = 3) -> str:
        return ""

    async def record_task_outcome(self, **kwargs) -> None:
        return None


class NoopAgentLogger:
    async def log_workflow_state(self, state) -> None:
        return None


class NoopApprovalQueue:
    def submit(self, experience):
        return {"id": "mock-approval"}


class NoopExperienceExtractor:
    def extract(self, state):
        return None


def _install_mocks() -> None:
    import agents.software_org.dev_agent as dev_agent
    import agents.software_org.qa_agent as qa_agent
    import agents.software_org.reviewer_agent as reviewer_agent
    import core.graph.engine as engine
    import workflows.dev_pipeline as dev_pipeline

    dev_agent.create_llm_client = lambda model=None: create_mock_client(DEV_RESPONSES)
    reviewer_agent.create_llm_client = lambda model=None: create_mock_client(REVIEWER_RESPONSES)
    qa_agent.create_llm_client = lambda model=None: create_mock_client(QA_RESPONSES)

    engine.memory_manager = NoopMemoryManager()
    dev_pipeline.memory_manager = NoopMemoryManager()
    dev_pipeline.agent_logger = NoopAgentLogger()
    dev_pipeline.experience_extractor = NoopExperienceExtractor()
    dev_pipeline.approval_queue = NoopApprovalQueue()


async def test_pipeline_with_mock_llm() -> None:
    os.environ["ALLOW_LOCAL_SANDBOX"] = "true"
    _install_mocks()

    from workflows.dev_pipeline import run_task
    from core.graph.state import TaskStatus

    state = await run_task(
        "Viết hàm Python mock_add_numbers(a: int, b: int) -> int trả về tổng a + b.",
        task_id="mock-e2e-001",
        max_attempts=1,
        use_docker=False,
    )

    assert state["status"] == TaskStatus.DONE
    assert state["test_result"] == "pass"
    assert state["review_result"].startswith("approved")
    assert state["fix_attempts"] == 0
    assert "def mock_add_numbers" in (state["current_code"] or "")
    assert any("[Dev]" in log for log in state["logs"])
    assert any("[Reviewer]" in log for log in state["logs"])
    assert any("[QA] pass" in log for log in state["logs"])


def main() -> None:
    print("Running mocked pipeline E2E test")
    asyncio.run(test_pipeline_with_mock_llm())
    print("✅ Mock LLM pipeline test passed")


if __name__ == "__main__":
    main()
