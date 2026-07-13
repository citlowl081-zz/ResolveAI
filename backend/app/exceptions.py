"""Unified exception hierarchy.

All application errors inherit from AppError, enabling consistent
error handling in FastAPI exception handlers.
"""

from http import HTTPStatus


class AppError(Exception):
    """Base application error."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""

    status_code: int = HTTPStatus.NOT_FOUND
    code: str = "NOT_FOUND"


class ValidationError(AppError):
    """Request validation failed."""

    status_code: int = HTTPStatus.BAD_REQUEST
    code: str = "VALIDATION_ERROR"


class ConflictError(AppError):
    """Resource conflict (duplicate, idempotency, state transition)."""

    status_code: int = HTTPStatus.CONFLICT
    code: str = "CONFLICT"


class AuthenticationError(AppError):
    """Authentication failed (Phase 02+)."""

    status_code: int = HTTPStatus.UNAUTHORIZED
    code: str = "AUTHENTICATION_ERROR"


class AuthorizationError(AppError):
    """Insufficient permissions (Phase 02+)."""

    status_code: int = HTTPStatus.FORBIDDEN
    code: str = "AUTHORIZATION_ERROR"


class ServiceUnavailableError(AppError):
    """External service unavailable (LLM, DB)."""

    status_code: int = HTTPStatus.SERVICE_UNAVAILABLE
    code: str = "SERVICE_UNAVAILABLE"
