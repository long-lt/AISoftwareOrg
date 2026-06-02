# PHASE 3 — Upgrade Agent Pipeline

## Objective

Upgrade the current 12-phase AI Agent pipeline into a reliable, observable, and quality-controlled software generation workflow.

The goal of this phase is to make the pipeline truly useful in real development scenarios by ensuring that each agent has a clear responsibility, produces deterministic outputs, writes structured artifacts, updates job progress, supports repair loops, validates generated code, and exports a clean handoff package.

This phase focuses on five major improvements:

1. Standardize the 12 pipeline phases.
2. Define clear input and output contracts for every phase.
3. Add quality gates between critical phases.
4. Improve repair and validation behavior.
5. Produce a complete export package for generated projects.

---

# 3.1 Standardize the 12 Pipeline Phases

## Target Phase List

```text
01_create_brief
02_business_analysis
03_backend_design
04_architecture_design
05_uiux_design
06_flutter_dev
07_static_qa
08_refactor_repair
09_runtime_test
10_security_audit
11_release_review
12_export_package
```

Each phase must be treated as a first-class pipeline step with:

* Unique phase ID
* Display name
* Assigned agent
* Required input files
* Required output files
* Start status
* End status
* Error message, if failed
* Quality gate result
* Logs
* Timestamp metadata

---

# 3.2 Global Pipeline Rules

## Every Phase Must Follow This Lifecycle

Each phase should execute with the same lifecycle:

```text
pending -> running -> passed
pending -> running -> failed
pending -> skipped
running -> cancelled
```

## Required Phase Metadata

Each phase should record:

```json
{
  "job_slug": "pantry-saver",
  "phase": "02_business_analysis",
  "status": "passed",
  "started_at": "2026-06-02T10:00:00Z",
  "finished_at": "2026-06-02T10:01:30Z",
  "agent": "ba_agent",
  "input_files": [],
  "output_files": [],
  "error": null
}
```

## Required Phase Behavior

Before running a phase, the pipeline must:

1. Check whether the job has been cancelled.
2. Mark the phase as `running`.
3. Validate required input files.
4. Execute the assigned agent.
5. Validate required output files.
6. Run phase-specific quality checks.
7. Mark the phase as `passed` or `failed`.
8. Write phase logs.
9. Update the dashboard state.

---

# 3.3 Phase Detail Plan

---

## Phase 01 — `01_create_brief`

## Purpose

Convert the raw user request into a structured project brief.

This phase creates the foundation for the entire generation process. It must capture the app idea, target platform, feature list, design style, backend preference, and generation constraints.

## Assigned Agent

```text
brief_agent
```

or existing:

```text
planner_agent
```

## Inputs

```text
User prompt
Job payload
Selected platform
Selected style
Selected backend option
Feature list
```

## Required Outputs

```text
docs/input.json
docs/app_brief.md
docs/project_context.md
docs/initial_constraints.md
```

## Output Description

### `docs/input.json`

Stores the original normalized job request.

### `docs/app_brief.md`

Human-readable summary of the app.

### `docs/project_context.md`

Explains the product background, target users, use cases, and assumptions.

### `docs/initial_constraints.md`

Stores technical and business constraints.

## Quality Gate

This phase passes only if:

* `input.json` exists.
* `app_brief.md` exists.
* App name is not empty.
* Description is not empty.
* Feature list is not empty.
* Target platform is valid.

## Failure Handling

If this phase fails, the pipeline must stop immediately because all later phases depend on the brief.

---

## Phase 02 — `02_business_analysis`

## Purpose

Transform the project brief into a complete business and product specification.

This phase defines what the application must do, who it is for, and how success will be measured.

## Assigned Agent

```text
ba_agent
```

## Inputs

```text
docs/input.json
docs/app_brief.md
docs/project_context.md
docs/initial_constraints.md
```

## Required Outputs

```text
docs/requirements.md
docs/user_stories.md
docs/feature_list.md
docs/acceptance_criteria.md
docs/product_spec.json
docs/non_functional_requirements.md
```

## Output Description

### `docs/requirements.md`

Functional requirements grouped by module.

### `docs/user_stories.md`

User stories in this format:

```text
As a [user type], I want to [action], so that [benefit].
```

