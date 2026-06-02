# Changelog — Unified AI Software Factory

All notable changes to the **Unified AI Software Factory** platform will be documented in this file. This project adheres to Semantic Versioning (`MAJOR.MINOR.PATCH`).

---

## [v1.2.0] — Security & Stability (Current Stable)

### Added
*   **Role-Based Access Control (RBAC) System:** Enforced permission checking (`READ`, `WRITE`, `EXECUTE`, `CRITICAL`) for every agent action. Unauthorized attempts are intercepted, throwing security warnings and logging details directly to the dashboard violations feed.
*   **Persistent SQLite State:** Replaced simple server memory structures with structured SQLite database storage to persist active jobs, tail log histories, token accumulations, and HITL checkpoints.
*   **Human-in-the-Loop (HITL) Gateways:** Implemented the `ApprovalQueue` allowing administrators to inspect and approve/reject agent self-learning experiences and sensitive deployment checkpoints.
*   **Self-repairing Loops (Dart Static Repair):** Configured Dev and Refactor agents to execute continuous loops analyzing static compilation reports from `flutter analyze` and applying in-place code fixes until reaching a clean PASS state.

### Fixed
*   Resolved synchronization issues where parallel Dev pipeline steps overwrote mutual files inside the workspace.
*   Improved JWT token token validation handling during session expirations within dashboard backend API routes.
*   Corrected mathematical roundings representing custom token-to-USD pricing calculations.

### Test Suite
*   Integrated 26 automated unit and integration tests (under `tests/`) validating agent structures, RBAC, SQLite schemas, FastAPI authentication, logging, and cost limits.
*   **Test Status:** `26/26 tests passed` (100% success rate).

---

## [v1.1.0] — Enterprise Dashboard & Observability

### Added
*   **SPA Frontend Dashboard:** Built a sleek, glassmorphic Single-Page Application using Vite, Vanilla JS, and customized CSS variables with dark-navy backgrounds and neon accents.
*   **Real-time SSE Logs Streaming:** Added FastAPI endpoints streaming tail agent logs directly onto interactive terminal views on the frontend.
*   **LLM Provider Registry:** Developed backend and frontend support to query active providers (OpenRouter, OpenAI, Gemini) and dynamically switch the active LLM directly from the UI.
*   **Granular Cost Auditing:** Implemented visual donut charts and metrics mapping token usage and dollar costs to specific agents and engineering tasks.

---

## [v1.0.0] — Core Framework & 12-Phase Pipeline

### Added
*   **LangGraph Orchestration Core:** Constructed the foundational asynchronous multi-agent coordinator using LangGraph states.
*   **12-Stage Flutter Synthesis Pipeline:** Developed specialized agents (BA, Architect, API designer, Dev, QA, Security, Reviewer) working sequentially to transform natural language user requests into structural mobile code.
*   **Isolated Workspace:** Set up the sandboxed `workspace/` directory to separate generated software drafts.
*   **Export ZIP Integration:** Enabled automatic packaging compressing successfully tested compilation outcomes into a single ZIP archive for immediate delivery.

---

## [v1.3.0] — Future Roadmap Plans

### Planned
*   **Docker-packaged Sandbox Compilation:** Sandbox the `flutter analyze` and `flutter test` runners inside standard container environments to protect the host server from malicious scripts.
*   **Headless Emulator UI Verifications:** Integrate automated headless mobile runners inside the runtime agent to capture views and perform visual screenshot OCR layouts tests.
*   **Multi-Platform IPA/APK Exports:** Support Xcode and Gradle compile workflows to deliver fully built binary packages.
