"""LogisticsRepository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logistics_record import LogisticsRecord
from app.repositories.base import BaseRepository


class LogisticsRepository(BaseRepository):
    model = LogisticsRecord

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_order(self, order_id: uuid.UUID) -> LogisticsRecord | None:
        result = await self.session.execute(
            select(LogisticsRecord).where(LogisticsRecord.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_for_update(self, order_id: uuid.UUID) -> LogisticsRecord | None:
        result = await self.session.execute(
            select(LogisticsRecord)
            .where(LogisticsRecord.order_id == order_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()
