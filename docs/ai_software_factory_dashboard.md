# AI Software Factory Platform — Full UI Design Prompt Pack

## Mục tiêu

Thiết kế một bộ giao diện hoàn chỉnh cho **AI Software Factory Platform** — một nền tảng SaaS doanh nghiệp giúp đội ngũ CTO, Engineering Manager, DevOps Lead, AI Platform Owner và Product Team quản lý toàn bộ vòng đời phát triển phần mềm có hỗ trợ AI.

Nền tảng bao gồm:

- Quản lý dự án phần mềm AI
- Quản lý pipeline CI/CD
- Quản lý AI Models
- Quản lý AI Agents
- Quản lý code assets
- Đánh giá chất lượng AI
- Deployment
- Monitoring
- Cost Management
- Knowledge Hub
- Automations
- Team
- Settings

---

# 1. Global Design System Prompt

```text
Design a complete high-fidelity desktop web app UI for an “AI Software Factory Platform”.

This is an enterprise SaaS platform that helps CTOs, engineering managers, DevOps leads, AI platform owners, and product teams manage the full AI-powered software delivery lifecycle: idea, requirements, planning, coding, testing, deployment, monitoring, cost, knowledge base, and AI agents.

Visual style:
- Premium dark-mode enterprise dashboard.
- Dark navy / near-black background.
- Glassmorphism cards.
- Rounded corners.
- Subtle blue-gray borders.
- Neon blue, purple, cyan, green, yellow, and red accents.
- Clean typography similar to Inter or SF Pro.
- Thin-line modern icons.
- Spacious layout.
- High information density but not cluttered.
- Inspired by Linear, Vercel, Datadog, GitHub Copilot, Supabase, and modern AI Ops dashboards.

Global layout:
- Desktop-first layout, 1440px or wider.
- Persistent left sidebar.
- Persistent top header.
- Main content area with responsive card grids.
- Sidebar should include:
  - Overview
  - Projects
  - Pipelines
  - AI Models
  - AI Agents
  - Code Assets
  - Evaluations
  - Deployments
  - Monitoring
  - Cost Management
  - Knowledge Hub
  - Automations
  - Team
  - Settings
- Active item should use a blue gradient background.
- Header should include:
  - Page title
  - Page subtitle
  - Search input
  - Date range selector
  - Notification bell
  - User avatar
  - User name: Alex Nguyen
  - Role: Platform Owner
```

---

# 2. Overview Dashboard

```text
Create the Overview Dashboard screen.

Purpose:
Give a high-level command center view of the entire AI software factory.

Content:
- Header title: “AI Software Factory Dashboard”
- Subtitle: “End-to-end visibility into AI-powered software delivery”

Top KPI cards:
1. Projects — 24 — ↑ 20% vs last 7 days
2. Pipelines — 48 — ↑ 18% vs last 7 days
3. AI Models — 32 — ↑ 14% vs last 7 days
4. Deployments — 19 — ↑ 27% vs last 7 days
5. Success Rate — 96.3% — ↑ 3.2% vs last 7 days
6. Cost This Month — $18,540 — ↓ 8% vs last month

Main card:
- Title: “Delivery Pipeline Overview”
- Horizontal pipeline stages:
  - Plan
  - Code
  - Build
  - Test
  - Deploy
  - Monitor
- Use neon connected wave visualization.
- Each stage has icon, metric, trend, and description.

Pipeline stage data:
- Plan: 24 active items, ↑ 14%
- Code: 48 commits, ↑ 18%
- Build: 48 builds, ↑ 18%
- Test: 36 test runs, ↑ 22%
- Deploy: 19 deployments, ↑ 27%
- Monitor: 19 services, ↑ 27%

Right card:
- Recent Deployments
- Rows:
  - Customer Support Agent — service-cs-agent — Prod — Success — 2h ago
  - Invoice Processing API — invoice-processor — Prod — Success — 4h ago
  - Code Review Assistant — code-review-agent — Staging — Success — 6h ago
  - Marketing Content Gen — content-gen-service — Prod — Success — 8h ago
  - Data Ingestion Pipeline — data-ingestion — Staging — Success — 10h ago

Bottom cards:
- AI Model Performance table
- Activity Feed timeline
- Cost Overview donut chart

Make this screen feel like the main control center.
```

