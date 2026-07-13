"""JWT token generation and validation."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

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
    return cast(str, jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


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
    return cast(str, jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Returns the decoded claims dict."""
    result = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if not isinstance(result, dict):
        raise TypeError(f"JWT decode returned unexpected type: {type(result).__name__}")
    return cast(dict[str, Any], result)
