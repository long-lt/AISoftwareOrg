"""
workflows/flutter_mvp.py
Wrapper workflow for Flutter MVP 12-Phase Pipeline.
Imports the orchestrator from agents.flutter_factory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.flutter_factory.orchestrator import run_full_pipeline, export_source_archive, PipelineResult


def run_flutter_mvp_pipeline(app_input: dict[str, Any], app_dir: Path) -> PipelineResult:
    """Chạy toàn bộ pipeline Flutter MVP sinh code tự động 12 bước.

    Args:
        app_input: Cấu hình thông tin app sinh ra (slug, features, style, backend, etc.).
        app_dir: Thư mục chứa tài liệu sinh ra và mã nguồn đầu ra.
    """
    return run_full_pipeline(app_input, app_dir)
