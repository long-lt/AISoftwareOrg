"""
config/client.py
Centralized LLM client factory — injectable, mockable.

Usage:
    from config.client import create_llm_client, LLMClient

    # Default (read from config)
    client = create_llm_client()

    # Custom model
    client = create_llm_client(model="gpt-4")
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI


def create_llm_client(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> AsyncOpenAI:
    """Create an AsyncOpenAI client.

    Args:
        api_key: Defaults to config.LLM_API_KEY.
        base_url: Defaults to config.LLM_BASE_URL.
        model: Not used by the client itself (passed separately).

    Returns:
        AsyncOpenAI instance.
    """
    from config.settings import AppSettings
    from config.providers import resolve_active_provider

    settings = AppSettings()
    provider = resolve_active_provider(
        settings.llm_provider,
        fallback_base_url=settings.llm_base_url,
        fallback_model=settings.llm_model,
        path=settings.llm_providers_file,
    )

    resolved_base_url = base_url or provider.base_url
    if settings.use_local_llm:
        resolved_base_url = settings.ollama_base_url
        provider_api_key = os.getenv("OLLAMA_API_KEY", "")
    else:
        provider_api_key = os.getenv(provider.api_key_env, "")

    return AsyncOpenAI(
        api_key=api_key or provider_api_key or settings.llm_api_key or "dummy",
        base_url=resolved_base_url,
    )
