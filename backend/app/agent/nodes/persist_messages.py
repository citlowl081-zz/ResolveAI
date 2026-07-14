"""persist_messages node — TX-B: save messages, complete turn, clear active_turn."""

from app.agent.state import AgentState


async def persist_messages(state: AgentState) -> AgentState:
    state["current_node"] = "persist_messages"

    # The actual TX-B commit is handled by the orchestrator's complete_turn()
    # method, which is called after the graph finishes.
    # This node is a placeholder — the orchestrator handles persistence
    # outside the LangGraph node to maintain transaction control.

    # For now, just mark the node as complete.
    return state
