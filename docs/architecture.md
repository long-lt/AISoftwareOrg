# Architecture Reference

Tài liệu tham khảo kiến trúc hệ thống Unified AI Software Factory.

---

## Tổng quan

Hệ thống gồm 4 phân hệ chính, giao tiếp qua REST API và message queue:

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (Vite + Vanilla JS)               │
│                    SPA · Client-side Router · JWT Auth        │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST API (JSON)
┌──────────────────────────▼───────────────────────────────────┐
│                  Dashboard API (FastAPI)                      │
│  Auth · Jobs · Projects · Agents · Providers · HITL · Costs  │
│  SQLite (jobs, settings) · JSON (memory, approval queue)     │
└──────────────────────────┬───────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│  software_  │  │  flutter_    │  │     Core          │
│  org/       │  │  factory/    │  │  Cost · LLM ·     │
│  7 agents   │  │  10 agents   │  │  Graph · Log ·    │
│  (class)    │  │  (functions) │  │  Memory · Message │
└─────────────┘  └──────────────┘  └──────────────────┘
```

---

## Phân hệ chi tiết

### 1. Frontend (`frontend/`)

- **Stack**: Vite + Vanilla JavaScript (SPA)
- **Routing**: Client-side router tại `src/js/router.js`
- **API Client**: `src/js/api.js` — tự động đính kèm JWT, polling mỗi 5s
- **Build**: `npm run build` → `frontend/dist/` (FastAPI serve trực tiếp)

### 2. Dashboard API (`dashboard/`)

- **Framework**: FastAPI
- **Entry point**: `dashboard/app.py` — tạo app, register routers, mount static files
- **Routers** (7 module trong `dashboard/routers/`):
  - `auth.py` — JWT token generation
  - `jobs.py` — CRUD jobs, phase tracking, cancel, download, code browser
  - `projects.py` — CRUD project initiatives
  - `agents.py` — Agent config management, system settings
  - `providers.py` — LLM provider registry, model listing
  - `hitl.py` — Experience & checkpoint approval queue
  - `observability.py` — Tasks, agent logs, permissions, costs, KPIs
- **Database**: SQLite (`workspace/jobs.sqlite3`) — jobs, job_phases, initiatives, settings, agents_config
- **Auth**: HS256 JWT, secret từ `DASHBOARD_SECRET`, admin token issuance bảo vệ bằng `ADMIN_API_KEY`

### 3. Agents (`agents/`)

**Base class** (`agents/base.py`):
- `BaseAgent` — abstract class với `validate_permission()` (RBAC) và `run(task) -> result`
- `AgentTask` / `AgentResult` — Pydantic models cho input/output

**Team: software_org** (7 agents, class-based):
- `PMAgent` — Phân tích yêu cầu → JSON spec
- `PlannerAgent` — Spec → technical plan + data models
- `DevAgent` — Viết / sửa Python code
- `QAAgent` — Sinh test + chạy sandbox
- `ReviewerAgent` — Code review → APPROVED / REJECTED
- `GitAgent` — Git branch, commit (local)
- `DevOpsAgent` — Infrastructure, deploy (CRITICAL permission)

**Team: flutter_factory** (10 agents, functional modules):
- `ba_agent` — Business analysis documents
- `architect_agent` — Architecture, folder structure, state management
- `backend_agent` — FastAPI backend skeleton
- `dev_agent` — Full Flutter source code (Clean Architecture)
- `qa_agent` — `flutter analyze` + `flutter test` + `flutter build`
- `refactor_agent` — Auto-fix Dart issues
- `runtime_agent` — Device detection + smoke build
- `security_agent` — Security scan + deployment plan
- `reviewer_agent` — Final review + release checklist
- `uiux_agent` — Design docs + theme config
- `orchestrator.py` — Điều phối toàn bộ 12-phase pipeline

### 4. Core (`core/`)

Các module lõi, mỗi module trong thư mục riêng:
- `cost/` — Token cost tracking theo agent và task
- `graph/` — LangGraph state definitions
- `llm/` — LLM routing (fast/medium/strong tiers)
- `logging/` — Centralized structured logging (structlog)
- `memory/` — Agent memory management
- `messaging/` — Message bus (Redis pub/sub hoặc in-memory)
- `skills/` — Skill registry cho agents

### 5. Workflows (`workflows/`)

- `full_pipeline.py` — Software Org pipeline: PM → Planner → Dev/QA/Review per task
- `flutter_mvp.py` — Flutter 12-phase pipeline wrapper
- `dev_pipeline.py` — Single task: Dev → Review → QA → Fix loop

### 6. System (`system/`)

- `rbac/` — Role-Based Access Control validation
- `learning/` — ApprovalQueue (experiences) + CheckpointStore

### 7. Config (`config/`)

- `settings.py` — Pydantic BaseSettings, load từ `.env`
- `providers.py` — LLM provider registry
- `client.py` — LLM client wrapper
- `rules.yaml` — Runtime rules (max_repair_attempts, daily_cost_limit)

---

## Data Flow: Flutter 12-Phase Pipeline

```
User tạo job (POST /api/jobs)
    │
    ▼
[01] Create Brief → input.json, app_brief.md, project_context.md, initial_constraints.md
    │
    ▼
[02] BA Agent → requirements, user_stories, product_spec.json, non_functional_requirements.md
    │
    ▼
[03] Backend Agent → api_contract.md, openapi.yaml, database_schema.sql, backend_strategy.md
    │
    ▼
[04] Architect Agent → architecture.md, folder_structure.md, state_management.md, navigation_map.md
    │
    ▼
[05] UI/UX Agent → design.md, screen_list.md, component_spec.md, theme_config.dart
    │
    ▼
[06] Dev Agent → Flutter source (pubspec, main.dart, features/*, tests)
    │
    ▼
[07] Static QA → test_report.md, bug_list.md, static_analysis.log, qa_summary.json
    │       │ FAIL → [08] Refactor/Repair → [07] Static QA again
    │
    ▼
[09] Runtime Test → runtime_report.md, runtime_smoke.log, runtime_summary.json
    │       │ FAIL → [08] Refactor/Repair → [07] Static QA → [09] Runtime Test
    │
    ▼
[10] Security Audit → security_report.md, privacy_review.md, deployment_plan.md
    │       │ FAIL → [08] Refactor/Repair → QA/runtime/security loop
    │
    ▼
[11] Release Review → final_review.md, release_checklist.md, handoff_notes.md
    │
    ▼
[12] Export Package → {slug}_source.zip, export_report.md
    │
    ▼
Quality Gate Check:
    │   QA = PASS? Production Build = PASS? Runtime = PASS?
    │   Security = PASS? Reviewer = READY_FOR_MVP_HANDOFF?
```

Phase 3 chi tiết: [`phase3_agent_pipeline.md`](phase3_agent_pipeline.md).

---

## Security Model

- **RBAC**: Mỗi agent có permission level (`READ`, `WRITE`, `EXECUTE`, `CRITICAL`)
- **JWT Auth**: Token chứa `team_id`, `role`, `iat`, `exp`
- **Production guard**: Không cho dùng default secret trong production
- **HITL**: Checkpoint interceptor tạm dừng pipeline chờ admin phê duyệt

---

## External Dependencies

| Dependency | Purpose |
|---|---|
| LangGraph | Agent orchestration framework |
| LangChain Core | LLM abstractions |
| FastAPI | Web framework |
| SQLite | Local database |
| Redis (optional) | Job queue (RQ mode) |
| OpenAI SDK | LLM API calls (OpenRouter compatible) |
| Vite | Frontend build tool |
