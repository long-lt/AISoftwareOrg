"""
config/__init__.py
Cấu hình hệ thống — wrapper quanh AppSettings.
Constants giữ nguyên tên cũ để các agents không cần sửa nhiều.
"""

from .settings import AppSettings

_settings = AppSettings()

# Backward-compatible constants
LLM_API_KEY = _settings.llm_api_key
LLM_BASE_URL = _settings.llm_base_url
LLM_MODEL = _settings.llm_model
LLM_PROVIDER = _settings.llm_provider
LLM_PROVIDERS_FILE = _settings.llm_providers_file

DEV_MODEL = _settings.get_dev_model()
REVIEWER_MODEL = _settings.get_reviewer_model()
QA_MODEL = _settings.get_qa_model()
PM_MODEL = _settings.get_pm_model()
PLANNER_MODEL = _settings.get_planner_model()
