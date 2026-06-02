from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BackendResult:
    paths: list[Path]


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _snake(value: str) -> str:
    result = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
    while "__" in result:
        result = result.replace("__", "_")
    return result.strip("_") or "item"


def _class_name(value: str) -> str:
    return "".join(part.capitalize() for part in _snake(value).split("_"))


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required backend contract: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _feature_keys(product_spec: dict[str, Any]) -> list[str]:
    return [_snake(str(feature["key"])) for feature in product_spec.get("features", [])]


def _requirements() -> str:
    return """fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.9.0
"""


def _readme(app_name: str) -> str:
    return f"""# {app_name} Backend

Generated FastAPI backend contract.

## Run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

## Test

```bash
python3 -m unittest discover -s tests
```
"""


def _env_example() -> str:
    return """APP_ENV=local
DATABASE_URL=sqlite:///./app.db
API_HOST=127.0.0.1
API_PORT=8001
"""


def _schemas_py(product_spec: dict[str, Any]) -> str:
    feature_classes = []
    for feature in _feature_keys(product_spec):
        class_name = _class_name(feature)
        feature_classes.append(
            f"""class {class_name}Item(BaseModel):
    id: str
    title: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class {class_name}Create(BaseModel):
    title: str
    description: str | None = None
"""
        )

    return f"""from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str


{chr(10).join(feature_classes)}
"""


def _database_py(product_spec: dict[str, Any]) -> str:
    seed_blocks = []
    feature_getters = []
    feature_creators = []
    for feature in _feature_keys(product_spec):
        seed_blocks.append(
            f"""    "{feature}": [
        {{"id": "{feature}-1", "title": "{_class_name(feature)} item 1", "description": "Seed data for {feature}."}},
        {{"id": "{feature}-2", "title": "{_class_name(feature)} item 2", "description": "Second seed data for {feature}."}},
    ],"""
        )
        feature_getters.append(
            f"""def list_{feature}_items() -> list[dict[str, str | None]]:
    return list(_DATA["{feature}"])
"""
        )
        feature_creators.append(
            f"""def create_{feature}_item(payload: dict[str, str | None]) -> dict[str, str | None]:
    item = {{
        "id": f"{feature}-{{len(_DATA['{feature}']) + 1}}",
        "title": payload["title"],
        "description": payload.get("description"),
    }}
    _DATA["{feature}"].append(item)
    return item
"""
        )

    return f"""from __future__ import annotations


_DATA: dict[str, list[dict[str, str | None]]] = {{
{chr(10).join(seed_blocks)}
}}


def reset_seed_data() -> None:
    for key, items in _DATA.items():
        items.clear()
        items.extend([
            {{"id": f"{{key}}-1", "title": f"{{key.title()}} item 1", "description": f"Seed data for {{key}}."}},
            {{"id": f"{{key}}-2", "title": f"{{key.title()}} item 2", "description": f"Second seed data for {{key}}."}},
        ])


{chr(10).join(feature_getters)}
{chr(10).join(feature_creators)}
"""


def _main_py(product_spec: dict[str, Any]) -> str:
    app_name = product_spec["app"]["name"]
    imports = [
        "from __future__ import annotations",
        "",
        "from fastapi import FastAPI",
        "",
        "from app import database",
        "from app.schemas import HealthResponse",
    ]
    for feature in _feature_keys(product_spec):
        class_name = _class_name(feature)
        imports.append(f"from app.schemas import {class_name}Create, {class_name}Item")

    route_blocks = []
    for feature in _feature_keys(product_spec):
        class_name = _class_name(feature)
        route_blocks.append(
            f"""@app.get("/api/{feature}", response_model=list[{class_name}Item], tags=["{feature}"])
def list_{feature}() -> list[dict[str, str | None]]:
    return database.list_{feature}_items()


@app.post("/api/{feature}", response_model={class_name}Item, tags=["{feature}"])
def create_{feature}(payload: {class_name}Create) -> dict[str, str | None]:
    return database.create_{feature}_item(payload.model_dump())
"""
        )

    return f"""{chr(10).join(imports)}


app = FastAPI(title="{app_name} API", version="0.1.0")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", app="{app_name}")


{chr(10).join(route_blocks)}
"""


def _database_schema_sql(data_model: dict[str, Any]) -> str:
    statements = []
    for entity in data_model.get("entities", []):
        table = entity["table_name"]
        columns = []
        for field in entity.get("fields", []):
            name = field["name"]
            field_type = str(field["type"])
            sql_type = {
                "string": "TEXT",
                "datetime": "TEXT",
                "boolean": "INTEGER",
                "integer": "INTEGER",
                "decimal": "REAL",
            }.get(field_type, "TEXT")
            required = " NOT NULL" if field.get("required") else ""
            primary = " PRIMARY KEY" if name == "id" else ""
            columns.append(f"  {name} {sql_type}{primary}{required}")
        statements.append(
            f"CREATE TABLE IF NOT EXISTS {table} (\n{',\n'.join(columns)}\n);"
        )
    return "\n\n".join(statements) + "\n"


