"""handle_tool_error node — classify errors, decide retry."""

from app.agent.state import AgentState

RETRYABLE_CODES = {"TOOL_TIMEOUT", "LLM_ERROR"}


async def handle_tool_error(state: AgentState) -> AgentState:
    state["current_node"] = "handle_tool_error"
    state.setdefault("node_timings", []).append({"node": "handle_tool_error"})
    results = state.get("tool_results") or []
    state["loop_count"] = state.get("loop_count", 0) + 1

    for r in results:
        if not r.get("is_success"):
            code = r.get("error_code", "TOOL_EXECUTION_FAILED")
            if code in RETRYABLE_CODES and state["loop_count"] < state.get("max_loops", 3):
                # Will be retried in the next execute_tool iteration
                pass
            else:
                state["errors"].append({
                    "node": "execute_tool",
                    "tool_name": r.get("tool_name"),
                    "error_code": code,
                    "error_message": r.get("error_message", ""),
                })

    return state