### `docs/feature_list.md`

Prioritized feature list:

```text
P0 — Required for MVP
P1 — Important
P2 — Nice to have
```

### `docs/acceptance_criteria.md`

Clear testable conditions for every P0 feature.

### `docs/product_spec.json`

Machine-readable product specification used by later agents.

### `docs/non_functional_requirements.md`

Performance, security, accessibility, localization, offline, and scalability requirements.

## Quality Gate

This phase passes only if:

* Every P0 feature has acceptance criteria.
* `product_spec.json` is valid JSON.
* At least one primary user persona exists.
* At least one core user flow exists.
* No empty requirement sections exist.

## Failure Handling

If this phase fails:

* Retry once with a stricter BA prompt.
* If still failed, mark job as failed.
* Do not continue to architecture or code generation.

---

## Phase 03 — `03_backend_design`

## Purpose

Design the backend strategy, API contract, database schema, and integration model.

This phase must decide whether the generated app needs a backend and, if yes, what backend structure is required.

## Assigned Agent

```text
backend_agent
```

## Inputs

```text
docs/product_spec.json
docs/requirements.md
docs/acceptance_criteria.md
```

## Required Outputs

```text
docs/api_contract.md
docs/openapi.yaml
docs/database_schema.sql
docs/data_model.json
docs/backend_strategy.md
docs/env_contract.md
backend/
```

## Output Description

### `docs/api_contract.md`

Human-readable API contract.

### `docs/openapi.yaml`

Machine-readable OpenAPI specification.

### `docs/database_schema.sql`

SQL schema if persistence is needed.

### `docs/data_model.json`

Entity definitions and relationships.

### `docs/backend_strategy.md`

Explains backend choice:

```text
none
mock
local SQLite
Supabase
FastAPI
Firebase
custom REST API
```

### `docs/env_contract.md`

Required environment variables.

### `backend/`

Optional generated backend source code.

## Quality Gate

This phase passes only if:

* Backend decision is explicit.
* If backend is `none`, the reason is documented.
* If backend is required, API contract exists.
* If database is required, schema exists.
* OpenAPI file is valid YAML when generated.
* No secrets are hardcoded.

## Failure Handling

If backend design fails:

* Continue only if backend is optional.
* Fail if core app features require backend.

---

## Phase 04 — `04_architecture_design`

## Purpose

Design the technical architecture for the generated Flutter application.

This phase defines folder structure, state management, navigation, dependency strategy, error handling, and integration boundaries.

## Assigned Agent

```text
architect_agent
```

## Inputs

```text
docs/product_spec.json
docs/api_contract.md
docs/data_model.json
docs/backend_strategy.md
```

## Required Outputs

```text
docs/architecture.md
docs/folder_structure.md
docs/state_management.md
docs/navigation_map.md
docs/api_strategy.md
docs/database_strategy.md
docs/dependency_plan.md
```

## Output Description

### `docs/architecture.md`

High-level app architecture.

### `docs/folder_structure.md`

Target source folder structure.

### `docs/state_management.md`

Chosen state management pattern.

Recommended default:

```text
Riverpod or Provider for generated Flutter apps
```

### `docs/navigation_map.md`

Screen routing and navigation relationships.

### `docs/api_strategy.md`

How the app communicates with backend or local data.

### `docs/database_strategy.md`

Local persistence plan.

### `docs/dependency_plan.md`

Flutter package list and why each package is needed.

## Quality Gate

This phase passes only if:

* Folder structure is defined.
* State management is selected.
* Navigation map exists.
* Dependencies are justified.
* Architecture matches product requirements.
* Architecture does not over-engineer small MVP apps.

## Failure Handling

If architecture fails:

* Retry with simplified MVP architecture.
* If retry fails, stop pipeline.

---

## Phase 05 — `05_uiux_design`

## Purpose

Generate the UI/UX specification for the Flutter application.

This phase defines screens, layout behavior, design tokens, component rules, empty states, loading states, and error states.

## Assigned Agent

```text
uiux_agent
```

## Inputs

```text
docs/product_spec.json
docs/user_stories.md
docs/navigation_map.md
docs/architecture.md
```

## Required Outputs

```text
docs/design.md
docs/screen_list.md
docs/component_spec.md
docs/theme_config.dart
docs/interaction_flow.md
docs/ui_states.md
```

