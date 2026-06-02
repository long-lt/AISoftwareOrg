"""
Tests for Phase 7 Task 7 — Multi-LLM Routing.
"""

from pathlib import Path
import asyncio
import os
import sys
from types import SimpleNamespace

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.llm import LLMRouter


def test_router_preserves_default_model_without_tiers():
    router = LLMRouter(default_model="base-model")

    assert router.route("pm") == "base-model"
    assert router.route("dev") == "base-model"
    assert router.route("qa") == "base-model"


def test_router_uses_role_tiers():
    router = LLMRouter(
        default_model="base",
        fast_model="fast-model",
        medium_model="medium-model",
        strong_model="strong-model",
    )

    assert router.route("pm") == "fast-model"
    assert router.route("planner") == "fast-model"
    assert router.route("qa") == "medium-model"
    assert router.route("reviewer") == "medium-model"
    assert router.route("dev", context_length=1000) == "medium-model"
    assert router.route("dev", context_length=5000) == "strong-model"
    assert router.route("dev", is_retry=True) == "strong-model"


def test_router_respects_agent_override():
    router = LLMRouter(
        default_model="base",
        fast_model="fast-model",
        medium_model="medium-model",
        strong_model="strong-model",
        agent_overrides={"dev": "dev-specific"},
    )

    assert router.route("dev", context_length=9000, is_retry=True) == "dev-specific"


def test_router_uses_local_llm_when_enabled():
    router = LLMRouter(
        default_model="base",
        fast_model="fast-model",
        medium_model="medium-model",
        strong_model="strong-model",
        use_local_llm=True,
        ollama_model="codellama:7b",
    )

    assert router.route("pm") == "codellama:7b"
    assert router.base_url() == "http://localhost:11434/v1"


def test_dev_agent_uses_routed_model():
    from agents import AgentTask, DevAgent

    class FakeCompletions:
        def __init__(self):
            self.last_model = None

        async def create(self, **kwargs):
            self.last_model = kwargs["model"]
            message = SimpleNamespace(content="def add(a: int, b: int) -> int:\n    return a + b\n")
            choice = SimpleNamespace(message=message)
            return SimpleNamespace(choices=[choice])

    class FakeClient:
        def __init__(self):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    old_medium = os.environ.get("MEDIUM_LLM_MODEL")
    old_dev = os.environ.get("DEV_MODEL")
    os.environ["MEDIUM_LLM_MODEL"] = "medium-test-model"
    os.environ["DEV_MODEL"] = ""
    try:
        client = FakeClient()
        agent = DevAgent(client=client)
        result = asyncio.run(
            agent.run(AgentTask(id="router-agent-test", description="Viết hàm add"))
        )
    finally:
        if old_medium is None:
            os.environ.pop("MEDIUM_LLM_MODEL", None)
        else:
            os.environ["MEDIUM_LLM_MODEL"] = old_medium
        if old_dev is None:
            os.environ.pop("DEV_MODEL", None)
        else:
            os.environ["DEV_MODEL"] = old_dev

    assert result.success
    assert client.chat.completions.last_model == "medium-test-model"


def main():
    print("Running LLM router tests")
    test_router_preserves_default_model_without_tiers()
    test_router_uses_role_tiers()
    test_router_respects_agent_override()
    test_router_uses_local_llm_when_enabled()
    test_dev_agent_uses_routed_model()
    print("All LLM router tests passed")


if __name__ == "__main__":
    main()
