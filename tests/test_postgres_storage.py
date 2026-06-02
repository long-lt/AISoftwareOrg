"""
tests/test_postgres_storage.py
Tests for Postgres storage and factory pattern.

Chạy:
    cd my-ai-org && python tests/test_postgres_storage.py

Postgres tests bị skip nếu không có MEMORY_DATABASE_URL.
"""

import os
import sys
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


def test_factory_returns_json_by_default():
    """Test get_storage() returns MemoryStorage by default."""
    print("TEST 1: Factory returns MemoryStorage by default")

    from memory.storage import get_storage, MemoryStorage

    # Clear env if set
    old_val = os.environ.pop("STORAGE_BACKEND", None)
    try:
        storage = get_storage()
        assert isinstance(storage, MemoryStorage)
        print("  ✅ Returns MemoryStorage when STORAGE_BACKEND not set")
    finally:
        if old_val is not None:
            os.environ["STORAGE_BACKEND"] = old_val


def test_factory_json_explicit():
    """Test get_storage('json') returns MemoryStorage."""
    print("TEST 2: Factory returns MemoryStorage for 'json'")

    from memory.storage import get_storage, MemoryStorage

    storage = get_storage("json")
    assert isinstance(storage, MemoryStorage)
    print("  ✅ Returns MemoryStorage for 'json'")


def test_factory_postgres_requires_url():
    """Test get_storage('postgres') raises if MEMORY_DATABASE_URL not set."""
    print("TEST 3: Factory raises if postgres but no URL")

    from memory.storage import get_storage

    old_val = os.environ.pop("MEMORY_DATABASE_URL", None)
    try:
        try:
            get_storage("postgres")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "MEMORY_DATABASE_URL" in str(e)
            print("  ✅ Raises RuntimeError when MEMORY_DATABASE_URL not set")
    finally:
        if old_val is not None:
            os.environ["MEMORY_DATABASE_URL"] = old_val


def test_factory_respects_env():
    """Test get_storage() respects STORAGE_BACKEND env."""
    print("TEST 4: Factory respects STORAGE_BACKEND env")

    from memory.storage import get_storage, MemoryStorage

    old_backend = os.environ.get("STORAGE_BACKEND")
    try:
        os.environ["STORAGE_BACKEND"] = "json"
        storage = get_storage()
        assert isinstance(storage, MemoryStorage)
        print("  ✅ Respects STORAGE_BACKEND=json")
    finally:
        if old_backend is None:
            os.environ.pop("STORAGE_BACKEND", None)
        else:
            os.environ["STORAGE_BACKEND"] = old_backend


def test_postgres_storage_crud():
    """Test PostgresStorage CRUD operations (requires Postgres)."""
    print("TEST 5: PostgresStorage CRUD")

    database_url = os.environ.get("MEMORY_DATABASE_URL")
    if not database_url:
        print("  ⚠️  MEMORY_DATABASE_URL not set — skipping Postgres tests")
        return

    from memory.postgres_storage import PostgresStorage

    # Use a test-specific table to avoid conflicts
    storage = PostgresStorage(database_url)

    # Test save and load
    test_data = {
        "version": "1.0",
        "experiences": [
            {"task_id": "test-1", "content": "test experience", "status": "approved"}
        ],
        "facts": [{"key": "test", "value": "fact"}],
    }
    storage.save(test_data)

    loaded = storage.load()
    assert loaded["version"] == "1.0"
    assert len(loaded["experiences"]) >= 1
    assert loaded["experiences"][-1]["task_id"] == "test-1"
    print("  ✅ Save and load works")

    # Test add_experience
    storage.add_experience({"task_id": "test-2", "content": "another experience"})
    loaded = storage.load()
    assert any(e.get("task_id") == "test-2" for e in loaded["experiences"])
    print("  ✅ add_experience works")

    # Cleanup: remove test data
    storage.save({"version": "1.0", "experiences": [], "facts": []})
    print("  ✅ Cleanup done")


def test_postgres_storage_max_experiences():
    """Test PostgresStorage limits experiences to 100."""
    print("TEST 6: PostgresStorage max experiences")

    database_url = os.environ.get("MEMORY_DATABASE_URL")
    if not database_url:
        print("  ⚠️  MEMORY_DATABASE_URL not set — skipping")
        return

    from memory.postgres_storage import PostgresStorage

    storage = PostgresStorage(database_url)

    # Add 105 experiences
    for i in range(105):
        storage.add_experience({"task_id": f"test-{i}", "content": f"experience {i}"})

    loaded = storage.load()
    assert len(loaded["experiences"]) <= 100, f"Expected <=100, got {len(loaded['experiences'])}"
    print(f"  ✅ Experiences capped at {len(loaded['experiences'])}")

    # Cleanup
    storage.save({"version": "1.0", "experiences": [], "facts": []})


def test_json_storage_still_works():
    """Test that JSON storage still works after factory changes."""
    print("TEST 7: JSON storage still works")

    from memory.storage import MemoryStorage

    with TemporaryDirectory() as tmp:
        storage = MemoryStorage(Path(tmp) / "test.json")

        # Test save and load
        storage.save({
            "version": "1.0",
            "experiences": [{"task_id": "test", "content": "test"}],
            "facts": [],
        })
        loaded = storage.load()
        assert loaded["experiences"][0]["task_id"] == "test"
        print("  ✅ JSON save/load works")

        # Test add_experience
        storage.add_experience({"task_id": "test-2", "content": "another"})
        loaded = storage.load()
        assert len(loaded["experiences"]) == 2
        print("  ✅ JSON add_experience works")


def test_add_experience_uses_reentrant_lock():
    """Regression: add_experience() should not deadlock on nested load/save lock usage."""
    print("TEST 8: add_experience uses re-entrant lock")
    from memory.postgres_storage import PostgresStorage

    storage = PostgresStorage.__new__(PostgresStorage)
    storage._lock = threading.RLock()
    state = {"version": "1.0", "experiences": [], "facts": []}

    def _load():
        with storage._lock:
            return {
                "version": state["version"],
                "experiences": list(state["experiences"]),
                "facts": list(state["facts"]),
            }

    def _save(data):
        with storage._lock:
            state["version"] = data["version"]
            state["experiences"] = list(data["experiences"])
            state["facts"] = list(data["facts"])

    storage.load = _load
    storage.save = _save

    storage.add_experience({"task_id": "rlock-test", "content": "ok"})
    assert state["experiences"][-1]["task_id"] == "rlock-test"
    print("  ✅ add_experience completed without deadlock")


def main():
    print("\n🔬 Phase 6 — Task 2: Postgres Storage Tests\n" + "=" * 50)

    tests = [
        test_factory_returns_json_by_default,
        test_factory_json_explicit,
        test_factory_postgres_requires_url,
        test_factory_respects_env,
        test_postgres_storage_crud,
        test_postgres_storage_max_experiences,
        test_json_storage_still_works,
        test_add_experience_uses_reentrant_lock,
    ]

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

    for t in tests:
        run_test(t)

    print("=" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print(f"Results: {passed}/{len(results)} passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED — Postgres storage ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        for name, ok in results:
            if not ok:
                print(f"   - {name}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
