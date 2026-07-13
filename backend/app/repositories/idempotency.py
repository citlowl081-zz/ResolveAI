"""IdempotencyRepository — INSERT ON CONFLICT DO NOTHING RETURNING."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_record import IdempotencyRecord


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def acquire_or_get(
        self,
        user_id: uuid.UUID,
        operation: str,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[IdempotencyRecord | None, bool]:
        """Try to INSERT a PROCESSING record. Returns (record, is_new).

        is_new=True  → this request won the race, proceed with business logic.
        is_new=False → another request exists; the caller should handle the conflict.
        """
        result = await self.session.execute(
            pg_insert(IdempotencyRecord)
            .values(
                user_id=user_id,
                operation=operation,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                status="PROCESSING",
                locked_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(
                index_elements=["user_id", "operation", "idempotency_key"]
            )
            .returning(IdempotencyRecord.id)
        )
        row = result.fetchone()
        if row is not None:
            await self.session.flush()
            record = await self._get_by_id(row.id)
            return record, True  # is_new = True
        return None, False  # conflict, no insert

    async def get_for_update(
        self, user_id: uuid.UUID, operation: str, idempotency_key: str
    ) -> IdempotencyRecord | None:
        result = await self.session.execute(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.user_id == user_id,
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def reset_expired(
        self,
        record_id: uuid.UUID,
        request_hash: str,
    ) -> None:
        await self.session.execute(
            update(IdempotencyRecord)
            .where(IdempotencyRecord.id == record_id)
            .values(
                request_hash=request_hash,
                status="PROCESSING",
                locked_at=datetime.now(UTC),
                expires_at=func_default_expiry(),
                response_status=None,
                response_body=None,
                resource_id=None,
                completed_at=None,
            )
        )

    async def complete(
        self,
        record_id: uuid.UUID,
        response_status: int,
        response_body: dict | None = None,
        resource_id: uuid.UUID | None = None,
    ) -> None:
        await self.session.execute(
            update(IdempotencyRecord)
            .where(IdempotencyRecord.id == record_id)
            .values(
                status="COMPLETED",
                response_status=response_status,
                response_body=response_body,
                resource_id=resource_id,
                completed_at=datetime.now(UTC),
            )
        )

    async def _get_by_id(self, record_id: uuid.UUID) -> IdempotencyRecord | None:
        result = await self.session.execute(
            select(IdempotencyRecord).where(IdempotencyRecord.id == record_id)
        )
        return result.scalar_one_or_none()


def func_default_expiry() -> str:
    """Return a server-default expression for expires_at (NOW() + 24h)."""
    from sqlalchemy import func
    return func.now() + func.make_interval(0, 0, 0, 0, 0, 0, 24)  # type: ignore[return-value]
