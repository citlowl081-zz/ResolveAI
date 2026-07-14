"""AgentTraceRepository — trace persistence and retrieval."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_trace import AgentTrace


class AgentTraceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, trace: AgentTrace) -> AgentTrace:
        self.session.add(trace)
        await self.session.flush()
        return trace

    async def get_by_trace_id(self, trace_id: uuid.UUID) -> list[AgentTrace]:
        result = await self.session.execute(
            select(AgentTrace)
            .where(AgentTrace.trace_id == trace_id)
            .order_by(AgentTrace.sequence.asc())
        )
        return list(result.scalars().all())

    async def list_all(
        self, page: int = 1, page_size: int = 20,
        session_id: uuid.UUID | None = None,
    ) -> tuple[list[AgentTrace], int]:
        base = select(AgentTrace)
        if session_id:
            base = base.where(AgentTrace.session_id == session_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_q)).scalar() or 0

        query = (
            base
            .order_by(AgentTrace.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
