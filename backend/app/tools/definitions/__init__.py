"""Tool definitions package.

Each module exports a single ``BaseTool`` subclass.  Call
``register_all(registry)`` once at application startup to populate the
global ``ToolRegistry`` with every customer-facing tool.
"""

from __future__ import annotations

from app.tools.registry import ToolRegistry, set_registry

from .cancel_after_sales_ticket import CancelAfterSalesTicketTool
from .create_after_sales_ticket import CreateAfterSalesTicketTool
from .get_after_sales_ticket import GetAfterSalesTicketTool
from .get_logistics import GetLogisticsTool
from .get_order import GetOrderTool
from .list_after_sales_tickets import ListAfterSalesTicketsTool
from .list_orders import ListOrdersTool


def register_all(registry: ToolRegistry) -> None:
    """Register every customer-facing tool on *registry*.

    If *registry* is ``None``, a new ``ToolRegistry`` is created,
    populated, and set as the module-level singleton so that
    ``get_registry()`` works everywhere.
    """
    if registry is None:
        registry = ToolRegistry()

    registry.register(GetOrderTool())
    registry.register(ListOrdersTool())
    registry.register(GetLogisticsTool())
    registry.register(GetAfterSalesTicketTool())
    registry.register(ListAfterSalesTicketsTool())
    registry.register(CreateAfterSalesTicketTool())
    registry.register(CancelAfterSalesTicketTool())

    set_registry(registry)
