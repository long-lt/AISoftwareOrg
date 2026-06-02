# PLAN NÂNG CẤP AISoftwareOrg

## 1. Mục tiêu

Biến `AISoftwareOrg` thành một hệ thống **AI Software Factory** có khả năng:

* Tạo project/app từ mô tả tự nhiên.
* Điều phối nhiều AI Agent theo pipeline rõ ràng.
* Tự sinh tài liệu, source code, backend, frontend, checklist release.
* Có dashboard quản lý project, job, agent, model, chi phí token.
* Có queue xử lý background ổn định.
* Có bảo mật cơ bản để deploy online.
* Có CI/CD, test, lint và quy trình vận hành rõ ràng.

---

# PHASE 0 — Chuẩn hóa nền tảng repo

## Mục tiêu

Làm repo rõ ràng, dễ chạy, dễ cho AI Agent/Codex/Claude tiếp tục phát triển.

## Việc cần làm

### 0.1. Sửa README

* Đổi toàn bộ link `file:///Users/...` thành relative path.
* Thêm mục `Current Status`.
* Thêm mục `Quick Start`.
* Thêm mục `Architecture`.
* Thêm mục `Known Limitations`.
* Thêm mục `Roadmap`.

### 0.2. Thêm file cấu hình chuẩn

Cần có các file:

```text
.env.example
.gitignore
docker-compose.yml
Makefile
pyproject.toml
pytest.ini
README.md
CLAUDE.md
docs/architecture.md
docs/api_contract.md
docs/development_guide.md
docs/deployment_guide.md
docs/agent_workflow.md
```

### 0.3. Chuẩn hóa thư mục

Cấu trúc đề xuất:

```text
AISoftwareOrg/
├── agents/
│   ├── software_org/
│   └── flutter_factory/
├── config/
├── core/
├── dashboard/
│   ├── routers/
│   ├── services/
│   ├── schemas/
│   ├── database.py
│   ├── queue_manager.py
│   └── app.py
├── frontend/
├── memory/
├── system/
├── workflows/
├── workspace/
├── tests/
├── docs/
├── scripts/
├── .github/workflows/
└── README.md
```

## Kết quả cần đạt

* Người khác clone repo có thể hiểu và chạy được.
* AI Agent đọc repo không bị lạc.
* Tài liệu khớp với code thật.

---

# PHASE 1 — Fix lỗi P0: Security, Config, Queue

## Mục tiêu

Sửa các lỗi nguy hiểm trước khi phát triển thêm.

---

## 1.1. Fix Authentication

### Vấn đề hiện tại

Endpoint `/api/auth/token` chỉ cần truyền `team_id` là lấy được token.

### Việc cần làm

* Thêm `ADMIN_API_KEY` vào `.env`.
* Endpoint `/api/auth/token` bắt buộc header:

```text
X-Admin-Key: <ADMIN_API_KEY>
```

* Token phải có:

  * `team_id`
  * `role`
  * `iat`
  * `exp`

### API đề xuất

```http
POST /api/auth/token
```

Body:

```json
{
  "team_id": "default",
  "role": "admin"
}
```

Header:

```text
X-Admin-Key: xxx
```

Response:

```json
{
  "token": "...",
  "team_id": "default",
  "role": "admin",
  "expires_in": 86400
}
```

---

## 1.2. Bắt buộc secret khi production

### Việc cần làm

Trong `dashboard/app.py`:

* Nếu `APP_ENV=production` mà không có `DASHBOARD_SECRET` thì raise error.
* Không cho dùng default `dev-secret-change-me` trong production.

---

## 1.3. Fix đường dẫn `rules.yaml`

### Vấn đề

`orchestrator.py` đang tìm sai path config.

### Fix

Thay logic đọc config bằng `AppSettings`.

Thêm vào `config/settings.py`:

```python
max_repair_attempts: int = Field(default=2, alias="MAX_REPAIR_ATTEMPTS")
```

Trong orchestrator dùng:

```python
from config.settings import AppSettings

def _configured_max_repair_attempts() -> int:
    return AppSettings().max_repair_attempts
```

---

## 1.4. Fix cancel job

### Vấn đề

Cancel hiện chỉ update DB, thread vẫn chạy.

### Việc cần làm

Thêm cột vào bảng `jobs`:

```sql
cancel_requested INTEGER DEFAULT 0
```

Khi gọi:

```http
POST /api/jobs/{slug}/cancel
```

Thay vì chỉ set `status=cancelled`, set:

```text
cancel_requested = 1
```

Trong mỗi phase pipeline, check:

```python
if is_cancel_requested(slug):
    raise JobCancelledError()
```

### Kết quả

