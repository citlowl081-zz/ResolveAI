"""list_orders — paginate the authenticated customer's orders."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.services.order import OrderService
from app.tools.base import BaseTool, ToolContract


class ListOrdersTool(BaseTool):
    contract = ToolContract(
        tool_name="list_orders",
        description=(
            "List the current customer's orders with pagination. "
            "Each order includes its ID, order number, status, total "
            "amount, and creation timestamp."
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
                    "description": "Number of orders per page.",
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
                            "order_number": {"type": "string"},
                            "status": {"type": "string"},
                            "total_amount": {"type": "string"},
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
        audit_action="list_orders",
        underlying_service="OrderService",
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

        svc = OrderService(session)
        result = await svc.list_my_orders(user_id, page=page, page_size=page_size)

        return {
            "items": [
                {
                    "id": item["id"],
                    "order_number": item["order_number"],
                    "status": item["status"],
                    "total_amount": item["total_amount"],
                    "created_at": item["created_at"],
                }
                for item in result.get("items", [])
            ],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_pages": result["total_pages"],
        }