---

# 3. Projects Screen

```text
Create the Projects screen.

Purpose:
Allow users to manage AI-powered software projects.

Header:
- Title: “Projects”
- Subtitle: “Manage software initiatives, AI apps, internal tools, and automation products”
- Primary button: “New Project”
- Secondary button: “Import Repository”

Top KPI cards:
1. Active Projects — 24
2. In Discovery — 6
3. In Development — 11
4. In Production — 7
5. Blocked — 2

Main content:
- Project grid with modern cards.
- Each project card should show:
  - Project name
  - Description
  - Owner avatar
  - Status
  - Priority
  - Progress bar
  - Linked repository
  - Active pipeline count
  - Cost this month
  - Last deployment time
  - Health indicator

Project examples:
1. Customer Support Agent
   - AI chatbot for support automation
   - Status: Production
   - Progress: 92%
   - Cost: $6,240
   - Health: Healthy

2. Invoice Processing API
   - Extracts invoice data using OCR and LLM validation
   - Status: Production
   - Progress: 88%
   - Cost: $4,820
   - Health: Healthy

3. AI-Powered QA Assistant
   - Generates test cases from product requirements
   - Status: Development
   - Progress: 64%
   - Cost: $1,960
   - Health: Warning

4. Marketing Content Generator
   - Generates marketing copy and landing page ideas
   - Status: Production
   - Progress: 96%
   - Cost: $3,210
   - Health: Healthy

5. Data Ingestion Pipeline
   - Ingests documents into vector database
   - Status: Staging
   - Progress: 74%
   - Cost: $2,730
   - Health: Healthy

Filters:
- Status
- Owner
- Priority
- Health
- Cost range

Also include table/list toggle.
```

---

# 4. Project Detail Screen

```text
Create the Project Detail screen for “Customer Support Agent”.

Purpose:
Show complete project information, lifecycle, pipeline, model usage, deployment history, and cost.

Header:
- Breadcrumb: Projects / Customer Support Agent
- Title: “Customer Support Agent”
- Status pill: Production
- Health pill: Healthy
- Buttons:
  - Run Pipeline
  - Deploy
  - Open Repository
  - Settings

Hero section:
- Project summary card
- Owner
- Team members
- Repository URL
- Environment
- Current version
- Last deployed
- Monthly cost
- SLA
- Success rate

Tabs:
- Overview
- Requirements
- Pipelines
- Models
- Agents
- Deployments
- Monitoring
- Cost
- Activity

Overview tab content:
- Project progress timeline:
  - Discovery
  - Planning
  - Development
  - Testing
  - Deployment
  - Monitoring
- Cards:
  - Active Issues
  - Open Pull Requests
  - Test Coverage
  - Model Accuracy
  - Error Rate
  - Token Usage
- Recent activity feed
- Deployment history mini table
- Model usage card
- Cost breakdown card

Use a strong SaaS product-detail layout.
```

---

# 5. Pipelines Screen

