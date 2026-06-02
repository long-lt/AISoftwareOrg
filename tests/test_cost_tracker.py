"""
Tests for Phase 7 Task 6 — Cost Tracking & Budget System.
"""

from pathlib import Path
import sys

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.cost import BudgetExceededError, CostTracker, estimate_tokens


def test_estimate_tokens_is_stable():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 9) == 3


def test_cost_tracker_records_priced_call():
    tracker = CostTracker(budget_usd=1.0)
    cost = tracker.record(
        task_id="task-1",
        agent="DevAgent",
        model="deepseek/deepseek-v4-flash",
        input_tokens=1000,
        output_tokens=500,
    )

    assert round(cost, 6) == 0.00028
    assert tracker.spent_usd == cost
    assert tracker.calls[0]["total_tokens"] == 1500
    assert tracker.summary()["calls"] == 1


def test_cost_tracker_blocks_budget_overrun():
    tracker = CostTracker(budget_usd=0.0001)

    try:
        tracker.record(
            task_id="task-2",
            agent="DevAgent",
            model="unknown-expensive-model",
            input_tokens=1000,
            output_tokens=1000,
        )
    except BudgetExceededError as exc:
        assert "budget" in str(exc).lower()
        return

    raise AssertionError("Expected BudgetExceededError")


def main():
    print("Running cost tracker tests")
    test_estimate_tokens_is_stable()
    test_cost_tracker_records_priced_call()
    test_cost_tracker_blocks_budget_overrun()
    print("All cost tracker tests passed")


if __name__ == "__main__":
    main()