## Output Description

### `docs/design.md`

Overall design direction.

### `docs/screen_list.md`

All required screens with description.

### `docs/component_spec.md`

Reusable components.

### `docs/theme_config.dart`

Flutter theme tokens.

### `docs/interaction_flow.md`

User interaction flow across screens.

### `docs/ui_states.md`

Loading, empty, error, success, permission, and offline states.

## Quality Gate

This phase passes only if:

* Every P0 feature maps to at least one screen.
* Every screen has a clear purpose.
* Theme config is valid Dart.
* Empty/loading/error states are documented.
* UI spec is implementable in Flutter.

## Failure Handling

If UI/UX design fails:

* Retry with simplified screen list.
* If theme Dart fails, regenerate only `theme_config.dart`.

---

## Phase 06 — `06_flutter_dev`

## Purpose

Generate the Flutter source code based on the product, architecture, backend, and UI/UX specifications.

This is the main implementation phase.

## Assigned Agent

```text
dev_agent
```

## Inputs

```text
docs/product_spec.json
docs/architecture.md
docs/folder_structure.md
docs/state_management.md
docs/navigation_map.md
docs/design.md
docs/screen_list.md
docs/component_spec.md
docs/theme_config.dart
docs/api_contract.md
```

## Required Outputs

```text
source/pubspec.yaml
source/lib/main.dart
source/lib/app.dart
source/lib/core/
source/lib/features/
source/lib/shared/
source/test/
```

## Recommended Flutter Structure

```text
source/lib/
├── main.dart
├── app.dart
├── core/
│   ├── constants/
│   ├── errors/
│   ├── network/
│   ├── routing/
│   ├── storage/
│   └── theme/
├── shared/
│   ├── widgets/
│   ├── models/
│   └── utils/
└── features/
    └── feature_name/
        ├── data/
        ├── domain/
        └── presentation/
```

## Quality Gate

This phase passes only if:

* `pubspec.yaml` exists.
* `main.dart` exists.
* `app.dart` exists.
* All generated imports are valid.
* Required screens exist.
* No TODO-only implementation for P0 features.
* Code follows the selected architecture.

## Failure Handling

If source generation fails:

* Retry only the failed file group.
* Do not regenerate the whole app unless the structure is invalid.
* Record failed files in `docs/dev_generation_errors.md`.

---

## Phase 07 — `07_static_qa`

## Purpose

Run static validation against generated Flutter code.

This phase checks syntax, imports, formatting, static analysis, and basic test readiness.

## Assigned Agent

```text
qa_agent
```

## Inputs

```text
source/
docs/architecture.md
docs/acceptance_criteria.md
```

## Required Outputs

```text
docs/test_report.md
docs/bug_list.md
docs/static_analysis.log
docs/qa_summary.json
```

## Required Commands

Run inside `source/`:

```bash
flutter pub get
dart format --set-exit-if-changed .
flutter analyze
flutter test
```

If Flutter is not installed, fallback mode should still inspect files and mark environment limitation clearly.

## Quality Gate

This phase passes only if:

* `flutter pub get` passes.
* `flutter analyze` passes.
* Formatting passes.
* No critical missing files.
* `qa_summary.json` is valid.
* `test_report.md` contains `Status: PASS`.

## Failure Handling

If QA fails:

* Write all issues to `docs/bug_list.md`.
* Mark phase as failed.
* Continue to `08_refactor_repair`.

---

## Phase 08 — `08_refactor_repair`

## Purpose

Repair generated code based on QA results.

This phase should not blindly rewrite the whole project. It should apply targeted fixes based on the bug list.

## Assigned Agent

```text
refactor_agent
```

## Inputs

```text
docs/bug_list.md
docs/test_report.md
docs/static_analysis.log
source/
```

## Required Outputs

```text
docs/refactor_report.md
docs/repair_history.md
docs/changed_files.md
source/
```

## Repair Strategy

The repair loop should:

1. Read `bug_list.md`.
2. Group issues by file.
3. Fix syntax errors first.
4. Fix missing imports.
5. Fix type errors.
6. Fix dependency errors.
7. Fix architecture violations.
8. Re-run static QA.
9. Repeat until pass or max attempts reached.

