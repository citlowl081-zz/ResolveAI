"""classify_intent node — LLM call with structured output, keyword fallback."""

import json
import re
import time

from app.agent.provider import get_provider
from app.agent.state import AgentState
from app.llm.provider import ChatMessage, ChatRequest

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "LOGISTICS_INQUIRY", "PRE_SHIP_REFUND", "QUALITY_REFUND",
                "EXCHANGE", "MISSING_PARTS", "OTHER",
            ],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "extracted_entities": {
            "type": "object",
            "properties": {
                "order_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "ticket_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "product_ref": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            },
        },
        "request_mode": {
            "type": "string",
            "enum": ["CONSULTATION", "ACTION", "INFORMATION"],
        },
    },
    "required": ["intent", "confidence"],
}


async def classify_intent(state: AgentState) -> AgentState:
    state["current_node"] = "classify_intent"
    message = state.get("user_message", "")
    provider = get_provider()

    if provider is not None:
        t0 = time.monotonic()
        fallback_used = False
        try:
            request = ChatRequest(
                messages=[
                    ChatMessage(
                        role="system",
                        content=(
                            "You are an e-commerce after-sales agent. "
                            "Classify the user's message into one of these intents: "
                            "LOGISTICS_INQUIRY, PRE_SHIP_REFUND, QUALITY_REFUND, "
                            "EXCHANGE, MISSING_PARTS, OTHER. "
                            "For after-sales issues, suggest searching the policy "
                            "knowledge base via search_after_sales_policy tool. "
                            "Provide confidence (0.0-1.0) and any extracted entities "
                            "(order_id, ticket_id, product_ref). Classify policy "
                            "questions as CONSULTATION and only explicit requests to "
                            "apply, create, submit, or execute as ACTION."
                        ),
                    ),
                    ChatMessage(role="user", content=message),
                ],
                max_tokens=2048,
                temperature=0.0,
            )
            response = await provider.chat_structured(request, INTENT_SCHEMA)
            if not response.content:
                raise ValueError("Provider returned empty structured intent")
            if response.content:
                parsed = json.loads(response.content)
                intent = parsed.get("intent")
                confidence = parsed.get("confidence")
                allowed_intents = {
                    "LOGISTICS_INQUIRY", "PRE_SHIP_REFUND", "QUALITY_REFUND",
                    "EXCHANGE", "MISSING_PARTS", "OTHER",
                }
                if intent not in allowed_intents or not isinstance(confidence, int | float):
                    raise ValueError("Invalid structured intent response")
                state["intent"] = intent
                state["confidence"] = float(confidence)
                state["extracted_entities"] = parsed.get("extracted_entities", {})
                state["request_mode"] = _classify_request_mode(
                    message, parsed.get("request_mode"),
                )
                _normalize_post_delivery_refund_intent(state)
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                provider_fallback = bool(response.metadata.get("fallback_used", False))
                # Record LLM trace data
                state.setdefault("node_timings", []).append({
                    "node": "classify_intent",
                    "llm_call": {
                        "provider": provider.provider_name,
                        "model": response.model,
                        "execution_mode": (
                            "mock" if provider.provider_name == "mock" else "real_llm"
                        ),
                        "prompt_tokens": response.usage.get("prompt_tokens", 0),
                        "completion_tokens": response.usage.get("completion_tokens", 0),
                        "latency_ms": elapsed_ms,
                        "real_llm_success": provider.provider_name != "mock",
                        "structured_output_failed": bool(
                            response.metadata.get("structured_output_failed", False)
                        ),
                        "fallback_used": provider_fallback,
                        "fallback_reason": response.metadata.get("fallback_reason"),
                    },
                    "routing_decision": f"intent:{state['intent']} mode:{state['request_mode']}",
                })
                return state
        except Exception as exc:
            fallback_used = True
            fallback_reason = type(exc).__name__

        if fallback_used:
            # Log fallback in trace
            state.setdefault("node_timings", []).append({
                "node": "classify_intent",
                "llm_call": {
                    "provider": provider.provider_name,
                    "execution_mode": "fallback",
                    "real_llm_success": False,
                    "structured_output_failed": True,
                    "fallback_used": True,
                    "fallback_reason": fallback_reason,
                },
                "routing_decision": "fallback:keyword",
            })

    else:
        state.setdefault("node_timings", []).append({
            "node": "classify_intent",
            "llm_call": {
                "provider": "none",
                "execution_mode": "fallback",
                "real_llm_success": False,
                "structured_output_failed": True,
                "fallback_used": True,
                "fallback_reason": "provider_unavailable",
            },
            "routing_decision": "fallback:keyword",
        })

    # ── Keyword fallback (provider is None or LLM call failed) ─────
    _keyword_classify(state, message)
    _normalize_post_delivery_refund_intent(state)
    return state


