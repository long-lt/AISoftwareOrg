"""
agents/devops_agent.py
DevOps Agent: Quản lý infra, deploy và các task critical.
"""

from agents.base import BaseAgent, AgentTask, AgentResult
from system.rbac import Permission, require_permission

class DevOpsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="DevOpsAgent",
            role="DevOps Engineer"
        )

    @require_permission(Permission.CRITICAL)
    async def deploy(self, task: AgentTask) -> AgentResult:
        """Thực hiện deploy (Action này yêu cầu quyền CRITICAL)."""
        return AgentResult(
            success=True,
            output=f"🚀 Deploy thành công cho task {task.id}",
            reason="Agent có đầy đủ quyền CRITICAL"
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Hành động mặc định cho DevOps."""
        return AgentResult(
            success=True,
            output="DevOps Agent is ready.",
            reason="No specific run action defined."
        )
