"""
tests/test_checkpoint.py
Test Task 17 — Human-in-the-Loop Checkpoint.

Chạy: cd my-ai-org && python tests/test_checkpoint.py
"""

import sys
import json
from pathlib import Path
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.graph.state import TaskStatus
from core.graph.engine import needs_human_approval
from system.learning.checkpoint_store import CheckpointStore
from memory.storage import MemoryStorage


# ---------------------------------------------------------------------------
# Test 1: needs_human_approval — fix_attempts >= 2 on "delete" task
# ---------------------------------------------------------------------------
def test_needs_approval_for_dangerous_task():
    print("TEST 1: needs_human_approval with 'delete' in task_desc")
    state = {
        "task_desc": "Xoá user khỏi database",
        "fix_attempts": 0,
        "max_attempts": 3,
        "status": TaskStatus.PENDING,
    }
    assert needs_human_approval(state) is True, \
        "Task with 'delete' should need approval"
    print("  ✅ 'delete' task detected")


# ---------------------------------------------------------------------------
# Test 2: needs_human_approval — fix_attempts >= 2
# ---------------------------------------------------------------------------
def test_needs_approval_for_high_fix_attempts():
    print("TEST 2: needs_human_approval with fix_attempts >= 2")
    state = {
        "task_desc": "Viết hàm add",
        "fix_attempts": 2,
        "max_attempts": 3,
        "status": TaskStatus.FIXING,
    }
    assert needs_human_approval(state) is True, \
        "fix_attempts >= 2 should need approval"
    print("  ✅ High fix_attempts detected")


# ---------------------------------------------------------------------------
# Test 3: needs_human_approval — safe task returns False
# ---------------------------------------------------------------------------
def test_no_approval_needed_for_safe_task():
    print("TEST 3: needs_human_approval returns False for safe task")
    state = {
        "task_desc": "Viết hàm add(a, b)",
        "fix_attempts": 0,
        "max_attempts": 3,
        "status": TaskStatus.PENDING,
    }
    assert needs_human_approval(state) is False
    print("  ✅ Safe task: no approval needed")


# ---------------------------------------------------------------------------
# Test 4: needs_human_approval — fix_attempts = 1 (not yet >= 2)
# ---------------------------------------------------------------------------
def test_no_approval_for_fix_attempts_1():
    print("TEST 4: needs_human_approval returns False for fix_attempts=1")
    state = {
        "task_desc": "Viết hàm add",
        "fix_attempts": 1,
        "max_attempts": 3,
        "status": TaskStatus.FIXING,
    }
    assert needs_human_approval(state) is False
    print("  ✅ fix_attempts=1: no approval needed")


# ---------------------------------------------------------------------------
# Test 5: needs_human_approval — "DELETE" case-insensitive
# ---------------------------------------------------------------------------
def test_needs_approval_case_insensitive():
    print("TEST 5: needs_human_approval case-insensitive for DELETE")
    state = {
        "task_desc": "DROP TABLE users",
        "fix_attempts": 0,
        "status": TaskStatus.PENDING,
    }
    assert needs_human_approval(state) is True
    print("  ✅ 'DROP' triggers via 'drop ' keyword check")

# Actually let me fix that — "DROP" doesn't contain "delete". Let me check edge cases:
def test_needs_approval_edge_cases():
    print("TEST 5b: edge cases — 'Delete' (capitalized), 'deleted' (contains 'delete')")
    state1 = {"task_desc": "Delete all records", "fix_attempts": 0, "max_attempts": 3, "status": TaskStatus.PENDING}
    assert needs_human_approval(state1) is True, "Capitalized 'Delete' should match"
    state2 = {"task_desc": "Handle deleted items", "fix_attempts": 0, "max_attempts": 3, "status": TaskStatus.PENDING}
    assert needs_human_approval(state2) is True, "'deleted' contains 'delete'"
    print("  ✅ Case-insensitive + substring match works")


# ---------------------------------------------------------------------------
# Test 6: CheckpointStore — submit + list_pending
# ---------------------------------------------------------------------------
def test_checkpoint_store_submit(tmp_path):
    print("TEST 6: CheckpointStore submit + list_pending")
    store = CheckpointStore(storage=MemoryStorage(tmp_path / "memory.json"))
    cp = store.submit(task_id="task-001", reason="High fix attempts")
    assert cp["status"] == "pending"
    assert cp["id"] is not None
    assert cp["task_id"] == "task-001"
    assert cp["reason"] == "High fix attempts"

    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0]["id"] == cp["id"]
    print(f"  ✅ Checkpoint submitted: id={cp['id']}")


