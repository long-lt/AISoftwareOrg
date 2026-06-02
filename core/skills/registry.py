"""
core/skills/registry.py
Compatibility wrapper for the system skill registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from system.skills import SkillRegistry as SystemSkillRegistry


class SkillRegistry(SystemSkillRegistry):
    """Expose the Task 7 registry through the older core.skills import path."""

    def __init__(self, skills_dir: str | Path | None = None):
        super().__init__(skills_dir=skills_dir)

    def get_relevant_skills(
        self,
        task_desc: str,
        agent_role: str = "dev_agent",
    ) -> list[dict[str, Any]]:
        """Return loaded skill objects relevant to a task."""
        return [self.get(name) for name in self.match_for_task(agent_role, task_desc)]

    def format_skills_for_prompt(self, skills: list[dict[str, Any]]) -> str:
        """Format skill objects for prompt context."""
        if not skills:
            return ""

        lines = ["HUONG DAN SKILL TU REGISTRY:"]
        for skill in skills:
            lines.append(f"\nSkill: {skill['name']} ({skill['version']})")
            lines.append("Steps:")
            for step in skill.get("steps", []):
                lines.append(f"- {step}")

            examples = skill.get("examples", [])
            if examples:
                lines.append("Examples:")
                for example in examples:
                    lines.append(f"- {example}")

        return "\n".join(lines)
