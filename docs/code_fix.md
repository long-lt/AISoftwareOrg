Dưới đây là bộ code fix trực tiếp cho các lỗi bạn liệt kê. Ưu tiên copy theo đúng file/path.

---

# 1. Fix `dashboard/routers/projects.py`

Thay toàn bộ file bằng bản này:

```python
"""
dashboard/routers/projects.py
Router for business portfolio initiatives and projects management.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dashboard.routers.auth import require_auth, require_role
from dashboard.database import (
    list_initiatives,
    create_initiative,
    get_initiative,
    delete_initiative,
)

router = APIRouter()


class ProjectRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    slug: str = ""
    status: str = "discovery"
    health: str = "healthy"
    icon: str = "🤖"
    repository: str = ""
    monthly_spend: float = 0.0
    sla: str = "100%"
    build_progress: int = 0
    features: list[str] = []


@router.get("")
def get_projects(_auth: dict = Depends(require_auth)) -> list[dict[str, Any]]:
    return list_initiatives()


@router.post("", status_code=201)
def post_project(
    payload: ProjectRequest,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    return create_initiative(payload.model_dump())


@router.get("/{slug}")
def get_single_project(
    slug: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    project = get_initiative(slug)
    if project is None:
        raise HTTPException(status_code=404, detail="Project initiative not found")
    return project


@router.put("/{slug}")
def update_project(
    slug: str,
    payload: ProjectRequest,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["slug"] = slug
    return create_initiative(data)


@router.patch("/{slug}")
def patch_project(
    slug: str,
    payload: ProjectRequest,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    data = payload.model_dump()
    data["slug"] = slug
    return create_initiative(data)


@router.delete("/{slug}")
def delete_single_project(
    slug: str,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, str]:
    if not delete_initiative(slug):
        raise HTTPException(status_code=404, detail="Project initiative not found")
    return {"deleted": slug}
```

---

# 2. Fix `dashboard/routers/providers.py`

Điểm chính:

* Bỏ `key` khỏi query.
* Không nhận API key qua URL.
* Toàn bộ provider management phải có auth.
* Những route ghi/sửa/xóa provider dùng `require_role("admin")`.

Sửa import đầu file:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

Đổi import auth thành:

```python
from dashboard.routers.auth import require_auth, require_role
```

## 2.1. Sửa `GET /models`

Thay function `list_active_provider_models()` bằng:

```python
@router.get("/models")
async def list_active_provider_models(
    provider: Optional[str] = Query(None),
    base_url: Optional[str] = Query(None),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    from dashboard.app import settings

    active_name = provider or settings.llm_provider

    resolved_base_url = base_url

    if not resolved_base_url:
        try:
            provider_config = get_enabled_provider(active_name, settings.llm_providers_file)
            resolved_base_url = provider_config.base_url
            resolved_key = os.getenv(provider_config.api_key_env, "")
        except Exception:
            resolved_key = ""
    else:
        resolved_key = ""

    if not resolved_base_url:
        defaults = {
            "openai": "https://api.openai.com/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
            "deepseek": "https://api.deepseek.com/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "ollama": "http://localhost:11434/v1",
        }
        resolved_base_url = defaults.get(active_name, "https://api.openai.com/v1")

    resolved_base_url = resolved_base_url.rstrip("/")
    url = f"{resolved_base_url}/models"

    headers = {
        "User-Agent": "Unified-AI-Software-Dashboard/1.0",
        "Accept": "application/json",
    }

    if resolved_key:
        headers["Authorization"] = f"Bearer {resolved_key}"

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            models_list = response_data.get("data", [])
            return {
                "provider": active_name,
                "success": True,
                "models": models_list,
            }

    except urllib.error.URLError as error:
        fallbacks = {
            "openai": [
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
                {"id": "gpt-4o", "name": "GPT-4o"},
            ],
            "gemini": [
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            ],
            "deepseek": [
                {"id": "deepseek-chat", "name": "DeepSeek V3"},
                {"id": "deepseek-coder", "name": "DeepSeek Coder"},
            ],
            "openrouter": [
                {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
                {"id": "qwen/qwen-2.5-coder-32b", "name": "Qwen 2.5 Coder 32B"},
                {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"},
                {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3"},
            ],
            "ollama": [
                {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder 7B"},
                {"id": "llama3.1:8b", "name": "Llama 3.1 8B"},
                {"id": "codegemma", "name": "CodeGemma"},
            ],
        }

        return {
            "provider": active_name,
            "success": False,
            "error": str(error),
            "models": fallbacks.get(active_name, []),
        }

    except Exception as error:
        return {
            "provider": active_name,
            "success": False,
            "error": str(error),
            "models": [],
        }
```

