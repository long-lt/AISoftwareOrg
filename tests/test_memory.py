import asyncio
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.memory.long_term import LongTermMemory
from memory.manager import MemoryManager
from memory.storage import DEFAULT_MEMORY_FILE, MemoryStorage, MemoryStorageError


def test_default_storage_path_is_project_root():
    storage = MemoryStorage()
    assert storage.file_path == DEFAULT_MEMORY_FILE
    assert storage.file_path.parent == _root / "storage"


def test_corrupt_memory_is_not_silently_overwritten(tmp_path):
    memory_file = Path(tmp_path) / "memory.json"
    memory_file.write_text("{not-json", encoding="utf-8")
    storage = MemoryStorage(memory_file)

    _assert_raises(MemoryStorageError, storage.load)

    _assert_raises(
        MemoryStorageError,
        lambda: storage.add_experience({"task_id": "task-1", "content": "new memory"}),
    )

    assert memory_file.read_text(encoding="utf-8") == "{not-json"


def test_memory_records_full_task_data_and_searches_semantically(tmp_path):
    async def run_test():
        storage = MemoryStorage(tmp_path / "memory.json")
        manager = MemoryManager(storage=storage, long_term=LongTermMemory(storage=storage))
        code = (
            "def add(a: int, b: int) -> int:\n"
            "    \"\"\"Return the sum of two integers.\"\"\"\n"
            "    if not isinstance(a, int) or not isinstance(b, int):\n"
            "        raise ValueError('Both values must be int')\n"
            "    return a + b\n"
        )

        await manager.record_task_outcome(
            task_id="task-add",
            task_desc="Viết hàm add(a, b) trả về tổng hai số nguyên",
            success=True,
            output=code,
            logs=["[Dev] code generated", "[QA] pass"],
            fix_attempts=2,
            review_result="approved",
            test_result="pass",
        )

        data = storage.load()
        record = data["experiences"][0]
        assert record["metadata"]["code"] == code
        assert record["metadata"]["fix_attempts"] == 2
        assert "embedding" in record

        context = await manager.get_relevant_context(
            "Viết hàm sum_numbers(x, y) tính tổng hai số",
            limit=1,
        )
        assert "Viết hàm add(a, b)" in context
        assert "Fix attempts: 2" in context
        assert "def add" in context

    asyncio.run(run_test())


def _assert_raises(error_type, fn):
    try:
        fn()
    except error_type:
        return
    raise AssertionError(f"Expected {error_type.__name__}")


def main():
    print("Running memory tests")
    test_default_storage_path_is_project_root()
    with TemporaryDirectory() as tmp_dir:
        test_corrupt_memory_is_not_silently_overwritten(Path(tmp_dir))
    with TemporaryDirectory() as tmp_dir:
        test_memory_records_full_task_data_and_searches_semantically(Path(tmp_dir))
    print("All memory tests passed")


if __name__ == "__main__":
    main()
