"""Products API — list, detail, create (ADMIN), update (ADMIN)."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.product import ProductCreateRequest, ProductUpdateRequest
from app.security.dependencies import require_role
from app.services.product import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    service = ProductService(db)
    result = await service.list_products(page, page_size, category, name)
    return APIResponse(success=True, code="OK", data=result)


@router.get("/{product_id}")
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> APIResponse[dict]:
    service = ProductService(db)
    product = await service.get_product(product_id)
    return APIResponse(success=True, code="OK", data=product)


@router.post("", status_code=201)
async def create_product(
    req: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    service = ProductService(db)
    product = await service.create_product(
        name=req.name, category=req.category, price=req.price,
        stock=req.stock, description=req.description, image_url=req.image_url,
    )
    return APIResponse(success=True, code="OK", message="Product created", data=product)


@router.patch("/{product_id}")
async def update_product(
    product_id: uuid.UUID,
    req: ProductUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_role("ADMIN")),
) -> APIResponse[dict]:
    service = ProductService(db)
    update_fields = {k: v for k, v in req.model_dump(exclude={"expected_version"}).items() if v is not None}
    product = await service.update_product(product_id, req.expected_version, **update_fields)
    return APIResponse(success=True, code="OK", data=product)
