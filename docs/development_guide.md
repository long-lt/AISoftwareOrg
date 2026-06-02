# Development Guide

Hướng dẫn thiết lập môi trường phát triển và đóng góp vào dự án.

---

## Yêu cầu hệ thống

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend & agents |
| Node.js | 18+ | Frontend build |
| Docker | (optional) | Redis queue |
| Flutter SDK | (optional) | QA/Runtime agents |

---

## Thiết lập môi trường

### 1. Clone & Setup

```bash
git clone <repo-url>
cd AISoftwareOrg
cp .env.example .env
# Chỉnh sửa .env — điền LLM_API_KEY
```

### 2. Quick Setup (dùng Makefile)

```bash
make setup    # Tạo venv + pip install + npm install
make dev      # Chạy backend tại http://localhost:8000
```

### 3. Manual Setup

```bash
# Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Run
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## Chạy trong Development

### Backend (FastAPI)

```bash
make dev
# Hoặc: uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

### Frontend (Vite)

```bash
make frontend
# Hoặc: cd frontend && npm run dev
```

- Dev server: http://localhost:5173
- Auto-proxy `/api/*` → http://localhost:8000

### Production Build

```bash
make build
# Sau đó truy cập http://localhost:8000 (FastAPI serve frontend/dist/)
```

### Redis (optional)

```bash
make docker-up    # docker-compose up -d
```

### Background Worker (optional)

Thread queue là default khi `JOB_QUEUE_BACKEND=thread`. Nếu dùng RQ/Redis:

```bash
python -m dashboard.worker
# Hoặc: rq worker flutter_ai_factory
```

Worker sẽ chạy generation jobs và cập nhật phase progress trong SQLite.

---

## Chạy Tests

```bash
make test              # Tất cả tests
make test-verbose      # Verbose output
make test-dashboard    # Dashboard & auth tests
make test-rbac         # RBAC tests
make test-workflow     # Pipeline tests
make test-cost         # Cost tracker tests
```

Hoặc chạy trực tiếp:

```bash
pytest
pytest tests/test_dashboard.py -v
pytest -k "test_auth" -v
```

---

## Linting

```bash
make lint        # Check
make lint-fix    # Auto-fix
```

Dùng `ruff` — config trong `pyproject.toml`.

---

## Coding Standards

### Python

- **PEP 8** — indent 4 spaces, max line 120 chars
- **Type annotations** — bắt buộc cho tất cả function params và return values
- **Pydantic models** — dùng cho API requests/responses và agent interactions
- **Error handling** — không để exception silent, luôn log và return structured error
- **Imports** — sắp xếp: stdlib → third-party → internal

### AI Agents

- **Inheritance** — mọi agent class phải inherit từ `BaseAgent`
- **RBAC** — gọi `self.validate_permission()` trước mọi action write/execute
- **Token tracking** — register prompt/response tokens qua `CostTracker`

### Frontend

- **Vanilla CSS** — không thêm UI library (Tailwind, Bootstrap)除非 được yêu cầu
- **Dark theme** — follow aesthetic hiện tại (deep navy, neon accents, glassmorphism)
- **SPA routing** — maintain client-side router trong `frontend/src/router.js`

---

## Project Structure

```
AISoftwareOrg/
├── agents/                  # AI Agent definitions
│   ├── base.py              # BaseAgent abstract class
│   ├── software_org/        # PM, Planner, Dev, QA, Reviewer, Git, DevOps
│   └── flutter_factory/     # BA, Architect, Backend, Dev, QA, Refactor, Runtime, Security, Reviewer, UI/UX
├── config/                  # Settings, providers, rules
├── core/                    # Cost, Graph, LLM, Logging, Memory, Messaging, Skills
├── dashboard/               # FastAPI backend
│   ├── app.py               # App factory
│   ├── database.py          # SQLite connection
│   ├── jwt_utils.py         # JWT encode/decode
│   ├── queue_manager.py     # Thread/RQ queue
│   └── routers/             # API route modules
├── docs/                    # Documentation
├── frontend/                # Vite + Vanilla JS SPA
├── memory/                  # Agent memory storage
├── prompts/                 # LLM prompt templates
├── sandbox/                 # Code execution sandbox
├── scripts/                 # Utility scripts
├── skills/                  # Skill registry
├── storage/                 # Local JSON storage
├── system/                  # RBAC, Learning, HITL
├── tests/                   # Test suite
├── workflows/               # Pipeline orchestration
├── workspace/               # Runtime workspace (gitignored)
├── .env.example             # Environment template
├── .gitignore
├── CLAUDE.md                # AI agent instructions
├── docker-compose.yml       # Redis container
├── Makefile                 # Dev commands
├── pyproject.toml           # Python project config
├── requirements.txt         # Python dependencies
└── run_factory.sh           # Full startup script
```

---

## Agent Pipeline Docs

- [`agent_workflow.md`](agent_workflow.md) — agent roles và pipeline overview.
- [`phase3_agent_pipeline.md`](phase3_agent_pipeline.md) — Phase 3 detailed plan: 12 standardized phases, contracts, quality gates, DB/API/service updates, tests, and acceptance criteria.
- [`project_plane.md`](project_plane.md) — roadmap tổng thể theo phase.

---

## Quy trình đóng góp

1. Tạo branch: `git checkout -b feature/my-feature`
2. Code + test
3. Chạy `make lint` và `make test`
4. Commit với message rõ ràng
5. Push và tạo Pull Request

---

## Debugging

### Backend không khởi động

```bash
# Kiểm tra .env
cat .env | head -5

# Kiểm tra dependencies
pip list | grep fastapi

# Chạy trực tiếp để xem lỗi
python -c "from dashboard.app import app; print('OK')"
```

### Frontend không kết nối API

```bash
# Kiểm tra vite proxy
cat frontend/vite.config.js

# Đảm backend đang chạy
curl http://localhost:8000/health
```

### Tests fail

```bash
# Chạy single test
pytest tests/test_dashboard.py::test_health -v

# Xem full traceback
pytest -v --tb=long
```
