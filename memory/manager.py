"""
memory/manager.py
High-level API for recording and injecting task memory.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.memory.long_term import LongTermMemory
from .storage import MemoryStorage, get_storage

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, storage: MemoryStorage | None = None, long_term: LongTermMemory | None = None):
        self.storage = storage or get_storage()
        self.long_term = long_term or LongTermMemory(storage=self.storage)

    async def record_task_outcome(
        self,
        task_id: str,
        task_desc: str,
        success: bool,
        output: str,
        logs: list[str],
        fix_attempts: int = 0,
        review_result: str | None = None,
        test_result: str | None = None,
    ) -> None:
        """Ghi lại kết quả của một task để làm kinh nghiệm."""
        code = output or ""
        metadata: dict[str, Any] = {
            "task_id": task_id,
            "task_desc": task_desc,
            "success": success,
            "code": code,
            "fix_attempts": fix_attempts,
            "review_result": review_result,
            "test_result": test_result,
            "logs": logs or [],
        }

        content = "\n".join(
            [
                f"Task: {task_desc}",
                f"Success: {success}",
                f"Fix attempts: {fix_attempts}",
                f"Review result: {review_result or ''}",
                f"Test result: {test_result or ''}",
                "Generated code:",
                code,
                "Logs:",
                "\n".join(logs or []),
            ]
        )

        try:
            await self.long_term.save(task_id=task_id, content=content, metadata=metadata)
        except Exception:
            logger.exception("Failed to record task outcome to memory")

    async def record_experience(self, experience) -> None:
        """Ghi một Experience object vào memory storage."""
        try:
            await asyncio.to_thread(
                self.storage.add_experience,
                experience.to_dict(),
            )
        except Exception:
            logger.exception("Failed to record experience to memory")

    async def get_relevant_context(self, current_task_desc: str, limit: int = 3) -> str:
        """Tìm các kinh nghiệm cũ có liên quan đến task hiện tại."""
        try:
            results = await self.long_term.search(current_task_desc, top_k=limit)
        except Exception:
            logger.exception("Failed to search task memory")
            return ""
        if not results:
            return ""

        context_lines = ["Dưới đây là các kinh nghiệm từ các task tương tự trong quá khứ:"]
        for item in results:
            metadata = item.get("metadata") or {}
            status = "THÀNH CÔNG" if metadata.get("success") else "THẤT BẠI"
            task_desc = metadata.get("task_desc") or item.get("task_id", "unknown")
            context_lines.append(f"- Task: {task_desc}")
            context_lines.append(f"  Kết quả: {status}")
            context_lines.append(f"  Fix attempts: {metadata.get('fix_attempts', 0)}")
            if metadata.get("test_result"):
                context_lines.append(f"  QA: {metadata['test_result']}")
            logs = metadata.get("logs") or []
            if logs:
                context_lines.append(f"  Bài học: {logs[-1]}")
            code = metadata.get("code") or ""
            if code:
                preview = code if len(code) <= 1200 else code[:1200] + "\n...(truncated)"
                context_lines.append(f"  Code đã tạo:\n{preview}")

        return "\n".join(context_lines)

    def record_task_outcome_sync(self, *args: Any, **kwargs: Any) -> None:
        if _has_running_loop():
            raise RuntimeError("Use await record_task_outcome(...) inside an event loop")
        asyncio.run(self.record_task_outcome(*args, **kwargs))

    def get_relevant_context_sync(self, *args: Any, **kwargs: Any) -> str:
        if _has_running_loop():
            raise RuntimeError("Use await get_relevant_context(...) inside an event loop")
        return asyncio.run(self.get_relevant_context(*args, **kwargs))


def _has_running_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True