def _openapi_yaml(product_spec: dict[str, Any]) -> str:
    path_blocks = [
        """  /health:
    get:
      tags: [system]
      summary: Health check
      responses:
        "200":
          description: API is healthy"""
    ]
    for feature in _feature_keys(product_spec):
        path_blocks.append(
            f"""  /api/{feature}:
    get:
      tags: [{feature}]
      summary: List {feature} items
      responses:
        "200":
          description: List of {feature} items
    post:
      tags: [{feature}]
      summary: Create {feature} item
      responses:
        "200":
          description: Created {feature} item"""
        )

    return f"""openapi: 3.0.3
info:
  title: {product_spec["app"]["name"]} API
  version: 0.1.0
paths:
{chr(10).join(path_blocks)}
"""


def _test_contract_py(product_spec: dict[str, Any], data_model: dict[str, Any]) -> str:
    features = _feature_keys(product_spec)
    route_assertions = "\n".join(
        f"""        self.assertIn('/api/{feature}', source)
        self.assertIn('def list_{feature}', source)
        self.assertIn('def create_{feature}', source)"""
        for feature in features
    )
    entity_assertions = "\n".join(
        f"""        self.assertIn('CREATE TABLE IF NOT EXISTS {entity["table_name"]}', schema)"""
        for entity in data_model.get("entities", [])
    )
    return f"""from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackendContractTest(unittest.TestCase):
    def test_routes_match_feature_contract(self) -> None:
        source = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')
        self.assertIn('/health', source)
{route_assertions}

    def test_database_schema_contains_contract_entities(self) -> None:
        schema = (ROOT.parent / 'docs' / 'database_schema.sql').read_text(encoding='utf-8')
{entity_assertions}

    def test_openapi_contains_contract_paths(self) -> None:
        openapi = (ROOT.parent / 'docs' / 'openapi.yaml').read_text(encoding='utf-8')
        self.assertIn('/health:', openapi)
{chr(10).join(f"        self.assertIn('/api/{feature}:', openapi)" for feature in features)}


if __name__ == '__main__':
    unittest.main()
"""


def _run_backend_tests(backend_dir: Path) -> tuple[int, str]:
    process = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests"],
        cwd=backend_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    return process.returncode, process.stdout.strip()


def _backend_report(
    app_name: str,
    backend_dir: Path,
    test_exit_code: int,
    test_output: str,
    features: list[str],
) -> str:
    status = "PASS" if test_exit_code == 0 else "FAIL"
    return f"""# Backend Report: {app_name}

## Tổng Quan

- Status: {status}
- Created at: {datetime.now().isoformat(timespec="seconds")}
- Backend: `{backend_dir}`
- Features: {", ".join(features)}

## Generated Scope

- FastAPI app skeleton.
- Feature list/create endpoints.
- Pydantic request/response schemas.
- Seed in-memory data module.
- OpenAPI contract handoff file.
- SQLite/PostgreSQL-compatible schema handoff file.
- Contract tests.

## Test Command

```bash
python3 -m unittest discover -s tests
```

## Test Result

- Exit code: {test_exit_code}

```text
{test_output or "(no output)"}
```
"""


def write_backend_source(
    app_input: dict[str, Any],
    docs_dir: Path,
    backend_dir: Path,
) -> list[Path]:
    product_spec = _load_json(docs_dir / "product_spec.json")
    data_model = _load_json(docs_dir / "data_model.json")
    app_name = product_spec["app"]["name"]
    features = _feature_keys(product_spec)

    paths = [
        _write(backend_dir / "requirements.txt", _requirements()),
        _write(backend_dir / "README.md", _readme(app_name)),
        _write(backend_dir / ".env.example", _env_example()),
        _write(backend_dir / "app" / "__init__.py", ""),
        _write(backend_dir / "app" / "schemas.py", _schemas_py(product_spec)),
        _write(backend_dir / "app" / "database.py", _database_py(product_spec)),
        _write(backend_dir / "app" / "main.py", _main_py(product_spec)),
        _write(backend_dir / "tests" / "__init__.py", ""),
        _write(backend_dir / "tests" / "test_contract.py", _test_contract_py(product_spec, data_model)),
        _write(docs_dir / "openapi.yaml", _openapi_yaml(product_spec)),
        _write(docs_dir / "database_schema.sql", _database_schema_sql(data_model)),
    ]

    test_exit_code, test_output = _run_backend_tests(backend_dir)
    report = _backend_report(app_name, backend_dir, test_exit_code, test_output, features)
    paths.append(_write(docs_dir / "backend_report.md", report))

    if test_exit_code != 0:
        raise RuntimeError(f"Backend tests failed:\n{test_output}")

    return paths
