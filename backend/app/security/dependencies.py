"""FastAPI security dependencies — JWT extraction + RBAC."""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.exceptions import AuthenticationError, AuthorizationError
from app.security.jwt import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Extract Bearer token from Authorization header."""
    if credentials is None:
        raise AuthenticationError("Authentication required")
    return credentials.credentials


async def get_current_user(token: Annotated[str, Depends(get_token)]) -> dict:
    """Validate JWT and require type='access'. Returns decoded payload."""
    try:
        payload = decode_token(token)
    except JWTError as e:
        raise AuthenticationError("Invalid or expired token") from e

    if payload.get("type") != "access":
        raise AuthenticationError("Access token required")

    return payload


async def get_current_user_from_refresh(token: Annotated[str, Depends(get_token)]) -> dict:
    """Validate JWT and require type='refresh'. Returns decoded payload."""
    try:
        payload = decode_token(token)
    except JWTError as e:
        raise AuthenticationError("Invalid or expired refresh token") from e

    if payload.get("type") != "refresh":
        raise AuthenticationError("Refresh token required")

    return payload


def require_role(*allowed_roles: str):
    """Dependency factory: require one of the given roles."""

    async def role_checker(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
        user_role = current_user.get("role", "")
        if user_role not in allowed_roles:
            raise AuthorizationError("Insufficient permissions")
        return current_user

    return role_checker


def get_user_id(current_user: Annotated[dict, Depends(get_current_user)]) -> uuid.UUID:
    """Extract user_id from current user payload."""
    return uuid.UUID(current_user["sub"])
