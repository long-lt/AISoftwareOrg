"""
dashboard/routers/projects.py
Router for business portfolio initiatives and projects management.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dashboard.database import (
    list_initiatives,
    create_initiative,
    get_initiative,
    delete_initiative,
)

router = APIRouter()


class ProjectRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    slug: str = ""
    status: str = "discovery"
    health: str = "healthy"
    icon: str = "🤖"
    repository: str = ""
    monthly_spend: float = 0.0
    sla: str = "100%"
    build_progress: int = 0
    features: list[str] = []


@router.get("")
def get_projects() -> list[dict[str, Any]]:
    return list_initiatives()


@router.post("", status_code=201)
def post_project(payload: ProjectRequest) -> dict[str, Any]:
    data = payload.dict()
    return create_initiative(data)


@router.get("/{slug}")
def get_single_project(slug: str) -> dict[str, Any]:
    proj = get_initiative(slug)
    if proj is None:
        raise HTTPException(status_code=404, detail="Project initiative not found")
    return proj


@router.put("/{slug}")
def update_project(slug: str, payload: ProjectRequest) -> dict[str, Any]:
    data = payload.dict()
    data["slug"] = slug
    return create_initiative(data)


@router.patch("/{slug}")
def patch_project(slug: str, payload: ProjectRequest) -> dict[str, Any]:
    data = payload.dict()
    data["slug"] = slug
    return create_initiative(data)


@router.delete("/{slug}")
def delete_single_project(slug: str) -> dict[str, Any]:
    if not delete_initiative(slug):
        raise HTTPException(status_code=404, detail="Project initiative not found")
    return {"deleted": slug}
