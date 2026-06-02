from __future__ import annotations

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
        name="Phase 2 Job",
        description="exercise job phase persistence",
        status="queued",
        features=["dashboard"],
        app_dir=app_dir,
        cancel_requested=False,
    )


def test_job_statuses_are_validated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)

    from dashboard.database import GENERATED_APPS_DIR, _upsert_job

    with pytest.raises(ValueError, match="Invalid job status"):
        _upsert_job(
            slug="bad-status",
            name="Bad Status",
            description="invalid",
            status="done",
            features=[],
            app_dir=GENERATED_APPS_DIR / "bad-status",
        )


def test_job_phase_table_initializes_all_phases_without_duplicates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)

    from dashboard.database import (
        PIPELINE_PHASES,
        GENERATED_APPS_DIR,
        initialize_job_phases,
        list_job_phases,
    )

    _seed_job("phase-init", GENERATED_APPS_DIR / "phase-init")
    initialize_job_phases("phase-init")
    initialize_job_phases("phase-init")

    phases = list_job_phases("phase-init")
    assert [phase["phase"] for phase in phases] == list(PIPELINE_PHASES)
    assert [phase["status"] for phase in phases] == ["pending"] * len(PIPELINE_PHASES)


def test_start_and_finish_phase_persist_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)

    from dashboard.database import (
        GENERATED_APPS_DIR,
        finish_phase,
        list_job_phases,
        phase_status,
        start_phase,
    )

    _seed_job("phase-progress", GENERATED_APPS_DIR / "phase-progress")
    start_phase("phase-progress", "ba")
    running = {phase["phase"]: phase for phase in list_job_phases("phase-progress")}
    assert running["ba"]["status"] == "running"
    assert running["ba"]["started_at"] is not None
    assert running["ba"]["finished_at"] is None

    finish_phase(
        "phase-progress",
        "ba",
        "passed",
        output_path="/tmp/phase-progress/docs/requirements.md",
    )

    finished = {phase["phase"]: phase for phase in list_job_phases("phase-progress")}
    assert finished["ba"]["status"] == "passed"
    assert finished["ba"]["finished_at"] is not None
    assert finished["ba"]["output_path"] == "/tmp/phase-progress/docs/requirements.md"
    assert phase_status("phase-progress")["ba"] == "passed"


def test_job_phases_endpoint_reads_database_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "development")

    from dashboard.app import create_app
    from dashboard.database import GENERATED_APPS_DIR, finish_phase, start_phase

    _seed_job("api-progress", GENERATED_APPS_DIR / "api-progress")
    start_phase("api-progress", "ba")
    finish_phase("api-progress", "ba", "passed")
    start_phase("api-progress", "dev")

    import time
    from dashboard.jwt_utils import encode_hs256
    now = int(time.time())
    token = encode_hs256({"team_id": "test", "role": "admin", "iat": now, "exp": now + 3600}, "phase2-secret")
    headers = {"Authorization": f"Bearer {token}"}

    client = TestClient(create_app(secret_key="phase2-secret"))
    response = client.get("/api/jobs/api-progress/phase-status", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ba"] == "passed"
    assert body["dev"] == "running"
    assert body["export"] == "pending"


def test_orchestrator_records_phase_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _isolated_database(monkeypatch, tmp_path)

    import agents.flutter_factory.orchestrator as orchestrator
    from dashboard.database import GENERATED_APPS_DIR, phase_status

    app_dir = GENERATED_APPS_DIR / "orchestrator-progress"
    _seed_job("orchestrator-progress", app_dir)

    def write_doc(_app_input, docs_dir: Path, filename: str) -> list[Path]:
        docs_dir.mkdir(parents=True, exist_ok=True)
        path = docs_dir / filename
        path.write_text("ok", encoding="utf-8")
        return [path]

    def write_status_doc(_app_input, docs_dir: Path, filename: str, status: str = "PASS") -> list[Path]:
        docs_dir.mkdir(parents=True, exist_ok=True)
        path = docs_dir / filename
        path.write_text(f"- Status: {status}\n", encoding="utf-8")
        return [path]

    monkeypatch.setattr(
        orchestrator,
        "write_ba_documents",
        lambda app_input, docs_dir: write_doc(app_input, docs_dir, "requirements.md"),
    )
    monkeypatch.setattr(
        orchestrator,
        "write_backend_source",
        lambda app_input, docs_dir, backend_dir: [],
    )
    monkeypatch.setattr(
        orchestrator,
        "write_architect_documents",
        lambda app_input, docs_dir: write_doc(app_input, docs_dir, "architecture.md"),
    )
    monkeypatch.setattr(
        orchestrator,
        "write_uiux_documents",
        lambda app_input, docs_dir: write_doc(app_input, docs_dir, "design.md"),
    )
    monkeypatch.setattr(
        orchestrator,
        "write_flutter_source",
        lambda app_input, docs_dir, source_dir: write_doc(app_input, docs_dir, "main.dart"),
    )
    monkeypatch.setattr(
        orchestrator,
        "_run_repair_loop",
        lambda app_input, docs_dir, source_dir, max_attempts: write_status_doc(
            app_input, docs_dir, "repair_history.md"
        ),
    )
    monkeypatch.setattr(
        orchestrator,
        "write_review_documents",
        lambda app_input, docs_dir, source_dir: write_doc(app_input, docs_dir, "final_review.md"),
    )
    monkeypatch.setattr(
        orchestrator,
        "run_qa_checks",
        lambda app_input, docs_dir, source_dir, include_release_build=False: write_doc(app_input, docs_dir, "test_report.md"),
    )
    monkeypatch.setattr(
        orchestrator,
        "run_runtime_verification",
        lambda app_input, docs_dir, source_dir: write_doc(app_input, docs_dir, "runtime_report.md"),
    )
    monkeypatch.setattr(
        orchestrator,
        "write_security_documents",
        lambda app_input, docs_dir, source_dir, backend_dir: write_doc(app_input, docs_dir, "security_report.md"),
    )
    monkeypatch.setattr(orchestrator, "_pipeline_gate_error", lambda docs_dir: None)
    monkeypatch.setattr(
        orchestrator,
        "export_source_archive",
        lambda app_input, app_dir: write_doc(app_input, app_dir / "exports", "source.zip"),
    )

    orchestrator.run_full_pipeline(
        {
            "slug": "orchestrator-progress",
            "name": "Orchestrator Progress",
            "description": "test",
            "features": [],
        },
        app_dir,
    )

    statuses = phase_status("orchestrator-progress")
    assert statuses["ba"] == "passed"
    assert statuses["architect"] == "passed"
    assert statuses["uiux"] == "passed"
    assert statuses["dev"] == "passed"
    assert statuses["repair"] == "passed"
    assert statuses["reviewer"] == "passed"
    assert statuses["export"] == "passed"


def test_worker_module_exposes_main() -> None:
    from dashboard import worker

    assert worker.RQ_QUEUE_NAME == "flutter_ai_factory"
    assert callable(worker.main)
