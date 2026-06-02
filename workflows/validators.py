from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    yaml = None


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    errors: list[str]


def _ok() -> ValidationResult:
    return ValidationResult(passed=True, errors=[])


def _fail(message: str) -> ValidationResult:
    return ValidationResult(passed=False, errors=[message])


def validate_required_files(app_dir: Path, required_paths: list[str] | tuple[str, ...]) -> ValidationResult:
    missing = [
        rel_path
        for rel_path in required_paths
        if not (app_dir / rel_path).exists()
    ]
    if missing:
        return ValidationResult(
            passed=False,
            errors=[f"Missing required file or directory: {path}" for path in missing],
        )
    return _ok()


def validate_json_file(path: Path) -> ValidationResult:
    if not path.exists():
        return _fail(f"Missing JSON file: {path}")
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return _fail(f"Invalid JSON in {path}: {error}")
    return _ok()


def validate_yaml_file(path: Path) -> ValidationResult:
    if not path.exists():
        return _fail(f"Missing YAML file: {path}")
    if yaml is None:
        return _ok()
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as error:
        return _fail(f"Invalid YAML in {path}: {error}")
    return _ok()


def validate_dart_file(path: Path) -> ValidationResult:
    if not path.exists():
        return _fail(f"Missing Dart file: {path}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "TODO" in text and len(text.strip().splitlines()) <= 3:
        return _fail(f"Dart file appears to be TODO-only: {path}")
    return _ok()


def validate_markdown_status(path: Path, expected: str = "PASS") -> ValidationResult:
    if not path.exists():
        return _fail(f"Missing Markdown status file: {path}")
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith("- Status:"):
            status = stripped.removeprefix("- Status:").strip()
            return _ok() if status == expected else _fail(f"{path} status is {status}, expected {expected}")
        if stripped.startswith("Status:"):
            status = stripped.removeprefix("Status:").strip()
            return _ok() if status == expected else _fail(f"{path} status is {status}, expected {expected}")
    return _fail(f"No Status line found in {path}")
