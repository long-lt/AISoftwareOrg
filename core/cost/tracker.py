"""
Track LLM token usage, USD cost, and budget limits.

Costs are estimated when provider usage metadata is unavailable. Pricing values
are USD per 1K tokens.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


MODEL_PRICING: dict[str, dict[str, float]] = {
    "deepseek/deepseek-v4-flash": {"input": 0.00014, "output": 0.00028},
    "nvidia/nemotron-3-super-120b-a12b:free": {"input": 0.0, "output": 0.0},
    "openai/gpt-oss-120b:free": {"input": 0.0, "output": 0.0},
}

DEFAULT_PRICING = {"input": 0.001, "output": 0.002}


class BudgetExceededError(RuntimeError):
    """Raised when a cost record would exceed the configured budget."""


def estimate_tokens(text: str) -> int:
    """Rough token estimate for providers that omit usage metadata."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _usage_value(usage: Any, name: str) -> int | None:
    if usage is None:
        return None
    if isinstance(usage, dict):
        value = usage.get(name)
    else:
        value = getattr(usage, name, None)
    return int(value) if value is not None else None


@dataclass
class CostTracker:
    """In-memory cost tracker with a hard budget guard."""

    budget_usd: float = 1.0
    spent_usd: float = 0.0
    calls: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        task_id: str,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Record one LLM call and return its USD cost."""
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        cost = (
            input_tokens / 1000 * pricing["input"]
            + output_tokens / 1000 * pricing["output"]
        )

        if self.spent_usd + cost > self.budget_usd:
            raise BudgetExceededError(
                f"LLM budget exceeded: ${self.spent_usd + cost:.6f} / ${self.budget_usd:.2f}"
            )

        self.spent_usd += cost
        self.calls.append(
            {
                "task_id": task_id,
                "agent": agent,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": cost,
            }
        )
        return cost

    def summary(self) -> dict[str, Any]:
        """Return current aggregate cost state."""
        total_tokens = sum(call["total_tokens"] for call in self.calls)
        return {
            "budget_usd": self.budget_usd,
            "spent_usd": self.spent_usd,
            "remaining_usd": max(0.0, self.budget_usd - self.spent_usd),
            "calls": len(self.calls),
            "total_tokens": total_tokens,
        }


def _budget_from_env() -> float:
    raw = os.getenv("LLM_BUDGET_USD", "1.0")
    try:
        return float(raw)
    except ValueError:
        return 1.0


global_cost_tracker = CostTracker(budget_usd=_budget_from_env())


async def record_llm_usage(
    task_id: str,
    agent: str,
    model: str,
    prompt: str,
    response: Any,
    tracker: CostTracker | None = None,
) -> dict[str, Any]:
    """Record and log usage for one LLM response."""
    usage = getattr(response, "usage", None)
    output_text = ""
    try:
        output_text = response.choices[0].message.content or ""
    except (AttributeError, IndexError, TypeError):
        output_text = ""

    input_tokens = _usage_value(usage, "prompt_tokens")
    output_tokens = _usage_value(usage, "completion_tokens")
    if input_tokens is None:
        input_tokens = estimate_tokens(prompt)
    if output_tokens is None:
        output_tokens = estimate_tokens(output_text)

    active_tracker = tracker or global_cost_tracker
    cost = active_tracker.record(
        task_id=task_id,
        agent=agent,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    payload = active_tracker.calls[-1]

    from core.logging import AgentLogger

    await AgentLogger(echo=False).log_action(
        task_id=task_id,
        agent=agent,
        action="llm_cost",
        details=payload,
        status="success",
    )
    return {**payload, "cost_usd": cost}