```text
Create the Pipelines screen.

Purpose:
Manage CI/CD and AI delivery pipelines.

Header:
- Title: “Pipelines”
- Subtitle: “Build, test, evaluate, and deploy AI-powered software automatically”
- Button: “Create Pipeline”

Top KPI cards:
1. Total Pipines — 48
2. Running — 5
3. Successful Today — 36
4. Failed Today — 3
5. Average Duration — 8m 42s

Main content:
- Pipeline table with columns:
  - Pipeline
  - Project
  - Trigger
  - Current Stage
  - Status
  - Duration
  - Last Run
  - Success Rate
  - Actions

Example rows:
1. customer-support-agent-prod
   - Project: Customer Support Agent
   - Trigger: Git push
   - Stage: Deploy
   - Status: Success
   - Duration: 9m 12s
   - Last Run: 2h ago
   - Success Rate: 96%

2. invoice-processor-staging
   - Trigger: Pull request
   - Stage: Test
   - Status: Running
   - Duration: 4m 30s
   - Success Rate: 91%

3. code-review-agent-eval
   - Trigger: Scheduled
   - Stage: Evaluation
   - Status: Failed
   - Duration: 12m 04s
   - Success Rate: 84%

Include:
- Search
- Status filters
- Stage filters
- “View logs” action
- “Rerun” action
```

---

# 6. Pipeline Detail Screen

```text
Create the Pipeline Detail screen.

Purpose:
Show detailed execution status of a software delivery pipeline.

Header:
- Breadcrumb: Pipelines / customer-support-agent-prod
- Title: “customer-support-agent-prod”
- Status: Running
- Buttons:
  - Cancel Run
  - Rerun
  - Edit Pipeline

Main layout:
- Horizontal pipeline stage tracker:
  - Checkout
  - Install
  - Code Quality
  - Unit Tests
  - AI Evaluation
  - Security Scan
  - Build
  - Deploy
  - Smoke Test

Each stage should show:
- Status: completed, running, failed, pending
- Duration
- Logs preview
- Icon

Left side:
- Run metadata
  - Run ID
  - Triggered by
  - Branch
  - Commit
  - Environment
  - Started at
  - Duration

Center:
- Live log viewer
- Dark terminal-style block
- Monospace text
- Highlight errors and warnings

Right side:
- AI evaluation result
- Test summary
- Security scan summary
- Deployment target
- Related pull request

Make this screen feel technical and operational.
```

---

# 7. AI Models Screen

```text
Create the AI Models screen.

Purpose:
Manage LLMs, embedding models, OCR models, classification models, and fine-tuned internal models.

Header:
- Title: “AI Models”
- Subtitle: “Track model performance, usage, cost, drift, and deployment readiness”
- Button: “Register Model”

Top KPI cards:
1. Registered Models — 32
2. Production Models — 12
3. Models With Drift — 3
4. Avg Accuracy — 89.7%
5. Token Cost Today — $842

Main content:
- Model performance table.
- Columns:
  - Model
  - Type
  - Provider
  - Version
  - Accuracy
  - Latency p95
  - Cost / 1K calls
  - Drift Score
  - Status
  - Last Evaluated

Rows:
1. Code Generation v2 — LLM — OpenAI — v2.4 — 92.1% — 1.2s — $0.031 — 0.03 — Healthy
2. Code Review v1 — LLM — Anthropic — v1.8 — 89.3% — 1.8s — $0.044 — 0.07 — Healthy
3. Doc Summarization v1 — LLM — Gemini — v1.3 — 94.2% — 2.1s — $0.022 — 0.02 — Healthy
4. Test Case Generation v1 — LLM — OpenRouter — v1.1 — 87.6% — 1.5s — $0.018 — 0.05 — Warning
5. Requirements Extractor v1 — LLM — Internal — v0.9 — 85.4% — 2.4s — $0.012 — 0.11 — Drift Detected

Include:
- Model type filters
- Provider filters
- Health filters
- “Compare Models” button
```

---

# 8. Model Detail Screen

```text
Create the Model Detail screen for “Code Generation v2”.

Purpose:
Show model performance, evaluations, deployments, usage, cost, and drift.

Header:
- Breadcrumb: AI Models / Code Generation v2
- Title: “Code Generation v2”
- Status: Healthy
- Version: v2.4
- Buttons:
  - Run Evaluation
  - Promote Version
  - Rollback
  - Settings

Top cards:
- Accuracy: 92.1%
- Latency p95: 1.2s
- Drift Score: 0.03
- Cost Today: $128
- Requests Today: 42,390

Main sections:
1. Performance trend chart
   - Accuracy over time
   - Latency over time
   - Drift over time

2. Evaluation results
   - Code correctness
   - Security score
   - Style consistency
   - Test pass rate
   - Hallucination risk

3. Version history table
   - Version
   - Released date
   - Accuracy
   - Cost
   - Status
   - Notes

4. Projects using this model
   - Customer Support Agent
   - Code Review Assistant
   - AI-Powered QA Assistant

5. Prompt templates linked to this model

Use a technical ML Ops dashboard style.
```

