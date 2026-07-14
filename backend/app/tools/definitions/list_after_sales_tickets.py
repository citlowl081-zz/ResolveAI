"""list_after_sales_tickets — paginate the customer's after-sales tickets."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.services.ticket import TicketService
from app.tools.base import BaseTool, ToolContract


class ListAfterSalesTicketsTool(BaseTool):
    contract = ToolContract(
        tool_name="list_after_sales_tickets",
        description=(
            "List the current customer's after-sales tickets with "
            "pagination. Each ticket summary includes its ID, ticket "
            "number, order ID, intent, status, and creation timestamp."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "Page number (1-based).",
                    "default": 1,
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page.",
                    "default": 20,
                },
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "ticket_number": {"type": "string"},
                            "order_id": {"type": "string"},
                            "intent": {"type": "string"},
                            "status": {"type": "string"},
                            "created_at": {"type": ["string", "null"]},
                        },
                    },
                },
                "total": {"type": "integer"},
                "page": {"type": "integer"},
                "page_size": {"type": "integer"},
                "total_pages": {"type": "integer"},
            },
        },
        allowed_roles={UserRole.CUSTOMER},
        audit_action="list_tickets",
        underlying_service="TicketService",
        possible_error_codes=["TOOL_TIMEOUT"],
    )

    async def execute(
        self,
        session: AsyncSession,
        tool_input: dict,
        user_id: uuid.UUID,
    ) -> dict:
        page = int(tool_input.get("page", 1))
        page_size = int(tool_input.get("page_size", 20))

        svc = TicketService(session)
        result = await svc.list_my_tickets(user_id, page=page, page_size=page_size)

        return result  # already projected with the right fields
