"""
Small HS256 JWT helper for dashboard team tokens.

The dashboard only needs HMAC-signed JWTs with a team_id claim. Keeping this
stdlib-only avoids importing optional crypto packages in local tests.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Any


class InvalidTokenError(ValueError):
    """Raised when a JWT cannot be decoded or verified."""


def encode_hs256(payload: dict[str, Any], secret: str) -> str:
    """Encode a JSON payload as a compact HS256 JWT."""
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64url_json(header),
            _b64url_json(_json_safe_payload(payload)),
        ]
    )
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_hs256(token: str, secret: str) -> dict[str, Any]:
    """Decode and verify a compact HS256 JWT."""
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise InvalidTokenError("JWT must have three segments") from exc

    signing_input = f"{header_segment}.{payload_segment}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()

    try:
        supplied = _b64url_decode(signature_segment)
    except ValueError as exc:
        raise InvalidTokenError("JWT signature is not valid base64url") from exc

    if not hmac.compare_digest(expected, supplied):
        raise InvalidTokenError("JWT signature verification failed")

    header = _decode_json_segment(header_segment)
    if header.get("alg") != "HS256":
        raise InvalidTokenError("JWT algorithm must be HS256")

    payload = _decode_json_segment(payload_segment)
    if not isinstance(payload, dict):
        raise InvalidTokenError("JWT payload must be a JSON object")

    # Validate expiration
    now = int(time.time())
    exp = payload.get("exp")
    if exp is not None:
        try:
            if int(exp) < now:
                raise InvalidTokenError("JWT has expired")
        except (ValueError, TypeError) as exc:
            raise InvalidTokenError("Invalid exp claim in JWT") from exc

    # Validate issued-at (not in the far future)
    iat = payload.get("iat")
    if iat is not None:
        try:
            if int(iat) > now + 300:  # 5 min clock skew tolerance
                raise InvalidTokenError("JWT iat is in the future")
        except (ValueError, TypeError) as exc:
            raise InvalidTokenError("Invalid iat claim in JWT") from exc

    # Validate required claims
    if not payload.get("team_id"):
        raise InvalidTokenError("JWT missing team_id claim")

    return payload


def _json_safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe = dict(payload)
    for key, value in list(safe.items()):
        if isinstance(value, datetime):
            safe[key] = int(value.timestamp())
    return safe


def _b64url_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _b64url_encode(raw)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _decode_json_segment(segment: str) -> Any:
    try:
        return json.loads(_b64url_decode(segment).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidTokenError("JWT segment is not valid JSON") from exc
