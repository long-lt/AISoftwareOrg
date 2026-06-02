from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.flutter_factory.openrouter_client import OpenRouterError, chat_completion, parse_json_response


MODEL_BY_AGENT = {
    "ba": "openai/gpt-oss-120b:free",
    "architect": "openai/gpt-oss-120b:free",
    "uiux": "minimax/minimax-m2.5:free",
    "dev": "qwen/qwen-2.5-coder-32b-instruct",
    "qa": "openai/gpt-oss-120b:free",
    "refactor": "qwen/qwen3-coder:free",
    "reviewer": "openai/gpt-oss-120b:free",
}


@dataclass(frozen=True)
class ValidationCommandResult:
    command: str
    exit_code: int
    output: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _context_block(title: str, content: str) -> str:
    return f"## {title}\n\n```text\n{content.strip()}\n```"


def build_docs_context(app_input: dict[str, Any], docs_dir: Path, filenames: list[str]) -> str:
    blocks = [
        _context_block(
            "input.json",
            json.dumps(app_input, ensure_ascii=False, indent=2),
        )
    ]
    for filename in filenames:
        content = _read(docs_dir / filename)
        if content:
            blocks.append(_context_block(filename, content))
    return "\n\n".join(blocks)


def get_db_model_for_agent(agent_name: str, default_model: str) -> str:
    db_path = Path(__file__).resolve().parents[2] / "workspace" / "jobs.sqlite3"
    if db_path.exists():
        import sqlite3
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT model FROM agents_config WHERE agent_id = ?", (agent_name,)).fetchone()
                if row and row["model"]:
                    return row["model"]
        except Exception:
            pass
    return default_model


def get_db_prompt_for_agent(agent_name: str, default_prompt: str) -> str:
    db_path = Path(__file__).resolve().parents[2] / "workspace" / "jobs.sqlite3"
    if db_path.exists():
        import sqlite3
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT system_prompt FROM agents_config WHERE agent_id = ?", (agent_name,)).fetchone()
                if row and row["system_prompt"]:
                    return row["system_prompt"]
        except Exception:
            pass
    return default_prompt


def write_openrouter_files(
    *,
    agent_name: str,
    prompt_path: Path,
    app_input: dict[str, Any],
    docs_dir: Path,
    context_filenames: list[str],
    expected_files: list[str],
) -> list[Path]:
    model = get_db_model_for_agent(agent_name, MODEL_BY_AGENT[agent_name])
    prompt = get_db_prompt_for_agent(agent_name, _read(prompt_path))
    context = build_docs_context(app_input, docs_dir, context_filenames)
    expected = "\n".join(f"- {filename}" for filename in expected_files)

    system_message = (
        "You are a precise file-generation agent for Flutter AI Factory. "
        "Return only valid JSON. Do not wrap the response in markdown."
    )
    user_message = f"""Agent prompt:

{prompt}

Context:

{context}

Expected output files:

{expected}

Return JSON exactly in this shape:

{{
  "files": [
    {{
      "path": "requirements.md",
      "content": "# Markdown or code content here"
    }}
  ]
}}

Rules:
- Every expected output file must be present.
- Paths must be relative filenames only, no directories.
- Content must be complete file content.
- Use Vietnamese for product documentation unless code requires English.
"""

    response = chat_completion(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )
    parsed = parse_json_response(response.content)
    files = parsed.get("files")
    if not isinstance(files, list):
        raise ValueError("OpenRouter response must contain a files list.")

    allowed = set(expected_files)
    written_paths: list[Path] = []
    seen: set[str] = set()

    for file_item in files:
        if not isinstance(file_item, dict):
            raise ValueError("Each OpenRouter file item must be an object.")
        path = str(file_item.get("path", "")).strip()
        content = file_item.get("content")
        if path not in allowed:
            raise ValueError(f"Unexpected OpenRouter output path: {path}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"OpenRouter output for {path} is empty.")
        output_path = docs_dir / path
        output_path.write_text(content.rstrip() + "\n", encoding="utf-8")
        written_paths.append(output_path)
        seen.add(path)

    missing = allowed - seen
    if missing:
        raise ValueError(f"OpenRouter response missing files: {', '.join(sorted(missing))}")

    return written_paths


def _run_command(command: list[str], cwd: Path, timeout: int = 120) -> ValidationCommandResult:
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
        return ValidationCommandResult(
            command=command_text,
            exit_code=process.returncode,
            output=process.stdout.strip(),
        )
    except FileNotFoundError:
        return ValidationCommandResult(
            command=command_text,
            exit_code=127,
            output=f"Command not found: {command[0]}",
        )
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or "").strip() if isinstance(error.stdout, str) else ""
        return ValidationCommandResult(
            command=command_text,
            exit_code=124,
            output=f"Command timed out after {timeout}s.\n{output}".strip(),
        )


