"""get_after_sales_ticket — retrieve a single after-sales ticket by ID."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.services.ticket import TicketService
from app.tools.base import BaseTool, ToolContract


class GetAfterSalesTicketTool(BaseTool):
    contract = ToolContract(
        tool_name="get_after_sales_ticket",
        description=(
            "Retrieve the details of a specific after-sales ticket by "
            "its ID. Returns the ticket number, intent, status, "
            "creation timestamp, and any rejection information."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "The UUID of the ticket to retrieve.",
                },
            },
            "required": ["ticket_id"],
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
        audit_action="get_ticket",
        underlying_service="TicketService",
        possible_error_codes=["NOT_FOUND", "TOOL_TIMEOUT"],
    )

    async def execute(
        self,
        session: AsyncSession,
        tool_input: dict,
        user_id: uuid.UUID,
    ) -> dict:
        ticket_id = uuid.UUID(tool_input["ticket_id"])

        svc = TicketService(session)
        full = await svc.get_ticket(ticket_id, user_id, role="CUSTOMER")

        return {
            "ticket_number": full["ticket_number"],
            "intent": full["intent"],
            "status": full["status"],
            "created_at": full["created_at"],
            "reject_code": full.get("reject_code"),
            "reject_reason": full.get("reject_reason"),
        }
