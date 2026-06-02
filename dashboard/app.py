"""
dashboard/app.py
Unified Dashboard & API Server for Unified AI Software Factory.
Refactored into modular routers.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config.settings import AppSettings
from core.logging import AgentLogger
from memory.storage import TenantAwareStorage
from system.learning import ApprovalQueue, CheckpointStore

# Import Database & Queue managers to ensure initialization
from dashboard.database import ROOT_DIR, _connect
from dashboard.queue_manager import QUEUE_BACKEND

# Import routers
from dashboard.routers import (
    auth,
    observability,
    providers,
    hitl,
    projects,
    agents,
    jobs,
)

settings = AppSettings()


def create_app(
    logger: Optional[AgentLogger] = None,
    approval_queue: Optional[ApprovalQueue] = None,
    checkpoint_store: Optional[CheckpointStore] = None,
    secret_key: Optional[str] = None,
) -> FastAPI:
    # 1. Initialize DB Tables
    _connect().close()

    agent_logger = logger or AgentLogger(echo=False)
    queue = approval_queue or ApprovalQueue()
    cp_store = checkpoint_store or CheckpointStore()
    secret = secret_key or os.getenv("DASHBOARD_SECRET", "dev-secret-change-me")
    is_production = os.getenv("APP_ENV", "development").lower() == "production"

    app = FastAPI(title="Unified AI Software Factory Dashboard", version="1.0.0")

    # Store shared components in app state to share with routers
    app.state.agent_logger = agent_logger
    app.state.approval_queue = queue
    app.state.checkpoint_store = cp_store
    app.state.secret = secret

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not is_production else os.getenv("CORS_ORIGINS", "").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register Routers
    app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(observability.router, prefix="/api", tags=["Observability"])
    app.include_router(providers.router, prefix="/api", tags=["Providers"])
    app.include_router(hitl.router, prefix="/api", tags=["HITL"])
    app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
    app.include_router(agents.router, prefix="/api", tags=["Agents"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])

    # 3. Health & Readiness
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "queue_backend": QUEUE_BACKEND}

    @app.get("/ready")
    async def ready() -> dict[str, Any]:
        try:
            queue_storage = queue.storage
            base_storage = (
                queue_storage.base_storage
                if isinstance(queue_storage, TenantAwareStorage)
                else queue_storage
            )
            base_storage.load()
            return {"status": "ready"}
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "error": str(exc)},
            )

    @app.get("/api")
    async def api_root() -> dict[str, str]:
        return {
            "status": "online",
            "service": "Unified AI Software Factory API Backend",
            "version": "1.0.0",
            "docs_url": "/docs"
        }

    # 4. HTML Rendering & Static Files Mapping (Production UI Integration)
    DASHBOARD_DIST_DIR = ROOT_DIR / "frontend" / "dist"

    if DASHBOARD_DIST_DIR.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(DASHBOARD_DIST_DIR / "assets")),
            name="dashboard_assets",
        )

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> Any:
        dist_index = DASHBOARD_DIST_DIR / "index.html"
        if dist_index.exists():
            return HTMLResponse(content=dist_index.read_text(encoding="utf-8"))
        
        # Fallback if UI exists but not built yet
        return HTMLResponse(
            content="""
            <html>
                <head>
                    <title>Unified AI Software Factory Backend</title>
                    <style>
                        body { background-color: #0b0f19; color: #f3f4f6; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }
                        .card { background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.08); padding: 40px; border-radius: 12px; }
                        h1 { color: #00d2ff; }
                        code { background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; font-family: monospace; }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>Unified AI Software Factory API Backend</h1>
                        <p>Dịch vụ API hoạt động bình thường.</p>
                        <p>Giao diện UI đang được tích hợp tại <code>frontend</code>.</p>
                        <p>Vui lòng chạy <code>npm run build</code> trong thư mục UI để kích hoạt giao diện sản xuất.</p>
                        <p><a href="/docs" style="color: #9d4edd; text-decoration: none; font-weight: bold;">Tài liệu Swagger API Docs &rarr;</a></p>
                    </div>
                </body>
            </html>
            """
        )

    return app


# Standard app runner
app = create_app()