## 2.2. Sửa các route provider còn lại

Đổi các function này:

```python
@router.post("/providers")
async def add_provider_body(
    payload: ProviderCreatePayload,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    from dashboard.app import settings
    provider = upsert_provider(
        payload.name,
        base_url=payload.base_url,
        api_key_env=payload.api_key_env,
        default_model=payload.default_model,
        enabled=payload.enabled,
        path=settings.llm_providers_file,
    )
    return provider_to_dict(provider)


@router.get("/providers")
async def get_providers(
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    from dashboard.app import settings
    return provider_registry_payload(
        active_provider=settings.llm_provider,
        path=settings.llm_providers_file,
    )


@router.post("/providers/{name}")
async def add_provider(
    name: str,
    payload: ProviderPayload,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    from dashboard.app import settings
    if not payload.base_url or not payload.default_model:
        raise HTTPException(status_code=400, detail="base_url and default_model are required")

    provider = upsert_provider(
        name,
        base_url=payload.base_url,
        api_key_env=payload.api_key_env or "LLM_API_KEY",
        default_model=payload.default_model,
        enabled=True if payload.enabled is None else payload.enabled,
        path=settings.llm_providers_file,
    )
    return provider_to_dict(provider)


@router.post("/providers/{name}/test")
async def test_provider(
    name: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    from dashboard.app import settings

    try:
        provider = get_enabled_provider(name, settings.llm_providers_file)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    base_url = provider.base_url.rstrip("/")
    api_key = os.getenv(provider.api_key_env, "")

    headers = {
        "User-Agent": "Unified-AI-Software-Dashboard/1.0",
        "Accept": "application/json",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(f"{base_url}/models", headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            return {
                "provider": name,
                "status": "ok",
                "models_count": len(data.get("data", [])),
            }
    except Exception as exc:
        return {
            "provider": name,
            "status": "error",
            "error": str(exc),
        }


@router.patch("/providers/{name}")
async def patch_provider(
    name: str,
    payload: ProviderPayload,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    from dashboard.app import settings

    try:
        provider = update_provider(
            name,
            base_url=payload.base_url,
            api_key_env=payload.api_key_env,
            default_model=payload.default_model,
            enabled=payload.enabled,
            path=settings.llm_providers_file,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return provider_to_dict(provider)


@router.delete("/providers/{name}")
async def delete_provider(
    name: str,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    from dashboard.app import settings

    if not remove_provider(name, settings.llm_providers_file):
        raise HTTPException(status_code=404, detail=f"No custom provider named {name}")

    return {"removed": name}


@router.post("/providers/{name}/use")
async def use_provider(
    name: str,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    from dashboard.app import settings

    try:
        provider = get_enabled_provider(name, settings.llm_providers_file)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    env_path = Path(os.getenv("DASHBOARD_ENV_FILE", ".env"))
    write_env_value(env_path, "LLM_PROVIDER", provider.name)

    return {"active": provider.name}
```

---

# 3. Fix `dashboard/routers/agents.py`

Thay import đầu file:

```python
from fastapi import APIRouter, Depends, HTTPException, Request
```

Đổi auth import:

```python
from dashboard.routers.auth import require_auth, require_role
```

