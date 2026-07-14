"""AgentSessionRepository — session CRUD with turn lock operations."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_session import AgentSession


class AgentSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, session_id: uuid.UUID) -> AgentSession | None:
        result = await self.session.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, session_id: uuid.UUID) -> AgentSession | None:
        result = await self.session.execute(
            select(AgentSession)
            .where(AgentSession.id == session_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def save(self, session: AgentSession) -> AgentSession:
        self.session.add(session)
        await self.session.flush()
        return session

    async def try_acquire_turn(
        self,
        session_id: uuid.UUID,
        turn_id: uuid.UUID,
        trace_id: uuid.UUID,
        key_hash: str,
        request_hash: str,
        now: datetime | None = None,
    ) -> AgentSession | None:
        """Atomically acquire the active_turn slot.

        Returns the updated AgentSession row if acquisition succeeded.
        Returns None if a non-expired turn is already active.
        """
        ts = now or datetime.now(UTC)
        expiry = ts + timedelta(seconds=90)

        result = await self.session.execute(
            update(AgentSession)
            .where(AgentSession.id == session_id)
            .where(AgentSession.status == "ACTIVE")
            .where(
                (AgentSession.active_turn_id.is_(None))
                | (AgentSession.active_turn_expires_at < ts)
            )
            .values(
                active_turn_id=turn_id,
                active_turn_trace_id=trace_id,
                active_turn_idempotency_key_hash=key_hash,
                active_turn_request_hash=request_hash,
                active_turn_started_at=ts,
                active_turn_expires_at=expiry,
                updated_at=ts,
            )
            .returning(AgentSession.id)
        )
        row = result.fetchone()
        if row is None:
            return None
        await self.session.flush()
        return await self.get_by_id(session_id)

    async def clear_active_turn(
        self, session_id: uuid.UUID, turn_id: uuid.UUID, now: datetime | None = None
    ) -> None:
        ts = now or datetime.now(UTC)
        await self.session.execute(
            update(AgentSession)
            .where(AgentSession.id == session_id)
            .where(AgentSession.active_turn_id == turn_id)
            .values(
                active_turn_id=None,
                active_turn_trace_id=None,
                active_turn_idempotency_key_hash=None,
                active_turn_request_hash=None,
                active_turn_started_at=None,
                active_turn_expires_at=None,
                updated_at=ts,
            )
        )

    async def set_turn_expired(
        self, session_id: uuid.UUID, turn_id: uuid.UUID
    ) -> None:
        """Set active_turn_expires_at = NOW() for recoverable interruption."""
        await self.session.execute(
            update(AgentSession)
            .where(AgentSession.id == session_id)
            .where(AgentSession.active_turn_id == turn_id)
            .values(
                active_turn_expires_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

    async def update_message_count(
        self, session_id: uuid.UUID, increment: int
    ) -> None:
        await self.session.execute(
            update(AgentSession)
            .where(AgentSession.id == session_id)
            .values(
                message_count=AgentSession.message_count + increment,
                updated_at=datetime.now(UTC),
            )
        )

    async def list_by_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[AgentSession], int]:
        from sqlalchemy import func as sqlfunc

        base = select(AgentSession).where(AgentSession.user_id == user_id)
        if status:
            base = base.where(AgentSession.status == status)

        count_q = select(sqlfunc.count()).select_from(base.subquery())
        total = (await self.session.execute(count_q)).scalar() or 0

        query = (
            base
            .order_by(AgentSession.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
