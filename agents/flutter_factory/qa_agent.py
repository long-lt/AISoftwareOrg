from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int
    output: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def _run_command(command: list[str], cwd: Path, timeout: int = 120) -> CommandResult:
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
        return CommandResult(
            command=command_text,
            exit_code=process.returncode,
            output=process.stdout.strip(),
        )
    except FileNotFoundError:
        return CommandResult(
            command=command_text,
            exit_code=127,
            output=f"Command not found: {command[0]}",
        )
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or "").strip() if isinstance(error.stdout, str) else ""
        return CommandResult(
            command=command_text,
            exit_code=124,
            output=f"Command timed out after {timeout}s.\n{output}".strip(),
        )


def _source_files(source_dir: Path) -> list[Path]:
    return sorted(path for path in source_dir.rglob("*.dart") if path.is_file())


def _required_source_files(app_input: dict[str, Any], source_dir: Path) -> list[Path]:
    features = app_input.get("features", [])
    feature_paths = [
        source_dir
        / "lib"
        / "features"
        / str(feature).strip().lower().replace(" ", "_")
        / "presentation"
        / "screens"
        / f"{str(feature).strip().lower().replace(' ', '_')}_screen.dart"
        for feature in features
    ]
    return [
        source_dir / ".env.example",
        source_dir / "pubspec.yaml",
        source_dir / "lib" / "main.dart",
        source_dir / "lib" / "app.dart",
        source_dir / "lib" / "core" / "api" / "api_client.dart",
        source_dir / "lib" / "core" / "config" / "app_config.dart",
        source_dir / "lib" / "core" / "di" / "app_dependencies.dart",
        source_dir / "lib" / "core" / "theme" / "app_theme.dart",
        source_dir / "lib" / "shared" / "widgets" / "app_scaffold.dart",
        source_dir / "lib" / "shared" / "widgets" / "feature_card.dart",
        source_dir / "lib" / "shared" / "widgets" / "state_view.dart",
        source_dir
        / "lib"
        / "features"
        / "home"
        / "presentation"
        / "screens"
        / "home_screen.dart",
        source_dir
        / "lib"
        / "features"
        / "settings"
            / "presentation"
            / "screens"
            / "settings_screen.dart",
        source_dir / "test" / "app_widget_test.dart",
        source_dir / "test" / "core" / "api" / "api_client_test.dart",
        *feature_paths,
        *[
            source_dir
            / "test"
            / "features"
            / str(feature).strip().lower().replace(" ", "_")
            / f"{str(feature).strip().lower().replace(' ', '_')}_logic_test.dart"
            for feature in features
        ],
        *[
            source_dir
            / "test"
            / "features"
            / str(feature).strip().lower().replace(" ", "_")
            / f"{str(feature).strip().lower().replace(' ', '_')}_data_test.dart"
            for feature in features
        ],
    ]


def _render_command_result(result: CommandResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    output = result.output or "(no output)"
    return f"""### `{result.command}`

- Status: {status}
- Exit code: {result.exit_code}

```text
{output}
```
"""


def _coverage_summary(source_dir: Path) -> str:
    percent, hit_lines, found_lines = _coverage_numbers(source_dir)
    if found_lines == 0:
        coverage_path = source_dir / "coverage" / "lcov.info"
        if not coverage_path.exists():
            return "- Coverage: Không có dữ liệu"
        return "- Coverage: Không có dòng Dart được ghi nhận"

    return f"- Coverage: {percent:.1f}% ({hit_lines}/{found_lines} lines)"


def _coverage_numbers(source_dir: Path) -> tuple[float, int, int]:
    coverage_path = source_dir / "coverage" / "lcov.info"
    if not coverage_path.exists():
        return 0.0, 0, 0

    found_lines = 0
    hit_lines = 0
    for line in coverage_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("LF:"):
            found_lines += int(line.removeprefix("LF:") or 0)
        elif line.startswith("LH:"):
            hit_lines += int(line.removeprefix("LH:") or 0)

    if found_lines == 0:
        return 0.0, 0, 0

    percent = hit_lines / found_lines * 100
    return percent, hit_lines, found_lines


def _parse_acceptance_tests(docs_dir: Path) -> list[str]:
    path = docs_dir / "acceptance_tests.md"
    if not path.exists():
        return []
    tests: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"- \[[ xX]\] (.+)", line.strip())
        if match:
            tests.append(match.group(1).strip())
    return tests


