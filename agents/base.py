"""
agents/base.py
Base classes cho mọi agent trong hệ thống.
"""

from typing import Optional
from pydantic import BaseModel


class AgentTask(BaseModel):
    """Đầu vào cho một Agent."""
    id:          str
    description: str
    context:     Optional[str] = None   # Code cũ, lỗi trước đó, v.v.


class AgentResult(BaseModel):
    """Kết quả trả về từ một Agent."""
    success:  bool
    output:   str           # Code, review comment, test result
    reason:   Optional[str] = None


class BaseAgent:
    """Base class cho mọi agent."""
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def validate_permission(self, permission: str):
        """Kiểm tra quyền hạn của agent dựa trên self.role."""
        from system.rbac import Permission, has_permission, PermissionDenied
        
        if not has_permission(self.role, Permission(permission)):
             raise PermissionDenied(
                f"Agent '{self.name}' with role '{self.role}' "
                f"does not have permission '{permission}'"
            )

    async def run(self, task: AgentTask) -> AgentResult:
        """Thực thi công việc được giao. Phải được implement ở subclass."""
        raise NotImplementedError("Subclasses must implement run()")
