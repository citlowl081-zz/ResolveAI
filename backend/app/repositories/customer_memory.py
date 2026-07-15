"""CustomerMemoryRepository — CRUD + query for long-term user memories."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_memory import CustomerMemory
from app.models.enums import MemoryStatus
from app.repositories.base import BaseRepository


class CustomerMemoryRepository(BaseRepository):
    """Repository for ``CustomerMemory`` rows — user-scoped CRUD + queries."""

    model = CustomerMemory

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ── Create / Upsert ──────────────────────────────────────────────

    async def create(self, memory: CustomerMemory) -> CustomerMemory:
        """Persist a new memory row.  Caller must commit."""
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get_active_by_key(
        self, user_id: uuid.UUID, memory_type: str, key: str,
    ) -> CustomerMemory | None:
        """Find an active memory with the same (user_id, type, key)."""
        result = await self.session.execute(
            select(CustomerMemory).where(
                and_(
                    CustomerMemory.user_id == user_id,
                    CustomerMemory.memory_type == memory_type,
                    CustomerMemory.key == key,
                    CustomerMemory.status == MemoryStatus.ACTIVE.value,
                )
            )
        )
        return result.scalar_one_or_none()

    # ── Read ─────────────────────────────────────────────────────────

    async def get_by_id_and_user(
        self, memory_id: uuid.UUID, user_id: uuid.UUID,
    ) -> CustomerMemory | None:
        """Fetch a memory row, scoped to a specific user."""
        result = await self.session.execute(
            select(CustomerMemory).where(
                and_(
                    CustomerMemory.id == memory_id,
                    CustomerMemory.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        memory_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CustomerMemory], int]:
        """Paginated list of a user's memories, optionally filtered."""
        conditions = [CustomerMemory.user_id == user_id]
        if memory_type is not None:
            conditions.append(CustomerMemory.memory_type == memory_type)
        if status is not None:
            conditions.append(CustomerMemory.status == status)

        base_q = select(CustomerMemory).where(and_(*conditions))
        count_q = select(func.count()).select_from(
            base_q.order_by(None).subquery()
        )
        total: int = (await self.session.execute(count_q)).scalar() or 0

        items_q = (
            base_q
            .order_by(CustomerMemory.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.execute(items_q)).scalars().all())

        return items, total

    async def get_active_for_context(
        self, user_id: uuid.UUID, limit: int = 20,
    ) -> list[CustomerMemory]:
        """Return active memories for LLM context injection (most recent first)."""
        result = await self.session.execute(
            select(CustomerMemory)
            .where(
                and_(
                    CustomerMemory.user_id == user_id,
                    CustomerMemory.status == MemoryStatus.ACTIVE.value,
                )
            )
            .order_by(CustomerMemory.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Update ───────────────────────────────────────────────────────

    async def update(
        self, memory: CustomerMemory, changes: dict,
    ) -> CustomerMemory:
        """Apply field updates to an existing memory row."""
        from datetime import UTC
        from datetime import datetime as dt
        for field, value in changes.items():
            if hasattr(memory, field) and field not in ("id", "user_id", "created_at"):
                setattr(memory, field, value)
        # Manually bump updated_at — onupdate=func.now() is incompatible
        # with SQLAlchemy async (triggers MissingGreenlet during flush).
        memory.updated_at = dt.now(UTC)
        await self.session.flush()
        return memory

    # ── Delete ───────────────────────────────────────────────────────

    async def delete(self, memory: CustomerMemory) -> None:
        """Remove a memory row.  Caller must commit."""
        await self.session.delete(memory)
        await self.session.flush()
