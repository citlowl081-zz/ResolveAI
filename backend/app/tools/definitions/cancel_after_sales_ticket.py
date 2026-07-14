"""cancel_after_sales_ticket — cancel a pending after-sales ticket (mutating)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RiskLevel, UserRole
from app.services.ticket import TicketService
from app.tools.base import BaseTool, ToolContract


class CancelAfterSalesTicketTool(BaseTool):
    contract = ToolContract(
        tool_name="cancel_after_sales_ticket",
        description=(
            "Cancel an existing after-sales ticket. The caller must "
            "provide the current version for optimistic concurrency "
            "control."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "The UUID of the ticket to cancel.",
                },
                "expected_version": {
                    "type": "integer",
                    "description": (
                        "The current version number of the ticket. "
                        "Obtained from a prior get/list call."
                    ),
                },
            },
            "required": ["ticket_id", "expected_version"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "ticket_number": {"type": "string"},
                "intent": {"type": "string"},
                "status": {"type": "string"},
                "created_at": {"type": ["string", "null"]},
                "reject_code": {"type": ["string", "null"]},
                "reject_reason": {"type": ["string", "null"]},
            },
        },
        allowed_roles={UserRole.CUSTOMER},
        risk_level=RiskLevel.MEDIUM,
        is_mutating=True,
        timeout_seconds=30,
        max_retries=0,
        idempotency_operation="agent_tool:cancel_after_sales_ticket",
        audit_action="cancel_ticket",
        underlying_service="TicketService",
        possible_error_codes=[
            "NOT_FOUND",
            "CONFLICT",
            "TOOL_TIMEOUT",
        ],
    )

    async def execute(
        self,
        session: AsyncSession,
        tool_input: dict,
        user_id: uuid.UUID,
    ) -> dict:
        ticket_id = uuid.UUID(tool_input["ticket_id"])
        expected_version = int(tool_input["expected_version"])

        svc = TicketService(session)
        full = await svc.cancel_ticket(
            user_id=user_id,
            ticket_id=ticket_id,
            expected_version=expected_version,
            user_agent="agent",
        )

        return {
            "ticket_number": full["ticket_number"],
            "intent": full["intent"],
            "status": full["status"],
            "created_at": full["created_at"],
            "reject_code": full.get("reject_code"),
            "reject_reason": full.get("reject_reason"),
        }
