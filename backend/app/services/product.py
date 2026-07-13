"""ProductService — CRUD with pagination, filtering, optimistic locking."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.repositories.product import ProductRepository


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.product_repo = ProductRepository(session)

    async def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        name_search: str | None = None,
    ) -> dict:
        items, total = await self.product_repo.list_active(
            page=page, page_size=page_size, category=category, name_search=name_search,
        )
        return {
            "items": [
                {
                    "id": str(p.id), "name": p.name, "description": p.description,
                    "category": p.category, "price": str(p.price), "stock": p.stock,
                    "image_url": p.image_url, "is_returnable": p.is_returnable,
                }
                for p in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
        }

    async def get_product(self, product_id: uuid.UUID) -> dict:
        p = await self.product_repo.get_by_id(product_id)
        if p is None or not p.is_active:
            raise NotFoundError("Product not found")
        return {
            "id": str(p.id), "name": p.name, "description": p.description,
            "category": p.category, "price": str(p.price), "stock": p.stock,
            "image_url": p.image_url, "is_returnable": p.is_returnable,
            "version": p.version,
        }

    async def create_product(
        self, name: str, category: str, price: str, stock: int,
        description: str | None = None, image_url: str | None = None,
    ) -> dict:
        from decimal import Decimal

        from app.models.product import Product

        p = Product(
            name=name, category=category, price=Decimal(price), stock=stock,
            description=description, image_url=image_url,
        )
        await self.product_repo.save(p)
        return await self.get_product(p.id)

    async def update_product(
        self, product_id: uuid.UUID, expected_version: int, **fields: object,
    ) -> dict:
        existing = await self.product_repo.get_by_id(product_id)
        if existing is None or not existing.is_active:
            raise NotFoundError("Product not found")

        update_fields = {k: v for k, v in fields.items() if v is not None}
        p = await self.product_repo.update_with_version(
            product_id, expected_version, **update_fields,
        )
        return await self.get_product(p.id)