Sau đó sửa các route như dưới đây.

```python
@router.get("/agents/config")
def get_all_agents_config(
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT agent_id, name, model, system_prompt, updated_at FROM agents_config"
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("/agents/config/{agent_id}")
def update_single_agent_config(
    agent_id: str,
    payload: AgentConfigRequest,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    now = datetime.now().isoformat()
    with _connect() as connection:
        existing = connection.execute(
            "SELECT agent_id FROM agents_config WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        connection.execute(
            "UPDATE agents_config SET model = ?, system_prompt = ?, updated_at = ? WHERE agent_id = ?",
            (payload.model, payload.system_prompt, now, agent_id),
        )
        connection.commit()

    return {"agent_id": agent_id, "status": "updated"}


@router.get("/agents/{agent_id}")
def get_single_agent(
    agent_id: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT agent_id, name, type, status, model, system_prompt, description, updated_at
            FROM agents_config
            WHERE agent_id = ?
            """,
            (agent_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return dict(row)


@router.patch("/agents/{agent_id}")
def patch_agent(
    agent_id: str,
    payload: AgentConfigRequest,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    now = datetime.now().isoformat()
    with _connect() as connection:
        existing = connection.execute(
            "SELECT agent_id FROM agents_config WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        connection.execute(
            "UPDATE agents_config SET model = ?, system_prompt = ?, updated_at = ? WHERE agent_id = ?",
            (payload.model, payload.system_prompt, now, agent_id),
        )
        connection.commit()

    return {"agent_id": agent_id, "status": "updated"}


@router.post("/agents/{agent_id}/test")
async def test_agent(
    agent_id: str,
    request: Request,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
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
                {
                    "role": "system",
                    "content": row["system_prompt"] or "You are a helpful assistant.",
                },
                {
                    "role": "user",
                    "content": "Reply with exactly: OK",
                },
            ],
            max_tokens=10,
        )
        reply = response.choices[0].message.content or ""
        return {
            "agent_id": agent_id,
            "model": row["model"],
            "status": "ok",
            "response": reply.strip(),
        }

    except Exception as exc:
        return {
            "agent_id": agent_id,
            "model": row["model"],
            "status": "error",
            "error": str(exc),
        }
```

Sửa settings/system routes:

```python
@router.get("/settings")
def get_system_settings_dict(
    _auth: dict = Depends(require_auth),
) -> dict[str, str]:
    with _connect() as connection:
        rows = connection.execute("SELECT key, value FROM system_settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


@router.get("/system/settings")
def get_system_settings_alias(
    _auth: dict = Depends(require_auth),
) -> dict[str, str]:
    return get_system_settings_dict(_auth)


@router.patch("/system/settings")
def patch_system_settings(
    payload: SettingsRequest,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, str]:
    return update_system_settings_dict(payload, _auth)


@router.get("/system/status")
def get_system_status(
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
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
def update_system_settings_dict(
    payload: SettingsRequest,
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, str]:
    now = datetime.now().isoformat()

    with _connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES ('daily_cost_limit', ?, ?)",
            (payload.daily_cost_limit, now),
        )
        connection.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES ('smart_model_fallback', ?, ?)",
            (payload.smart_model_fallback, now),
        )
        connection.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES ('max_repair_attempts', ?, ?)",
            (payload.max_repair_attempts, now),
        )
        connection.commit()

    env_path = Path(os.getenv("DASHBOARD_ENV_FILE", ".env"))

    try:
        write_env_value(env_path, "DAILY_COST_LIMIT", payload.daily_cost_limit)
        write_env_value(env_path, "FALLBACK_SMART_MODEL", payload.smart_model_fallback)
        write_env_value(env_path, "MAX_REPAIR_ATTEMPTS", payload.max_repair_attempts)
    except Exception:
        pass

    return {"status": "saved"}


@router.post("/settings/wipe")
def wipe_all_system_data(
    _auth: dict = Depends(require_role("admin")),
) -> dict[str, Any]:
    import shutil
    from dashboard.database import GENERATED_APPS_DIR

    with _connect() as connection:
        connection.execute("DELETE FROM jobs")
        connection.execute("DELETE FROM initiatives")
        connection.execute("DELETE FROM system_settings")
        connection.execute("DELETE FROM agents_config")
        connection.commit()

    _connect().close()

    if GENERATED_APPS_DIR.exists():
        for item in GENERATED_APPS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

    memory_path = Path(__file__).resolve().parents[2] / "storage" / "memory.json"
    if memory_path.exists():
        try:
            memory_path.write_text("{}", encoding="utf-8")
        except Exception:
            pass

    return {
        "status": "success",
        "message": "All data wiped and reset to default startup state.",
    }
```

