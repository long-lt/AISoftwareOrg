"""
tests/test_extractor.py
Test Task 12 — Experience Extractor.

Chạy: cd my-ai-org && python tests/test_extractor.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from system.learning.extractor import ExperienceExtractor, Experience


def _make_state(**overrides):
    """Tạo mock WorkflowState với defaults hợp lý."""
    state = {
        "task_id": "test-001",
        "task_desc": "Viết hàm add(a, b) trả về tổng",
        "current_code": "def add(a, b):\n    return a + b",
        "previous_code": None,
        "review_result": "approved",
        "test_result": "fail: AssertionError: expected 5, got 3",
        "fix_attempts": 1,
        "max_attempts": 3,
        "status": "done",
        "logs": [
            "[Dev] attempt=1 | code generated",
            "[Reviewer] approved",
            "[QA] fail: AssertionError: expected 5, got 3",
            "[Fix] attempt 1/3 | qa failed",
            "[Dev] attempt=2 | code generated",
            "[QA] pass",
        ],
        "error": None,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Test 1: Extract khi fix_attempts > 0 → trả về Experience
# ---------------------------------------------------------------------------
def test_extract_returns_experience_when_fixes_exist():
    print("TEST 1: Extract khi fix_attempts > 0")
    extractor = ExperienceExtractor()
    state = _make_state(fix_attempts=1)

    result = extractor.extract(state)

    assert result is not None, "Nên trả về Experience khi fix_attempts > 0"
    assert isinstance(result, Experience)
    assert result.task_id == "test-001"
    assert result.fix_count == 1
    assert result.status == "pending_review"
    print(f"  ✅ Experience extracted: task_type={result.task_type}, fix_count={result.fix_count}")


# ---------------------------------------------------------------------------
# Test 2: Extract khi fix_attempts == 0 → trả về None
# ---------------------------------------------------------------------------
def test_extract_returns_none_when_no_fixes():
    print("TEST 2: Extract khi fix_attempts == 0")
    extractor = ExperienceExtractor()
    state = _make_state(fix_attempts=0, test_result="pass")

    result = extractor.extract(state)

    assert result is None, "Nên trả về None khi fix_attempts == 0"
    print("  ✅ Returns None — no experience to extract")


# ---------------------------------------------------------------------------
# Test 3: task_type detection
# ---------------------------------------------------------------------------
def test_task_type_detection():
    print("TEST 3: Task type detection")
    extractor = ExperienceExtractor()

    cases = [
        ("Viết API endpoint GET /users", "api"),
        ("Tạo REST API cho todo list", "api"),
        ("Viết hàm đọc file CSV", "file_io"),
        ("Xử lý dữ liệu JSON từ database", "data_processing"),
        ("Viết hàm utility để validate email", "utility"),
        ("Tạo class quản lý user", "data_processing"),
        ("Fix bug trong hàm tính tổng", "utility"),
    ]

    for desc, expected_type in cases:
        state = _make_state(task_desc=desc, fix_attempts=1)
        result = extractor.extract(state)
        assert result is not None, f"Should extract for: {desc}"
        assert result.task_type == expected_type, \
            f"Expected '{expected_type}' for '{desc}', got '{result.task_type}'"
        print(f"  ✅ '{desc[:40]}' → {result.task_type}")


# ---------------------------------------------------------------------------
# Test 4: Lessons được trích xuất từ logs
# ---------------------------------------------------------------------------
def test_lessons_extracted_from_logs():
    print("TEST 4: Lessons extracted from logs")
    extractor = ExperienceExtractor()
    state = _make_state(
        fix_attempts=2,
        test_result="fail: TypeError: unsupported operand",
        review_result="rejected: Missing error handling for None input",
        logs=[
            "[Dev] attempt=1 | code generated",
            "[Reviewer] rejected: Missing error handling for None input",
            "[Fix] attempt 1/3 | reviewer rejected",
            "[Dev] attempt=2 | code generated",
            "[QA] fail: TypeError: unsupported operand",
            "[Fix] attempt 2/3 | qa failed",
            "[Dev] attempt=3 | code generated",
            "[QA] pass",
        ],
    )

    result = extractor.extract(state)

    assert result is not None
    assert len(result.lessons) > 0, "Phải có ít nhất 1 lesson"
    assert result.problem, "Phải có problem description"
    assert result.solution, "Phải có solution code"
    print(f"  ✅ {len(result.lessons)} lessons extracted")
    for lesson in result.lessons:
        print(f"     - {lesson[:60]}")


# ---------------------------------------------------------------------------
# Test 5: Experience có đầy đủ fields
# ---------------------------------------------------------------------------
def test_experience_has_all_fields():
    print("TEST 5: Experience có đầy đủ fields")
    extractor = ExperienceExtractor()
    state = _make_state(fix_attempts=1)
    result = extractor.extract(state)

    assert result is not None
    assert result.id, "Missing id"
    assert result.task_id, "Missing task_id"
    assert result.task_type, "Missing task_type"
    assert result.problem, "Missing problem"
    assert result.solution, "Missing solution"
    assert result.fix_count >= 0, "Missing fix_count"
    assert result.status == "pending_review", "Wrong status"
    assert result.created_at, "Missing created_at"
    assert isinstance(result.lessons, list), "lessons should be list"
    print(f"  ✅ All fields present: id={result.id[:8]}..., task_type={result.task_type}")


# ---------------------------------------------------------------------------
# Test 6: original_code lấy từ previous_code trong state
# ---------------------------------------------------------------------------
def test_original_code_from_previous_code():
    print("TEST 6: original_code từ previous_code")
    extractor = ExperienceExtractor()
    old_code = "def add(a, b):\n    return a - b  # bug"
    new_code = "def add(a, b):\n    return a + b  # fixed"
    state = _make_state(
        fix_attempts=1,
        current_code=new_code,
        previous_code=old_code,
    )

    result = extractor.extract(state)

    assert result is not None
    assert result.original_code == old_code, f"Expected old code, got: {result.original_code[:50]}"
    assert result.solution == new_code
    print(f"  ✅ original_code captured ({len(old_code)} chars)")
    print(f"  ✅ solution is updated code ({len(new_code)} chars)")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    print("\n🔬 Task 12 — Experience Extractor Tests\n" + "=" * 50)

    results = []

    def run_test(fn):
        try:
            fn()
            results.append((fn.__name__, True))
            print()
        except Exception as e:
            results.append((fn.__name__, False))
            print(f"  ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            print()

    run_test(test_extract_returns_experience_when_fixes_exist)
    run_test(test_extract_returns_none_when_no_fixes)
    run_test(test_task_type_detection)
    run_test(test_lessons_extracted_from_logs)
    run_test(test_experience_has_all_fields)
    run_test(test_original_code_from_previous_code)

    print("=" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print(f"Results: {passed}/{len(results)} passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED — Task 12 Experience Extractor ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        for name, ok in results:
            if not ok:
                print(f"   - {name}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
