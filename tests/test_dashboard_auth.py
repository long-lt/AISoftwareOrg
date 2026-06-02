"""
tests/test_dashboard_auth.py
Tests for Dashboard JWT Auth + Team Scoping.

Chạy: cd my-ai-org && python tests/test_dashboard_auth.py
"""

import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi.testclient import TestClient
from core.logging import AgentLogger
from dashboard.jwt_utils import decode_hs256, encode_hs256
from system.learning import ApprovalQueue, CheckpointStore
from memory.storage import MemoryStorage, TenantAwareStorage

SECRET = "test-secret-key"


def _create_app(tmp_path: Path):
    """Tạo dashboard app với test config."""
    from dashboard.app import create_app

    log_path = tmp_path / "agent_actions.jsonl"
    logger = AgentLogger(log_file=log_path)

    # Seed a log entry so /api/tasks has data
    async def _seed():
        await logger.log_action("task-1", "DevAgent", "code_generated", {}, "success")
        await logger.log_action("task-1", "Pipeline", "workflow_completed", {}, "success")
    asyncio.run(_seed())

    memory_path = tmp_path / "memory.json"
    storage = MemoryStorage(memory_path)
    queue = ApprovalQueue(storage=storage)
    cp_store = CheckpointStore(storage=storage)

    # Submit experiences for two teams
    alpha_storage = TenantAwareStorage("alpha", storage)
    beta_storage = TenantAwareStorage("beta", storage)
    alpha_queue = ApprovalQueue(storage=alpha_storage)
    beta_queue = ApprovalQueue(storage=beta_storage)
    alpha_queue.submit({"task_id": "alpha-task", "task_type": "api", "lessons": []})
    beta_queue.submit({"task_id": "beta-task", "task_type": "api", "lessons": []})

    # Submit checkpoints for two teams
    alpha_cp = CheckpointStore(storage=alpha_storage)
    beta_cp = CheckpointStore(storage=beta_storage)
    alpha_cp.submit("alpha-task", "alpha checkpoint")
    beta_cp.submit("beta-task", "beta checkpoint")

    app = create_app(
        logger=logger,
        approval_queue=queue,
        checkpoint_store=cp_store,
        secret_key=SECRET,
    )
    return app


def _make_token(team_id: str) -> str:
    return encode_hs256({"team_id": team_id}, SECRET)


# ---------------------------------------------------------------------------
# Test 1: No token → backward compatible (returns data)
# ---------------------------------------------------------------------------
def test_no_token_returns_data():
    print("TEST 1: No token → backward compatible")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        resp = client.get("/api/experiences")
        assert resp.status_code == 200
        data = resp.json()
        assert "pending" in data
        assert "counts" in data

        resp = client.get("/api/checkpoints")
        assert resp.status_code == 200
        assert "pending" in resp.json()

        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1
    print("  ✅ No token → all endpoints return data")


# ---------------------------------------------------------------------------
# Test 2: Invalid token → error
# ---------------------------------------------------------------------------
def test_invalid_token_returns_error():
    print("TEST 2: Invalid token → error")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        # Invalid JWT
        resp = client.get(
            "/api/auth/token?team_id=x",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        # Auth token endpoint doesn't require auth, should still work
        assert resp.status_code == 200

        # But experiences with invalid token should still work (graceful fallback)
        resp = client.get(
            "/api/experiences",
            headers={"Authorization": "Bearer invalid-token"},
        )
        # Invalid token → team_id is None → falls back to default queue
        assert resp.status_code == 200
    print("  ✅ Invalid token → graceful fallback")


# ---------------------------------------------------------------------------
# Test 3: Valid token scopes experiences by team
# ---------------------------------------------------------------------------
def test_valid_token_scopes_experiences():
    print("TEST 3: Valid token scopes experiences by team")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        alpha_token = _make_token("alpha")
        resp = client.get(
            "/api/experiences",
            headers={"Authorization": f"Bearer {alpha_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        pending_ids = [e["task_id"] for e in data["pending"]]
        assert "alpha-task" in pending_ids
        assert "beta-task" not in pending_ids
    print("  ✅ Token with team_id=alpha → only alpha experiences")


# ---------------------------------------------------------------------------
# Test 4: Different teams see different data
# ---------------------------------------------------------------------------
def test_different_teams_isolated():
    print("TEST 4: Different teams see different data")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        alpha_token = _make_token("alpha")
        beta_token = _make_token("beta")

        alpha_resp = client.get(
            "/api/experiences",
            headers={"Authorization": f"Bearer {alpha_token}"},
        )
        beta_resp = client.get(
            "/api/experiences",
            headers={"Authorization": f"Bearer {beta_token}"},
        )

        alpha_ids = [e["task_id"] for e in alpha_resp.json()["pending"]]
        beta_ids = [e["task_id"] for e in beta_resp.json()["pending"]]

        assert "alpha-task" in alpha_ids
        assert "alpha-task" not in beta_ids
        assert "beta-task" in beta_ids
        assert "beta-task" not in alpha_ids

        # Checkpoints too
        alpha_cp = client.get(
            "/api/checkpoints",
            headers={"Authorization": f"Bearer {alpha_token}"},
        )
        beta_cp = client.get(
            "/api/checkpoints",
            headers={"Authorization": f"Bearer {beta_token}"},
        )

        alpha_cp_ids = [cp["task_id"] for cp in alpha_cp.json()["pending"]]
        beta_cp_ids = [cp["task_id"] for cp in beta_cp.json()["pending"]]

        assert "alpha-task" in alpha_cp_ids
        assert "beta-task" not in alpha_cp_ids
        assert "beta-task" in beta_cp_ids
        assert "alpha-task" not in beta_cp_ids
    print("  ✅ Alpha and beta see completely separate data")


# ---------------------------------------------------------------------------
# Test 5: /api/auth/token returns valid JWT
# ---------------------------------------------------------------------------
def test_auth_token_endpoint():
    print("TEST 5: /api/auth/token → valid JWT")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        resp = client.get("/api/auth/token?team_id=gamma")
        assert resp.status_code == 200
        data = resp.json()
        assert data["team_id"] == "gamma"
        assert "token" in data

        # Verify the token is valid and contains the right team_id
        payload = decode_hs256(data["token"], SECRET)
        assert payload["team_id"] == "gamma"
    print("  ✅ /api/auth/token returns valid JWT with correct team_id")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\n🔬 Dashboard JWT Auth Tests\n" + "=" * 50)

    tests = [
        test_no_token_returns_data,
        test_invalid_token_returns_error,
        test_valid_token_scopes_experiences,
        test_different_teams_isolated,
        test_auth_token_endpoint,
    ]

    results = []

    def run_test(fn):
        try:
            fn()
            results.append((fn.__name__, True))
            print()
        except Exception as e:
            results.append((fn.__name__, False))
            print(f"  ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            print()

    for t in tests:
        run_test(t)

    print("=" * 50)
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print(f"Results: {passed}/{len(results)} passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED — Dashboard JWT auth ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        for name, ok in results:
            if not ok:
                print(f"   - {name}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
