"""
core/memory/long_term.py
Long-term task memory with real semantic embeddings.

Embedding strategy (priority order):
  1. sentence-transformers (all-MiniLM-L6-v2, runs fully local, no API needed)
  2. Postgres + pgvector (when MEMORY_DATABASE_URL is set)
  3. Hash-based fallback (dev/test only — not real semantic similarity)

The sentence-transformers model is lazy-loaded on first use and cached as a
module-level singleton so subsequent calls are instant.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memory.storage import MemoryStorage

logger = logging.getLogger(__name__)

DEFAULT_VECTOR_DIM = 384  # all-MiniLM-L6-v2 output dimension

# ---------------------------------------------------------------------------
# Embedding — real model, lazy singleton
# ---------------------------------------------------------------------------

_model = None          # SentenceTransformer instance (loaded once)
_model_lock = None     # asyncio.Lock — created lazily (needs running loop)
_model_loaded = False  # True once model has been attempted


def _get_lock() -> asyncio.Lock:
    global _model_lock
    if _model_lock is None:
        _model_lock = asyncio.Lock()
    return _model_lock


def _load_model_sync():
    """Load the model synchronously (called from thread pool)."""
    global _model, _model_loaded
    if _model_loaded:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("[Memory] Loading sentence-transformers model all-MiniLM-L6-v2…")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("[Memory] Model loaded. Embedding dim=%d", DEFAULT_VECTOR_DIM)
    except Exception as exc:
        logger.warning("[Memory] sentence-transformers unavailable (%s) — falling back to hash embedding", exc)
        _model = None
    _model_loaded = True
    return _model


async def _get_model():
    """Return the model, loading it on first call (thread-safe)."""
    global _model, _model_loaded
    if _model_loaded:
        return _model
    async with _get_lock():
        if not _model_loaded:
            await asyncio.to_thread(_load_model_sync)
    return _model


async def embed_text_async(text: str) -> list[float]:
    """Embed text using the real model; fall back to hash embedding."""
    model = await _get_model()
    if model is not None:
        try:
            vector = await asyncio.to_thread(
                lambda: model.encode(text, normalize_embeddings=True).tolist()
            )
            return vector
        except Exception as exc:
            logger.warning("[Memory] Embedding failed (%s), using hash fallback", exc)
    return _hash_embed(text)


def embed_text(text: str, dim: int = DEFAULT_VECTOR_DIM) -> list[float]:
    """
    Synchronous embed — tries real model first if already loaded,
    otherwise uses hash fallback. Use embed_text_async() in async contexts.
    """
    global _model, _model_loaded
    if _model_loaded and _model is not None:
        try:
            return _model.encode(text, normalize_embeddings=True).tolist()
        except Exception:
            pass
    return _hash_embed(text, dim)


# ---------------------------------------------------------------------------
# Hash-based fallback (dev / offline)
# ---------------------------------------------------------------------------

import hashlib
import re
import unicodedata

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+", re.UNICODE)

_SYNONYMS = {
    "add": "addition", "sum": "addition", "total": "addition", "plus": "addition",
    "cong": "addition", "tong": "addition", "tinh": "calculate",
    "calculate": "calculate", "compute": "calculate",
    "divide": "division", "division": "division", "chia": "division",
    "validate": "validation", "validation": "validation",
    "api": "api", "endpoint": "api", "route": "api",
    "fix": "fix", "bug": "fix", "error": "fix",
}


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


def _hash_embed(text: str, dim: int = DEFAULT_VECTOR_DIM) -> list[float]:
    """Deterministic fallback embedding — NOT real semantic similarity."""
    vector = [0.0] * dim
    tokens = _TOKEN_RE.findall(_strip_accents(text).lower())
    if not tokens:
        return vector
    for token in tokens:
        canonical = _SYNONYMS.get(token, token)
        for t in {token, canonical}:
            digest = hashlib.sha256(t.encode()).digest()
            idx = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# LongTermMemory
# ---------------------------------------------------------------------------

class LongTermMemory:
    """Async long-term memory store.

    Embeddings are generated with sentence-transformers (local, no API key).
    Falls back to Postgres+pgvector when MEMORY_DATABASE_URL is set.
    Falls back to JSON file storage + hash embeddings when neither is available.
    """

    def __init__(
        self,
        storage: "MemoryStorage | None" = None,
        database_url: str | None = None,
        vector_dim: int = DEFAULT_VECTOR_DIM,
    ):
        from memory.storage import MemoryStorage as _MS
        self.storage = storage or _MS()
        self.database_url = database_url or os.getenv("MEMORY_DATABASE_URL")
        self.vector_dim = vector_dim
        self._postgres_ready = False

    async def save(
        self,
        task_id: str,
        content: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist one memory item with a real semantic embedding."""
        # Use real embedding unless caller supplies one explicitly
        vector = embedding or await embed_text_async(content)

        payload = {
            "task_id": task_id,
            "content": content,
            "embedding": vector,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "embedding_model": "all-MiniLM-L6-v2" if (await _get_model()) else "hash-fallback",
        }

        if self.database_url:
            try:
                await asyncio.to_thread(self._save_postgres, payload)
                return
            except Exception:
                logger.exception("[Memory] Postgres save failed; falling back to file")

        await asyncio.to_thread(self.storage.add_experience, payload)

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Semantic search — uses the same embedding model as save()."""
        query_vec = await embed_text_async(query)

        if self.database_url:
            try:
                return await asyncio.to_thread(self._search_postgres, query_vec, top_k)
            except Exception:
                logger.exception("[Memory] Postgres search failed; falling back to file")

        return await asyncio.to_thread(self._search_file, query_vec, top_k)

    # ------------------------------------------------------------------
    # File storage (JSON + cosine)
    # ------------------------------------------------------------------

    def _search_file(self, query_vec: list[float], top_k: int) -> list[dict[str, Any]]:
        data = self.storage.load()
        scored: list[dict[str, Any]] = []

        for item in data.get("experiences", []):
            content = self._item_content(item)
            embedding = item.get("embedding")

            # Re-embed on the fly if stored embedding has wrong dim
            # (e.g. records written before model was loaded)
            if not isinstance(embedding, list) or len(embedding) != len(query_vec):
                embedding = _hash_embed(content, self.vector_dim)

            score = cosine_similarity(query_vec, embedding)
            if score <= 0:
                continue

            scored.append({
                "task_id": item.get("task_id", ""),
                "content": content,
                "metadata": item.get("metadata", item),
                "created_at": item.get("created_at") or item.get("timestamp"),
                "score": score,
                "embedding_model": item.get("embedding_model", "unknown"),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------
    # Postgres (optional)
    # ------------------------------------------------------------------

    def _ensure_postgres_schema(self, conn: Any) -> None:
        if self._postgres_ready:
            return
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS task_memory (
                    task_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({self.vector_dim}) NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    embedding_model TEXT
                )
            """)
        conn.commit()
        self._postgres_ready = True

    def _connect_postgres(self) -> Any:
        try:
            import psycopg2
        except ImportError as exc:
            raise RuntimeError("psycopg2 required for MEMORY_DATABASE_URL") from exc
        conn = psycopg2.connect(self.database_url)
        self._ensure_postgres_schema(conn)
        return conn

    def _save_postgres(self, payload: dict[str, Any]) -> None:
        vec = "[" + ",".join(f"{v:.8f}" for v in payload["embedding"]) + "]"
        conn = self._connect_postgres()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO task_memory (task_id, content, embedding, metadata, created_at, embedding_model)
                        VALUES (%s, %s, %s::vector, %s::jsonb, %s, %s)
                        ON CONFLICT (task_id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            created_at = EXCLUDED.created_at,
                            embedding_model = EXCLUDED.embedding_model
                    """, (
                        payload["task_id"], payload["content"], vec,
                        json.dumps(payload["metadata"], ensure_ascii=False),
                        payload["created_at"], payload.get("embedding_model"),
                    ))
        finally:
            conn.close()

    def _search_postgres(self, query_vec: list[float], top_k: int) -> list[dict[str, Any]]:
        vec = "[" + ",".join(f"{v:.8f}" for v in query_vec) + "]"
        conn = self._connect_postgres()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT task_id, content, metadata, created_at,
                           1 - (embedding <=> %s::vector) AS score
                    FROM task_memory
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (vec, vec, top_k))
                rows = cur.fetchall()
        finally:
            conn.close()
        return [
            {
                "task_id": r[0], "content": r[1],
                "metadata": r[2] or {}, "created_at": r[3],
                "score": float(r[4] or 0),
            }
            for r in rows
        ]

    @staticmethod
    def _item_content(item: dict[str, Any]) -> str:
        if isinstance(item.get("content"), str):
            return item["content"]
        return "\n".join(filter(None, [
            str(item.get("task_desc", "")),
            str(item.get("output_summary", "")),
            " ".join(str(l) for l in item.get("final_logs", [])),
        ]))