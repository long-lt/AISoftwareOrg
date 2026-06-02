from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeCommandResult:
    command: str
    exit_code: int
    output: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def _run_command(
    command: list[str],
    cwd: Path,
    timeout: int = 180,
) -> RuntimeCommandResult:
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
        return RuntimeCommandResult(
            command=command_text,
            exit_code=process.returncode,
            output=process.stdout.strip(),
        )
    except FileNotFoundError:
        return RuntimeCommandResult(
            command=command_text,
            exit_code=127,
            output=f"Command not found: {command[0]}",
        )
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or "").strip() if isinstance(error.stdout, str) else ""
        return RuntimeCommandResult(
            command=command_text,
            exit_code=124,
            output=f"Command timed out after {timeout}s.\n{output}".strip(),
        )


def _render_command_result(result: RuntimeCommandResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    output = result.output or "(no output)"
    return f"""### `{result.command}`

- Status: {status}
- Exit code: {result.exit_code}

```text
{output}
```
"""


def _device_summary(devices_result: RuntimeCommandResult) -> tuple[str, bool]:
    if not devices_result.passed:
        return "- Không đọc được danh sách device từ Flutter CLI.", False

    try:
        devices = json.loads(devices_result.output or "[]")
    except json.JSONDecodeError:
        return "- Flutter devices output không phải JSON hợp lệ.", False

    if not devices:
        return "- Không có runtime device khả dụng.", False

    lines = []
    has_runnable_device = False
    for device in devices:
        name = device.get("name", "unknown")
        device_id = device.get("id", "unknown")
        target_platform = device.get("targetPlatform", "unknown")
        emulator = device.get("emulator", False)
        lines.append(
            f"- `{device_id}`: {name} ({target_platform}, emulator={emulator})"
        )
        if target_platform != "unknown":
            has_runnable_device = True

    return "\n".join(lines), has_runnable_device


def _runtime_status(command_results: list[RuntimeCommandResult]) -> str:
    required_results = [
        result
        for result in command_results
        if result.command in {"flutter devices --machine", "flutter build web --debug"}
    ]
    return "PASS" if required_results and all(result.passed for result in required_results) else "FAIL"


def run_runtime_verification(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
) -> list[Path]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy source dir: {source_dir}")

    command_results = [
        _run_command(["flutter", "devices", "--machine"], source_dir, timeout=60),
        _run_command(["flutter", "build", "web", "--debug"], source_dir, timeout=240),
    ]
    device_text, has_runnable_device = _device_summary(command_results[0])
    build_web_dir = source_dir / "build" / "web"
    web_index_exists = build_web_dir.joinpath("index.html").exists()
    screenshot_status = (
        "SKIPPED - runtime agent chỉ build smoke; browser screenshot sẽ nằm ở Phase F mở rộng."
    )
    status = _runtime_status(command_results)
    commands_text = "\n".join(_render_command_result(result) for result in command_results)

    report = f"""# Runtime Report: {app_input["name"]}

## Tổng Quan

- Status: {status}
- Thời gian kiểm tra: {datetime.now().isoformat(timespec="seconds")}
- Source: `{source_dir}`
- Build web output: `{build_web_dir}`
- Web index exists: {"YES" if web_index_exists else "NO"}
- Runnable device detected: {"YES" if has_runnable_device else "NO"}
- Screenshot: {screenshot_status}

## Devices

{device_text}

## Runtime Smoke

- `flutter build web --debug` xác nhận app có thể compile qua Flutter runtime target.
- Không chạy `flutter run` tự động để tránh treo pipeline khi không có simulator/device interactive.
- Khi cần manual runtime, chạy `flutter run -d <device_id>` trong thư mục `source/`.

## Command Checks

{commands_text}
"""

    report_path = docs_dir / "runtime_report.md"
    report_path.write_text(report, encoding="utf-8")
    return [report_path]
