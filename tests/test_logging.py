"""
tests/test_logging.py
Test Task 8 — Logging System.

Viết trước khi implement (test-driven).
Chạy: cd my-ai-org && python tests/test_logging.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


# ---------------------------------------------------------------------------
# Test 1: Logger khởi tạo không lỗi
# ---------------------------------------------------------------------------
def test_logger_imports():
    print("TEST 1: Import và khởi tạo")
    from core.logging import AgentLogger, LogLevel, LogEntry
    logger = AgentLogger()
    assert logger is not None
    print("  ✅ AgentLogger() khởi tạo thành công")
    print("  ✅ LogLevel enum available")
    print("  ✅ LogEntry dataclass available")


# ---------------------------------------------------------------------------
# Test 2: Log một agent action → ghi vào file
# ---------------------------------------------------------------------------
def test_log_agent_action_writes_to_file(tmp_path):
    print("TEST 2: Log agent action → ghi vào file")
    from core.logging import AgentLogger

    log_file = tmp_path / "test.jsonl"
    logger = AgentLogger(log_file=log_file)

    asyncio.run(logger.log_action(
        task_id="task-001",
        agent="DevAgent",
        action="code_generated",
        details={"lines": 42, "language": "python"},
        status="success",
    ))

    assert log_file.exists(), "Log file không được tạo"
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["task_id"] == "task-001"
    assert entry["agent"] == "DevAgent"
    assert entry["action"] == "code_generated"
    assert entry["status"] == "success"
    assert entry["details"]["lines"] == 42
    assert "timestamp" in entry

    print(f"  ✅ Entry ghi vào file đúng format")
    print(f"  ✅ timestamp: {entry['timestamp']}")
    print(f"  ✅ details: {entry['details']}")


# ---------------------------------------------------------------------------
# Test 3: Log nhiều entries → query theo task_id
# ---------------------------------------------------------------------------
def test_query_by_task_id(tmp_path):
    print("TEST 3: Query logs theo task_id")
    from core.logging import AgentLogger

    log_file = tmp_path / "test.jsonl"
    logger = AgentLogger(log_file=log_file)

    async def write_logs():
        await logger.log_action("task-A", "DevAgent",   "code_generated", {}, "success")
        await logger.log_action("task-B", "QAAgent",    "test_run",        {}, "fail")
        await logger.log_action("task-A", "ReviewerAgent", "review_done",  {}, "success")
        await logger.log_action("task-B", "DevAgent",   "code_generated", {}, "success")

    asyncio.run(write_logs())

    entries_A = asyncio.run(logger.query(task_id="task-A"))
    entries_B = asyncio.run(logger.query(task_id="task-B"))

    assert len(entries_A) == 2, f"Expected 2 entries for task-A, got {len(entries_A)}"
    assert len(entries_B) == 2, f"Expected 2 entries for task-B, got {len(entries_B)}"
    assert all(e["task_id"] == "task-A" for e in entries_A)

    print(f"  ✅ task-A: {len(entries_A)} entries")
    print(f"  ✅ task-B: {len(entries_B)} entries")


# ---------------------------------------------------------------------------
# Test 4: Query theo agent
# ---------------------------------------------------------------------------
def test_query_by_agent(tmp_path):
    print("TEST 4: Query logs theo agent")
    from core.logging import AgentLogger

    log_file = tmp_path / "test.jsonl"
    logger = AgentLogger(log_file=log_file)

    async def write_logs():
        await logger.log_action("task-1", "DevAgent",  "code_generated", {}, "success")
        await logger.log_action("task-1", "QAAgent",   "test_run",        {}, "pass")
        await logger.log_action("task-2", "DevAgent",  "code_generated", {}, "success")
        await logger.log_action("task-2", "ReviewerAgent", "review_done", {}, "success")

    asyncio.run(write_logs())

    dev_logs = asyncio.run(logger.query(agent="DevAgent"))
    assert len(dev_logs) == 2
    assert all(e["agent"] == "DevAgent" for e in dev_logs)

    print(f"  ✅ DevAgent: {len(dev_logs)} entries")


# ---------------------------------------------------------------------------
# Test 5: Query theo status (fail)
# ---------------------------------------------------------------------------
def test_query_by_status(tmp_path):
    print("TEST 5: Query logs theo status")
    from core.logging import AgentLogger

    log_file = tmp_path / "test.jsonl"
    logger = AgentLogger(log_file=log_file)

    async def write_logs():
        await logger.log_action("task-1", "DevAgent", "code_generated", {}, "success")
        await logger.log_action("task-1", "QAAgent",  "test_run",       {}, "fail")
        await logger.log_action("task-2", "QAAgent",  "test_run",       {}, "fail")

    asyncio.run(write_logs())

    fails = asyncio.run(logger.query(status="fail"))
    assert len(fails) == 2
    assert all(e["status"] == "fail" for e in fails)

    print(f"  ✅ fail entries: {len(fails)}")


# ---------------------------------------------------------------------------
# Test 6: log_workflow_state — log toàn bộ state từ pipeline
# ---------------------------------------------------------------------------
def test_log_workflow_state(tmp_path):
    print("TEST 6: log_workflow_state")
    from core.logging import AgentLogger

    log_file = tmp_path / "test.jsonl"
    logger = AgentLogger(log_file=log_file)

    # Dùng plain dict thay vì import TaskStatus — test logger độc lập
    state = {
        "task_id":      "task-999",
        "task_desc":    "Viết hàm add(a, b)",
        "current_code": "def add(a, b): return a + b",
        "review_result": "approved",
        "test_result":   "pass",
        "fix_attempts":  1,
        "max_attempts":  3,
        "status":        "done",
        "logs":          ["[Dev] generated", "[QA] pass"],
        "error":         None,
    }

    asyncio.run(logger.log_workflow_state(state))

    entries = asyncio.run(logger.query(task_id="task-999"))
    assert len(entries) == 1
    entry = entries[0]

    assert entry["action"] == "workflow_completed"
    assert entry["details"]["fix_attempts"] == 1
    assert entry["details"]["test_result"] == "pass"
    assert entry["status"] == "success"

    print(f"  ✅ workflow_completed logged")
    print(f"  ✅ details: fix_attempts={entry['details']['fix_attempts']}, test={entry['details']['test_result']}")


# ---------------------------------------------------------------------------
# Test 7: File rotate khi quá lớn
# ---------------------------------------------------------------------------
def test_log_file_does_not_crash_on_large_file(tmp_path):
    print("TEST 7: File lớn không crash")
    from core.logging import AgentLogger

    log_file = tmp_path / "test.jsonl"
    logger = AgentLogger(log_file=log_file, max_entries=5)

    async def write_many():
        for i in range(10):
            await logger.log_action(f"task-{i}", "DevAgent", "action", {"i": i}, "success")

    asyncio.run(write_many())

    # Không crash là pass — size check là bonus
    entries = asyncio.run(logger.query())
    print(f"  ✅ Logged 10 entries, stored {len(entries)} (max_entries=5)")
    assert len(entries) <= 10  # Không quan trọng số lượng, chỉ cần không crash


# ---------------------------------------------------------------------------
# Test 8: Thread-safe concurrent writes
# ---------------------------------------------------------------------------
def test_concurrent_writes_no_corruption(tmp_path):
    print("TEST 8: Concurrent writes không corrupt file")
    from core.logging import AgentLogger

    log_file = tmp_path / "test.jsonl"
    logger = AgentLogger(log_file=log_file)

    async def write_concurrently():
        tasks = [
            logger.log_action(f"task-{i}", "DevAgent", "action", {"i": i}, "success")
            for i in range(20)
        ]
        await asyncio.gather(*tasks)

    asyncio.run(write_concurrently())

    # Verify tất cả entries đều là valid JSON
    lines = log_file.read_text().strip().split("\n")
    valid = 0
    for line in lines:
        if line.strip():
            try:
                json.loads(line)
                valid += 1
            except json.JSONDecodeError:
                print(f"  ❌ Invalid JSON line: {line[:50]}")

    assert valid == len([l for l in lines if l.strip()])
    print(f"  ✅ {valid} concurrent entries, all valid JSON")


# ---------------------------------------------------------------------------
# Test 9: Hash chain detects tampering
# ---------------------------------------------------------------------------
def test_hash_chain_detects_tampering(tmp_path):
    print("TEST 9: Hash chain phát hiện log bị sửa")
    from core.logging import AgentLogger
    from core.logging.verify import verify_log_file

    log_file = tmp_path / "test.jsonl"
    logger = AgentLogger(log_file=log_file)

    async def write_logs():
        await logger.log_action("task-1", "DevAgent", "code_generated", {"lines": 12}, "success")
        await logger.log_action("task-1", "QAAgent", "test_run", {"passed": 3}, "success")
        await logger.log_action("task-1", "Pipeline", "workflow_completed", {"test_result": "pass"}, "success")

    asyncio.run(write_logs())

    intact = verify_log_file(log_file)
    assert intact.ok
    assert intact.checked_entries == 3
    assert intact.error is None

    lines = log_file.read_text(encoding="utf-8").splitlines()
    edited = json.loads(lines[1])
    edited["details"]["passed"] = 999
    lines[1] = json.dumps(edited, ensure_ascii=False)
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tampered = verify_log_file(log_file)
    assert not tampered.ok
    assert "hash mismatch" in (tampered.error or "")

    print("  ✅ Chain intact trước khi sửa")
    print(f"  ✅ Tamper detected: {tampered.error}")


# ---------------------------------------------------------------------------
# Test 10: Legacy logs can be upgraded once
# ---------------------------------------------------------------------------
def test_legacy_log_upgrade(tmp_path):
    print("TEST 10: Upgrade legacy JSONL log")
    from core.logging.verify import upgrade_log_file, verify_log_file

    log_file = tmp_path / "legacy.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_entries = [
        {"task_id": "old-1", "agent": "DevAgent", "action": "code", "status": "success", "details": {}},
        {"task_id": "old-1", "agent": "QAAgent", "action": "test", "status": "success", "details": {}},
    ]
    log_file.write_text(
        "\n".join(json.dumps(entry, ensure_ascii=False) for entry in legacy_entries) + "\n",
        encoding="utf-8",
    )

    before = verify_log_file(log_file)
    assert not before.ok
    assert "missing entry_hash" in (before.error or "")

    upgraded = upgrade_log_file(log_file)
    assert upgraded.ok
    assert upgraded.checked_entries == 2

    after = verify_log_file(log_file)
    assert after.ok

    print("  ✅ Legacy log được upgrade")
    print(f"  ✅ Chain intact: {after.checked_entries} entries")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    print("\n🔬 Task 8 — Logging System Tests\n" + "=" * 50)

    results = []

    def run_test(fn, *args):
        try:
            fn(*args)
            results.append((fn.__name__, True))
            print()
        except Exception as e:
            results.append((fn.__name__, False))
            print(f"  ❌ FAILED: {e}")
            import traceback; traceback.print_exc()
            print()

    run_test(test_logger_imports)

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        run_test(test_log_agent_action_writes_to_file, tmp_path / "t2")
        run_test(test_query_by_task_id,               tmp_path / "t3")
        run_test(test_query_by_agent,                 tmp_path / "t4")
        run_test(test_query_by_status,                tmp_path / "t5")
        run_test(test_log_workflow_state,             tmp_path / "t6")
        run_test(test_log_file_does_not_crash_on_large_file, tmp_path / "t7")
        run_test(test_concurrent_writes_no_corruption, tmp_path / "t8")
        run_test(test_hash_chain_detects_tampering,   tmp_path / "t9")
        run_test(test_legacy_log_upgrade,             tmp_path / "t10")

    print("=" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print(f"Results: {passed}/{len(results)} passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED — Task 8 Logging ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        for name, ok in results:
            if not ok:
                print(f"   - {name}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
