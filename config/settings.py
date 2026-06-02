"""
config/settings.py
Centralized configuration với Pydantic BaseSettings.
Load từ .env file tự động. Có validation, type casting, defaults.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """App configuration — load từ .env và environment variables.

    Usage:
        from config.settings import AppSettings
        settings = AppSettings()
        print(settings.llm_model)
    """

    # LLM config
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="LLM_BASE_URL"
    )
    llm_model: str = Field(
        default="deepseek/deepseek-v4-flash", alias="LLM_MODEL"
    )
    llm_provider: str = Field(default="openrouter", alias="LLM_PROVIDER")
    llm_providers_file: str = Field(default=".aiorg/providers.json", alias="LLM_PROVIDERS_FILE")

    # Per-agent model overrides (empty = use llm_model)
    dev_model: str = Field(default="", alias="DEV_MODEL")
    reviewer_model: str = Field(default="", alias="REVIEWER_MODEL")
    qa_model: str = Field(default="", alias="QA_MODEL")
    pm_model: str = Field(default="", alias="PM_MODEL")
    planner_model: str = Field(default="", alias="PLANNER_MODEL")

    # LLM routing tiers
    fast_llm_model: str = Field(default="", alias="FAST_LLM_MODEL")
    medium_llm_model: str = Field(default="", alias="MEDIUM_LLM_MODEL")
    strong_llm_model: str = Field(default="", alias="STRONG_LLM_MODEL")
    use_local_llm: bool = Field(default=False, alias="USE_LOCAL_LLM")
    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="codellama:7b", alias="OLLAMA_MODEL")

    # Pipeline defaults
    max_attempts: int = Field(default=3, alias="MAX_ATTEMPTS")
    max_repair_attempts: int = Field(default=2, alias="MAX_REPAIR_ATTEMPTS")
    use_docker: bool = Field(default=False, alias="USE_DOCKER")

    # Dashboard
    dashboard_host: str = Field(default="0.0.0.0", alias="DASHBOARD_HOST")
    dashboard_port: int = Field(default=8000, alias="DASHBOARD_PORT")
    admin_api_key: str = Field(default="", alias="ADMIN_API_KEY")

    # Redis connection url for queues and message bus
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }

    def get_dev_model(self) -> str:
        return self.dev_model or self.llm_model

    def get_reviewer_model(self) -> str:
        return self.reviewer_model or self.llm_model

    def get_qa_model(self) -> str:
        return self.qa_model or self.llm_model

    def get_pm_model(self) -> str:
        return self.pm_model or self.llm_model

    def get_planner_model(self) -> str:
        return self.planner_model or self.llm_model
