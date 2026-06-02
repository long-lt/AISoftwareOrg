"""
dashboard/database.py
SQLite Database operations and repository helpers for the AI Software Factory.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

# Base Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
GENERATED_APPS_DIR = ROOT_DIR / "workspace" / "generated_apps"
DB_PATH = ROOT_DIR / "workspace" / "jobs.sqlite3"

EXPORT_PHASE_FILES = {
    "create": ["docs/input.json", "docs/app_brief.md", "docs/plane.md"],
    "ba": [
        "docs/requirements.md",
        "docs/user_stories.md",
        "docs/feature_list.md",
        "docs/acceptance_criteria.md",
    ],
    "architect": [
        "docs/architecture.md",
        "docs/folder_structure.md",
        "docs/state_management.md",
        "docs/api_strategy.md",
        "docs/database_strategy.md",
    ],
    "uiux": [
        "docs/design.md",
        "docs/screen_list.md",
        "docs/theme_config.dart",
        "docs/component_spec.md",
    ],
    "dev": ["source/pubspec.yaml", "source/lib/main.dart", "source/lib/app.dart"],
    "qa": ["docs/test_report.md", "docs/bug_list.md"],
    "refactor": ["docs/refactor_report.md"],
    "repair": ["docs/repair_history.md"],
    "runtime": ["docs/runtime_report.md"],
    "security": [
        "docs/security_report.md",
        "docs/deployment_plan.md",
        "docs/env_contract.md",
        "docs/production_release_checklist.md",
    ],
    "reviewer": ["docs/final_review.md", "docs/release_checklist.md"],
    "export": ["docs/export_report.md"],
}


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    
    # 1. Create jobs table
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
          slug TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          description TEXT NOT NULL,
          status TEXT NOT NULL,
          features_json TEXT NOT NULL,
          app_dir TEXT NOT NULL,
          export_path TEXT,
          error TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    
    # 2. Create initiatives table
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS initiatives (
          slug TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          description TEXT NOT NULL,
          status TEXT NOT NULL,
          health TEXT NOT NULL,
          icon TEXT NOT NULL,
          repository TEXT NOT NULL,
          monthly_spend REAL NOT NULL,
          sla TEXT NOT NULL,
          build_progress INTEGER NOT NULL,
          features_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    
    # 3. Create agents_config table
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS agents_config (
          agent_id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          model TEXT NOT NULL,
          system_prompt TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    
    # 4. Create system_settings table
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS system_settings (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    
    # Check if initiatives is empty, populate initial mockup portfolio ONLY ONCE on initial setup
    # (Disabled mockup seeding to support clean zero-state initialization)
    now = datetime.now().isoformat()
    cursor = connection.cursor()
        
    # Check if agents_config is empty, populate all 17 system agents
    cursor.execute("SELECT COUNT(*) FROM agents_config")
    if cursor.fetchone()[0] == 0:
        agents_data = [
            # --- AISoftwareOrg (LangGraph Multi-Agent System - 7 agents) ---
            ("lg_pm", "[LangGraph] Product Manager Agent", "google/gemini-2.5-flash", "Bạn là PM Agent trong hệ thống LangGraph, chịu trách nhiệm quản lý kế hoạch dự án và phân rã các tính năng."),
            ("lg_planner", "[LangGraph] Planner Agent", "google/gemini-2.5-flash", "Bạn là Planner Agent trong hệ thống LangGraph, thiết kế sơ đồ kiến trúc và phân công tasks."),
            ("lg_dev", "[LangGraph] Developer Agent", "google/gemini-2.5-flash", "Bạn là Dev Agent trong hệ thống LangGraph, viết mã nguồn ứng dụng chất lượng cao."),
            ("lg_qa", "[LangGraph] QA Tester Agent", "google/gemini-2.5-flash", "Bạn là QA Agent trong hệ thống LangGraph, chạy unit tests và phát hiện bugs."),
            ("lg_reviewer", "[LangGraph] Reviewer Agent", "google/gemini-2.5-flash", "Bạn là Reviewer Agent trong hệ thống LangGraph, đánh giá chất lượng code PRs."),
            ("lg_devops", "[LangGraph] DevOps Agent", "google/gemini-2.5-flash", "Bạn là DevOps Agent trong hệ thống LangGraph, phụ trách CI/CD và deployment."),
            ("lg_git", "[LangGraph] Git Agent", "google/gemini-2.5-flash", "Bạn là Git Agent trong hệ thống LangGraph, quản lý các branch, commit và repository."),
            
            # --- flutter_ai_factory (12-Phase Pipeline - 10 agents) ---
            ("ba", "[Factory] Business Analyst Agent", "google/gemini-2.5-flash", "Bạn là BA Agent, phân tích đặc tả nghiệp vụ, viết User Stories và Product Spec."),
            ("architect", "[Factory] Architect Agent", "google/gemini-2.5-flash", "Bạn là Architect Agent, thiết kế sơ đồ thư mục và cấu trúc API."),
            ("uiux", "[Factory] UI/UX Designer Agent", "google/gemini-2.5-flash", "Bạn là UI/UX Agent, xây dựng theme Dart và bố cục màn hình."),
            ("dev", "[Factory] Developer Agent", "google/gemini-2.5-flash", "Bạn là Dev Agent, chịu trách nhiệm code Flutter Dart sạch và đúng spec."),
            ("qa", "[Factory] QA Static Tester Agent", "google/gemini-2.5-flash", "Bạn là QA Agent, chạy test tĩnh, flutter analyze và phát hiện lỗi cú pháp."),
            ("refactor", "[Factory] Refactor Agent", "google/gemini-2.5-flash", "Bạn là Refactor Agent, phân tích và tối ưu hóa cấu trúc mã nguồn."),
            ("runtime", "[Factory] Runtime Agent", "google/gemini-2.5-flash", "Bạn là Runtime Agent, kiểm tra phát hiện lỗi khi chạy thực tế ứng dụng."),
            ("security", "[Factory] Security Auditor Agent", "google/gemini-2.5-flash", "Bạn là Security Agent, quét lỗ hổng bảo mật và lập kế hoạch deployment."),
            ("reviewer", "[Factory] Release Reviewer Agent", "google/gemini-2.5-flash", "Bạn là Reviewer Agent, phê duyệt chất lượng và đóng gói MVP bàn giao."),
            ("backend", "[Factory] Backend Developer Agent", "google/gemini-2.5-flash", "Bạn là Backend Agent, phát triển các dịch vụ API backend đi kèm ứng dụng."),
        ]
        for agent_id, name, model, system_prompt in agents_data:
            cursor.execute(
                "INSERT INTO agents_config (agent_id, name, model, system_prompt, updated_at) VALUES (?, ?, ?, ?, ?)",
                (agent_id, name, model, system_prompt, now)
            )
        connection.commit()
        
    # Check if system_settings is empty, populate defaults
    cursor.execute("SELECT COUNT(*) FROM system_settings")
    if cursor.fetchone()[0] == 0:
        settings_data = [
            ("daily_cost_limit", "5.00"),
            ("smart_model_fallback", "anthropic/claude-3.5-sonnet"),
            ("max_repair_attempts", "5")
        ]
        for key, value in settings_data:
            cursor.execute(
                "INSERT INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, now)
            )
        connection.commit()
        
    return connection


def _upsert_job(
    *,
    slug: str,
    name: str,
    description: str,
    status: str,
    features: list[str],
    app_dir: Path,
    export_path: Path | None = None,
    error: str | None = None,
) -> None:
    now = datetime.now().isoformat()
    with _connect() as connection:
        existing = connection.execute(
            "SELECT created_at FROM jobs WHERE slug = ?",
            (slug,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        connection.execute(
            """
            INSERT INTO jobs (
              slug, name, description, status, features_json, app_dir,
              export_path, error, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
              name = excluded.name,
              description = excluded.description,
              status = excluded.status,
              features_json = excluded.features_json,
              app_dir = excluded.app_dir,
              export_path = excluded.export_path,
              error = excluded.error,
              updated_at = excluded.updated_at
            """,
            (
                slug,
                name,
                description,
                status,
                json.dumps(features, ensure_ascii=False),
                str(app_dir),
                str(export_path) if export_path else None,
                error,
                created_at,
                now,
            ),
        )
        connection.commit()


def _job_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["features"] = json.loads(data.pop("features_json") or "[]")
    data["phases"] = phase_status(data["slug"])
    data["download_url"] = (
        f"/api/jobs/{data['slug']}/download" if data.get("export_path") else None
    )
    return data


def list_jobs() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC",
        ).fetchall()
    return [_job_row_to_dict(row) for row in rows]


def get_job(slug: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM jobs WHERE slug = ?",
            (slug,),
        ).fetchone()
    return _job_row_to_dict(row) if row else None


def list_initiatives() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM initiatives ORDER BY created_at DESC",
        ).fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["features"] = json.loads(data.pop("features_json") or "[]")
        result.append(data)
    return result


def get_initiative(slug: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM initiatives WHERE slug = ?",
            (slug,),
        ).fetchone()
    if row:
        data = dict(row)
        data["features"] = json.loads(data.pop("features_json") or "[]")
        return data
    return None


def create_initiative(data: dict[str, Any]) -> dict[str, Any]:
    slug = data.get("slug") or slugify(data["name"])
    now = datetime.now().isoformat()
    with _connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO initiatives (
                slug, name, description, status, health, icon, repository,
                monthly_spend, sla, build_progress, features_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slug,
                data["name"],
                data["description"],
                data.get("status", "discovery"),
                data.get("health", "healthy"),
                data.get("icon", "🤖"),
                data.get("repository", "github.com/factory/" + slug),
                float(data.get("monthly_spend") or 0.0),
                data.get("sla", "100%"),
                int(data.get("build_progress") or 0),
                json.dumps(data.get("features", []), ensure_ascii=False),
                now,
                now,
            )
        )
        connection.commit()
    return get_initiative(slug)


def delete_initiative(slug: str) -> bool:
    with _connect() as connection:
        res = connection.execute("DELETE FROM initiatives WHERE slug = ?", (slug,))
        connection.commit()
        return res.rowcount > 0


def phase_status(slug: str) -> dict[str, str]:
    app_dir = GENERATED_APPS_DIR / slug
    statuses: dict[str, str] = {}
    for phase, files in EXPORT_PHASE_FILES.items():
        statuses[phase] = (
            "done" if all((app_dir / filename).exists() for filename in files) else "pending"
        )
    export_dir = app_dir / "exports"
    if export_dir.exists() and any(export_dir.glob("*_source.zip")):
        statuses["export"] = "done"
    return statuses


def _report_status(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("- Status:"):
                return stripped.removeprefix("- Status:").strip()
            if stripped.startswith("Status:"):
                return stripped.removeprefix("Status:").strip()
    except Exception:
        pass
    return "UNKNOWN"


def _quality_gate_status(app_dir: Path) -> tuple[bool, str | None]:
    docs_dir = app_dir / "docs"
    checks = {
        "qa": _report_status(docs_dir / "test_report.md"),
        "production_qa": _report_status(docs_dir / "production_qa_report.md"),
        "repair": _report_status(docs_dir / "repair_history.md"),
        "refactor": _report_status(docs_dir / "refactor_report.md"),
        "runtime": _report_status(docs_dir / "runtime_report.md"),
        "security": _report_status(docs_dir / "security_report.md"),
        "reviewer": _report_status(docs_dir / "final_review.md"),
    }
    passed = (
        checks["qa"] == "PASS"
        and checks["production_qa"] == "PASS"
        and (checks["repair"] == "PASS" or checks["repair"] == "MISSING")
        and checks["refactor"] == "PASS"
        and checks["runtime"] == "PASS"
        and checks["security"] == "PASS"
        and checks["reviewer"] == "READY_FOR_MVP_HANDOFF"
    )
    if passed:
        return True, None
    return False, "Quality gates failed: " + ", ".join(
        f"{name}={status}" for name, status in checks.items()
    )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    slug = slug.strip("_")
    return slug or "flutter_app"