---

# 9. AI Agents Screen

```text
Create the AI Agents screen.

Purpose:
Manage autonomous AI agents used in the software factory.

Header:
- Title: “AI Agents”
- Subtitle: “Monitor AI workers that plan, code, test, review, deploy, and analyze software”
- Button: “Create Agent”

Top KPI cards:
1. Active Agents — 18
2. Running Tasks — 42
3. Completed Today — 318
4. Failed Tasks — 9
5. Avg Task Duration — 3m 24s

Agent cards:
Each card should show:
- Agent name
- Agent role
- Status
- Current task
- Tool access
- Success rate
- Cost today
- Last activity

Agent examples:
1. Product Planner Agent
   - Converts ideas into PRDs and task plans
   - Status: Active
   - Current task: Generating feature roadmap
   - Success rate: 94%

2. Code Writer Agent
   - Implements features from tasks
   - Status: Active
   - Current task: Writing API integration
   - Success rate: 88%

3. QA Agent
   - Generates and runs test cases
   - Status: Active
   - Current task: Regression test generation
   - Success rate: 91%

4. DevOps Agent
   - Handles deployments and infrastructure checks
   - Status: Active
   - Current task: Deployment validation
   - Success rate: 96%

5. Cost Monitor Agent
   - Tracks token usage and infrastructure cost
   - Status: Active
   - Current task: Budget anomaly detection
   - Success rate: 98%

6. Security Reviewer Agent
   - Reviews code and dependencies
   - Status: Warning
   - Current task: Dependency risk scan
   - Success rate: 86%
```

---

# 10. Agent Detail Screen

```text
Create the Agent Detail screen for “Code Writer Agent”.

Purpose:
Show the work history, permissions, task queue, memory, tools, and performance of an AI agent.

Header:
- Breadcrumb: AI Agents / Code Writer Agent
- Title: “Code Writer Agent”
- Status: Active
- Buttons:
  - Assign Task
  - Pause Agent
  - Edit Tools
  - View Memory

Top cards:
- Success Rate: 88%
- Tasks Completed: 1,284
- Current Tasks: 3
- Cost Today: $74
- Avg Duration: 4m 16s

Main content:
1. Current task card
   - Task: Implement payment retry logic
   - Project: Invoice Processing API
   - Progress: 68%
   - Current step: Writing unit tests

2. Task queue table
   - Task
   - Project
   - Priority
   - Status
   - ETA
   - Assigned by

3. Tool permissions
   - GitHub
   - Supabase
   - Cloudflare
   - Figma
   - Slack
   - Linear
   - Jira
   - Terminal
   - Browser

4. Agent memory panel
   - Project rules
   - Coding standards
   - Deployment rules
   - Recent decisions

5. Performance chart
   - Tasks completed over time
   - Failure rate
   - Token usage
```

---

# 11. Code Assets Screen

