"""
tests/test_dashboard_auth.py
Tests for Dashboard JWT Auth + Team Scoping.
"""

import asyncio
import os
import sys
import time
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
ADMIN_KEY = "test-admin-key"


def _create_app(tmp_path: Path):
    """Tạo dashboard app với test config."""
    from dashboard.app import create_app

    log_path = tmp_path / "agent_actions.jsonl"
    logger = AgentLogger(log_file=log_path)

    async def _seed():
        await logger.log_action("task-1", "DevAgent", "code_generated", {}, "success")
        await logger.log_action("task-1", "Pipeline", "workflow_completed", {}, "success")
    asyncio.run(_seed())

    memory_path = tmp_path / "memory.json"
    storage = MemoryStorage(memory_path)
    queue = ApprovalQueue(storage=storage)
    cp_store = CheckpointStore(storage=storage)

    alpha_storage = TenantAwareStorage("alpha", storage)
    beta_storage = TenantAwareStorage("beta", storage)
    alpha_queue = ApprovalQueue(storage=alpha_storage)
    beta_queue = ApprovalQueue(storage=beta_storage)
    alpha_queue.submit({"task_id": "alpha-task", "task_type": "api", "lessons": []})
    beta_queue.submit({"task_id": "beta-task", "task_type": "api", "lessons": []})

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


def _make_token(team_id: str, role: str = "admin") -> str:
    now = int(time.time())
    return encode_hs256({
        "team_id": team_id,
        "role": role,
        "iat": now,
        "exp": now + 3600,
    }, SECRET)


# ---------------------------------------------------------------------------
# Test 1: Protected endpoints require auth
# ---------------------------------------------------------------------------
def test_protected_endpoints_require_auth():
    print("TEST 1: Protected endpoints require auth")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        # These should return 401 without token
        for method, path in [
            ("GET", "/api/projects"),
            ("POST", "/api/projects"),
            ("GET", "/api/providers"),
            ("POST", "/api/providers/test/use"),
            ("GET", "/api/agents/config"),
        ]:
            resp = getattr(client, method.lower())(path)
            assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"
    print("  ✅ Protected endpoints return 401 without token")


# ---------------------------------------------------------------------------
# Test 2: Invalid token → 401
# ---------------------------------------------------------------------------
def test_invalid_token_returns_401():
    print("TEST 2: Invalid token → 401")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        resp = client.get(
            "/api/projects",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert resp.status_code == 401
    print("  ✅ Invalid token → 401")


# ---------------------------------------------------------------------------
# Test 3: Valid token grants access to protected endpoints
# ---------------------------------------------------------------------------
def test_valid_token_grants_access():
    print("TEST 3: Valid token grants access")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)
        token = _make_token("alpha")

        resp = client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        resp = client.get(
            "/api/agents/config",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
    print("  ✅ Valid token → 200 on protected endpoints")


# ---------------------------------------------------------------------------
# Test 4: Valid token scopes experiences by team
# ---------------------------------------------------------------------------
def test_valid_token_scopes_experiences():
    print("TEST 4: Valid token scopes experiences by team")
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
# Test 5: Different teams see different data
# ---------------------------------------------------------------------------
def test_different_teams_isolated():
    print("TEST 5: Different teams see different data")
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
    print("  ✅ Alpha and beta see completely separate data")


# ---------------------------------------------------------------------------
# Test 6: POST /api/auth/token returns valid JWT
# ---------------------------------------------------------------------------
def test_auth_token_endpoint():
    print("TEST 6: POST /api/auth/token → valid JWT")
    os.environ["ADMIN_API_KEY"] = ADMIN_KEY
    try:
        with TemporaryDirectory() as tmp:
            app = _create_app(Path(tmp))
            client = TestClient(app)

            resp = client.post(
                "/api/auth/token",
                json={"team_id": "gamma", "role": "admin"},
                headers={"X-Admin-Key": ADMIN_KEY},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["team_id"] == "gamma"
            assert "token" in data

            # Verify the token is valid and contains the right team_id
            payload = decode_hs256(data["token"], SECRET)
            assert payload["team_id"] == "gamma"
            assert payload["role"] == "admin"
            assert "exp" in payload
    finally:
        del os.environ["ADMIN_API_KEY"]
    print("  ✅ POST /api/auth/token returns valid JWT with correct claims")


# ---------------------------------------------------------------------------
# Test 7: Expired token is rejected
# ---------------------------------------------------------------------------
def test_expired_token_rejected():
    print("TEST 7: Expired token → 401")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        # Create an expired token
        now = int(time.time())
        expired_token = encode_hs256({
            "team_id": "alpha",
            "role": "admin",
            "iat": now - 7200,
            "exp": now - 3600,  # expired 1 hour ago
        }, SECRET)

        resp = client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
    print("  ✅ Expired token → 401")


# ---------------------------------------------------------------------------
# Test 8: Token without team_id is rejected
# ---------------------------------------------------------------------------
def test_token_without_team_id_rejected():
    print("TEST 8: Token without team_id → 401")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)

        now = int(time.time())
        bad_token = encode_hs256({
            "role": "admin",
            "iat": now,
            "exp": now + 3600,
            # no team_id
        }, SECRET)

        resp = client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code == 401
    print("  ✅ Token without team_id → 401")


# ---------------------------------------------------------------------------
# Test 9: GET /api/auth/me returns team_id
# ---------------------------------------------------------------------------
def test_auth_me_endpoint():
    print("TEST 9: GET /api/auth/me → team_id")
    with TemporaryDirectory() as tmp:
        app = _create_app(Path(tmp))
        client = TestClient(app)
        token = _make_token("delta")

        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["team_id"] == "delta"

        # Without token → 401
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401
    print("  ✅ GET /api/auth/me returns team_id")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("\n🔬 Dashboard JWT Auth Tests\n" + "=" * 50)

    tests = [
        test_protected_endpoints_require_auth,
        test_invalid_token_returns_401,
        test_valid_token_grants_access,
        test_valid_token_scopes_experiences,
        test_different_teams_isolated,
        test_auth_token_endpoint,
        test_expired_token_rejected,
        test_token_without_team_id_rejected,
        test_auth_me_endpoint,
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
