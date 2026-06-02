"""
system/learning/extractor.py
Experience Extractor — trích xuất bài học kinh nghiệm từ WorkflowState.

Chỉ extract khi task phải fix ít nhất 1 lần (fix_attempts > 0).
Phân tích logs, review_result, test_result để tạo Experience có cấu trúc.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Experience:
    """Một bài học kinh nghiệm được trích xuất từ task."""
    id:            str
    task_id:       str
    task_type:     str           # "api", "file_io", "data_processing", "utility"
    problem:       str           # Lỗi gì đã xảy ra
    solution:      str           # Code fix
    original_code: str           # Code trước khi fix (nếu có từ logs)
    fix_count:     int           # Số lần fix
    review_notes:  str           # Reviewer nhận xét
    status:        str           # "pending_review"
    created_at:    str
    lessons:       list[str]     # Bài học rút ra

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


# Keyword → task_type mapping
_TASK_TYPE_PATTERNS: list[tuple[str, list[str]]] = [
    ("api",              ["api", "endpoint", "route", "fastapi", "flask", "http", "get /", "post /", "rest"]),
    ("data_processing",  ["data", "database", "sql", "query", "json", "model", "class", "schema"]),
    ("file_io",          ["file", "read file", "write file", "csv", "open(", "pathlib"]),
]

# Default type nếu không match
_DEFAULT_TASK_TYPE = "utility"


def detect_task_type(task_desc: str) -> str:
    """Phân loại task dựa trên keyword trong mô tả."""
    normalized = task_desc.lower()
    for task_type, keywords in _TASK_TYPE_PATTERNS:
        if any(kw in normalized for kw in keywords):
            return task_type
    return _DEFAULT_TASK_TYPE


def _extract_lessons(
    logs: list[str],
    review_result: str | None,
    test_result: str | None,
) -> list[str]:
    """Rút ra bài học từ logs, review, và test result."""
    lessons: list[str] = []

    # Từ test_result — lỗi cụ thể
    if test_result and test_result != "pass" and "fail:" in test_result:
        error_msg = test_result.split("fail:", 1)[1].strip()
        if error_msg:
            lessons.append(f"Test failed: {error_msg[:150]}")

    # Từ review_result — reviewer nhận xét
    if review_result and review_result.startswith("rejected"):
        reason = review_result.split(":", 1)[1].strip() if ":" in review_result else review_result
        lessons.append(f"Reviewer feedback: {reason[:150]}")

    # Từ logs — tìm pattern fix
    fix_logs = [l for l in logs if "[Fix]" in l]
    if fix_logs:
        reasons = set()
        for log in fix_logs:
            if "reviewer rejected" in log:
                reasons.add("code quality issue")
            if "qa failed" in log:
                reasons.add("logic/test failure")
        if reasons:
            lessons.append(f"Fix reasons: {', '.join(sorted(reasons))}")

    # Từ logs — số lần retry
    dev_attempts = len([l for l in logs if "[Dev] attempt=" in l])
    if dev_attempts > 1:
        lessons.append(f"Required {dev_attempts} development attempts")

    return lessons


class ExperienceExtractor:
    """Trích xuất Experience từ WorkflowState.

    Chỉ extract khi fix_attempts > 0 — task cần sửa ít nhất 1 lần.
    """

    def extract(self, state: dict[str, Any]) -> Optional[Experience]:
        """Trích xuất experience từ workflow state.

        Args:
            state: WorkflowState dict (hoặc bất kỳ dict có cùng fields).

        Returns:
            Experience nếu fix_attempts > 0, None nếu không có fix.
        """
        fix_attempts = state.get("fix_attempts", 0)
        if fix_attempts == 0:
            return None

        task_desc = state.get("task_desc", "")
        task_type = detect_task_type(task_desc)

        # Problem: lỗi từ test hoặc reviewer
        test_result = state.get("test_result") or ""
        review_result = state.get("review_result") or ""
        problem_parts = []
        if test_result and test_result != "pass":
            problem_parts.append(f"QA: {test_result[:200]}")
        if review_result.startswith("rejected"):
            problem_parts.append(f"Review: {review_result[:200]}")
        problem = "; ".join(problem_parts) if problem_parts else "Unknown issue"

        # Solution: code sau khi fix
        solution = state.get("current_code") or ""

        # Original code: code trước khi fix (lưu bởi fix_node)
        original_code = state.get("previous_code") or ""

        # Review notes
        review_notes = review_result if review_result else ""

        # Lessons
        lessons = _extract_lessons(
            logs=state.get("logs", []),
            review_result=review_result,
            test_result=test_result,
        )

        return Experience(
            id=str(uuid.uuid4())[:8],
            task_id=state.get("task_id", ""),
            task_type=task_type,
            problem=problem,
            solution=solution,
            original_code=original_code,
            fix_count=fix_attempts,
            review_notes=review_notes,
            status="pending_review",
            created_at=datetime.now(timezone.utc).isoformat(),
            lessons=lessons,
        )
