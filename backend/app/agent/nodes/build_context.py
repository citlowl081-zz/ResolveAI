"""build_context node — load orders, tickets, recent messages for LLM context."""

import uuid

from app.agent.state import AgentState
from app.config.settings import settings
from app.repositories.agent_message import AgentMessageRepository
from app.services.order import OrderService
from app.services.ticket import TicketService


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


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
            recent_messages = [
                {
                    "role": m.role, "content": m.content,
                    "sequence_number": m.sequence_number,
                    "tool_calls": m.tool_calls, "tool_call_id": m.tool_call_id,
                }
                for m in recent_messages_raw
            ]
        except Exception:
            recent_messages = []

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
        if msg.get("tool_calls"):
            import json
            msg_tokens += _estimate_tokens(json.dumps(msg["tool_calls"], sort_keys=True))
        if remaining - msg_tokens < 0:
            break
        selected.append(msg)
        remaining -= msg_tokens
    selected.reverse()

    state["context_messages"] = selected
    state["recent_orders"] = recent_orders
    state["pending_tickets"] = pending_tickets
    state["context"] = {
        "orders": recent_orders,
        "tickets": pending_tickets,
        "message_count": len(selected),
    }

    return state
