"""
tests/test_approval_queue.py
Test Task 13 — Human Approval Gate.

Chạy: cd my-ai-org && python tests/test_approval_queue.py
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from system.learning import ApprovalQueue
from memory.storage import MemoryStorage


def _make_experience(**overrides):
    """Tạo mock experience dict để test."""
    exp = {
        "id": None,
        "task_id": "task-001",
        "task_type": "api",
        "problem": "QA: TypeError: unsupported operand",
        "solution": "def add(a, b): return a + b",
        "original_code": "def add(a, b): return a - b",
        "fix_count": 1,
        "review_notes": "approved",
        "lessons": ["Test failed: TypeError"],
    }
    exp.update(overrides)
    return exp


# ---------------------------------------------------------------------------
# Test 1: Submit experience → xuất hiện trong list_pending
# ---------------------------------------------------------------------------
def test_submit_adds_to_pending(tmp_path):
    print("TEST 1: Submit experience → list_pending")
    storage_path = tmp_path / "memory.json"
    queue = ApprovalQueue(storage=MemoryStorage(storage_path))

    exp = _make_experience()
    result = queue.submit(exp)

    assert result["status"] == "pending_review"
    assert result["submitted_at"] is not None
    assert result["id"] is not None

    pending = queue.list_pending()
    assert len(pending) == 1
    assert pending[0]["id"] == result["id"]
    print(f"  ✅ Submitted: id={result['id']}, status={result['status']}")


# ---------------------------------------------------------------------------
# Test 2: Approve experience → status thành "approved"
# ---------------------------------------------------------------------------
def test_approve_changes_status(tmp_path):
    print("TEST 2: Approve experience")
    storage_path = tmp_path / "memory.json"
    queue = ApprovalQueue(storage=MemoryStorage(storage_path))

    exp = _make_experience()
    submitted = queue.submit(exp)

    approved = queue.approve(submitted["id"], approved_by="test-bot")
    assert approved is not None
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "test-bot"
    assert approved["approved_at"] is not None

    pending = queue.list_pending()
    assert len(pending) == 0
    approved_list = queue.list_approved()
    assert len(approved_list) == 1
    print(f"  ✅ Approved: id={approved['id']}, by={approved['approved_by']}")


# ---------------------------------------------------------------------------
# Test 3: Reject experience → status thành "rejected" + lưu lý do
# ---------------------------------------------------------------------------
def test_reject_saves_reason(tmp_path):
    print("TEST 3: Reject experience với lý do")
    storage_path = tmp_path / "memory.json"
    queue = ApprovalQueue(storage=MemoryStorage(storage_path))

    exp = _make_experience()
    submitted = queue.submit(exp)

    rejected = queue.reject(submitted["id"], reason="Bài học chưa đủ tổng quát", rejected_by="test-bot")
    assert rejected is not None
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "Bài học chưa đủ tổng quát"
    assert rejected["rejected_by"] == "test-bot"

    pending = queue.list_pending()
    assert len(pending) == 0
    rejected_list = queue.list_rejected()
    assert len(rejected_list) == 1
    print(f"  ✅ Rejected: id={rejected['id']}, reason={rejected['rejection_reason']}")


# ---------------------------------------------------------------------------
# Test 4: Approve/reject với exp_id không tồn tại → trả về None
# ---------------------------------------------------------------------------
def test_unknown_id_returns_none(tmp_path):
    print("TEST 4: Unknown exp_id → None")
    storage_path = tmp_path / "memory.json"
    queue = ApprovalQueue(storage=MemoryStorage(storage_path))

    assert queue.approve("nonexistent") is None
    assert queue.reject("nonexistent", reason="no") is None
    assert queue.get("nonexistent") is None
    print("  ✅ All return None for unknown id")


# ---------------------------------------------------------------------------
# Test 5: Count trả về đúng số lượng theo trạng thái
# ---------------------------------------------------------------------------
def test_count_returns_correct_counts(tmp_path):
    print("TEST 5: Count experiences")
    storage_path = tmp_path / "memory.json"
    queue = ApprovalQueue(storage=MemoryStorage(storage_path))

    e1 = queue.submit(_make_experience(task_id="t1"))
    e2 = queue.submit(_make_experience(task_id="t2"))
    queue.submit(_make_experience(task_id="t3"))

    queue.approve(e1["id"])
    queue.reject(e2["id"], reason="bad")

    counts = queue.count()
    assert counts["total"] == 3
    assert counts["pending_review"] == 1
    assert counts["approved"] == 1
    assert counts["rejected"] == 1
    print(f"  ✅ Counts: {counts}")


# ---------------------------------------------------------------------------
# Test 6: Submit nhiều experiences cùng lúc không corrupt
# ---------------------------------------------------------------------------
def test_multiple_submits_no_corruption(tmp_path):
    print("TEST 6: Multiple submits không corrupt file")
    storage_path = tmp_path / "memory.json"
    queue = ApprovalQueue(storage=MemoryStorage(storage_path))

    ids = []
    for i in range(10):
        result = queue.submit(_make_experience(task_id=f"t{i}"))
        ids.append(result["id"])

    assert len(queue.list_pending()) == 10
    assert queue.count()["total"] == 10

    # Approve 3, reject 2
    queue.approve(ids[0])
    queue.approve(ids[1])
    queue.approve(ids[2])
    queue.reject(ids[3], reason="no")
    queue.reject(ids[4], reason="bad")

    counts = queue.count()
    assert counts["approved"] == 3
    assert counts["rejected"] == 2
    assert counts["pending_review"] == 5
    print(f"  ✅ 10 submits, 3 approved, 2 rejected, 5 pending")


# ---------------------------------------------------------------------------
# Test 7: get() trả về đúng experience
# ---------------------------------------------------------------------------
def test_get_returns_experience(tmp_path):
    print("TEST 7: Get experience by id")
    storage_path = tmp_path / "memory.json"
    queue = ApprovalQueue(storage=MemoryStorage(storage_path))

    exp = _make_experience(task_id="find-me")
    submitted = queue.submit(exp)

    found = queue.get(submitted["id"])
    assert found is not None
    assert found["task_id"] == "find-me"
    assert found["status"] == "pending_review"
    print(f"  ✅ Found: id={found['id']}, task_id={found['task_id']}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    print("\n🔬 Task 13 — Human Approval Gate Tests\n" + "=" * 50)

    results = []

    def run_test(fn):
        try:
            with TemporaryDirectory() as tmp:
                fn(Path(tmp))
            results.append((fn.__name__, True))
            print()
        except Exception as e:
            results.append((fn.__name__, False))
            print(f"  ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            print()

    run_test(test_submit_adds_to_pending)
    run_test(test_approve_changes_status)
    run_test(test_reject_saves_reason)
    run_test(test_unknown_id_returns_none)
    run_test(test_count_returns_correct_counts)
    run_test(test_multiple_submits_no_corruption)
    run_test(test_get_returns_experience)

    print("=" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print(f"Results: {passed}/{len(results)} passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED — Task 13 Human Approval Gate ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        for name, ok in results:
            if not ok:
                print(f"   - {name}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
