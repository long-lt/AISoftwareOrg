from __future__ import annotations


_DATA: dict[str, list[dict[str, str | None]]] = {
    "todo": [
        {"id": "todo-1", "title": "Todo item 1", "description": "Seed data for todo."},
        {"id": "todo-2", "title": "Todo item 2", "description": "Second seed data for todo."},
    ],
    "dashboard": [
        {"id": "dashboard-1", "title": "Dashboard item 1", "description": "Seed data for dashboard."},
        {"id": "dashboard-2", "title": "Dashboard item 2", "description": "Second seed data for dashboard."},
    ],
    "settings": [
        {"id": "settings-1", "title": "Settings item 1", "description": "Seed data for settings."},
        {"id": "settings-2", "title": "Settings item 2", "description": "Second seed data for settings."},
    ],
}


def reset_seed_data() -> None:
    for key, items in _DATA.items():
        items.clear()
        items.extend([
            {"id": f"{key}-1", "title": f"{key.title()} item 1", "description": f"Seed data for {key}."},
            {"id": f"{key}-2", "title": f"{key.title()} item 2", "description": f"Second seed data for {key}."},
        ])


def list_todo_items() -> list[dict[str, str | None]]:
    return list(_DATA["todo"])

def list_dashboard_items() -> list[dict[str, str | None]]:
    return list(_DATA["dashboard"])

def list_settings_items() -> list[dict[str, str | None]]:
    return list(_DATA["settings"])

def create_todo_item(payload: dict[str, str | None]) -> dict[str, str | None]:
    item = {
        "id": f"todo-{len(_DATA['todo']) + 1}",
        "title": payload["title"],
        "description": payload.get("description"),
    }
    _DATA["todo"].append(item)
    return item

def create_dashboard_item(payload: dict[str, str | None]) -> dict[str, str | None]:
    item = {
        "id": f"dashboard-{len(_DATA['dashboard']) + 1}",
        "title": payload["title"],
        "description": payload.get("description"),
    }
    _DATA["dashboard"].append(item)
    return item

def create_settings_item(payload: dict[str, str | None]) -> dict[str, str | None]:
    item = {
        "id": f"settings-{len(_DATA['settings']) + 1}",
        "title": payload["title"],
        "description": payload.get("description"),
    }
    _DATA["settings"].append(item)
    return item

