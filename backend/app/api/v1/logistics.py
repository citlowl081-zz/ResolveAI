"""Logistics API — query logistics, add events."""

import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.logistics import LogisticsEventRequest
from app.security.dependencies import get_current_user, require_role
from app.services.idempotency import IdempotencyService, compute_request_hash
from app.services.logistics import LogisticsService

router = APIRouter(tags=["logistics"])


@router.get("/orders/{order_id}/logistics")
async def get_logistics(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> APIResponse[dict]:
    service = LogisticsService(db)
    result = await service.get_logistics(order_id)
    return APIResponse(success=True, code="OK", data=result)


@router.post("/orders/{order_id}/logistics/events")
async def add_logistics_event(
    order_id: uuid.UUID,
    req: LogisticsEventRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/orders/{order_id}/logistics/events"
    rhash = compute_request_hash("POST", path, {"order_id": str(order_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "logistics_event", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = LogisticsService(db)
    result = await service.add_event(op_id, order_id, req.status, req.location, req.description)
    await idem_service.complete(op_id, "logistics_event", idempotency_key, 200, result)
    return APIResponse(success=True, code="OK", data=result)
