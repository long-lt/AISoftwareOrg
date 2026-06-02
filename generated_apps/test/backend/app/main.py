from __future__ import annotations

from fastapi import FastAPI

from app import database
from app.schemas import HealthResponse
from app.schemas import TodoCreate, TodoItem
from app.schemas import DashboardCreate, DashboardItem
from app.schemas import SettingsCreate, SettingsItem


app = FastAPI(title="Test API", version="0.1.0")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", app="Test")


@app.get("/api/todo", response_model=list[TodoItem], tags=["todo"])
def list_todo() -> list[dict[str, str | None]]:
    return database.list_todo_items()


@app.post("/api/todo", response_model=TodoItem, tags=["todo"])
def create_todo(payload: TodoCreate) -> dict[str, str | None]:
    return database.create_todo_item(payload.model_dump())

@app.get("/api/dashboard", response_model=list[DashboardItem], tags=["dashboard"])
def list_dashboard() -> list[dict[str, str | None]]:
    return database.list_dashboard_items()


@app.post("/api/dashboard", response_model=DashboardItem, tags=["dashboard"])
def create_dashboard(payload: DashboardCreate) -> dict[str, str | None]:
    return database.create_dashboard_item(payload.model_dump())

@app.get("/api/settings", response_model=list[SettingsItem], tags=["settings"])
def list_settings() -> list[dict[str, str | None]]:
    return database.list_settings_items()


@app.post("/api/settings", response_model=SettingsItem, tags=["settings"])
def create_settings(payload: SettingsCreate) -> dict[str, str | None]:
    return database.create_settings_item(payload.model_dump())

