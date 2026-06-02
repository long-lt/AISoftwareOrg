"""
tests/test_rbac.py
Kiểm tra hệ thống RBAC: Đảm bảo agent bị chặn khi không có quyền.
"""

import asyncio
from pathlib import Path
import sys

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from agents import DevAgent, AgentTask, DevOpsAgent
from system.rbac import (
    Permission, PermissionDenied,
    has_permission, normalize_role, permissions_for_role,
)


def test_normalize_role():
    """Test normalize_role với các input khác nhau."""
    assert normalize_role("dev") == "dev"
    assert normalize_role("Backend Developer") == "dev"
    assert normalize_role("devops engineer") == "devops"
    assert normalize_role("DevOps Engineer") == "devops"
    assert normalize_role(None) is None
    assert normalize_role("") is None
    assert normalize_role("   ") is None
    assert normalize_role("unknown_role") == "unknown_role"
    print("✅ test_normalize_role: OK")


def test_has_permission():
    """Test has_permission đúng theo ROLE_PERMISSIONS."""
    # dev có WRITE, không có CRITICAL
    assert has_permission("dev", Permission.WRITE)
    assert not has_permission("dev", Permission.CRITICAL)
    # reviewer chỉ có READ
    assert has_permission("reviewer", Permission.READ)
    assert not has_permission("reviewer", Permission.WRITE)
    assert not has_permission("reviewer", Permission.EXECUTE)
    # devops có CRITICAL
    assert has_permission("devops", Permission.CRITICAL)
    # alias hoạt động
    assert has_permission("Backend Developer", Permission.WRITE)
    assert has_permission("DevOps Engineer", Permission.CRITICAL)
    # None role → không permission nào
    assert not has_permission(None, Permission.READ)
    print("✅ test_has_permission: OK")


def test_permissions_for_role():
    """Test permissions_for_role trả về set đúng."""
    dev_perms = permissions_for_role("dev")
    assert Permission.READ in dev_perms
    assert Permission.WRITE in dev_perms
    assert Permission.EXECUTE not in dev_perms
    assert Permission.CRITICAL not in dev_perms

    devops_perms = permissions_for_role("DevOps Engineer")
    assert Permission.CRITICAL in devops_perms

    unknown_perms = permissions_for_role("no_such_role")
    assert unknown_perms == set()
    print("✅ test_permissions_for_role: OK")


async def test_permission_denied():
    print("\n🔬 Kiểm tra Permission Denial (decorator)...")
    dev = DevAgent()
    task = AgentTask(id="T-99", description="Test deploy")

    # Dev không có quyền CRITICAL, nên gọi deploy() phải fail
    try:
        await dev.deploy(task)
        print("❌ FAIL: DevAgent có thể gọi deploy() mà không bị chặn!")
    except PermissionDenied as e:
        print(f"✅ SUCCESS: Bị chặn đúng như kỳ vọng: {e}")


async def test_devops_can_deploy():
    print("\n🔬 Kiểm tra DevOpsAgent có quyền CRITICAL...")
    devops = DevOpsAgent()
    task = AgentTask(id="T-100", description="Deploy to production")

    try:
        result = await devops.deploy(task)
        assert result.success
        print(f"✅ SUCCESS: DevOpsAgent deploy thành công: {result.output}")
    except PermissionDenied as e:
        print(f"❌ FAIL: DevOpsAgent bị chặn deploy nhầm: {e}")


async def test_dev_can_write():
    print("\n🔬 Kiểm tra DevAgent có quyền WRITE (không bị chặn bởi decorator)...")
    # Chỉ kiểm tra DevAgent.run() tồn tại và được decorated, không gọi LLM thật
    assert hasattr(DevAgent.run, "__wrapped__"), "DevAgent.run() phải được decorate"
    assert has_permission("Backend Developer", Permission.WRITE)
    print("✅ SUCCESS: DevAgent có quyền write.")


if __name__ == "__main__":
    test_normalize_role()
    test_has_permission()
    test_permissions_for_role()
    asyncio.run(test_permission_denied())
    asyncio.run(test_devops_can_deploy())
    asyncio.run(test_dev_can_write())
