"""AuditLogRepository with field-level sanitization."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository

_SENSITIVE_FIELDS = {
    "hashed_password", "password", "access_token", "refresh_token",
    "authorization",
}


def _sanitize_changes(raw: dict) -> dict:
    """Remove sensitive fields from audit changes."""
    sanitized: dict = {}
    for key, value in raw.items():
        if key in _SENSITIVE_FIELDS:
            continue
        if key == "phone" and isinstance(value, str) and len(value) >= 11:
            sanitized[key] = value[:3] + "****" + value[-4:]
        elif key in ("shipping_address", "default_address") and isinstance(value, str):
            sanitized[key] = value[:3] + "****" if len(value) > 3 else "****"
        elif key == "email" and isinstance(value, str) and "@" in value:
            parts = value.split("@")
            sanitized[key] = parts[0][0] + "***" + parts[0][-1] + "@" + parts[1]
        else:
            sanitized[key] = value
    return sanitized


class AuditLogRepository(BaseRepository):
    model = AuditLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_log(
        self,
        user_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trace_id: str | None = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=_sanitize_changes(changes) if changes else None,
            ip_address=ip_address,
            user_agent=user_agent,
            trace_id=trace_id,
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry
