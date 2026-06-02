"""
memory/postgres_storage.py
Postgres-backed storage for production use.

Replaces JSON file storage when STORAGE_BACKEND=postgres.
Thread-safe via connection pooling and transactions.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class PostgresStorageError(RuntimeError):
    """Raised when Postgres storage cannot be safely read or written."""


def _empty_memory() -> dict[str, Any]:
    return {"version": "1.0", "experiences": [], "facts": []}


class PostgresStorage:
    """Postgres-backed storage for production.

    Stores all data in a single JSONB column for compatibility with
    the existing MemoryStorage interface.

    Args:
        database_url: PostgreSQL connection string.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        # Re-entrant lock is required because add_experience() calls load()/save().
        self._lock = threading.RLock()
        self._ensure_schema()

    def _connect(self):
        """Create a new database connection."""
        try:
            import psycopg2
        except ImportError as exc:
            raise PostgresStorageError(
                "psycopg2 required for Postgres storage. "
                "Install with: pip install psycopg2-binary"
            ) from exc
        return psycopg2.connect(self.database_url)

    def _ensure_schema(self) -> None:
        """Create storage_data table if it doesn't exist."""
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS storage_data (
                            key TEXT PRIMARY KEY,
                            value JSONB NOT NULL,
                            updated_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
            logger.info("[PostgresStorage] Schema ready")
        except Exception as exc:
            raise PostgresStorageError(f"Failed to create schema: {exc}") from exc
        finally:
            conn.close()

    def load(self) -> dict[str, Any]:
        """Load data from Postgres.

        Returns:
            Dict with version, experiences, facts, etc.
        """
        with self._lock:
            conn = self._connect()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT value FROM storage_data WHERE key = 'main'")
                    row = cur.fetchone()
                    if row:
                        data = row[0]
                        if not isinstance(data, dict):
                            raise PostgresStorageError("storage_data.value must be a JSON object")
                        # Normalize
                        normalized = _empty_memory()
                        normalized.update(data)
                        if not isinstance(normalized.get("experiences"), list):
                            raise PostgresStorageError("Field 'experiences' must be a list")
                        if not isinstance(normalized.get("facts"), list):
                            raise PostgresStorageError("Field 'facts' must be a list")
                        return normalized
                    return _empty_memory()
            except PostgresStorageError:
                raise
            except Exception as exc:
                raise PostgresStorageError(f"Failed to load from Postgres: {exc}") from exc
            finally:
                conn.close()

    def save(self, data: dict[str, Any]) -> None:
        """Save data to Postgres.

        Args:
            data: Dict with version, experiences, facts, etc.
        """
        payload = dict(data)
        payload.setdefault("version", "1.0")
        payload.setdefault("experiences", [])
        payload.setdefault("facts", [])
        payload["last_updated"] = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._connect()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO storage_data (key, value, updated_at)
                            VALUES ('main', %s::jsonb, NOW())
                            ON CONFLICT (key) DO UPDATE SET
                                value = EXCLUDED.value,
                                updated_at = EXCLUDED.updated_at
                        """, (json.dumps(payload, ensure_ascii=False),))
            except Exception as exc:
                raise PostgresStorageError(f"Failed to save to Postgres: {exc}") from exc
            finally:
                conn.close()

    def add_experience(self, experience: dict[str, Any]) -> None:
        """Add an experience to the experiences list.

        Args:
            experience: Experience dict to add.
        """
        with self._lock:
            data = self.load()
            item = dict(experience)
            item["timestamp"] = datetime.now(timezone.utc).isoformat()
            data["experiences"].append(item)
            if len(data["experiences"]) > 100:
                data["experiences"] = data["experiences"][-100:]
            self.save(data)
