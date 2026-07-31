"""build_context node — load orders, tickets, recent messages, and user memories for LLM context."""

import uuid
from collections.abc import Sequence

from app.agent.sanitization import project_memory_for_llm
from app.agent.state import AgentState
from app.config.settings import settings
from app.models.agent_message import AgentMessage
from app.repositories.agent_message import AgentMessageRepository
from app.services.order import OrderService
from app.services.ticket import TicketService


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def _project_prior_messages(
    messages: Sequence[AgentMessage], current_sequence: int,
) -> list[dict]:
    """Project only prior customer-visible turns into the LLM context."""
    return [
        {
            "role": message.role,
            "content": message.content,
            "sequence_number": message.sequence_number,
            "tool_calls": None,
            "tool_call_id": None,
        }
        for message in messages
        if message.sequence_number < current_sequence
        and message.role in {"USER", "ASSISTANT"}
    ]


async def build_context(state: AgentState) -> AgentState:
    state["current_node"] = "build_context"
    state.setdefault("node_timings", []).append({"node": "build_context"})
    user_id = uuid.UUID(state["user_id"])
    session_id = uuid.UUID(state["session_id"])

    # We need the session factory — it's stored in the orchestrator's config.
    # For now, use a minimal approach: import the global factory.
    from app.database.session import _get_session_factory
    factory = _get_session_factory()

    recent_orders = []
    pending_tickets = []
    recent_messages = []
    user_memories: list[dict] = []

    # Build context in a short read-only transaction
    async with factory() as session:
        try:
            order_service = OrderService(session)
            orders_data = await order_service.list_my_orders(user_id, page=1, page_size=5)
            recent_orders = orders_data.get("items", [])
        except Exception:
            recent_orders = []

        try:
            ticket_service = TicketService(session)
            tickets_data = await ticket_service.list_my_tickets(user_id, page=1, page_size=5)
            pending_tickets = tickets_data.get("items", [])
        except Exception:
            pending_tickets = []

        try:
            msg_repo = AgentMessageRepository(session)
            recent_messages_raw = await msg_repo.list_recent_for_context(session_id, limit=50)
            recent_messages = _project_prior_messages(
                recent_messages_raw, state["user_msg_sequence"],
            )
        except Exception:
            recent_messages = []

        # ── Load user memories (Phase 05) ────────────────────────────
        try:
            from app.services.memory_service import MemoryService
            memory_service = MemoryService(session)
            active_memories = await memory_service.get_active_for_context(user_id, limit=20)
            user_memories = [
                project_memory_for_llm({
                    "memory_type": m.memory_type.value if m.memory_type else "",
                    "key": m.key or "",
                    "content": m.content,
                    "confidence": m.confidence or 1.0,
                })
                for m in active_memories
            ]
        except Exception:
            user_memories = []

        await session.commit()

    # ── In-memory: LLM data minimization + token budget truncation ──
    budget = settings.agent_context_token_budget
    system_prompt_tokens = 500
    current_msg_tokens = _estimate_tokens(state["user_message"])
    reserved = system_prompt_tokens + current_msg_tokens

    # pending_action reservation
    pa = state.get("pending_action")
    if pa and state.get("pending_action_valid"):
        reserved += 200

    selected: list[dict] = []
    remaining = budget - reserved
    for msg in reversed(recent_messages):
        msg_content = msg.get("content", "")
        msg_tokens = _estimate_tokens(msg_content if isinstance(msg_content, str) else "")
        if remaining - msg_tokens < 0:
            break
        selected.append(msg)
        remaining -= msg_tokens
    selected.reverse()

    state["context_messages"] = selected
    state["recent_orders"] = recent_orders
    state["pending_tickets"] = pending_tickets
    state["user_memories"] = user_memories
    state["memory_changes"] = None
    state["context"] = {
        "orders": recent_orders,
        "tickets": pending_tickets,
        "message_count": len(selected),
        "memory_count": len(user_memories),
    }

    return state
