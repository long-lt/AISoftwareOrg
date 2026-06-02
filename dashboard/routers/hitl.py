"""
dashboard/routers/hitl.py
Router for Human-in-the-Loop gates (Experiences approval queue & Checkpoints store).
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request

from memory.storage import TenantAwareStorage
from system.learning import ApprovalQueue, CheckpointStore
from dashboard.routers.auth import get_team_id_from_token

router = APIRouter()


def _team_queue(team_id: str, queue: ApprovalQueue) -> ApprovalQueue:
    queue_storage = queue.storage
    base_storage = (
        queue_storage.base_storage
        if isinstance(queue_storage, TenantAwareStorage)
        else queue_storage
    )
    return ApprovalQueue(storage=TenantAwareStorage(team_id, base_storage))


def _team_cp_store(team_id: str, cp_store: CheckpointStore) -> CheckpointStore:
    queue_storage = cp_store.storage
    base_storage = (
        queue_storage.base_storage
        if isinstance(queue_storage, TenantAwareStorage)
        else queue_storage
    )
    return CheckpointStore(storage=TenantAwareStorage(team_id, base_storage))


@router.get("/hitl/queue")
async def get_hitl_queue(request: Request) -> dict[str, Any]:
    queue = request.app.state.approval_queue
    cp_store = request.app.state.checkpoint_store
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    q = _team_queue(team_id, queue) if team_id else queue
    cs = _team_cp_store(team_id, cp_store) if team_id else cp_store

    exp_pending = [{"type": "experience", **item} for item in q.list_pending()]
    cp_pending = [{"type": "checkpoint", **item} for item in cs.list_pending()]

    return {
        "pending": exp_pending + cp_pending,
        "counts": {
            "experiences": q.count(),
            "checkpoints": cs.count(),
        },
    }


@router.post("/hitl/{item_id}/approve")
async def hitl_approve(item_id: str, request: Request) -> dict[str, Any]:
    queue = request.app.state.approval_queue
    cp_store = request.app.state.checkpoint_store
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    q = _team_queue(team_id, queue) if team_id else queue
    cs = _team_cp_store(team_id, cp_store) if team_id else cp_store

    result = q.approve(item_id)
    if result is not None:
        return result
    result = cs.approve(item_id)
    if result is not None:
        return result
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


@router.post("/hitl/{item_id}/reject")
async def hitl_reject(
    item_id: str,
    request: Request,
    reason: str = Query("", description="Lý do từ chối"),
) -> dict[str, Any]:
    queue = request.app.state.approval_queue
    cp_store = request.app.state.checkpoint_store
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    q = _team_queue(team_id, queue) if team_id else queue
    cs = _team_cp_store(team_id, cp_store) if team_id else cp_store

    result = q.reject(item_id, reason=reason)
    if result is not None:
        return result
    result = cs.reject(item_id, reason=reason)
    if result is not None:
        return result
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


@router.get("/experiences")
async def get_experiences(request: Request) -> dict[str, Any]:
    queue = request.app.state.approval_queue
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    q = _team_queue(team_id, queue) if team_id else queue
    pending = q.list_pending()
    approved = q.list_approved()
    rejected = q.list_rejected()
    counts = q.count()
    return {
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "counts": counts,
    }


@router.post("/experiences/{exp_id}/approve")
async def approve_experience(exp_id: str, request: Request) -> dict[str, Any]:
    queue = request.app.state.approval_queue
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    q = _team_queue(team_id, queue) if team_id else queue
    result = q.approve(exp_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Experience {exp_id} not found")
    return result


@router.post("/experiences/{exp_id}/reject")
async def reject_experience(
    exp_id: str,
    request: Request,
    reason: str = Query("", description="Lý do từ chối"),
) -> dict[str, Any]:
    queue = request.app.state.approval_queue
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    q = _team_queue(team_id, queue) if team_id else queue
    result = q.reject(exp_id, reason=reason)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Experience {exp_id} not found")
    return result


@router.get("/checkpoints")
async def get_checkpoints(request: Request) -> dict[str, Any]:
    cp_store = request.app.state.checkpoint_store
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    cs = _team_cp_store(team_id, cp_store) if team_id else cp_store
    pending = cs.list_pending()
    approved = cs.list_approved()
    rejected = cs.list_rejected()
    counts = cs.count()
    return {
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "counts": counts,
    }


@router.post("/checkpoints/{cp_id}/approve")
async def approve_checkpoint(cp_id: str, request: Request) -> dict[str, Any]:
    cp_store = request.app.state.checkpoint_store
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    cs = _team_cp_store(team_id, cp_store) if team_id else cp_store
    result = cs.approve(cp_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Checkpoint {cp_id} not found")
    return result


@router.post("/checkpoints/{cp_id}/reject")
async def reject_checkpoint(
    cp_id: str,
    request: Request,
    reason: str = Query("", description="Lý do từ chối"),
) -> dict[str, Any]:
    cp_store = request.app.state.checkpoint_store
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    cs = _team_cp_store(team_id, cp_store) if team_id else cp_store
    result = cs.reject(cp_id, reason=reason)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Checkpoint {cp_id} not found")
    return result
