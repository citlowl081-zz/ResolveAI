"""AgentOrchestrator — preflight, turn lifecycle, crash recovery, trace writing.

Owns the async_sessionmaker. Manages all short-transaction boundaries.
LangGraph nodes call back into the orchestrator for DB access.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.state import AgentState
from app.config.settings import settings
from app.exceptions import AppError, ConflictError, NotFoundError
from app.llm.provider import ModelProvider
from app.models.agent_message import AgentMessage
from app.models.agent_session import AgentSession
from app.models.agent_trace import AgentTrace
from app.models.enums import MessageRole
from app.repositories.agent_message import AgentMessageRepository
from app.repositories.agent_session import AgentSessionRepository
from app.repositories.agent_trace import AgentTraceRepository
from app.services.idempotency import IdempotencyService

# ── Exception classification ─────────────────────────────────────────

TERMINAL_ERROR_CODES = frozenset({
    "RESOURCE_NOT_FOUND", "BUSINESS_CONFLICT", "IDEMPOTENCY_CONFLICT",
    "ACTION_EXPIRED", "ACTION_ALREADY_CONSUMED", "ACTION_NOT_FOUND",
    "TOOL_EXECUTION_FAILED", "SESSION_CLOSED", "AGENT_LOOP_LIMIT",
    "INVALID_TOOL_ARGUMENTS", "TOOL_NOT_FOUND", "TOOL_FORBIDDEN",
})

RECOVERABLE_ERROR_CODES = frozenset({
    "TOOL_TIMEOUT", "LLM_ERROR",
})


def _classify_exception(exc: Exception) -> str:
    """Return 'terminal', 'recoverable', or 'corruption'."""
    if isinstance(exc, AppError):
        code = getattr(exc, "code", "")
        if code in TERMINAL_ERROR_CODES:
            return "terminal"
        if code in RECOVERABLE_ERROR_CODES:
            return "recoverable"
    # OOM, CancelledError, network errors, etc.
    return "recoverable"


def _compute_key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


# ── Orchestrator ──────────────────────────────────────────────────────

class AgentOrchestrator:
    """Owns turn lifecycle, transaction boundaries, and LangGraph execution."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        graph: Any,  # Compiled LangGraph graph
        llm: ModelProvider | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.graph = graph
        self.llm = llm

    # ── Public entry point ──────────────────────────────────────────

    async def run(
        self,
        *,
        user_id: uuid.UUID,
        user_role: str,
        user_message: str,
        session_id: uuid.UUID | None,
        confirm_action_id: str | None,
        idempotency_key: str,
        request_hash: str,
    ) -> dict:
        """Execute one Agent turn. Called from FastAPI router."""
        turn_id = uuid.uuid4()
        trace_id = uuid.uuid4()

        # ── Preflight TX-A ──────────────────────────────────────────
        async with self.session_factory() as session:
            preflight_result = await self._preflight(
                session, user_id, user_role, user_message,
                session_id, confirm_action_id, idempotency_key,
                request_hash, turn_id, trace_id,
            )
            if preflight_result.get("cached_response"):
                return preflight_result["cached_response"]  # type: ignore[no-any-return]
            if preflight_result.get("error"):
                raise preflight_result["error"]
            await session.commit()

        session_id_val = uuid.UUID(preflight_result["session_id"])
        pending_action = preflight_result.get("pending_action")
        pending_action_valid = preflight_result.get("pending_action_valid", False)

        # ── Build initial state ─────────────────────────────────────
        initial_state: AgentState = {
            "user_message": user_message,
            "user_id": str(user_id),
            "user_role": user_role,
            "session_id": str(session_id_val),
            "confirm_action_id": confirm_action_id,
            "idempotency_key": idempotency_key,
            "session": preflight_result.get("session_dict"),
            "session_status": preflight_result.get("session_status", "ACTIVE"),
            "turn_id": str(turn_id),
            "trace_id": str(trace_id),
            "trace_sequence": 0,
            "pending_action": pending_action,
            "pending_action_valid": pending_action_valid,
            "user_profile": None,
            "recent_orders": None,
            "pending_tickets": None,
            "context": None,
            "context_messages": None,
            "intent": None,
            "confidence": None,
            "extracted_entities": None,
            "planned_tools": None,
            "authorized_tools": None,
            "forbidden_tools": None,
            "tool_results": None,
            "assistant_tool_message_id": None,
            "response_text": None,
            "proposed_actions": None,
            "current_node": "receive_message",
            "loop_count": 0,
            "max_loops": settings.agent_max_loops_per_turn,
            "max_tools_per_turn": settings.agent_max_tools_per_turn,
            "errors": [],
            "injection_detected": False,
            "terminal_error": False,
            "terminal_error_code": None,
            "terminal_error_message": None,
            "node_timings": [],
            "_pending_action_for_snapshot": None,
        }

        # ── Run LangGraph ───────────────────────────────────────────
        from app.agent.provider import set_provider
        set_provider(self.llm)
        try:
            result_state = await self.graph.ainvoke(initial_state)

            # ── TX-B: Persist response + clear turn ────────────────
            response_text = result_state.get("response_text", "")
            tool_results = result_state.get("tool_results")
            tool_msgs = None
            if tool_results:
                tool_msgs = [
                    {
                        "tool_call_id": tr.get("tool_call_id", ""),
                        "data": tr.get("data"),
                        "is_success": tr.get("is_success"),
                    }
                    for tr in tool_results
                ]

            await self.complete_turn(result_state, response_text, tool_msgs)

            return await self._build_success_response(result_state)
        except Exception as exc:
            return await self._handle_exception(
                exc, initial_state, turn_id, trace_id,
                user_id, idempotency_key, request_hash,
            )

    # ── Preflight ───────────────────────────────────────────────────

    async def _preflight(
        self, session: AsyncSession,
        user_id: uuid.UUID, user_role: str, user_message: str,
        session_id_in: uuid.UUID | None, confirm_action_id: str | None,
        idempotency_key: str, request_hash: str,
        turn_id: uuid.UUID, trace_id: uuid.UUID,
    ) -> dict:
        repo = AgentSessionRepository(session)
        msg_repo = AgentMessageRepository(session)
        idem_service = IdempotencyService(session)

        # 1. API idempotency
        cached = await idem_service.acquire_or_get_cached(
            user_id, "agent_message", idempotency_key, request_hash,
        )
        if cached is not None:
            body = cached.get("body") or {}
            return {"cached_response": body}

        # 2. Load or create session
        if session_id_in:
            sess = await repo.get_by_id(session_id_in)
            if sess is None:
                return {"error": NotFoundError("Session not found")}
            if str(sess.user_id) != str(user_id):
                return {"error": NotFoundError("Session not found")}
            is_new_session = False
        else:
            sess = AgentSession(user_id=user_id)
            await repo.save(sess)
            is_new_session = True

        # 3. Bind resource_id early
        if is_new_session:
            await idem_service.bind_resource(user_id, "agent_message", idempotency_key, sess.id)

        # 4. Validate session status
        if not is_new_session and sess.status == "EXPIRED":
            sess.status = "EXPIRED"
            return {"error": ConflictError("Session has expired")}
        if not is_new_session and sess.status == "COMPLETED":
            return {"error": ConflictError("Session is closed")}

        # 5. Acquire turn
        key_hash = _compute_key_hash(idempotency_key)
        updated = await repo.try_acquire_turn(
            sess.id, turn_id, trace_id, key_hash, request_hash,
        )
        if updated is None:
            return {"error": ConflictError("Another request is processing for this session")}

        # 6. Load pending_action if confirm_action_id provided
        pending_action = None
        pending_action_valid = False
        if confirm_action_id:
            cs = sess.context_snapshot or {}
            pa = cs.get("pending_action")
            if pa and pa.get("action_id") == confirm_action_id:
                from app.agent.pending_action_builder import validate_pending_action
                is_valid, _ = validate_pending_action(pa, confirm_action_id)
                pending_action = pa
                pending_action_valid = is_valid

        # 7. Save USER message
        seq = await msg_repo.get_next_sequence(sess.id)
        user_msg = AgentMessage(
            session_id=sess.id, turn_id=turn_id,
            role=MessageRole.USER.value, content=user_message,
            sequence_number=seq, turn_sequence=0,
        )
        await msg_repo.save(user_msg)
        await repo.update_message_count(sess.id, 1)

        return {
            "session_id": str(sess.id),
            "session_dict": {
                "id": str(sess.id), "user_id": str(sess.user_id),
                "status": sess.status, "context_snapshot": sess.context_snapshot,
                "message_count": sess.message_count, "version": sess.version,
                "active_turn_id": str(sess.active_turn_id) if sess.active_turn_id else None,
            },
            "session_status": sess.status,
            "pending_action": pending_action,
            "pending_action_valid": pending_action_valid,
            "user_msg_sequence": seq,
        }

    # ── Success response ────────────────────────────────────────────

    async def _build_success_response(self, state: AgentState) -> dict:
        return {
            "session_id": state["session_id"],
            "messages": state.get("context_messages", []),
            "proposed_actions": state.get("proposed_actions") or [],
            "trace_id": state["trace_id"],
        }

    # ── Exception handling ──────────────────────────────────────────

    async def _handle_exception(
        self, exc: Exception, state: AgentState,
        turn_id: uuid.UUID, trace_id: uuid.UUID,
        user_id: uuid.UUID, idempotency_key: str, request_hash: str,
    ) -> dict:
        category = _classify_exception(exc)
        session_id = uuid.UUID(state["session_id"])

        if category == "terminal":
            return await self._handle_terminal_error(
                exc, state, turn_id, trace_id, user_id, idempotency_key,
            )
        elif category == "recoverable":
            await self._handle_recoverable_interruption(
                exc, state, turn_id, trace_id,
            )
            # Re-raise so the HTTP layer returns 500/503
            raise
        else:
            # Corruption — log and return 500
            await self._handle_state_corruption(session_id, turn_id, exc)
            raise AppError("AGENT_TURN_STATE_CORRUPTED: Internal state inconsistency")

    async def _handle_terminal_error(
        self, exc: Exception, state: AgentState,
        turn_id: uuid.UUID, trace_id: uuid.UUID,
        user_id: uuid.UUID, idempotency_key: str,
    ) -> dict:
        """Atomically: save error msg + complete idempotency + clear turn."""
        session_id = uuid.UUID(state["session_id"])
        code = getattr(exc, "code", "TOOL_EXECUTION_FAILED")
        message = str(exc)

        async with self.session_factory() as session:
            msg_repo = AgentMessageRepository(session)
            sess_repo = AgentSessionRepository(session)

            # Save error message
            seq = await msg_repo.get_next_sequence(session_id)
            error_msg = AgentMessage(
                session_id=session_id, turn_id=turn_id,
                role=MessageRole.ASSISTANT.value,
                content=f"抱歉，{message}",
                sequence_number=seq, turn_sequence=100,
            )
            await msg_repo.save(error_msg)

            # Complete idempotency
            idem_service = IdempotencyService(session)
            await idem_service.complete(
                user_id, "agent_message", idempotency_key,
                response_status=409 if code == "BUSINESS_CONFLICT" else 400,
                response_body={"code": code, "message": message},
            )

            # Clear turn
            await sess_repo.clear_active_turn(session_id, turn_id)

            await session.commit()

        return {
            "session_id": str(session_id),
            "error": {"code": code, "message": message},
        }

    async def _handle_recoverable_interruption(
        self, exc: Exception, state: AgentState,
        turn_id: uuid.UUID, trace_id: uuid.UUID,
    ) -> None:
        """Set expires_at=NOW() and persist failure traces. Preserve turn identity."""
        session_id = uuid.UUID(state["session_id"])

        async with self.session_factory() as session:
            sess_repo = AgentSessionRepository(session)
            trace_repo = AgentTraceRepository(session)

            # Write failure traces for unrecorded nodes
            await self._persist_failure_traces(
                session, trace_repo, state, trace_id, turn_id, exc,
            )

            # Set turn expired (preserves active_turn_id, trace_id, key_hash, etc.)
            await sess_repo.set_turn_expired(session_id, turn_id)

            await session.commit()

    async def _handle_state_corruption(
        self, session_id: uuid.UUID, turn_id: uuid.UUID, exc: Exception,
    ) -> None:
        """Log corruption trace — no guessing, no auto-recovery."""
        async with self.session_factory() as session:
            trace_repo = AgentTraceRepository(session)
            trace = AgentTrace(
                session_id=session_id,
                turn_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                trace_id=uuid.uuid4(),
                node_name="orchestrator",
                sequence=0,
                is_success=False,
                error_code="AGENT_TURN_STATE_CORRUPTED",
                error_detail={
                    "message": "PROCESSING idempotency but active_turn_id is NULL",
                    "session_id": str(session_id),
                    "exception": str(exc)[:500],
                },
                duration_ms=0,
            )
            await trace_repo.save(trace)
            await session.commit()

    # ── Trace persistence ───────────────────────────────────────────

    async def write_trace(
        self, state: AgentState, node_name: str,
        node_input: dict | None, node_output: dict | None,
        routing_decision: str | None, duration_ms: int,
        is_success: bool = True, error_code: str | None = None,
        error_detail: dict | None = None,
        llm_call: dict | None = None,
        tool_calls_summary: list[dict] | None = None,
    ) -> None:
        """Write a trace row in an independent short transaction."""
        session_id = uuid.UUID(state["session_id"])
        turn_id = uuid.UUID(state["turn_id"])
        trace_id = uuid.UUID(state["trace_id"])
        seq = state.get("trace_sequence", 0)

        async with self.session_factory() as session:
            trace_repo = AgentTraceRepository(session)
            from app.agent.sanitization import strip_pii_from_dict
            trace = AgentTrace(
                session_id=session_id, turn_id=turn_id,
                trace_id=trace_id, node_name=node_name,
                sequence=seq,
                node_input=strip_pii_from_dict(node_input) if node_input else None,
                node_output=strip_pii_from_dict(node_output) if node_output else None,
                routing_decision=routing_decision,
                llm_call=llm_call,
                tool_calls_summary=tool_calls_summary,
                duration_ms=duration_ms, is_success=is_success,
                error_code=error_code, error_detail=error_detail,
            )
            await trace_repo.save(trace)
            await session.commit()

        state["trace_sequence"] = seq + 1

    async def _persist_failure_traces(
        self, session: AsyncSession, trace_repo: Any,
        state: AgentState, trace_id: uuid.UUID, turn_id: uuid.UUID,
        exc: Exception,
    ) -> None:
        """Write failure traces for any nodes that haven't been recorded."""
        recorded_nodes = {t.get("node_name") for t in state.get("node_timings", [])}
        all_nodes = [
            "receive_message", "load_session", "build_context",
            "classify_intent", "select_tools", "authorize_tool",
            "execute_tool", "handle_tool_error", "compose_response",
        ]
        seq = state.get("trace_sequence", 0)
        for node_name in all_nodes:
            if node_name not in recorded_nodes:
                trace = AgentTrace(
                    session_id=uuid.UUID(state["session_id"]),
                    turn_id=turn_id, trace_id=trace_id,
                    node_name=node_name, sequence=seq,
                    is_success=False,
                    error_code="AGENT_CRASH",
                    error_detail={"message": str(exc)[:500]},
                    duration_ms=0,
                )
                await trace_repo.save(trace)
                seq += 1

    # ── TX-P: Save ASSISTANT tool-call message ──────────────────────

    async def save_tool_call_message(
        self, state: AgentState,
        tool_calls: list[dict],
    ) -> str:
        """TX-P: Save the ASSISTANT tool-call message. Returns message_id as str."""
        session_id = uuid.UUID(state["session_id"])
        turn_id = uuid.UUID(state["turn_id"])

        async with self.session_factory() as session:
            msg_repo = AgentMessageRepository(session)
            sess_repo = AgentSessionRepository(session)

            seq = await msg_repo.get_next_sequence(session_id)
            msg = AgentMessage(
                session_id=session_id, turn_id=turn_id,
                role=MessageRole.ASSISTANT.value, content="",
                sequence_number=seq, turn_sequence=10,
                tool_calls=tool_calls,
            )
            await msg_repo.save(msg)
            await sess_repo.update_message_count(session_id, 1)
            await session.commit()
            return str(msg.id)

    # ── TX-B: Complete turn ─────────────────────────────────────────

    async def complete_turn(
        self, state: AgentState, assistant_content: str,
        tool_results_for_messages: list[dict] | None = None,
    ) -> None:
        """TX-B: Save final messages, complete idempotency, clear turn."""
        session_id = uuid.UUID(state["session_id"])
        turn_id = uuid.UUID(state["turn_id"])
        user_id = uuid.UUID(state["user_id"])
        idempotency_key = state["idempotency_key"]
        trace_uuid = uuid.UUID(state["trace_id"])

        # ── Write agent traces from node_timings (short TX before TX-B) ─
        node_timings: list[dict] = state.get("node_timings", [])
        if node_timings:
            async with self.session_factory() as trace_session:
                trace_repo = AgentTraceRepository(trace_session)
                for i, timing in enumerate(node_timings):
                    trace = AgentTrace(
                        session_id=session_id,
                        turn_id=turn_id,
                        trace_id=trace_uuid,
                        node_name=timing.get("node", "unknown"),
                        sequence=i,
                        duration_ms=timing.get("duration_ms", 0),
                        is_success=True,
                        routing_decision=timing.get("routing_decision"),
                        llm_call=timing.get("llm_call"),
                        tool_calls_summary=timing.get("tool_calls_summary"),
                    )
                    await trace_repo.save(trace)
                await trace_session.commit()

        async with self.session_factory() as session:
            msg_repo = AgentMessageRepository(session)
            sess_repo = AgentSessionRepository(session)

            seq = await msg_repo.get_next_sequence(session_id)
            msgs_to_insert = 0

            # TOOL result messages
            if tool_results_for_messages:
                for i, tr in enumerate(tool_results_for_messages):
                    tool_msg = AgentMessage(
                        session_id=session_id, turn_id=turn_id,
                        role=MessageRole.TOOL.value, content="",
                        sequence_number=seq + msgs_to_insert,
                        turn_sequence=20 + i,
                        tool_call_id=tr.get("tool_call_id"),
                        metadata={"result": tr.get("data"), "is_success": tr.get("is_success")},
                    )
                    await msg_repo.save(tool_msg)
                    msgs_to_insert += 1

            # Final ASSISTANT message
            final_msg = AgentMessage(
                session_id=session_id, turn_id=turn_id,
                role=MessageRole.ASSISTANT.value,
                content=assistant_content,
                sequence_number=seq + msgs_to_insert,
                turn_sequence=100,
            )
            await msg_repo.save(final_msg)
            msgs_to_insert += 1

            # Update session
            sess = await sess_repo.get_by_id_for_update(session_id)
            if sess:
                sess.message_count += msgs_to_insert

                # Consume pending_action if applicable
                pending = state.get("pending_action")
                if state.get("pending_action_valid") and pending is not None:
                    cs = dict(sess.context_snapshot or {})
                    pa = dict(pending)
                    pa["status"] = "CONSUMED"
                    cs["pending_action"] = pa
                    sess.context_snapshot = cs

                # Store pending_action from compose_response in context_snapshot
                pending_snapshot = state.get("_pending_action_for_snapshot")
                if pending_snapshot:
                    cs = dict(sess.context_snapshot or {})
                    proposed = state.get("proposed_actions")
                    if "description" not in pending_snapshot and proposed and len(proposed) > 0:
                        pending_snapshot["description"] = proposed[0].get("description", "")
                    cs["pending_action"] = pending_snapshot
                    sess.context_snapshot = cs

                sess.expires_at = datetime.now(UTC) + timedelta(hours=24)

            # Complete idempotency + clear turn
            idem_service = IdempotencyService(session)
            full_response = await self._build_success_response(state)
            await idem_service.complete(
                user_id, "agent_message", idempotency_key,
                response_status=200,
                response_body=full_response,
            )
            await sess_repo.clear_active_turn(session_id, turn_id)

            await session.commit()
