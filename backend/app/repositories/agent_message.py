"""AgentMessageRepository — message persistence and retrieval."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_message import AgentMessage


class AgentMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, message: AgentMessage) -> AgentMessage:
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_next_sequence(self, session_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(AgentMessage.sequence_number), 0))
            .where(AgentMessage.session_id == session_id)
        )
        return (result.scalar() or 0) + 1

    async def get_by_session_turn(
        self, session_id: uuid.UUID, turn_id: uuid.UUID,
    ) -> list[AgentMessage]:
        result = await self.session.execute(
            select(AgentMessage)
            .where(AgentMessage.session_id == session_id)
            .where(AgentMessage.turn_id == turn_id)
            .order_by(AgentMessage.turn_sequence.asc())
        )
        return list(result.scalars().all())

    async def list_by_session(
        self, session_id: uuid.UUID, page: int = 1, page_size: int = 50,
        before_sequence: int | None = None,
    ) -> tuple[list[AgentMessage], int]:
        base = select(AgentMessage).where(AgentMessage.session_id == session_id)
        if before_sequence is not None:
            base = base.where(AgentMessage.sequence_number < before_sequence)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_q)).scalar() or 0

        query = (
            base
            .order_by(AgentMessage.sequence_number.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows, total

    async def list_recent_for_context(
        self, session_id: uuid.UUID, limit: int = 50,
    ) -> list[AgentMessage]:
        """Newest messages first — for sliding window construction."""
        result = await self.session.execute(
            select(AgentMessage)
            .where(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.sequence_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
