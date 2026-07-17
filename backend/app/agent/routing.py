"""Conditional edge routing for the Agent LangGraph state machine."""

from app.agent.state import AgentState


def route_after_receive_message(state: AgentState) -> str:
    if state.get("injection_detected"):
        return "compose_response"
    return "load_session"


def route_after_load_session(state: AgentState) -> str:
    status = state.get("session_status", "")
    if status in ("COMPLETED", "EXPIRED"):
        return "__end__"
    return "build_context"


def route_after_classify_intent(state: AgentState) -> str:
    if state.get("pending_action_valid"):
        return "select_tools"
    confidence = state.get("confidence")
    if confidence is not None and confidence >= 0.6:
        return "select_tools"
    return "compose_response"


def route_after_select_tools(state: AgentState) -> str:
    planned = state.get("planned_tools") or []
    if planned:
        return "authorize_tool"
    return "compose_response"


def route_after_authorize_tool(state: AgentState) -> str:
    authorized = state.get("authorized_tools") or []
    if authorized:
        return "execute_tool"
    return "compose_response"


def route_after_execute_tool(state: AgentState) -> str:
    if state.get("terminal_error"):
        return "compose_response"
    results = state.get("tool_results") or []
    if all(r.get("is_success", False) for r in results):
        return "compose_response"
    return "handle_tool_error"


def route_after_handle_tool_error(state: AgentState) -> str:
    if state.get("retry_tool_execution", False):
        return "execute_tool"
    return "compose_response"
