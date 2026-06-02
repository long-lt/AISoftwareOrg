"""
agents/pm_agent.py
PM Agent: Nhận yêu cầu mơ hồ từ user → viết spec rõ ràng + danh sách tasks.

Output là JSON có thể parse được, để Planner Agent đọc tiếp.
"""

import json
from config.client import create_llm_client
from core.cost import record_llm_usage
from core.llm import route_model
from system.rbac import Permission, require_permission
from agents.base import BaseAgent, AgentTask, AgentResult


class PMAgent(BaseAgent):
    def __init__(self, client=None):
        super().__init__(
            name="PMAgent", 
            role="Product Manager",
        )
        self._client = client or create_llm_client()

    @require_permission(Permission.READ)
    async def run(self, task: AgentTask) -> AgentResult:
        """Nhận requirement mơ hồ, trả về spec JSON.

        Output JSON schema:
        {
            "feature_name": str,
            "one_line_summary": str,
            "assumptions": [{"ambiguity": str, "decision": str}],
            "acceptance_criteria": [{"given": str, "when": str, "then": str}],
            "tasks": [
                {
                    "id": str,          # "T1", "T2", ...
                    "title": str,
                    "description": str,
                    "depends_on": [],   # list of task ids
                }
            ],
            "out_of_scope": [str]
        }
        """
        prompt = f"""Bạn là một Product Manager. Nhận yêu cầu từ stakeholder và viết spec kỹ thuật rõ ràng.

YÊU CẦU TỪ STAKEHOLDER:
{task.description}

NHIỆM VỤ:
1. Xác định core feature chính (một câu)
2. Liệt kê các điểm mơ hồ và quyết định assumption hợp lý cho từng điểm
3. Viết acceptance criteria theo format GIVEN/WHEN/THEN (tối thiểu 3)
4. Chia thành tasks nhỏ có thể implement được (mỗi task tối đa 4 giờ)
5. Xác định rõ những gì KHÔNG thuộc scope

QUY TẮC:
- Mỗi task phải có output cụ thể (một hàm, một API endpoint, một class)
- Acceptance criteria phải testable — QA viết được test từ đó
- KHÔNG assume technical implementation — đó là việc của Planner
- Nếu requirement quá mơ hồ, đặt assumption hợp lý thay vì hỏi lại

Trả về JSON hợp lệ theo schema sau. Không có text nào ngoài JSON:
{{
    "feature_name": "tên ngắn gọn",
    "one_line_summary": "mô tả trong 1 câu",
    "assumptions": [
        {{"ambiguity": "điểm chưa rõ", "decision": "assumption đã chọn"}}
    ],
    "acceptance_criteria": [
        {{"given": "...", "when": "...", "then": "..."}}
    ],
    "tasks": [
        {{
            "id": "T1",
            "title": "tên task",
            "description": "mô tả chi tiết cần làm gì",
            "depends_on": []
        }}
    ],
    "out_of_scope": ["danh sách những gì không làm"]
}}
"""

        try:
            model = route_model("pm", context_length=len(prompt))
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            await record_llm_usage(task.id, self.name, model, prompt, response)
            raw = (response.choices[0].message.content or "").strip()
            spec = _parse_json(raw)

            if spec is None:
                return AgentResult(
                    success=False,
                    output=raw,
                    reason="Model không trả về JSON hợp lệ",
                )

            return AgentResult(
                success=True,
                output=json.dumps(spec, ensure_ascii=False, indent=2),
                reason=f"Spec tạo thành công: {len(spec.get('tasks', []))} tasks",
            )

        except Exception as e:
            return AgentResult(success=False, output="", reason=str(e))


def _parse_json(text: str) -> dict | None:
    """Parse JSON từ response của model, bỏ qua markdown fences nếu có."""
    text = text.strip()
    # Bỏ markdown code fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Thử tìm JSON object trong text
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None
