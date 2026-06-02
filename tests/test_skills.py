import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from agents import AgentTask, DevAgent
from core.skills import SkillRegistry as CoreSkillRegistry
from system.skills import SkillRegistry, SkillRegistryError


def _write_skill(base: Path, name: str, version: str, steps: list[str]):
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "version": version,
        "applies_to": "dev_agent",
        "triggers": ["api"],
        "steps": steps,
        "examples": ["GET /items returns items"],
    }
    (skill_dir / f"{version}.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_registry_loads_latest_version(tmp_path):
    skills_dir = Path(tmp_path) / "skills"
    _write_skill(skills_dir, "create_api", "v1", ["old step"])
    _write_skill(skills_dir, "create_api", "v2", ["new step"])

    registry = SkillRegistry(skills_dir=skills_dir)
    skill = registry.get("create_api")

    assert skill["version"] == "v2"
    assert skill["steps"] == ["new step"]


def test_registry_injects_skill_steps(tmp_path):
    skills_dir = Path(tmp_path) / "skills"
    _write_skill(skills_dir, "create_api", "v1", ["Define route", "Validate input"])

    registry = SkillRegistry(skills_dir=skills_dir)
    prompt = registry.inject_into_prompt("PROMPT", "create_api")

    assert "HUONG DAN SKILL: create_api (v1)" in prompt
    assert "- Define route" in prompt
    assert "- Validate input" in prompt


def test_registry_rejects_path_traversal(tmp_path):
    skills_dir = Path(tmp_path) / "skills"
    _write_skill(skills_dir, "create_api", "v1", ["Define route"])
    registry = SkillRegistry(skills_dir=skills_dir)

    _assert_raises(SkillRegistryError, lambda: registry.get("../secret"))
    _assert_raises(SkillRegistryError, lambda: registry.get("create_api", "../v1"))


def test_core_registry_compatibility_uses_project_skills():
    registry = CoreSkillRegistry()
    skills = registry.get_relevant_skills(
        "Tạo một FastAPI endpoint để lấy thông tin thời tiết."
    )
    formatted = registry.format_skills_for_prompt(skills)

    assert skills
    assert skills[0]["name"] == "create_api"
    assert "HUONG DAN SKILL TU REGISTRY" in formatted


def test_dev_agent_injects_create_api_skill_for_api_tasks():
    agent = DevAgent()
    task = AgentTask(
        id="dev-skill-test",
        description="Tạo FastAPI endpoint GET /users trả về danh sách users.",
    )

    prompt = agent._build_initial_prompt(task)

    assert "HUONG DAN SKILL: create_api" in prompt
    assert "Define the route path and HTTP method explicitly." in prompt


def test_dev_agent_does_not_match_api_inside_unrelated_words():
    agent = DevAgent()
    task = AgentTask(
        id="dev-no-skill-test",
        description="Viết hàm capitalize_name(name) để chuẩn hóa tên người dùng.",
    )

    prompt = agent._build_initial_prompt(task)

    assert "HUONG DAN SKILL: create_api" not in prompt


def test_registry_semantic_match_finds_paraphrased_api_task(tmp_path):
    skills_dir = Path(tmp_path) / "skills"
    _write_skill(
        skills_dir,
        "create_api",
        "v1",
        ["Accept request payload", "Validate input", "Return HTTP response"],
    )
    registry = SkillRegistry(skills_dir=skills_dir)

    task_text = "Tạo cổng tiếp nhận dữ liệu người dùng mới"
    assert registry._keyword_match("dev_agent", task_text) == []

    import system.skills.registry as registry_module

    original_embed_text = registry_module.embed_text
    original_cosine_similarity = registry_module.cosine_similarity

    def fake_embed_text(text: str):
        lowered = text.lower()
        if "cổng tiếp nhận" in lowered:
            return [1.0, 0.0, 0.0]
        if "create_api" in lowered:
            return [0.95, 0.05, 0.0]
        return [0.0, 1.0, 0.0]

    try:
        registry_module.embed_text = fake_embed_text
        registry_module.cosine_similarity = lambda left, right: sum(
            a * b for a, b in zip(left, right)
        )

        semantic = registry.match_for_task_semantic("dev_agent", task_text, threshold=0.5)
        hybrid = registry.match_for_task("dev_agent", task_text, semantic_threshold=0.5)
    finally:
        registry_module.embed_text = original_embed_text
        registry_module.cosine_similarity = original_cosine_similarity

    assert semantic == ["create_api"]
    assert hybrid == ["create_api"]


def _assert_raises(error_type, fn):
    try:
        fn()
    except error_type:
        return
    raise AssertionError(f"Expected {error_type.__name__}")


def main():
    print("Running skill registry tests")
    with TemporaryDirectory() as tmp_dir:
        test_registry_loads_latest_version(Path(tmp_dir))
    with TemporaryDirectory() as tmp_dir:
        test_registry_injects_skill_steps(Path(tmp_dir))
    with TemporaryDirectory() as tmp_dir:
        test_registry_rejects_path_traversal(Path(tmp_dir))
    test_core_registry_compatibility_uses_project_skills()
    test_dev_agent_injects_create_api_skill_for_api_tasks()
    test_dev_agent_does_not_match_api_inside_unrelated_words()
    with TemporaryDirectory() as tmp_dir:
        test_registry_semantic_match_finds_paraphrased_api_task(Path(tmp_dir))
    print("All skill registry tests passed")


if __name__ == "__main__":
    main()
