"""ApprovalTaskRepository — CRUD + conditional-update for approval tasks."""

from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime as dt
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_task import ApprovalTask
from app.models.enums import ApprovalStatus
from app.repositories.base import BaseRepository


class ApprovalTaskRepository(BaseRepository):
    """Repository for ``ApprovalTask`` rows — approval lifecycle management."""

    model = ApprovalTask

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ── Create ───────────────────────────────────────────────────────

    async def create(self, task: ApprovalTask) -> ApprovalTask:
        """Persist a new approval task. Caller must commit."""
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_by_action_id(self, action_id: str) -> ApprovalTask | None:
        """Find an approval task by its unique action_id."""
        result = await self.session.execute(
            select(ApprovalTask).where(ApprovalTask.action_id == action_id)
        )
        return result.scalar_one_or_none()

    # ── Read ─────────────────────────────────────────────────────────

    async def get_by_id(self, task_id: uuid.UUID) -> ApprovalTask | None:
        result = await self.session.execute(
            select(ApprovalTask).where(ApprovalTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_pending(
        self,
        status: str | None = None,
        approval_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ApprovalTask], int]:
        """List approval tasks for admin view, optionally filtered."""
        conditions: list = []
        if status:
            conditions.append(ApprovalTask.status == status)
        if approval_type:
            conditions.append(ApprovalTask.approval_type == approval_type)

        base_q = select(ApprovalTask)
        if conditions:
            base_q = base_q.where(and_(*conditions))

        count_q = select(func.count()).select_from(base_q.order_by(None).subquery())
        total: int = (await self.session.execute(count_q)).scalar() or 0

        items_q = (
            base_q
            .order_by(ApprovalTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.execute(items_q)).scalars().all())

        return items, total

    async def list_by_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20,
    ) -> tuple[list[ApprovalTask], int]:
        """List a user's own approval tasks."""
        base_q = select(ApprovalTask).where(ApprovalTask.user_id == user_id)
        count_q = select(func.count()).select_from(base_q.order_by(None).subquery())
        total: int = (await self.session.execute(count_q)).scalar() or 0

        items_q = (
            base_q
            .order_by(ApprovalTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.execute(items_q)).scalars().all())
        return items, total

    # ── Conditional update (optimistic locking) ─────────────────────

    async def decide(
        self,
        task_id: uuid.UUID,
        expected_version: int,
        new_status: str,
        decided_by: uuid.UUID,
        decision_reason: str = "",
    ) -> ApprovalTask | None:
        """Atomically update status with version check. Returns None on conflict."""
        now = dt.now(UTC)
        result = await self.session.execute(
            update(ApprovalTask)
            .where(
                and_(
                    ApprovalTask.id == task_id,
                    ApprovalTask.version == expected_version,
                    ApprovalTask.status == ApprovalStatus.PENDING.value,
                )
            )
            .values(
                status=new_status,
                decided_by=decided_by,
                decision_reason=decision_reason,
                decided_at=now,
                version=ApprovalTask.version + 1,
            )
            .returning(ApprovalTask.id)
        )
        updated_id = result.scalar_one_or_none()
        if updated_id is None:
            return None

        # Re-fetch the updated row
        return await self.get_by_id(task_id)

    async def expire_pending(self) -> int:
        """Expire all PENDING tasks past their expires_at. Returns count."""
        from sqlalchemy import text as sa_text

        result: Any = await self.session.execute(
            sa_text(
                "UPDATE approval_tasks SET status = 'EXPIRED', "
                "version = version + 1 "
                "WHERE status = 'PENDING' AND expires_at < now()"
            )
        )
        await self.session.flush()
        return result.rowcount or 0