def _acceptance_checklist(
    docs_dir: Path,
    source_dir: Path,
    command_results: list[CommandResult],
) -> list[tuple[str, str, str]]:
    tests = _parse_acceptance_tests(docs_dir)
    test_sources = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted((source_dir / "test").rglob("*.dart"))
        if path.is_file()
    )
    command_passed = all(result.passed for result in command_results)
    checklist: list[tuple[str, str, str]] = []
    for test in tests:
        lowered = test.lower()
        if "load success" in lowered:
            status = "PASS" if "renders" in test_sources and command_passed else "FAIL"
            reason = "Widget smoke test renders feature data."
        elif "empty state" in lowered:
            status = "PASS" if "emits empty" in test_sources and command_passed else "FAIL"
            reason = "Cubit empty-state test exists."
        elif "error state" in lowered:
            status = "PASS" if "emits failure" in test_sources and command_passed else "FAIL"
            reason = "Cubit failure-state test exists."
        elif "main action" in lowered:
            status = "SKIP"
            reason = "Main write actions are scheduled for CRUD/Write Flow Generation."
        else:
            status = "SKIP"
            reason = "No automated mapper for this acceptance item yet."
        checklist.append((test, status, reason))
    return checklist


def _run_backend_tests(source_dir: Path) -> CommandResult | None:
    backend_dir = source_dir.parent / "backend"
    if not backend_dir.exists():
        return None
    return _run_command(["python3", "-m", "unittest", "discover", "-s", "tests"], backend_dir)


def _render_production_qa_report(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
    command_results: list[CommandResult],
    backend_result: CommandResult | None,
    missing_files: list[Path],
    coverage_threshold: float,
) -> str:
    coverage_percent, hit_lines, found_lines = _coverage_numbers(source_dir)
    acceptance_items = _acceptance_checklist(docs_dir, source_dir, command_results)
    acceptance_failed = [item for item in acceptance_items if item[1] == "FAIL"]
    acceptance_unmapped = [item for item in acceptance_items if item[1] == "SKIP"]
    backend_passed = backend_result.passed if backend_result else False
    release_build = next(
        (result for result in command_results if result.command == "flutter build web --release"),
        None,
    )
    flutter_analyze = next(
        (result for result in command_results if result.command == "flutter analyze"),
        None,
    )
    flutter_test = next(
        (result for result in command_results if result.command == "flutter test --coverage"),
        None,
    )
    gates = [
        ("Required source files", not missing_files, "All required generated files are present."),
        ("flutter analyze", bool(flutter_analyze and flutter_analyze.passed), "Static analysis must pass."),
        ("flutter test --coverage", bool(flutter_test and flutter_test.passed), "Unit/widget/API tests must pass."),
        (
            f"Coverage >= {coverage_threshold:.0f}%",
            found_lines > 0 and coverage_percent >= coverage_threshold,
            f"Coverage is {coverage_percent:.1f}% ({hit_lines}/{found_lines} lines).",
        ),
        ("Backend tests", backend_passed, "Generated backend contract tests must pass."),
        (
            "Acceptance tests",
            not acceptance_failed and bool(acceptance_items),
            "Acceptance items must PASS or have explicit SKIP reason.",
        ),
        (
            "Release build",
            bool(release_build and release_build.passed),
            "Flutter web release build must pass.",
        ),
    ]
    status = "PASS" if all(passed for _, passed, _ in gates) else "FAIL"
    gate_text = "\n".join(
        f"- [{'x' if passed else ' '}] {name}: {detail}" for name, passed, detail in gates
    )
    acceptance_text = (
        "\n".join(
            f"- {status_value}: {name} - {reason}"
            for name, status_value, reason in acceptance_items
        )
        if acceptance_items
        else "- FAIL: `acceptance_tests.md` missing or empty."
    )
    backend_text = _render_command_result(backend_result) if backend_result else "- Backend tests: FAIL - backend dir missing."
    skip_text = (
        "\n".join(f"- {name}: {reason}" for name, _, reason in acceptance_unmapped)
        if acceptance_unmapped
        else "- Không có"
    )

    return f"""# Production QA Report: {app_input["name"]}

## Tổng Quan

- Status: {status}
- Checked at: {datetime.now().isoformat(timespec="seconds")}
- Coverage threshold: {coverage_threshold:.0f}%
- Source: `{source_dir}`

## Quality Gates

{gate_text}

## Acceptance Checklist

{acceptance_text}

## Explicit Skips

{skip_text}

## Backend Check

{backend_text}
"""


