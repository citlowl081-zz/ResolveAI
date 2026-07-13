"""Base repository with common CRUD operations."""

import uuid
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository:
    """Generic async repository with common CRUD patterns."""

    model: type[Base]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Any | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar() or 0

    async def save(self, entity: Any) -> Any:
        self.session.add(entity)
        await self.session.flush()
        return entity

    def _paginate(self, query: Select, page: int, page_size: int) -> Select:
        return query.offset((page - 1) * page_size).limit(page_size)


def decimal_as_python(value: Any) -> Decimal | None:
    """Convert SQLAlchemy Decimal result to Python Decimal, preserving None."""
    if value is None:
        return None
    return Decimal(str(value))
