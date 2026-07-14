"""Admin after-sales API — manage tickets, execute refunds and reshipments."""

import uuid

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.after_sales import (
    RefundExecuteRequest,
    ReshipmentCreateRequest,
    TicketApproveRequest,
    TicketRejectRequest,
)
from app.schemas.common import APIResponse
from app.security.dependencies import require_role
from app.services.idempotency import IdempotencyService, compute_request_hash
from app.services.refund import RefundService
from app.services.reshipment import ReshipmentService
from app.services.ticket import TicketService

router = APIRouter(prefix="/admin/after-sales", tags=["admin-after-sales"])


def _build_hash(method: str, path: str, path_params: dict, query_params: dict, body: dict | None) -> str:
    return compute_request_hash(method, path, path_params, query_params, body)


# ── View tickets ──────────────────────────────────────────────────────

@router.get("/tickets")
async def list_all_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    intent: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_role("OPERATOR", "ADMIN")),
) -> APIResponse[dict]:
    service = TicketService(db)
    result = await service.list_all_tickets(page, page_size, status, intent)
    return APIResponse(success=True, code="OK", data=result)


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_role("OPERATOR", "ADMIN")),
) -> APIResponse[dict]:
    service = TicketService(db)
    result = await service.get_ticket(ticket_id, uuid.UUID(_admin["sub"]), _admin.get("role", "OPERATOR"))
    return APIResponse(success=True, code="OK", data=result)


# ── Approve / Reject ─────────────────────────────────────────────────

@router.post("/tickets/{ticket_id}/approve")
async def approve_ticket(
    ticket_id: uuid.UUID,
    req: TicketApproveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/after-sales/tickets/{ticket_id}/approve"
    rhash = _build_hash("POST", path, {"ticket_id": str(ticket_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "ticket_approve", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = TicketService(db)
    result = await service.approve_ticket(op_id, ticket_id, req.expected_version)
    await idem_service.complete(op_id, "ticket_approve", idempotency_key, 200, result, ticket_id)
    return APIResponse(success=True, code="OK", message="Ticket approved", data=result)


@router.post("/tickets/{ticket_id}/reject")
async def reject_ticket(
    ticket_id: uuid.UUID,
    req: TicketRejectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/after-sales/tickets/{ticket_id}/reject"
    rhash = _build_hash("POST", path, {"ticket_id": str(ticket_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "ticket_reject", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = TicketService(db)
    result = await service.reject_ticket(op_id, ticket_id, req.expected_version, req.reject_reason)
    await idem_service.complete(op_id, "ticket_reject", idempotency_key, 200, result, ticket_id)
    return APIResponse(success=True, code="OK", message="Ticket rejected", data=result)


# ── Execute Refund ────────────────────────────────────────────────────

@router.post("/tickets/{ticket_id}/refund")
async def execute_refund(
    ticket_id: uuid.UUID,
    req: RefundExecuteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/after-sales/tickets/{ticket_id}/refund"
    rhash = _build_hash("POST", path, {"ticket_id": str(ticket_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "refund_execute", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = RefundService(db)
    result = await service.execute_refund(op_id, ticket_id, req.expected_version)
    resource_id = uuid.UUID(result["refund"]["id"])
    await idem_service.complete(op_id, "refund_execute", idempotency_key, 200, result, resource_id)
    return APIResponse(success=True, code="OK", message="Refund executed", data=result)


# ── Create Reshipment ─────────────────────────────────────────────────

@router.post("/tickets/{ticket_id}/reship")
async def create_reshipment(
    ticket_id: uuid.UUID,
    req: ReshipmentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/after-sales/tickets/{ticket_id}/reship"
    rhash = _build_hash("POST", path, {"ticket_id": str(ticket_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(op_id, "reshipment_create", idempotency_key, rhash)
    if cached is not None:
        return APIResponse(success=True, code="OK", data=cached["body"])

    service = ReshipmentService(db)
    result = await service.create_reshipment(op_id, ticket_id, req.expected_version)
    resource_id = uuid.UUID(result["reshipment"]["id"]) if result["reshipment"] else ticket_id
    await idem_service.complete(op_id, "reshipment_create", idempotency_key, 200, result, resource_id or ticket_id)
    return APIResponse(success=True, code="OK", message="Reshipment created", data=result)
