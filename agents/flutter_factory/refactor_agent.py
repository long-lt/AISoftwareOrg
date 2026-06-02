from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RefactorCommandResult:
    command: str
    exit_code: int
    output: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def _run_command(command: list[str], cwd: Path, timeout: int = 120) -> RefactorCommandResult:
    command_text = " ".join(command)
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return RefactorCommandResult(
            command=command_text,
            exit_code=process.returncode,
            output=process.stdout.strip(),
        )
    except FileNotFoundError:
        return RefactorCommandResult(
            command=command_text,
            exit_code=127,
            output=f"Command not found: {command[0]}",
        )
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or "").strip() if isinstance(error.stdout, str) else ""
        return RefactorCommandResult(
            command=command_text,
            exit_code=124,
            output=f"Command timed out after {timeout}s.\n{output}".strip(),
        )


def _has_known_bugs(bug_list: str) -> bool:
    clean_markers = [
        "Không phát hiện bug",
        "No bugs",
        "No issue",
    ]
    return not any(marker in bug_list for marker in clean_markers)


def _render_command_result(result: RefactorCommandResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    output = result.output or "(no output)"
    return f"""### `{result.command}`

- Status: {status}
- Exit code: {result.exit_code}

```text
{output}
```
"""


def _render_report(
    app_input: dict[str, Any],
    source_dir: Path,
    bug_list: str,
    command_results: list[RefactorCommandResult],
) -> str:
    has_bugs = _has_known_bugs(bug_list)
    status = "PASS" if all(result.passed for result in command_results) else "FAIL"
    action_summary = (
        "- QA bug list có item cần xử lý. Refactor Agent đã chạy format và verify lại source."
        if has_bugs
        else "- QA bug list không có bug. Refactor Agent chỉ format và verify lại source."
    )
    commands_text = "\n".join(_render_command_result(result) for result in command_results)

    return f"""# Refactor Report: {app_input["name"]}

## Tổng Quan

- Status: {status}
- Thời gian refactor: {datetime.now().isoformat(timespec="seconds")}
- Source: `{source_dir}`

## Bug Input

```markdown
{bug_list.strip()}
```

## Hành Động

{action_summary}
- Không thực hiện rewrite logic khi không có lỗi cụ thể.
- Giữ nguyên scope MVP đã sinh ở DEV Agent.

## Verification

{commands_text}
"""


def run_refactor(app_input: dict[str, Any], docs_dir: Path, source_dir: Path) -> list[Path]:
    bug_list_path = docs_dir / "bug_list.md"
    if not bug_list_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy bug_list.md: {bug_list_path}. "
            "Hãy chạy `python3 app.py run-qa --slug <slug>` trước."
        )

    bug_list = bug_list_path.read_text(encoding="utf-8")
    if not source_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy source dir: {source_dir}")

    command_results = [
        _run_command(["dart", "format", "lib"], source_dir),
        _run_command(["flutter", "analyze"], source_dir),
    ]

    report = _render_report(app_input, source_dir, bug_list, command_results)
    report_path = docs_dir / "refactor_report.md"
    report_path.write_text(report, encoding="utf-8")

    return [report_path]
