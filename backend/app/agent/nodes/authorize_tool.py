"""authorize_tool node — exact role check against tool's allowed_roles."""

from app.agent.state import AgentState
from app.models.enums import UserRole


async def authorize_tool(state: AgentState) -> AgentState:
    state["current_node"] = "authorize_tool"
    state.setdefault("node_timings", []).append({"node": "authorize_tool"})
    planned = state.get("planned_tools") or []
    user_role_str = state.get("user_role", "CUSTOMER")

    try:
        user_role = UserRole(user_role_str)
    except ValueError:
        user_role = UserRole.CUSTOMER

    # All Phase 03 agent tools are CUSTOMER-only
    CUSTOMER_TOOLS = {
        "get_order", "list_orders", "get_logistics",
        "get_after_sales_ticket", "list_after_sales_tickets",
        "create_after_sales_ticket", "cancel_after_sales_ticket",
        "search_after_sales_policy",
    }

    authorized: list[dict] = []
    forbidden: list[dict] = []

    for tool in planned:
        tool_name = tool["tool_name"]
        if tool_name in CUSTOMER_TOOLS and user_role == UserRole.CUSTOMER:
            authorized.append(tool)
        else:
            forbidden.append(tool)

    state["authorized_tools"] = authorized
    state["forbidden_tools"] = forbidden
    return state