def _validate_source_response(
    content: str,
    allowed_paths: list[str],
    require_all: bool,
) -> list[dict[str, str]]:
    parsed = parse_json_response(content)
    files = parsed.get("files")
    if not isinstance(files, list):
        raise ValueError("OpenRouter response must contain a files list.")

    allowed = set(allowed_paths)
    seen: set[str] = set()
    validated: list[dict[str, str]] = []
    for file_item in files:
        if not isinstance(file_item, dict):
            raise ValueError("Each OpenRouter file item must be an object.")
        path = str(file_item.get("path", "")).strip()
        file_content = file_item.get("content")
        file_content_lines = file_item.get("content_lines")
        path_obj = Path(path)
        if path_obj.is_absolute() or ".." in path_obj.parts:
            raise ValueError(f"Unsafe OpenRouter output path: {path}")
        if path not in allowed:
            raise ValueError(f"Unexpected OpenRouter output path: {path}")
        if isinstance(file_content_lines, list):
            if not all(isinstance(line, str) for line in file_content_lines):
                raise ValueError(f"OpenRouter content_lines for {path} must be strings.")
            file_content = "\n".join(file_content_lines)
        if not isinstance(file_content, str) or not file_content.strip():
            raise ValueError(f"OpenRouter output for {path} is empty.")
        validated.append({"path": path, "content": file_content.rstrip() + "\n"})
        seen.add(path)

    if require_all:
        missing = allowed - seen
        if missing:
            raise ValueError(
                f"OpenRouter response missing files: {', '.join(sorted(missing))}"
            )

    return validated


def _write_source_files(source_dir: Path, files: list[dict[str, str]]) -> list[Path]:
    written_paths: list[Path] = []
    for file_item in files:
        output_path = source_dir / file_item["path"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(file_item["content"], encoding="utf-8")
        written_paths.append(output_path)
    return written_paths


def _chunk_paths(paths: list[str], chunk_size: int = 4) -> list[list[str]]:
    return [paths[index : index + chunk_size] for index in range(0, len(paths), chunk_size)]


def _source_prompt(
    *,
    prompt: str,
    context: str,
    allowed_paths: list[str],
    repair_context: str | None,
) -> str:
    allowed = "\n".join(f"- {path}" for path in allowed_paths)
    repair = ""
    if repair_context:
        repair = f"""

Previous output failed validation:

```text
{repair_context}
```

Regenerate all files and fix the validation failures.
"""

    return f"""Agent prompt:

{prompt}

Context:

{context}

Allowed output paths:

{allowed}

Return JSON exactly in this shape:

{{
  "files": [
    {{
      "path": "pubspec.yaml",
      "content_lines": [
        "line 1",
        "line 2"
      ]
    }}
  ]
}}

Rules:
- Return every allowed output path exactly once.
- Do not include any path outside the allowlist.
- Paths are relative to the Flutter project root.
- Prefer `content_lines` over `content` so JSON remains valid.
- Use Flutter SDK and any relevant third-party dependencies to fulfill requirements.
- Ensure all used packages are added to `pubspec.yaml`.
- Prioritize real implementation over placeholders if enough information is available.
- `pubspec.yaml` must use the package name from input slug.
- Dart files must compile with null safety.
- Do not wrap JSON in markdown.
{repair}
"""


def _get_fallback_model(default_model: str) -> str:
    """Đọc fallback model từ SQLite system_settings. Trả default nếu không có."""
    db_path = Path(__file__).resolve().parents[2] / "workspace" / "jobs.sqlite3"
    if db_path.exists():
        import sqlite3
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT value FROM system_settings WHERE key = 'smart_model_fallback'"
                ).fetchone()
                if row and row["value"]:
                    return row["value"]
        except Exception:
            pass
    return default_model


def write_openrouter_source_files(
    *,
    agent_name: str,
    prompt_path: Path,
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
    context_filenames: list[str],
    allowed_paths: list[str],
    max_repairs: int = 1,
) -> list[Path]:
    model = get_db_model_for_agent(agent_name, MODEL_BY_AGENT[agent_name])
    prompt = get_db_prompt_for_agent(agent_name, _read(prompt_path))
    context = build_docs_context(app_input, docs_dir, context_filenames)
    system_message = (
        "You are a careful Flutter code generation agent. "
        "Return only valid JSON matching the requested schema."
    )

    written_paths: list[Path] = []
    repair_context: str | None = None
    attempts = max_repairs + 1

    for attempt in range(attempts):
        active_model = model
        if attempt >= 2:
            active_model = _get_fallback_model(model)

        files: list[dict[str, str]] = []
        generation_error: OpenRouterError | ValueError | None = None
        for target_paths in _chunk_paths(allowed_paths):
            try:
                response = chat_completion(
                    model=active_model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {
                            "role": "user",
                            "content": _source_prompt(
                                prompt=prompt,
                                context=context,
                                allowed_paths=target_paths,
                                repair_context=repair_context,
                            ),
                        },
                    ],
                    max_tokens=9000,
                )
                files.extend(
                    _validate_source_response(
                        response.content,
                        allowed_paths=target_paths,
                        require_all=True,
                    )
                )
            except (OpenRouterError, ValueError) as error:
                generation_error = error
                break

        if generation_error is not None:
            repair_context = str(generation_error)
            if attempt == attempts - 1:
                raise generation_error
            continue

        written_paths = _write_source_files(source_dir, files)
        format_result = _run_command(["dart", "format", "lib"], source_dir)
        analyze_result = _run_command(["flutter", "analyze"], source_dir)
        if format_result.passed and analyze_result.passed:
            return written_paths

        repair_context = (
            f"{format_result.command} exit={format_result.exit_code}\n"
            f"{format_result.output}\n\n"
            f"{analyze_result.command} exit={analyze_result.exit_code}\n"
            f"{analyze_result.output}"
        )
        if attempt == attempts - 1:
            raise ValueError(f"OpenRouter DEV output failed validation:\n{repair_context}")

    return written_paths
