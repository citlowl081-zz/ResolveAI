"""LangGraph state machine construction for the ResolveAI Agent.

Compiles an 11-node graph with conditional edges for the three flows:
- Flow A: Read-only query
- Flow B: Write proposed (pending_action created)
- Flow C: Write confirmed (confirm_action_id provided)
"""

from langgraph.graph import END, StateGraph

from app.agent.routing import (
    route_after_authorize_tool,
    route_after_classify_intent,
    route_after_execute_tool,
    route_after_handle_tool_error,
    route_after_load_session,
    route_after_receive_message,
    route_after_select_tools,
)
from app.agent.state import AgentState


def build_agent_graph():  # type: ignore[no-untyped-def]
    """Build and compile the LangGraph agent state machine.

    Returns a compiled graph ready for ainvoke().
    """
    graph = StateGraph(AgentState)

    # Import nodes lazily to avoid circular imports
    from app.agent.nodes.authorize_tool import authorize_tool
    from app.agent.nodes.build_context import build_context
    from app.agent.nodes.classify_intent import classify_intent
    from app.agent.nodes.compose_response import compose_response
    from app.agent.nodes.execute_tool import execute_tool
    from app.agent.nodes.handle_tool_error import handle_tool_error
    from app.agent.nodes.load_session import load_session
    from app.agent.nodes.persist_messages import persist_messages
    from app.agent.nodes.receive_message import receive_message
    from app.agent.nodes.select_tools import select_tools

    # ── Add nodes ─────────────────────────────────────────────────
    graph.add_node("receive_message", receive_message)
    graph.add_node("load_session", load_session)
    graph.add_node("build_context", build_context)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("select_tools", select_tools)
    graph.add_node("authorize_tool", authorize_tool)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("handle_tool_error", handle_tool_error)
    graph.add_node("compose_response", compose_response)
    graph.add_node("persist_messages", persist_messages)

    # ── Entry point ───────────────────────────────────────────────
    graph.set_entry_point("receive_message")

    # ── Edges ─────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "receive_message", route_after_receive_message,
        {"load_session": "load_session", "compose_response": "compose_response"},
    )
    graph.add_conditional_edges(
        "load_session", route_after_load_session,
        {"build_context": "build_context", "__end__": END},
    )
    graph.add_edge("build_context", "classify_intent")
    graph.add_conditional_edges(
        "classify_intent", route_after_classify_intent,
        {"select_tools": "select_tools", "compose_response": "compose_response"},
    )
    graph.add_conditional_edges(
        "select_tools", route_after_select_tools,
        {"authorize_tool": "authorize_tool", "compose_response": "compose_response"},
    )
    graph.add_conditional_edges(
        "authorize_tool", route_after_authorize_tool,
        {"execute_tool": "execute_tool", "compose_response": "compose_response"},
    )
    graph.add_conditional_edges(
        "execute_tool", route_after_execute_tool,
        {
            "compose_response": "compose_response",
            "handle_tool_error": "handle_tool_error",
        },
    )
    graph.add_conditional_edges(
        "handle_tool_error", route_after_handle_tool_error,
        {
            "execute_tool": "execute_tool",
            "compose_response": "compose_response",
        },
    )
    graph.add_edge("compose_response", "persist_messages")
    graph.add_edge("persist_messages", END)

    return graph.compile()
