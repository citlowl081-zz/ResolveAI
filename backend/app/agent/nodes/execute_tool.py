"""execute_tool node — execute authorized tools via Phase 02 Services."""

import time
import uuid

from app.agent.sanitization import project_for_llm
from app.agent.state import AgentState
from app.database.session import _get_session_factory
from app.services.logistics import LogisticsService
from app.services.order import OrderService
from app.services.ticket import TicketService


async def execute_tool(state: AgentState) -> AgentState:
    state["current_node"] = "execute_tool"
    authorized = state.get("authorized_tools") or []
    user_id = uuid.UUID(state["user_id"])

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
            return await ticket_service.create_ticket(
                user_id,
                uuid.UUID(tool_input["order_id"]),
                tool_input["intent"],
                tool_input["requested_items"],
                tool_input.get("customer_request", ""),
                user_agent="agent",
            )
        elif tool_name == "cancel_after_sales_ticket":
            ticket_service = TicketService(session)
            return await ticket_service.cancel_ticket(
                user_id,
                uuid.UUID(tool_input["ticket_id"]),
                tool_input.get("expected_version", 1),
                user_agent="agent",
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
