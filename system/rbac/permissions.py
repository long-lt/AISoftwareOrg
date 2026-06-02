"""
system/rbac/permissions.py
Permission model for agent actions.
"""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    CRITICAL = "critical"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "dev": {Permission.READ, Permission.WRITE},
    "qa": {Permission.READ, Permission.EXECUTE},
    "reviewer": {Permission.READ},
    "fix": {Permission.READ, Permission.WRITE, Permission.EXECUTE},
    "devops": {
        Permission.READ,
        Permission.WRITE,
        Permission.EXECUTE,
        Permission.CRITICAL,
    },
    "pm": {Permission.READ},
    "planner": {Permission.READ},
}


ROLE_ALIASES = {
    "backend developer": "dev",
    "devagent": "dev",
    "quality assurance engineer": "qa",
    "qaagent": "qa",
    "senior software engineer": "reviewer",
    "revieweragent": "reviewer",
    "product manager": "pm",
    "pmagent": "pm",
    "software architect": "planner",
    "planneragent": "planner",
    "devops engineer": "devops",
    "devopsagent": "devops",
}


def normalize_role(role: str | None) -> str | None:
    """Return the canonical RBAC role key for a human-readable agent role."""
    if role is None:
        return None

    key = role.strip().lower()
    if not key:
        return None
    if key in ROLE_PERMISSIONS:
        return key
    return ROLE_ALIASES.get(key, key)


def permissions_for_role(role: str | None) -> set[Permission]:
    """Return permissions granted to a role."""
    normalized = normalize_role(role)
    if normalized is None:
        return set()
    return set(ROLE_PERMISSIONS.get(normalized, set()))


def has_permission(role: str | None, permission: Permission) -> bool:
    """Check if a role has a permission."""
    return permission in permissions_for_role(role)
