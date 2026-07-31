"""Typed response models for the read-only administration console."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class AdminPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range_days: int
    pending_tickets: int
    today_tickets: int
    pending_approvals: int
    agent_sessions: int
    policy_searches: int
    failed_tool_calls: int
    ticket_trend: list[dict[str, Any]]
    ticket_statuses: list[dict[str, Any]]
    intent_types: list[dict[str, Any]]
    recent_high_risk_approvals: list[dict[str, Any]]
    recent_failed_tools: list[dict[str, Any]]


class SystemStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str
    database: str
    provider: str
    model: str
    embedding_provider: str
    api_key_configured: bool
    base_url_configured: bool
    active_policy_count: int
    latest_policy_update: str | None
    latest_seed: str | None
    latest_tool_failure: str | None
    app_version: str
