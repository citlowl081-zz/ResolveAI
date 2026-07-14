"""create_after_sales_ticket — submit a new after-sales request (mutating)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RiskLevel, UserRole
from app.services.ticket import TicketService
from app.tools.base import BaseTool, ToolContract


class CreateAfterSalesTicketTool(BaseTool):
    contract = ToolContract(
        tool_name="create_after_sales_ticket",
        description=(
            "Create a new after-sales ticket (return, exchange, refund "
            "request, etc.) for a specific order. The system will "
            "validate eligibility automatically."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The UUID of the order this ticket applies to.",
                },
                "intent": {
                    "type": "string",
                    "description": (
                        "The type of after-sales request. One of: "
                        "LOGISTICS_INQUIRY, PRE_SHIP_REFUND, QUALITY_REFUND, "
                        "EXCHANGE, MISSING_PARTS, OTHER."
                    ),
                },
                "requested_items": {
                    "type": "array",
                    "description": (
                        "List of items to include. Each item must have "
                        "order_item_id, product_id, and quantity."
                    ),
                },
                "customer_request": {
                    "type": "string",
                    "description": "Free-text description of what the customer wants.",
                    "default": "",
                },
            },
            "required": ["order_id", "intent", "requested_items"],
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
        idempotency_operation="agent_tool:create_after_sales_ticket",
        audit_action="create_ticket",
        underlying_service="TicketService",
        possible_error_codes=[
            "NOT_FOUND",
            "VALIDATION_ERROR",
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
        order_id = uuid.UUID(tool_input["order_id"])
        intent = tool_input["intent"]
        requested_items = tool_input["requested_items"]
        customer_request = tool_input.get("customer_request", "")

        svc = TicketService(session)
        full = await svc.create_ticket(
            user_id=user_id,
            order_id=order_id,
            intent=intent,
            requested_items=requested_items,
            customer_request=customer_request,
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