---

# 4. Fix `/api/jobs/{slug}/phases`

Trong `dashboard/routers/jobs.py`, sửa import database.

Nếu đang có:

```python
from dashboard.database import (
    GENERATED_APPS_DIR,
    ...
    phase_status,
)
```

thêm `list_job_phases`:

```python
from dashboard.database import (
    GENERATED_APPS_DIR,
    get_job,
    list_jobs,
    list_job_phases,
    phase_status,
    request_job_cancellation,
    delete_job_record,
    _upsert_job,
)
```

Sau đó thay route phases cũ:

```python
@router.get("/{slug}/phases")
def get_job_phases(slug: str) -> dict[str, str]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return phase_status(slug)
```

bằng:

```python
@router.get("/{slug}/phases")
def get_job_phases(
    slug: str,
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list_job_phases(slug)
```

Nếu frontend cũ vẫn cần dict status, thêm route phụ:

```python
@router.get("/{slug}/phase-status")
def get_job_phase_status(
    slug: str,
    _auth: dict = Depends(require_auth),
) -> dict[str, str]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return phase_status(slug)
```

---

# 5. Thêm bảng `job_phase_attempts`

Trong `dashboard/database.py`, thêm schema này vào `_create_tables()` hoặc nơi đang create DB schema.

```python
connection.execute(
    """
    CREATE TABLE IF NOT EXISTS job_phase_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_slug TEXT NOT NULL,
        phase TEXT NOT NULL,
        attempt INTEGER NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        error TEXT,
        output_files_json TEXT,
        logs_path TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """
)
```

Thêm index:

```python
connection.execute(
    """
    CREATE INDEX IF NOT EXISTS idx_job_phase_attempts_job_phase
    ON job_phase_attempts(job_slug, phase, attempt)
    """
)
```

## Thêm helper functions vào `database.py`

