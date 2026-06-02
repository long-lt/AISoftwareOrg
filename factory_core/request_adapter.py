from __future__ import annotations

from typing import Any

from factory_core.types import FactoryRequest


def normalize_factory_request(payload: dict[str, Any]) -> FactoryRequest:
    """
    Convert both legacy Flutter job payloads and new modular factory payloads
    into a normalized FactoryRequest.
    """

    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    slug = str(payload.get("slug", "")).strip()

    project_type = str(payload.get("project_type") or "").strip()
    targets = payload.get("targets")
    stack = payload.get("stack")
    features = payload.get("features")

    # Legacy support:
    # Old payload shape:
    # {
    #   name,
    #   description,
    #   platform,
    #   style,
    #   backend,
    #   features
    # }
    if not project_type:
        project_type = "mobile_app"

    if not isinstance(targets, list) or not targets:
        targets = ["mobile"]

    if not isinstance(stack, dict) or not stack:
        backend = str(payload.get("backend", "none")).strip().lower()

        stack = {
            "mobile": "flutter",
        }

        if backend and backend != "none":
            stack["backend"] = "fastapi"

    if isinstance(features, str):
        features = [item.strip() for item in features.split(",") if item.strip()]

    if not isinstance(features, list):
        features = []

    features = [str(item).strip() for item in features if str(item).strip()]

    return FactoryRequest(
        name=name,
        description=description,
        project_type=project_type,  # type: ignore[arg-type]
        targets=[str(item).strip() for item in targets if str(item).strip()],
        stack={str(key): str(value) for key, value in stack.items()},
        features=features,
        slug=slug,
    )