```text
Create the Code Assets screen.

Purpose:
Manage repositories, reusable modules, APIs, SDKs, templates, and generated code.

Header:
- Title: “Code Assets”
- Subtitle: “Track repositories, services, modules, APIs, and reusable software components”
- Buttons:
  - Connect Repository
  - New Template

Top KPI cards:
1. Repositories — 16
2. Services — 42
3. Shared Modules — 28
4. API Endpoints — 184
5. Code Quality Score — 91%

Main content:
- Repository cards or table.
- Columns:
  - Asset Name
  - Type
  - Language
  - Owner
  - Quality Score
  - Test Coverage
  - Vulnerabilities
  - Last Commit
  - Linked Projects

Example assets:
1. ai-support-agent-api — Service — TypeScript — 94% quality — 82% coverage
2. invoice-ocr-worker — Worker — Python — 89% quality — 76% coverage
3. prompt-template-kit — Library — TypeScript — 96% quality — 91% coverage
4. ai-eval-runner — CLI Tool — Go — 88% quality — 80% coverage
5. vector-ingestion-pipeline — Service — Python — 84% quality — 72% coverage

Include:
- Language filter
- Type filter
- Quality filter
- Security filter
```

---

# 12. Evaluations Screen

```text
Create the Evaluations screen.

Purpose:
Run and review AI model, prompt, agent, and product quality evaluations.

Header:
- Title: “Evaluations”
- Subtitle: “Measure AI quality, safety, reliability, and production readiness”
- Button: “New Evaluation”

Top KPI cards:
1. Evaluations Today — 126
2. Pass Rate — 91.4%
3. Failed Checks — 14
4. Regression Detected — 3
5. Avg Score — 87.9%

Main content:
- Evaluation runs table.
- Columns:
  - Evaluation
  - Target
  - Type
  - Dataset
  - Score
  - Result
  - Started
  - Duration
  - Owner

Evaluation types:
- Prompt Evaluation
- Model Benchmark
- Agent Task Evaluation
- Regression Test
- Security / Safety Evaluation
- Hallucination Test

Example rows:
1. CodeGen Regression Suite — Code Generation v2 — Model Benchmark — Score 92.1 — Passed
2. Support Bot Safety Check — Customer Support Agent — Safety — Score 89.4 — Passed
3. Invoice Extraction Accuracy — Invoice Processing API — Data Extraction — Score 94.8 — Passed
4. Requirements Drift Test — Requirements Extractor v1 — Drift — Score 72.2 — Failed
5. QA Agent Task Quality — QA Agent — Agent Evaluation — Score 84.6 — Warning

Include:
- Result pills: Passed, Warning, Failed
- Score visualization
- Dataset size
```

---

# 13. Deployments Screen

```text
Create the Deployments screen.

Purpose:
Manage software and AI service deployments across environments.

Header:
- Title: “Deployments”
- Subtitle: “Track releases, environments, rollouts, and production health”
- Button: “New Deployment”

Top KPI cards:
1. Deployments Today — 19
2. Production Services — 12
3. Rollbacks — 1
4. Failed Deployments — 2
5. Deployment Success Rate — 96.3%

Main content:
- Deployment table.
- Columns:
  - Service
  - Project
  - Environment
  - Version
  - Status
  - Region
  - Started
  - Duration
  - Deployed By
  - Actions

Rows:
1. service-cs-agent — Customer Support Agent — Production — v2.4.1 — Success — us-east
2. invoice-processor — Invoice Processing API — Production — v1.8.0 — Success — asia-southeast
3. code-review-agent — Code Review Assistant — Staging — v0.9.7 — Success — us-east
4. content-gen-service — Marketing Content Gen — Production — v3.2.0 — Success — eu-west
5. data-ingestion — Data Platform — Staging — v1.1.3 — Failed — asia-southeast

Include:
- Environment filter
- Status filter
- Region filter
- Rollback button
- View logs button
```

---

# 14. Monitoring Screen

```text
Create the Monitoring screen.

Purpose:
Monitor system health, uptime, latency, errors, model drift, token usage, and incidents.

Header:
- Title: “Monitoring”
- Subtitle: “Observe AI services, software systems, and production behavior in real time”
- Status pill: “All Systems Operational”

Top KPI cards:
1. Uptime — 99.98%
2. Avg Latency — 382ms
3. Error Rate — 0.21%
4. Active Incidents — 0
5. Token Usage Today — 8.4M

Main content:
- Large time-series chart:
  - Request volume
  - Latency
  - Error rate

Right side:
- Service health list:
  - Customer Support Agent — Healthy
  - Invoice Processing API — Healthy
  - Code Review Assistant — Healthy
  - Data Ingestion Pipeline — Warning
  - Requirements Extractor — Drift Detected

Bottom cards:
1. Incident Timeline
2. Model Drift Monitor
3. API Latency by Region
4. Error Logs

Error log rows:
- Timestamp
- Service
- Severity
- Error message
- Count
- Status

Use red/yellow/green status indicators clearly.
```

