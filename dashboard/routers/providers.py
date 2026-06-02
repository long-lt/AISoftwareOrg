"""
dashboard/routers/providers.py
Router for LLM Models and Custom Providers registry management.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from dashboard.routers.auth import require_auth

from config.env_file import write_env_value
from config.providers import (
    get_enabled_provider,
    provider_registry_payload,
    provider_to_dict,
    remove_provider,
    update_provider,
    upsert_provider,
)

router = APIRouter()


class ProviderPayload(BaseModel):
    base_url: str | None = None
    api_key_env: str | None = None
    default_model: str | None = None
    enabled: bool | None = None


class ProviderCreatePayload(BaseModel):
    name: str
    base_url: str
    api_key_env: str = "LLM_API_KEY"
    default_model: str
    enabled: bool = True


@router.get("/models")
async def list_active_provider_models(
    provider: Optional[str] = Query(None),
    key: Optional[str] = Query(None),
    base_url: Optional[str] = Query(None)
) -> dict[str, Any]:
    from dashboard.app import settings

    active_name = provider or settings.llm_provider
    
    resolved_base_url = base_url
    resolved_key = key
    
    if not resolved_base_url or not resolved_key:
        from config.providers import get_enabled_provider
        try:
            p_config = get_enabled_provider(active_name, settings.llm_providers_file)
            if not resolved_base_url:
                resolved_base_url = p_config.base_url
            if not resolved_key:
                resolved_key = os.getenv(p_config.api_key_env, "")
        except Exception:
            pass

    if not resolved_base_url:
        defaults = {
            "openai": "https://api.openai.com/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
            "deepseek": "https://api.deepseek.com/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "ollama": "http://localhost:11434/v1"
        }
        resolved_base_url = defaults.get(active_name, "https://api.openai.com/v1")

    resolved_base_url = resolved_base_url.rstrip("/")
    url = f"{resolved_base_url}/models"
    
    headers = {
        "User-Agent": "Unified-AI-Software-Dashboard/1.0",
        "Accept": "application/json"
    }
    if resolved_key:
        headers["Authorization"] = f"Bearer {resolved_key}"
        
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            models_list = res_data.get("data", [])
            return {
                "provider": active_name,
                "success": True,
                "models": models_list
            }
    except urllib.error.URLError as e:
        fallbacks = {
            "openai": [
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
                {"id": "gpt-4o", "name": "GPT-4o"},
                {"id": "o1-mini", "name": "o1 Mini"},
                {"id": "o1-preview", "name": "o1 Preview"}
            ],
            "gemini": [
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
                {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash"}
            ],
            "deepseek": [
                {"id": "deepseek-chat", "name": "DeepSeek V3"},
                {"id": "deepseek-coder", "name": "DeepSeek Coder V2"}
            ],
            "openrouter": [
                {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
                {"id": "qwen/qwen-2.5-coder-32b", "name": "Qwen 2.5 Coder 32B"},
                {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"},
                {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3"}
            ],
            "ollama": [
                {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder 7B"},
                {"id": "llama3.1:8b", "name": "Llama 3.1 8B"},
                {"id": "codegemma", "name": "CodeGemma"}
            ]
        }
        return {
            "provider": active_name,
            "success": False,
            "error": str(e),
            "models": fallbacks.get(active_name, [])
        }
    except Exception as e:
        return {
            "provider": active_name,
            "success": False,
            "error": str(e),
            "models": []
        }


@router.post("/providers")
async def add_provider_body(payload: ProviderCreatePayload) -> dict[str, Any]:
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
async def get_providers(_auth: dict = Depends(require_auth)) -> dict[str, Any]:
    from dashboard.app import settings
    return provider_registry_payload(
        active_provider=settings.llm_provider,
        path=settings.llm_providers_file,
    )


@router.post("/providers/{name}")
async def add_provider(name: str, payload: ProviderPayload) -> dict[str, Any]:
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
async def test_provider(name: str) -> dict[str, Any]:
    from dashboard.app import settings
    try:
        provider = get_enabled_provider(name, settings.llm_providers_file)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    import urllib.request
    import urllib.error
    import os

    base_url = provider.base_url.rstrip("/")
    api_key = os.getenv(provider.api_key_env, "")
    headers = {"User-Agent": "Unified-AI-Software-Dashboard/1.0", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(f"{base_url}/models", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            return {"provider": name, "status": "ok", "models_count": len(data.get("data", []))}
    except Exception as exc:
        return {"provider": name, "status": "error", "error": str(exc)}


@router.patch("/providers/{name}")
async def patch_provider(name: str, payload: ProviderPayload) -> dict[str, Any]:
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
async def delete_provider(name: str) -> dict[str, Any]:
    from dashboard.app import settings
    if not remove_provider(name, settings.llm_providers_file):
        raise HTTPException(status_code=404, detail=f"No custom provider named {name}")
    return {"removed": name}


@router.post("/providers/{name}/use")
async def use_provider(name: str, _auth: dict = Depends(require_auth)) -> dict[str, Any]:
    from dashboard.app import settings
    try:
        provider = get_enabled_provider(name, settings.llm_providers_file)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    env_path = Path(os.getenv("DASHBOARD_ENV_FILE", ".env"))
    write_env_value(env_path, "LLM_PROVIDER", provider.name)
    return {"active": provider.name}
