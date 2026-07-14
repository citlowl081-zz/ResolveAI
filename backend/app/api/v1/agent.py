"""Agent customer API — create sessions, send messages, close sessions."""

import hashlib
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import AgentOrchestrator
from app.database.session import _get_session_factory, get_db
from app.schemas.agent import (
    AgentMessageRequest,
    AgentSessionCreateRequest,
)
from app.schemas.common import APIResponse
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/agent", tags=["agent"])


def _get_orchestrator() -> AgentOrchestrator:
    """Create an AgentOrchestrator with session factory, graph, and LLM provider."""
    from app.agent.graph import build_agent_graph
    from app.config import settings

    graph = build_agent_graph()  # type: ignore[no-untyped-call]
    factory = _get_session_factory()

    # Create provider based on config
    provider: Any = None
    if settings.llm_provider == "anthropic" and settings.llm_api_key:
        from app.llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(
            api_key=settings.llm_api_key,
            default_model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    elif settings.llm_provider == "mock":
        from app.llm.mock_provider import MockProvider
        provider = MockProvider()

    return AgentOrchestrator(session_factory=factory, graph=graph, llm=provider)


@router.post("/sessions", status_code=201)
async def create_session_and_chat(
    req: AgentSessionCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    """Create a new agent session and send the first message."""
    user_id = uuid.UUID(current_user["sub"])
    user_role = current_user.get("role", "CUSTOMER")

    rhash = _compute_body_hash({"message": req.message})

    orchestrator = _get_orchestrator()
    result = await orchestrator.run(
        user_id=user_id,
        user_role=user_role,
        user_message=req.message,
        session_id=None,
        confirm_action_id=None,
        idempotency_key=idempotency_key,
        request_hash=rhash,
    )

    if result.get("error"):
        code = result["error"]["code"]
        if code == "SESSION_CLOSED":
            return APIResponse(success=False, code="CONFLICT",
                              message=result["error"]["message"])
        return APIResponse(success=False, code=code,
                          message=result["error"].get("message", ""))

    return APIResponse(success=True, code="OK", message="Session created",
                       data=result)


@router.post("/sessions/{session_id}/messages", status_code=200)
async def send_message(
    session_id: uuid.UUID,
    req: AgentMessageRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> APIResponse[dict]:
    """Send a message to an existing agent session."""
    user_id = uuid.UUID(current_user["sub"])
    user_role = current_user.get("role", "CUSTOMER")

    body: dict = {"message": req.message}
    if req.confirm_action_id:
        body["confirm_action_id"] = str(req.confirm_action_id)
    rhash = _compute_body_hash(body)

    orchestrator = _get_orchestrator()
    result = await orchestrator.run(
        user_id=user_id,
        user_role=user_role,
        user_message=req.message,
        session_id=session_id,
        confirm_action_id=str(req.confirm_action_id) if req.confirm_action_id else None,
        idempotency_key=idempotency_key,
        request_hash=rhash,
    )

    if result.get("error"):
        code = result["error"]["code"]
        return APIResponse(success=False, code=code,
                          message=result["error"].get("message", ""),
                          data=result)

    return APIResponse(success=True, code="OK", data=result)


@router.get("/sessions", status_code=200)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """List current user's agent sessions."""
    from app.repositories.agent_session import AgentSessionRepository
    repo = AgentSessionRepository(db)
    items, total = await repo.list_by_user(
        uuid.UUID(current_user["sub"]), page, page_size, status,
    )
    return APIResponse(success=True, code="OK", data={
        "items": [_session_to_dict(s) for s in items],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
    })


@router.get("/sessions/{session_id}", status_code=200)
async def get_session(
    session_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Get session detail."""
    from app.repositories.agent_session import AgentSessionRepository
    repo = AgentSessionRepository(db)
    sess = await repo.get_by_id(session_id)
    if sess is None or str(sess.user_id) != current_user["sub"]:
        from app.exceptions import NotFoundError
        raise NotFoundError("Session not found")
    return APIResponse(success=True, code="OK", data=_session_to_dict(sess))


@router.get("/sessions/{session_id}/messages", status_code=200)
async def get_messages(
    session_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    before_sequence: int | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Get message history for a session."""
    from app.repositories.agent_message import AgentMessageRepository
    from app.repositories.agent_session import AgentSessionRepository

    sess_repo = AgentSessionRepository(db)
    sess = await sess_repo.get_by_id(session_id)
    if sess is None or str(sess.user_id) != current_user["sub"]:
        from app.exceptions import NotFoundError
        raise NotFoundError("Session not found")

    msg_repo = AgentMessageRepository(db)
    items, total = await msg_repo.list_by_session(session_id, page, page_size, before_sequence)
    return APIResponse(success=True, code="OK", data={
        "items": [_msg_to_dict(m) for m in items],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
    })


@router.post("/sessions/{session_id}/close", status_code=200)
async def close_session(
    session_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Close an agent session."""
    from datetime import UTC
    from datetime import datetime as dt

    from sqlalchemy import select

    from app.exceptions import NotFoundError
    from app.models.agent_session import AgentSession

    user_id = uuid.UUID(current_user["sub"])

    result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    sess = result.scalar_one_or_none()
    if sess is None or str(sess.user_id) != str(user_id):
        raise NotFoundError("Session not found")

    sess.status = "COMPLETED"
    sess.closed_at = dt.now(UTC)

    resp_data = _session_to_dict(sess)
    return APIResponse(success=True, code="OK",
                       message="Session closed", data=resp_data)


# ── Helpers ──────────────────────────────────────────────────────────

def _compute_body_hash(body: dict) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _session_to_dict(sess) -> dict:  # type: ignore[no-untyped-def]
    return {
        "id": str(sess.id),
        "user_id": str(sess.user_id),
        "status": sess.status,
        "message_count": sess.message_count,
        "created_at": sess.created_at.isoformat() if sess.created_at else None,
        "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
        "expires_at": sess.expires_at.isoformat() if sess.expires_at else None,
        "closed_at": sess.closed_at.isoformat() if sess.closed_at else None,
    }


def _msg_to_dict(msg) -> dict:  # type: ignore[no-untyped-def]
    return {
        "role": msg.role,
        "content": msg.content,
        "sequence_number": msg.sequence_number,
        "turn_sequence": msg.turn_sequence,
        "tool_calls": msg.tool_calls,
        "tool_call_id": msg.tool_call_id,
        "metadata": msg.message_metadata,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
