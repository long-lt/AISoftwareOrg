# Agent Workflow Reference

Tài liệu tham khảo về các AI Agents và pipeline workflows.

---

## Tổng quan

Hệ thống có 2 nhóm agents:

| Team | Agents | Type | Purpose |
|---|---|---|---|
| `software_org` | 7 | Class-based (BaseAgent) | General software development |
| `flutter_factory` | 10 | Functional modules | Flutter app generation |

---

## Base Class: `BaseAgent`

Tất cả class-based agents kế thừa từ `BaseAgent`:

```python
class BaseAgent:
    name: str
    role: str

    def validate_permission(action: str) -> None  # RBAC check
    async def run(task: AgentTask) -> AgentResult   # Abstract
```

**Input/Output models:**
- `AgentTask` — id, description, context (optional)
- `AgentResult` — success (bool), output (str), reason (optional)

---

## Team: software_org

### PMAgent (Product Manager)

**Input:** Yêu cầu thô từ stakeholder
**Output:** JSON spec với:
- Feature name, one-line summary
- Assumptions cho các điểm mơ hồ
- Acceptance criteria (GIVEN/WHEN/THEN)
- Task list với dependencies
- Out-of-scope items

### PlannerAgent (Software Architect)

**Input:** PM spec JSON
**Output:** Technical plan:
- Architecture pattern
- Tech stack (language, framework, DB, libs)
- Data models với field definitions
- Dev tasks với implementation notes

### DevAgent (Backend Developer)

**Input:** Task description
**Output:** Python source code

2 modes:
- **Initial mode**: Tạo code mới (type hints, docstrings, error handling, validation)
- **Fix mode**: Sửa code dựa trên QA failures hoặc reviewer rejection

Supports skill injection qua `SkillRegistry`.

### QAAgent (QA Engineer)

**Input:** Production code
**Output:** Test results

Quy trình:
1. Generate test code (≥3 test cases: happy path, edge, error)
2. Run tests trong sandbox (local hoặc Docker)
3. Parse pass/fail results

### ReviewerAgent (Senior Engineer)

**Input:** Source code
**Output:** `APPROVED` hoặc `REJECTED` với reasons

Checklist: correctness, error handling, input validation, security, code quality. Default to rejected on API failure.

### GitAgent (DevOps)

**Input:** Code + task ID
**Output:** Local git branch + commit

Tạo branch `ai-agent/<task_id>`, write files, stage, commit. Không auto-push.

### DevOpsAgent (DevOps Engineer)

**Input:** Deploy request
**Output:** Deployment result

`deploy()` method yêu cầu CRITICAL permission.

---

## Team: flutter_factory

Tất cả agents là **functional modules** (không class, chỉ functions).

### BA Agent

**Function:** `write_ba_documents(app_input, output_dir)`
**Outputs:**
- `requirements.md` — Functional requirements
- `user_stories.md` — User stories
- `feature_list.md` — Feature inventory
- `acceptance_criteria.md` — Acceptance criteria
- `product_spec.json` — Product specification (structured)
- `data_model.json` — Data model definition
- `user_flows.md` — User flow descriptions
- `acceptance_tests.md` — Test scenarios
- `non_functional_requirements.md` — Performance, security, etc.

### Architect Agent

**Function:** `write_architect_documents(app_input, output_dir)`
**Outputs:**
- `architecture.md` — Clean Architecture, feature-first
- `folder_structure.md` — lib/ tree (data/domain/presentation per feature)
- `state_management.md` — Cubit-based với flutter_bloc
- `api_strategy.md` — API integration patterns
- `database_strategy.md` — Local storage strategy

### Backend Agent

**Function:** `write_backend_source(product_spec, data_model, output_dir)`
**Outputs:**
- `main.py` — FastAPI app với CRUD endpoints
- `requirements.txt` — Backend dependencies
- `database_schema.sql` — SQL schema
- Pydantic schemas, in-memory database, tests, OpenAPI YAML

### Dev Agent (Flutter)

**Function:** `write_flutter_source(app_input, architect_docs, output_dir)`
**Outputs:**
- `pubspec.yaml`, `main.dart`, `app.dart`
- `core/` — API client, config, dependencies, theme
- `shared/` — AppScaffold, FeatureCard, StateView widgets
- Per-feature: entity, model, DTO, data sources, repository, use case, cubit, screen
- Tests: widget, API client, logic, data

### QA Agent (Flutter)

**Function:** `run_qa_checks(source_dir, backend_dir)`
**Outputs:**
- `test_report.md` — File checks + command results + coverage
- `bug_list.md` — Missing files, failed commands
- `production_qa_report.md` — Quality gates

