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


def get_team_id_from_token(request: Request, secret: str) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_hs256(auth[7:], secret)
        return payload.get("team_id") or None
    except (InvalidTokenError, IndexError):
        return None
