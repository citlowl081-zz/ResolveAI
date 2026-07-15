"""AgentState TypedDict — shared state across all LangGraph nodes."""

from typing import TypedDict


class AgentState(TypedDict):
    # ── HTTP Input ──
    user_message: str
    user_id: str                       # UUID from JWT
    user_role: str                     # from JWT
    session_id: str                    # UUID
    confirm_action_id: str | None      # UUID or None
    idempotency_key: str               # API-level Idempotency-Key header

    # ── Preflight (populated by orchestrator before graph) ──
    session: dict | None
    session_status: str | None
    turn_id: str
    trace_id: str
    trace_sequence: int
    pending_action: dict | None
    pending_action_valid: bool

    # ── Context ──
    user_profile: dict | None
    recent_orders: list[dict] | None
    pending_tickets: list[dict] | None
    context: dict | None
    context_messages: list[dict] | None

    # ── Intent ──
    intent: str | None
    confidence: float | None
    extracted_entities: dict | None

    # ── Tools ──
    planned_tools: list[dict] | None
    authorized_tools: list[dict] | None
    forbidden_tools: list[dict] | None
    tool_results: list[dict] | None
    assistant_tool_message_id: str | None

    # ── Response ──
    response_text: str | None
    proposed_actions: list[dict] | None
    _pending_action_for_snapshot: dict | None  # Set by compose_response, saved in TX-B

    # ── Policy Citations (Phase 04B) ──
    citations: list[dict] | None

    # ── Control ──
    current_node: str
    loop_count: int
    max_loops: int
    max_tools_per_turn: int
    errors: list[dict]
    injection_detected: bool
    terminal_error: bool
    terminal_error_code: str | None
    terminal_error_message: str | None

    # ── Node timing (for trace) ──
    node_timings: list[dict]
