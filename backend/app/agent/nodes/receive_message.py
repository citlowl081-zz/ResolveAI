"""receive_message node — validate input, detect prompt injection."""

import re

from app.agent.state import AgentState

INJECTION_PATTERNS = [
    r"ignore (all |your |previous )?instructions",
    r"system prompt",
    r"you are now",
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
]


async def receive_message(state: AgentState) -> AgentState:
    state["current_node"] = "receive_message"

    message = state.get("user_message", "")
    detected = False
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            detected = True
            break

    state["injection_detected"] = detected
    return state
