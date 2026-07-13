"""Orders API — create, list, detail, pay, cancel, ship, deliver."""

import uuid

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.order import CancelRequest, OrderCreateRequest, ShipRequest, VersionedRequest
from app.security.dependencies import get_current_user, require_role
from app.services.idempotency import IdempotencyService, compute_request_hash
from app.services.order import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def _build_hash(method: str, path: str, path_params: dict, query_params: dict, body: dict | None) -> str:
    return compute_request_hash(method, path, path_params, query_params, body)


@router.post("", status_code=201)
async def create_order(
    req: OrderCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    user_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    rhash = _build_hash("POST", "/api/v1/orders", {}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(user_id, "order_create", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = OrderService(db)
    result = await service.create_order(
        user_id, [i.model_dump() for i in req.items],
        req.shipping_address, req.shipping_fee,
    )
    await idem_service.complete(user_id, "order_create", idempotency_key, 201, result)
    return APIResponse(success=True, code="OK", message="Order created", data=result)


@router.get("")
async def list_my_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> APIResponse[dict]:
    service = OrderService(db)
    result = await service.list_my_orders(uuid.UUID(current_user["sub"]), page, page_size)
    return APIResponse(success=True, code="OK", data=result)


@router.get("/{order_id}")
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> APIResponse[dict]:
    service = OrderService(db)
    result = await service.get_order(order_id, uuid.UUID(current_user["sub"]), current_user.get("role", "CUSTOMER"))
    return APIResponse(success=True, code="OK", data=result)


@router.post("/{order_id}/pay")
async def pay_order(
    order_id: uuid.UUID,
    req: VersionedRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    user_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/orders/{order_id}/pay"
    rhash = _build_hash("POST", path, {"order_id": str(order_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(user_id, "order_pay", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = OrderService(db)
    result = await service.pay_order(user_id, order_id, req.expected_version)
    await idem_service.complete(user_id, "order_pay", idempotency_key, 200, result, order_id)
    return APIResponse(success=True, code="OK", message="Payment successful", data=result)


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: uuid.UUID,
    req: CancelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    user_id = uuid.UUID(current_user["sub"])

    idem_service = IdempotencyService(db)
    path = f"/api/v1/orders/{order_id}/cancel"
    rhash = _build_hash("POST", path, {"order_id": str(order_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(user_id, "order_cancel", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = OrderService(db)
    result = await service.cancel_order(user_id, order_id, req.expected_version, req.reason)
    await idem_service.complete(user_id, "order_cancel", idempotency_key, 200, result, order_id)
    return APIResponse(success=True, code="OK", message="Order cancelled", data=result)


@router.post("/{order_id}/ship")
async def ship_order(
    order_id: uuid.UUID,
    req: ShipRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _op: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    idem_service = IdempotencyService(db)
    path = f"/api/v1/orders/{order_id}/ship"
    rhash = _build_hash("POST", path, {"order_id": str(order_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "order_ship", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = OrderService(db)
    result = await service.ship_order(op_id, order_id, req.expected_version, req.tracking_number, req.carrier)
    await idem_service.complete(op_id, "order_ship", idempotency_key, 200, result, order_id)
    return APIResponse(success=True, code="OK", message="Order shipped", data=result)


@router.post("/{order_id}/deliver")
async def deliver_order(
    order_id: uuid.UUID,
    req: VersionedRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _op: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    idem_service = IdempotencyService(db)
    path = f"/api/v1/orders/{order_id}/deliver"
    rhash = _build_hash("POST", path, {"order_id": str(order_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "order_deliver", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = OrderService(db)
    result = await service.deliver_order(op_id, order_id, req.expected_version)
    await idem_service.complete(op_id, "order_deliver", idempotency_key, 200, result, order_id)
    return APIResponse(success=True, code="OK", message="Order delivered", data=result)