Commands run:
1. File existence verification
2. `flutter analyze`
3. `flutter test --coverage`
4. `flutter build web --release`
5. Backend tests

### Refactor Agent

**Function:** `run_refactor(source_dir, bug_list)`
**Output:** `refactor_report.md`

Quy trình: `dart format lib` → `flutter analyze` → verify fixes.

### Runtime Agent

**Function:** `run_runtime_verification(source_dir)`
**Output:** `runtime_report.md`

Checks:
1. `flutter devices --machine` — detect devices/emulators
2. `flutter build web --debug` — smoke compile test

### Security Agent

**Function:** `write_security_documents(source_dir, backend_dir, output_dir)`
**Outputs:**
- `security_report.md` — Hardcoded secrets, missing .env, timeout issues
- `deployment_plan.md` — Deployment recommendations
- `env_contract.md` — Required environment variables
- `production_release_checklist.md` — Pre-release checklist

### Reviewer Agent (Flutter)

**Function:** `write_review_documents(all_reports_dir, output_dir)`
**Outputs:**
- `final_review.md` — Aggregated review với score (0-100)
- `release_checklist.md` — Release readiness checklist

Score calculation: QA pass + Refactor pass + Runtime pass + file count.

### UI/UX Agent

**Function:** `write_uiux_documents(app_input, output_dir)`
**Outputs:**
- `design.md` — Design principles, visual system, color palette, typography
- `screen_list.md` — Screen inventory table
- `theme_config.dart` — Flutter ThemeData (Material 3)
- `component_spec.md` — Shared component specs

---

## Pipeline: Flutter MVP (12-Phase)

**File:** `agents/flutter_factory/orchestrator.py`
**Function:** `run_full_pipeline(app_input)`
**Detailed Phase 3 plan:** [`phase3_agent_pipeline.md`](phase3_agent_pipeline.md)

### Flow

```
01_create_brief
  -> 02_business_analysis
  -> 03_backend_design
  -> 04_architecture_design
  -> 05_uiux_design
  -> 06_flutter_dev
  -> 07_static_qa
  -> 08_refactor_repair
  -> 09_runtime_test
  -> 10_security_audit
  -> 11_release_review
  -> 12_export_package
```

### Phase Lifecycle

```
pending -> running -> passed
pending -> running -> failed
pending -> skipped
running -> cancelled
```

Each phase records DB progress and should include phase ID, assigned agent, required inputs, required outputs, timestamps, quality gate result, error, and logs.

### Feedback Loops

```
07_static_qa FAIL
  -> 08_refactor_repair
  -> 07_static_qa again

09_runtime_test FAIL
  -> 08_refactor_repair
  -> 07_static_qa
  -> 09_runtime_test again

10_security_audit FAIL
  -> 08_refactor_repair
  -> 07_static_qa
  -> 09_runtime_test
  -> 10_security_audit again
```

### Quality Gates

Job chỉ `succeeded` khi ALL conditions met:

| Gate | Condition |
|---|---|
| QA | `flutter analyze` PASS, tests PASS |
| Production Build | `flutter build web --release` PASS |
| Runtime | Device detected OR web build works |
| Security | No hardcoded secrets |
| Reviewer | `READY_FOR_MVP_HANDOFF` |
| Export | ZIP file created |

### Repair Loop

```
attempts = 0
max_attempts = AppSettings().max_repair_attempts  # MAX_REPAIR_ATTEMPTS

while attempts < max_attempts:
    qa_result = run_qa_checks()
    if qa_result.status == "PASS":
        break
    run_refactor(bug_list=qa_result.bug_list)
    attempts += 1
```

---

## Pipeline: Software Org (Full Pipeline)

**File:** `workflows/full_pipeline.py`

### Flow

```
[1] PMAgent → JSON spec
[2] PlannerAgent → Technical plan
[3] Per task (sequential):
    DevAgent → code
    ReviewerAgent → review
    QAAgent → tests
    Fix loop (max N attempts)
```

**Output:** `FullPipelineResult` với spec, plan, per-task results, errors.

---

## Configuration

### `config/rules.yaml`

```yaml
max_repair_attempts: 3
daily_cost_limit: 5.00
```

### Per-agent model overrides (`.env`)

```env
DEV_MODEL=gpt-4o
QA_MODEL=gpt-4o-mini
REVIEWER_MODEL=gpt-4o
```

### LLM Routing Tiers

```env
FAST_LLM_MODEL=gpt-4o-mini      # Quick tasks
MEDIUM_LLM_MODEL=gpt-4o          # Standard tasks
STRONG_LLM_MODEL=o1-preview      # Complex reasoning
```
