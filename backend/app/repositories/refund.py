"""RefundRepository."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refund_record import RefundRecord
from app.repositories.base import BaseRepository


class RefundRepository(BaseRepository):
    model = RefundRecord

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_order(self, order_id: uuid.UUID) -> list[RefundRecord]:
        result = await self.session.execute(
            select(RefundRecord).where(RefundRecord.order_id == order_id)
        )
        return list(result.scalars().all())

    async def get_by_ticket_id(self, ticket_id: uuid.UUID) -> RefundRecord | None:
        result = await self.session.execute(
            select(RefundRecord).where(RefundRecord.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def sum_refund_amount_by_order(self, order_id: uuid.UUID) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(RefundRecord.refund_amount), 0))
            .where(RefundRecord.order_id == order_id)
        )
        return Decimal(str(result.scalar() or 0))

    async def sum_shipping_refund_by_order(self, order_id: uuid.UUID) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(RefundRecord.shipping_refund_amount), 0))
            .where(RefundRecord.order_id == order_id)
        )
        return Decimal(str(result.scalar() or 0))
