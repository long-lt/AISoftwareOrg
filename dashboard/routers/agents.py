"""
dashboard/routers/agents.py
Router for agents configurations, prompts, models, and system settings.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config.env_file import write_env_value
from dashboard.database import _connect

router = APIRouter()


class AgentConfigRequest(BaseModel):
    model: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)


class SettingsRequest(BaseModel):
    daily_cost_limit: str = "5.00"
    smart_model_fallback: str = "anthropic/claude-3.5-sonnet"
    max_repair_attempts: str = "5"


@router.get("/agents/config")
def get_all_agents_config() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute("SELECT agent_id, name, model, system_prompt, updated_at FROM agents_config").fetchall()
    return [dict(row) for row in rows]


@router.post("/agents/config/{agent_id}")
def update_single_agent_config(agent_id: str, payload: AgentConfigRequest) -> dict[str, Any]:
    now = datetime.now().isoformat()
    with _connect() as connection:
        existing = connection.execute("SELECT agent_id FROM agents_config WHERE agent_id = ?", (agent_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        connection.execute(
            "UPDATE agents_config SET model = ?, system_prompt = ?, updated_at = ? WHERE agent_id = ?",
            (payload.model, payload.system_prompt, now, agent_id)
        )
        connection.commit()
    return {"agent_id": agent_id, "status": "updated"}


@router.get("/agents/{agent_id}")
def get_single_agent(agent_id: str) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT agent_id, name, type, status, model, system_prompt, description, updated_at FROM agents_config WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return dict(row)


@router.patch("/agents/{agent_id}")
def patch_agent(agent_id: str, payload: AgentConfigRequest) -> dict[str, Any]:
    now = datetime.now().isoformat()
    with _connect() as connection:
        existing = connection.execute("SELECT agent_id FROM agents_config WHERE agent_id = ?", (agent_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        connection.execute(
            "UPDATE agents_config SET model = ?, system_prompt = ?, updated_at = ? WHERE agent_id = ?",
            (payload.model, payload.system_prompt, now, agent_id),
        )
        connection.commit()
    return {"agent_id": agent_id, "status": "updated"}


@router.post("/agents/{agent_id}/test")
async def test_agent(agent_id: str, request: Request) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            "SELECT agent_id, name, model, system_prompt FROM agents_config WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    from dashboard.app import settings
    import openai

    client = openai.OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "sk-test",
    )
    try:
        response = client.chat.completions.create(
            model=row["model"] or settings.llm_model,
            messages=[
                {"role": "system", "content": row["system_prompt"] or "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: OK"},
            ],
            max_tokens=10,
        )
        reply = response.choices[0].message.content or ""
        return {"agent_id": agent_id, "model": row["model"], "status": "ok", "response": reply.strip()}
    except Exception as exc:
        return {"agent_id": agent_id, "model": row["model"], "status": "error", "error": str(exc)}


@router.get("/settings")
def get_system_settings_dict() -> dict[str, str]:
    with _connect() as connection:
        rows = connection.execute("SELECT key, value FROM system_settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


@router.get("/system/settings")
def get_system_settings_alias() -> dict[str, str]:
    return get_system_settings_dict()


@router.patch("/system/settings")
def patch_system_settings(payload: SettingsRequest) -> dict[str, str]:
    return update_system_settings_dict(payload)


@router.get("/system/status")
def get_system_status() -> dict[str, Any]:
    from dashboard.database import DB_PATH, GENERATED_APPS_DIR
    from dashboard.queue_manager import QUEUE_BACKEND
    return {
        "status": "ok",
        "version": "1.0.0",
        "queue_backend": QUEUE_BACKEND,
        "db_path": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "generated_apps_dir": str(GENERATED_APPS_DIR),
    }


@router.post("/settings")
def update_system_settings_dict(payload: SettingsRequest) -> dict[str, str]:
    now = datetime.now().isoformat()
    with _connect() as connection:
        connection.execute("INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES ('daily_cost_limit', ?, ?)", (payload.daily_cost_limit, now))
        connection.execute("INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES ('smart_model_fallback', ?, ?)", (payload.smart_model_fallback, now))
        connection.execute("INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES ('max_repair_attempts', ?, ?)", (payload.max_repair_attempts, now))
        connection.commit()
    # Save back to .env as well
    env_path = Path(os.getenv("DASHBOARD_ENV_FILE", ".env"))
    try:
        write_env_value(env_path, "DAILY_COST_LIMIT", payload.daily_cost_limit)
        write_env_value(env_path, "FALLBACK_SMART_MODEL", payload.smart_model_fallback)
        write_env_value(env_path, "MAX_REPAIR_ATTEMPTS", payload.max_repair_attempts)
    except Exception:
        pass
    return {"status": "saved"}


@router.post("/settings/wipe")
def wipe_all_system_data() -> dict[str, Any]:
    import shutil
    from dashboard.database import GENERATED_APPS_DIR

    # 1. Clean SQLite tables
    with _connect() as conn:
        conn.execute("DELETE FROM jobs")
        conn.execute("DELETE FROM initiatives")
        conn.execute("DELETE FROM system_settings")
        conn.execute("DELETE FROM agents_config")
        conn.commit()

    # 2. Re-seed default DB records
    # Calling _connect() will automatically detect empty tables and re-populate default records!
    _connect().close()

    # 3. Clean generated apps directory
    if GENERATED_APPS_DIR.exists():
        for item in GENERATED_APPS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

    # 4. Clean dynamic memory file
    memory_path = Path(__file__).resolve().parents[2] / "storage" / "memory.json"
    if memory_path.exists():
        try:
            memory_path.write_text("{}", encoding="utf-8")
        except Exception:
            pass

    return {"status": "success", "message": "All data wiped and reset to default startup state."}