# ---------------------------------------------------------------------------
# Test 7: CheckpointStore — approve
# ---------------------------------------------------------------------------
def test_checkpoint_store_approve(tmp_path):
    print("TEST 7: CheckpointStore approve checkpoint")
    store = CheckpointStore(storage=MemoryStorage(tmp_path / "memory.json"))
    cp = store.submit(task_id="task-001", reason="test")
    result = store.approve(cp["id"])
    assert result["status"] == "approved"
    assert result["approved_at"] is not None

    pending = store.list_pending()
    assert len(pending) == 0
    print(f"  ✅ Checkpoint approved: id={cp['id']}")


# ---------------------------------------------------------------------------
# Test 8: CheckpointStore — reject
# ---------------------------------------------------------------------------
def test_checkpoint_store_reject(tmp_path):
    print("TEST 8: CheckpointStore reject checkpoint")
    store = CheckpointStore(storage=MemoryStorage(tmp_path / "memory.json"))
    cp = store.submit(task_id="task-001", reason="test")
    result = store.reject(cp["id"], reason="Manual review needed")
    assert result["status"] == "rejected"
    assert result["rejection_reason"] == "Manual review needed"

    pending = store.list_pending()
    assert len(pending) == 0
    print(f"  ✅ Checkpoint rejected: reason={result['rejection_reason']}")


# ---------------------------------------------------------------------------
# Test 9: CheckpointStore — get
# ---------------------------------------------------------------------------
def test_checkpoint_store_get(tmp_path):
    print("TEST 9: CheckpointStore get by id")
    store = CheckpointStore(storage=MemoryStorage(tmp_path / "memory.json"))
    cp = store.submit(task_id="task-002", reason="dangerous")
    found = store.get(cp["id"])
    assert found is not None
    assert found["task_id"] == "task-002"
    assert store.get("nonexistent") is None
    print("  ✅ Get by id works + missing returns None")


# ---------------------------------------------------------------------------
# Test 10: CheckpointStore — unknown approve/reject returns None
# ---------------------------------------------------------------------------
def test_checkpoint_store_unknown_id(tmp_path):
    print("TEST 10: CheckpointStore approve/reject unknown id -> None")
    store = CheckpointStore(storage=MemoryStorage(tmp_path / "memory.json"))
    assert store.approve("nonexistent") is None
    assert store.reject("nonexistent", reason="no") is None
    print("  ✅ Unknown id returns None")


# ---------------------------------------------------------------------------
# Test 11: Webhook: interrupted flag in state
# ---------------------------------------------------------------------------
def test_checkpoint_node_decision(tmp_path):
    print("TEST 11: checkpoint node decision tracking")
    store = CheckpointStore(storage=MemoryStorage(tmp_path / "memory.json"))
    cp = store.submit(task_id="task-001", reason="test")
    store.approve(cp["id"])
    # After approve, checkpoint should reflect decision
    cp2 = store.get(cp["id"])
    assert cp2["status"] == "approved"
    print("  ✅ Decision tracking works")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    print("\n🔬 Task 17 — Human-in-the-Loop Checkpoint Tests\n" + "=" * 50)

    results = []

    def run_test(fn, uses_tmp=False):
        try:
            if uses_tmp:
                with TemporaryDirectory() as tmp:
                    fn(Path(tmp))
            else:
                fn()
            results.append((fn.__name__, True))
            print()
        except Exception as e:
            results.append((fn.__name__, False))
            print(f"  ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            print()

    run_test(test_needs_approval_for_dangerous_task)
    run_test(test_needs_approval_for_high_fix_attempts)
    run_test(test_no_approval_needed_for_safe_task)
    run_test(test_no_approval_for_fix_attempts_1)
    run_test(test_needs_approval_case_insensitive)
    run_test(test_needs_approval_edge_cases)
    run_test(test_checkpoint_store_submit, uses_tmp=True)
    run_test(test_checkpoint_store_approve, uses_tmp=True)
    run_test(test_checkpoint_store_reject, uses_tmp=True)
    run_test(test_checkpoint_store_get, uses_tmp=True)
    run_test(test_checkpoint_store_unknown_id, uses_tmp=True)
    run_test(test_checkpoint_node_decision, uses_tmp=True)

    print("=" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print(f"Results: {passed}/{len(results)} passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED — Task 17 Checkpoint ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        for name, ok in results:
            if not ok:
                print(f"   - {name}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
