"""
memory/storage.py
JSON storage for local long-term memory fallback.

Thread-safe via file locking (fcntl.flock on Unix, threading.Lock fallback).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_FILE = PROJECT_ROOT / "storage" / "memory.json"

# File locking — fcntl on Unix, no-op fallback
_Fcntl = None
if os.name == "posix":
    import fcntl as _Fcntl  # type: ignore[no-redef]

_LOCK = threading.Lock()  # in-process safety


def _acquire_file_lock(f):
    """Acquire exclusive file lock. Cross-process safe on Unix."""
    if _Fcntl:
        _Fcntl.flock(f, _Fcntl.LOCK_EX)


def _release_file_lock(f):
    """Release file lock."""
    if _Fcntl:
        _Fcntl.flock(f, _Fcntl.LOCK_UN)


class MemoryStorageError(RuntimeError):
    """Raised when memory storage cannot be safely read or written."""


def _empty_memory() -> dict[str, Any]:
    return {"version": "1.0", "experiences": [], "facts": []}


class MemoryStorage:
    def __init__(self, file_path: str | Path | None = None):
        raw_path = Path(file_path) if file_path is not None else DEFAULT_MEMORY_FILE
        self.file_path = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.save(_empty_memory())

    def load(self) -> dict[str, Any]:
        with _LOCK:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    _acquire_file_lock(f)
                    data = json.load(f)
            except FileNotFoundError:
                return _empty_memory()
            except json.JSONDecodeError as exc:
                raise MemoryStorageError(f"Memory file is corrupt: {self.file_path}") from exc
            except OSError as exc:
                raise MemoryStorageError(f"Cannot read memory file: {self.file_path}") from exc

            if not isinstance(data, dict):
                raise MemoryStorageError(f"Memory file must contain a JSON object: {self.file_path}")

            normalized = _empty_memory()
            normalized.update(data)
            if not isinstance(normalized.get("experiences"), list):
                raise MemoryStorageError("Memory field 'experiences' must be a list")
            if not isinstance(normalized.get("facts"), list):
                raise MemoryStorageError("Memory field 'facts' must be a list")
            return normalized

    def save(self, data: dict[str, Any]):
        payload = deepcopy(data)
        payload.setdefault("version", "1.0")
        payload.setdefault("experiences", [])
        payload.setdefault("facts", [])
        payload["last_updated"] = datetime.now(timezone.utc).isoformat()

        with _LOCK:
            temp_path = self.file_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                temp_path.replace(self.file_path)
            except OSError as exc:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
                raise MemoryStorageError(f"Cannot write memory file: {self.file_path}") from exc

    def add_experience(self, experience: dict[str, Any]):
        data = self.load()
        item = deepcopy(experience)
        item["timestamp"] = datetime.now(timezone.utc).isoformat()
        data["experiences"].append(item)
        if len(data["experiences"]) > 100:
            data["experiences"] = data["experiences"][-100:]
        self.save(data)


class TenantAwareStorage:
    """Namespace any storage backend by team_id.

    The wrapped storage keeps a top-level ``teams`` object. Each team receives
    its own memory-shaped document, so experiences, facts, approval queue items,
    and checkpoints do not leak across teams.
    """

    def __init__(self, team_id: str, base_storage: MemoryStorage | Any):
        self.team_id = _normalize_team_id(team_id)
        self.base_storage = base_storage

    def load(self) -> dict[str, Any]:
        data = self.base_storage.load()
        teams = data.setdefault("teams", {})
        team_data = deepcopy(teams.get(self.team_id, _empty_memory()))
        normalized = _empty_memory()
        normalized.update(team_data)
        normalized["team_id"] = self.team_id
        return normalized

    def save(self, data: dict[str, Any]) -> None:
        all_data = self.base_storage.load()
        teams = all_data.setdefault("teams", {})
        payload = deepcopy(data)
        payload.pop("team_id", None)
        payload.setdefault("version", "1.0")
        payload.setdefault("experiences", [])
        payload.setdefault("facts", [])
        payload["last_updated"] = datetime.now(timezone.utc).isoformat()
        teams[self.team_id] = payload
        self.base_storage.save(all_data)

    def add_experience(self, experience: dict[str, Any]) -> None:
        data = self.load()
        item = deepcopy(experience)
        item["team_id"] = self.team_id
        item["timestamp"] = datetime.now(timezone.utc).isoformat()
        data["experiences"].append(item)
        if len(data["experiences"]) > 100:
            data["experiences"] = data["experiences"][-100:]
        self.save(data)


def get_storage(backend: str | None = None) -> MemoryStorage | Any:
    """Factory: return storage based on STORAGE_BACKEND env.

    Args:
        backend: Storage backend. Default: from env or "json".

    Returns:
        MemoryStorage (JSON) or PostgresStorage (Postgres).

    Raises:
        RuntimeError: If backend=postgres but MEMORY_DATABASE_URL not set.
    """
    backend = backend or os.getenv("STORAGE_BACKEND", "json")
    team_id = os.getenv("TEAM_ID", "").strip()

    if backend == "postgres":
        database_url = os.getenv("MEMORY_DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "STORAGE_BACKEND=postgres requires MEMORY_DATABASE_URL. "
                "Set it in .env: MEMORY_DATABASE_URL=postgresql://user:pass@localhost/aiorg"
            )
        from .postgres_storage import PostgresStorage
        logger.info("[Storage] Using PostgresStorage")
        storage = PostgresStorage(database_url)
        return TenantAwareStorage(team_id, storage) if team_id else storage

    logger.info("[Storage] Using MemoryStorage (JSON)")
    memory_file = os.getenv("MEMORY_FILE")
    storage = MemoryStorage(memory_file) if memory_file else MemoryStorage()
    return TenantAwareStorage(team_id, storage) if team_id else storage


def _normalize_team_id(team_id: str) -> str:
    normalized = team_id.strip()
    if not normalized:
        raise ValueError("team_id must not be empty")
    safe = []
    for char in normalized:
        if char.isalnum() or char in {"-", "_", "."}:
            safe.append(char)
        else:
            safe.append("-")
    result = "".join(safe).strip(".-_")
    if not result:
        raise ValueError(f"Invalid team_id: {team_id!r}")
    return result
