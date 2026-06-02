from pathlib import Path
import pytest

from factory_core import FactoryRequest
from factory_core.pipeline_runner import run_modular_pipeline


def test_run_modular_fullstack_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from dashboard.database import DB_PATH, _connect, _upsert_job
    monkeypatch.setattr("dashboard.database.DB_PATH", tmp_path / "jobs.sqlite3")

    app_dir = tmp_path / "pantry-saver"

    # Seed job to satisfy foreign key constraints
    _upsert_job(
        slug="pantry-saver",
        name="PantrySaver",
        description="Food expiry tracker and meal planner",
        status="queued",
        features=["auth", "inventory"],
        app_dir=app_dir,
    )

    request = FactoryRequest(
        name="PantrySaver",
        slug="pantry-saver",
        description="Food expiry tracker and meal planner",
        project_type="fullstack_saas",
        targets=["web", "backend"],
        stack={
            "frontend": "nextjs",
            "backend": "fastapi",
            "database": "supabase",
        },
        features=["auth", "inventory"],
    )

    result = run_modular_pipeline(request, app_dir)

    assert Path(result["export_path"]).exists()
    assert (app_dir / "docs" / "pipeline_plan.json").exists()
    assert (app_dir / "source" / "frontend" / "package.json").exists()
    assert (app_dir / "source" / "backend" / "main.py").exists()
    assert (app_dir / "source" / "infra" / "supabase" / "schema.sql").exists()
