"""
LLM provider registry.
Providers are OpenAI-compatible endpoints used by AsyncOpenAI. Built-ins cover
common providers; custom providers are persisted in .aiorg/providers.json.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    default_model: str
    enabled: bool = True
    source: str = "builtin"


BUILT_IN_PROVIDERS: dict[str, ProviderConfig] = {
    "openrouter": ProviderConfig(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="LLM_API_KEY",
        default_model="google/gemini-2.5-flash",
    ),
    "openai": ProviderConfig(
        name="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o-mini",
    ),
    "deepseek": ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
    ),
    "ollama": ProviderConfig(
        name="ollama",
        base_url="http://localhost:11434/v1",
        api_key_env="OLLAMA_API_KEY",
        default_model="qwen2.5-coder:7b",
    ),
    "groq": ProviderConfig(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        default_model="llama-3.1-8b-instant",
    ),
    "together": ProviderConfig(
        name="together",
        base_url="https://api.together.xyz/v1",
        api_key_env="TOGETHER_API_KEY",
        default_model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    ),
    "fireworks": ProviderConfig(
        name="fireworks",
        base_url="https://api.fireworks.ai/inference/v1",
        api_key_env="FIREWORKS_API_KEY",
        default_model="accounts/fireworks/models/llama-v3p1-8b-instruct",
    ),
    "xai": ProviderConfig(
        name="xai",
        base_url="https://api.x.ai/v1",
        api_key_env="XAI_API_KEY",
        default_model="grok-2-latest",
    ),
    "gemini": ProviderConfig(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key_env="GEMINI_API_KEY",
        default_model="gemini-1.5-flash",
    ),
}


def get_provider_file(path: str | None = None) -> Path:
    return Path(path or os.getenv("LLM_PROVIDERS_FILE", ".aiorg/providers.json"))


def list_providers(path: str | None = None) -> dict[str, ProviderConfig]:
    """Return built-in providers plus custom overrides."""
    providers = dict(BUILT_IN_PROVIDERS)
    providers.update(_load_custom(path))
    return dict(sorted(providers.items()))


def get_provider(name: str, path: str | None = None) -> ProviderConfig | None:
    return list_providers(path).get(_normalize_name(name))


def upsert_provider(
    name: str,
    *,
    base_url: str,
    api_key_env: str,
    default_model: str,
    enabled: bool = True,
    path: str | None = None,
) -> ProviderConfig:
    """Create or replace a custom provider entry."""
    provider = ProviderConfig(
        name=_normalize_name(name),
        base_url=base_url,
        api_key_env=api_key_env,
        default_model=default_model,
        enabled=enabled,
        source="custom",
    )
    custom = _load_custom(path)
    custom[provider.name] = provider
    _save_custom(custom, path)
    return provider


def update_provider(
    name: str,
    *,
    base_url: str | None = None,
    api_key_env: str | None = None,
    default_model: str | None = None,
    enabled: bool | None = None,
    path: str | None = None,
) -> ProviderConfig:
    """Update a provider. Built-ins are copied to custom overrides."""
    current = get_provider(name, path)
    if current is None:
        raise KeyError(f"Unknown provider: {name}")
    return upsert_provider(
        current.name,
        base_url=base_url or current.base_url,
        api_key_env=api_key_env or current.api_key_env,
        default_model=default_model or current.default_model,
        enabled=current.enabled if enabled is None else enabled,
        path=path,
    )


def remove_provider(name: str, path: str | None = None) -> bool:
    """Remove a custom provider or custom override. Built-in defaults remain available."""
    normalized = _normalize_name(name)
    custom = _load_custom(path)
    if normalized not in custom:
        return False
    del custom[normalized]
    _save_custom(custom, path)
    return True


def resolve_active_provider(
    provider_name: str,
    *,
    fallback_base_url: str,
    fallback_api_key_env: str = "LLM_API_KEY",
    fallback_model: str,
    path: str | None = None,
) -> ProviderConfig:
    """Resolve selected provider, or synthesize one from legacy LLM_* settings."""
    normalized = _normalize_name(provider_name)
    if normalized:
        provider = get_provider(normalized, path)
        if provider is None:
            raise KeyError(f"Unknown provider: {provider_name}")
        return provider
    return ProviderConfig(
        name="legacy",
        base_url=fallback_base_url,
        api_key_env=fallback_api_key_env,
        default_model=fallback_model,
        source="legacy",
    )


def provider_to_dict(provider: ProviderConfig, *, redact_secret: bool = True) -> dict[str, Any]:
    data = asdict(provider)
    data["api_key_set"] = bool(os.getenv(provider.api_key_env))
    if redact_secret:
        data["api_key_value"] = "***" if data["api_key_set"] else "(not set)"
    return data


def provider_registry_payload(
    *,
    active_provider: str = "",
    path: str | None = None,
) -> dict[str, Any]:
    """Return provider registry data suitable for CLI JSON and dashboard APIs."""
    active = _normalize_name(active_provider) or "legacy"
    return {
        "active": active,
        "providers": {
            name: {
                **provider_to_dict(provider),
                "active": name == active,
            }
            for name, provider in list_providers(path).items()
        },
    }


def get_enabled_provider(name: str, path: str | None = None) -> ProviderConfig:
    """Return a provider or raise a clear exception if unknown/disabled."""
    provider = get_provider(name, path)
    if provider is None:
        raise KeyError(f"Unknown provider: {name}")
    if not provider.enabled:
        raise ValueError(f"Provider is disabled: {provider.name}")
    return provider


def _load_custom(path: str | None = None) -> dict[str, ProviderConfig]:
    provider_file = get_provider_file(path)
    if not provider_file.exists():
        return {}
    try:
        raw = json.loads(provider_file.read_text(encoding="utf-8"))
    except Exception:
        return {}
    providers = raw.get("providers", raw)
    result = {}
    for name, data in providers.items():
        normalized = _normalize_name(name)
        result[normalized] = ProviderConfig(
            name=normalized,
            base_url=str(data.get("base_url", "")),
            api_key_env=str(data.get("api_key_env", "LLM_API_KEY")),
            default_model=str(data.get("default_model", "")),
            enabled=bool(data.get("enabled", True)),
            source="custom",
        )
    return result


def _save_custom(providers: dict[str, ProviderConfig], path: str | None = None) -> None:
    provider_file = get_provider_file(path)
    provider_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "providers": {
            name: {
                "base_url": provider.base_url,
                "api_key_env": provider.api_key_env,
                "default_model": provider.default_model,
                "enabled": provider.enabled,
            }
            for name, provider in sorted(providers.items())
        }
    }
    provider_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _normalize_name(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "-")
