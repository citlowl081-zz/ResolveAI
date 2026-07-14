"""Admin agent observability API — traces and tool logs."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.common import APIResponse
from app.security.dependencies import require_role

router = APIRouter(prefix="/admin/agent", tags=["admin-agent"])


@router.get("/traces", status_code=200)
async def list_traces(
    session_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """List agent traces (OPERATOR, ADMIN only)."""
    from app.repositories.agent_trace import AgentTraceRepository
    repo = AgentTraceRepository(db)
    items, total = await repo.list_all(page, page_size, session_id=session_id)
    return APIResponse(success=True, code="OK", data={
        "items": [_trace_to_dict(t) for t in items],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
    })


@router.get("/traces/{trace_id}", status_code=200)
async def get_trace_detail(
    trace_id: uuid.UUID,
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Get full trace detail with ordered node executions."""
    from app.repositories.agent_trace import AgentTraceRepository
    repo = AgentTraceRepository(db)
    traces = await repo.get_by_trace_id(trace_id)
    if not traces:
        from app.exceptions import NotFoundError
        raise NotFoundError("Trace not found")
    return APIResponse(success=True, code="OK", data={
        "trace_id": str(trace_id),
        "nodes": [_trace_to_dict(t) for t in traces],
    })


@router.get("/tool-logs", status_code=200)
async def list_tool_logs(
    session_id: uuid.UUID | None = Query(None),
    trace_id: uuid.UUID | None = Query(None),
    tool_name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """List tool logs (OPERATOR, ADMIN only)."""
    from app.repositories.agent_tool_log import AgentToolLogRepository
    repo = AgentToolLogRepository(db)
    items, total = await repo.list_all(
        page, page_size, session_id=session_id, trace_id=trace_id,
        tool_name=tool_name,
    )
    return APIResponse(success=True, code="OK", data={
        "items": [_tool_log_to_dict(tl) for tl in items],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
    })


@router.get("/tool-logs/{tool_log_id}", status_code=200)
async def get_tool_log_detail(
    tool_log_id: uuid.UUID,
    current_user: dict = Depends(require_role("OPERATOR", "ADMIN")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Get single tool log detail."""
    from sqlalchemy import select

    from app.models.agent_tool_log import AgentToolLog
    result = await db.execute(select(AgentToolLog).where(AgentToolLog.id == tool_log_id))
    tl = result.scalar_one_or_none()
    if tl is None:
        from app.exceptions import NotFoundError
        raise NotFoundError("Tool log not found")
    return APIResponse(success=True, code="OK", data=_tool_log_to_dict(tl))


# ── Helpers ──────────────────────────────────────────────────────────

def _trace_to_dict(t) -> dict:  # type: ignore[no-untyped-def]
    return {
        "id": str(t.id),
        "session_id": str(t.session_id),
        "turn_id": str(t.turn_id),
        "trace_id": str(t.trace_id),
        "node_name": t.node_name,
        "sequence": t.sequence,
        "duration_ms": t.duration_ms,
        "is_success": t.is_success,
        "error_code": t.error_code,
        "routing_decision": t.routing_decision,
        "llm_call": t.llm_call,
        "tool_calls_summary": t.tool_calls_summary,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _tool_log_to_dict(tl) -> dict:  # type: ignore[no-untyped-def]
    return {
        "id": str(tl.id),
        "session_id": str(tl.session_id),
        "turn_id": str(tl.turn_id),
        "message_id": str(tl.message_id),
        "trace_id": str(tl.trace_id),
        "tool_call_id": tl.tool_call_id,
        "tool_name": tl.tool_name,
        "is_success": tl.is_success,
        "error_code": tl.error_code,
        "error_message": tl.error_message,
        "duration_ms": tl.duration_ms,
        "retry_count": tl.retry_count,
        "created_at": tl.created_at.isoformat() if tl.created_at else None,
    }
