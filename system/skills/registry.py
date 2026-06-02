"""
system/skills/registry.py
Load versioned skill JSON files and inject their instructions into prompts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.memory.long_term import cosine_similarity, embed_text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SKILLS_DIR = PROJECT_ROOT / "skills"
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_VERSION_RE = re.compile(r"^v(\d+)$")
_WORD_OVERLAP_THRESHOLD = 0.1  # minimum overlap ratio for word-level fallback
_SEMANTIC_THRESHOLD = 0.35


class SkillRegistryError(RuntimeError):
    """Raised when a skill cannot be loaded or validated."""


class SkillRegistry:
    def __init__(self, skills_dir: str | Path | None = None):
        raw_dir = Path(skills_dir) if skills_dir is not None else DEFAULT_SKILLS_DIR
        self.skills_dir = raw_dir if raw_dir.is_absolute() else PROJECT_ROOT / raw_dir
        self._embedding_cache: dict[tuple[str, str], list[float]] = {}

    def get(self, skill_name: str, version: str = "latest") -> dict[str, Any]:
        """Load a skill by name and version."""
        skill_dir = self._skill_dir(skill_name)
        if not skill_dir.is_dir():
            raise SkillRegistryError(f"Skill not found: {skill_name}")

        selected_version = self.latest_version(skill_name) if version == "latest" else version
        self._validate_version(selected_version)
        version_path = skill_dir / f"{selected_version}.json"
        if not version_path.is_file():
            raise SkillRegistryError(f"Skill version not found: {skill_name}/{selected_version}")

        try:
            with open(version_path, encoding="utf-8") as f:
                skill = json.load(f)
        except json.JSONDecodeError as exc:
            raise SkillRegistryError(f"Skill JSON is invalid: {version_path}") from exc
        except OSError as exc:
            raise SkillRegistryError(f"Cannot read skill file: {version_path}") from exc

        self._validate_skill(skill, skill_name=skill_name, version=selected_version)
        return skill

    def latest_version(self, skill_name: str) -> str:
        """Return the highest numeric vN version for a skill."""
        skill_dir = self._skill_dir(skill_name)
        versions = self.list_versions(skill_name)
        if not versions:
            raise SkillRegistryError(f"Skill has no versions: {skill_name}")
        return versions[-1]

    def list_versions(self, skill_name: str) -> list[str]:
        """List available versions sorted by numeric version."""
        skill_dir = self._skill_dir(skill_name)
        if not skill_dir.is_dir():
            return []

        versions = []
        for path in skill_dir.glob("v*.json"):
            match = _VERSION_RE.match(path.stem)
            if match:
                versions.append((int(match.group(1)), path.stem))
        versions.sort(key=lambda item: item[0])
        return [version for _, version in versions]

    def list_skills(self, applies_to: str | None = None) -> list[str]:
        """List skill names, optionally filtered by agent role."""
        if not self.skills_dir.is_dir():
            return []

        names = []
        for skill_dir in sorted(path for path in self.skills_dir.iterdir() if path.is_dir()):
            name = skill_dir.name
            if applies_to is None:
                names.append(name)
                continue
            try:
                skill = self.get(name)
            except SkillRegistryError:
                continue
            if skill.get("applies_to") == applies_to:
                names.append(name)
        return names

    def match_for_task(
        self,
        applies_to: str,
        task_text: str,
        semantic_threshold: float = _SEMANTIC_THRESHOLD,
    ) -> list[str]:
        """Find skills using hybrid keyword + semantic matching.

        Keyword matches are returned first because explicit triggers are the
        strongest signal. Semantic matches catch paraphrases that do not contain
        hard-coded trigger words.
        """
        keyword_matches = self._keyword_match(applies_to, task_text)
        semantic_matches = self.match_for_task_semantic(
            applies_to,
            task_text,
            threshold=semantic_threshold,
        )
        return list(dict.fromkeys(keyword_matches + semantic_matches))

    def _keyword_match(self, applies_to: str, task_text: str) -> list[str]:
        """Find skills by exact triggers and conservative word-overlap fallback."""
        normalized = task_text.lower()
        task_words = set(re.findall(r"[a-z0-9]+", normalized))
        matches = []

        for name in self.list_skills(applies_to=applies_to):
            skill = self.get(name)
            triggers = skill.get("triggers") or [name.replace("_", " ")]

            # Fast path: keyword match
            if any(_contains_trigger(normalized, str(trigger)) for trigger in triggers):
                matches.append(name)
                continue

            # Fallback: word-overlap score
            skill_text = " ".join([
                name.replace("_", " "),
                *triggers,
                *skill.get("steps", []),
            ])
            score = _word_overlap_score(task_words, skill_text)
            if score >= _WORD_OVERLAP_THRESHOLD:
                matches.append(name)

        return matches

    def match_for_task_semantic(
        self,
        applies_to: str,
        task_text: str,
        threshold: float = _SEMANTIC_THRESHOLD,
    ) -> list[str]:
        """Find skills by embedding similarity between task and skill metadata."""
        task_embedding = embed_text(task_text)
        scored: list[tuple[str, float]] = []

        for name in self.list_skills(applies_to=applies_to):
            skill = self.get(name)
            cache_key = (name, skill["version"])
            skill_embedding = self._embedding_cache.get(cache_key)
            if skill_embedding is None:
                skill_embedding = embed_text(_skill_semantic_text(skill))
                self._embedding_cache[cache_key] = skill_embedding

            score = cosine_similarity(task_embedding, skill_embedding)
            if score >= threshold:
                scored.append((name, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return [name for name, _ in scored]

    def inject_into_prompt(self, prompt: str, skill_name: str, version: str = "latest") -> str:
        """Append a skill's working instructions to an agent prompt."""
        skill = self.get(skill_name, version=version)
        steps = "\n".join(f"- {step}" for step in skill["steps"])

        examples = ""
        if skill.get("examples"):
            example_lines = "\n".join(f"- {example}" for example in skill["examples"])
            examples = f"\n\nVI DU:\n{example_lines}"

        return (
            f"{prompt.rstrip()}\n\n"
            f"HUONG DAN SKILL: {skill['name']} ({skill['version']})\n"
            f"AP DUNG CHO: {skill['applies_to']}\n"
            f"STEPS:\n{steps}"
            f"{examples}\n"
        )

    def _skill_dir(self, skill_name: str) -> Path:
        self._validate_name(skill_name, label="skill_name")
        return self.skills_dir / skill_name

    @staticmethod
    def _validate_name(name: str, label: str) -> None:
        if not name or not _SAFE_NAME_RE.match(name):
            raise SkillRegistryError(f"Invalid {label}: {name!r}")

    @staticmethod
    def _validate_version(version: str) -> None:
        if not version or not _VERSION_RE.match(version):
            raise SkillRegistryError(f"Invalid skill version: {version!r}")

    @staticmethod
    def _validate_skill(skill: dict[str, Any], skill_name: str, version: str) -> None:
        if not isinstance(skill, dict):
            raise SkillRegistryError("Skill file must contain a JSON object")
        if skill.get("name") != skill_name:
            raise SkillRegistryError(f"Skill name mismatch: expected {skill_name!r}")
        if skill.get("version") != version:
            raise SkillRegistryError(f"Skill version mismatch: expected {version!r}")
        if not isinstance(skill.get("applies_to"), str) or not skill["applies_to"]:
            raise SkillRegistryError("Skill must define applies_to")
        if not isinstance(skill.get("steps"), list) or not skill["steps"]:
            raise SkillRegistryError("Skill must define a non-empty steps list")
        if not all(isinstance(step, str) and step.strip() for step in skill["steps"]):
            raise SkillRegistryError("Skill steps must be non-empty strings")
        if "examples" in skill and not isinstance(skill["examples"], list):
            raise SkillRegistryError("Skill examples must be a list")
        if "triggers" in skill and not isinstance(skill["triggers"], list):
            raise SkillRegistryError("Skill triggers must be a list")


def _contains_trigger(normalized_text: str, trigger: str) -> bool:
    normalized_trigger = trigger.lower().strip()
    if not normalized_trigger:
        return False
    if re.match(r"^[a-z0-9_]+$", normalized_trigger):
        return re.search(rf"\b{re.escape(normalized_trigger)}\b", normalized_text) is not None
    return normalized_trigger in normalized_text


def _word_overlap_score(task_words: set[str], skill_text: str) -> float:
    """Fraction of skill words that also appear in task words (0..1)."""
    skill_words = set(re.findall(r"[a-z0-9]+", skill_text.lower()))
    if not skill_words:
        return 0.0
    overlap = task_words & skill_words
    return len(overlap) / len(skill_words)


def _skill_semantic_text(skill: dict[str, Any]) -> str:
    """Build the text used to embed one skill for semantic matching."""
    return " ".join(
        str(part)
        for part in [
            skill.get("name", ""),
            " ".join(str(trigger) for trigger in skill.get("triggers", [])),
            " ".join(str(step) for step in skill.get("steps", [])),
            " ".join(str(example) for example in skill.get("examples", [])),
        ]
        if part
    )
