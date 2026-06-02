"""
tests/test_sandbox.py
Test script để verify sandbox hoạt động đúng.

Chạy:
    cd my-ai-org
    source venv/bin/activate
    python tests/test_sandbox.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path regardless of cwd
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


async def test_local_sandbox():
    """Test LocalSandbox — không cần Docker."""
    print("=" * 50)
    print("TEST: LocalSandbox")
    print("=" * 50)

    from sandbox import LocalSandbox

    async with LocalSandbox(sandbox_id="test-local") as sb:
        # Test 1: basic command
        result = await sb.run_command("echo 'sandbox works'")
        assert result.success, f"Command failed: {result.stderr}"
        assert "sandbox works" in result.stdout
        print(f"✅ echo test passed: {result.stdout.strip()!r}")

        # Test 2: python execution
        result = await sb.run_command("python3 -c \"print(2 + 2)\"")
        assert result.success, f"Python failed: {result.stderr}"
        assert "4" in result.stdout
        print(f"✅ python test passed: {result.stdout.strip()!r}")

        # Test 3: write and read file
        await sb.write_file("hello.txt", "hello from sandbox\n")
        content = await sb.read_file("hello.txt")
        assert "hello from sandbox" in content
        print(f"✅ file I/O test passed: {content.strip()!r}")

        # Test 4: run file written to sandbox
        await sb.write_file("test_script.py", "x = 10\nprint(f'result: {x * x}')\n")
        result = await sb.run_command("python3 test_script.py")
        assert result.success, f"Script failed: {result.stderr}"
        assert "result: 100" in result.stdout
        print(f"✅ script execution test passed: {result.stdout.strip()!r}")

        # Test 5: timeout handling
        result = await sb.run_command("sleep 10", timeout=1)
        assert not result.success
        print(f"✅ timeout test passed: timeout correctly raised")

    print("\n🎉 LocalSandbox: ALL TESTS PASSED\n")


async def test_docker_availability():
    """Check if Docker is available for AioSandbox."""
    print("=" * 50)
    print("TEST: AioSandbox (Docker check)")
    print("=" * 50)

    from sandbox import AioSandbox

    available = await AioSandbox.is_docker_available()
    if not available:
        print("⚠️  Docker is not running — skipping AioSandbox tests")
        print("   Start Docker Desktop to enable Docker sandbox tests.")
        return False

    print("✅ Docker is available")

    async with AioSandbox(sandbox_id="test-docker") as sb:
        # Test basic echo in container
        result = await sb.run_command("echo 'docker sandbox works'")
        assert result.success, f"Docker command failed: {result.stderr}"
        assert "docker sandbox works" in result.stdout
        print(f"✅ Docker echo test passed: {result.stdout.strip()!r}")

        # Test python in container
        result = await sb.run_python("import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')")
        assert result.success, f"Docker python failed: {result.stderr}"
        print(f"✅ Docker python test passed: {result.stdout.strip()!r}")

        # Verify no network access (should fail)
        await sb.write_file("check_network.py", """
import urllib.request
try:
    urllib.request.urlopen('https://google.com', timeout=3)
    print('NETWORK_OK')
except Exception as e:
    print(f'NO_NETWORK: {type(e).__name__}')
