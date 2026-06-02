from __future__ import annotations

import json
import re
import sqlite3
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from workflows.phase_registry import (
    PHASE_IDS,
    PIPELINE_PHASES as PHASE_CONTRACTS,
    canonical_phase_id,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
GENERATED_APPS_DIR = ROOT_DIR / "workspace" / "generated_apps"
DB_PATH = ROOT_DIR / "dashboard" / "data" / "app.db"

JOB_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled", "cancel_requested"}
PHASE_STATUSES = {"pending", "running", "passed", "failed", "skipped", "cancelled"}
PIPELINE_PHASES = tuple(
    [phase.id for phase in PHASE_CONTRACTS]
    + [alias for phase in PHASE_CONTRACTS for alias in phase.aliases]
)
EXPORT_PHASE_FILES = {phase.id: tuple(phase.required_outputs) for phase in PHASE_CONTRACTS}

T = TypeVar("T")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _with_write_retry(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    sleep_seconds: float = 0.05,
) -> T:
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                raise
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(sleep_seconds * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("Write retry operation failed without an error")


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _add_column_if_missing(connection: sqlite3.Connection, table: str, definition: str) -> None:
    column = definition.split()[0]
    if column not in _table_columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            slug TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            features_json TEXT NOT NULL,
            app_dir TEXT,
            export_path TEXT,
            error TEXT,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            current_phase TEXT,
            progress INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    _add_column_if_missing(connection, "jobs", "cancel_requested INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(connection, "jobs", "current_phase TEXT")
    _add_column_if_missing(connection, "jobs", "progress INTEGER NOT NULL DEFAULT 0")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS job_phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_slug TEXT NOT NULL,
            phase TEXT NOT NULL,
            agent TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            input_files_json TEXT NOT NULL DEFAULT '[]',
            output_files_json TEXT NOT NULL DEFAULT '[]',
            output_path TEXT,
            error TEXT,
            logs_path TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(job_slug, phase),
            FOREIGN KEY(job_slug) REFERENCES jobs(slug) ON DELETE CASCADE
        )
        """
    )
    for definition in [
        "job_slug TEXT NOT NULL DEFAULT ''",
        "phase TEXT NOT NULL DEFAULT ''",
        "agent TEXT NOT NULL DEFAULT ''",
        "status TEXT NOT NULL DEFAULT 'pending'",
        "started_at TEXT",
        "finished_at TEXT",
        "error TEXT",
        "created_at TEXT NOT NULL DEFAULT ''",
        "updated_at TEXT NOT NULL DEFAULT ''",
    ]:
        _add_column_if_missing(connection, "job_phases", definition)
    _add_column_if_missing(connection, "job_phases", "input_files_json TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(connection, "job_phases", "output_files_json TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(connection, "job_phases", "output_path TEXT")
    _add_column_if_missing(connection, "job_phases", "logs_path TEXT")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_job_phases_job_phase ON job_phases(job_slug, phase)"
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS job_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_slug TEXT NOT NULL,
            phase TEXT,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(job_slug) REFERENCES jobs(slug) ON DELETE CASCADE
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS initiatives (
            slug TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            health TEXT NOT NULL,
            icon TEXT NOT NULL,
            repository TEXT NOT NULL,
            monthly_spend REAL NOT NULL,
            sla TEXT NOT NULL,
            build_progress INTEGER NOT NULL,
            features_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    for definition in [
        "slug TEXT",
        "name TEXT NOT NULL DEFAULT ''",
        "description TEXT NOT NULL DEFAULT ''",
        "status TEXT NOT NULL DEFAULT 'discovery'",
        "health TEXT NOT NULL DEFAULT 'healthy'",
        "icon TEXT NOT NULL DEFAULT ''",
        "repository TEXT NOT NULL DEFAULT ''",
        "monthly_spend REAL NOT NULL DEFAULT 0",
        "sla TEXT NOT NULL DEFAULT '100%'",
        "build_progress INTEGER NOT NULL DEFAULT 0",
        "features_json TEXT NOT NULL DEFAULT '[]'",
        "created_at TEXT NOT NULL DEFAULT ''",
        "updated_at TEXT NOT NULL DEFAULT ''",
    ]:
        _add_column_if_missing(connection, "initiatives", definition)
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_initiatives_slug ON initiatives(slug)"
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS agents_config (
            id TEXT PRIMARY KEY,
            agent_id TEXT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            model TEXT NOT NULL,
            system_prompt TEXT NOT NULL DEFAULT '',
            temperature REAL NOT NULL,
            max_tokens INTEGER NOT NULL,
            specialties_json TEXT NOT NULL,
            description TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT '',
            last_active TEXT NOT NULL,
            success_rate REAL NOT NULL,
            tasks_completed INTEGER NOT NULL
        )
        """
    )
    for definition in [
        "id TEXT",
        "agent_id TEXT",
        "type TEXT NOT NULL DEFAULT 'agent'",
        "status TEXT NOT NULL DEFAULT 'active'",
        "temperature REAL NOT NULL DEFAULT 0.2",
        "max_tokens INTEGER NOT NULL DEFAULT 4096",
        "specialties_json TEXT NOT NULL DEFAULT '[]'",
        "description TEXT NOT NULL DEFAULT ''",
        "last_active TEXT NOT NULL DEFAULT ''",
        "success_rate REAL NOT NULL DEFAULT 0",
        "tasks_completed INTEGER NOT NULL DEFAULT 0",
        "system_prompt TEXT NOT NULL DEFAULT ''",
        "updated_at TEXT NOT NULL DEFAULT ''",
    ]:
        _add_column_if_missing(connection, "agents_config", definition)
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_config_agent_id ON agents_config(agent_id)"
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    _add_column_if_missing(connection, "system_settings", "updated_at TEXT NOT NULL DEFAULT ''")
    _seed_defaults(connection)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    _initialize_schema(connection)
    connection.commit()
    return connection


def _seed_defaults(connection: sqlite3.Connection) -> None:
    agents = [
        (
            "ba",
            "Business Analyst",
            "analysis",
            "active",
            "gpt-5",
            0.4,
            4096,
            ["requirements", "market research", "strategy"],
            "Analyzes product goals and turns vague ideas into executable requirements.",
            _now(),
            97.0,
            42,
        ),
        (
            "backend",
            "Backend Designer",
            "engineering",
            "active",
            "gpt-5-codex",
            0.2,
            4096,
            ["APIs", "data models", "security"],
            "Designs backend contracts, schemas, and integration points.",
            _now(),
            95.0,
            37,
        ),
        (
            "architect",
            "Software Architect",
            "architecture",
            "active",
            "gpt-5-codex",
            0.2,
            4096,
            ["system architecture", "scalability", "quality gates"],
            "Defines the technical blueprint and non-functional constraints.",
            _now(),
            94.0,
            31,
        ),
        (
            "uiux",
            "UI/UX Designer",
            "design",
            "active",
            "gpt-5",
            0.5,
            4096,
            ["interface design", "prototyping", "accessibility"],
            "Creates UX flows and visual direction for generated products.",
            _now(),
            96.0,
            39,
        ),
        (
            "dev",
            "Flutter Developer",
            "engineering",
            "active",
            "gpt-5-codex",
            0.2,
            8192,
            ["Flutter", "Dart", "frontend implementation"],
            "Builds generated Flutter applications from approved specs.",
            _now(),
            93.0,
            28,
        ),
        (
            "qa",
            "QA Reviewer",
            "quality",
            "active",
            "gpt-5-codex",
            0.2,
            4096,
            ["testing", "static analysis", "release checks"],
            "Runs validation checks and repair loops before release.",
            _now(),
            92.0,
            24,
        ),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO agents_config (
            id, agent_id, name, type, status, model, system_prompt, temperature, max_tokens,
            specialties_json, description, updated_at, last_active, success_rate, tasks_completed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                agent_id,
                agent_id,
                name,
                agent_type,
                status,
                model,
                description,
                temperature,
                max_tokens,
                json.dumps(specialties),
                description,
                last_active,
                last_active,
                success_rate,
                tasks_completed,
            )
            for (
                agent_id,
                name,
                agent_type,
                status,
                model,
                temperature,
                max_tokens,
                specialties,
                description,
                last_active,
                success_rate,
                tasks_completed,
            ) in agents
        ],
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO system_settings (key, value)
        VALUES (?, ?)
        """,
        [
            ("queue_mode", "sqlite"),
            ("max_parallel_jobs", "1"),
            ("default_job_timeout_minutes", "30"),
        ],
    )


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "app"


def _validate_job_status(status: str) -> None:
    if status not in JOB_STATUSES:
        raise ValueError(f"Invalid job status: {status}")


def _validate_phase_status(status: str) -> None:
    if status not in PHASE_STATUSES:
        raise ValueError(f"Invalid phase status: {status}")


def _canonical_phase(phase: str | None) -> str | None:
    if phase is None:
        return None
    try:
        return canonical_phase_id(phase)
    except ValueError as exc:
        raise ValueError(f"Invalid phase: {phase}") from exc


def _decode_json_array(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _insert_default_phases(connection: sqlite3.Connection, slug: str) -> None:
    timestamp = _now()
    for phase in PHASE_CONTRACTS:
        connection.execute(
            """
            INSERT OR IGNORE INTO job_phases (
                job_slug, phase, agent, status, input_files_json, output_files_json,
                output_path, logs_path, created_at, updated_at
            )
            VALUES (?, ?, ?, 'pending', ?, '[]', NULL, NULL, ?, ?)
            """,
            (
                slug,
                phase.id,
                phase.agent,
                json.dumps(list(phase.required_inputs)),
                timestamp,
                timestamp,
            ),
        )


def initialize_job_phases(slug: str) -> None:
    def operation() -> None:
        with _connect() as connection:
            _insert_default_phases(connection, slug)
            _set_job_progress(connection, slug)
            connection.commit()

    _with_write_retry(operation)


def _passed_progress(connection: sqlite3.Connection, slug: str) -> int:
    rows = connection.execute(
        "SELECT phase FROM job_phases WHERE job_slug = ? AND status = 'passed'",
        (slug,),
    ).fetchall()
    passed = {str(row["phase"]) for row in rows}
    return round((len(passed) / len(PHASE_IDS)) * 100)


def _set_job_progress(
    connection: sqlite3.Connection,
    slug: str,
    *,
    current_phase: str | None = None,
) -> None:
    progress = _passed_progress(connection, slug)
    if current_phase is None:
        connection.execute(
            "UPDATE jobs SET progress = ?, updated_at = ? WHERE slug = ?",
            (progress, _now(), slug),
        )
    else:
        connection.execute(
            """
            UPDATE jobs
            SET progress = ?, current_phase = ?, updated_at = ?
            WHERE slug = ?
            """,
            (progress, current_phase, _now(), slug),
        )


def _upsert_job(
    slug: str,
    *,
    name: str,
    description: str,
    features: list[str],
    status: str = "queued",
    app_dir: str | None = None,
    export_path: str | None = None,
    error: str | None = None,
    cancel_requested: bool | None = None,
) -> None:
    _validate_job_status(status)
    features_json = json.dumps(features)
    app_dir_value = str(app_dir) if app_dir is not None else None
    export_path_value = str(export_path) if export_path is not None else None

    def operation() -> None:
        with _connect() as connection:
            existing = connection.execute(
                "SELECT cancel_requested FROM jobs WHERE slug = ?",
                (slug,),
            ).fetchone()
            timestamp = _now()
            should_cancel = (
                int(cancel_requested)
                if cancel_requested is not None
                else int(existing["cancel_requested"]) if existing else 0
            )
            if status in {"queued", "succeeded", "failed", "cancelled"} and cancel_requested is None:
                should_cancel = 0

            connection.execute(
                """
                INSERT INTO jobs (
                    slug, name, description, status, features_json, app_dir, export_path,
                    error, cancel_requested, current_phase, progress, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    status = excluded.status,
                    features_json = excluded.features_json,
                    app_dir = excluded.app_dir,
                    export_path = excluded.export_path,
                    error = excluded.error,
                    cancel_requested = excluded.cancel_requested,
                    updated_at = excluded.updated_at
                """,
                (
                    slug,
                    name,
                    description,
                    status,
                    features_json,
                    app_dir_value,
                    export_path_value,
                    error,
                    should_cancel,
                    timestamp,
                    timestamp,
                ),
            )
            if status == "queued":
                connection.execute("DELETE FROM job_logs WHERE job_slug = ?", (slug,))
                connection.execute("DELETE FROM job_phases WHERE job_slug = ?", (slug,))
                _insert_default_phases(connection, slug)
                _set_job_progress(connection, slug)
            connection.commit()

    _with_write_retry(operation)


def _job_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    try:
        features = json.loads(row["features_json"])
    except json.JSONDecodeError:
        features = []
    return {
        "slug": row["slug"],
        "name": row["name"],
        "description": row["description"],
        "features": features,
        "status": row["status"],
        "app_dir": row["app_dir"],
        "export_path": row["export_path"],
        "error": row["error"],
        "cancel_requested": bool(row["cancel_requested"]),
        "current_phase": row["current_phase"],
        "progress": int(row["progress"] or 0),
        "phases": phase_status(row["slug"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_jobs() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return [_job_row_to_dict(row) for row in rows]


def get_job(slug: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE slug = ?", (slug,)).fetchone()
    return _job_row_to_dict(row) if row else None


def delete_job_record(slug: str) -> bool:
    def operation() -> bool:
        with _connect() as connection:
            cursor = connection.execute("DELETE FROM jobs WHERE slug = ?", (slug,))
            connection.commit()
            return cursor.rowcount > 0

    return _with_write_retry(operation)


def list_job_phases(slug: str) -> list[dict[str, Any]]:
    initialize_job_phases(slug)
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM job_phases WHERE job_slug = ?",
            (slug,),
        ).fetchall()
    by_phase = {row["phase"]: row for row in rows}
    phases_by_name: dict[str, dict[str, Any]] = {}
    for contract in PHASE_CONTRACTS:
        phase_id = contract.id
        row = by_phase.get(phase_id)
        if not row:
            continue
        phase_payload = {
            "id": row["id"],
            "job_slug": row["job_slug"],
            "phase": row["phase"],
            "agent": row["agent"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "input_files_json": row["input_files_json"],
            "output_files_json": row["output_files_json"],
            "output_path": row["output_path"],
            "error": row["error"],
            "logs_path": row["logs_path"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        phases_by_name[phase_id] = phase_payload
        for alias in contract.aliases:
            phases_by_name[alias] = {**phase_payload, "phase": alias}
    return [phases_by_name[phase] for phase in PIPELINE_PHASES if phase in phases_by_name]


def phase_status(slug: str) -> dict[str, str]:
    phases = {phase["phase"]: phase["status"] for phase in list_job_phases(slug)}
    statuses: dict[str, str] = {}
    for phase in PHASE_CONTRACTS:
        status = phases.get(phase.id, "pending")
        statuses[phase.id] = status
        for alias in phase.aliases:
            statuses[alias] = status
    return statuses


def start_phase(slug: str, phase: str) -> None:
    phase_id = _canonical_phase(phase)
    assert phase_id is not None

    def operation() -> None:
        with _connect() as connection:
            _insert_default_phases(connection, slug)
            timestamp = _now()
            connection.execute(
                """
                UPDATE job_phases
                SET status = 'running',
                    started_at = COALESCE(started_at, ?),
                    finished_at = NULL,
                    error = NULL,
                    updated_at = ?
                WHERE job_slug = ? AND phase = ?
                """,
                (timestamp, timestamp, slug, phase_id),
            )
            _set_job_progress(connection, slug, current_phase=phase_id)
            connection.commit()

    _with_write_retry(operation)


def finish_phase(
    slug: str,
    phase: str,
    status: str,
    *,
    error: str | None = None,
    output_files: list[str] | tuple[str, ...] | None = None,
    output_path: str | None = None,
    logs_path: str | None = None,
) -> None:
    phase_id = _canonical_phase(phase)
    assert phase_id is not None
    _validate_phase_status(status)

    normalized_outputs = [str(path) for path in (output_files or [])]
    if output_path is None and len(normalized_outputs) == 1:
        output_path = normalized_outputs[0]

    def operation() -> None:
        with _connect() as connection:
            _insert_default_phases(connection, slug)
            timestamp = _now()
            connection.execute(
                """
                UPDATE job_phases
                SET status = ?,
                    finished_at = ?,
                    output_files_json = ?,
                    output_path = ?,
                    error = ?,
                    logs_path = ?,
                    updated_at = ?
                WHERE job_slug = ? AND phase = ?
                """,
                (
                    status,
                    timestamp,
                    json.dumps(normalized_outputs),
                    output_path,
                    error,
                    logs_path,
                    timestamp,
                    slug,
                    phase_id,
                ),
            )
            _set_job_progress(connection, slug, current_phase=phase_id)
            connection.commit()

    _with_write_retry(operation)


def request_job_cancellation(slug: str) -> bool:
    def operation() -> bool:
        with _connect() as connection:
            timestamp = _now()
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = 'cancel_requested',
                    cancel_requested = 1,
                    updated_at = ?
                WHERE slug = ? AND status IN ('queued', 'running', 'cancel_requested')
                """,
                (timestamp, slug),
            )
            connection.commit()
            return cursor.rowcount > 0

    return _with_write_retry(operation)


def is_cancel_requested(slug: str) -> bool:
    with _connect() as connection:
        row = connection.execute(
            "SELECT status, cancel_requested FROM jobs WHERE slug = ?",
            (slug,),
        ).fetchone()
    if row is None:
        return False
    return bool(row["cancel_requested"]) or row["status"] in {"cancel_requested", "cancelled"}


def write_job_log(
    job_slug: str,
    *,
    phase: str | None,
    level: str,
    message: str,
) -> dict[str, Any]:
    phase_id = _canonical_phase(phase) if phase else None
    normalized_level = level.lower()

    def operation() -> dict[str, Any]:
        with _connect() as connection:
            timestamp = _now()
            cursor = connection.execute(
                """
                INSERT INTO job_logs (job_slug, phase, level, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_slug, phase_id, normalized_level, message, timestamp),
            )
            connection.commit()
            return {
                "id": cursor.lastrowid,
                "job_slug": job_slug,
                "phase": phase_id,
                "level": normalized_level,
                "message": message,
                "created_at": timestamp,
            }

    return _with_write_retry(operation)


def list_job_logs(
    job_slug: str,
    *,
    phase: str | None = None,
    level: str | None = None,
) -> list[dict[str, Any]]:
    phase_id = _canonical_phase(phase) if phase else None
    normalized_level = level.lower() if level else None
    clauses = ["job_slug = ?"]
    params: list[Any] = [job_slug]
    if phase_id:
        clauses.append("phase = ?")
        params.append(phase_id)
    if normalized_level:
        clauses.append("level = ?")
        params.append(normalized_level)
    query = f"SELECT * FROM job_logs WHERE {' AND '.join(clauses)} ORDER BY id ASC"
    with _connect() as connection:
        rows = connection.execute(query, params).fetchall()
    return [
        {
            "id": row["id"],
            "job_slug": row["job_slug"],
            "phase": row["phase"],
            "level": row["level"],
            "message": row["message"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def list_initiatives() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM initiatives ORDER BY updated_at DESC").fetchall()
    initiatives: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["features"] = _decode_json_array(item.pop("features_json", "[]"))
        initiatives.append(item)
    return initiatives


def get_initiative(slug: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM initiatives WHERE slug = ?",
            (slug,),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["features"] = _decode_json_array(item.pop("features_json", "[]"))
    return item


def create_initiative(
    data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    payload = {**(data or {}), **kwargs}
    name = str(payload.get("name") or payload.get("title") or "Untitled Project")
    slug = str(payload.get("slug") or slugify(name))
    description = str(payload.get("description") or payload.get("detail") or "")
    features = payload.get("features") or []
    if not isinstance(features, list):
        features = [str(features)]
    timestamp = _now()

    def operation() -> None:
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO initiatives (
                    slug, name, description, status, health, icon, repository,
                    monthly_spend, sla, build_progress, features_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    status = excluded.status,
                    health = excluded.health,
                    icon = excluded.icon,
                    repository = excluded.repository,
                    monthly_spend = excluded.monthly_spend,
                    sla = excluded.sla,
                    build_progress = excluded.build_progress,
                    features_json = excluded.features_json,
                    updated_at = excluded.updated_at
                """,
                (
                    slug,
                    name,
                    description,
                    str(payload.get("status") or "discovery"),
                    str(payload.get("health") or "healthy"),
                    str(payload.get("icon") or ""),
                    str(payload.get("repository") or ""),
                    float(payload.get("monthly_spend") or 0.0),
                    str(payload.get("sla") or "100%"),
                    int(payload.get("build_progress") or 0),
                    json.dumps([str(feature) for feature in features]),
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()

    _with_write_retry(operation)
    created = get_initiative(slug)
    if created is None:
        raise RuntimeError(f"Failed to create initiative: {slug}")
    return created


def delete_initiative(slug: str) -> bool:
    def operation() -> bool:
        with _connect() as connection:
            cursor = connection.execute("DELETE FROM initiatives WHERE slug = ?", (slug,))
            connection.commit()
            return cursor.rowcount > 0

    return _with_write_retry(operation)


def list_agents_config() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM agents_config ORDER BY name").fetchall()
    agents: list[dict[str, Any]] = []
    for row in rows:
        agent = dict(row)
        agent["specialties"] = _decode_json_array(agent.pop("specialties_json", "[]"))
        agents.append(agent)
    return agents


def get_system_settings() -> dict[str, str]:
    with _connect() as connection:
        rows = connection.execute("SELECT key, value FROM system_settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def _report_status(job: dict[str, Any] | None) -> str:
    if not job:
        return "missing"
    if job["status"] == "succeeded":
        return "ready"
    if job["status"] in {"queued", "running", "cancel_requested"}:
        return "pending"
    return "attention"


def _quality_gate_status(job: dict[str, Any] | None) -> str:
    if not job:
        return "unknown"
    phases = job.get("phases", {})
    if phases.get("07_static_qa") == "passed" and phases.get("10_security_audit") == "passed":
        return "passed"
    if job.get("status") == "failed":
        return "failed"
    return "pending"
