"""Pydantic schemas for the Approval API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ApprovalDecisionRequest(BaseModel):
    """Admin decision on a pending approval task."""

    expected_version: int = Field(..., ge=1)
    decision_reason: str = Field(
        default="", max_length=1000,
        description="Reason for approve/reject (required for reject)",
    )


class ApprovalTaskResponse(BaseModel):
    """Public representation of an approval task.

    Does NOT expose the full sanitized_action_payload — only summary fields.
    """

    id: str
    user_id: str
    agent_session_id: str | None
    turn_id: str | None
    action_id: str
    tool_name: str
    approval_type: str
    status: str
    risk_level: str
    reason: str | None
    requested_by: str
    decided_by: str | None
    decision_reason: str | None
    expires_at: datetime | None
    decided_at: datetime | None
    version: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ApprovalDetailResponse(ApprovalTaskResponse):
    """Admin detail view — includes sanitized payload summary."""

    action_summary: dict | None = Field(
        default=None,
        description="Summary of action_payload: intent + item count",
    )


class ApprovalListResponse(BaseModel):
    """Paginated list of approval tasks."""

    items: list[ApprovalTaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
