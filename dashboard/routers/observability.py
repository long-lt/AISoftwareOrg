"""
dashboard/routers/observability.py
Router for system logs, token costs, permissions and KPIs metrics.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Query, Request

from config.providers import provider_registry_payload
from dashboard.database import list_jobs, list_initiatives

router = APIRouter()


@router.get("/tasks")
async def get_tasks(request: Request) -> dict[str, Any]:
    agent_logger = request.app.state.agent_logger
    all_logs = await agent_logger.tail(n=1000)
    completed = [l for l in all_logs if l.get("action") == "workflow_completed"]
    total = len(completed)
    success = sum(1 for l in completed if l.get("status") == "success")
    failed = sum(1 for l in completed if l.get("status") == "fail")
    return {"total": total, "success": success, "failed": failed, "logs": completed[-20:]}


@router.get("/agents")
async def get_agents(request: Request, limit: int = Query(50, ge=1, le=500)) -> list[dict[str, Any]]:
    agent_logger = request.app.state.agent_logger
    return await agent_logger.tail(n=limit)


@router.get("/permissions")
async def get_permissions(request: Request) -> list[dict[str, Any]]:
    agent_logger = request.app.state.agent_logger
    all_logs = await agent_logger.tail(n=1000)
    return [l for l in all_logs if l.get("action") == "permission_denied"][-100:]


@router.get("/costs")
async def get_costs(request: Request) -> dict[str, Any]:
    agent_logger = request.app.state.agent_logger
    all_logs = await agent_logger.tail(n=1000)
    cost_logs = [l for l in all_logs if l.get("action") == "llm_cost"]

    by_task: dict[str, dict[str, Any]] = {}
    by_agent: dict[str, dict[str, Any]] = {}
    total_cost = 0.0
    total_tokens = 0

    for entry in cost_logs:
        details = entry.get("details") or {}
        task_id = entry.get("task_id", "unknown")
        agent = entry.get("agent", "unknown")
        cost = float(details.get("cost_usd") or 0.0)
        tokens = int(details.get("total_tokens") or 0)
        total_cost += cost
        total_tokens += tokens

        task_bucket = by_task.setdefault(task_id, {"cost_usd": 0.0, "tokens": 0, "calls": 0})
        task_bucket["cost_usd"] += cost
        task_bucket["tokens"] += tokens
        task_bucket["calls"] += 1

        agent_bucket = by_agent.setdefault(agent, {"cost_usd": 0.0, "tokens": 0, "calls": 0})
        agent_bucket["cost_usd"] += cost
        agent_bucket["tokens"] += tokens
        agent_bucket["calls"] += 1

    return {
        "total_cost_usd": total_cost,
        "total_tokens": total_tokens,
        "calls": len(cost_logs),
        "by_task": by_task,
        "by_agent": by_agent,
        "recent": cost_logs[-20:],
    }


@router.get("/costs/summary")
async def get_costs_summary(request: Request) -> dict[str, Any]:
    agent_logger = request.app.state.agent_logger
    all_logs = await agent_logger.tail(n=1000)
    cost_logs = [l for l in all_logs if l.get("action") == "llm_cost"]

    total_cost = 0.0
    total_calls = len(cost_logs)
    agent_costs: dict[str, float] = {}

    for entry in cost_logs:
        details = entry.get("details") or {}
        cost = float(details.get("cost_usd") or 0.0)
        total_cost += cost
        agent = entry.get("agent", "unknown")
        agent_costs[agent] = agent_costs.get(agent, 0.0) + cost

    top_agent = max(agent_costs, key=agent_costs.get) if agent_costs else None

    return {
        "total_cost_usd": round(total_cost, 4),
        "total_calls": total_calls,
        "avg_cost_per_call": round(total_cost / total_calls, 6) if total_calls else 0.0,
        "top_agent": top_agent,
    }


@router.get("/costs/by-agent")
async def get_costs_by_agent(request: Request) -> list[dict[str, Any]]:
    agent_logger = request.app.state.agent_logger
    all_logs = await agent_logger.tail(n=1000)
    cost_logs = [l for l in all_logs if l.get("action") == "llm_cost"]

    by_agent: dict[str, dict[str, Any]] = {}
    for entry in cost_logs:
        details = entry.get("details") or {}
        agent = entry.get("agent", "unknown")
        cost = float(details.get("cost_usd") or 0.0)
        tokens_in = int(details.get("prompt_tokens") or 0)
        tokens_out = int(details.get("completion_tokens") or 0)

        bucket = by_agent.setdefault(agent, {"cost_usd": 0.0, "calls": 0, "tokens_in": 0, "tokens_out": 0})
        bucket["cost_usd"] += cost
        bucket["calls"] += 1
        bucket["tokens_in"] += tokens_in
        bucket["tokens_out"] += tokens_out

    return [
        {"agent": agent, "cost_usd": round(d["cost_usd"], 4), "calls": d["calls"], "tokens_in": d["tokens_in"], "tokens_out": d["tokens_out"]}
        for agent, d in sorted(by_agent.items(), key=lambda x: x[1]["cost_usd"], reverse=True)
    ]


@router.get("/costs/by-job")
async def get_costs_by_job(request: Request) -> list[dict[str, Any]]:
    agent_logger = request.app.state.agent_logger
    all_logs = await agent_logger.tail(n=1000)
    cost_logs = [l for l in all_logs if l.get("action") == "llm_cost"]

    by_job: dict[str, dict[str, Any]] = {}
    for entry in cost_logs:
        details = entry.get("details") or {}
        job_slug = entry.get("task_id", "unknown")
        cost = float(details.get("cost_usd") or 0.0)

        bucket = by_job.setdefault(job_slug, {"cost_usd": 0.0, "calls": 0})
        bucket["cost_usd"] += cost
        bucket["calls"] += 1

    return [
        {"job_slug": slug, "cost_usd": round(d["cost_usd"], 4), "calls": d["calls"]}
        for slug, d in sorted(by_job.items(), key=lambda x: x[1]["cost_usd"], reverse=True)
    ]


@router.get("/costs/daily")
async def get_costs_daily(request: Request, days: int = Query(7, ge=1, le=30)) -> list[dict[str, Any]]:
    agent_logger = request.app.state.agent_logger
    all_logs = await agent_logger.tail(n=2000)
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=days - 1)

    daily_buckets: dict[str, dict[str, float]] = {}
    for entry in all_logs:
        if entry.get("action") != "llm_cost":
            continue
        ts = entry.get("timestamp", "")
        date_str = ts[:10]  # "YYYY-MM-DD"
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if entry_date < cutoff:
            continue
        bucket = daily_buckets.setdefault(date_str, {"cost_usd": 0.0, "calls": 0})
        details = entry.get("details") or {}
        bucket["cost_usd"] += float(details.get("cost_usd") or 0)
        bucket["calls"] += 1

    result: list[dict[str, Any]] = []
    for i in range(days):
        d = (cutoff + timedelta(days=i)).isoformat()
        bucket = daily_buckets.get(d, {"cost_usd": 0.0, "calls": 0})
        result.append(
            {
                "date": d,
                "cost_usd": round(bucket["cost_usd"], 4),
                "calls": int(bucket["calls"]),
            }
        )
    return result


@router.get("/kpis")
async def get_kpis(request: Request) -> dict[str, Any]:
    from dashboard.app import settings

    agent_logger = request.app.state.agent_logger
    jobs_list = list_jobs()
    init_list = list_initiatives()
    total_projects = len(jobs_list) + len(init_list)
    
    discovery = sum(1 for p in init_list if p.get("status") == "discovery")
    development = sum(1 for p in init_list if p.get("status") == "development") + sum(1 for j in jobs_list if j.get("status") in ("running", "queued"))
    production = sum(1 for p in init_list if p.get("status") == "production") + sum(1 for j in jobs_list if j.get("status") == "succeeded")
    blocked = sum(1 for p in init_list if p.get("status") in ("blocked", "error")) + sum(1 for j in jobs_list if j.get("status") == "failed")
    
    all_logs = await agent_logger.tail(n=1000)
    completed = [l for l in all_logs if l.get("action") == "workflow_completed"]
    total_completed = len(completed)
    success_count = sum(1 for l in completed if l.get("status") == "success")
    success_rate = (success_count / total_completed * 100) if total_completed > 0 else 0.0
    
    cost_logs = [l for l in all_logs if l.get("action") == "llm_cost"]
    total_cost = sum(float(l.get("details", {}).get("cost_usd") or 0.0) for l in cost_logs)
    
    from dashboard.routers.providers import list_active_provider_models
    try:
        models_data = await list_active_provider_models()
        active_models = len(models_data.get("models", []))
    except Exception:
        active_models = 0
        
    try:
        provs = provider_registry_payload(settings.llm_provider, settings.llm_providers_file)
        active_provs_count = sum(1 for p in provs.get("providers", []) if p.get("enabled"))
    except Exception:
        active_provs_count = 1
        
    return {
        "total_projects": total_projects,
        "discovery": discovery,
        "development": development,
        "production": production,
        "blocked": blocked,
        "success_rate": round(success_rate, 1),
        "total_cost_usd": round(total_cost, 4),
        "active_models_count": active_models,
        "active_providers_count": active_provs_count,
    }