def _render_test_report(
    app_input: dict[str, Any],
    source_dir: Path,
    command_results: list[CommandResult],
    missing_files: list[Path],
) -> str:
    passed = all(result.passed for result in command_results) and not missing_files
    status = "PASS" if passed else "FAIL"
    dart_files = _source_files(source_dir)
    commands_text = "\n".join(_render_command_result(result) for result in command_results)
    missing_text = (
        "\n".join(f"- `{path.relative_to(source_dir)}`" for path in missing_files)
        if missing_files
        else "- Không có"
    )
    dart_file_text = "\n".join(f"- `{path.relative_to(source_dir)}`" for path in dart_files)
    coverage_text = _coverage_summary(source_dir)

    return f"""# Test Report: {app_input["name"]}

## Tổng Quan

- Status: {status}
- Thời gian kiểm tra: {datetime.now().isoformat(timespec="seconds")}
- Source: `{source_dir}`
- Dart files: {len(dart_files)}

## Kiểm Tra File Bắt Buộc

{missing_text}

## Dart Files

{dart_file_text}

## Coverage

{coverage_text}

## Command Checks

{commands_text}
"""


def _render_bug_list(
    app_input: dict[str, Any],
    command_results: list[CommandResult],
    missing_files: list[Path],
    source_dir: Path,
) -> str:
    bugs: list[str] = []
    for path in missing_files:
        bugs.append(
            f"- [ ] Missing file: `{path.relative_to(source_dir)}` cần được DEV/Refactor Agent tạo."
        )

    for result in command_results:
        if not result.passed:
            bugs.append(
                f"- [ ] Command `{result.command}` failed với exit code {result.exit_code}."
            )

    if not bugs:
        bugs.append("- Không phát hiện bug ở vòng QA hiện tại.")

    return f"""# Bug List: {app_input["name"]}

## Bugs

{chr(10).join(bugs)}

## Ghi Chú

- Bug list được sinh từ kiểm tra file bắt buộc và command QA tự động.
- Nếu có lỗi, Refactor Agent sẽ dùng file này làm input chính.
"""


def run_qa_checks(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
    *,
    include_release_build: bool = True,
) -> list[Path]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy source dir: {source_dir}")

    required_files = _required_source_files(app_input, source_dir)
    missing_files = [path for path in required_files if not path.exists()]

    command_results = [
        _run_command(["flutter", "analyze"], source_dir),
    ]

    test_dir = source_dir / "test"
    if test_dir.exists():
        command_results.append(_run_command(["flutter", "test", "--coverage"], source_dir))
    if include_release_build:
        command_results.append(_run_command(["flutter", "build", "web", "--release"], source_dir, timeout=240))
    backend_result = _run_backend_tests(source_dir)
    coverage_threshold = float(app_input.get("coverage_threshold") or 80)

    test_report = _render_test_report(
        app_input,
        source_dir,
        command_results,
        missing_files,
    )
    bug_list = _render_bug_list(
        app_input,
        [*command_results, *([backend_result] if backend_result else [])],
        missing_files,
        source_dir,
    )
    production_qa_report = _render_production_qa_report(
        app_input,
        docs_dir,
        source_dir,
        command_results,
        backend_result,
        missing_files,
        coverage_threshold,
    )

    output_files = {
        "test_report.md": test_report,
        "bug_list.md": bug_list,
        "production_qa_report.md": production_qa_report,
    }

    written_paths: list[Path] = []
    for filename, content in output_files.items():
        path = docs_dir / filename
        path.write_text(content, encoding="utf-8")
        written_paths.append(path)

    return written_paths
