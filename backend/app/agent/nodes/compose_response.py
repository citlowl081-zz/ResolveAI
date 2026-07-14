"""compose_response node — generate natural language response from tool results."""

from app.agent.state import AgentState


async def compose_response(state: AgentState) -> AgentState:
    state["current_node"] = "compose_response"

    # If injection was detected, return safe rejection
    if state.get("injection_detected"):
        state["response_text"] = "抱歉，您的消息中包含无法处理的指令。请以自然语言描述您的需求。"
        state["proposed_actions"] = []
        return state

    # If terminal error, return safe error message
    if state.get("terminal_error"):
        code: str = state.get("terminal_error_code") or "TOOL_EXECUTION_FAILED"
        messages: dict[str, str] = {
            "ACTION_NOT_FOUND": "未找到待确认的操作，请重新描述您的需求。",
            "ACTION_EXPIRED": "该操作已过期，请重新确认。",
            "ACTION_ALREADY_CONSUMED": "该操作已执行，无需重复确认。",
            "BUSINESS_CONFLICT": "当前状态下无法执行此操作。",
            "IDEMPOTENCY_CONFLICT": "请求冲突，请重试。",
            "RESOURCE_NOT_FOUND": "未找到相关资源，请检查信息是否正确。",
        }
        state["response_text"] = messages.get(code, "抱歉，处理请求时遇到问题，请稍后重试。")
        state["proposed_actions"] = []
        return state

    # Build response from tool results
    results = state.get("tool_results") or []
    success_results = [r for r in results if r.get("is_success")]
    failed_results = [r for r in results if not r.get("is_success")]
    response_parts: list[str] = []

    # Generate summary from successful tool results
    intent = state.get("intent", "OTHER")
    confirm = state.get("confirm_action_id")

    if confirm and state.get("pending_action_valid"):
        # Flow C: Write was confirmed and executed
        pa = state.get("pending_action") or {}
        tool_name = pa.get("tool_name", "")
        if tool_name == "create_after_sales_ticket":
            # Find the create_ticket result
            for r in success_results:
                raw = r.get("raw_data", {})
                if raw.get("ticket_number"):
                    status = raw.get("status", "")
                    if status == "APPROVED":
                        response_parts.append(f"已为您创建售后工单 {raw['ticket_number']}，状态：已通过审核。")
                    elif status == "REJECTED":
                        reason = raw.get("reject_reason", "不符合条件")
                        response_parts.append(f"工单 {raw['ticket_number']} 已创建，但因 {reason} 未通过自动审核。")
                    elif status == "NEEDS_REVIEW":
                        response_parts.append(f"工单 {raw['ticket_number']} 已创建，需要人工审核。")
                    else:
                        response_parts.append(f"已创建工单 {raw['ticket_number']}。")
                    break
            else:
                response_parts.append("已处理您的确认请求。")
        elif tool_name == "cancel_after_sales_ticket":
            for r in success_results:
                raw = r.get("raw_data", {})
                if raw.get("status") == "CANCELLED":
                    response_parts.append(f"工单 {raw.get('ticket_number', '')} 已取消。")
                    break
            else:
                response_parts.append("已取消工单。")
    else:
        # Flow A/B: Summarize read tool results
        order_info = None
        logistics_info = None
        ticket_info = None

        for r in success_results:
            raw = r.get("raw_data", {})
            if r["tool_name"] == "get_order":
                order_info = raw
            elif r["tool_name"] == "get_logistics":
                logistics_info = raw
            elif r["tool_name"] == "list_after_sales_tickets":
                ticket_info = raw

        if order_info:
            status_map = {
                "PENDING_PAYMENT": "待支付", "PAID": "已支付",
                "SHIPPED": "已发货", "DELIVERED": "已签收",
                "CANCELLED": "已取消", "REFUNDED": "已退款",
            }
            status_cn = status_map.get(order_info.get("status", ""), order_info.get("status", ""))
            response_parts.append(
                f"您的订单 {order_info.get('order_number', '')} 当前状态：{status_cn}，"
                f"金额：{order_info.get('total_amount', '')}元。"
            )

        if logistics_info:
            carrier = logistics_info.get("carrier", "")
            tracking = logistics_info.get("tracking_number", "")
            status = logistics_info.get("status", "")
            if carrier and tracking:
                response_parts.append(f"物流信息：{carrier} {tracking}，状态：{status}。")

        if ticket_info:
            items = ticket_info.get("items", [])
            if items:
                response_parts.append(f"您有 {len(items)} 个相关售后工单。")

        # Flow B: Propose write action if appropriate
        if intent in ("QUALITY_REFUND", "PRE_SHIP_REFUND", "MISSING_PARTS", "EXCHANGE") \
                and not confirm and order_info:
            # LLM would normally produce this. For Phase 03 deterministic mode:
            proposed = {
                "action_id": "",  # Will be filled by PendingActionBuilder
                "tool_name": "create_after_sales_ticket",
                "description": f"为您创建{intent}工单",
                "status": "pending_confirmation",
            }
            state["proposed_actions"] = [proposed]

    if failed_results:
        response_parts.append("部分查询暂时不可用，请稍后重试。")

    if not response_parts:
        response_parts.append("请问还有什么可以帮您的？")

    state["response_text"] = "\n".join(response_parts)
    return state
