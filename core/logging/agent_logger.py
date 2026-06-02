"""
core/logging/agent_logger.py
Structured logger cho mọi agent action trong hệ thống.

Storage:
    - Primary: JSONL file (JSON Lines — mỗi dòng là 1 JSON object)
    - Optional: Postgres (khi LOGGING_DATABASE_URL được set)
    - JSONL entries are hash-chained with prev_hash/entry_hash for tamper detection.

Format mỗi log entry:
    {
        "timestamp": "2026-05-09T10:30:00.000Z",
        "task_id":   "task-abc123",
        "agent":     "DevAgent",
        "action":    "code_generated",
        "status":    "success" | "fail" | "error" | "info",
        "details":   { ... }   // Dữ liệu tuỳ theo action
    }

Không dùng print() — dùng logger này cho tất cả output có ý nghĩa.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default log file — trong project root/logs/
PROJECT_ROOT   = Path(__file__).resolve().parents[2]
DEFAULT_LOG_FILE = PROJECT_ROOT / "logs" / "agent_actions.jsonl"
GENESIS_HASH = "0" * 64


class LogLevel(str, Enum):
    INFO    = "info"
    SUCCESS = "success"
    FAIL    = "fail"
    ERROR   = "error"
    WARNING = "warning"


@dataclass
class LogEntry:
    """Một log entry chuẩn hóa."""
    task_id:   str
    agent:     str
    action:    str
    status:    str
    details:   dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    prev_hash: str = GENESIS_HASH
    entry_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogEntry:
        return cls(
            task_id=data.get("task_id", ""),
            agent=data.get("agent", ""),
            action=data.get("action", ""),
            status=data.get("status", ""),
            details=data.get("details", {}),
            timestamp=data.get("timestamp", ""),
            prev_hash=data.get("prev_hash", GENESIS_HASH),
            entry_hash=data.get("entry_hash", ""),
        )


class AgentLogger:
    """Async structured logger với JSONL file storage.

    Thread-safe qua asyncio.Lock.
    Postgres support: set LOGGING_DATABASE_URL env var.

    Args:
        log_file:    Path đến JSONL file. Default: logs/agent_actions.jsonl
        max_entries: Giữ tối đa N entries trong file (0 = không giới hạn).
                     Khi vượt quá, xoá entries cũ nhất.
        db_url:      Postgres connection URL. Auto-read từ LOGGING_DATABASE_URL.
        echo:        True = in log ra stdout kèm với ghi file.
    """

    def __init__(
        self,
        log_file:    Optional[Path | str] = None,
        max_entries: int = 0,
        db_url:      Optional[str] = None,
        echo:        bool = False,
    ):
        raw = Path(log_file) if log_file else DEFAULT_LOG_FILE
        self.log_file    = raw if raw.is_absolute() else PROJECT_ROOT / raw
        self.max_entries = max_entries
        self.db_url      = db_url or os.getenv("LOGGING_DATABASE_URL")
        self.echo        = echo
        self._lock       = asyncio.Lock()
        self._ensure_log_dir()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def log_action(
        self,
        task_id: str,
        agent:   str,
        action:  str,
        details: dict[str, Any],
        status:  str = LogLevel.INFO,
    ) -> LogEntry:
        """Ghi một agent action vào log.

        Args:
            task_id: ID của task đang chạy.
            agent:   Tên agent (DevAgent, QAAgent, ...).
            action:  Tên action (code_generated, test_run, review_done, ...).
            details: Dict chứa dữ liệu bổ sung (không giới hạn).
            status:  "success" | "fail" | "error" | "info" | "warning"

        Returns:
            LogEntry đã được lưu.
        """
        entry = LogEntry(
            task_id=task_id,
            agent=agent,
            action=action,
            status=status,
            details=details,
        )
        await self._write(entry)

        if self.echo:
            icon = {"success": "✅", "fail": "❌", "error": "💥", "warning": "⚠️"}.get(status, "ℹ️")
            print(f"{icon} [{agent}] {action} | task={task_id} | {status}")

        return entry

    async def log_workflow_state(self, state: dict[str, Any]) -> LogEntry:
        """Convenience: log kết quả cuối của một workflow state.

        Tự động xác định status từ test_result và fix_attempts.
        """
        is_success  = state.get("test_result") == "pass"
        fix_count   = state.get("fix_attempts", 0)

        details = {
            "task_desc":     (state.get("task_desc") or "")[:200],
            "test_result":   state.get("test_result"),
            "review_result": state.get("review_result"),
            "fix_attempts":  fix_count,
            "max_attempts":  state.get("max_attempts"),
            "code_length":   len(state.get("current_code") or ""),
            "log_count":     len(state.get("logs") or []),
        }

        return await self.log_action(
            task_id = state.get("task_id", "unknown"),
            agent   = "Pipeline",
            action  = "workflow_completed",
            details = details,
            status  = "success" if is_success else "fail",
        )

    async def query(
        self,
        task_id: Optional[str] = None,
        agent:   Optional[str] = None,
        status:  Optional[str] = None,
        limit:   int = 100,
    ) -> list[dict[str, Any]]:
        """Query log entries với optional filters.

        Args:
            task_id: Filter theo task ID.
            agent:   Filter theo agent name.
            status:  Filter theo status.
            limit:   Trả về tối đa N entries mới nhất.

        Returns:
            List of entry dicts, mới nhất ở cuối.
        """
        if self.db_url:
            try:
                return await asyncio.to_thread(
                    self._query_postgres, task_id, agent, status, limit
                )
            except Exception:
                logger.exception("Postgres query failed; falling back to file")

        return await asyncio.to_thread(
            self._query_file, task_id, agent, status, limit
        )

    async def tail(self, n: int = 20) -> list[dict[str, Any]]:
        """Trả về N entries mới nhất."""
        return await self.query(limit=n)

    # ------------------------------------------------------------------
    # File storage
    # ------------------------------------------------------------------

    def _ensure_log_dir(self) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.touch()

    async def _write(self, entry: LogEntry) -> None:
        """Append entry vào JSONL file, thread-safe."""
        async with self._lock:
            await asyncio.to_thread(self._append_to_file, entry)

    def _append_to_file(self, entry: LogEntry) -> None:
        """Ghi 1 dòng JSON vào file. Rotate nếu vượt max_entries."""
        entry.prev_hash = self._last_entry_hash()
        entry.entry_hash = compute_entry_hash(entry.to_dict())
        line = entry.to_json() + "\n"

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)

        # Rotate nếu max_entries được set
        if self.max_entries > 0:
            self._rotate_if_needed()

    def _rotate_if_needed(self) -> None:
        """Giữ chỉ max_entries entries mới nhất."""
        try:
            text  = self.log_file.read_text(encoding="utf-8")
            lines = [l for l in text.splitlines() if l.strip()]
            if len(lines) > self.max_entries:
                kept = lines[-self.max_entries:]
                self.log_file.write_text("\n".join(kept) + "\n", encoding="utf-8")
        except OSError:
            pass

    def _last_entry_hash(self) -> str:
        """Return the last known entry hash, or genesis when no hash exists."""
        try:
            lines = [l for l in self.log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        except OSError:
            return GENESIS_HASH

        for line in reversed(lines):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entry_hash = entry.get("entry_hash")
            if isinstance(entry_hash, str) and entry_hash:
                return entry_hash
        return GENESIS_HASH

    def _query_file(
        self,
        task_id: Optional[str],
        agent:   Optional[str],
        status:  Optional[str],
        limit:   int,
    ) -> list[dict[str, Any]]:
        """Read + filter JSONL file."""
        if not self.log_file.exists():
            return []

        results: list[dict[str, Any]] = []
        try:
            text = self.log_file.read_text(encoding="utf-8")
        except OSError:
            return []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if task_id and entry.get("task_id") != task_id:
                continue
            if agent and entry.get("agent") != agent:
                continue
            if status and entry.get("status") != status:
                continue

            results.append(entry)

        return results[-limit:]

    # ------------------------------------------------------------------
    # Postgres storage (optional)
    # ------------------------------------------------------------------

    def _get_postgres_conn(self):
        try:
            import psycopg2
        except ImportError as exc:
            raise RuntimeError("psycopg2 required for LOGGING_DATABASE_URL") from exc
        return psycopg2.connect(self.db_url)

    def _ensure_postgres_schema(self, conn) -> None:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id          BIGSERIAL PRIMARY KEY,
                    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    task_id     TEXT NOT NULL,
                    agent       TEXT NOT NULL,
                    action      TEXT NOT NULL,
                    status      TEXT NOT NULL,
                    details     JSONB NOT NULL DEFAULT '{}'::jsonb
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_task_id ON agent_logs(task_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_agent   ON agent_logs(agent)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_status  ON agent_logs(status)")
        conn.commit()

    def _write_postgres(self, entry: LogEntry) -> None:
        conn = self._get_postgres_conn()
        try:
            self._ensure_postgres_schema(conn)
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO agent_logs (timestamp, task_id, agent, action, status, details)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """, (
                        entry.timestamp, entry.task_id, entry.agent,
                        entry.action, entry.status,
                        json.dumps(entry.details, ensure_ascii=False),
                    ))
        finally:
            conn.close()

    def _query_postgres(
        self,
        task_id: Optional[str],
        agent:   Optional[str],
        status:  Optional[str],
        limit:   int,
    ) -> list[dict[str, Any]]:
        conn = self._get_postgres_conn()
        try:
            self._ensure_postgres_schema(conn)
            conditions = []
            params: list[Any] = []
            if task_id:
                conditions.append("task_id = %s"); params.append(task_id)
            if agent:
                conditions.append("agent = %s");   params.append(agent)
            if status:
                conditions.append("status = %s");  params.append(status)

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            params.append(limit)

            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT timestamp, task_id, agent, action, status, details
                    FROM agent_logs {where}
                    ORDER BY id DESC LIMIT %s
                """, params)
                rows = cur.fetchall()

            return [
                {
                    "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
                    "task_id":   tid,
                    "agent":     ag,
                    "action":    act,
                    "status":    st,
                    "details":   det or {},
                }
                for ts, tid, ag, act, st, det in reversed(rows)
            ]
        finally:
            conn.close()


def compute_entry_hash(entry: dict[str, Any]) -> str:
    """Compute the canonical SHA-256 hash for a log entry."""
    payload = {key: value for key, value in entry.items() if key != "entry_hash"}
    content = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
