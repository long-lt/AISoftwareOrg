from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SECRET = "test-dashboard-secret"


def _isolated_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from dashboard import database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "jobs.sqlite3")
    monkeypatch.setattr(database, "GENERATED_APPS_DIR", tmp_path / "generated_apps")


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    _isolated_database(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "development")

    from dashboard.app import create_app

    return TestClient(create_app(secret_key=SECRET))


def test_auth_token_requires_admin_key_and_includes_role_claims(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "admin-secret")
    client = _client(monkeypatch, tmp_path)

    missing_key = client.post(
        "/api/auth/token",
        json={"team_id": "default", "role": "admin"},
    )
    assert missing_key.status_code == 401

    response = client.post(
        "/api/auth/token",
        headers={"X-Admin-Key": "admin-secret"},
        json={"team_id": "default", "role": "admin"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["team_id"] == "default"
    assert body["role"] == "admin"
    assert body["expires_in"] == 86400

    from dashboard.jwt_utils import decode_hs256

    payload = decode_hs256(body["token"], SECRET)
    assert payload["team_id"] == "default"
    assert payload["role"] == "admin"
    assert isinstance(payload["iat"], int)
    assert isinstance(payload["exp"], int)
    assert payload["exp"] - payload["iat"] == 86400


@pytest.mark.parametrize("secret_value", [None, "", "dev-secret-change-me"])
def test_production_rejects_missing_empty_or_default_dashboard_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    secret_value: str | None,
) -> None:
    _isolated_database(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "development")

    from dashboard.app import create_app

    monkeypatch.setenv("APP_ENV", "production")
    if secret_value is None:
        monkeypatch.delenv("DASHBOARD_SECRET", raising=False)
    else:
        monkeypatch.setenv("DASHBOARD_SECRET", secret_value)

    with pytest.raises(RuntimeError, match="DASHBOARD_SECRET"):
        create_app()


def test_max_repair_attempts_comes_from_app_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_REPAIR_ATTEMPTS", "7")

    from agents.flutter_factory.orchestrator import _configured_max_repair_attempts

    assert _configured_max_repair_attempts() == 7


def test_cancel_endpoint_marks_cancel_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)

    from dashboard.database import GENERATED_APPS_DIR, _upsert_job, get_job, is_cancel_requested

    _upsert_job(
        slug="cancel-me",
        name="Cancel Me",
        description="running job",
        status="running",
        features=["dashboard"],
        app_dir=GENERATED_APPS_DIR / "cancel-me",
    )

    response = client.post("/api/jobs/cancel-me/cancel")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "slug": "cancel-me",
        "status": "cancel_requested",
        "cancel_requested": True,
    }
    job = get_job("cancel-me")
    assert job is not None
    assert job["status"] == "cancel_requested"
    assert job["cancel_requested"] is True
    assert is_cancel_requested("cancel-me") is True


def test_pipeline_cancellation_check_raises_job_cancelled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)

    from agents.flutter_factory.orchestrator import (
        JobCancelledError,
        _check_cancellation,
    )
    from dashboard.database import GENERATED_APPS_DIR, _upsert_job, request_job_cancellation

    _upsert_job(
        slug="cancelled-pipeline",
        name="Cancelled Pipeline",
        description="running job",
        status="running",
        features=["dashboard"],
        app_dir=GENERATED_APPS_DIR / "cancelled-pipeline",
    )
    assert request_job_cancellation("cancelled-pipeline") is True

    with pytest.raises(JobCancelledError):
        _check_cancellation("cancelled-pipeline")


def test_queue_manager_marks_cancelled_jobs_cancelled_not_failed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)

    from agents.flutter_factory.orchestrator import JobCancelledError
    from dashboard import queue_manager
    from dashboard.database import get_job

    def cancelled_pipeline(_payload, _app_dir):
        raise JobCancelledError("Job was cancelled")

    monkeypatch.setattr(queue_manager, "run_flutter_mvp_pipeline", cancelled_pipeline)

    payload = {
        "name": "Cancelled Queue Job",
        "description": "cancel while running",
        "platform": "android,ios",
        "style": "modern",
        "backend": "none",
        "features": ["dashboard"],
        "slug": "cancelled-queue-job",
    }

    queue_manager._run_flutter_job(payload, "cancelled-queue-job")

    job = get_job("cancelled-queue-job")
    assert job is not None
    assert job["status"] == "cancelled"
    assert "Job was cancelled" in (job["error"] or "")


def test_write_retry_retries_locked_sqlite_operations() -> None:
    from dashboard.database import _with_write_retry

    attempts = 0

    def locked_once() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    assert _with_write_retry(locked_once, sleep_seconds=0) == "ok"
    assert attempts == 2
