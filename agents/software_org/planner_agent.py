"""
agents/planner_agent.py
Planner Agent: Nhận spec từ PM → thiết kế architecture + tech stack
               → tạo dev tasks chi tiết để giao cho Dev agent.

Output là JSON có thể parse được và đưa thẳng vào dev_pipeline.
"""

import json
from config.client import create_llm_client
from core.cost import record_llm_usage
from core.llm import route_model
from system.rbac import Permission, require_permission
from agents.base import BaseAgent, AgentTask, AgentResult

# Framework quyết định tech stack — inject vào prompt để planner có hướng dẫn
_DECISION_GUIDE = """
NGUYÊN TẮC CHỌN TECH STACK:
- Database: Postgres nếu cần ACID/relations, Redis nếu chỉ cần cache/session. Không dùng MongoDB trừ khi schema thực sự flexible.
- API: REST mặc định. GraphQL chỉ khi frontend cần flexible queries. gRPC chỉ cho internal services.
- Async: Đồng bộ trước, chỉ thêm async/queue khi có task chạy >5s.
- Framework: FastAPI mặc định cho Python API. Không over-engineer.
- Monolith trước, microservices chỉ khi thực sự cần scale độc lập.
""".strip()


class PlannerAgent(BaseAgent):
    def __init__(self, client=None):
        super().__init__(
            name="PlannerAgent", 
            role="Software Architect",
        )
        self._client = client or create_llm_client()

    @require_permission(Permission.READ)
    async def run(self, task: AgentTask) -> AgentResult:
        """Nhận spec JSON từ PM, trả về plan JSON với dev tasks chi tiết.

        Input (task.context): JSON spec từ PMAgent
        Input (task.description): Yêu cầu gốc (fallback nếu không có spec)

        Output JSON schema:
        {
            "architecture_pattern": str,
            "tech_stack": {
                "language": str, "framework": str,
                "database": str, "other": [str]
            },
            "data_models": [
                {
                    "name": str,
                    "fields": [{"name": str, "type": str, "constraints": str}]
                }
            ],
            "dev_tasks": [
                {
                    "id": str,
                    "title": str,
                    "description": str,        # Mô tả đầy đủ cho Dev agent
                    "implementation_notes": str,# Gợi ý kỹ thuật cụ thể
                    "depends_on": []
                }
            ]
        }
        """
        # Parse spec từ PM nếu có
        pm_spec = None
        if task.context:
            try:
                pm_spec = json.loads(task.context)
            except json.JSONDecodeError:
                pass

        spec_text = (
            json.dumps(pm_spec, ensure_ascii=False, indent=2)
            if pm_spec else task.description
        )

        prompt = f"""Bạn là một {self.role}. Thiết kế architecture và tạo dev tasks từ spec sau.

SPEC TỪ PM:
{spec_text}

{_DECISION_GUIDE}

NHIỆM VỤ:
1. Chọn architecture pattern phù hợp (REST API / Event-driven / CRUD service / ...)
2. Quyết định tech stack với lý do rõ ràng
3. Thiết kế data models (chỉ những model thực sự cần)
4. Chia thành dev tasks độc lập, mỗi task:
   - Có description đủ để Dev agent implement ngay, không cần hỏi thêm
   - Có implementation_notes với hints kỹ thuật cụ thể (tên function/class, library nên dùng)
   - Có depends_on chính xác

Trả về JSON hợp lệ theo schema sau. Không có text nào ngoài JSON:
{{
    "architecture_pattern": "mô tả ngắn pattern",
    "tech_stack": {{
        "language": "Python 3.11",
        "framework": "FastAPI",
        "database": "Postgres",
        "other": ["pydantic", "asyncpg"]
    }},
    "data_models": [
        {{
            "name": "TênModel",
            "fields": [
                {{"name": "id", "type": "UUID", "constraints": "primary key, auto-generate"}},
                {{"name": "name", "type": "str", "constraints": "not null, max 200 chars"}}
            ]
        }}
    ],
    "dev_tasks": [
        {{
            "id": "D1",
            "title": "tên task ngắn",
            "description": "mô tả đầy đủ: viết gì, input/output là gì, behavior cụ thể",
            "implementation_notes": "gợi ý: dùng class nào, function nào, library nào",
            "depends_on": []
        }}
    ]
}}
"""

        try:
            model = route_model("planner", context_length=len(prompt))
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            await record_llm_usage(task.id, self.name, model, prompt, response)
            raw = (response.choices[0].message.content or "").strip()
            plan = _parse_json(raw)

            if plan is None:
                return AgentResult(
                    success=False,
                    output=raw,
                    reason="Model không trả về JSON hợp lệ",
                )

            n_tasks = len(plan.get("dev_tasks", []))
            return AgentResult(
                success=True,
                output=json.dumps(plan, ensure_ascii=False, indent=2),
                reason=f"Plan tạo thành công: {n_tasks} dev tasks, stack={plan.get('tech_stack', {}).get('framework', '?')}",
            )

        except Exception as e:
            return AgentResult(success=False, output="", reason=str(e))


def _parse_json(text: str) -> dict | None:
    text = text.strip()
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
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None
