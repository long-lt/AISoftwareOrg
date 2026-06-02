# Unified AI Software Factory

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**Unified AI Software Factory** is an experimental AI-powered software factory designed to automate the process of planning, generating, validating, and packaging software projects.

The project combines two complementary AI-agent systems:

1. **AISoftwareOrg** — a multi-agent software organization framework that simulates real software team roles such as Product Manager, Planner, Developer, QA, Reviewer, DevOps, and Git Agent.
2. **AI Factory Pipeline** — a modular 12-phase application generation pipeline that currently creates Flutter mobile apps and optional backend APIs from natural language requirements, with an architecture designed to support additional target platforms (React, Next.js, FastAPI, etc.) in the future.

The platform also includes a web-based dashboard for monitoring jobs, agents, generated projects, token usage, provider configuration, human-in-the-loop approvals, and build status.

---

## Project Status

This repository is currently in active development.

Some components are functional, while others are still experimental or under refinement. The current focus is to stabilize the backend, job pipeline, authentication, queue system, dashboard APIs, and generated Flutter project workflow.

Recommended current usage:

* Local experimentation
* AI-agent workflow research
* Flutter code generation experiments
* Software factory architecture prototyping
* Dashboard and automation system development

Not yet recommended for:

* Production deployment without additional hardening
* Public SaaS usage
* Handling sensitive user data
* Fully unattended enterprise workflows

---

## Core Features

### 12-Phase App Generation Pipeline

The system can generate applications through a structured software delivery workflow (currently Flutter, designed for modularity):

1. Product brief creation
2. Business analysis
3. Backend and API planning
4. Architecture design
5. UI/UX specification
6. Flutter source code generation
7. Static QA checks
8. Refactor and repair loop
9. Runtime verification
10. Security review
11. Release review
12. Source code export

---

### Multi-Agent Software Organization

The platform defines specialized AI agents for different software engineering responsibilities:

* Product Manager Agent
* Planner Agent
* Developer Agent
* QA Agent
* Reviewer Agent
* DevOps Agent
* Git Agent
* Business Analyst Agent
* Architect Agent
* UI/UX Agent
* Security Agent
* Runtime Verification Agent

Each agent is designed to focus on a specific stage of the software delivery lifecycle.

---

### Automated Repair Loop

The QA Agent can run static analysis against generated Flutter code.

If issues are detected, the bug report is passed to the Refactor Agent, which attempts to repair the generated source code. This loop can repeat until the project passes validation or reaches the configured repair attempt limit.

---

### Human-in-the-Loop Checkpoints

The system supports human approval flows for sensitive actions, generated knowledge, and critical workflow checkpoints.

This is designed to prevent fully autonomous agents from making unsafe or unwanted decisions without review.

---

### Dashboard and Monitoring

The dashboard is intended to provide visibility into:

* Active generation jobs
* Job phase progress
* Agent activity
* Provider configuration
* Token and cost usage
* Human approval queue
* Generated source files
* Downloadable project exports

---

## Repository Structure

```text
unified-ai-software-org/
├── agents/                  # AI agent definitions and role-specific logic
│   ├── software_org/        # Software organization agents
│   └── flutter_factory/     # App generation pipeline agents (Flutter module)
├── config/                  # Application settings and provider configuration
├── core/                    # Shared logging, cost tracking, and provider utilities
├── dashboard/               # FastAPI backend and dashboard API server
│   ├── routers/             # API route modules
│   ├── app.py               # FastAPI application entry point
│   ├── database.py          # SQLite persistence layer
│   ├── jwt_utils.py         # JWT helper utilities
│   └── queue_manager.py     # Background job queue handling
├── frontend/                # Vite-based dashboard frontend
│   ├── src/                 # Frontend source code
│   ├── public/              # Static assets
│   ├── dist/                # Production build output
│   └── package.json         # Frontend scripts and dependencies
├── memory/                  # Agent memory and learned knowledge storage
├── storage/                 # Persistent runtime storage
├── system/                  # Human-in-the-loop approval and checkpoint logic
├── workflows/               # Workflow definitions and pipeline wrappers
├── workspace/               # Generated apps, job outputs, and temporary workspaces
├── docs/                    # Technical documentation
├── scripts/                 # Utility scripts
├── logs/                    # Application logs (gitignored)
├── .env.example             # Environment configuration template
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Python project config (pytest + ruff)
├── Makefile                 # Development commands
├── docker-compose.yml       # Redis and local service orchestration
└── CLAUDE.md                # AI agent development instructions
```

---

## Requirements

Before running the project, install:

* Python 3.10+
* Node.js 18+
* Docker
* Redis, if using the RQ queue backend
* Flutter SDK, if running full Flutter validation locally

---

## Quick Start

```bash
# 1. Clone & configure
git clone <repo-url> && cd AISoftwareOrg
cp .env.example .env
# Edit .env — set LLM_API_KEY

# 2. Install & run
make setup    # Create venv + install Python & Node deps
make dev      # Start backend at http://localhost:8000

# 3. Frontend (separate terminal)
make frontend # Dev server at http://localhost:5173
# Or build for production:
make build    # Then visit http://localhost:8000
```

Run `make help` to see all available commands.

---

## Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Then configure the required values:

```env
APP_ENV=development
DASHBOARD_SECRET=change-me
LLM_PROVIDER=openrouter
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemini-2.5-flash
JOB_QUEUE_BACKEND=thread
REDIS_URL=redis://localhost:6379/0
MAX_REPAIR_ATTEMPTS=2
```

