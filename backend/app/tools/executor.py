"""ToolExecutor — session-scoped tool execution with timeout, retry, and
idempotency-key generation for mutating tools.

The executor is stateless.  It receives an ``async_sessionmaker``,
looks up the tool, creates a fresh session, and runs the tool through
``BaseTool.execute``.  All lifecycle concerns (timeout, retries,
idempotency) belong here so individual tool definitions stay focused
on their service calls.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.exceptions import AppError
from app.tools.base import ToolContract, ToolResult
from app.tools.registry import get_registry


async def execute_tool(
    session_factory: async_sessionmaker,
    tool_name: str,
    tool_input: dict,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    turn_id: uuid.UUID,
    trace_id: uuid.UUID,
    tool_call_id: str,
    action_id: uuid.UUID,
) -> ToolResult:
    """Execute a named tool with timeout, retry, and optional idempotency.

    Parameters
    ----------
    session_factory:
        An ``async_sessionmaker`` bound to the application's engine.
        A fresh session is created for each attempt.
    tool_name:
        The registered name of the tool to run.
    tool_input:
        Already-deserialized argument dict matching the tool's
        ``input_schema``.
    user_id:
        The authenticated user on whose behalf the tool runs.
    session_id:
        The parent ``AgentSession.id`` — used for idempotency-key
        derivation for write tools.
    turn_id:
        The current ``turn_id`` — passed through for logging.
    trace_id:
        The current ``trace_id`` — passed through for tracing.
    tool_call_id:
        A deterministic ID assigned by the orchestrator so tool-call
        messages and tool-logs can be correlated.
    action_id:
        The ``pending_action.id`` — used in the idempotency-key
        derivation so that each distinct action produces a unique key.

    Returns
    -------
    ToolResult
        Always returns a ``ToolResult`` — the caller inspects
        ``is_success`` to decide how to persist the outcome.
    """
    registry = get_registry()
    tool = registry.get(tool_name)
    if tool is None:
        return ToolResult(
            is_success=False,
            error_code="TOOL_NOT_FOUND",
            error_message=f"No tool registered under name '{tool_name}'",
            tool_call_id=tool_call_id,
            idempotency_key=None,
        )

    contract = tool.contract
    wall_start = time.monotonic()

    # ── Idempotency key for mutating tools ───────────────────────
    idempotency_key: str | None = None
    if contract.is_mutating:
        canonical = _canonicalize(tool_input)
        raw = (
            str(session_id)
            + str(action_id)
            + tool_name
            + canonical
        )
        idempotency_key = hashlib.sha256(raw.encode()).hexdigest()

    # ── Retry loop ───────────────────────────────────────────────
    max_attempts = contract.max_retries + 1
    last_error_code: str | None = None
    last_error_message: str | None = None

    for attempt in range(max_attempts):
        try:
            async with session_factory() as session, session.begin():
                result_data = await asyncio.wait_for(
                    tool.execute(session, tool_input, user_id),
                    timeout=contract.timeout_seconds,
                )

            duration_ms = int((time.monotonic() - wall_start) * 1000)
            return ToolResult(
                is_success=True,
                data=result_data,
                duration_ms=duration_ms,
                retry_count=attempt,
                tool_call_id=tool_call_id,
                idempotency_key=idempotency_key,
            )

        except TimeoutError:
            last_error_code = "TOOL_TIMEOUT"
            last_error_message = (
                f"Tool '{tool_name}' timed out after "
                f"{contract.timeout_seconds}s"
            )
            if _should_retry("TOOL_TIMEOUT", contract, attempt):
                continue
            break

        except AppError as exc:
            last_error_code = exc.code
            last_error_message = exc.message
            if _should_retry(exc.code, contract, attempt):
                continue
            break

        except Exception as exc:
            last_error_code = "TOOL_EXECUTION_FAILED"
            last_error_message = str(exc)
            if _should_retry("TOOL_EXECUTION_FAILED", contract, attempt):
                continue
            break

    # ── All attempts exhausted or non-retryable error ────────────
    duration_ms = int((time.monotonic() - wall_start) * 1000)
    return ToolResult(
        is_success=False,
        error_code=last_error_code or "TOOL_EXECUTION_FAILED",
        error_message=last_error_message or "Tool execution failed",
        duration_ms=duration_ms,
        retry_count=min(attempt + 1, max_attempts - 1),
        tool_call_id=tool_call_id,
        idempotency_key=idempotency_key,
    )


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────


def _should_retry(
    error_code: str,
    contract: ToolContract,
    attempt: int,
) -> bool:
    """Return True when the error is retryable and attempts remain."""
    retryable: list[str] = contract.retryable_errors
    max_retries: int = contract.max_retries
    return error_code in retryable and attempt < max_retries


def _canonicalize(obj: object) -> str:
    """Produce a deterministic, sorted JSON string for hashing."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
