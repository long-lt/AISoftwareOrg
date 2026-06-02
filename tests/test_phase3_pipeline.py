from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _isolated_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from dashboard import database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "jobs.sqlite3")
    monkeypatch.setattr(database, "GENERATED_APPS_DIR", tmp_path / "generated_apps")


def _seed_job(slug: str, app_dir: Path) -> None:
    from dashboard.database import _upsert_job

    _upsert_job(
        slug=slug,
        name="Phase 3 Job",
        description="phase 3 pipeline job",
        status="queued",
        features=["dashboard"],
        app_dir=app_dir,
        cancel_requested=False,
    )


def test_phase_registry_defines_exactly_12_standardized_phases() -> None:
    from workflows.phase_registry import PIPELINE_PHASES, get_phase_contract

    assert len(PIPELINE_PHASES) == 12
    ids = [phase.id for phase in PIPELINE_PHASES]
    assert ids == [
        "01_create_brief",
        "02_business_analysis",
        "03_backend_design",
        "04_architecture_design",
        "05_uiux_design",
        "06_flutter_dev",
        "07_static_qa",
        "08_refactor_repair",
        "09_runtime_test",
        "10_security_audit",
        "11_release_review",
        "12_export_package",
    ]
    assert get_phase_contract("07_static_qa").agent == "qa_agent"
    assert "docs/test_report.md" in get_phase_contract("07_static_qa").required_outputs


def test_validators_detect_missing_outputs_and_invalid_json(tmp_path: Path) -> None:
    from workflows.validators import validate_json_file, validate_required_files

    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "docs").mkdir()
    (app_dir / "docs" / "input.json").write_text("{bad json", encoding="utf-8")

    result = validate_required_files(
        app_dir,
        ["docs/input.json", "docs/app_brief.md"],
    )
    assert result.passed is False
    assert "docs/app_brief.md" in result.errors[0]

    json_result = validate_json_file(app_dir / "docs" / "input.json")
    assert json_result.passed is False
    assert "Invalid JSON" in json_result.errors[0]


def test_phase_service_records_metadata_logs_and_job_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)

    from dashboard.database import GENERATED_APPS_DIR, get_job, list_job_logs, list_job_phases
    from dashboard.services.phase_service import fail_phase, pass_phase, start_phase

    _seed_job("phase3-service", GENERATED_APPS_DIR / "phase3-service")
    start_phase("phase3-service", "01_create_brief")
    pass_phase(
        "phase3-service",
        "01_create_brief",
        output_files=["docs/input.json", "docs/app_brief.md"],
    )
    start_phase("phase3-service", "02_business_analysis")
    fail_phase("phase3-service", "02_business_analysis", "missing product_spec.json")

    phases = {phase["phase"]: phase for phase in list_job_phases("phase3-service")}
    assert phases["01_create_brief"]["agent"] == "brief_agent"
    assert phases["01_create_brief"]["status"] == "passed"
    assert json.loads(phases["01_create_brief"]["output_files_json"]) == [
        "docs/input.json",
        "docs/app_brief.md",
    ]
    assert phases["02_business_analysis"]["status"] == "failed"
    assert phases["02_business_analysis"]["error"] == "missing product_spec.json"

    job = get_job("phase3-service")
    assert job is not None
    assert job["current_phase"] == "02_business_analysis"
    assert job["progress"] == 8

    logs = list_job_logs("phase3-service", phase="02_business_analysis")
    assert any(log["level"] == "error" and "missing product_spec" in log["message"] for log in logs)


def test_job_logs_endpoint_filters_by_phase_and_level(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "development")

    from dashboard.app import create_app
    from dashboard.database import GENERATED_APPS_DIR
    from dashboard.services.job_log_service import write_job_log

    _seed_job("api-logs", GENERATED_APPS_DIR / "api-logs")
    write_job_log("api-logs", "07_static_qa", "info", "QA started")
    write_job_log("api-logs", "07_static_qa", "error", "flutter analyze failed")
    write_job_log("api-logs", "08_refactor_repair", "info", "repair started")

    import time
    from dashboard.jwt_utils import encode_hs256
    now = int(time.time())
    token = encode_hs256({"team_id": "test", "role": "admin", "iat": now, "exp": now + 3600}, "phase3-secret")
    headers = {"Authorization": f"Bearer {token}"}

    client = TestClient(create_app(secret_key="phase3-secret"))
    response = client.get("/api/jobs/api-logs/logs?phase=07_static_qa&level=error", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "job_slug": "api-logs",
            "phase": "07_static_qa",
            "level": "error",
            "message": "flutter analyze failed",
            "created_at": response.json()[0]["created_at"],
        }
    ]


def test_export_package_excludes_secrets_and_logs(tmp_path: Path) -> None:
    from agents.flutter_factory.orchestrator import export_source_archive

    app_dir = tmp_path / "generated" / "safe-export"
    source_dir = app_dir / "source"
    docs_dir = app_dir / "docs"
    backend_dir = app_dir / "backend"
    source_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    backend_dir.mkdir(parents=True)

    (source_dir / "pubspec.yaml").write_text("name: safe_export\n", encoding="utf-8")
    (source_dir / ".env").write_text("SECRET=do-not-export\n", encoding="utf-8")
    (source_dir / "debug.log").write_text("debug", encoding="utf-8")
    (backend_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (docs_dir / "final_review.md").write_text("Status: READY_FOR_MVP_HANDOFF\n", encoding="utf-8")
    (app_dir / "README.md").write_text("# Safe Export\n", encoding="utf-8")
    (app_dir / ".env.example").write_text("APP_ENV=local\n", encoding="utf-8")

    archive_path, report_path = export_source_archive(
        {"slug": "safe-export", "name": "Safe Export"},
        app_dir,
    )

    assert archive_path.exists()
    assert report_path.exists()
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "source/pubspec.yaml" in names
    assert "backend/main.py" in names
    assert "README.md" in names
    assert ".env.example" in names
    assert "source/.env" not in names
    assert "source/debug.log" not in names
