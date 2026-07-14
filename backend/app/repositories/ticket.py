"""TicketRepository."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.after_sales_ticket import AfterSalesTicket
from app.repositories.base import BaseRepository


class TicketRepository(BaseRepository):
    model = AfterSalesTicket

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20,
    ) -> tuple[list[AfterSalesTicket], int]:
        base = select(AfterSalesTicket).where(AfterSalesTicket.user_id == user_id)
        count_q = select(func.count()).select_from(AfterSalesTicket).where(
            AfterSalesTicket.user_id == user_id
        )
        total_result = await self.session.execute(count_q)
        total = total_result.scalar() or 0

        query = base.order_by(AfterSalesTicket.created_at.desc())
        query = self._paginate(query, page, page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def list_all(
        self, page: int = 1, page_size: int = 20,
        status: str | None = None, intent: str | None = None,
    ) -> tuple[list[AfterSalesTicket], int]:
        base = select(AfterSalesTicket)
        count_q = select(func.count()).select_from(AfterSalesTicket)

        if status:
            base = base.where(AfterSalesTicket.status == status)
            count_q = count_q.where(AfterSalesTicket.status == status)
        if intent:
            base = base.where(AfterSalesTicket.intent == intent)
            count_q = count_q.where(AfterSalesTicket.intent == intent)

        total_result = await self.session.execute(count_q)
        total = total_result.scalar() or 0

        query = base.order_by(AfterSalesTicket.created_at.desc())
        query = self._paginate(query, page, page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def list_by_order(self, order_id: uuid.UUID) -> list[AfterSalesTicket]:
        result = await self.session.execute(
            select(AfterSalesTicket).where(AfterSalesTicket.order_id == order_id)
        )
        return list(result.scalars().all())

    async def get_by_id_for_update(self, ticket_id: uuid.UUID) -> AfterSalesTicket | None:
        result = await self.session.execute(
            select(AfterSalesTicket)
            .where(AfterSalesTicket.id == ticket_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def update_with_version(
        self, ticket_id: uuid.UUID, expected_version: int, **fields: object,
    ) -> AfterSalesTicket | None:
        result = await self.session.execute(
            update(AfterSalesTicket)
            .where(AfterSalesTicket.id == ticket_id, AfterSalesTicket.version == expected_version)
            .values(version=AfterSalesTicket.version + 1, **fields)
            .returning(AfterSalesTicket.version)
        )
        if result.fetchone() is None:
            return None
        await self.session.flush()
        return await self.get_by_id(ticket_id)

    async def find_active_by_order_intent_fingerprint(
        self, order_id: uuid.UUID, intent: str, fingerprint: str,
    ) -> AfterSalesTicket | None:
        """Find an APPROVED or NEEDS_REVIEW ticket matching the fingerprint."""
        result = await self.session.execute(
            select(AfterSalesTicket)
            .where(
                AfterSalesTicket.order_id == order_id,
                AfterSalesTicket.intent == intent,
                AfterSalesTicket.request_fingerprint == fingerprint,
                AfterSalesTicket.status.in_(["APPROVED", "NEEDS_REVIEW"]),
            )
        )
        return result.scalar_one_or_none()

    async def generate_ticket_number(self) -> str:
        from sqlalchemy import text
        result = await self.session.execute(text("SELECT nextval('ticket_number_seq')"))
        seq = result.scalar_one()
        return f"TKT-{seq:06d}"
