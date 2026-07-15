"""PolicyDocumentRepository — read-only queries for policy_documents."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy_document import PolicyDocument
from app.repositories.base import BaseRepository


class PolicyDocumentRepository(BaseRepository):
    """Read-only repository for ``PolicyDocument``.

    Write operations (create, activate, archive) belong in the Service
    layer and are not provided here.
    """

    model = PolicyDocument

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ── Single-row lookups ───────────────────────────────────────────

    async def get_by_key_and_version(
        self, policy_key: str, version: int,
    ) -> PolicyDocument | None:
        """Return the exact (policy_key, version) row, or ``None``."""
        result = await self.session.execute(
            select(PolicyDocument).where(
                PolicyDocument.policy_key == policy_key,
                PolicyDocument.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def get_active(self, policy_key: str) -> PolicyDocument | None:
        """Return the ACTIVE version for *policy_key*, or ``None``."""
        result = await self.session.execute(
            select(PolicyDocument).where(
                PolicyDocument.policy_key == policy_key,
                PolicyDocument.status == "ACTIVE",
            )
        )
        return result.scalar_one_or_none()

    async def get_latest(self, policy_key: str) -> PolicyDocument | None:
        """Return the version with the highest ``version`` number, or ``None``."""
        result = await self.session.execute(
            select(PolicyDocument)
            .where(PolicyDocument.policy_key == policy_key)
            .order_by(PolicyDocument.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Collections ──────────────────────────────────────────────────

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
    ) -> tuple[list[PolicyDocument], int]:
        """Return (rows, total) across all policy_keys, newest version first."""
        base = select(PolicyDocument)
        if category:
            base = base.where(PolicyDocument.category == category)
        if status:
            base = base.where(PolicyDocument.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar() or 0

        query = base.order_by(
            PolicyDocument.policy_key.asc(),
            PolicyDocument.version.desc(),
        )
        query = self._paginate(query, page, page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def list_versions(
        self,
        policy_key: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PolicyDocument], int]:
        """Return (rows, total) of all versions for *policy_key*, newest first."""
        base = select(PolicyDocument).where(
            PolicyDocument.policy_key == policy_key
        )
        count_q = select(func.count()).select_from(base.subquery())

        query = base.order_by(PolicyDocument.version.desc())
        query = self._paginate(query, page, page_size)

        total_result = await self.session.execute(count_q)
        total = total_result.scalar() or 0

        result = await self.session.execute(query)
        return list(result.scalars().all()), total