```python
def next_phase_attempt(job_slug: str, phase: str) -> int:
    phase_id = _canonical_phase(phase)
    assert phase_id is not None

    with _connect() as connection:
        row = connection.execute(
            """
            SELECT COALESCE(MAX(attempt), 0) AS max_attempt
            FROM job_phase_attempts
            WHERE job_slug = ? AND phase = ?
            """,
            (job_slug, phase_id),
        ).fetchone()

    return int(row["max_attempt"] or 0) + 1


def start_phase_attempt(job_slug: str, phase: str, attempt: int | None = None) -> int:
    phase_id = _canonical_phase(phase)
    assert phase_id is not None

    selected_attempt = attempt or next_phase_attempt(job_slug, phase_id)

    def operation() -> int:
        with _connect() as connection:
            timestamp = _now()
            connection.execute(
                """
                INSERT INTO job_phase_attempts (
                    job_slug,
                    phase,
                    attempt,
                    status,
                    started_at,
                    finished_at,
                    error,
                    output_files_json,
                    logs_path,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'running', ?, NULL, NULL, '[]', NULL, ?, ?)
                """,
                (
                    job_slug,
                    phase_id,
                    selected_attempt,
                    timestamp,
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()

        return selected_attempt

    return _with_write_retry(operation)


def finish_phase_attempt(
    job_slug: str,
    phase: str,
    attempt: int,
    status: str,
    *,
    error: str | None = None,
    output_files: list[str] | tuple[str, ...] | None = None,
    logs_path: str | None = None,
) -> None:
    phase_id = _canonical_phase(phase)
    assert phase_id is not None
    _validate_phase_status(status)

    normalized_outputs = [str(path) for path in (output_files or [])]

    def operation() -> None:
        with _connect() as connection:
            timestamp = _now()
            connection.execute(
                """
                UPDATE job_phase_attempts
                SET status = ?,
                    finished_at = ?,
                    error = ?,
                    output_files_json = ?,
                    logs_path = ?,
                    updated_at = ?
                WHERE job_slug = ? AND phase = ? AND attempt = ?
                """,
                (
                    status,
                    timestamp,
                    error,
                    json.dumps(normalized_outputs),
                    logs_path,
                    timestamp,
                    job_slug,
                    phase_id,
                    attempt,
                ),
            )
            connection.commit()

    _with_write_retry(operation)


def list_phase_attempts(job_slug: str, phase: str | None = None) -> list[dict[str, Any]]:
    with _connect() as connection:
        if phase:
            phase_id = _canonical_phase(phase)
            assert phase_id is not None
            rows = connection.execute(
                """
                SELECT *
                FROM job_phase_attempts
                WHERE job_slug = ? AND phase = ?
                ORDER BY phase ASC, attempt ASC
                """,
                (job_slug, phase_id),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM job_phase_attempts
                WHERE job_slug = ?
                ORDER BY phase ASC, attempt ASC
                """,
                (job_slug,),
            ).fetchall()

    return [dict(row) for row in rows]
```

---

# 6. Ghi attempt cho phase QA/Runtime/Security

Trong `agents/flutter_factory/orchestrator.py`, chỗ nào chạy phase có thể chạy lại như:

```python
start_phase(slug, "07_static_qa")
...
finish_phase(slug, "07_static_qa", "passed")
```

đổi thành pattern:

```python
from dashboard.database import start_phase_attempt, finish_phase_attempt
```

Ví dụ cho `07_static_qa`:

```python
attempt = start_phase_attempt(slug, "07_static_qa")

try:
    start_phase(slug, "07_static_qa")

    qa_report = qa_agent.run_static_qa(...)

    finish_phase_attempt(
        slug,
        "07_static_qa",
        attempt,
        "passed",
        output_files=[
            "docs/test_report.md",
            "docs/bug_list.md",
            "docs/static_analysis.log",
            "docs/qa_summary.json",
        ],
    )

    finish_phase(
        slug,
        "07_static_qa",
        "passed",
        output_files=[
            "docs/test_report.md",
            "docs/bug_list.md",
            "docs/static_analysis.log",
            "docs/qa_summary.json",
        ],
    )

except Exception as exc:
    finish_phase_attempt(
        slug,
        "07_static_qa",
        attempt,
        "failed",
        error=str(exc),
    )
    finish_phase(
        slug,
        "07_static_qa",
        "failed",
        error=str(exc),
    )
    raise
```

Tương tự áp dụng cho:

```text
07_static_qa
08_refactor_repair
09_runtime_test
10_security_audit
```

---

# 7. Thêm API xem attempts

Trong `dashboard/routers/jobs.py`, import:

```python
from dashboard.database import list_phase_attempts
```

Thêm route:

```python
@router.get("/{slug}/phase-attempts")
def get_job_phase_attempts(
    slug: str,
    phase: str | None = None,
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    if get_job(slug) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list_phase_attempts(slug, phase)
```

Dùng:

```http
GET /api/jobs/pantry-saver/phase-attempts
GET /api/jobs/pantry-saver/phase-attempts?phase=07_static_qa
```

---

# 8. Thêm CI workflow

Tạo file:

```text
.github/workflows/ci.yml
```

Nội dung:

