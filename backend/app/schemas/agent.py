"""Pydantic schemas for Agent API requests and responses."""

import uuid

from pydantic import BaseModel, Field

# ── Request Schemas ──────────────────────────────────────────────────

class AgentMessageRequest(BaseModel):
    """POST /agent/sessions/{id}/messages request body."""
    message: str = Field(..., min_length=1, max_length=4000,
                         description="User message text")
    confirm_action_id: uuid.UUID | None = Field(
        None, description="Confirm a pending action by its action_id"
    )


class AgentSessionCreateRequest(BaseModel):
    """POST /agent/sessions request body."""
    message: str = Field(..., min_length=1, max_length=4000,
                         description="First user message")


# ── Response Schemas ─────────────────────────────────────────────────

class ProposedActionResponse(BaseModel):
    action_id: str
    tool_name: str
    description: str
    status: str
    expires_at: str | None = None


class AgentMessageResponse(BaseModel):
    role: str
    content: str
    sequence_number: int
    turn_sequence: int | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    metadata: dict | None = None
    created_at: str | None = None


class AgentTurnResponse(BaseModel):
    session_id: str
    messages: list[AgentMessageResponse] = []
    proposed_actions: list[ProposedActionResponse] = []
    trace_id: str


class AgentSessionResponse(BaseModel):
    id: str
    user_id: str
    status: str
    message_count: int
    created_at: str | None = None
    updated_at: str | None = None
    expires_at: str | None = None
    closed_at: str | None = None


class AgentSessionListResponse(BaseModel):
    items: list[AgentSessionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AgentMessageListResponse(BaseModel):
    items: list[AgentMessageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AgentTraceResponse(BaseModel):
    id: str
    session_id: str
    turn_id: str
    trace_id: str
    node_name: str
    sequence: int
    duration_ms: int
    is_success: bool
    error_code: str | None = None
    routing_decision: str | None = None
    llm_call: dict | None = None
    tool_calls_summary: list[dict] | None = None
    created_at: str | None = None


class AgentTraceListResponse(BaseModel):
    items: list[AgentTraceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AgentToolLogResponse(BaseModel):
    id: str
    session_id: str
    turn_id: str
    message_id: str
    trace_id: str
    tool_call_id: str
    tool_name: str
    is_success: bool
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: int
    retry_count: int
    created_at: str | None = None


class AgentToolLogListResponse(BaseModel):
    items: list[AgentToolLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
