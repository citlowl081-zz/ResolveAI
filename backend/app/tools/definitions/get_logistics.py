"""get_logistics — retrieve tracking information for an order.

This is the ONLY tool that performs an extra ownership check before
calling its underlying service, because ``LogisticsService`` does not
validate ownership internally.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.services.logistics import LogisticsService
from app.services.order import OrderService
from app.tools.base import BaseTool, ToolContract


class GetLogisticsTool(BaseTool):
    contract = ToolContract(
        tool_name="get_logistics",
        description=(
            "Retrieve the logistics (tracking) information for a "
            "specific order. Returns the tracking number, carrier, "
            "current status, location, and event history."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The UUID of the order to query logistics for.",
                },
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "tracking_number": {"type": "string"},
                "carrier": {"type": "string"},
                "status": {"type": "string"},
                "current_location": {"type": "string"},
                "events": {"type": "array"},
            },
        },
        allowed_roles={UserRole.CUSTOMER},
        audit_action="get_logistics",
        underlying_service="LogisticsService",
        possible_error_codes=["NOT_FOUND", "TOOL_TIMEOUT"],
    )

    async def execute(
        self,
        session: AsyncSession,
        tool_input: dict,
        user_id: uuid.UUID,
    ) -> dict:
        order_id = uuid.UUID(tool_input["order_id"])

        # 1. Ownership check: LogisticsService doesn't do this, so we
        #    call OrderService first to verify the customer owns the order.
        order_svc = OrderService(session)
        await order_svc.get_order(order_id, user_id, role="CUSTOMER")

        # 2. Fetch logistics
        logistics_svc = LogisticsService(session)
        full = await logistics_svc.get_logistics(order_id)

        return {
            "tracking_number": full["tracking_number"],
            "carrier": full["carrier"],
            "status": full["status"],
            "current_location": full["current_location"],
            "events": full.get("events", []),
        }