* User bấm cancel thì job dừng thật.
* Không sinh file tiếp sau khi cancel.

---

## 1.5. Fix SQLite concurrency

### Việc cần làm

Trong `_connect()` thêm:

```python
connection.execute("PRAGMA journal_mode=WAL")
connection.execute("PRAGMA busy_timeout=5000")
```

Thêm retry khi ghi DB.

---

# PHASE 2 — Chuẩn hóa Job System

## Mục tiêu

Biến hệ thống job thành nền tảng ổn định để dashboard theo dõi được.

---

## 2.1. Chuẩn hóa trạng thái job

Trạng thái chuẩn:

```text
queued
running
cancel_requested
cancelled
failed
succeeded
```

---

## 2.2. Thêm bảng `job_phases`

Schema:

```sql
CREATE TABLE IF NOT EXISTS job_phases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_slug TEXT NOT NULL,
  phase TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  error TEXT,
  output_path TEXT
);
```

Phase status:

```text
pending
running
passed
failed
skipped
cancelled
```

---

## 2.3. Lưu progress thật vào database

Hiện tại phase đang suy ra từ file. Cần chuyển sang DB.

Mỗi phase khi chạy:

```python
start_phase(slug, "ba")
...
finish_phase(slug, "ba", "passed")
```

Nếu lỗi:

```python
finish_phase(slug, "ba", "failed", error=str(error))
```

---

## 2.4. Tạo worker riêng

Thêm file:

```text
dashboard/worker.py
```

Chạy worker:

```bash
python -m dashboard.worker
```

Nếu dùng RQ:

```bash
rq worker flutter_ai_factory
```

---

# PHASE 3 — Nâng cấp Agent Pipeline

```
phase3_agent_pipeline.md
```

---

# PHASE 4 — Dashboard Frontend

## Mục tiêu

Xây dashboard quản trị thật sự dùng được.

---

## 4.1. Công nghệ đề xuất

Nên dùng:

```text
React + Vite + TypeScript + Tailwind + Zustand + TanStack Query
```

Không nên tiếp tục Vanilla JS nếu dashboard sẽ lớn.

---

## 4.2. Các màn hình cần có

### 1. Overview Dashboard

Hiển thị:

* Tổng số project.
* Tổng số job.
* Job đang chạy.
* Job lỗi.
* Chi phí token hôm nay.
* Agent đang active.
* Queue status.

---

### 2. Projects

Hiển thị danh sách project/app đã tạo.

Thông tin:

* Name
* Slug
* Status
* Health
* Build progress
* Repository
* Created date

---

### 3. Create App Job

Form tạo app:

```text
App name
Description
Platform
Style
Backend option
Features
Model preset
Max repair attempts
```

---

### 4. Job Detail

Hiển thị:

* Thông tin job.
* Timeline 12 phase.
* Logs.
* File tree.
* Preview source.
* Download zip.
* Cancel job.

---

### 5. Agents

Hiển thị danh sách agent:

* Name
* Type
* Model
* System prompt
* Status
* Token usage
* Last run

Cho phép edit:

* Model
* Prompt
* Enable/disable

---

### 6. Providers

Quản lý LLM providers:

* OpenRouter
* OpenAI
* Gemini
* Ollama
* Local model

Thông tin:

* Provider name
* Base URL
* Active model
* API key status
* Cost estimate

---

### 7. Costs

Hiển thị:

* Cost theo ngày.
* Cost theo agent.
* Cost theo job.
* Token input/output.
* Model nào tốn nhất.

---

### 8. HITL Queue

Human-in-the-loop approval:

* Agent suggestion.
* Memory proposal.
* Checkpoint approval.
* Approve / Reject.
* Comment.

---

### 9. Settings

Cấu hình:

* Daily cost limit.
* Default model.
* Max repair attempts.
* Queue backend.
* Dashboard secret status.
* Redis status.

---

# PHASE 5 — Backend API Contract

## Mục tiêu

Chuẩn hóa API để frontend và agent dùng ổn định.

---

## API cần có

### Auth

```http
POST /api/auth/token
GET /api/auth/me
```

### Jobs

```http
GET /api/jobs
POST /api/jobs
GET /api/jobs/{slug}
DELETE /api/jobs/{slug}
POST /api/jobs/{slug}/cancel
GET /api/jobs/{slug}/phases
GET /api/jobs/{slug}/logs
GET /api/jobs/{slug}/download
GET /api/jobs/{slug}/code/tree
GET /api/jobs/{slug}/code/file?path=
```

### Projects

```http
GET /api/projects
POST /api/projects
GET /api/projects/{slug}
PATCH /api/projects/{slug}
DELETE /api/projects/{slug}
```

