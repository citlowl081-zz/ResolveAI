"""compose_response node — LLM generation with PendingActionBuilder, template fallback."""

import json
import time
from typing import Any, cast

from app.agent.pending_action_builder import (
    build_pending_action,
    build_proposed_action_response,
)
from app.agent.provider import get_provider
from app.agent.state import AgentState
from app.llm.provider import ChatMessage, ChatRequest


async def compose_response(state: AgentState) -> AgentState:
    state["current_node"] = "compose_response"

    # ── Build citations from policy search tool results ──────────────
    state["citations"] = _build_citations(state)

    # If injection was detected, return safe rejection
    if state.get("injection_detected"):
        state["response_text"] = "抱歉，您的消息中包含无法处理的指令。请以自然语言描述您的需求。"
        state["proposed_actions"] = []
        return _finalize_response(state)

    # If terminal error, return safe error message
    if state.get("terminal_error"):
        code: str = state.get("terminal_error_code") or "TOOL_EXECUTION_FAILED"
        state["response_text"] = _terminal_error_message(code)
        state["proposed_actions"] = []
        return _finalize_response(state)

    provider = get_provider()

    if provider is not None:
        t0 = time.monotonic()
        fallback_used = False
        try:
            response = await _llm_compose(state, provider)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            state.setdefault("node_timings", []).append({
                "node": "compose_response",
                "llm_call": {
                    "model": response.model,
                    "prompt_tokens": response.usage.get("prompt_tokens", 0),
                    "completion_tokens": response.usage.get("completion_tokens", 0),
                    "latency_ms": elapsed_ms,
                },
            })
            if response.content:
                try:
                    parsed = json.loads(response.content)
                    state["response_text"] = parsed.get("response", "")
                    # PendingActionBuilder for write proposals
                    if parsed.get("propose_action"):
                        pa_data = parsed["propose_action"]
                        intent = pa_data.get("intent", state.get("intent", "OTHER"))
                        items_spec = pa_data.get("items", [])
                        description = pa_data.get("description", "")
                        order_ctx = _get_order_context(state)
                        if order_ctx and items_spec:
                            pending = build_pending_action(
                                intent=intent,
                                order_context=order_ctx,
                                items_spec=items_spec,
                                description=description,
                            )
                            if pending:
                                state["proposed_actions"] = [
                                    build_proposed_action_response(pending)
                                ]
                                state.setdefault("_pending_action_for_snapshot", pending)
                            else:
                                state["proposed_actions"] = []
                        else:
                            state["proposed_actions"] = []
                    else:
                        state["proposed_actions"] = []
                    return _finalize_response(state)
                except (json.JSONDecodeError, KeyError):
                    # Non-JSON response — use content as-is
                    state["response_text"] = response.content or ""
                    state["proposed_actions"] = []
                    return _finalize_response(state)
        except Exception:
            fallback_used = True

        if fallback_used:
            state.setdefault("node_timings", []).append({
                "node": "compose_response",
                "fallback": True,
                "reason": "LLM call failed, using template",
            })

    # ── Template fallback ──────────────────────────────────────────
    _template_compose(state)
    return _finalize_response(state)


def _finalize_response(state: AgentState) -> AgentState:
    """Evaluate memory writes and return state — called at every return point."""
    state["memory_changes"] = _evaluate_memory_changes(state)
    return state


async def _llm_compose(state: AgentState, provider: Any) -> Any:
    """Call LLM to generate response and propose actions."""
    results = state.get("tool_results") or []
    intent = state.get("intent", "OTHER")
    confirm = state.get("confirm_action_id")

    # Build context summary from tool results
    context_items: list[str] = []
    for r in results:
        if r.get("is_success") and r.get("data"):
            context_items.append(f"{r['tool_name']} result: {json.dumps(r['data'], ensure_ascii=False)}")

    context_str = "\n".join(context_items) if context_items else "No tool results available."

    system_prompt = (
        "You are an e-commerce after-sales customer service agent. "
        "Generate a helpful, natural Chinese response based on the tool results. "
        "Respond with JSON: {\"response\": \"...\", \"propose_action\": null or {\"intent\": \"...\", \"items\": [{\"product_name\": \"...\", \"quantity\": N, \"reason_code\": \"...\"}], \"description\": \"...\"}}. "
        "Only propose an action (propose_action) if the user clearly needs a refund/exchange/reshipment and has NOT yet confirmed one. "
        "If confirm_action_id was already used, do NOT propose another action."
    )

    user_prompt = (
        f"User message: {state['user_message']}\n"
        f"Detected intent: {intent}\n"
        f"Confirm action ID: {confirm or 'none'}\n"
        f"Tool results:\n{context_str}\n\n"
        "Generate a JSON response with a natural Chinese reply and optionally a proposed action."
    )

    request = ChatRequest(
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ],
        max_tokens=1024,
        temperature=0.3,
    )
    return await provider.chat_structured(request, {
        "type": "object",
        "properties": {
            "response": {"type": "string"},
            "propose_action": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_name": {"type": "string"},
                                "quantity": {"type": "integer"},
                                "reason_code": {"type": "string"},
                            },
                        },
                    },
                    "description": {"type": "string"},
                },
            },
        },
        "required": ["response"],
    })


