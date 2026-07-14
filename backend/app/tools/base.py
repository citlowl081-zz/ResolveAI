"""Tool contract, result, and abstract base class for all Agent tools.

Every tool exposed to the LLM must subclass BaseTool, declare a
ToolContract, and return a ToolResult.  The executor (executor.py) uses
the contract to enforce timeouts, retries, and idempotency.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RiskLevel, UserRole

# ──────────────────────────────────────────────────────────────────
# ToolContract — static metadata describing one tool
# ──────────────────────────────────────────────────────────────────

@dataclass
class ToolContract:
    """Immutable metadata that the executor, registry, and LLM adapter
    all consult before (and during) tool execution."""

    tool_name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    allowed_roles: set[UserRole] = field(default_factory=lambda: {UserRole.CUSTOMER})
    risk_level: RiskLevel = RiskLevel.LOW
    is_mutating: bool = False
    timeout_seconds: int = 30
    max_retries: int = 0
    retryable_errors: list[str] = field(default_factory=list)
    idempotency_operation: str | None = None
    audit_action: str = ""
    underlying_service: str = ""
    possible_error_codes: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────
# ToolResult — the outcome of a single tool execution
# ──────────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    """Returned by ToolExecutor after running (or retrying) a tool.

    On success ``is_success`` is True and ``data`` holds the projected
    dict.  On failure ``error_code`` and ``error_message`` describe what
    went wrong so the orchestrator can persist a tool-log row.
    """

    is_success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: int = 0
    retry_count: int = 0
    tool_call_id: str | None = None
    idempotency_key: str | None = None
    from_cache: bool = False


# ──────────────────────────────────────────────────────────────────
# BaseTool — every Agent tool must subclass this
# ──────────────────────────────────────────────────────────────────

class BaseTool(ABC):
    """Abstract Agent tool.

    Subclasses:
    * Set ``contract`` as a class-level ``ToolContract``.
    * Implement ``execute(session, tool_input, user_id)``.
    * Call the Service layer only — never touch the DB directly.
    """

    contract: ToolContract

    @abstractmethod
    async def execute(
        self,
        session: AsyncSession,
        tool_input: dict[str, Any],
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Execute the tool against the given session.

        Returns a **projected** dict suitable for the LLM context
        window.  The caller (executor) wraps the result in a
        ``ToolResult``, adds timing/metadata, and handles errors.
        """
        ...
