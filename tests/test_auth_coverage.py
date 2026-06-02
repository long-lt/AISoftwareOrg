from __future__ import annotations

import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from dashboard.app import create_app
from dashboard.jwt_utils import encode_hs256


SECRET = "test-secret"
ADMIN_KEY = "test-admin-key"


def _make_client(tmp_path: Path) -> TestClient:
    os.environ["APP_ENV"] = "development"
    os.environ["DASHBOARD_SECRET"] = SECRET
    os.environ["ADMIN_API_KEY"] = ADMIN_KEY
    os.environ["DASHBOARD_DB_PATH"] = str(tmp_path / "dashboard.db")
    return TestClient(create_app())


def _token(role: str = "admin") -> str:
    now = int(time.time())
    return encode_hs256(
        {
            "team_id": "test",
            "role": role,
            "iat": now,
            "exp": now + 3600,
        },
        SECRET,
    )


def test_project_mutation_routes_require_auth():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))

        assert client.get("/api/projects/example").status_code == 401
        assert client.put("/api/projects/example", json={}).status_code == 401
        assert client.patch("/api/projects/example", json={}).status_code == 401
        assert client.delete("/api/projects/example").status_code == 401


def test_provider_mutation_routes_require_auth():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))

        assert client.get("/api/models").status_code == 401
        assert client.post("/api/providers", json={}).status_code == 401
        assert client.post("/api/providers/openrouter", json={}).status_code == 401
        assert client.post("/api/providers/openrouter/test").status_code == 401
        assert client.patch("/api/providers/openrouter", json={}).status_code == 401
        assert client.delete("/api/providers/openrouter").status_code == 401


def test_agent_and_settings_routes_require_auth():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))

        assert client.get("/api/agents/some-agent").status_code == 401
        assert client.post("/api/agents/some-agent/test").status_code == 401
        assert client.get("/api/settings").status_code == 401
        assert client.get("/api/system/settings").status_code == 401
        assert client.patch("/api/system/settings", json={}).status_code == 401
        assert client.post("/api/settings", json={}).status_code == 401
        assert client.post("/api/settings/wipe").status_code == 401


def test_admin_can_access_protected_system_status():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))
        response = client.get(
            "/api/system/status",
            headers={"Authorization": f"Bearer {_token('admin')}"},
        )
        assert response.status_code == 200


def test_factory_routes_require_auth():
    with TemporaryDirectory() as tmp:
        client = _make_client(Path(tmp))

        assert client.get("/api/factory/modules").status_code == 401
        assert client.get("/api/factory/workflows").status_code == 401
        assert client.post("/api/factory/pipeline/preview", json={}).status_code == 401

