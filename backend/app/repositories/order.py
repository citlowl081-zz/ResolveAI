"""OrderRepository."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository):
    model = Order

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Order], int]:
        base = select(Order).where(Order.user_id == user_id)
        count_q = select(func.count()).select_from(Order).where(Order.user_id == user_id)

        total_result = await self.session.execute(count_q)
        total = total_result.scalar() or 0

        query = base.order_by(Order.created_at.desc())
        query = self._paginate(query, page, page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update_with_version(
        self, order_id: uuid.UUID, expected_version: int, **fields
    ) -> Order | None:
        result = await self.session.execute(
            update(Order)
            .where(Order.id == order_id, Order.version == expected_version)
            .values(version=Order.version + 1, **fields)
            .returning(Order.version)
        )
        if result.fetchone() is None:
            return None
        await self.session.flush()
        return await self.get_by_id(order_id)

    async def generate_order_number(self) -> str:
        count_result = await self.session.execute(select(func.count()).select_from(Order))
        total = count_result.scalar() or 0
        return f"ORD-{total + 1:06d}"
