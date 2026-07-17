"""Admin Approval API — list, view, approve, reject approval tasks."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalDetailResponse,
    ApprovalListResponse,
    ApprovalTaskResponse,
)
from app.schemas.common import APIResponse
from app.security.dependencies import require_role
from app.services.approval_service import ApprovalService
from app.services.idempotency import IdempotencyService, compute_request_hash

router = APIRouter(prefix="/admin/approvals", tags=["admin-approvals"])


def _task_to_response(t: Any) -> ApprovalTaskResponse:
    return ApprovalTaskResponse(
        id=str(t.id),
        user_id=str(t.user_id),
        agent_session_id=str(t.agent_session_id) if t.agent_session_id else None,
        turn_id=str(t.turn_id) if t.turn_id else None,
        action_id=t.action_id,
        tool_name=t.tool_name,
        approval_type=t.approval_type.value if hasattr(t.approval_type, "value") else str(t.approval_type),
        status=t.status.value if hasattr(t.status, "value") else str(t.status),
        risk_level=t.risk_level,
        reason=t.reason,
        requested_by=str(t.requested_by),
        decided_by=str(t.decided_by) if t.decided_by else None,
        decision_reason=t.decision_reason,
        expires_at=t.expires_at,
        decided_at=t.decided_at,
        version=t.version,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _task_to_detail(t: Any) -> ApprovalDetailResponse:
    base = _task_to_response(t)
    payload = t.sanitized_action_payload or {}
    return ApprovalDetailResponse(
        **base.model_dump(),
        action_summary={
            "intent": payload.get("intent", ""),
            "item_count": len(payload.get("requested_items", [])),
        },
    )


# ── List / View ────────────────────────────────────────────────────────

@router.get("")
async def list_approvals(
    status: str | None = Query(None),
    approval_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_role("OPERATOR", "ADMIN")),
) -> APIResponse[ApprovalListResponse]:
    """List approval tasks. Filterable by status and type."""
    service = ApprovalService(db)
    items, total = await service.list_tasks(
        status=status, approval_type=approval_type,
        page=page, page_size=page_size,
    )
    return APIResponse(
        success=True, code="OK",
        data=ApprovalListResponse(
            items=[_task_to_response(t) for t in items],
            total=total, page=page, page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
        ),
    )


@router.get("/{task_id}")
async def get_approval(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_role("OPERATOR", "ADMIN")),
) -> APIResponse[ApprovalDetailResponse]:
    """Get approval task detail including action summary."""
    service = ApprovalService(db)
    task = await service.get_task(task_id)
    return APIResponse(success=True, code="OK", data=_task_to_detail(task))


# ── Decide ─────────────────────────────────────────────────────────────

@router.post("/{task_id}/approve")
async def approve_task(
    task_id: uuid.UUID,
    req: ApprovalDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[ApprovalTaskResponse]:
    """Approve a pending approval task. Uses optimistic locking."""
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/approvals/{task_id}/approve"
    rhash = compute_request_hash("POST", path, {"task_id": str(task_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(
        op_id, "approval_decide", idempotency_key, rhash,
    )
    if cached is not None:
        body = cached.get("body") or {}
        return APIResponse(success=True, code="OK", data=body)

    service = ApprovalService(db)
    task = await service.approve(
        task_id=task_id,
        decided_by=op_id,
        expected_version=req.expected_version,
        decision_reason=req.decision_reason,
    )

    result = _task_to_response(task)
    await idem_service.complete(
        op_id, "approval_decide", idempotency_key, 200,
        result.model_dump(mode="json"), task_id,
    )
    return APIResponse(success=True, code="OK", message="Approved", data=result)


@router.post("/{task_id}/reject")
async def reject_task(
    task_id: uuid.UUID,
    req: ApprovalDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[ApprovalTaskResponse]:
    """Reject a pending approval task. Uses optimistic locking."""
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/approvals/{task_id}/reject"
    rhash = compute_request_hash("POST", path, {"task_id": str(task_id)}, {}, req.model_dump())

    cached = await idem_service.acquire_or_get_cached(
        op_id, "approval_decide", idempotency_key, rhash,
    )
    if cached is not None:
        body = cached.get("body") or {}
        return APIResponse(success=True, code="OK", data=body)

    service = ApprovalService(db)
    task = await service.reject(
        task_id=task_id,
        decided_by=op_id,
        expected_version=req.expected_version,
        decision_reason=req.decision_reason,
    )

    result = _task_to_response(task)
    await idem_service.complete(
        op_id, "approval_decide", idempotency_key, 200,
        result.model_dump(mode="json"), task_id,
    )
    return APIResponse(success=True, code="OK", message="Rejected", data=result)


@router.post("/{task_id}/execute")
async def execute_approval(
    task_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    """Execute the approved business action using the stored payload.

    Re-runs the tool with the original sanitized_action_payload.
    Tool-level idempotency prevents duplicate execution.
    """
    op_id = uuid.UUID(current_user["sub"])
    idem_service = IdempotencyService(db)
    path = f"/api/v1/admin/approvals/{task_id}/execute"
    rhash = compute_request_hash("POST", path, {"task_id": str(task_id)}, {}, None)

    cached = await idem_service.acquire_or_get_cached(
        op_id, "approval_execute", idempotency_key, rhash,
    )
    if cached is not None:
        body = cached.get("body") or {}
        return APIResponse(success=True, code="OK", data=body)

    from app.agent.graph import build_agent_graph
    from app.agent.orchestrator import AgentOrchestrator
    from app.database.session import _get_session_factory

    factory = _get_session_factory()
    graph = build_agent_graph()  # type: ignore[no-untyped-call]
    orchestrator = AgentOrchestrator(session_factory=factory, graph=graph)

    result = await orchestrator.execute_approved_action(
        approval_task_id=task_id,
        executed_by=op_id,
    )

    await idem_service.complete(op_id, "approval_execute", idempotency_key, 200, result, task_id)
    return APIResponse(success=True, code="OK", message="Action executed", data=result)
