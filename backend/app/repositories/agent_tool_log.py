"""AgentToolLogRepository — tool log persistence and retrieval."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_tool_log import AgentToolLog


class AgentToolLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, log: AgentToolLog) -> AgentToolLog:
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_by_turn(
        self, session_id: uuid.UUID, turn_id: uuid.UUID,
    ) -> list[AgentToolLog]:
        result = await self.session.execute(
            select(AgentToolLog)
            .where(AgentToolLog.session_id == session_id)
            .where(AgentToolLog.turn_id == turn_id)
            .order_by(AgentToolLog.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_successful_by_turn(
        self, session_id: uuid.UUID, turn_id: uuid.UUID,
    ) -> list[AgentToolLog]:
        result = await self.session.execute(
            select(AgentToolLog)
            .where(AgentToolLog.session_id == session_id)
            .where(AgentToolLog.turn_id == turn_id)
            .where(AgentToolLog.is_success.is_(True))
        )
        return list(result.scalars().all())

    async def list_all(
        self, page: int = 1, page_size: int = 20,
        session_id: uuid.UUID | None = None,
        trace_id: uuid.UUID | None = None,
        tool_name: str | None = None,
    ) -> tuple[list[AgentToolLog], int]:
        base = select(AgentToolLog)
        if session_id:
            base = base.where(AgentToolLog.session_id == session_id)
        if trace_id:
            base = base.where(AgentToolLog.trace_id == trace_id)
        if tool_name:
            base = base.where(AgentToolLog.tool_name == tool_name)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_q)).scalar() or 0

        query = (
            base
            .order_by(AgentToolLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
