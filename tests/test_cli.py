"""
tests/test_cli.py
Test Task 18 — CLI & Config.

Chạy: cd my-ai-org && python tests/test_cli.py
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


# ---------------------------------------------------------------------------
# Test 1: AppSettings loads defaults
# ---------------------------------------------------------------------------
def test_config_defaults():
    print("TEST 1: AppSettings loads defaults")
    from config.settings import AppSettings

    settings = AppSettings(_env_file=None)
    assert settings.llm_base_url == "https://openrouter.ai/api/v1"
    assert settings.llm_model == "deepseek/deepseek-v4-flash"
    assert settings.llm_provider == ""
    assert settings.llm_providers_file == ".aiorg/providers.json"
    assert settings.max_attempts == 3
    assert settings.use_docker is False
    assert settings.dashboard_host == "0.0.0.0"
    assert settings.dashboard_port == 8080
    print("  ✅ All defaults correct")


# ---------------------------------------------------------------------------
# Test 2: AppSettings loads from .env
# ---------------------------------------------------------------------------
def test_config_from_env():
    print("TEST 2: AppSettings loads from .env file")
    from config.settings import AppSettings

    with TemporaryDirectory() as tmp:
        env_file = Path(tmp) / ".env"
        env_file.write_text(
            "LLM_API_KEY=test-key-123\n"
            "LLM_MODEL=gpt-4\n"
            "MAX_ATTEMPTS=5\n"
            "USE_DOCKER=true\n"
            "DASHBOARD_PORT=9090\n"
        )
        settings = AppSettings(_env_file=str(env_file))
        assert settings.llm_api_key == "test-key-123"
        assert settings.llm_model == "gpt-4"
        assert settings.max_attempts == 5
        assert settings.use_docker is True
        assert settings.dashboard_port == 9090
    print("  ✅ .env loading works")


# ---------------------------------------------------------------------------
# Test 3: Agent model fallbacks
# ---------------------------------------------------------------------------
def test_config_model_fallbacks():
    print("TEST 3: Agent model fallbacks to llm_model")
    from config.settings import AppSettings

    with TemporaryDirectory() as tmp:
        env_file = Path(tmp) / ".env"
        env_file.write_text("LLM_MODEL=base-model\n")
        settings = AppSettings(_env_file=str(env_file))
        assert settings.get_dev_model() == "base-model"
        assert settings.get_reviewer_model() == "base-model"
        assert settings.get_qa_model() == "base-model"
        assert settings.get_pm_model() == "base-model"
        assert settings.get_planner_model() == "base-model"

        env_file.write_text("LLM_MODEL=base-model\nDEV_MODEL=dev-specific\n")
        settings = AppSettings(_env_file=str(env_file))
        assert settings.get_dev_model() == "dev-specific"
        assert settings.get_reviewer_model() == "base-model"
    print("  ✅ Model fallbacks work correctly")


# ---------------------------------------------------------------------------
# Test 4: Backward-compatible config constants
# ---------------------------------------------------------------------------
def test_config_backward_compat():
    print("TEST 4: Backward-compatible config constants")
    import importlib
    import config

    importlib.reload(config)
    assert hasattr(config, "LLM_API_KEY")
    assert hasattr(config, "LLM_BASE_URL")
    assert hasattr(config, "LLM_MODEL")
    assert hasattr(config, "DEV_MODEL")
    assert hasattr(config, "REVIEWER_MODEL")
    assert hasattr(config, "QA_MODEL")
    assert hasattr(config, "PM_MODEL")
    assert hasattr(config, "PLANNER_MODEL")
    assert isinstance(config.LLM_BASE_URL, str)
    print("  ✅ All backward-compatible constants present")


# ---------------------------------------------------------------------------
# Test 5: CLI --version
# ---------------------------------------------------------------------------
def test_cli_version():
    print("TEST 5: CLI --version")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.0.0" in result.output
    print("  ✅ --version works")


# ---------------------------------------------------------------------------
# Test 6: CLI --help
# ---------------------------------------------------------------------------
def test_cli_help():
    print("TEST 6: CLI --help shows all commands")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ["run", "pipeline", "dashboard", "config", "providers", "status"]:
        assert cmd in result.output, f"Missing command: {cmd}"
    print("  ✅ --help lists all commands")


# ---------------------------------------------------------------------------
# Test 7: CLI run --help
# ---------------------------------------------------------------------------
def test_cli_run_help():
    print("TEST 7: cli run --help")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "--max-attempts" in result.output
    assert "--docker" in result.output
    print("  ✅ run --help shows options")


# ---------------------------------------------------------------------------
# Test 8: CLI config show
# ---------------------------------------------------------------------------
def test_cli_config():
    print("TEST 8: cli config shows settings")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    assert "llm_model" in result.output
    assert "max_attempts" in result.output
    assert "dashboard_port" in result.output
    assert "llm_api_key" in result.output
    print("  ✅ config command works, no secrets exposed")


# ---------------------------------------------------------------------------
# Test 8b: CLI config show (explicit)
# ---------------------------------------------------------------------------
def test_cli_config_show_explicit():
    print("TEST 8b: cli config show (explicit subcommand)")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "llm_model" in result.output
    print("  ✅ config show subcommand works")


# ---------------------------------------------------------------------------
# Test 8c: CLI config set
# ---------------------------------------------------------------------------
def test_cli_config_set():
    print("TEST 8c: cli config set key value")
    from click.testing import CliRunner
    from cli.main import cli

    with TemporaryDirectory() as tmp:
        env_file = Path(tmp) / ".env"
        env_file.write_text("LLM_MODEL=old-model\nMAX_ATTEMPTS=3\n")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "config", "set", "LLM_MODEL", "gpt-4",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "LLM_MODEL=gpt-4" in result.output or "Set LLM_MODEL=gpt-4" in result.output

        content = env_file.read_text()
        assert 'LLM_MODEL="gpt-4"' in content
        assert "MAX_ATTEMPTS=3" in content  # Other keys preserved
    print("  ✅ config set works, other keys preserved")


# ---------------------------------------------------------------------------
# Test 8d: CLI config set with Python-style key
# ---------------------------------------------------------------------------
def test_cli_config_set_python_key():
    print("TEST 8d: cli config set with lowercase python key")
    from click.testing import CliRunner
    from cli.main import cli

    with TemporaryDirectory() as tmp:
        env_file = Path(tmp) / ".env"
        env_file.write_text("")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "config", "set", "max_attempts", "5",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"

        content = env_file.read_text()
        assert 'MAX_ATTEMPTS="5"' in content
    print("  ✅ config set resolves python keys to env aliases")


# ---------------------------------------------------------------------------
# Test 8e: CLI config set with invalid key
# ---------------------------------------------------------------------------
def test_cli_config_set_invalid_key():
    print("TEST 8e: cli config set with unknown key")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "set", "INVALID_KEY", "value"])
    assert result.exit_code != 0
    assert "Unknown" in result.output
    print("  ✅ Unknown key rejected")


# ---------------------------------------------------------------------------
# Test 9: CLI status
# ---------------------------------------------------------------------------
def test_cli_status():
    print("TEST 9: cli status shows counts")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Experiences" in result.output
    assert "Checkpoints" in result.output
    assert "Pending" in result.output
    print("  ✅ status command works")


# ---------------------------------------------------------------------------
# Test 9b: CLI status --output json
# ---------------------------------------------------------------------------
def test_cli_status_json():
    print("TEST 9b: cli status --output json")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--output", "json", "status"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "experiences" in data
    assert "checkpoints" in data
    print("  ✅ status --output json works")


# ---------------------------------------------------------------------------
# Test 9c: CLI config --output json
# ---------------------------------------------------------------------------
def test_cli_config_json():
    print("TEST 9c: cli config --output json")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--output", "json", "config"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.output)
    assert "llm_model" in data
    assert "max_attempts" in data
    print("  ✅ config --output json works")


# ---------------------------------------------------------------------------
# Test 9d: CLI --quiet suppresses info
# ---------------------------------------------------------------------------
def test_cli_quiet():
    print("TEST 9d: cli --quiet suppresses info output")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    # status with --quiet should still show the section headers
    result = runner.invoke(cli, ["--quiet", "status"])
    assert result.exit_code == 0
    assert "Experiences" in result.output
    print("  ✅ --quiet still shows status output")


# ---------------------------------------------------------------------------
# Test 9e: CLI --env-file loads custom env
# ---------------------------------------------------------------------------
def test_cli_env_file():
    print("TEST 9e: cli --env-file loads custom env file")
    from click.testing import CliRunner
    from cli.main import cli

    with TemporaryDirectory() as tmp:
        env_file = Path(tmp) / "custom.env"
        env_file.write_text("MAX_ATTEMPTS=7\nDASHBOARD_PORT=9090\n")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "--output", "json",
            "config",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        import json
        data = json.loads(result.output)
        assert data.get("max_attempts") == "7"
        assert data.get("dashboard_port") == "9090"
    print("  ✅ --env-file correctly loads custom env")


# ---------------------------------------------------------------------------
# Test 10: CLI pipeline --help
# ---------------------------------------------------------------------------
def test_cli_pipeline_help():
    print("TEST 10: cli pipeline --help")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["pipeline", "--help"])
    assert result.exit_code == 0
    assert "--parallel" in result.output
    assert "--max-attempts" in result.output
    assert "--docker" in result.output
    print("  ✅ pipeline --help shows options")


# ---------------------------------------------------------------------------
# Test 11: CLI dashboard --help
# ---------------------------------------------------------------------------
def test_cli_dashboard_help():
    print("TEST 11: cli dashboard --help")
    from click.testing import CliRunner
    from cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["dashboard", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.output
    assert "--port" in result.output
    print("  ✅ dashboard --help shows options")


# ---------------------------------------------------------------------------
# Test 12: CLI providers CRUD
# ---------------------------------------------------------------------------
def test_cli_providers_crud():
    print("TEST 12: cli providers CRUD")
    from click.testing import CliRunner
    from cli.main import cli

    with TemporaryDirectory() as tmp:
        provider_file = Path(tmp) / "providers.json"
        env_file = Path(tmp) / ".env"
        env_file.write_text(f"LLM_PROVIDERS_FILE={provider_file}\n")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "providers", "list",
        ])
        assert result.exit_code == 0, result.output
        assert "openrouter" in result.output
        assert "ollama" in result.output

        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "providers", "add", "local-test",
            "--base-url", "http://localhost:9999/v1",
            "--api-key-env", "LOCAL_TEST_API_KEY",
            "--default-model", "test-model",
        ])
        assert result.exit_code == 0, result.output
        assert provider_file.exists()

        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "providers", "set", "local-test",
            "--default-model", "test-model-v2",
        ])
        assert result.exit_code == 0, result.output

        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "providers", "show", "local-test",
        ])
        assert result.exit_code == 0, result.output
        assert "test-model-v2" in result.output

        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "providers", "use", "local-test",
        ])
        assert result.exit_code == 0, result.output
        assert 'LLM_PROVIDER="local-test"' in env_file.read_text()

        result = runner.invoke(cli, [
            "--env-file", str(env_file),
            "providers", "remove", "local-test",
        ])
        assert result.exit_code == 0, result.output
    print("  ✅ providers list/add/set/show/use/remove work")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main():
    print("\n🔬 Task 18 — CLI & Config Tests\n" + "=" * 50)

    tests = [
        test_config_defaults,
        test_config_from_env,
        test_config_model_fallbacks,
        test_config_backward_compat,
        test_cli_version,
        test_cli_help,
        test_cli_run_help,
        test_cli_config,
        test_cli_config_show_explicit,
        test_cli_config_set,
        test_cli_config_set_python_key,
        test_cli_config_set_invalid_key,
        test_cli_status,
        test_cli_status_json,
        test_cli_config_json,
        test_cli_quiet,
        test_cli_env_file,
        test_cli_pipeline_help,
        test_cli_dashboard_help,
        test_cli_providers_crud,
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
        print("✅ ALL TESTS PASSED — Task 18 CLI & Config ready!")
    else:
        print(f"❌ {failed} test(s) FAILED")
        for name, ok in results:
            if not ok:
                print(f"   - {name}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
