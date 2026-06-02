"""Helpers for small .env file updates."""

from __future__ import annotations

import re
from pathlib import Path


def write_env_value(env_path: str | Path, key: str, value: str) -> None:
    """Write or replace one KEY=\"VALUE\" line in an env file."""
    path = Path(env_path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    new_line = f'{key}="{value}"'
    pattern = re.compile(rf"^{re.escape(key)}\s*=")
    replaced = False
    new_lines = []
    for line in lines:
        if pattern.match(line.strip()):
            new_lines.append(new_line)
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(new_line)

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
