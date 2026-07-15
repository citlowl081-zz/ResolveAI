"""Pydantic schemas for the Memory API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    """Create a new user memory."""

    memory_type: str = Field(
        ..., pattern=r"^(PREFERENCE|FACT|SUMMARY|COMMITMENT|RISK_PROFILE)$",
        description="Memory category",
    )
    key: str | None = Field(
        default=None, max_length=200,
        description="Stable dedup key — if provided, overwrites an existing ACTIVE memory with the same (type, key)",
    )
    content: str = Field(
        ..., min_length=1, max_length=5000,
        description="Human-readable memory text",
    )
    structured_data: dict | None = Field(
        default=None,
        description="Optional machine-readable metadata",
    )
    source: str = Field(
        default="explicit_api", max_length=100,
        description="Origin of this memory (explicit_api, agent_inferred, session_summary)",
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Confidence score (0.0–1.0)",
    )


class MemoryUpdateRequest(BaseModel):
    """Update an existing memory."""

    content: str | None = Field(
        default=None, min_length=1, max_length=5000,
        description="Updated human-readable memory text",
    )
    structured_data: dict | None = Field(
        default=None,
        description="Updated machine-readable metadata",
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="Updated confidence score",
    )
    status: str | None = Field(
        default=None, pattern=r"^(ACTIVE|ARCHIVED)$",
        description="Updated status",
    )


class MemoryResponse(BaseModel):
    """Public representation of a user memory (no internal IDs beyond memory_id)."""

    id: str
    memory_type: str
    key: str | None
    content: str
    structured_data: dict | None
    source: str
    confidence: float
    status: str
    version: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class MemoryListResponse(BaseModel):
    """Paginated list of user memories."""

    items: list[MemoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
