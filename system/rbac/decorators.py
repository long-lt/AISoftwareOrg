"""
system/rbac/decorators.py
Decorators for enforcing agent permissions.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from .permissions import Permission, permissions_for_role, normalize_role

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class PermissionDenied(Exception):
    """Raised when an agent attempts an action outside its permissions."""


def require_permission(permission: Permission) -> Callable[[F], F]:
    """Require an async agent method to have a permission before it runs."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            raw_role = getattr(self, "role", None)
            agent_name = getattr(self, "name", self.__class__.__name__)
            agent_role = normalize_role(raw_role)
            allowed = permissions_for_role(raw_role)

            if permission not in allowed:
                logger.warning(
                    "[SECURITY] %s role=%s denied permission=%s",
                    agent_name,
                    agent_role or raw_role,
                    permission.value,
                )
                raise PermissionDenied(
                    f"Agent '{agent_name}' with role '{agent_role or raw_role}' "
                    f"does not have permission '{permission.value}'"
                )

            return await func(self, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
