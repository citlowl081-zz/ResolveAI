"""classify_intent node — LLM call with structured output, keyword fallback."""

import json
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
                "order_id": {"type": "string"},
                "ticket_id": {"type": "string"},
                "product_ref": {"type": "string"},
            },
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
                            "Provide confidence (0.0-1.0) and any extracted entities "
                            "(order_id, ticket_id, product_ref)."
                        ),
                    ),
                    ChatMessage(role="user", content=message),
                ],
                max_tokens=256,
                temperature=0.0,
            )
            response = await provider.chat_structured(request, INTENT_SCHEMA)
            if response.content:
                parsed = json.loads(response.content)
                state["intent"] = parsed.get("intent", "OTHER")
                state["confidence"] = parsed.get("confidence", 0.5)
                state["extracted_entities"] = parsed.get("extracted_entities", {})
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                # Record LLM trace data
                state.setdefault("node_timings", []).append({
                    "node": "classify_intent",
                    "llm_call": {
                        "model": response.model,
                        "prompt_tokens": response.usage.get("prompt_tokens", 0),
                        "completion_tokens": response.usage.get("completion_tokens", 0),
                        "latency_ms": elapsed_ms,
                    },
                })
                return state
        except Exception:
            fallback_used = True

        if fallback_used:
            # Log fallback in trace
            state.setdefault("node_timings", []).append({
                "node": "classify_intent",
                "fallback": True,
                "reason": "LLM call failed, using keyword matching",
            })

    # ── Keyword fallback (provider is None or LLM call failed) ─────
    _keyword_classify(state, message)
    return state


def _keyword_classify(state: AgentState, message: str) -> None:
    msg = message.lower()
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
