"""
core/graph/test_graph.py
Test Task 2 — LangGraph State Machine.

Kiểm tra:
1. Import không lỗi
2. create_workflow() biên dịch thành công
3. Workflow chạy được với state hợp lệ
4. Routing logic đúng (pass → END, fail → fix → dev loop)
5. max_attempts dừng loop vô tận

Chạy:
    cd my-ai-org
    source venv/bin/activate
    python core/graph/test_graph.py
"""

import os
import sys
from pathlib import Path

# Ensure project root on path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import asyncio
import pytest


def make_state(
    task_desc: str = "test task",
    test_result: str | None = None,
    review_result: str | None = None,
    fix_attempts: int = 0,
    max_attempts: int = 3,
) -> dict:
    from core.graph.state import TaskStatus
    return {
        "task_id":      "test-001",
        "task_desc":    task_desc,
        "current_code": None,
        "review_result": review_result,
        "test_result":  test_result,
        "fix_attempts": fix_attempts,
        "max_attempts": max_attempts,
        "status":       TaskStatus.PENDING,
        "logs":         [],
        "error":        None,
        "cp_id":        None,
        "human_decision": None,
        "git_branch":   None,
        "git_commit":   None,
        "reviewer_feedback": None,
    }


# ── Test 1: Import ─────────────────────────────────────────────────────────

def test_import():
    print("TEST 1: Import")
    from core.graph.engine import create_workflow, route_after_qa, route_after_reviewer
    from core.graph.state import TaskStatus, WorkflowState
    print("  ✅ from core.graph.engine import create_workflow  OK")
    print("  ✅ from core.graph.state import WorkflowState, TaskStatus  OK")


# ── Test 2: Graph biên dịch thành công ────────────────────────────────────

def test_compile():
    print("TEST 2: Graph compile")
    from core.graph.engine import create_workflow
    workflow = create_workflow()
    assert workflow is not None
    print("  ✅ create_workflow() returned compiled graph")


# ── Test 3: Routing — QA pass → git ───────────────────────────────────────

def test_route_qa_pass():
    print("TEST 3: route_after_qa — pass case")
    from core.graph.engine import route_after_qa
    state = make_state(test_result="pass")
    result = route_after_qa(state)
    assert result == "git", f"Expected 'git', got {result!r}"
    print(f"  ✅ test_result='pass' → {result}")


# ── Test 4: Routing — QA fail + attempts left → fix ───────────────────────

def test_route_qa_fail_with_attempts():
    print("TEST 4: route_after_qa — fail, attempts remaining")
    from core.graph.engine import route_after_qa
    state = make_state(test_result="fail: AssertionError", fix_attempts=1, max_attempts=3)
    result = route_after_qa(state)
    assert result == "fix", f"Expected 'fix', got {result!r}"
    print(f"  ✅ test_result='fail', fix_attempts=1/3 → '{result}'")


# ── Test 5: Routing — QA fail + max_attempts reached → END ───────────────

def test_route_qa_fail_max_attempts():
    print("TEST 5: route_after_qa — fail, max attempts reached")
    from langgraph.graph import END
    from core.graph.engine import route_after_qa
    state = make_state(test_result="fail: still broken", fix_attempts=3, max_attempts=3)
    result = route_after_qa(state)
    assert result == END, f"Expected END, got {result!r}"
    print(f"  ✅ fix_attempts=3/3 → {result} (loop stopped)")


# ── Test 6: Routing — Reviewer approved → qa ──────────────────────────────

def test_route_reviewer_approved():
    print("TEST 6: route_after_reviewer — approved")
    from core.graph.engine import route_after_reviewer
    state = make_state(review_result="approved")
    result = route_after_reviewer(state)
    assert result == "qa", f"Expected 'qa', got {result!r}"
    print(f"  ✅ review_result='approved' → '{result}'")


# ── Test 7: Routing — Reviewer rejected → fix ─────────────────────────────

def test_route_reviewer_rejected():
    print("TEST 7: route_after_reviewer — rejected")
    from core.graph.engine import route_after_reviewer
    state = make_state(review_result="rejected: missing error handling")
    result = route_after_reviewer(state)
    assert result == "fix", f"Expected 'fix', got {result!r}"
    print(f"  ✅ review_result='rejected: ...' → '{result}'")


# ── Test 8: Full workflow run với placeholder nodes ────────────────────────

@pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Full workflow invokes live agents. Use tests/test_pipeline_mock.py for default E2E.",
)
async def test_full_workflow_run():
    print("TEST 8: Full workflow invoke (placeholder nodes)")
    from core.graph.engine import create_workflow
    from core.graph.state import TaskStatus

    workflow = create_workflow()

    # Với placeholder nodes, test_result sẽ là None → route_after_qa → None không phải "pass"
    # fix_attempts=0 < max_attempts=1 → sẽ loop nhưng... placeholder không increment fix_attempts
    # Để test dừng được, đặt max_attempts=1 để sau 1 lần fix → END
    initial_state = make_state(
        task_desc="Viết hello world",
        max_attempts=1,   # Giới hạn thấp để test nhanh, dừng sau 1 vòng
    )

    final_state = await workflow.ainvoke(initial_state)

    # Kiểm tra workflow đã chạy qua các nodes (có logs)
    assert len(final_state["logs"]) > 0, "Không có logs — workflow không chạy"
    print(f"  ✅ Workflow completed. Logs ({len(final_state['logs'])} entries):")
    for log in final_state["logs"]:
        print(f"     → {log}")

    # Kiểm tra state vẫn hợp lệ
    assert "task_id" in final_state
    assert "task_desc" in final_state
    print("  ✅ Final state structure is valid")


# ── Test 9: WorkflowState structure ───────────────────────────────────────

def test_state_structure():
    print("TEST 9: WorkflowState field validation")
    from core.graph.state import TaskStatus, WorkflowState

    state: WorkflowState = make_state()

    required_keys = [
        "task_id", "task_desc", "current_code", "review_result",
        "test_result", "fix_attempts", "max_attempts", "status", "logs", "error"
    ]
    for key in required_keys:
        assert key in state, f"Missing key: {key}"

    assert isinstance(state["logs"], list)
    assert isinstance(state["fix_attempts"], int)
    assert state["status"] == TaskStatus.PENDING
    print(f"  ✅ All {len(required_keys)} required fields present")
    print(f"  ✅ TaskStatus enum values: {[s.value for s in TaskStatus]}")


# ── Runner ─────────────────────────────────────────────────────────────────

async def main():
    print("\n🔬 Running Task 2 — LangGraph State Machine Tests\n")
    print("=" * 55)

    tests_sync = [
        test_import,
        test_compile,
        test_route_qa_pass,
        test_route_qa_fail_with_attempts,
        test_route_qa_fail_max_attempts,
        test_route_reviewer_approved,
        test_route_reviewer_rejected,
        test_state_structure,
    ]

    failed = 0
    for test_fn in tests_sync:
        try:
            test_fn()
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        print()

    # Async test
    try:
        await test_full_workflow_run()
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        failed += 1
    print()

    print("=" * 55)
    if failed == 0:
        print("✅ Task 2 — ALL TESTS PASSED")
        print("   LangGraph State Machine is ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
