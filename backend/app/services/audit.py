"""AuditService — centralized audit logging."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_log import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.audit_repo = AuditLogRepository(session)

    async def log(
        self,
        user_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        await self.audit_repo.create_log(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            trace_id=trace_id,
        )
