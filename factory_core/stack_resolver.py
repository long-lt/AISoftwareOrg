from __future__ import annotations

from factory_core.types import FactoryRequest


class StackResolverError(RuntimeError):
    pass


STACK_MODULE_MAP: dict[str, dict[str, str]] = {
    "mobile": {
        "flutter": "mobile.flutter",
    },
    "frontend": {
        "react": "frontend.react",
        "nextjs": "frontend.nextjs",
    },
    "backend": {
        "fastapi": "backend.fastapi",
    },
    "database": {
        "supabase": "database.supabase",
    },
}


def resolve_selected_module(selector: str, request: FactoryRequest) -> str:
    """
    Resolve workflow placeholders such as:
    - mobile.selected
    - frontend.selected
    - backend.selected
    - database.selected
    """

    if not selector.endswith(".selected"):
        return selector

    category = selector.split(".", 1)[0]
    selected_stack = request.stack.get(category)

    if not selected_stack:
        raise StackResolverError(
            f"Workflow requires '{category}.selected', but request.stack['{category}'] is missing"
        )

    category_map = STACK_MODULE_MAP.get(category)
    if not category_map:
        raise StackResolverError(f"No stack map configured for category: {category}")

    module_id = category_map.get(selected_stack)
    if not module_id:
        raise StackResolverError(
            f"Unsupported {category} stack '{selected_stack}'. "
            f"Supported: {sorted(category_map.keys())}"
        )

    return module_id
