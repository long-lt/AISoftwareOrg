from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.client import IncompleteRead
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenRouterResponse:
    content: str
    model: str
    usage: dict[str, Any]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_api_key() -> str:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise OpenRouterError(
            "Thiếu OPENROUTER_API_KEY hoặc LLM_API_KEY. Hãy đặt trong .env hoặc environment."
        )
    return api_key


def check_daily_cost_guard() -> None:
    # 1. Retrieve limit from DB, default 5.00
    daily_limit = 5.00
    db_path = Path(__file__).resolve().parents[2] / "workspace" / "jobs.sqlite3"
    if db_path.exists():
        import sqlite3
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT value FROM system_settings WHERE key = 'daily_cost_limit'").fetchone()
                if row and row["value"]:
                    daily_limit = float(row["value"])
        except Exception:
            pass
            
    # 2. Sum costs logged today
    log_file = Path(__file__).resolve().parents[2] / "logs" / "agent_actions.jsonl"
    if not log_file.exists():
        return
        
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    total_cost_today = 0.0
    
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("action") == "llm_cost" and entry.get("timestamp", "").startswith(today_str):
                        cost = float(entry.get("details", {}).get("cost_usd") or 0.0)
                        total_cost_today += cost
                except Exception:
                    pass
    except Exception:
        pass
        
    if total_cost_today >= daily_limit:
        raise RuntimeError(
            f"COST GUARD ALERT: Daily LLM cost limit reached. Spent ${total_cost_today:.4f} of limit ${daily_limit:.2f}. "
            f"Pipeline terminated to prevent infinite loops."
        )


def chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 4000,
    app_title: str = "Flutter AI Factory",
) -> OpenRouterResponse:
    check_daily_cost_guard()
    api_key = require_api_key()
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": app_title,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except IncompleteRead as error:
        raise OpenRouterError(
            f"OpenRouter response was incomplete: {len(error.partial)} bytes read"
        ) from error
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise OpenRouterError(f"OpenRouter HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise OpenRouterError(f"OpenRouter request failed: {error}") from error
    except TimeoutError as error:
        raise OpenRouterError(f"OpenRouter request timed out: {error}") from error

    choices = response_data.get("choices") or []
    if not choices:
        raise OpenRouterError(f"OpenRouter response has no choices: {response_data}")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OpenRouterError(f"OpenRouter response has empty content: {response_data}")

    return OpenRouterResponse(
        content=content,
        model=str(response_data.get("model", model)),
        usage=response_data.get("usage") or {},
    )


def strip_markdown_fence(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_json_response(content: str) -> dict[str, Any]:
    cleaned = strip_markdown_fence(content)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise OpenRouterError(f"OpenRouter did not return valid JSON: {error}") from error

    if not isinstance(parsed, dict):
        raise OpenRouterError("OpenRouter JSON response must be an object.")
    return parsed