---

# 15. Cost Management Screen

```text
Create the Cost Management screen.

Purpose:
Show AI token cost, infrastructure cost, project cost, provider spend, budget alerts, and optimization suggestions.

Header:
- Title: “Cost Management”
- Subtitle: “Track AI usage, cloud spend, token cost, and budget efficiency”
- Button: “Create Budget”

Top KPI cards:
1. Total Cost This Month — $18,540
2. AI Token Cost — $7,420
3. Infrastructure Cost — $8,310
4. Storage Cost — $1,240
5. Savings Opportunity — $3,180

Main content:
1. Cost trend chart
   - Daily cost over current month
   - Compare with previous month

2. Cost by project donut chart:
   - customer-support-agent — $6,240
   - data-platform — $4,820
   - marketing-suite — $3,210
   - internal-tools — $2,730
   - others — $1,540

3. Provider spend table:
   - OpenAI
   - Anthropic
   - Gemini
   - OpenRouter
   - Supabase
   - Cloudflare
   - AWS

4. Budget alerts:
   - Data Platform is 85% of budget
   - Marketing Suite token usage increased 32%
   - Code Review Assistant latency increased cost by 18%

5. Optimization suggestions:
   - Cache repeated prompt calls
   - Use cheaper model for low-risk classification
   - Reduce embedding refresh frequency
   - Archive unused vector indexes
```

---

# 16. Knowledge Hub Screen

```text
Create the Knowledge Hub screen.

Purpose:
Manage internal documentation, requirements, product specs, architecture decisions, prompts, playbooks, and reusable knowledge for AI agents.

Header:
- Title: “Knowledge Hub”
- Subtitle: “Centralized project knowledge for humans and AI agents”
- Buttons:
  - Upload Document
  - New Knowledge Base

Top KPI cards:
1. Documents — 1,284
2. Knowledge Bases — 12
3. Indexed Chunks — 84,392
4. Search Queries Today — 2,930
5. Outdated Docs — 17

Main content:
- Knowledge base cards:
  1. Product Requirements
  2. Architecture Decisions
  3. Coding Standards
  4. Deployment Playbooks
  5. Prompt Library
  6. Customer Support Docs

Each card:
- Name
- Description
- Document count
- Last updated
- Linked projects
- Index status
- Access level

Right panel:
- Recent documents
- Suggested updates
- Outdated knowledge warnings

Search bar:
- “Ask anything about your software factory...”

Include a modern AI search experience.
```

---

# 17. Automations Screen

```text
Create the Automations screen.

Purpose:
Manage automated workflows that connect agents, pipelines, repositories, deployments, notifications, and monitoring events.

Header:
- Title: “Automations”
- Subtitle: “Create rules that keep your AI software factory running automatically”
- Button: “Create Automation”

Top KPI cards:
1. Active Automations — 36
2. Runs Today — 1,284
3. Failed Runs — 7
4. Time Saved — 128h
5. Success Rate — 98.7%

Main content:
- Automation workflow cards.
- Each card should show:
  - Automation name
  - Trigger
  - Actions
  - Status
  - Last run
  - Success rate

Examples:
1. Auto-create task plan from PRD
   - Trigger: New PRD uploaded
   - Actions: Extract requirements → Create tasks → Assign agents

2. Auto-run evaluation before deploy
   - Trigger: Pull request merged
   - Actions: Run model eval → Run tests → Approve deployment

3. Cost anomaly alert
   - Trigger: Daily cost exceeds threshold
   - Actions: Notify owner → Recommend optimization

4. Production drift response
   - Trigger: Drift score > 0.10
   - Actions: Pause deployment → Run evaluation → Alert team

5. Auto-generate release notes
   - Trigger: Deployment success
   - Actions: Summarize commits → Publish notes
```

