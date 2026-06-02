"""
agents/reviewer_agent.py
Reviewer Agent: Review code, trả về "approved" hoặc "rejected: <lý do>".
"""

from config import REVIEWER_MODEL
from config.client import create_llm_client
from core.cost import record_llm_usage
from core.llm import route_model
from system.rbac import Permission, require_permission
from agents.base import BaseAgent, AgentTask, AgentResult

# Checklist review — inject vào prompt để reviewer có hướng dẫn cụ thể
_REVIEW_CHECKLIST = """
CHECKLIST REVIEW (kiểm tra theo thứ tự):
1. CORRECTNESS  — Code có thực hiện đúng yêu cầu không? Logic có đúng không?
2. ERROR HANDLING — Có try/except cho các operation có thể fail không?
3. INPUT VALIDATION — Input có được kiểm tra trước khi dùng không?
4. SECURITY — Có hardcoded credential, SQL injection, hay lỗ hổng rõ ràng không?
5. CODE QUALITY — Có magic numbers/strings? Function có quá dài không (>50 lines)?
""".strip()

_SEVERITY = """
- CRITICAL issue (bất kỳ 1 trong những cái này) → REJECTED:
    • Logic sai, code không thực hiện đúng yêu cầu
    • Lỗ hổng bảo mật rõ ràng
    • Không handle exception cho DB/file/network calls
- MINOR issue → APPROVED (kèm ghi chú cải thiện)
""".strip()


class ReviewerAgent(BaseAgent):
    def __init__(self, client=None):
        super().__init__(
            name="ReviewerAgent", 
            role="Senior Software Engineer",
        )
        self._client = client or create_llm_client(model=REVIEWER_MODEL)

    @require_permission(Permission.READ)
    async def run(self, task: AgentTask) -> AgentResult:
        code_to_review = task.context or ""

        prompt = f"""Bạn là một {self.role} đang review code của teammate.

YÊU CẦU GỐC:
{task.description}

CODE CẦN REVIEW:
```python
{code_to_review}
```

{_REVIEW_CHECKLIST}

{_SEVERITY}

QUY TẮC OUTPUT BẮT BUỘC:
Dòng đầu tiên PHẢI là một trong hai dạng sau (viết hoa chính xác):
    APPROVED: <nhận xét ngắn>
    REJECTED: <lý do cụ thể, liệt kê vấn đề>

Các dòng tiếp theo có thể giải thích thêm chi tiết nếu cần.

Ví dụ output hợp lệ:
    APPROVED: Code đúng logic, có error handling, không có vấn đề bảo mật.
    REJECTED: Missing error handling cho database call ở line 12; thiếu input validation cho tham số `user_id`.
"""

        try:
            model = route_model("reviewer", context_length=len(prompt))
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            await record_llm_usage(task.id, self.name, model, prompt, response)
            raw = (response.choices[0].message.content or "").strip()

            verdict, output = self._parse_verdict(raw)

            return AgentResult(
                success=True,
                output=output,      # "approved" hoặc "rejected: <lý do>"
                reason=raw,         # Full response để debug
            )

        except Exception as e:
            # Khi API fail, mặc định là rejected để không deploy code chưa review
            return AgentResult(
                success=False,
                output="rejected: reviewer agent error",
                reason=str(e),
            )

    @staticmethod
    def _parse_verdict(raw: str) -> tuple[str, str]:
        """Parse output của model thành (verdict, output_string)."""
        lines = [line.strip() for line in raw.split("\n") if line.strip()]

        for line in lines:
            upper = line.upper()

            if upper.startswith("APPROVED"):
                comment = line[len("APPROVED"):].lstrip(": ").strip()
                return "approved", "approved" + (f": {comment}" if comment else "")

            if upper.startswith("REJECTED"):
                reason = line[len("REJECTED"):].lstrip(": ").strip()
                if not reason:
                    reason = raw[:300]
                return "rejected", f"rejected: {reason}"

        upper_raw = raw.upper()
        if "APPROVED" in upper_raw and "REJECTED" not in upper_raw:
            return "approved", "approved: (inferred from response)"

        return "rejected", f"rejected: cannot parse verdict — raw response: {raw[:200]}"