def _template_compose(state: AgentState) -> None:
    """Template-based fallback response generation."""
    results = state.get("tool_results") or []
    success_results = [r for r in results if r.get("is_success")]
    failed_results = [r for r in results if not r.get("is_success")]
    response_parts: list[str] = []

    intent = state.get("intent", "OTHER")
    confirm = state.get("confirm_action_id")

    if confirm and state.get("pending_action_valid"):
        pa = state.get("pending_action") or {}
        tool_name = pa.get("tool_name", "")
        if tool_name == "create_after_sales_ticket":
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
        order_info = None
        logistics_info = None
        for r in success_results:
            raw = r.get("raw_data", {})
            if r["tool_name"] == "get_order":
                order_info = raw
            elif r["tool_name"] == "get_logistics":
                logistics_info = raw

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
            if carrier and tracking:
                response_parts.append(f"物流信息：{carrier} {tracking}。")

        # Flow B: Propose write action if appropriate (template fallback)
        if intent in ("QUALITY_REFUND", "PRE_SHIP_REFUND", "MISSING_PARTS", "EXCHANGE") \
                and not confirm and order_info is not None:
            ctx_order: dict = cast(dict, order_info)
            items_raw: Any = ctx_order.get("items", [])
            if items_raw:
                pa_template: dict | None = build_pending_action(
                    intent=intent,
                    order_context=ctx_order,
                    items_spec=[{
                        "product_name": items_raw[0].get("product_name", ""),
                        "quantity": 1,
                        "reason_code": "DAMAGED" if intent == "QUALITY_REFUND" else "OTHER",
                    }],
                    description=f"为您创建{intent}工单",
                )
                if pa_template:
                    pa_template["description"] = f"为您创建{intent}工单"
                    state["_pending_action_for_snapshot"] = pa_template
                    state["proposed_actions"] = [build_proposed_action_response(pa_template)]

    if failed_results:
        response_parts.append("部分查询暂时不可用，请稍后重试。")

    if not response_parts:
        response_parts.append("请问还有什么可以帮您的？")

    state["response_text"] = "\n".join(response_parts)


def _terminal_error_message(code: str) -> str:
    messages: dict[str, str] = {
        "ACTION_NOT_FOUND": "未找到待确认的操作，请重新描述您的需求。",
        "ACTION_EXPIRED": "该操作已过期，请重新确认。",
        "ACTION_ALREADY_CONSUMED": "该操作已执行，无需重复确认。",
        "BUSINESS_CONFLICT": "当前状态下无法执行此操作。",
        "IDEMPOTENCY_CONFLICT": "请求冲突，请重试。",
        "RESOURCE_NOT_FOUND": "未找到相关资源，请检查信息是否正确。",
    }
    return messages.get(code, "抱歉，处理请求时遇到问题，请稍后重试。")


def _build_citations(state: AgentState) -> list[dict]:
    """Build structured citation list from search_after_sales_policy results."""
    results = state.get("tool_results") or []
    for r in results:
        if not r.get("is_success"):
            continue
        if r.get("tool_name") != "search_after_sales_policy":
            continue
        data = r.get("data") or {}
        policies = data.get("policies") or []
        citations = []
        for p in policies:
            citations.append({
                "policy_key": p.get("policy_key", ""),
                "version": p.get("version", 0),
                "title": p.get("title", ""),
                "category": p.get("category", ""),
                "snippet": p.get("snippet", ""),
                "similarity_score": p.get("similarity_score", 0.0),
            })
        return citations
    return []


def _get_order_context(state: AgentState) -> dict | None:
    """Extract order data from tool results or context for PendingActionBuilder."""
    results = state.get("tool_results") or []
    for r in results:
        if r.get("is_success") and r["tool_name"] == "get_order":
            raw = r.get("raw_data")
            if isinstance(raw, dict):
                return raw
    ctx = state.get("context") or {}
    if isinstance(ctx, dict):
        orders = ctx.get("orders", [])
        if isinstance(orders, list) and orders:
            first = orders[0]
            if isinstance(first, dict):
                return first
    return None


def _evaluate_memory_changes(state: AgentState) -> list[dict] | None:
    """Evaluate whether this turn should trigger a memory write.

    Uses the rules from memory_decisions.py.  Only applies for CUSTOMER users.
    Never saves for ADMIN or OPERATOR roles.
    """
    if state.get("user_role") != "CUSTOMER":
        return None

    from app.agent.memory_decisions import should_not_save, should_save_memory

    user_message = state.get("user_message", "")
    response_text = state.get("response_text", "")
    intent = state.get("intent")
    tool_results = state.get("tool_results") or []

    # Quick rejection: skip trivial/one-off messages
    if should_not_save(user_message):
        return None

    # Estimate turn count from context messages
    ctx_msgs = state.get("context_messages") or []
    turn_count = max(1, len([m for m in ctx_msgs if m.get("role") == "USER"]))

    do_save, mem_type, content = should_save_memory(
        user_message=user_message,
        response_text=response_text,
        intent=intent,
        tool_results=tool_results,
        turn_count=turn_count,
    )

    if do_save and content:
        return [{
            "memory_type": mem_type,
            "content": content,
            "source": "agent_inferred",
            "confidence": 0.8 if mem_type == "PREFERENCE" else 0.95,
        }]

    return None
