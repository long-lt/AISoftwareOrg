"""
core/graph/state.py
Định nghĩa trạng thái trung tâm của workflow.

WorkflowState là một TypedDict — mọi dữ liệu được truyền qua các nodes
đều nằm trong dict này. Đây là "bộ nhớ ngắn hạn" (short-term memory)
của một task đang chạy.
"""

from enum import Enum
from typing import List, Optional, TypedDict


class TaskStatus(str, Enum):
    """Trạng thái vòng đời của một task."""
    PENDING     = "pending"       # Chưa bắt đầu
    IN_PROGRESS = "in_progress"   # Đang chạy
    REVIEW      = "review"        # Đang chờ reviewer
    TESTING     = "testing"       # Đang chạy test
    FIXING      = "fixing"        # Đang sửa lỗi
    DONE        = "done"          # Hoàn thành thành công
    FAILED      = "failed"        # Thất bại (hết max_attempts)
    AWAITING_APPROVAL = "awaiting_approval"  # Đang chờ người duyệt (Task 17)


class WorkflowState(TypedDict):
    """Trạng thái đầy đủ của một workflow task.

    Dict này được truyền qua tất cả các nodes trong LangGraph.
    Mỗi node nhận state, xử lý, rồi trả về state đã cập nhật.

    Fields:
        task_id:        UUID duy nhất của task
        task_desc:      Mô tả yêu cầu gốc từ user/PM
        current_code:   Code Python hiện tại (được tạo hoặc sửa bởi Dev agent)
        previous_code:  Code trước khi fix (để extractor so sánh)
        review_result:  Nhận xét từ Reviewer agent ("approved" / "rejected: ...")
        test_result:    Kết quả từ QA agent ("pass" / "fail: ...")
        fix_attempts:   Số lần đã sửa lỗi (tăng sau mỗi lần Fix agent chạy)
        max_attempts:   Giới hạn tối đa — dừng loop khi fix_attempts >= max_attempts
        status:         Trạng thái hiện tại (TaskStatus enum)
        logs:           Lịch sử mọi hành động theo thứ tự thời gian
        error:          Lỗi hệ thống (không phải lỗi code) nếu có
        cp_id:          UUID của checkpoint đang chờ duyệt (Task 17)
        human_decision: Kết quả duyệt: "approved" / "rejected" / None
        git_branch:     Branch local chứa commit AI-generated code
        git_commit:     Short SHA của commit AI-generated code
        reviewer_feedback: Feedback từ Reviewer qua message bus trước khi Dev retry
    """
    task_id:        str
    task_desc:      str
    current_code:   Optional[str]
    previous_code:  Optional[str]
    review_result:  Optional[str]
    test_result:    Optional[str]
    fix_attempts:   int
    max_attempts:   int
    status:         TaskStatus
    logs:           List[str]
    error:          Optional[str]
    cp_id:          Optional[str]
    human_decision: Optional[str]
    git_branch:     Optional[str]
    git_commit:     Optional[str]
    reviewer_feedback: Optional[str]


from operator import add
from typing import Annotated

class MasterWorkflowState(TypedDict):
    """Trạng thái của Orchestrator (Phase 5).

    Điều phối PM -> Planner -> Dev Pipeline (Parallel).
    """
    requirement:    str
    pm_spec:        Optional[dict]
    plan:           Optional[dict]
    tasks:          List[dict]                  # Danh sách dev tasks từ Planner
    results:        Annotated[List[dict], add]  # Kết quả từ các sub-tasks (fan-out)
    error:          Optional[str]
    logs:           List[str]
    max_attempts:   int                         # Số lần fix tối đa cho mỗi sub-task
    use_docker:     bool                        # True = Docker sandbox
