"""classify_intent node — LLM call for intent classification."""

from app.agent.state import AgentState


async def classify_intent(state: AgentState) -> AgentState:
    state["current_node"] = "classify_intent"
    # In a full implementation, this would call the LLM with structured output.
    # For Phase 03, we use a deterministic fallback based on message content.

    message = (state.get("user_message", "")).lower()

    # Simple keyword-based classification (deterministic fallback)
    if any(kw in message for kw in ["退款", "refund", "退货", "return"]):
        state["intent"] = "QUALITY_REFUND"
        state["confidence"] = 0.8
    elif any(kw in message for kw in ["物流", "logistics", "快递", "tracking", "发货"]):
        state["intent"] = "LOGISTICS_INQUIRY"
        state["confidence"] = 0.8
    elif any(kw in message for kw in ["换货", "exchange"]):
        state["intent"] = "EXCHANGE"
        state["confidence"] = 0.8
    elif any(kw in message for kw in ["缺件", "missing", "少"]):
        state["intent"] = "MISSING_PARTS"
        state["confidence"] = 0.7
    elif any(kw in message for kw in ["订单", "order", "ord-"]):
        state["intent"] = "OTHER"
        state["confidence"] = 0.6
    else:
        state["intent"] = "OTHER"
        state["confidence"] = 0.5

    state["extracted_entities"] = {}
    return state