---

# 18. Team Screen

```text
Create the Team screen.

Purpose:
Manage human team members, roles, permissions, activity, and ownership.

Header:
- Title: “Team”
- Subtitle: “Manage people, roles, permissions, and ownership across your software factory”
- Button: “Invite Member”

Top KPI cards:
1. Team Members — 18
2. Admins — 3
3. Engineers — 9
4. Product Members — 4
5. External Guests — 2

Main content:
- Team member table.
- Columns:
  - Name
  - Role
  - Department
  - Owned Projects
  - Last Active
  - Access Level
  - Status

Example members:
1. Alex Nguyen — Platform Owner — Admin
2. Maya Tran — Engineering Manager — Admin
3. David Kim — DevOps Lead — Maintainer
4. Sarah Chen — ML Engineer — Maintainer
5. John Lee — Product Manager — Editor
6. Nina Patel — QA Lead — Editor

Right panel:
- Permission groups:
  - Admin
  - Maintainer
  - Editor
  - Viewer
  - Guest

Also show:
- Recent team activity
- Pending invitations
```

---

# 19. Settings Screen

```text
Create the Settings screen.

Purpose:
Allow users to configure workspace, integrations, billing, permissions, security, notifications, and AI behavior.

Header:
- Title: “Settings”
- Subtitle: “Configure your AI Software Factory workspace”

Layout:
- Left settings submenu
- Right settings form panel

Settings menu:
- General
- Workspace
- AI Defaults
- Model Providers
- Integrations
- Notifications
- Security
- Billing
- API Keys
- Audit Logs

General tab:
- Workspace name
- Workspace logo
- Timezone
- Default language
- Default date format

AI Defaults tab:
- Default model
- Default embedding model
- Default coding agent
- Max token budget per task
- Auto-evaluation before deployment toggle
- Human approval required toggle

Model Providers tab:
- OpenAI
- Anthropic
- Google Gemini
- OpenRouter
- Local Models
- Custom Endpoint

Integrations tab:
- GitHub
- GitLab
- Supabase
- Cloudflare
- Vercel
- Slack
- Linear
- Jira
- Figma

Security tab:
- SSO
- 2FA
- Role-based access control
- IP allowlist
- Secret vault
- Audit log retention

Use professional enterprise settings UI.
```

---

# 20. Login Screen

```text
Create the Login screen for AI Software Factory.

Purpose:
Secure authentication entry point.

Layout:
- Split screen.
- Left side: dark gradient brand panel.
- Right side: login form card.

Left side:
- Logo: AI Software Factory
- Headline: “Build, ship, and monitor AI-powered software faster.”
- Subtext: “Your command center for agents, pipelines, models, deployments, and cost.”
- Decorative abstract AI network illustration.

Right side:
- Title: “Welcome back”
- Subtitle: “Sign in to your workspace”
- Email input
- Password input
- Forgot password link
- Sign in button
- Continue with Google
- Continue with GitHub
- Create account link

Style:
- Premium dark SaaS.
- Clean form.
- Subtle neon accents.
```

---

# 21. Create Project Wizard

```text
Create a multi-step “Create New Project” flow.

Use a centered modal or full-page wizard.

Step 1: Project Basics
- Project name
- Description
- Owner
- Team
- Priority
- Target environment

Step 2: Source
- Start from scratch
- Import GitHub repository
- Import Figma design
- Upload PRD
- Generate from idea

Step 3: AI Setup
- Select planning agent
- Select coding agent
- Select QA agent
- Select default model
- Select knowledge base

Step 4: Pipeline Setup
- Enable CI/CD
- Enable AI evaluation
- Enable security scan
- Enable deployment approval
- Enable cost monitoring

Step 5: Review
- Summary of selected settings
- Create Project button

Style:
- Dark modal
- Stepper at top
- Clear form hierarchy
- Smooth enterprise SaaS design
```