For production, always set a strong `DASHBOARD_SECRET` and avoid using development defaults.

---

## Backend Setup

Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

The API server will be available at:

```text
http://localhost:8000
```

Swagger API documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

Readiness check:

```text
http://localhost:8000/ready
```

---

## Frontend Setup

Go to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend development server will be available at:

```text
http://localhost:5173
```

Build the frontend for production:

```bash
npm run build
```

After building, the backend can serve the compiled dashboard directly from the `frontend/dist` directory.

---

## Queue Backend

The project supports two queue modes.

### Thread Mode

Thread mode is simple and works for local development:

```env
JOB_QUEUE_BACKEND=thread
```

This mode starts jobs in background Python threads.

### RQ Mode

RQ mode is recommended for more reliable background processing:

```env
JOB_QUEUE_BACKEND=rq
REDIS_URL=redis://localhost:6379/0
```

Start Redis:

```bash
docker-compose up -d
```

Then run an RQ worker if configured:

```bash
rq worker ai_software_factory
```

---

## Main API Endpoints

### System

```http
GET /health
GET /ready
GET /api
```

### Jobs

```http
GET /api/jobs
POST /api/jobs
GET /api/jobs/{slug}
DELETE /api/jobs/{slug}
POST /api/jobs/{slug}/cancel
GET /api/jobs/{slug}/phases
GET /api/jobs/{slug}/download
GET /api/jobs/{slug}/code/tree
GET /api/jobs/{slug}/code/file?path=
```

### Agents

```http
GET /api/agents
```

### Providers and Models

```http
GET /api/providers
POST /api/providers/{name}/use
GET /api/models
```

### Observability

```http
GET /api/tasks
GET /api/permissions
GET /api/costs
```

### Human-in-the-Loop

```http
GET /api/experiences
POST /api/experiences/{id}/approve
GET /api/checkpoints
```

---

## Example: Create a Generation Job

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pantry Saver",
    "description": "A Flutter app that tracks food expiration dates and suggests meals.",
    "platform": "android,ios",
    "style": "modern",
    "backend": "none",
    "features": "inventory, expiry reminders, meal suggestions, shopping list"
  }'
```

---

## Generated Output

Generated projects are stored under:

```text
workspace/generated_apps/
```

A successful job may contain:

```text
workspace/generated_apps/{slug}/
├── docs/
│   ├── app_brief.md
│   ├── requirements.md
│   ├── architecture.md
│   ├── design.md
│   ├── test_report.md
│   ├── runtime_report.md
│   ├── security_report.md
│   └── final_review.md
├── source/
│   ├── pubspec.yaml
│   └── lib/
├── backend/
└── exports/
    └── {slug}_source.zip
```

---

## Documentation

Technical documentation is available in the `docs/` directory.

Recommended documents:

* [Developer Guide](./CLAUDE.md)
* [Project Plan](./docs/project_plane.md)
* [Changelog](./docs/changelog.md)
* [Architecture Overview](./docs/architecture_overview.html)
* [Architecture Reference](./docs/architecture.md)
* [API Contract](./docs/api_contract.md)
* [Development Guide](./docs/development_guide.md)
* [Deployment Guide](./docs/deployment_guide.md)
* [Agent Workflow](./docs/agent_workflow.md)
* [Improvement Roadmap](./docs/improvement_roadmap.html)
* [Admin Manual](./docs/admin_manual.html)

If a document is missing, it may still be under development.

---

## Development Roadmap

### Phase 1 — Stabilize the Core

* Harden authentication
* Enforce production secrets
* Improve job cancellation
* Fix queue behavior
* Improve SQLite concurrency
* Add test coverage
* Add CI workflow

### Phase 2 — Improve Job Tracking

* Add persistent job phase records
* Add structured logs
* Add retry and cancellation support
* Add worker process support
* Improve generated project export flow

### Phase 3 — Improve Dashboard UX

* Add project overview
* Add job detail page
* Add phase timeline
* Add agent management
* Add provider management
* Add cost monitoring
* Add human approval queue

### Phase 4 — Improve Agent Quality

* Improve prompts
* Add model routing
* Add memory review
* Add better Flutter generation templates
* Add backend generation support
* Add security and release gates

### Phase 5 — Production Hardening

* Add Dockerfile
* Add deployment guide
* Add role-based access control
* Add audit logs
* Add backup and restore strategy
* Add observability and alerting

---

## Known Limitations

* Authentication is still being improved.
* Thread-based jobs are intended mainly for development.
* Some dashboard features may be partially implemented.
* Some generated Flutter projects may require manual review.
* Provider costs may vary depending on the selected LLM vendor.
* Full production deployment requires additional security hardening.

---

## Security Notice

Do not commit secrets, API keys, tokens, generated private data, or production `.env` files.

Before deploying publicly, configure:

* Strong `DASHBOARD_SECRET`
* Admin authentication
* Restricted CORS origins
* Secure provider API keys
* HTTPS
* Proper file access controls
* Job execution limits
* Rate limiting

---

## Contributing

Contributions are welcome.

Before submitting changes:

1. Create a feature branch.
2. Keep changes focused.
3. Update documentation when needed.
4. Add tests for new backend logic.
5. Run lint and tests before opening a pull request.

Suggested branch naming:

```text
feature/job-phase-tracking
fix/auth-token-security
docs/update-readme
```

---

## License

This project is licensed under the MIT License.

See the [LICENSE](./LICENSE) file for details.
