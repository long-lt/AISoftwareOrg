"""
Model router for choosing the cheapest suitable LLM per agent/task.

Defaults preserve existing behavior: if no tier models are configured, every
route returns LLM_MODEL. Per-agent overrides still win.
"""

from __future__ import annotations

from dataclasses import dataclass, field


_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"


@dataclass(frozen=True)
class LLMRouter:
    """Route agent calls to fast, medium, strong, or local models."""

    default_model: str
    fast_model: str = ""
    medium_model: str = ""
    strong_model: str = ""
    use_local_llm: bool = False
    ollama_model: str = "codellama:7b"
    ollama_base_url: str = _DEFAULT_OLLAMA_BASE_URL
    agent_overrides: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LLMRouter":
        """Build router config from environment and app settings."""
        from config.providers import resolve_active_provider
        from config.settings import AppSettings

        settings = AppSettings()
        provider = resolve_active_provider(
            settings.llm_provider,
            fallback_base_url=settings.llm_base_url,
            fallback_model=settings.llm_model,
            path=settings.llm_providers_file,
        )
        default_settings_model = AppSettings.model_fields["llm_model"].default
        default_model = settings.llm_model
        if settings.llm_provider and settings.llm_model == default_settings_model:
            default_model = provider.default_model or settings.llm_model
        return cls(
            default_model=default_model,
            fast_model=settings.fast_llm_model,
            medium_model=settings.medium_llm_model,
            strong_model=settings.strong_llm_model,
            use_local_llm=settings.use_local_llm,
            ollama_model=settings.ollama_model,
            ollama_base_url=settings.ollama_base_url,
            agent_overrides={
                "dev": settings.dev_model,
                "reviewer": settings.reviewer_model,
                "qa": settings.qa_model,
                "pm": settings.pm_model,
                "planner": settings.planner_model,
            },
        )

    def route(
        self,
        task_type: str,
        context_length: int = 0,
        is_retry: bool = False,
    ) -> str:
        """Return the selected model for an agent/task."""
        role = _normalize_task_type(task_type)

        override = self.agent_overrides.get(role, "")
        if override:
            return override

        if self.use_local_llm:
            return self.ollama_model

        if role in {"pm", "planner"}:
            return self._pick("fast")
        if role == "dev" and (is_retry or context_length > 4000):
            return self._pick("strong")
        return self._pick("medium")

    def base_url(self) -> str | None:
        """Return provider base URL override when local LLM routing is enabled."""
        return self.ollama_base_url if self.use_local_llm else None

    def _pick(self, tier: str) -> str:
        if tier == "fast":
            return self.fast_model or self.default_model
        if tier == "strong":
            return self.strong_model or self.medium_model or self.default_model
        return self.medium_model or self.default_model


def route_model(task_type: str, context_length: int = 0, is_retry: bool = False) -> str:
    """Route a model using current environment settings."""
    return LLMRouter.from_env().route(task_type, context_length, is_retry)


def _normalize_task_type(task_type: str) -> str:
    normalized = (task_type or "").strip().lower()
    aliases = {
        "devagent": "dev",
        "developer": "dev",
        "backend developer": "dev",
        "qaagent": "qa",
        "quality assurance engineer": "qa",
        "revieweragent": "reviewer",
        "senior software engineer": "reviewer",
        "pmagent": "pm",
        "product manager": "pm",
        "planneragent": "planner",
        "software architect": "planner",
    }
    return aliases.get(normalized, normalized)
