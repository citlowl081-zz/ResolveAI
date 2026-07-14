"""select_tools node — deterministic mapping from intent to tool list."""


from app.agent.state import AgentState


async def select_tools(state: AgentState) -> AgentState:
    state["current_node"] = "select_tools"
    state.setdefault("node_timings", []).append({"node": "select_tools"})
    context = state.get("context") or {}
    has_confirm = bool(state.get("confirm_action_id"))

    planned: list[dict] = []

    # Determine if we have an order to query
    recent_orders = context.get("orders", [])
    if recent_orders:
        # Use the most recent order for context
        order_id = recent_orders[0].get("id")
        if order_id:
            planned.append({
                "tool_name": "get_order",
                "tool_input": {"order_id": order_id},
            })
            planned.append({
                "tool_name": "get_logistics",
                "tool_input": {"order_id": order_id},
            })
            planned.append({
                "tool_name": "list_after_sales_tickets",
                "tool_input": {"order_id": order_id},
            })
    else:
        planned.append({
            "tool_name": "list_orders",
            "tool_input": {"page": 1, "page_size": 5},
        })

    # If confirm_action_id is valid, include the confirmed write tool
    if has_confirm and state.get("pending_action_valid"):
        pa = state["pending_action"]
        if pa:
            planned.append({
                "tool_name": pa["tool_name"],
                "tool_input": pa["canonical_tool_input"],
                "is_confirmed": True,
            })

    state["planned_tools"] = planned
    return state