## Max Attempts

Controlled by:

```env
MAX_REPAIR_ATTEMPTS=2
```

## Quality Gate

This phase passes only if:

* Critical QA errors are resolved.
* `flutter analyze` passes after repair.
* `repair_history.md` exists.
* Repair attempts do not exceed limit.
* No unrelated mass rewrite occurs.

## Failure Handling

If repair fails:

* Keep the latest source.
* Mark job as failed.
* Write final failure reason.
* Do not proceed to runtime test.

---

## Phase 09 — `09_runtime_test`

## Purpose

Run basic runtime verification for the generated app.

This phase checks whether the app can start and whether the primary screens/routes are wired correctly.

## Assigned Agent

```text
runtime_agent
```

## Inputs

```text
source/
docs/navigation_map.md
docs/screen_list.md
docs/acceptance_criteria.md
```

## Required Outputs

```text
docs/runtime_report.md
docs/runtime_smoke.log
docs/runtime_summary.json
```

## Runtime Checks

Recommended commands:

```bash
flutter build web
flutter test
```

Optional:

```bash
flutter run -d chrome
```

For CI/headless mode, prefer:

```bash
flutter build web
```

## Quality Gate

This phase passes only if:

* App builds successfully.
* Main entrypoint works.
* No fatal runtime configuration error.
* Required routes are registered.
* Runtime report contains `Status: PASS`.

## Failure Handling

If runtime fails:

* Send runtime errors back to repair phase if attempts remain.
* If no attempts remain, fail the job.

---

## Phase 10 — `10_security_audit`

## Purpose

Review generated project for basic security, privacy, and deployment risks.

This phase does not need to be a full enterprise audit, but it must catch common mistakes before handoff.

## Assigned Agent

```text
security_agent
```

## Inputs

```text
source/
backend/
docs/api_contract.md
docs/env_contract.md
docs/database_schema.sql
```

## Required Outputs

```text
docs/security_report.md
docs/privacy_review.md
docs/deployment_plan.md
docs/production_release_checklist.md
```

## Security Checks

Must check:

* No hardcoded API keys.
* No committed secrets.
* No insecure default credentials.
* No dangerous file access.
* No excessive permissions.
* Safe API URL handling.
* Safe local storage usage.
* Basic input validation.
* Backend CORS configuration, if backend exists.
* Environment variables documented.

## Quality Gate

This phase passes only if:

* No critical security issue exists.
* All secrets are moved to env.
* Deployment checklist exists.
* `security_report.md` contains `Status: PASS`.

## Failure Handling

If critical security issues exist:

* Return to repair phase if fixable.
* Otherwise fail the job.

---

## Phase 11 — `11_release_review`

## Purpose

Perform final review before packaging the generated project.

This phase acts as the release manager. It checks whether the generated project is complete enough for MVP handoff.

## Assigned Agent

```text
reviewer_agent
```

## Inputs

```text
docs/test_report.md
docs/runtime_report.md
docs/security_report.md
docs/requirements.md
docs/acceptance_criteria.md
source/
backend/
```

## Required Outputs

```text
docs/final_review.md
docs/release_checklist.md
docs/handoff_notes.md
```

## Review Criteria

The reviewer must verify:

* P0 features are implemented.
* Main screens exist.
* Static QA passed.
* Runtime test passed.
* Security audit passed.
* Export package can be created.
* Known limitations are documented.
* Setup instructions are clear.

## Quality Gate

This phase passes only if:

```text
final_review.md contains:
Status: READY_FOR_MVP_HANDOFF
```

If not ready:

```text
Status: NOT_READY
```

## Failure Handling

If release review fails:

* If issues are fixable, return to repair phase.
* If issues are product-scope related, fail job and document reason.

---

## Phase 12 — `12_export_package`

## Purpose

Create a clean, downloadable source package for the generated project.

This is the final delivery step.

## Assigned Agent

```text
export_agent
```

or pipeline utility function:

```text
export_source_archive()
```

## Inputs

```text
source/
backend/
docs/
docs/final_review.md
docs/release_checklist.md
```

## Required Outputs

```text
exports/{slug}_source.zip
docs/export_report.md
```

## Export Package Must Include

