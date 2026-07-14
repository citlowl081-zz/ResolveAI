"""Admin reshipment lifecycle API — ship, deliver, cancel reshipments."""

import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.after_sales import (
    ReshipmentCancelRequest,
    ReshipmentDeliverRequest,
    ReshipmentShipRequest,
)
from app.schemas.common import APIResponse
from app.security.dependencies import require_role
from app.services.idempotency import IdempotencyService, compute_request_hash
from app.services.reshipment import ReshipmentService

router = APIRouter(prefix="/admin/reshipments", tags=["admin-reshipments"])


def _build_hash(method: str, path: str, path_params: dict, query_params: dict, body: dict | None) -> str:
    return compute_request_hash(method, path, path_params, query_params, body)


@router.post("/{reshipment_id}/ship")
async def ship_reshipment(
    reshipment_id: uuid.UUID,
    req: ReshipmentShipRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/reshipments/{reshipment_id}/ship"
    rhash = _build_hash("POST", path, {"reshipment_id": str(reshipment_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "reshipment_ship", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = ReshipmentService(db)
    result = await service.ship_reshipment(op_id, reshipment_id, req.expected_version, req.tracking_number, req.carrier)
    await idem_service.complete(op_id, "reshipment_ship", idempotency_key, 200, result, reshipment_id)
    return APIResponse(success=True, code="OK", message="Reshipment shipped", data=result)


@router.post("/{reshipment_id}/deliver")
async def deliver_reshipment(
    reshipment_id: uuid.UUID,
    req: ReshipmentDeliverRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/reshipments/{reshipment_id}/deliver"
    rhash = _build_hash("POST", path, {"reshipment_id": str(reshipment_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "reshipment_deliver", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = ReshipmentService(db)
    result = await service.deliver_reshipment(op_id, reshipment_id, req.expected_version)
    await idem_service.complete(op_id, "reshipment_deliver", idempotency_key, 200, result, reshipment_id)
    return APIResponse(success=True, code="OK", message="Reshipment delivered", data=result)


@router.post("/{reshipment_id}/cancel")
async def cancel_reshipment(
    reshipment_id: uuid.UUID,
    req: ReshipmentCancelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/reshipments/{reshipment_id}/cancel"
    rhash = _build_hash("POST", path, {"reshipment_id": str(reshipment_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "reshipment_cancel", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = ReshipmentService(db)
    result = await service.cancel_reshipment(op_id, reshipment_id, req.expected_version)
    await idem_service.complete(op_id, "reshipment_cancel", idempotency_key, 200, result, reshipment_id)
    return APIResponse(success=True, code="OK", message="Reshipment cancelled", data=result)
