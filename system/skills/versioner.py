"""
system/skills/versioner.py
Skill Auto-Update — tạo version mới của skill từ approved experience.

Nguyên tắc:
    - KHÔNG xoá file skill cũ — giữ lại tất cả versions
    - Lesson từ experience được chuyển thành steps mới
    - Chỉ tạo version mới nếu có lessons thực sự cải thiện skill

Flow:
    experience approved → SkillVersioner.create_new_version(experience)
                          → determine_skill_name() từ task_type
                          → bump_version() (v1 → v2)
                          → improved_steps() từ lessons
                          → save file mới
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

from .registry import SkillRegistry, SkillRegistryError

logger = logging.getLogger(__name__)

# Map: task_type (từ Experience Extractor) → skill name
TASK_TYPE_SKILL_MAP: dict[str, str] = {
    "api": "create_api",
    "data_processing": "process_data",
    "file_io": "handle_files",
}


class SkillVersioner:
    """Tạo version mới của skill từ approved experience.

    Args:
        registry: SkillRegistry instance. Default: SkillRegistry().
    """

    def __init__(self, registry: SkillRegistry | None = None):
        self.registry = registry or SkillRegistry()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_new_version(self, experience: dict[str, Any]) -> Optional[str]:
        """Tạo version mới của skill từ approved experience.

        Args:
            experience: Dict của approved experience (có task_type, lessons, ...).

        Returns:
            Version string (e.g. "v2") nếu tạo thành công, None nếu không có skill match.
        """
        skill_name = self._determine_skill_name(experience)
        if not skill_name:
            logger.info(
                "No skill matches task_type=%s for experience %s",
                experience.get("task_type"),
                experience.get("id"),
            )
            return None

        try:
            current = self.registry.get(skill_name)
        except SkillRegistryError:
            logger.warning("Skill %s not found — cannot create new version", skill_name)
            return None

        new_version = self._bump_version(current["version"])
        new_steps = self._improved_steps(current["steps"], experience)

        if new_steps == current["steps"]:
            logger.info(
                "No improvements from experience %s — skipping version bump",
                experience.get("id"),
            )
            return None

        new_skill = deepcopy(current)
        new_skill["version"] = new_version
        new_skill["steps"] = new_steps
        new_skill["created_from"] = experience.get("id", "")
        new_skill["created_at"] = datetime.now(timezone.utc).isoformat()
        new_skill["source_task_id"] = experience.get("task_id", "")

        lessons = experience.get("lessons", [])
        if lessons:
            new_skill["notes"] = lessons

        save_path = self.registry._skill_dir(skill_name) / f"{new_version}.json"
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(new_skill, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.error("Failed to write skill file %s: %s", save_path, exc)
            return None

        logger.info(
            "Created %s/%s from experience %s (%d steps, %d lessons)",
            skill_name,
            new_version,
            experience.get("id"),
            len(new_steps),
            len(lessons),
        )
        return new_version

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_skill_name(experience: dict[str, Any]) -> Optional[str]:
        """Map task_type của experience → skill name.

        Nếu không có mapping, trả về None (không thể auto-update skill).
        """
        task_type = experience.get("task_type", "")
        return TASK_TYPE_SKILL_MAP.get(task_type)

    @staticmethod
    def _bump_version(version: str) -> str:
        """Tăng version: v1 → v2, v2 → v3, ..."""
        try:
            num = int(version.lstrip("v"))
            return f"v{num + 1}"
        except (ValueError, AttributeError):
            return "v1"

    @staticmethod
    def _improved_steps(
        current_steps: list[str],
        experience: dict[str, Any],
    ) -> list[str]:
        """Cải thiện skill steps từ lessons của experience.

        Dùng template-based approach (không gọi LLM):
        - Lesson về test failure → thêm step kiểm tra edge case
        - Lesson về reviewer feedback → thêm step về code quality
        - Lesson về fix reasons → thêm step phòng ngừa lỗi tương tự

        Args:
            current_steps: Steps hiện tại của skill.
            experience: Approved experience chứa lessons.

        Returns:
            List steps mới (chỉ thêm, không xoá step cũ).
        """
        lessons = experience.get("lessons", [])
        if not lessons:
            return current_steps

        new_steps = list(current_steps)
        added: set[str] = set()

        for lesson in lessons:
            step = _lesson_to_step(lesson)
            if step and step not in added and step not in new_steps:
                new_steps.append(step)
                added.add(step)

        return new_steps


def _lesson_to_step(lesson: str) -> Optional[str]:
    """Chuyển một lesson string thành skill step.

    Returns:
        Step string, hoặc None nếu không thể chuyển đổi.
    """
    lesson_lower = lesson.lower()

    if lesson_lower.startswith("test failed"):
        error = lesson[len("test failed:"):].strip()
        if not error:
            return "Write comprehensive tests for edge cases"
        
        # Heuristics cho các lỗi thường gặp
        if "none" in error.lower() or "null" in error.lower():
            return f"Handle None/Null cases: {error[:80]}"
        if "not found" in error.lower() or "404" in error.lower():
            return f"Validate existence before access: {error[:80]}"
        if "timeout" in error.lower():
            return "Implement timeout handling and retries"
        
        return f"Prevent regression: {error[:120]}"

    if lesson_lower.startswith("reviewer feedback"):
        feedback = lesson[len("reviewer feedback:"):].strip()
        if feedback:
            return f"Code quality: {feedback[:120]}"
        return "Follow code review guidelines before submitting"

    if "logic/test failure" in lesson_lower:
        return "Double check business logic and edge cases"

    if "code quality issue" in lesson_lower:
        return "Ensure code follows organization's style guide and best practices"

    if lesson_lower.startswith("required "):
        return "Plan for iterative development — keep components modular"

    return None
