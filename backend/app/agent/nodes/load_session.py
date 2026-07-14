"""load_session node — session state is already loaded by preflight."""

from app.agent.state import AgentState


async def load_session(state: AgentState) -> AgentState:
    state["current_node"] = "load_session"
    # Session was loaded and validated in preflight TX-A.
    # state["session"] and state["session_status"] are already populated.
    return state