```text
source/
backend/
docs/
README.md
.env.example
```

## Export Package Must Exclude

```text
.git/
.dart_tool/
build/
node_modules/
.env
*.log
.DS_Store
.idea/
.vscode/
```

## Quality Gate

This phase passes only if:

* Zip file exists.
* Zip file is not empty.
* Source directory is included.
* Required docs are included.
* Secrets are excluded.
* `export_report.md` exists.

## Failure Handling

If export fails:

* Mark job as failed.
* Keep generated source for debugging.
* Write error to `docs/export_report.md`.

---

# 3.4 Pipeline Control Flow

## Normal Flow

```text
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

## Repair Flow

```text
07_static_qa FAIL
  -> 08_refactor_repair
  -> 07_static_qa again
```

## Runtime Failure Flow

```text
09_runtime_test FAIL
  -> 08_refactor_repair
  -> 07_static_qa
  -> 09_runtime_test again
```

## Security Failure Flow

```text
10_security_audit FAIL
  -> 08_refactor_repair
  -> 07_static_qa
  -> 09_runtime_test
  -> 10_security_audit again
```

## Final Failure Flow

```text
Max repair attempts reached
  -> mark job as failed
  -> write failure report
  -> keep workspace files
```

---

# 3.5 Required Database Changes

## Add `job_phases` Table

```sql
CREATE TABLE IF NOT EXISTS job_phases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_slug TEXT NOT NULL,
  phase TEXT NOT NULL,
  agent TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  input_files_json TEXT,
  output_files_json TEXT,
  error TEXT,
  logs_path TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

## Add `job_logs` Table

