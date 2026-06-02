"""
system/learning/checkpoint_store.py
Human-in-the-Loop Checkpoint Store (Phase 5, Task 17).

Lưu trạng thái các checkpoint đang chờ người duyệt.
Khi pipeline gặp checkpoint, nó lưu entry ở đây và poll đến khi
human approve/reject qua dashboard.

Flow:
    pipeline chạy → needs_human_approval() == True
                    → CheckpointStore.submit()
                    → pipeline poll: get(id) until status != "pending"
                    → human clicks "Approve" on dashboard
                    → CheckpointStore.approve(id)
                    → pipeline thấy status="approved" → tiếp tục
"""

from __future__ import annotations

import logging
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

from memory.storage import get_storage

logger = logging.getLogger(__name__)

STORAGE_KEY = "checkpoints"


class CheckpointStore:
    """Lưu và quản lý các checkpoint chờ duyệt.

    Args:
        storage: MemoryStorage instance. Default: from get_storage().
    """

    def __init__(self, storage=None):
        self.storage = storage or get_storage()
        self._lock = threading.Lock()

    def submit(
        self,
        task_id: str,
        reason: str,
        task_desc: str = "",
        fix_attempts: int = 0,
    ) -> dict[str, Any]:
        """Tạo checkpoint mới chờ duyệt.

        Args:
            task_id: ID của task đang chạy.
            reason: Lý do cần duyệt (vd: "High fix attempts", "Dangerous task").
            task_desc: Mô tả task (để hiển thị trên dashboard).
            fix_attempts: Số lần fix hiện tại.

        Returns:
            Dict checkpoint đã lưu.
        """
        cp = {
            "id": str(uuid.uuid4())[:8],
            "task_id": task_id,
            "task_desc": task_desc[:200],
            "reason": reason,
            "fix_attempts": fix_attempts,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "approved_at": None,
            "approved_by": None,
            "rejected_at": None,
            "rejected_by": None,
            "rejection_reason": None,
        }
        data = self.storage.load()
        checkpoints = data.setdefault(STORAGE_KEY, [])
        checkpoints.append(cp)
        # Giữ tối đa 100 checkpoints
        if len(checkpoints) > 100:
            data[STORAGE_KEY] = checkpoints[-100:]
        self.storage.save(data)
        return cp

    def get(self, cp_id: str) -> Optional[dict[str, Any]]:
        """Tìm checkpoint theo id."""
        data = self.storage.load()
        for cp in data.get(STORAGE_KEY, []):
            if cp.get("id") == cp_id:
                return cp
        return None

    def approve(self, cp_id: str, approved_by: str = "human") -> Optional[dict[str, Any]]:
        """Approve checkpoint — cho phép pipeline tiếp tục.

        Returns:
            Dict checkpoint đã cập nhật, None nếu không tìm thấy.
        """
        with self._lock:
            data = self.storage.load()
            for i, cp in enumerate(data.get(STORAGE_KEY, [])):
                if cp.get("id") == cp_id:
                    data[STORAGE_KEY][i]["status"] = "approved"
                    data[STORAGE_KEY][i]["approved_at"] = datetime.now(timezone.utc).isoformat()
                    data[STORAGE_KEY][i]["approved_by"] = approved_by
                    self.storage.save(data)
                    return data[STORAGE_KEY][i]
        return None

    def reject(
        self,
        cp_id: str,
        reason: str = "",
        rejected_by: str = "human",
    ) -> Optional[dict[str, Any]]:
        """Reject checkpoint — pipeline sẽ dừng task với lỗi.

        Returns:
            Dict checkpoint đã cập nhật, None nếu không tìm thấy.
        """
        with self._lock:
            data = self.storage.load()
            for i, cp in enumerate(data.get(STORAGE_KEY, [])):
                if cp.get("id") == cp_id:
                    data[STORAGE_KEY][i]["status"] = "rejected"
                    data[STORAGE_KEY][i]["rejected_at"] = datetime.now(timezone.utc).isoformat()
                    data[STORAGE_KEY][i]["rejected_by"] = rejected_by
                    data[STORAGE_KEY][i]["rejection_reason"] = reason
                    self.storage.save(data)
                    return data[STORAGE_KEY][i]
        return None

    def list_pending(self) -> list[dict[str, Any]]:
        """Trả về tất cả checkpoints đang chờ duyệt."""
        return self._filter("pending")

    def list_approved(self) -> list[dict[str, Any]]:
        """Trả về tất cả checkpoints đã duyệt."""
        return self._filter("approved")

    def list_rejected(self) -> list[dict[str, Any]]:
        """Trả về tất cả checkpoints bị từ chối."""
        return self._filter("rejected")

    def count(self) -> dict[str, int]:
        """Đếm số lượng checkpoints theo trạng thái."""
        data = self.storage.load()
        counts = {"pending": 0, "approved": 0, "rejected": 0}
        for cp in data.get(STORAGE_KEY, []):
            status = cp.get("status", "unknown")
            if status in counts:
                counts[status] += 1
        return counts

    def _filter(self, status: str) -> list[dict[str, Any]]:
        data = self.storage.load()
        return [cp for cp in data.get(STORAGE_KEY, []) if cp.get("status") == status]