---

# 22. Empty States

```text
Create empty states for important screens.

Screens:
- Projects empty state
- Pipelines empty state
- AI Models empty state
- AI Agents empty state
- Deployments empty state
- Knowledge Hub empty state
- Automations empty state

Each empty state should include:
- Simple futuristic illustration
- Clear title
- Helpful subtitle
- Primary action button
- Secondary documentation link

Examples:

Projects empty:
Title: “No projects yet”
Subtitle: “Create your first AI-powered software project and let agents help you plan, build, test, and deploy.”
Button: “Create Project”

Agents empty:
Title: “No AI agents configured”
Subtitle: “Create specialized agents for planning, coding, testing, deployment, and monitoring.”
Button: “Create Agent”
```

---

# 23. Mobile / Tablet Responsive Version

```text
Create responsive versions for tablet and mobile.

Tablet:
- Sidebar collapses into icon-only rail.
- Cards become two-column layout.
- Tables become scrollable.
- Header remains compact.

Mobile:
- Sidebar becomes bottom navigation or drawer.
- Dashboard KPI cards become horizontal scroll cards.
- Tables convert into stacked cards.
- Charts become simplified.
- Primary actions remain sticky at bottom where needed.

Mobile bottom navigation:
- Overview
- Projects
- Agents
- Monitoring
- Settings

Maintain the same dark premium style.
```

---

# 24. Prompt Ngắn Gọn Để Generate Cả Bộ Màn Hình

```text
Create a complete high-fidelity UI kit and full desktop SaaS web app design for “AI Software Factory Platform”.

The platform helps teams manage AI-powered software delivery: projects, pipelines, AI models, AI agents, code assets, evaluations, deployments, monitoring, cost management, knowledge base, automations, team, and settings.

Design all screens:
1. Overview Dashboard
2. Projects
3. Project Detail
4. Pipelines
5. Pipeline Detail
6. AI Models
7. Model Detail
8. AI Agents
9. Agent Detail
10. Code Assets
11. Evaluations
12. Deployments
13. Monitoring
14. Cost Management
15. Knowledge Hub
16. Automations
17. Team
18. Settings
19. Login
20. Create Project Wizard
21. Empty States
22. Responsive Mobile / Tablet Version

Use a premium dark-mode enterprise SaaS style:
- Dark navy / near-black background
- Glassmorphism cards
- Neon blue, purple, cyan, green, yellow, red accents
- Rounded cards
- Thin-line modern icons
- Clean Inter typography
- Strong information hierarchy
- Production-ready dashboard aesthetics
- Inspired by Linear, Vercel, Datadog, GitHub Copilot, Supabase, and modern AI Ops tools

The UI should feel like a command center for CTOs, engineering managers, DevOps leads, product owners, and AI platform teams.

Include realistic data, charts, tables, KPI cards, status pills, activity feeds, pipeline visualizations, cost charts, model performance metrics, deployment logs, agent task queues, and enterprise settings.
```

---

# 25. Khuyến nghị triển khai MVP

Theo hướng sản phẩm thật, nên làm trước 10 màn hình lõi:

1. Overview Dashboard
2. Projects
3. Project Detail
4. Pipelines
5. Pipeline Detail
6. AI Agents
7. Agent Detail
8. Monitoring
9. Cost Management
10. Settings

Lý do:

- Đây là nhóm màn hình thể hiện rõ nhất giá trị của sản phẩm.
- Có đủ luồng từ quản lý project → agent → pipeline → deployment → monitoring → cost.
- Dễ demo cho nhà đầu tư, team kỹ thuật hoặc AI coding agent.
- Các màn như Knowledge Hub, Evaluations, Code Assets, Automations có thể mở rộng ở phase 2.
