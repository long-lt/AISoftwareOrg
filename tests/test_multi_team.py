"""
Tests for Phase 8 Task 10 — Multi-Team Support.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from memory.storage import MemoryStorage, TenantAwareStorage, get_storage
from system.learning import ApprovalQueue, CheckpointStore
from dashboard.app import create_app
from dashboard.jwt_utils import encode_hs256
from fastapi.testclient import TestClient


def test_tenant_storage_isolates_memory(tmp_path):
    base = MemoryStorage(tmp_path / "memory.json")
    team_a = TenantAwareStorage("team-alpha", base)
    team_b = TenantAwareStorage("team-beta", base)

    team_a.add_experience({"task_id": "a-1", "content": "alpha memory"})
    team_b.add_experience({"task_id": "b-1", "content": "beta memory"})

    assert [item["task_id"] for item in team_a.load()["experiences"]] == ["a-1"]
    assert [item["task_id"] for item in team_b.load()["experiences"]] == ["b-1"]

    raw = base.load()
    assert sorted(raw["teams"].keys()) == ["team-alpha", "team-beta"]


def test_tenant_approval_and_checkpoint_are_isolated(tmp_path):
    base = MemoryStorage(tmp_path / "memory.json")
    queue_a = ApprovalQueue(storage=TenantAwareStorage("team-a", base))
    queue_b = ApprovalQueue(storage=TenantAwareStorage("team-b", base))
    checkpoint_a = CheckpointStore(storage=TenantAwareStorage("team-a", base))
    checkpoint_b = CheckpointStore(storage=TenantAwareStorage("team-b", base))

    exp_a = queue_a.submit({"task_id": "task-a", "task_type": "api", "lessons": []})
    exp_b = queue_b.submit({"task_id": "task-b", "task_type": "api", "lessons": []})
    cp_a = checkpoint_a.submit("task-a", "alpha reason")
    cp_b = checkpoint_b.submit("task-b", "beta reason")

    assert queue_a.get(exp_a["id"]) is not None
    assert queue_a.get(exp_b["id"]) is None
    assert queue_b.get(exp_b["id"]) is not None
    assert checkpoint_a.get(cp_a["id"]) is not None
    assert checkpoint_a.get(cp_b["id"]) is None
    assert checkpoint_b.get(cp_b["id"]) is not None


def test_get_storage_uses_team_id_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM_ID", "team-env")
    monkeypatch.setenv("MEMORY_FILE", str(tmp_path / "memory.json"))
    storage = get_storage("json")

    assert isinstance(storage, TenantAwareStorage)
    storage.add_experience({"task_id": "env-task"})
    assert storage.load()["experiences"][0]["task_id"] == "env-task"

    monkeypatch.delenv("TEAM_ID", raising=False)
    monkeypatch.delenv("MEMORY_FILE", raising=False)


def test_dashboard_unwraps_tenant_storage_for_token_scoping(tmp_path):
    """When queue is already team-scoped, token scoping must still work across teams."""
    base = MemoryStorage(tmp_path / "memory.json")
    queue = ApprovalQueue(storage=TenantAwareStorage("seed-team", base))
    cp_store = CheckpointStore(storage=TenantAwareStorage("seed-team", base))

    ApprovalQueue(storage=TenantAwareStorage("alpha", base)).submit(
        {"task_id": "alpha-task", "task_type": "api", "lessons": []}
    )
    ApprovalQueue(storage=TenantAwareStorage("beta", base)).submit(
        {"task_id": "beta-task", "task_type": "api", "lessons": []}
    )

    app = create_app(approval_queue=queue, checkpoint_store=cp_store, secret_key="test-secret")
    client = TestClient(app)

    alpha_token = encode_hs256({"team_id": "alpha"}, "test-secret")
    beta_token = encode_hs256({"team_id": "beta"}, "test-secret")

    alpha_resp = client.get("/api/experiences", headers={"Authorization": f"Bearer {alpha_token}"})
    beta_resp = client.get("/api/experiences", headers={"Authorization": f"Bearer {beta_token}"})

    alpha_ids = [e["task_id"] for e in alpha_resp.json()["pending"]]
    beta_ids = [e["task_id"] for e in beta_resp.json()["pending"]]
    assert alpha_ids == ["alpha-task"]
    assert beta_ids == ["beta-task"]


def main():
    print("Running multi-team tests")
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        test_tenant_storage_isolates_memory(Path(tmp))
    with TemporaryDirectory() as tmp:
        test_tenant_approval_and_checkpoint_are_isolated(Path(tmp))

    class _MonkeyPatch:
        def __init__(self):
            self._old = {}

        def setenv(self, key, value):
            self._old.setdefault(key, os.environ.get(key))
            os.environ[key] = value

        def delenv(self, key, raising=True):
            old = self._old.get(key)
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old

    with TemporaryDirectory() as tmp:
        test_get_storage_uses_team_id_env(Path(tmp), _MonkeyPatch())
    print("All multi-team tests passed")


if __name__ == "__main__":
    main()
