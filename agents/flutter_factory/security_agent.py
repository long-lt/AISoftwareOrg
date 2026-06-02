from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SecurityFinding:
    severity: str
    title: str
    detail: str


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),
]


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _iter_audited_files(source_dir: Path, backend_dir: Path) -> list[Path]:
    allowed_suffixes = {".dart", ".yaml", ".yml", ".py", ".txt", ".md", ".example"}
    excluded_parts = {".dart_tool", "build", "__pycache__", ".git"}
    files: list[Path] = []
    for root in [source_dir, backend_dir]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in excluded_parts for part in path.parts):
                continue
            if path.suffix in allowed_suffixes or path.name.endswith(".example"):
                files.append(path)
    return sorted(files)


def _scan_hardcoded_secrets(source_dir: Path, backend_dir: Path) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    for path in _iter_audited_files(source_dir, backend_dir):
        if path.name.endswith(".example"):
            continue
        text = _read_optional(path)
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(
                    SecurityFinding(
                        "BLOCKER",
                        "Hardcoded secret candidate",
                        f"`{path}` matches `{pattern.pattern}`.",
                    )
                )
                break
    return findings


def _env_findings(source_dir: Path, backend_dir: Path) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    source_env = source_dir / ".env.example"
    backend_env = backend_dir / ".env.example"
    if not source_env.exists():
        findings.append(
            SecurityFinding("BLOCKER", "Missing frontend env example", "`source/.env.example` is required.")
        )
    if not backend_env.exists():
        findings.append(
            SecurityFinding("BLOCKER", "Missing backend env example", "`backend/.env.example` is required.")
        )
    source_text = _read_optional(source_env)
    backend_text = _read_optional(backend_env)
    for key in ["API_BASE_URL", "APP_ENV", "USE_BACKEND_API"]:
        if key not in source_text:
            findings.append(SecurityFinding("WARN", "Frontend env key missing", f"`{key}` missing in source env contract."))
    for key in ["APP_ENV", "DATABASE_URL", "API_HOST", "API_PORT"]:
        if key not in backend_text:
            findings.append(SecurityFinding("WARN", "Backend env key missing", f"`{key}` missing in backend env contract."))
    return findings


def _source_security_findings(source_dir: Path, backend_dir: Path) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    api_client = _read_optional(source_dir / "lib" / "core" / "api" / "api_client.dart")
    app_config = _read_optional(source_dir / "lib" / "core" / "config" / "app_config.dart")
    backend_main = _read_optional(backend_dir / "app" / "main.py")
    backend_schemas = _read_optional(backend_dir / "app" / "schemas.py")

    if "timeout(AppConfig.requestTimeout)" not in api_client:
        findings.append(SecurityFinding("WARN", "Missing frontend request timeout", "API client should apply request timeout."))
    if "ApiException" not in api_client:
        findings.append(SecurityFinding("WARN", "Missing API error abstraction", "API client should normalize API errors."))
    if "String.fromEnvironment" not in app_config:
        findings.append(SecurityFinding("WARN", "Missing compile-time env config", "Frontend config should use dart-define."))
    if "FastAPI" not in backend_main:
        findings.append(SecurityFinding("BLOCKER", "Backend app missing", "Generated FastAPI app not found."))
    if "BaseModel" not in backend_schemas:
        findings.append(SecurityFinding("WARN", "Backend schema validation missing", "Pydantic schemas should validate request payloads."))
    if "print(" in backend_main or "console.log" in "\n".join(_read_optional(path) for path in source_dir.rglob("*.dart")):
        findings.append(SecurityFinding("WARN", "Debug logging detected", "Review logs to avoid leaking PII in production."))

    return findings


def _dependency_findings(source_dir: Path, backend_dir: Path) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    pubspec = _read_optional(source_dir / "pubspec.yaml")
    requirements = _read_optional(backend_dir / "requirements.txt")
    if "http:" not in pubspec:
        findings.append(SecurityFinding("WARN", "Frontend HTTP dependency missing", "API integration expects package:http."))
    for package in ["fastapi", "uvicorn", "pydantic"]:
        if package not in requirements:
            findings.append(SecurityFinding("WARN", "Backend dependency missing", f"`{package}` missing in backend requirements."))
    if any(marker in requirements for marker in ["==0.", "<0."]):
        findings.append(SecurityFinding("WARN", "Pinned pre-1.0 backend dependency", "Review dependency stability before production."))
    return findings


def _status(findings: list[SecurityFinding]) -> str:
    return "FAIL" if any(finding.severity == "BLOCKER" for finding in findings) else "PASS"


def _render_findings(findings: list[SecurityFinding]) -> str:
    if not findings:
        return "- Không phát hiện blocker hoặc warning tự động."
    return "\n".join(
        f"- {finding.severity}: {finding.title} - {finding.detail}" for finding in findings
    )


