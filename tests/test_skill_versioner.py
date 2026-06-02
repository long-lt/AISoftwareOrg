"""
tests/test_skill_versioner.py
Test Task 14 — Skill Auto-Update (SkillVersioner).

Chạy: cd my-ai-org && python tests/test_skill_versioner.py
"""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from system.skills.versioner import SkillVersioner, _lesson_to_step
from system.skills.registry import SkillRegistry


def _create_skill(base: Path, name: str, version: str = "v1", steps: list[str] | None = None):
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "version": version,
        "applies_to": "dev_agent",
        "triggers": ["api", "endpoint", "route"],
        "steps": steps or [
            "Define the route path and HTTP method explicitly.",
            "Validate request input with a Pydantic model.",
            "Handle expected errors and return appropriate HTTP status codes.",
        ],
        "examples": ["GET /users returns a list."],
    }
    (skill_dir / f"{version}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _make_experience(**overrides) -> dict:
    exp = {
        "id": "exp-001",
        "task_id": "task-001",
        "task_type": "api",
        "problem": "QA: TypeError: unsupported operand",
        "solution": "def add(a, b): return a + b",
        "original_code": "def add(a, b): return a - b",
        "fix_count": 1,
        "review_notes": "approved",
        "lessons": ["Test failed: TypeError on None input"],
    }
    exp.update(overrides)
    return exp


# ---------------------------------------------------------------------------
# Test 1: create_new_version with valid "api" task_type creates v2.json
# ---------------------------------------------------------------------------
def test_create_new_version_creates_v2(tmp_path):
    print("TEST 1: create_new_version vs api task_type -> tao v2.json")
    _create_skill(tmp_path, "create_api", "v1", steps=["Step A", "Step B"])
    registry = SkillRegistry(skills_dir=tmp_path)
    versioner = SkillVersioner(registry=registry)

    exp = _make_experience(task_type="api", lessons=["Test failed: NullPointerException"])
    result = versioner.create_new_version(exp)

    assert result == "v2", f"Expected 'v2', got {result}"

    v2_path = tmp_path / "create_api" / "v2.json"
    assert v2_path.is_file(), "v2.json should exist"

    v1_path = tmp_path / "create_api" / "v1.json"
    assert v1_path.is_file(), "v1.json should still exist (khong xoa file cu)"

    with open(v2_path, encoding="utf-8") as f:
        v2 = json.load(f)
    assert v2["version"] == "v2"
    assert v2["name"] == "create_api"
    assert v2["created_from"] == "exp-001"
    assert len(v2["steps"]) == 3, "Should have all original steps + 1 new step"
    assert "Handle None/Null cases: NullPointerException" in v2["steps"]
    print(f"  ✅ v2 created: {len(v2['steps'])} steps, version={v2['version']}")


# ---------------------------------------------------------------------------
# Test 2: Unmapped task_type -> returns None
# ---------------------------------------------------------------------------
def test_create_new_version_no_skill_match(tmp_path):
    print("TEST 2: task_type khong co mapping -> None")
    _create_skill(tmp_path, "create_api")
    registry = SkillRegistry(skills_dir=tmp_path)
    versioner = SkillVersioner(registry=registry)

    exp = _make_experience(task_type="unknown_type")
    result = versioner.create_new_version(exp)

    assert result is None, "Should return None for unmapped task_type"
    print("  ✅ Returns None for unmapped task_type")


# ---------------------------------------------------------------------------
# Test 3: Skill not found in registry -> returns None
# ---------------------------------------------------------------------------
def test_create_new_version_skill_not_found(tmp_path):
    print("TEST 3: skill khong ton tai trong registry -> None")
    registry = SkillRegistry(skills_dir=tmp_path)
    versioner = SkillVersioner(registry=registry)

    exp = _make_experience(task_type="api")
    result = versioner.create_new_version(exp)

    assert result is None, "Should return None when skill not found"
    print("  ✅ Returns None when skill not found")


# ---------------------------------------------------------------------------
# Test 4: Lessons don't add new steps -> returns None
# ---------------------------------------------------------------------------
def test_create_new_version_no_improvements(tmp_path):
    print("TEST 4: lessons khong cai thien steps -> None")
    _create_skill(tmp_path, "create_api", steps=["Step A", "Step B"])
    registry = SkillRegistry(skills_dir=tmp_path)
    versioner = SkillVersioner(registry=registry)

    exp = _make_experience(lessons=[])
    result = versioner.create_new_version(exp)

    assert result is None, "Should return None when no improvements"
    print("  ✅ Returns None khi khong co lessons")


# ---------------------------------------------------------------------------
# Test 5: _determine_skill_name mapping
# ---------------------------------------------------------------------------
def test_determine_skill_name():
    print("TEST 5: _determine_skill_name mapping")
    assert SkillVersioner._determine_skill_name({"task_type": "api"}) == "create_api"
    assert SkillVersioner._determine_skill_name({"task_type": "data_processing"}) == "process_data"
    assert SkillVersioner._determine_skill_name({"task_type": "file_io"}) == "handle_files"
    assert SkillVersioner._determine_skill_name({"task_type": "unknown"}) is None
    assert SkillVersioner._determine_skill_name({}) is None
    print("  ✅ All mappings correct")


# ---------------------------------------------------------------------------
# Test 6: _bump_version logic
# ---------------------------------------------------------------------------
def test_bump_version():
    print("TEST 6: _bump_version")
    assert SkillVersioner._bump_version("v1") == "v2"
    assert SkillVersioner._bump_version("v2") == "v3"
    assert SkillVersioner._bump_version("v9") == "v10"
    assert SkillVersioner._bump_version("") == "v1"
    assert SkillVersioner._bump_version("invalid") == "v1"
    print("  ✅ All version bumps correct")


# ---------------------------------------------------------------------------
# Test 7: _improved_steps adds lessons as steps
# ---------------------------------------------------------------------------
def test_improved_steps_adds_lessons():
    print("TEST 7: _improved_steps adds lessons as steps")
    current = ["Step A", "Step B"]
    exp = _make_experience(lessons=[
        "Test failed: TypeError on None input",
        "Reviewer feedback: Add input validation",
        "logic/test failure",
    ])

    result = SkillVersioner._improved_steps(current, exp)
    assert len(result) == 5, f"Expected 5 steps, got {len(result)}"
    assert "Step A" in result
    assert "Step B" in result
    assert "Handle None/Null cases: TypeError on None input" in result
    assert "Code quality: Add input validation" in result
    assert "Double check business logic and edge cases" in result
    print(f"  ✅ {len(result)} steps total (2 original + 3 from lessons)")


# ---------------------------------------------------------------------------
# Test 8: _improved_steps no duplicates when same lesson repeated
# ---------------------------------------------------------------------------
def test_improved_steps_no_duplicates():
    print("TEST 8: _improved_steps khong co duplicate steps")
    current = ["Step A"]
    exp = _make_experience(lessons=[
        "Test failed: Something",
        "Test failed: Something",
        "Reviewer feedback: Fix style",
        "Reviewer feedback: Fix style",
    ])

    result = SkillVersioner._improved_steps(current, exp)
    assert len(result) == 3, f"Expected 3 (1 original + 2 unique), got {len(result)}"
    print(f"  ✅ {len(result)} steps (no duplicates)")


# ---------------------------------------------------------------------------
# Test 9: _improved_steps with empty lessons returns current
# ---------------------------------------------------------------------------
def test_improved_steps_empty_lessons():
    print("TEST 9: _improved_steps empty lessons -> current steps")
    current = ["Step A", "Step B"]
    exp = _make_experience(lessons=[])
    result = SkillVersioner._improved_steps(current, exp)
    assert result == current
    print("  ✅ Returns current steps unchanged")


# ---------------------------------------------------------------------------
# Test 10: _lesson_to_step handles different lesson formats
# ---------------------------------------------------------------------------
def test_lesson_to_step_variations():
    print("TEST 10: _lesson_to_step variations")
    cases = [
        ("Test failed: MemoryError", "Prevent regression: MemoryError"),
        ("Test failed:", "Write comprehensive tests for edge cases"),
        ("Test failed", "Write comprehensive tests for edge cases"),
        ("Test failed: None value returned", "Handle None/Null cases: None value returned"),
        ("Test failed: 404 Not Found", "Validate existence before access: 404 Not Found"),
        ("Test failed: timeout waiting for response", "Implement timeout handling and retries"),
        ("Reviewer feedback: Need better naming", "Code quality: Need better naming"),
        ("Reviewer feedback:", "Follow code review guidelines before submitting"),
        ("logic/test failure", "Double check business logic and edge cases"),
        ("code quality issue", "Ensure code follows organization's style guide and best practices"),
        ("Required 3 development attempts", "Plan for iterative development — keep components modular"),
        ("Some random log message", None),
        ("", None),
    ]
    for lesson, expected in cases:
        result = _lesson_to_step(lesson)
        assert result == expected, f"For '{lesson[:30]}': expected {expected!r}, got {result!r}"
    print("  ✅ All lesson conversions correct")


# ---------------------------------------------------------------------------
# Test 11: _improved_steps does not add step already in current
# ---------------------------------------------------------------------------
def test_improved_steps_skips_existing_step():
    print("TEST 11: _improved_steps skips neu lesson step da ton tai")
    current = ["Handle None/Null cases: got None value"]
    exp = _make_experience(lessons=["Test failed: got None value"])
    result = SkillVersioner._improved_steps(current, exp)
    assert len(result) == 1, "Should not add duplicate step"
    print("  ✅ No duplicate added")


# ---------------------------------------------------------------------------
# Test 12: create_new_version saves notes from lessons
# ---------------------------------------------------------------------------
def test_create_new_version_saves_notes(tmp_path):
    print("TEST 12: create_new_version saves notes from lessons")
    _create_skill(tmp_path, "create_api", "v1")
    registry = SkillRegistry(skills_dir=tmp_path)
    versioner = SkillVersioner(registry=registry)

    lessons = ["Test failed: Edge case crash", "Reviewer feedback: Improve docs"]
    exp = _make_experience(lessons=lessons)
    versioner.create_new_version(exp)

    v2_path = tmp_path / "create_api" / "v2.json"
    with open(v2_path, encoding="utf-8") as f:
        v2 = json.load(f)
    assert v2["notes"] == lessons
    print(f"  ✅ notes saved: {len(v2['notes'])} lessons")


# ---------------------------------------------------------------------------
# Test 13: create_new_version sets source_task_id
# ---------------------------------------------------------------------------
def test_create_new_version_sets_source_task_id(tmp_path):
    print("TEST 13: create_new_version sets source_task_id")
    _create_skill(tmp_path, "create_api", "v1")
    registry = SkillRegistry(skills_dir=tmp_path)
    versioner = SkillVersioner(registry=registry)

    exp = _make_experience(task_id="task-999")
    versioner.create_new_version(exp)

    v2_path = tmp_path / "create_api" / "v2.json"
    with open(v2_path, encoding="utf-8") as f:
        v2 = json.load(f)
    assert v2["source_task_id"] == "task-999"
    print(f"  ✅ source_task_id = {v2['source_task_id']}")


# ---------------------------------------------------------------------------
# Test 14: Lesson step text truncated to 120 chars
# ---------------------------------------------------------------------------
def test_lesson_step_truncation():
    print("TEST 14: lesson step text truncation to 120 chars")
    long_error = "Test failed: " + "a" * 200
    result = _lesson_to_step(long_error)
    assert result is not None
    assert len(result) <= 140, f"Step too long: {len(result)} chars"
    print(f"  ✅ Truncated to {len(result)} chars")


# ---------------------------------------------------------------------------
# Test 15: Integration via ApprovalQueue.approve triggers SkillVersioner
# ---------------------------------------------------------------------------
def test_approval_queue_triggers_skill_versioner(tmp_path):
    print("TEST 15: ApprovalQueue.approve triggers SkillVersioner")
    _create_skill(tmp_path, "create_api", "v1", steps=["Step A"])
    from system.learning.approval_queue import ApprovalQueue
    from memory.storage import MemoryStorage

    storage_path = tmp_path / "memory.json"
    storage = MemoryStorage(storage_path)
    # Override registry for versioner used inside approval queue
    import system.skills.versioner as versioner_mod
    original_init = versioner_mod.SkillVersioner.__init__
    def patched_init(self, registry=None):
        original_init(self, registry=SkillRegistry(skills_dir=tmp_path))
    versioner_mod.SkillVersioner.__init__ = patched_init

    try:
        queue = ApprovalQueue(storage=storage)
        exp = _make_experience(task_type="api", lessons=["Test failed: Crash bug"])
        submitted = queue.submit(exp)
        approved = queue.approve(submitted["id"], approved_by="test-bot")
        assert approved is not None
        assert approved["status"] == "approved"

        v2_path = tmp_path / "create_api" / "v2.json"
        assert v2_path.is_file(), "v2.json should be created via SkillVersioner"
        print(f"  ✅ v2.json created via ApprovalQueue.approve()")
    finally:
        versioner_mod.SkillVersioner.__init__ = original_init


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    print("\n🔬 Task 14 — Skill Auto-Update (SkillVersioner) Tests\n" + "=" * 50)

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

    run_test(test_determine_skill_name)
    run_test(test_bump_version)
    run_test(test_improved_steps_adds_lessons)
    run_test(test_improved_steps_no_duplicates)
    run_test(test_improved_steps_empty_lessons)
    run_test(test_lesson_to_step_variations)
    run_test(test_improved_steps_skips_existing_step)
    run_test(test_lesson_step_truncation)
    run_test(test_create_new_version_creates_v2, uses_tmp=True)
    run_test(test_create_new_version_no_skill_match, uses_tmp=True)
    run_test(test_create_new_version_skill_not_found, uses_tmp=True)
    run_test(test_create_new_version_no_improvements, uses_tmp=True)
    run_test(test_create_new_version_saves_notes, uses_tmp=True)
    run_test(test_create_new_version_sets_source_task_id, uses_tmp=True)
    run_test(test_approval_queue_triggers_skill_versioner, uses_tmp=True)

    print("=" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print(f"Results: {passed}/{len(results)} passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED — Task 14 Skill Auto-Update ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        for name, ok in results:
            if not ok:
                print(f"   - {name}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
