"""select_tools node — deterministic mapping from intent to tool list."""


from app.agent.state import AgentState


async def select_tools(state: AgentState) -> AgentState:
    state["current_node"] = "select_tools"
    state.setdefault("node_timings", []).append({"node": "select_tools"})
    context = state.get("context") or {}
    has_confirm = bool(state.get("confirm_action_id"))

    planned: list[dict] = []

    if state.get("request_mode") == "CONSULTATION":
        planned.append({
            "tool_name": "search_after_sales_policy",
            "tool_input": {"query": state.get("user_message", ""), "top_k": 5},
        })
        state["planned_tools"] = planned
        state["node_timings"][-1]["routing_decision"] = "tool_route:policy_search"
        state["node_timings"][-1]["tool_calls_summary"] = [
            {"selected_tool": "search_after_sales_policy"}
        ]
        return state

    if has_confirm and state.get("pending_action_valid"):
        pa = state["pending_action"]
        if pa:
            planned.append({
                "tool_name": pa["tool_name"],
                "tool_input": pa["canonical_tool_input"],
                "is_confirmed": True,
            })
        state["planned_tools"] = planned
        state["node_timings"][-1]["routing_decision"] = "tool_route:confirmed_action"
        state["node_timings"][-1]["tool_calls_summary"] = [
            {"selected_tool": item["tool_name"]} for item in planned
        ]
        return state

    # Determine if we have an order to query
    recent_orders = context.get("orders", [])
    if recent_orders:
        selected_order = _select_order_for_message(
            recent_orders, state.get("user_message", ""),
        )
        order_id = selected_order.get("id")
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

    state["planned_tools"] = planned
    state["node_timings"][-1]["routing_decision"] = "tool_route:order_context"
    state["node_timings"][-1]["tool_calls_summary"] = [
        {"selected_tool": item["tool_name"]} for item in planned
    ]
    return state


_PRODUCT_ALIASES: dict[str, tuple[str, ...]] = {
    "耳机": ("headphone", "earphone", "headset"),
    "耳麦": ("headphone", "earphone", "headset"),
    "鞋": ("shoe", "sneaker"),
    "灯": ("lamp", "light"),
    "衣服": ("shirt", "jacket", "clothing"),
    "衣物": ("shirt", "jacket", "clothing"),
}


def _select_order_for_message(orders: list[dict], message: str) -> dict:
    """Prefer an order whose product name matches the customer's wording."""
    normalized = message.lower()
    wanted = {
        alias
        for keyword, aliases in _PRODUCT_ALIASES.items()
        if keyword in normalized
        for alias in aliases
    }
    if not wanted:
        return orders[0]

    for order in orders:
        items = order.get("items") or []
        names = " ".join(
            str(item.get("product_name", "")).lower() for item in items
        )
        if any(alias in names for alias in wanted):
            return order
    return orders[0]
