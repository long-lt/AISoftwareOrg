"""
dashboard/routers/auth.py
Router for JWT Authentication token generations.
"""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from config.settings import AppSettings
from dashboard.jwt_utils import InvalidTokenError, decode_hs256, encode_hs256

router = APIRouter()
TOKEN_EXPIRES_IN_SECONDS = 86400


class TokenRequest(BaseModel):
    team_id: str = Field(min_length=1)
    role: str = Field(default="admin", min_length=1)


@router.post("/token")
async def create_auth_token(
    request: Request,
    payload: TokenRequest,
    admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    configured_key = AppSettings().admin_api_key
    if not configured_key:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY is not configured")
    if admin_key is None or not hmac.compare_digest(admin_key, configured_key):
        raise HTTPException(status_code=401, detail="Invalid admin key")

    secret = request.app.state.secret
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=TOKEN_EXPIRES_IN_SECONDS)
    token = encode_hs256(
        {
            "team_id": payload.team_id,
            "role": payload.role,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        },
        secret,
    )
    return {
        "token": token,
        "team_id": payload.team_id,
        "role": payload.role,
        "expires_in": TOKEN_EXPIRES_IN_SECONDS,
    }


@router.get("/me")
async def get_current_user(request: Request) -> dict[str, Any]:
    secret = request.app.state.secret
    team_id = get_team_id_from_token(request, secret)
    if not team_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"team_id": team_id}


def get_team_id_from_token(request: Request, secret: str) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_hs256(auth[7:], secret)
        return payload.get("team_id") or None
    except (InvalidTokenError, IndexError):
        return None


def _decode_token_from_request(request: Request) -> dict[str, Any]:
    """Decode and validate JWT from Authorization header. Raises 401 on failure."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    secret = request.app.state.secret
    try:
        return decode_hs256(auth[7:], secret)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def require_auth(request: Request) -> dict[str, Any]:
    """FastAPI dependency: requires valid JWT. Returns payload dict."""
    return _decode_token_from_request(request)


def require_role(*allowed_roles: str):
    """FastAPI dependency factory: requires JWT with specific role(s)."""

    async def _check(request: Request) -> dict[str, Any]:
        payload = _decode_token_from_request(request)
        role = payload.get("role", "")
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Role '{role}' not authorized. Required: {allowed_roles}")
        return payload

    return _check
