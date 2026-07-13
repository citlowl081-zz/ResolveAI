"""LogisticsService — query logistics, append events with row locking."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.repositories.audit_log import AuditLogRepository
from app.repositories.logistics import LogisticsRepository


class LogisticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logistics_repo = LogisticsRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def get_logistics(self, order_id: uuid.UUID) -> dict:
        record = await self.logistics_repo.get_by_order(order_id)
        if record is None:
            raise NotFoundError("Logistics not found for this order")
        return self._to_response(record)

    async def add_event(
        self, user_id: uuid.UUID, order_id: uuid.UUID,
        status: str, location: str, description: str,
        user_agent: str | None = None,
    ) -> dict:
        # Lock logistics row to prevent concurrent JSONB overwrites
        record = await self.logistics_repo.get_by_order_for_update(order_id)
        if record is None:
            raise NotFoundError("Logistics not found for this order")

        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "status": status,
            "location": location,
            "description": description,
        }
        events: list = list(record.events) if isinstance(record.events, list) else []
        events.append(event)

        record.events = events
        record.status = status
        record.current_location = location
        await self.session.flush()

        await self.audit_repo.create_log(
            user_id=user_id, action="LOGISTICS_UPDATE", resource_type="LOGISTICS",
            resource_id=record.id,
            changes={"status": status, "location": location, "description": description},
            user_agent=user_agent,
        )
        return self._to_response(record)

    def _to_response(self, record) -> dict:
        return {
            "id": str(record.id),
            "order_id": str(record.order_id),
            "tracking_number": record.tracking_number,
            "carrier": record.carrier,
            "status": record.status,
            "current_location": record.current_location,
            "estimated_delivery": record.estimated_delivery.isoformat() if record.estimated_delivery else None,
            "actual_delivery": record.actual_delivery.isoformat() if record.actual_delivery else None,
            "events": record.events,
        }
