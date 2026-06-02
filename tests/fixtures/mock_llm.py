"""
Mock LLM client for pipeline tests.

The fake client matches the last chat message against configured keywords and
returns a response shaped like OpenAI's chat completion object. It lets tests
exercise agent and workflow logic without network access or API keys.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


def create_mock_client(responses: dict[str, str]):
    """Create an AsyncOpenAI-compatible mock client.

    Args:
        responses: Mapping of prompt keyword to completion content. The first
            keyword found in the prompt wins.

    Raises:
        AssertionError: If no configured keyword matches the prompt.
    """

    async def fake_create(**kwargs):
        messages = kwargs.get("messages") or [{}]
        prompt = messages[-1].get("content", "")

        for keyword, response in responses.items():
            if keyword.lower() in prompt.lower():
                message = SimpleNamespace(content=response)
                choice = SimpleNamespace(message=message)
                return SimpleNamespace(choices=[choice])

        raise AssertionError(f"No mock LLM response for prompt: {prompt[:200]}")

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_create)
    return client