def _env_contract(app_input: dict[str, Any], source_dir: Path, backend_dir: Path) -> str:
    return f"""# Environment Contract: {app_input["name"]}

## Frontend

Source: `{source_dir / ".env.example"}`

| Key | Required | Purpose |
| --- | --- | --- |
| `API_BASE_URL` | Yes | Backend API base URL for generated Flutter app. |
| `APP_ENV` | Yes | Environment label: `local`, `staging`, `production`. |
| `USE_BACKEND_API` | Yes | Enables generated remote data sources. |

## Backend

Source: `{backend_dir / ".env.example"}`

| Key | Required | Purpose |
| --- | --- | --- |
| `APP_ENV` | Yes | Backend runtime environment. |
| `DATABASE_URL` | Yes | Database connection string. |
| `API_HOST` | Yes | Bind host for local/staging runtime. |
| `API_PORT` | Yes | Bind port for local/staging runtime. |

## Rules

- Secrets must be provided by the deployment platform, not committed to source.
- Production frontend builds must set `USE_BACKEND_API=true`.
- Production backend must use a managed database URL, not the local SQLite example.
"""


def _deployment_plan(app_input: dict[str, Any], source_dir: Path, backend_dir: Path) -> str:
    slug = str(app_input["slug"])
    return f"""# Deployment Plan: {app_input["name"]}

## Local Backend

```bash
cd {backend_dir}
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## Local Frontend

```bash
cd {source_dir}
flutter pub get
flutter run --dart-define=USE_BACKEND_API=true --dart-define=API_BASE_URL=http://127.0.0.1:8001
```

## Staging Build

```bash
cd {source_dir}
flutter test --coverage
flutter build web --release --dart-define=APP_ENV=staging --dart-define=USE_BACKEND_API=true --dart-define=API_BASE_URL=https://staging-api.example.com
```

## Production Build

```bash
cd {source_dir}
flutter build web --release --dart-define=APP_ENV=production --dart-define=USE_BACKEND_API=true --dart-define=API_BASE_URL=https://api.example.com
```

## Release Artifacts

- Flutter web build: `{source_dir / "build" / "web"}`
- Backend source: `{backend_dir}`
- Handoff archive: `workspace/generated_apps/{slug}/exports/{slug}_source.zip`
"""


def _release_checklist(app_input: dict[str, Any], security_status: str) -> str:
    ready = security_status == "PASS"
    return f"""# Production Release Checklist: {app_input["name"]}

## Automated Gates

- [{'x' if ready else ' '}] Security report has no blocker
- [x] Environment contract generated
- [x] Deployment plan generated
- [x] Production QA report generated before release review

## Manual Gates Before Real Production

- [ ] Replace local example URLs with staging/production URLs
- [ ] Configure managed production database
- [ ] Configure TLS and CORS policy on backend hosting
- [ ] Review auth/session/token design for apps that need accounts
- [ ] Run manual QA on target Android/iOS/Web devices
- [ ] Review app store metadata, icon, signing and privacy disclosures

## Final Status

{'READY_FOR_STAGING' if ready else 'NEEDS_SECURITY_FIX'}
"""


def write_security_documents(
    app_input: dict[str, Any],
    docs_dir: Path,
    source_dir: Path,
    backend_dir: Path,
) -> list[Path]:
    findings = [
        *_scan_hardcoded_secrets(source_dir, backend_dir),
        *_env_findings(source_dir, backend_dir),
        *_source_security_findings(source_dir, backend_dir),
        *_dependency_findings(source_dir, backend_dir),
    ]
    status = _status(findings)
    security_report = f"""# Security Report: {app_input["name"]}

## Tổng Quan

- Status: {status}
- Checked at: {datetime.now().isoformat(timespec="seconds")}
- Source: `{source_dir}`
- Backend: `{backend_dir}`

## Findings

{_render_findings(findings)}

## Review Scope

- Hardcoded secret scan for generated frontend/backend source.
- Environment contract presence.
- Frontend API timeout/error abstraction.
- Backend FastAPI/Pydantic contract presence.
- Basic dependency inventory risk.
- Debug logging scan.
"""
    output_files = {
        "security_report.md": security_report,
        "deployment_plan.md": _deployment_plan(app_input, source_dir, backend_dir),
        "env_contract.md": _env_contract(app_input, source_dir, backend_dir),
        "production_release_checklist.md": _release_checklist(app_input, status),
    }
    written_paths: list[Path] = []
    for filename, content in output_files.items():
        path = docs_dir / filename
        path.write_text(content, encoding="utf-8")
        written_paths.append(path)
    return written_paths
