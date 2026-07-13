"""OrderItemRepository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_item import OrderItem
from app.repositories.base import BaseRepository


class OrderItemRepository(BaseRepository):
    model = OrderItem

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_batch(self, items: list[dict]) -> list[OrderItem]:
        order_items = [OrderItem(**item) for item in items]
        self.session.add_all(order_items)
        await self.session.flush()
        return order_items

    async def list_by_order(self, order_id: uuid.UUID) -> list[OrderItem]:
        result = await self.session.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        return list(result.scalars().all())
