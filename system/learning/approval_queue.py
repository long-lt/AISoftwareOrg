"""
system/learning/approval_queue.py
Human Approval Gate — experiences phải được người duyệt trước khi apply.

Nguyên tắc bất di bất dịch: Agent KHÔNG được tự học mà không có người duyệt.

Flow:
    extractor.extract(state) → ApprovalQueue.submit(experience)
                                         → human approve/reject (CLI or dashboard)
                                              → approve: trigger SkillAutoUpdate (Task 14)
                                              → reject: save reason, discard
"""

from __future__ import annotations

import logging
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

from memory.storage import get_storage
from system.skills import SkillVersioner

logger = logging.getLogger(__name__)


class ApprovalQueue:
    """Human approval queue cho experiences.

    Mỗi experience được submit sẽ có status "pending_review".
    Human có thể approve (→ "approved") hoặc reject (→ "rejected").
    Chi tiết (lý do, thời gian) được lưu kèm để audit.

    Args:
        storage: MemoryStorage instance. Default: from get_storage().
    """

    def __init__(self, storage=None):
        self.storage = storage or get_storage()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, experience: Any) -> dict[str, Any]:
        """Submit một experience vào queue chờ duyệt.

        Args:
            experience: Experience object (có method to_dict()) hoặc dict.

        Returns:
            Dict của experience đã được lưu (có id và status).
        """
        item = experience.to_dict() if hasattr(experience, "to_dict") else deepcopy(experience)
        item["status"] = "pending_review"
        item["submitted_at"] = datetime.now(timezone.utc).isoformat()
        if "id" not in item or not item["id"]:
            item["id"] = str(uuid.uuid4())[:8]

        data = self.storage.load()
        data["experiences"].append(item)
        if len(data["experiences"]) > 200:
            data["experiences"] = data["experiences"][-200:]
        self.storage.save(data)
        return item

    def list_pending(self) -> list[dict[str, Any]]:
        """Trả về tất cả experiences đang chờ duyệt."""
        return self._filter(status="pending_review")

    def list_approved(self) -> list[dict[str, Any]]:
        """Trả về tất cả experiences đã được duyệt."""
        return self._filter(status="approved")

    def list_rejected(self) -> list[dict[str, Any]]:
        """Trả về tất cả experiences đã bị từ chối."""
        return self._filter(status="rejected")

    def get(self, exp_id: str) -> Optional[dict[str, Any]]:
        """Tìm experience theo id."""
        data = self.storage.load()
        for exp in data["experiences"]:
            if exp.get("id") == exp_id:
                return exp
        return None

    def approve(self, exp_id: str, approved_by: str = "human") -> Optional[dict[str, Any]]:
        """Approve một experience.

        Chuyển status → "approved", lưu thời gian và người duyệt.
        Sau đó gọi apply_to_skill() để trigger Skill Auto-Update (Task 14).

        Args:
            exp_id: ID của experience cần approve.
            approved_by: Tên người duyệt. Default "human".

        Returns:
            Dict của experience đã cập nhật, hoặc None nếu không tìm thấy.
        """
        data = self.storage.load()
        for i, exp in enumerate(data["experiences"]):
            if exp.get("id") == exp_id:
                data["experiences"][i]["status"] = "approved"
                data["experiences"][i]["approved_at"] = datetime.now(timezone.utc).isoformat()
                data["experiences"][i]["approved_by"] = approved_by
                self.storage.save(data)
                self._apply_to_skill(data["experiences"][i])
                return data["experiences"][i]
        return None

    def reject(
        self,
        exp_id: str,
        reason: str = "",
        rejected_by: str = "human",
    ) -> Optional[dict[str, Any]]:
        """Reject một experience.

        Chuyển status → "rejected", lưu lý do và người từ chối.

        Args:
            exp_id: ID của experience cần reject.
            reason: Lý do từ chối.
            rejected_by: Tên người từ chối. Default "human".

        Returns:
            Dict của experience đã cập nhật, hoặc None nếu không tìm thấy.
        """
        data = self.storage.load()
        for i, exp in enumerate(data["experiences"]):
            if exp.get("id") == exp_id:
                data["experiences"][i]["status"] = "rejected"
                data["experiences"][i]["rejected_at"] = datetime.now(timezone.utc).isoformat()
                data["experiences"][i]["rejected_by"] = rejected_by
                data["experiences"][i]["rejection_reason"] = reason
                self.storage.save(data)
                return data["experiences"][i]
        return None

    def count(self) -> dict[str, int]:
        """Đếm số lượng experiences theo trạng thái."""
        data = self.storage.load()
        counts: dict[str, int] = {"total": 0, "pending_review": 0, "approved": 0, "rejected": 0}
        for exp in data["experiences"]:
            counts["total"] += 1
            status = exp.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _filter(self, status: str) -> list[dict[str, Any]]:
        """Lọc experiences theo status."""
        data = self.storage.load()
        return [exp for exp in data["experiences"] if exp.get("status") == status]

    @staticmethod
    def _apply_to_skill(experience: dict[str, Any]) -> None:
        """Trigger Skill Auto-Update khi experience được approve.

        Chỉ tạo version mới nếu:
        - experience có task_type mapping được (vd: "api" → "create_api")
        - lessons thực sự cải thiện được skill steps
        """
        versioner = SkillVersioner()
        new_version = versioner.create_new_version(experience)
        if new_version:
            logger.info(
                "[ApprovalQueue] Skill updated: task_type=%s → %s (version %s)",
                experience.get("task_type"),
                SkillVersioner._determine_skill_name(experience),
                new_version,
            )
        else:
            logger.info(
                "[ApprovalQueue] No skill update for experience %s "
                "(task_type=%s, no matching skill or no improvements)",
                experience.get("id"),
                experience.get("task_type"),
            )
