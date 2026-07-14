"""After-sales customer API — create, list, get, cancel tickets."""

import uuid

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.after_sales import (
    TicketCancelRequest,
    TicketCreateRequest,
)
from app.schemas.common import APIResponse
from app.security.dependencies import get_current_user
from app.services.idempotency import IdempotencyService, compute_request_hash
from app.services.ticket import TicketService

router = APIRouter(prefix="/after-sales/tickets", tags=["after-sales"])


def _build_hash(method: str, path: str, path_params: dict, query_params: dict, body: dict | None) -> str:
    return compute_request_hash(method, path, path_params, query_params, body)


@router.post("", status_code=201)
async def create_ticket(
    req: TicketCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    user_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    rhash = _build_hash("POST", "/api/v1/after-sales/tickets", {}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(user_id, "ticket_create", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = TicketService(db)
    result = await service.create_ticket(
        user_id, uuid.UUID(req.order_id), req.intent,
        [i.model_dump() for i in req.requested_items],
        req.customer_request,
    )
    await idem_service.complete(user_id, "ticket_create", idempotency_key, 201, result, uuid.UUID(result["id"]))
    return APIResponse(success=True, code="OK", message="Ticket created", data=result)


@router.get("")
async def list_my_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> APIResponse[dict]:
    service = TicketService(db)
    result = await service.list_my_tickets(uuid.UUID(current_user["sub"]), page, page_size)
    return APIResponse(success=True, code="OK", data=result)


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> APIResponse[dict]:
    service = TicketService(db)
    result = await service.get_ticket(ticket_id, uuid.UUID(current_user["sub"]), current_user.get("role", "CUSTOMER"))
    return APIResponse(success=True, code="OK", data=result)


@router.post("/{ticket_id}/cancel")
async def cancel_ticket(
    ticket_id: uuid.UUID,
    req: TicketCancelRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    user_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/after-sales/tickets/{ticket_id}/cancel"
    rhash = _build_hash("POST", path, {"ticket_id": str(ticket_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(user_id, "ticket_cancel", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = TicketService(db)
    result = await service.cancel_ticket(user_id, ticket_id, req.expected_version)
    await idem_service.complete(user_id, "ticket_cancel", idempotency_key, 200, result, ticket_id)
    return APIResponse(success=True, code="OK", message="Ticket cancelled", data=result)
