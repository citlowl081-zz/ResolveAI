"""Agent customer API — create sessions, send messages, close sessions."""

import hashlib
import json
import uuid

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
    from app.llm.factory import build_model_provider

    graph = build_agent_graph()  # type: ignore[no-untyped-call]
    factory = _get_session_factory()
    provider = build_model_provider(settings)

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

    body: dict = {"message": req.message}
    if req.client_message_id:
        body["client_message_id"] = str(req.client_message_id)
    rhash = _compute_body_hash(body)

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
    if req.client_message_id:
        body["client_message_id"] = str(req.client_message_id)
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
    from app.repositories.agent_message import AgentMessageRepository
    msg_repo = AgentMessageRepository(db)
    summaries = [await _session_to_summary(s, msg_repo) for s in items]
    return APIResponse(success=True, code="OK", data={
        "items": summaries,
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
    items, total = await msg_repo.list_customer_history(
        session_id, page, page_size, before_sequence,
    )
    active_action = (sess.context_snapshot or {}).get("pending_action")
    return APIResponse(success=True, code="OK", data={
        "items": [_msg_to_dict(m, active_action) for m in items],
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


async def _session_to_summary(sess, msg_repo) -> dict:  # type: ignore[no-untyped-def]
    first = await msg_repo.get_first_user_message(sess.id)
    last = await msg_repo.get_last_customer_message(sess.id)
    message_count = await msg_repo.count_customer_messages(sess.id)
    title = _preview(first.content if first else "新对话", 28)
    return {
        "session_id": str(sess.id),
        "title": title or "新对话",
        "status": sess.status,
        "message_count": message_count,
        "last_message_preview": _preview(last.content if last else "", 60),
        "created_at": sess.created_at.isoformat() if sess.created_at else None,
        "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
    }


def _preview(content: str, limit: int) -> str:
    compact = " ".join(content.split())
    return compact if len(compact) <= limit else f"{compact[:limit]}…"


def _msg_to_dict(msg, active_action: dict | None = None) -> dict:  # type: ignore[no-untyped-def]
    metadata = msg.message_metadata or {}
    citations = metadata.get("citations") if isinstance(metadata.get("citations"), list) else []
    proposed_actions = metadata.get("proposed_actions")
    raw_actions: list = proposed_actions if isinstance(proposed_actions, list) else []
    actions: list[dict] = []
    for raw in raw_actions:
        if not isinstance(raw, dict):
            continue
        action = {
            key: raw.get(key)
            for key in ("action_id", "tool_name", "description", "status", "expires_at")
        }
        if active_action and active_action.get("action_id") == action["action_id"]:
            action["status"] = active_action.get("status", action["status"])
        elif str(action.get("status", "")).lower() == "pending_confirmation":
            action["status"] = "CONSUMED"
        actions.append(action)
    return {
        "message_id": str(msg.id),
        "role": msg.role,
        "content": msg.content,
        "sequence_number": msg.sequence_number,
        "citations": citations,
        "proposed_actions": actions,
        "trace_id": metadata.get("trace_id"),
        "delivery_status": metadata.get("delivery_status", "sent"),
        "client_message_id": metadata.get("client_message_id"),
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