```sql
CREATE TABLE IF NOT EXISTS job_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_slug TEXT NOT NULL,
  phase TEXT,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

## Add `jobs` Columns

```sql
ALTER TABLE jobs ADD COLUMN current_phase TEXT;
ALTER TABLE jobs ADD COLUMN progress INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER DEFAULT 0;
```

---

# 3.6 Required Backend Services

Create:

```text
dashboard/services/pipeline_service.py
dashboard/services/phase_service.py
dashboard/services/job_log_service.py
dashboard/services/artifact_service.py
```

## `phase_service.py`

Responsibilities:

* Start phase
* Finish phase
* Fail phase
* Skip phase
* Get phase list
* Validate phase outputs

## `pipeline_service.py`

Responsibilities:

* Run full pipeline
* Control repair loop
* Check cancellation
* Manage max repair attempts
* Update job progress

## `job_log_service.py`

Responsibilities:

* Write structured logs
* Tail logs for dashboard
* Filter logs by phase

## `artifact_service.py`

Responsibilities:

* Validate output files
* Package export zip
* Prevent unsafe file access

---

# 3.7 Required API Updates

## Get Job Phases

```http
GET /api/jobs/{slug}/phases
```

Response:

```json
[
  {
    "phase": "01_create_brief",
    "agent": "brief_agent",
    "status": "passed",
    "started_at": "...",
    "finished_at": "...",
    "error": null
  }
]
```

## Get Job Logs

```http
GET /api/jobs/{slug}/logs
```

Query:

```text
?phase=07_static_qa&level=error
```

## Retry Job Phase

```http
POST /api/jobs/{slug}/phases/{phase}/retry
```

Only allowed for failed phases.

## Cancel Job

```http
POST /api/jobs/{slug}/cancel
```

Must set:

```text
cancel_requested = 1
```

The running pipeline must detect cancellation before starting each phase.

---

# 3.8 Implementation Plan

## Step 1 — Define Phase Registry

Create:

```text
workflows/phase_registry.py
```

Example:

```python
PIPELINE_PHASES = [
    {
        "id": "01_create_brief",
        "name": "Create Project Brief",
        "agent": "brief_agent",
        "required_inputs": [],
        "required_outputs": [
            "docs/input.json",
            "docs/app_brief.md",
            "docs/project_context.md",
            "docs/initial_constraints.md",
        ],
    },
    {
        "id": "02_business_analysis",
        "name": "Business Analysis",
        "agent": "ba_agent",
        "required_inputs": [
            "docs/app_brief.md",
            "docs/project_context.md",
        ],
        "required_outputs": [
            "docs/requirements.md",
            "docs/user_stories.md",
            "docs/acceptance_criteria.md",
            "docs/product_spec.json",
        ],
    },
]
```

---

## Step 2 — Add Phase Service

Create helper functions:

```python
start_phase(job_slug, phase_id)
pass_phase(job_slug, phase_id, output_files)
fail_phase(job_slug, phase_id, error)
skip_phase(job_slug, phase_id, reason)
```

---

## Step 3 — Add Output Validation

Create:

```text
workflows/validators.py
```

Validation examples:

```python
validate_required_files(app_dir, required_outputs)
validate_json_file(path)
validate_yaml_file(path)
validate_dart_file(path)
validate_markdown_status(path)
```

---

## Step 4 — Refactor Pipeline Runner

Replace direct sequential calls with phase executor:

```python
run_phase("01_create_brief", create_brief)
run_phase("02_business_analysis", write_ba_documents)
run_phase("03_backend_design", write_backend_source)
...
```

Each `run_phase()` should:

1. Check cancellation.
2. Start phase.
3. Run agent.
4. Validate outputs.
5. Mark phase passed or failed.
6. Write logs.

---

## Step 5 — Add Repair Controller

Create repair controller:

```python
run_repair_loop(job_slug, app_input, app_dir)
```

Responsibilities:

* Run static QA.
* If fail, run repair.
* Re-run QA.
* Stop after `MAX_REPAIR_ATTEMPTS`.
* Write `repair_history.md`.
* Return final status.

---

## Step 6 — Add Runtime and Security Feedback Loops

If runtime or security fails, the pipeline should route back to repair when possible.

Example:

```text
runtime failed -> repair -> static QA -> runtime
security failed -> repair -> static QA -> runtime -> security
```

---

## Step 7 — Update Export Logic

Ensure export package includes:

```text
source/
backend/
docs/
README.md
.env.example
```

Exclude unsafe files:

```text
.env
.git/
build/
.dart_tool/
node_modules/
*.log
```

---

## Step 8 — Add Tests

Create tests:

```text
tests/test_phase_registry.py
tests/test_phase_service.py
tests/test_pipeline_runner.py
tests/test_repair_loop.py
tests/test_export_package.py
```

Test cases:

* Phase registry has exactly 12 phases.
* Each phase has required outputs.
* Missing output causes phase failure.
* Cancelled job stops before next phase.
* Failed QA triggers repair.
* Max repair attempts stops loop.
* Export excludes secrets.
* Successful pipeline creates zip.

---

# 3.9 Acceptance Criteria

Phase 3 is complete when:

* Pipeline has exactly 12 standardized phases.
* Every phase is recorded in DB.
* Dashboard can display phase progress.
* Each phase has required input/output contracts.
* Static QA can trigger repair loop.
* Runtime failure can trigger repair when possible.
* Security failure can trigger repair when possible.
* Job cancellation stops the pipeline.
* Export zip is created only after all quality gates pass.
* Tests cover phase registry, phase service, repair loop, and export logic.
* Documentation is updated.

---

# 3.10 Recommended Commit Plan

## Commit 1

```text
docs: define standardized 12-phase agent pipeline
```

## Commit 2

```text
feat: add pipeline phase registry
```

## Commit 3

```text
feat: persist job phase progress and logs
```

## Commit 4

```text
feat: add phase executor with output validation
```

## Commit 5

```text
feat: improve repair loop controller
```

## Commit 6

```text
feat: add runtime and security feedback loops
```

## Commit 7

```text
feat: harden export package generation
```

## Commit 8

```text
test: add pipeline phase and export tests
```

## Commit 9

```text
docs: update agent workflow and development guide
```

---

# 3.11 Final Expected Result

After completing Phase 3, the system should be able to:

1. Accept an app generation request.
2. Create a normalized project brief.
3. Generate business requirements.
4. Design backend/API strategy.
5. Design app architecture.
6. Generate UI/UX specifications.
7. Generate Flutter source code.
8. Run static QA.
9. Repair failed code automatically.
10. Run runtime verification.
11. Run security audit.
12. Review readiness for MVP handoff.
13. Export a clean source zip.
14. Show full progress on the dashboard.
15. Stop safely if cancelled.
16. Fail clearly with useful error reports if quality gates are not met.
