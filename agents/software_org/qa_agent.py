"""
agents/qa_agent.py
QA Agent: Sinh test code riêng, chạy trong sandbox, báo cáo pass/fail.

Fix: Không concatenate code + test. Viết 2 file riêng:
    - script.py      → production code
    - test_output.py → import + test assertions
  Chạy test file độc lập — tránh lỗi if __name__, side effects.
"""

import re
import warnings
from config import QA_MODEL
from config.client import create_llm_client
from core.cost import record_llm_usage
from core.llm import route_model
from sandbox import get_sandbox
from system.rbac import Permission, require_permission
from agents.base import BaseAgent, AgentTask, AgentResult


class QAAgent(BaseAgent):
    def __init__(self, use_docker: bool = False, client=None):
        super().__init__(
            name="QAAgent",
            role="Quality Assurance Engineer",
        )
        self.use_docker = use_docker
        self._client = client or create_llm_client(model=QA_MODEL)

        if not use_docker:
            warnings.warn(
                "[QAAgent] Đang dùng LocalSandbox — code AI chạy trực tiếp trên host machine. "
                "Chỉ dùng khi dev/test local. Set use_docker=True cho production.",
                stacklevel=2,
            )

    async def run(self, task: AgentTask) -> AgentResult:
        code_to_test = task.context or ""

        if not code_to_test.strip():
            return AgentResult(
                success=False,
                output="fail: không có code để test",
                reason="context rỗng — dev_node chưa tạo được code",
            )

        test_code = await self._generate_test_code(task.id, task.description, code_to_test)
        if test_code is None:
            return AgentResult(
                success=False,
                output="fail: không thể sinh test code",
                reason="LLM call thất bại khi generate test",
            )

        return await self._run_in_sandbox(code_to_test, test_code)

    async def _generate_test_code(self, task_id: str, description: str, code: str) -> str | None:
        """Gọi LLM để sinh test code — dưới dạng file riêng biệt."""
        prompt = f"""Bạn là một {self.role}. Viết test code Python cho đoạn code dưới đây.

YÊU CẦU GỐC:
{description}

CODE CẦN TEST (sẽ lưu thành script.py):
```python
{code}
```

QUY TẮC (BẮT BUỘC):
1. File test của bạn sẽ được import từ script.py:
       from script import *
   KHÔNG định nghĩa lại function/class đã có — import từ script
2. Chỉ dùng assert statement — không dùng pytest, unittest
3. Viết tối thiểu 3 test cases: happy path, edge case (None/empty/0), error case
4. Mỗi assert phải có message: assert result == 5, f"Expected 5, got {{result}}"
5. KHÔNG dùng if __name__ == '__main__': 
6. Dòng cuối cùng phải là: print("QA_RESULT: PASS")

Chỉ trả về test code Python thuần túy. Không markdown, không giải thích.
"""

        try:
            model = route_model("qa", context_length=len(prompt))
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            await record_llm_usage(task_id, self.name, model, prompt, response)
            raw = (response.choices[0].message.content or "").strip()
            return self._strip_markdown(raw)
        except Exception:
            return None

    @require_permission(Permission.EXECUTE)
    async def _run_in_sandbox(self, code: str, test_code: str) -> AgentResult:
        """Viết 2 file riêng — production code + test — chạy test độc lập."""
        # Loại bỏ if __name__ block khỏi production code để tránh lỗi import
        sanitized_code = _remove_main_block(code)

        test_script = (
            f"from script import *\n\n"
            f"{test_code}\n"
        )

        try:
            async with get_sandbox(use_docker=self.use_docker) as sb:
                await sb.write_file("script.py", sanitized_code)
                await sb.write_file("test_output.py", test_script)
                run_result = await sb.run_command("python3 test_output.py", timeout=15)

            return self._parse_run_result(run_result)

        except Exception as e:
            return AgentResult(
                success=False,
                output=f"fail: sandbox error — {e}",
                reason=str(e),
            )

    @staticmethod
    def _parse_run_result(run_result) -> AgentResult:
        """Phân tích kết quả chạy test thành pass/fail."""
        combined = run_result.output

        if run_result.success and "QA_RESULT: PASS" in combined:
            return AgentResult(
                success=True,
                output="pass",
                reason=f"All assertions passed.\n{run_result.stdout}",
            )

        error_detail = _extract_error(run_result.stderr or combined)
        return AgentResult(
            success=False,
            output=f"fail: {error_detail}",
            reason=(
                f"Exit code: {run_result.exit_code}\n"
                f"Stdout: {run_result.stdout}\n"
                f"Stderr: {run_result.stderr}"
            ),
        )

    @staticmethod
    def _strip_markdown(text: str) -> str:
        if text.startswith("```python"):
            text = text[9:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()


def _remove_main_block(code: str) -> str:
    """Loại bỏ if __name__ == '__main__': block để import không chạy code thừa."""
    lines = code.split("\n")
    result = []
    in_main = False
    main_indent = 0

    for line in lines:
        stripped = line.rstrip()
        if re.match(r"^\s*if\s+__name__\s*==\s*['\"]__main__['\"]\s*:", stripped):
            in_main = True
            main_indent = len(line) - len(line.lstrip())
            continue
        if in_main:
            current_indent = len(line) - len(line.lstrip())
            if line.strip() == "" or current_indent > main_indent:
                continue
            in_main = False
        result.append(line)

    return "\n".join(result)


def _extract_error(stderr: str) -> str:
    if not stderr:
        return "unknown error (no stderr)"
    lines = stderr.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        if line and not line.startswith("Traceback") and not line.startswith("File "):
            return line[:200]
    return lines[-1][:200] if lines else "unknown error"