```yaml
name: CI

on:
  push:
    branches:
      - master
      - main
  pull_request:

jobs:
  backend:
    name: Backend checks
    runs-on: ubuntu-latest

    env:
      APP_ENV: development
      DASHBOARD_SECRET: test-secret
      ADMIN_API_KEY: test-admin-key
      LLM_PROVIDER: openrouter
      LLM_API_KEY: test-key
      LLM_MODEL: google/gemini-2.5-flash
      JOB_QUEUE_BACKEND: thread
      FACTORY_PIPELINE_MODE: modular

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install backend dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run Ruff
        run: |
          ruff check .

      - name: Run Pytest
        run: |
          pytest

  frontend:
    name: Frontend build
    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: frontend

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install frontend dependencies
        run: npm install

      - name: Build frontend
        run: npm run build
```

---

# 9. Thêm tests auth coverage

Tạo file:

```text
tests/test_auth_coverage.py
```

```python
from __future__ import annotations

import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from dashboard.app import create_app
from dashboard.jwt_utils import encode_hs256


SECRET = "test-secret"
ADMIN_KEY = "test-admin-key"


def _make_client(tmp_path: Path) -> TestClient:
    os.environ["APP_ENV"] = "development"
    os.environ["DASHBOARD_SECRET"] = SECRET
    os.environ["ADMIN_API_KEY"] = ADMIN_KEY
    os.environ["DASHBOARD_DB_PATH"] = str(tmp_path / "dashboard.db")
    return TestClient(create_app())


def _token(role: str = "admin") -> str:
    now = int(time.time())
    return encode_hs256(
        {
            "team_id": "test",
            "role": role,
            "iat": now,
            "exp": now + 3600,
        },
        SECRET,
    )


def test_project_mutation_routes_require_auth():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))

        assert client.get("/api/projects/example").status_code == 401
        assert client.put("/api/projects/example", json={}).status_code == 401
        assert client.patch("/api/projects/example", json={}).status_code == 401
        assert client.delete("/api/projects/example").status_code == 401


def test_provider_mutation_routes_require_auth():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))

        assert client.get("/api/models").status_code == 401
        assert client.post("/api/providers", json={}).status_code == 401
        assert client.post("/api/providers/openrouter", json={}).status_code == 401
        assert client.post("/api/providers/openrouter/test").status_code == 401
        assert client.patch("/api/providers/openrouter", json={}).status_code == 401
        assert client.delete("/api/providers/openrouter").status_code == 401


def test_agent_and_settings_routes_require_auth():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))

        assert client.get("/api/agents/some-agent").status_code == 401
        assert client.post("/api/agents/some-agent/test").status_code == 401
        assert client.get("/api/settings").status_code == 401
        assert client.get("/api/system/settings").status_code == 401
        assert client.patch("/api/system/settings", json={}).status_code == 401
        assert client.post("/api/settings", json={}).status_code == 401
        assert client.post("/api/settings/wipe").status_code == 401


def test_admin_can_access_protected_system_status():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))
        response = client.get(
            "/api/system/status",
            headers={"Authorization": f"Bearer {_token('admin')}"},
        )
        assert response.status_code == 200
```

---

# 10. Chạy kiểm tra

```bash
make setup
ruff check .
pytest
```

Test riêng:

```bash
pytest tests/test_auth_coverage.py
```

---

# 11. Commit

```bash
git status
git add dashboard/routers/projects.py \
        dashboard/routers/providers.py \
        dashboard/routers/agents.py \
        dashboard/routers/jobs.py \
        dashboard/database.py \
        .github/workflows/ci.yml \
        tests/test_auth_coverage.py

git commit -m "fix: protect sensitive dashboard routes and add CI"
git pull --rebase origin master
git push origin master
```

---

Sau khi fix xong nhóm này, repo mới an toàn hơn để nghĩ tới deploy public. Phần bắt buộc nhất là **auth coverage + bỏ API key query + CI**.
