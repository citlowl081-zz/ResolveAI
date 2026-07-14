"""execute_tool node — execute authorized tools via Phase 02 Services."""

import time
import uuid

from app.agent.sanitization import project_for_llm, strip_pii_from_dict
from app.agent.state import AgentState
from app.database.session import _get_session_factory
from app.services.logistics import LogisticsService
from app.services.order import OrderService
from app.services.ticket import TicketService


async def execute_tool(state: AgentState) -> AgentState:
    state["current_node"] = "execute_tool"
    authorized = state.get("authorized_tools") or []
    state.setdefault("node_timings", []).append({
        "node": "execute_tool",
        "tool_calls_summary": [
            {"tool_name": t["tool_name"], "tool_input": t.get("tool_input", {})}
            for t in authorized
        ],
    })
    user_id = uuid.UUID(state["user_id"])
    session_id = uuid.UUID(state["session_id"])
    turn_id = uuid.UUID(state["turn_id"])
    trace_id = uuid.UUID(state["trace_id"])

    results: list[dict] = []

    for tool in authorized:
        tool_name = tool["tool_name"]
        tool_input = tool.get("tool_input", {})
        t0 = time.monotonic()

        try:
            result_data = await _execute_single_tool(
                tool_name, tool_input, user_id,
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            # Project for LLM
            projected = project_for_llm(tool_name, result_data)

            results.append({
                "tool_name": tool_name,
                "tool_input": tool_input,
                "is_success": True,
                "data": projected,
                "raw_data": result_data,
                "duration_ms": elapsed_ms,
                "error_code": None,
                "error_message": None,
            })
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            code = getattr(exc, "code", "TOOL_EXECUTION_FAILED")
            results.append({
                "tool_name": tool_name,
                "tool_input": tool_input,
                "is_success": False,
                "data": None,
                "duration_ms": elapsed_ms,
                "error_code": code,
                "error_message": str(exc),
            })

            # Non-retryable errors: set terminal
            if code in ("RESOURCE_NOT_FOUND", "BUSINESS_CONFLICT",
                        "TOOL_FORBIDDEN", "INVALID_TOOL_ARGUMENTS"):
                state["terminal_error"] = True
                state["terminal_error_code"] = code
                state["terminal_error_message"] = str(exc)

    # Write tool logs — get a valid message_id first
    from sqlalchemy import select as sel

    from app.models.agent_message import AgentMessage
    from app.models.agent_tool_log import AgentToolLog

    async with _get_session_factory()() as ref_session:
        ref_result = await ref_session.execute(
            sel(AgentMessage.id).where(
                AgentMessage.session_id == session_id,
                AgentMessage.turn_id == turn_id,
            ).order_by(AgentMessage.sequence_number.asc()).limit(1)
        )
        ref_msg_id = ref_result.scalar_one_or_none()
        if ref_msg_id is None:
            ref_msg_id = uuid.uuid4()  # fallback
        await ref_session.commit()

    for tr in results:
        try:
            async with _get_session_factory()() as log_session:
                log = AgentToolLog(
                    session_id=session_id, turn_id=turn_id,
                    message_id=ref_msg_id,
                    trace_id=trace_id,
                    tool_call_id=tr.get("tool_call_id") or str(uuid.uuid4()),
                    tool_name=tr["tool_name"],
                    tool_input=strip_pii_from_dict(tr.get("tool_input", {})),
                    tool_output=strip_pii_from_dict(tr.get("data", {})) if tr.get("data") else None,
                    is_success=tr["is_success"],
                    error_code=tr.get("error_code"),
                    error_message=tr.get("error_message"),
                    duration_ms=tr.get("duration_ms", 0),
                    retry_count=0,
                )
                log_session.add(log)
                await log_session.commit()
        except Exception:
            pass  # Tool log write failure should not break the main flow

    state["tool_results"] = results
    return state


async def _execute_single_tool(
    tool_name: str, tool_input: dict, user_id: uuid.UUID,
) -> dict:
    factory = _get_session_factory()

    async with factory() as session:
        if tool_name == "get_order":
            order_service = OrderService(session)
            return await order_service.get_order(
                uuid.UUID(tool_input["order_id"]), user_id, "CUSTOMER",
            )
        elif tool_name == "list_orders":
            order_service = OrderService(session)
            result = await order_service.list_my_orders(
                user_id,
                page=tool_input.get("page", 1),
                page_size=tool_input.get("page_size", 5),
            )
            return result
        elif tool_name == "get_logistics":
            # Verify ownership first
            order_service = OrderService(session)
            await order_service.get_order(
                uuid.UUID(tool_input["order_id"]), user_id, "CUSTOMER",
            )
            logistics_service = LogisticsService(session)
            return await logistics_service.get_logistics(
                uuid.UUID(tool_input["order_id"]),
            )
        elif tool_name == "get_after_sales_ticket":
            ticket_service = TicketService(session)
            return await ticket_service.get_ticket(
                uuid.UUID(tool_input["ticket_id"]), user_id, "CUSTOMER",
            )
        elif tool_name == "list_after_sales_tickets":
            ticket_service = TicketService(session)
            return await ticket_service.list_my_tickets(
                user_id,
                page=tool_input.get("page", 1),
                page_size=tool_input.get("page_size", 20),
            )
        elif tool_name == "create_after_sales_ticket":
            ticket_service = TicketService(session)
            result = await ticket_service.create_ticket(
                user_id,
                uuid.UUID(tool_input["order_id"]),
                tool_input["intent"],
                tool_input["requested_items"],
                tool_input.get("customer_request", ""),
                user_agent="agent",
            )
            await session.commit()
            return result
        elif tool_name == "cancel_after_sales_ticket":
            ticket_service = TicketService(session)
            result = await ticket_service.cancel_ticket(
                user_id,
                uuid.UUID(tool_input["ticket_id"]),
                tool_input.get("expected_version", 1),
                user_agent="agent",
            )
            await session.commit()
            return result
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
