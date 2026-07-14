"""ReshipmentRepository."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reshipment_order import ReshipmentOrder
from app.repositories.base import BaseRepository


class ReshipmentRepository(BaseRepository):
    model = ReshipmentOrder

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_ticket_id(self, ticket_id: uuid.UUID) -> ReshipmentOrder | None:
        result = await self.session.execute(
            select(ReshipmentOrder).where(ReshipmentOrder.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, reshipment_id: uuid.UUID) -> ReshipmentOrder | None:
        result = await self.session.execute(
            select(ReshipmentOrder)
            .where(ReshipmentOrder.id == reshipment_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def update_with_version(
        self, reshipment_id: uuid.UUID, expected_version: int, **fields: object,
    ) -> ReshipmentOrder | None:
        result = await self.session.execute(
            update(ReshipmentOrder)
            .where(
                ReshipmentOrder.id == reshipment_id,
                ReshipmentOrder.version == expected_version,
            )
            .values(version=ReshipmentOrder.version + 1, **fields)
            .returning(ReshipmentOrder.version)
        )
        if result.fetchone() is None:
            return None
        await self.session.flush()
        return await self.get_by_id(reshipment_id)

    async def generate_reshipment_number(self) -> str:
        from sqlalchemy import text
        result = await self.session.execute(text("SELECT nextval('reshipment_number_seq')"))
        seq = result.scalar_one()
        return f"RSH-{seq:06d}"
