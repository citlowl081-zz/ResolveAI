"""get_order — retrieve a single order by ID (customer only)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.services.order import OrderService
from app.tools.base import BaseTool, ToolContract


class GetOrderTool(BaseTool):
    contract = ToolContract(
        tool_name="get_order",
        description=(
            "Retrieve the details of a specific order by its ID. "
            "Returns the order number, status, amounts, timestamps, "
            "and a list of items with product name, quantity, and unit price."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The UUID of the order to retrieve.",
                },
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "order_number": {"type": "string"},
                "status": {"type": "string"},
                "total_amount": {"type": "string"},
                "paid_amount": {"type": "string"},
                "shipping_fee": {"type": "string"},
                "paid_at": {"type": ["string", "null"]},
                "shipped_at": {"type": ["string", "null"]},
                "delivered_at": {"type": ["string", "null"]},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "unit_price": {"type": "string"},
                        },
                    },
                },
            },
        },
        allowed_roles={UserRole.CUSTOMER},
        audit_action="get_order",
        underlying_service="OrderService",
        possible_error_codes=["NOT_FOUND", "TOOL_TIMEOUT"],
    )

    async def execute(
        self,
        session: AsyncSession,
        tool_input: dict,
        user_id: uuid.UUID,
    ) -> dict:
        order_id = uuid.UUID(tool_input["order_id"])

        svc = OrderService(session)
        full = await svc.get_order(order_id, user_id, role="CUSTOMER")

        return {
            "order_number": full["order_number"],
            "status": full["status"],
            "total_amount": full["total_amount"],
            "paid_amount": full["paid_amount"],
            "shipping_fee": full["shipping_fee"],
            "paid_at": full["paid_at"],
            "shipped_at": full["shipped_at"],
            "delivered_at": full["delivered_at"],
            "items": [
                {
                    "product_name": item["product_name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                }
                for item in full.get("items", [])
            ],
        }
