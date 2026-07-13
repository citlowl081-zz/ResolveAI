"""JWT token generation and validation."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt

from app.config.settings import settings


def create_access_token(user_id: str, role: str) -> str:
    """Create a short-lived access token (type='access', 30 min)."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    result: object = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    if not isinstance(result, str):
        raise TypeError(
            f"JWT encode returned unexpected type: {type(result).__name__}"
        )
    return result


def create_refresh_token(user_id: str, role: str) -> str:
    """Create a long-lived refresh token (type='refresh', 7 days)."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
    }
    result: object = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    if not isinstance(result, str):
        raise TypeError(
            f"JWT encode returned unexpected type: {type(result).__name__}"
        )
    return result


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Returns the decoded claims dict."""
    decoded: object = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if not isinstance(decoded, dict):
        raise TypeError(
            f"JWT decode returned unexpected type: {type(decoded).__name__}"
        )
    # Build a clean dict with str keys — no cast
    result: dict[str, Any] = {}
    for key, value in decoded.items():
        if not isinstance(key, str):
            raise TypeError(
                f"JWT claims dict contains non-string key: {type(key).__name__}"
            )
        result[key] = value
    return result