### Agents

```http
GET /api/agents
GET /api/agents/{agent_id}
PATCH /api/agents/{agent_id}
POST /api/agents/{agent_id}/test
```

### Providers

```http
GET /api/providers
POST /api/providers
PATCH /api/providers/{provider_id}
POST /api/providers/{provider_id}/test
```

### Costs

```http
GET /api/costs
GET /api/costs/summary
GET /api/costs/by-agent
GET /api/costs/by-job
```

### HITL

```http
GET /api/hitl/queue
POST /api/hitl/{id}/approve
POST /api/hitl/{id}/reject
```

### System

```http
GET /health
GET /ready
GET /api/system/status
GET /api/system/settings
PATCH /api/system/settings
```

---

# PHASE 6 — Testing & CI/CD

## Mục tiêu

Mỗi lần push code phải biết repo còn chạy được hay không.

---

## 6.1. Thêm test backend

Thư mục:

```text
tests/
├── test_health.py
├── test_auth.py
├── test_jobs.py
├── test_database.py
├── test_queue.py
└── test_pipeline.py
```

---

## 6.2. Thêm lint/type check

Dùng:

```text
ruff
pytest
mypy hoặc pyright
```

Thêm vào `pyproject.toml`.

---

## 6.3. GitHub Actions

File:

```text
.github/workflows/ci.yml
```

Pipeline:

```text
checkout
setup-python
install dependencies
ruff check
pytest
setup-node
npm install
npm run build
```

---

# PHASE 7 — Deployment

## Mục tiêu

Deploy được bản dashboard online.

---

## 7.1. Local Docker

Cần có:

```text
Dockerfile
docker-compose.yml
```

Services:

```text
api
worker
redis
```

---

## 7.2. Production options

Ưu tiên deploy:

```text
Option 1: VPS + Docker Compose
Option 2: Railway / Render
Option 3: Fly.io
Option 4: Cloudflare Pages frontend + backend riêng
```

Khuyến nghị tốt nhất: **VPS + Docker Compose**, vì hệ thống cần worker, Redis, file workspace.

---

# PHASE 8 — Agent Memory & Project Dashboard Rule

## Mục tiêu

Mỗi khi AI Agent làm dự án nào cũng phải:

* Tạo plan.
* Tạo task.
* Update dashboard.
* Ghi log.
* Ghi decision.
* Ghi trạng thái job.

---

## Rule bắt buộc cho agent

Thêm vào `CLAUDE.md` hoặc `.hermes/agents/global_rules.md`:

```md
# Mandatory Project Workflow Rule

For every project or feature request, the agent must:

1. Create or update a project record in the dashboard.
2. Create a project plan before modifying code.
3. Break the plan into actionable tasks.
4. Update task status after each completed step.
5. Log important decisions into project memory.
6. Never perform large code changes without updating the dashboard.
7. At the end of the task, write a final implementation report.
```

---

# PHASE 9 — Ưu tiên triển khai

## Sprint 1

* Fix README.
* Thêm `.env.example`.
* Fix auth.
* Fix production secret.
* Fix `max_repair_attempts`.
* Fix SQLite WAL.
* Thêm test health/auth/jobs.
* Thêm GitHub Actions.

## Sprint 2

* Thêm bảng `job_phases`.
* Thêm cancel token.
* Tách worker.
* Chuẩn hóa phase progress.
* Thêm API logs.

## Sprint 3

* Nâng cấp frontend sang React + TypeScript.
* Làm màn Jobs.
* Làm Job Detail.
* Làm Agents.
* Làm Providers.

## Sprint 4

* Hoàn thiện cost tracking.
* HITL queue.
* Provider testing.
* Deployment Docker.

## Sprint 5

* Agent memory.
* Dashboard rule.
* Project automation.
* CI/CD production.

---

# Definition of Done

Repo được xem là đạt MVP khi:

* Clone về chạy được bằng README.
* Có `.env.example`.
* Backend chạy được.
* Frontend build được.
* Tạo job được.
* Job chạy qua pipeline.
* Xem được phase progress.
* Cancel job dừng thật.
* Download được source zip.
* Có auth bảo vệ API.
* Có test tối thiểu.
* Có CI chạy khi push.
* Có Docker deploy local.
* Dashboard hiển thị project, jobs, agents, providers, costs.

---

# Kết luận

Ưu tiên tốt nhất là không làm dashboard đẹp ngay. Trước tiên phải sửa nền:

1. Auth.
2. Queue.
3. Job phase.
4. Config.
5. Test.
6. CI.

Sau khi lõi chạy ổn mới nâng dashboard UI và mở rộng agent workflow.
