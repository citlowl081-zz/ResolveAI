"""Pydantic schemas for Admin Policy management API."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PolicyCreateRequest(BaseModel):
    policy_key: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=20)
    content: str = Field(..., min_length=1)
    issue_types: list[str] = Field(default_factory=list)
    content_summary: str = ""
    effective_date: date
    expiration_date: date | None = None
    source: str = ""
    metadata_filter: dict = Field(default_factory=dict)
    status: str = "DRAFT"  # DRAFT or ACTIVE


class PolicyUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=20)
    content: str = Field(..., min_length=1)
    issue_types: list[str] = Field(default_factory=list)
    content_summary: str = ""
    effective_date: date
    expiration_date: date | None = None
    source: str = ""
    metadata_filter: dict = Field(default_factory=dict)


class PolicyStatusRequest(BaseModel):
    status: str = Field(..., pattern=r"^(ACTIVE|ARCHIVED)$")


class PolicyIngestRequest(BaseModel):
    activate: bool = False
