"""
dashboard/routers/auth.py
Router for JWT Authentication token generations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Query, Request
from dashboard.jwt_utils import InvalidTokenError, decode_hs256, encode_hs256

router = APIRouter()


@router.get("/token")
async def get_auth_token(
    request: Request,
    team_id: str = Query(..., min_length=1),
) -> dict[str, Any]:
    secret = request.app.state.secret
    token = encode_hs256(
        {"team_id": team_id, "iat": datetime.now(timezone.utc)},
        secret,
    )
    return {"token": token, "team_id": team_id}


def get_team_id_from_token(request: Request, secret: str) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = decode_hs256(auth[7:], secret)
        return payload.get("team_id") or None
    except (InvalidTokenError, IndexError):
        return None
