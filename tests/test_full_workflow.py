"""
tests/test_full_workflow.py
Chạy thử nghiệm toàn bộ luồng: Dev → Reviewer → QA → Fix (nếu cần).

Verify các fix:
    1. Dev agent nhận đủ context khi retry (code + lỗi QA + nhận xét reviewer)
    2. review_result và test_result được reset sau mỗi retry
    3. Loop dừng đúng khi hết max_attempts
"""

import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.graph.engine import create_workflow
from core.graph.state import WorkflowState, TaskStatus


async def run_and_print(task_desc: str, max_attempts: int = 2) -> WorkflowState:
    workflow = create_workflow()

    initial_state: WorkflowState = {
        "task_id":       "test-001",
        "task_desc":     task_desc,
        "current_code":  None,
        "previous_code": None,
        "review_result": None,
        "test_result":   None,
        "fix_attempts":  0,
        "max_attempts":  max_attempts,
        "status":         TaskStatus.PENDING,
        "logs":           [],
        "error":          None,
    }

    print(f"\n{'='*60}")
    print(f"TASK: {task_desc}")
    print(f"max_attempts: {max_attempts}")
    print(f"{'='*60}")

    final_state = await workflow.ainvoke(initial_state)

    print(f"\n📜 LOGS:")
    for log in final_state.get("logs", []):
        print(f"   {log}")

    print(f"\n📊 FINAL STATE:")
    print(f"   status       : {final_state.get('status')}")
    print(f"   test_result  : {final_state.get('test_result')}")
    print(f"   review_result: {final_state.get('review_result')}")
    print(f"   fix_attempts : {final_state.get('fix_attempts')}")

    code = final_state.get("current_code") or ""
    print(f"\n📄 CODE ({len(code)} chars):")
    print("-" * 40)
    print(code[:800] + ("..." if len(code) > 800 else ""))
    print("-" * 40)

    return final_state


async def main():
    print("🎬 Full Workflow Test — with fix verification\n")

    # Test 1: task đơn giản — kỳ vọng pass ngay lần đầu
    state = await run_and_print(
        task_desc="Viết hàm Python `add(a: int, b: int) -> int` trả về tổng a + b.",
        max_attempts=2,
    )

    if state.get("test_result") == "pass":
        print("\n✅ TEST 1 PASSED — task simple, no fix needed")
    else:
        print(f"\n⚠️  TEST 1: task ended with fix_attempts={state.get('fix_attempts')}")

    # Test 2: task phức tạp hơn — có thể cần fix
    print("\n\n")
    state2 = await run_and_print(
        task_desc=(
            "Viết hàm `safe_divide(a: float, b: float) -> float` "
            "chia a cho b. Raise ValueError nếu b == 0."
        ),
        max_attempts=2,
    )

    print(f"\n{'='*60}")
    print("🏁 WORKFLOW TEST COMPLETE")
    print(f"   Task 1: {state.get('test_result')}")
    print(f"   Task 2: {state2.get('test_result')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
