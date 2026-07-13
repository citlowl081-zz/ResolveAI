"""ProductRepository."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError
from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    model = Product

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_active(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        name_search: str | None = None,
    ) -> tuple[list[Product], int]:
        query = select(Product).where(Product.is_active.is_(True))
        count_q = select(func.count()).select_from(Product).where(Product.is_active.is_(True))

        if category:
            query = query.where(Product.category == category)
            count_q = count_q.where(Product.category == category)
        if name_search:
            query = query.where(Product.name.ilike(f"%{name_search}%"))
            count_q = count_q.where(Product.name.ilike(f"%{name_search}%"))

        total_result = await self.session.execute(count_q)
        total = total_result.scalar() or 0

        query = query.order_by(Product.created_at.desc())
        query = self._paginate(query, page, page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def get_by_ids_for_update(self, product_ids: list[uuid.UUID]) -> list[Product]:
        """Lock products for update, sorted ascending to prevent deadlocks."""
        sorted_ids = sorted(product_ids)
        result = await self.session.execute(
            select(Product)
            .where(Product.id.in_(sorted_ids))
            .order_by(Product.id.asc())
            .with_for_update()
        )
        return list(result.scalars().all())

    async def update_with_version(
        self, product_id: uuid.UUID, expected_version: int, **fields
    ) -> Product:
        result = await self.session.execute(
            update(Product)
            .where(Product.id == product_id, Product.version == expected_version)
            .values(version=Product.version + 1, **fields)
            .returning(Product.version)
        )
        row = result.fetchone()
        if row is None:
            raise ConflictError("Product was modified by another request; please retry")
        await self.session.flush()
        return await self.get_by_id(product_id)  # type: ignore[return-value]

    async def deduct_stock(self, product_id: uuid.UUID, quantity: int) -> bool:
        """Atomically deduct stock. Returns False if insufficient."""
        result = await self.session.execute(
            update(Product)
            .where(Product.id == product_id, Product.stock >= quantity)
            .values(stock=Product.stock - quantity)
            .returning(Product.stock)
        )
        return result.fetchone() is not None

    async def restore_stock(self, product_id: uuid.UUID, quantity: int) -> None:
        await self.session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(stock=Product.stock + quantity)
        )