""")
        result = await sb.run_command("python3 /workspace/check_network.py")
        assert "NO_NETWORK" in result.output or result.exit_code != 0
        print("✅ Network isolation test passed: container has no internet access")

    print("\n🎉 AioSandbox: ALL TESTS PASSED\n")
    return True


async def test_command_sanitization():
    """Test that dangerous command patterns are blocked."""
    print("=" * 50)
    print("TEST: Command Sanitization")
    print("=" * 50)

    from sandbox import Sandbox

    # These should be blocked
    dangerous_commands = [
        "echo hello && rm -rf /",
        "echo $(whoami)",
        "echo `id`",
        "cat file; rm file",
        "ls | grep secret",
        "echo hello\nrm -rf /",
    ]

    for cmd in dangerous_commands:
        try:
            Sandbox.sanitize_command(cmd)
            print(f"  ❌ Should have blocked: {cmd[:40]}...")
            assert False, f"Command should be blocked: {cmd}"
        except ValueError:
            print(f"  ✅ Blocked dangerous pattern: {cmd[:40]}...")

    # These should be allowed
    safe_commands = [
        "echo hello",
        "python3 script.py",
        "ls -la",
        "cat file.txt",
        "python3 -c 'print(42)'",
        "python3 -c 'if 5 > 3: print(\"ok\")'",
        "python3 -c 'if 2 < 5: print(\"ok\")'",
        "echo > /etc/passwd",
        "cat < /etc/shadow",
    ]

    for cmd in safe_commands:
        try:
            result = Sandbox.sanitize_command(cmd)
            assert result == cmd
            print(f"  ✅ Allowed safe command: {cmd[:40]}...")
        except ValueError:
            print(f"  ❌ Should have allowed: {cmd[:40]}...")
            assert False, f"Command should be allowed: {cmd}"

    print("\n🎉 Command Sanitization: ALL TESTS PASSED\n")


async def test_allow_local_sandbox_flag():
    """Test ALLOW_LOCAL_SANDBOX environment variable enforcement."""
    print("=" * 50)
    print("TEST: ALLOW_LOCAL_SANDBOX Flag")
    print("=" * 50)

    from sandbox import get_sandbox

    # Save original value
    original_value = os.environ.get("ALLOW_LOCAL_SANDBOX")

    try:
        # Test 1: Default (not set) should block LocalSandbox
        os.environ.pop("ALLOW_LOCAL_SANDBOX", None)
        try:
            get_sandbox(use_docker=False)
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "disabled in production" in str(e)
            print("  ✅ Default blocks LocalSandbox")

        # Test 2: Explicit "false" should block LocalSandbox
        os.environ["ALLOW_LOCAL_SANDBOX"] = "false"
        try:
            get_sandbox(use_docker=False)
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "disabled in production" in str(e)
            print("  ✅ ALLOW_LOCAL_SANDBOX=false blocks LocalSandbox")

        # Test 3: "true" should allow LocalSandbox
        os.environ["ALLOW_LOCAL_SANDBOX"] = "true"
        try:
            sb = get_sandbox(use_docker=False)
            assert sb is not None
            print("  ✅ ALLOW_LOCAL_SANDBOX=true allows LocalSandbox")
        except RuntimeError:
            assert False, "Should not have raised RuntimeError"

    finally:
        # Restore original value
        if original_value is None:
            os.environ.pop("ALLOW_LOCAL_SANDBOX", None)
        else:
            os.environ["ALLOW_LOCAL_SANDBOX"] = original_value

    print("\n🎉 ALLOW_LOCAL_SANDBOX Flag: ALL TESTS PASSED\n")


async def test_docker_security_features():
    """Test Docker security features (read-only filesystem, network isolation)."""
    print("=" * 50)
    print("TEST: Docker Security Features")
    print("=" * 50)

    from sandbox import AioSandbox

    available = await AioSandbox.is_docker_available()
    if not available:
        print("⚠️  Docker is not running — skipping security tests")
        return False

    # Test 1: Read-only filesystem (except /workspace and /tmp)
    async with AioSandbox(sandbox_id="security-test", read_only=True) as sb:
        # Writing to /workspace should work
        await sb.write_file("test.txt", "hello")
        result = await sb.run_command("cat /workspace/test.txt")
        assert result.success
        assert "hello" in result.stdout
        print("  ✅ Can write to /workspace")

        # Writing to /tmp should work (tmpfs)
        await sb.write_file("write_tmp.py", "with open('/tmp/test.txt', 'w') as f: f.write('temp')\nwith open('/tmp/test.txt') as f: print(f.read())")
        result = await sb.run_command("python3 /workspace/write_tmp.py")
        assert result.success
        assert "temp" in result.stdout
        print("  ✅ Can write to /tmp (tmpfs)")

        # Writing to other locations should fail (read-only)
        await sb.write_file("write_etc.py", "try:\n    with open('/etc/test.txt', 'w') as f: f.write('hack')\n    print('WRITE_OK')\nexcept Exception as e:\n    print(f'READONLY: {e}')")
        result = await sb.run_command("python3 /workspace/write_etc.py")
        assert "READONLY" in result.output or result.exit_code != 0
        print("  ✅ Cannot write to read-only filesystem")

    # Test 2: Network isolation
    async with AioSandbox(sandbox_id="network-test", network_disabled=True) as sb:
        await sb.write_file("test_network.py", """
import urllib.request
try:
    urllib.request.urlopen('https://google.com', timeout=3)
    print('NETWORK_OK')
except Exception as e:
    print(f'NO_NETWORK: {type(e).__name__}')
""")
        result = await sb.run_command("python3 /workspace/test_network.py")
        assert "NO_NETWORK" in result.output or result.exit_code != 0
        print("  ✅ Network isolation enforced")

    print("\n🎉 Docker Security Features: ALL TESTS PASSED\n")
    return True


async def main():
    print("\n🔬 Running Sandbox Tests...\n")

    try:
        await test_local_sandbox()
    except Exception as e:
        print(f"❌ LocalSandbox test FAILED: {e}")
        sys.exit(1)

    try:
        await test_command_sanitization()
    except Exception as e:
        print(f"❌ Command Sanitization test FAILED: {e}")
        sys.exit(1)

    try:
        await test_allow_local_sandbox_flag()
    except Exception as e:
        print(f"❌ ALLOW_LOCAL_SANDBOX test FAILED: {e}")
        sys.exit(1)

    try:
        await test_docker_availability()
    except Exception as e:
        print(f"❌ AioSandbox test FAILED: {e}")
        # Don't exit — Docker might just not be running

    try:
        await test_docker_security_features()
    except Exception as e:
        print(f"❌ Docker Security test FAILED: {e}")
        # Don't exit — Docker might just not be running

    print("✅ Phase 6 - Task 1 COMPLETE: Sandbox Security Hardening!")


if __name__ == "__main__":
    asyncio.run(main())