def _keyword_classify(state: AgentState, message: str) -> None:
    msg = message.lower()
    state["request_mode"] = _classify_request_mode(message)
    if any(kw in msg for kw in ["退款", "refund", "退货", "return"]):
        if any(kw in msg for kw in ["品质", "质量", "quality", "坏", "损坏", "damaged"]):
            state["intent"] = "QUALITY_REFUND"
        else:
            state["intent"] = "PRE_SHIP_REFUND"
        state["confidence"] = 0.8
    elif any(kw in msg for kw in ["物流", "logistics", "快递", "tracking", "发货"]):
        state["intent"] = "LOGISTICS_INQUIRY"
        state["confidence"] = 0.8
    elif any(kw in msg for kw in ["换货", "exchange"]):
        state["intent"] = "EXCHANGE"
        state["confidence"] = 0.8
    elif any(kw in msg for kw in ["缺件", "missing", "少"]):
        state["intent"] = "MISSING_PARTS"
        state["confidence"] = 0.7
    elif any(kw in msg for kw in ["订单", "order", "ord-"]):
        state["intent"] = "OTHER"
        state["confidence"] = 0.6
    else:
        state["intent"] = "OTHER"
        state["confidence"] = 0.5
    state["extracted_entities"] = {}


_ACTION_PATTERNS = (
    re.compile(r"(?:帮我|请帮我|麻烦).*(?:申请|创建|提交|办理).*(?:退款|退货|换货|补发)"),
    re.compile(r"(?:现在|立即).*(?:退掉|退款|退货|换货|补发)"),
    re.compile(r"我要(?:申请|提交|办理|直接).*(?:退款|退货|换货|补发)"),
    re.compile(r"我要(?:退款|退货|换货|补发)"),
    re.compile(r"(?:需要|想要|打算)(?:申请)?(?:退款|退货|换货|补发)"),
    re.compile(r"请给我补发"),
    re.compile(r"确认执行|确认(?:申请|提交|退款|退货|换货|补发)"),
)

_AFTER_SALES_TERMS = ("退款", "退货", "换货", "补发", "七天无理由", "售后")
_CONSULTATION_MARKERS = (
    "能退", "能不能", "能否", "可以", "是否", "还能", "吗", "？",
    "什么", "怎么", "如何", "条件", "流程", "政策", "规则", "了解", "咨询",
)


def _classify_request_mode(message: str, model_mode: object = None) -> str:
    """Apply the deterministic no-write safety boundary after model classification."""
    normalized = message.strip().lower()
    if any(pattern.search(normalized) for pattern in _ACTION_PATTERNS):
        return "ACTION"
    has_after_sales_term = any(term in normalized for term in _AFTER_SALES_TERMS)
    if "能退" in normalized:
        return "CONSULTATION"
    if has_after_sales_term and any(
        marker in normalized for marker in _CONSULTATION_MARKERS
    ):
        return "CONSULTATION"
    if model_mode in {"CONSULTATION", "ACTION", "INFORMATION"}:
        return str(model_mode)
    if has_after_sales_term:
        return "CONSULTATION"
    return "INFORMATION"


def _normalize_post_delivery_refund_intent(state: AgentState) -> None:
    """Do not propose a pre-shipment refund for an already shipped order."""
    if (
        state.get("request_mode") != "ACTION"
        or state.get("intent") != "PRE_SHIP_REFUND"
    ):
        return
    orders = (state.get("context") or {}).get("orders") or []
    if any(str(order.get("status", "")).upper() in {"SHIPPED", "DELIVERED"} for order in orders):
        state["intent"] = "QUALITY_REFUND"
