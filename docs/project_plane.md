# Project Plan — Unified AI Software Factory

## Executive Summary

The **Unified AI Software Factory** is a next-generation platform designed to fully automate the software development lifecycle (SDLC) by integrating two core systems:
1.  **AISoftwareOrg**: A LangGraph-orchestrated multi-agent system simulating an enterprise engineering division (PM, Architect, Developer, QA, DevOps, Git).
2.  **flutter_ai_factory**: A highly targeted 12-stage compilation pipeline tailored for synthesizing fully-functional Flutter applications and companion REST APIs directly from natural language specifications.

This project plan details the roadmap to elevate the unified codebase from an advanced prototype to a production-grade enterprise SaaS platform capable of orchestrating concurrent workspaces, tracking real-time API costs, enforcing strict RBAC security parameters, and expanding self-learning database loops.

---

## User Review Required

> [!IMPORTANT]
> The transition from thread-based background workers to **Redis Queue (python-rq)** requires an active Redis instance. For enterprise production scale, migrating standard SQLite memory pools to a distributed **PostgreSQL** cluster is recommended to support multi-tenant state storage.

> [!WARNING]
> Sandboxed execution of Flutter builds using `flutter analyze` and `flutter test` requires pre-installed Flutter SDK dependencies inside target container environments. Docker packaging must guarantee these SDK resources are correctly distributed across workers.

---

## Open Questions

> [!NOTE]
> 1. Should we prioritize iOS build support (requires macOS runners) or focus initially on standard Android and Web compilation sandboxes?
> 2. Will custom tool registrations for Dev agents support arbitrary third-party REST APIs, or should we restrict tool invocation strictly to predefined workspace boundaries (FS, Git, Test runners)?

---

## Proposed Changes

### Component 1: Orchestration & Concurrency Core

Refining the underlying `LangGraph` and background task processing engines to support parallel workflows, session persistence, and multi-agent workspace integrity.

#### [MODIFY] [full_pipeline.py](file:///Users/long/Desktop/AI_/AISoftwareOrg/workflows/full_pipeline.py)
*   Activate parallel task execution in Step 3 by incorporating `create_master_workflow` from `core.graph.orchestrator`.
*   Support persistent state storage saving intermediate agent decisions directly to database checkpoints instead of standard server memory.

#### [MODIFY] [queue_manager.py](file:///Users/long/Desktop/AI_/AISoftwareOrg/dashboard/queue_manager.py)
*   Stabilize integration of Redis queues to distribute active synthesis jobs.
*   Implement automatic worker scaling based on queue depth metrics.

---

### Component 2: High-Fidelity Enterprise Dashboard

Implementing the global design system within Vite & Vanilla CSS to present a dark-mode dashboard tailored for Engineering Managers and Platform Owners.

#### [MODIFY] [app.py](file:///Users/long/Desktop/AI_/AISoftwareOrg/dashboard/app.py)
*   Expose streaming SSE (Server-Sent Events) endpoints for real-time tail logs streaming from individual AI agents.
*   Add granular analytical API routes reporting cumulative token costs, success distributions, and security violations.

#### [NEW] [router.js](file:///Users/long/Desktop/AI_/AISoftwareOrg/frontend/src/router.js)
*   Establish SPA navigation routes covering: Overview, Projects, Pipelines, AI Models, AI Agents, Evaluations, Cost, and HITL Approvals.

---

### Component 3: Mobile Sandbox & Runtime Validation

Building a secure execution environment to build, analyze, and test synthesized code assets without risk to the host operating system.

#### [NEW] [runtime_agent.py](file:///Users/long/Desktop/AI_/AISoftwareOrg/agents/flutter_factory/runtime_agent.py)
*   Construct an execution sandbox to execute `flutter test` and launch mock compilation runs.
*   Develop headless browser/emulator integrations to capture and verify runtime UI screenshots.

---

### Component 4: HITL Experience DB & Self-Learning

Completing the closed loop of experience accumulation where agents optimize their code output over time by reviewing past compilation repairs.

#### [MODIFY] [learning/](file:///Users/long/Desktop/AI_/AISoftwareOrg/system/learning/)
*   Extend SQLite experience database queries to save successful in-place Dart code refactoring sequences.
*   Develop the human approval UI integration so Platform Owners can approve/reject learned skills before they are registered globally.

---

## Verification Plan

### Automated Tests
1.  **Orchestrator Concurrency Validation:**
    Run automated tests verifying that parallel agent execution is safe:
    ```bash
    pytest tests/test_parallel.py tests/test_multi_team.py
    ```
2.  **Dashboard API Integrations:**
    Assert REST endpoints return expected token distribution metrics:
    ```bash
    pytest tests/test_dashboard.py tests/test_dashboard_auth.py
    ```
3.  **RBAC Violations Verification:**
    Validate that restricted agents cannot perform unauthorized file operations:
    ```bash
    pytest tests/test_rbac.py
    ```

### Manual Verification
*   Launch FastAPI Server and Vite frontend.
*   Connect to the local dashboard, submit a custom mobile app request, and monitor real-time tail logs and step status indicators.
*   Inspect the generated export ZIP archive in `workspace/` and verify that the Dart code compiles with zero static errors.
