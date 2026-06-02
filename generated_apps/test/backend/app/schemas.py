from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str


class TodoItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TodoCreate(BaseModel):
    title: str
    description: str | None = None

class DashboardItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DashboardCreate(BaseModel):
    title: str
    description: str | None = None

class SettingsItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SettingsCreate(BaseModel):
    title: str
    description: str | None = None

