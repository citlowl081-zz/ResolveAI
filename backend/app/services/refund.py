"""RefundService — atomic refund execution with lock ordering and cumulative cap."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.after_sales_ticket import AfterSalesTicket
from app.models.enums import OrderStatus, RefundType, ResolutionType, TicketStatus
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.refund_record import RefundRecord
from app.repositories.audit_log import AuditLogRepository
from app.repositories.order import OrderRepository
from app.repositories.order_item import OrderItemRepository
from app.repositories.product import ProductRepository
from app.repositories.refund import RefundRepository
from app.repositories.reshipment import ReshipmentRepository
from app.repositories.ticket import TicketRepository
from app.rules.refund_calculator import RefundCalcInput, calculate_refund
from app.rules.state_transitions import validate_ticket_transition


class RefundService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ticket_repo = TicketRepository(session)
        self.order_repo = OrderRepository(session)
        self.order_item_repo = OrderItemRepository(session)
        self.product_repo = ProductRepository(session)
        self.refund_repo = RefundRepository(session)
        self.reshipment_repo = ReshipmentRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def execute_refund(
        self,
        op_id: uuid.UUID,
        ticket_id: uuid.UUID,
        expected_version: int,
        user_agent: str | None = None,
    ) -> dict:
        """Execute refund for an APPROVED ticket. All in one transaction.

        Lock order: ticket → order → order_items → products
        """
        # ── Step 1: Lock ticket FOR UPDATE ──────────────────────────
        ticket = await self.ticket_repo.get_by_id_for_update(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")

        if ticket.version != expected_version:
            raise ConflictError("Ticket was modified by another request; please retry")

        current_status = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)
        validate_ticket_transition(current_status, TicketStatus.COMPLETED.value)

        # ── Step 2: Lock order FOR UPDATE ───────────────────────────
        order_id = ticket.order_id
        order_result = await self.session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        )
        order = order_result.scalar_one_or_none()
        if order is None:
            raise NotFoundError("Order not found")

        order_status = order.status.value if hasattr(order.status, 'value') else str(order.status)
        if order_status == "REFUNDED":
            raise ConflictError("Order is already fully refunded")

        # ── Step 3: Lock order_items FOR UPDATE (sorted by id) ─────
        order_items_result = await self.session.execute(
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.id.asc())
            .with_for_update()
        )
        order_items = list(order_items_result.scalars().all())

        # ── Step 4: Lock products FOR UPDATE (sorted by product_id) ─
        requested_items: list[dict] = (
            ticket.requested_items if isinstance(ticket.requested_items, list) else []
        )
        if not requested_items:
            raise ValidationError("Ticket has no requested_items")

        product_ids = sorted({uuid.UUID(item["product_id"]) for item in requested_items})
        products = await self.product_repo.get_by_ids_for_update(product_ids)
        product_map = {p.id: p for p in products}

        # ── Step 5: Re-validate after locks held ────────────────────
        # 5a. No existing refund or reshipment for this ticket
        existing_refund = await self.refund_repo.get_by_ticket_id(ticket_id)
        if existing_refund is not None:
            raise ConflictError("A refund has already been executed for this ticket")

        existing_reshipment = await self.reshipment_repo.get_by_ticket_id(ticket_id)
        if existing_reshipment is not None:
            raise ConflictError("A reshipment has already been created for this ticket")

        # 5b. Validate quantities available
        oi_map = {str(oi.id): oi for oi in order_items}
        for item in requested_items:
            oi_id = str(item["order_item_id"])
            oi = oi_map.get(oi_id)
            if oi is None:
                raise ValidationError(f"Order item '{oi_id}' not found in this order")
            qty = int(item["quantity"])
            available = oi.quantity - oi.refunded_quantity - oi.reshipped_quantity
            if qty > available:
                raise ValidationError(
                    f"Insufficient available quantity for '{oi_id}': "
                    f"requested {qty}, available {available}"
                )

        # ── Step 6: Cumulative refund cap ───────────────────────────
        cumulative_refund = await self.refund_repo.sum_refund_amount_by_order(order_id)
        cumulative_shipping = await self.refund_repo.sum_shipping_refund_by_order(order_id)

        paid_amount = order.paid_amount
        shipping_fee = order.shipping_fee

        # Determine refund type
        requested_qtys: dict[str, int] = {}
        for item in requested_items:
            oi_id = str(item["order_item_id"])
            requested_qtys[oi_id] = requested_qtys.get(oi_id, 0) + int(item["quantity"])

        is_full = True
        for oi in order_items:
            total_refunded = oi.refunded_quantity + requested_qtys.get(str(oi.id), 0)
            if total_refunded < oi.quantity:
                is_full = False
                break

        refund_type_str = RefundType.FULL.value if is_full else RefundType.PARTIAL.value

        # Calculate refund
        calc_input = RefundCalcInput(
            order_paid_amount=paid_amount,
            order_shipping_fee=shipping_fee,
            order_items=[{
                "id": str(oi.id), "product_id": str(oi.product_id),
                "unit_price": str(oi.unit_price), "quantity": oi.quantity,
                "refunded_quantity": oi.refunded_quantity,
            } for oi in order_items],
            refund_items=requested_items,
            refund_type=refund_type_str,
            cumulative_refund_amount=cumulative_refund,
            cumulative_shipping_refund=cumulative_shipping,
        )

        calc_result = calculate_refund(calc_input)

        if calc_result.total_refund_amount <= Decimal("0"):
            raise ValidationError("Refund amount must be positive")

        # ── Step 7: Stock restoration (PAID/SHIPPED only) ──────────
        order_status_str = order_status
        restore_stock = order_status_str in ("PAID", "SHIPPED")

        if restore_stock:
            for item in requested_items:
                pid = uuid.UUID(item["product_id"])
                qty = int(item["quantity"])
                if pid in product_map:
                    await self.product_repo.restore_stock(pid, qty)

        # ── Step 8: Update order_items.refunded_quantity ────────────
        for item in requested_items:
            oi_uuid = uuid.UUID(item["order_item_id"])
            qty = int(item["quantity"])
            oi = oi_map.get(str(oi_uuid))
            if oi is not None:
                await self.session.execute(
                    sql_update(OrderItem)
                    .where(OrderItem.id == oi_uuid)
                    .values(refunded_quantity=OrderItem.refunded_quantity + qty)
                )

        # ── Step 9: Update order status if fully refunded ──────────
        if is_full:
            await self.session.execute(
                sql_update(Order)
                .where(Order.id == order_id)
                .values(
                    status=OrderStatus.REFUNDED.value,
                    version=Order.version + 1,
                )
            )

        # ── Step 10: Create refund record ───────────────────────────
        refund_record = RefundRecord(
            ticket_id=ticket_id,
            order_id=order_id,
            user_id=ticket.user_id,
            refund_amount=calc_result.total_refund_amount,
            shipping_refund_amount=calc_result.shipping_refund_amount,
            refund_type=refund_type_str,
            refund_reason=ticket.customer_request,
            refund_items=calc_result.items,
            calculation_breakdown=calc_result.calculation_breakdown,
            rule_version=calc_result.rule_version,
            processed_by=op_id,
        )
        await self.refund_repo.save(refund_record)

        # ── Step 11: Update ticket to COMPLETED ─────────────────────
        await self.session.execute(
            sql_update(AfterSalesTicket)
            .where(AfterSalesTicket.id == ticket_id)
            .values(
                status=TicketStatus.COMPLETED,
                resolution_type=ResolutionType.REFUND,
                completed_at=datetime.now(UTC),
                version=AfterSalesTicket.version + 1,
            )
        )

        # ── Step 12: Audit log ──────────────────────────────────────
        await self.audit_repo.create_log(
            user_id=op_id, action="REFUND_EXECUTE", resource_type="REFUND",
            resource_id=refund_record.id,
            changes={
                "refund_amount": str(calc_result.total_refund_amount),
                "shipping_refund_amount": str(calc_result.shipping_refund_amount),
                "refund_type": refund_type_str,
                "ticket_id": str(ticket_id),
                "order_id": str(order_id),
            },
            user_agent=user_agent,
        )
        await self.audit_repo.create_log(
            user_id=op_id, action="TICKET_COMPLETE", resource_type="TICKET",
            resource_id=ticket_id,
            changes={"status": "COMPLETED", "resolution_type": "REFUND"},
            user_agent=user_agent,
        )

        # Build response
        return {
            "refund": {
                "id": str(refund_record.id),
                "ticket_id": str(ticket_id),
                "order_id": str(order_id),
                "user_id": str(ticket.user_id),
                "refund_amount": str(refund_record.refund_amount),
                "shipping_refund_amount": str(refund_record.shipping_refund_amount),
                "refund_type": refund_type_str,
                "refund_reason": refund_record.refund_reason,
                "refund_items": refund_record.refund_items,
                "calculation_breakdown": refund_record.calculation_breakdown,
                "rule_version": refund_record.rule_version,
                "processed_by": str(op_id),
                "created_at": refund_record.created_at.isoformat() if refund_record.created_at else None,
            },
            "ticket": {
                "id": str(ticket_id),
                "status": "COMPLETED",
                "resolution_type": "REFUND",
            },
            "order": {
                "id": str(order_id),
                "status": "REFUNDED" if is_full else order_status_str,
            },
        }
