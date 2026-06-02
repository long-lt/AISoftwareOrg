"""
agents/dev_agent.py
Dev Agent: Viết code Python theo yêu cầu, sửa lỗi khi được retry.

Khi retry (fix_attempts > 0), context từ engine.py sẽ chứa:
    - Code hiện tại đang lỗi
    - Lỗi cụ thể từ QA
    - Nhận xét từ Reviewer (nếu bị reject)
"""

from config import DEV_MODEL
from config.client import create_llm_client
from core.cost import record_llm_usage
from core.llm import route_model
from system.skills import SkillRegistry, SkillRegistryError
from system.rbac import Permission, require_permission
from agents.base import BaseAgent, AgentTask, AgentResult


_CODING_RULES = """
QUY TẮC VIẾT CODE (bắt buộc):
- Type hints đầy đủ cho parameters và return value
- Docstring ngắn cho function/class public
- try/except cho các operation có thể fail (file, network, DB)
- Validate input trước khi xử lý (raise ValueError nếu invalid)
- Không hardcode credentials hay magic numbers
- Không dùng bare except: — luôn catch exception cụ thể
""".strip()


class DevAgent(BaseAgent):
    def __init__(self, client=None):
        super().__init__(
            name="DevAgent", 
            role="Backend Developer",
        )
        self._client = client or create_llm_client(model=DEV_MODEL)

    @require_permission(Permission.WRITE)
    async def run(self, task: AgentTask) -> AgentResult:
        # Nếu context có chứa "CODE HIỆN TẠI" thì chắc chắn là retry
        is_fix_mode = task.context and "CODE HIỆN TẠI" in task.context

        if is_fix_mode:
            prompt = self._build_fix_prompt(task)
        else:
            prompt = self._build_initial_prompt(task)

        try:
            model = route_model("dev", context_length=len(prompt), is_retry=bool(is_fix_mode))
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            await record_llm_usage(task.id, self.name, model, prompt, response)
            code = self._strip_markdown(
                response.choices[0].message.content or ""
            )

            if not code.strip():
                return AgentResult(
                    success=False,
                    output="",
                    reason="Model trả về empty response",
                )

            return AgentResult(success=True, output=code)

        except Exception as e:
            return AgentResult(success=False, output="", reason=str(e))

    @require_permission(Permission.CRITICAL)
    async def deploy(self, task: AgentTask) -> AgentResult:
        """Dev agents are intentionally not allowed to deploy."""
        return AgentResult(
            success=True,
            output=f"Deploy requested for task {task.id}",
            reason="This should be unreachable without critical permission",
        )

    def _build_initial_prompt(self, task: AgentTask) -> str:
        context_block = f"\nBỐI CẢNH VÀ KINH NGHIỆM QUÁ KHỨ:\n{task.context}\n" if task.context else ""

        prompt = f"""Bạn là một {self.role} xuất sắc. Viết code Python cho yêu cầu sau.
{context_block}
YÊU CẦU:
{task.description}

{_CODING_RULES}

Chỉ trả về code Python thuần túy. Không markdown, không giải thích.
"""
        return self._inject_matching_skills(prompt, task)

    def _build_fix_prompt(self, task: AgentTask) -> str:
        return f"""Bạn là một {self.role} xuất sắc. Code bên dưới bị lỗi và cần sửa.

YÊU CẦU GỐC:
{task.description}

{task.context}

NHIỆM VỤ: Sửa code để fix đúng lỗi được mô tả ở trên.
- Chỉ thay đổi những gì cần thiết để fix lỗi
- Không refactor, không đổi tên biến, không thêm feature
- Đảm bảo code vẫn đáp ứng yêu cầu gốc

{_CODING_RULES}

Chỉ trả về code Python đã sửa. Không markdown, không giải thích.
"""

    @staticmethod
    def _strip_markdown(text: str) -> str:
        text = text.strip()
        if text.startswith("```python"):
            text = text[9:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    @staticmethod
    def _inject_matching_skills(prompt: str, task: AgentTask) -> str:
        if "HUONG DAN SKILL" in prompt:
            return prompt
        registry = SkillRegistry()
        try:
            skill_names = registry.match_for_task("dev_agent", task.description)
            for skill_name in skill_names:
                prompt = registry.inject_into_prompt(prompt, skill_name)
        except SkillRegistryError:
            return prompt
        return prompt
