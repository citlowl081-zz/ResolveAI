"""Customer Approval API — view own approval task status."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.approval import ApprovalListResponse, ApprovalTaskResponse
from app.schemas.common import APIResponse
from app.security.dependencies import require_role
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["approvals"])


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


@router.get("")
async def list_my_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("CUSTOMER")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ApprovalListResponse]:
    """List the current user's approval tasks."""
    user_id = uuid.UUID(current_user["sub"])
    service = ApprovalService(db)

    items, total = await service.list_user_tasks(
        user_id=user_id, page=page, page_size=page_size,
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
async def get_my_approval(
    task_id: uuid.UUID,
    current_user: dict = Depends(require_role("CUSTOMER")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ApprovalTaskResponse]:
    """Get a single approval task owned by the current user."""
    user_id = uuid.UUID(current_user["sub"])
    service = ApprovalService(db)

    task = await service.get_task_for_user(task_id, user_id)
    return APIResponse(success=True, code="OK", data=_task_to_response(task))
