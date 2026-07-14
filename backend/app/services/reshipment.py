"""ReshipmentService — create, ship, deliver, cancel reshipment orders."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.after_sales_ticket import AfterSalesTicket
from app.models.enums import (
    ReshipmentStatus,
    ResolutionType,
    TicketStatus,
)
from app.models.order_item import OrderItem
from app.models.reshipment_order import ReshipmentOrder
from app.repositories.audit_log import AuditLogRepository
from app.repositories.order import OrderRepository
from app.repositories.order_item import OrderItemRepository
from app.repositories.product import ProductRepository
from app.repositories.refund import RefundRepository
from app.repositories.reshipment import ReshipmentRepository
from app.repositories.ticket import TicketRepository
from app.rules.state_transitions import (
    validate_reshipment_transition,
    validate_ticket_transition,
)


class ReshipmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ticket_repo = TicketRepository(session)
        self.order_repo = OrderRepository(session)
        self.order_item_repo = OrderItemRepository(session)
        self.product_repo = ProductRepository(session)
        self.refund_repo = RefundRepository(session)
        self.reshipment_repo = ReshipmentRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def create_reshipment(
        self,
        op_id: uuid.UUID,
        ticket_id: uuid.UUID,
        expected_version: int,
        user_agent: str | None = None,
    ) -> dict:
        """Create reshipment for an APPROVED ticket.

        Lock order: ticket → order_items → products.
        If stock insufficient → ticket → NEEDS_REVIEW (committed).
        """
        # ── Step 1: Lock ticket FOR UPDATE ──────────────────────────
        ticket = await self.ticket_repo.get_by_id_for_update(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")

        if ticket.version != expected_version:
            raise ConflictError("Ticket was modified by another request; please retry")

        current_status = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)
        validate_ticket_transition(current_status, TicketStatus.COMPLETED.value)

        order_id = ticket.order_id

        # Check no existing refund or reshipment
        existing_refund = await self.refund_repo.get_by_ticket_id(ticket_id)
        if existing_refund is not None:
            raise ConflictError("A refund has already been executed for this ticket")

        existing_reshipment = await self.reshipment_repo.get_by_ticket_id(ticket_id)
        if existing_reshipment is not None:
            raise ConflictError("A reshipment has already been created for this ticket")

        # ── Step 2: Lock order_items FOR UPDATE (sorted by id) ─────
        order_items_result = await self.session.execute(
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.id.asc())
            .with_for_update()
        )
        order_items = list(order_items_result.scalars().all())

        # ── Step 3: Lock products FOR UPDATE (sorted by product_id) ─
        requested_items: list[dict] = (
            ticket.requested_items if isinstance(ticket.requested_items, list) else []
        )
        if not requested_items:
            raise ValidationError("Ticket has no requested_items")

        product_ids = sorted(set(
            uuid.UUID(item["product_id"]) for item in requested_items
        ))
        products = await self.product_repo.get_by_ids_for_update(product_ids)
        product_map = {p.id: p for p in products}

        # ── Step 4: Re-validate after locks held ────────────────────
        oi_map = {str(oi.id): oi for oi in order_items}
        missing_items = []
        product_name_map = {p.id: p.name for p in products}

        for item in requested_items:
            oi_id = str(item["order_item_id"])
            oi = oi_map.get(oi_id)
            if oi is None:
                raise ValidationError(f"Order item '{oi_id}' not found in this order")
            qty = int(item["quantity"])
            available = oi.quantity - oi.reshipped_quantity - oi.refunded_quantity
            if qty > available:
                raise ValidationError(
                    f"Insufficient available quantity for '{oi_id}': "
                    f"requested {qty}, available {available}"
                )

            pid = uuid.UUID(item["product_id"])
            if pid not in product_map:
                raise ValidationError(f"Product '{pid}' not found")

            missing_items.append({
                "order_item_id": oi_id,
                "product_id": str(pid),
                "quantity": qty,
                "product_name_snapshot": product_name_map.get(pid, str(pid)),
            })

        # ── Step 5: Check stock ─────────────────────────────────────
        insufficient_stock = False
        stock_details: list[str] = []
        for item in requested_items:
            pid = uuid.UUID(item["product_id"])
            qty = int(item["quantity"])
            product = product_map[pid]
            if qty > product.stock:
                insufficient_stock = True
                stock_details.append(
                    f"{product.name}: need {qty}, have {product.stock}"
                )

        # ── Foreseeable failure: insufficient stock → NEEDS_REVIEW ─
        if insufficient_stock:
            await self.session.execute(
                sql_update(AfterSalesTicket)
                .where(AfterSalesTicket.id == ticket_id)
                .values(
                    status=TicketStatus.NEEDS_REVIEW,
                    operator_notes=f"Insufficient stock for reshipment: {'; '.join(stock_details)}",
                    version=AfterSalesTicket.version + 1,
                )
            )
            await self.audit_repo.create_log(
                user_id=op_id, action="RESHIPMENT_FAILED", resource_type="TICKET",
                resource_id=ticket_id,
                changes={
                    "status": "NEEDS_REVIEW",
                    "reason": f"Insufficient stock: {'; '.join(stock_details)}",
                },
                user_agent=user_agent,
            )
            return {
                "ticket": {"id": str(ticket_id), "status": "NEEDS_REVIEW"},
                "reshipment": None,
                "reason": f"Insufficient stock: {'; '.join(stock_details)}",
            }

        # ── Step 6: Deduct stock ────────────────────────────────────
        for item in requested_items:
            pid = uuid.UUID(item["product_id"])
            qty = int(item["quantity"])
            ok = await self.product_repo.deduct_stock(pid, qty)
            if not ok:
                # Stock changed between check and deduction — treat as insufficient
                await self.session.execute(
                    sql_update(AfterSalesTicket)
                    .where(AfterSalesTicket.id == ticket_id)
                    .values(
                        status=TicketStatus.NEEDS_REVIEW,
                        operator_notes=f"Stock changed during reshipment for product {pid}",
                        version=AfterSalesTicket.version + 1,
                    )
                )
                await self.audit_repo.create_log(
                    user_id=op_id, action="RESHIPMENT_FAILED", resource_type="TICKET",
                    resource_id=ticket_id,
                    changes={"status": "NEEDS_REVIEW", "reason": "Stock changed during execution"},
                    user_agent=user_agent,
                )
                return {
                    "ticket": {"id": str(ticket_id), "status": "NEEDS_REVIEW"},
                    "reshipment": None,
                    "reason": f"Stock changed during reshipment for product {pid}",
                }

        # ── Step 7: Update order_items.reshipped_quantity ───────────
        for item in requested_items:
            oi_uuid = uuid.UUID(item["order_item_id"])
            qty = int(item["quantity"])
            await self.session.execute(
                sql_update(OrderItem)
                .where(OrderItem.id == oi_uuid)
                .values(reshipped_quantity=OrderItem.reshipped_quantity + qty)
            )

        # ── Step 8: Create reshipment order ─────────────────────────
        # Get shipping address from order
        order = await self.order_repo.get_by_id(order_id)
        shipping_address = order.shipping_address if order else ""

        reshipment = ReshipmentOrder(
            ticket_id=ticket_id,
            original_order_id=order_id,
            user_id=ticket.user_id,
            reshipment_number=await self.reshipment_repo.generate_reshipment_number(),
            missing_items=missing_items,
            shipping_address=shipping_address,
            status=ReshipmentStatus.CREATED,
            processed_by=op_id,
        )
        await self.reshipment_repo.save(reshipment)

        # ── Step 9: Update ticket to COMPLETED ──────────────────────
        await self.session.execute(
            sql_update(AfterSalesTicket)
            .where(AfterSalesTicket.id == ticket_id)
            .values(
                status=TicketStatus.COMPLETED,
                resolution_type=ResolutionType.RESHIPMENT,
                completed_at=datetime.now(UTC),
                version=AfterSalesTicket.version + 1,
            )
        )

        # ── Step 10: Audit log ──────────────────────────────────────
        await self.audit_repo.create_log(
            user_id=op_id, action="RESHIPMENT_CREATE", resource_type="RESHIPMENT",
            resource_id=reshipment.id,
            changes={"status": "CREATED", "ticket_id": str(ticket_id), "order_id": str(order_id)},
            user_agent=user_agent,
        )
        await self.audit_repo.create_log(
            user_id=op_id, action="TICKET_COMPLETE", resource_type="TICKET",
            resource_id=ticket_id,
            changes={"status": "COMPLETED", "resolution_type": "RESHIPMENT"},
            user_agent=user_agent,
        )

        return {
            "reshipment": {
                "id": str(reshipment.id),
                "ticket_id": str(ticket_id),
                "original_order_id": str(order_id),
                "user_id": str(ticket.user_id),
                "reshipment_number": reshipment.reshipment_number,
                "missing_items": reshipment.missing_items,
                "shipping_address": reshipment.shipping_address,
                "status": "CREATED",
                "tracking_number": None,
                "carrier": None,
                "shipped_at": None,
                "delivered_at": None,
                "version": reshipment.version,
                "processed_by": str(op_id),
                "created_at": reshipment.created_at.isoformat() if reshipment.created_at else None,
                "updated_at": reshipment.updated_at.isoformat() if reshipment.updated_at else None,
            },
            "ticket": {"id": str(ticket_id), "status": "COMPLETED", "resolution_type": "RESHIPMENT"},
        }

    async def ship_reshipment(
        self,
        op_id: uuid.UUID,
        reshipment_id: uuid.UUID,
        expected_version: int,
        tracking_number: str | None = None,
        carrier: str = "SF Express",
        user_agent: str | None = None,
    ) -> dict:
        reshipment = await self.reshipment_repo.get_by_id_for_update(reshipment_id)
        if reshipment is None:
            raise NotFoundError("Reshipment not found")

        if reshipment.version != expected_version:
            raise ConflictError("Reshipment was modified by another request; please retry")

        current_status = reshipment.status.value if hasattr(reshipment.status, 'value') else str(reshipment.status)
        validate_reshipment_transition(current_status, ReshipmentStatus.SHIPPED.value)

        import random
        tn = tracking_number or f"SF{random.randint(10000000000, 99999999999)}"

        updated = await self.reshipment_repo.update_with_version(
            reshipment_id, expected_version,
            status=ReshipmentStatus.SHIPPED,
            tracking_number=tn,
            carrier=carrier,
            shipped_at=datetime.now(UTC),
        )
        if updated is None:
            raise ConflictError("Reshipment was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=op_id, action="RESHIPMENT_SHIP", resource_type="RESHIPMENT",
            resource_id=reshipment_id,
            changes={"status": "SHIPPED", "tracking_number": tn, "carrier": carrier},
            user_agent=user_agent,
        )
        return self._reshipment_response(updated)

    async def deliver_reshipment(
        self,
        op_id: uuid.UUID,
        reshipment_id: uuid.UUID,
        expected_version: int,
        user_agent: str | None = None,
    ) -> dict:
        reshipment = await self.reshipment_repo.get_by_id_for_update(reshipment_id)
        if reshipment is None:
            raise NotFoundError("Reshipment not found")

        if reshipment.version != expected_version:
            raise ConflictError("Reshipment was modified by another request; please retry")

        current_status = reshipment.status.value if hasattr(reshipment.status, 'value') else str(reshipment.status)
        validate_reshipment_transition(current_status, ReshipmentStatus.DELIVERED.value)

        updated = await self.reshipment_repo.update_with_version(
            reshipment_id, expected_version,
            status=ReshipmentStatus.DELIVERED,
            delivered_at=datetime.now(UTC),
        )
        if updated is None:
            raise ConflictError("Reshipment was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=op_id, action="RESHIPMENT_DELIVER", resource_type="RESHIPMENT",
            resource_id=reshipment_id,
            changes={"status": "DELIVERED"},
            user_agent=user_agent,
        )
        return self._reshipment_response(updated)

    async def cancel_reshipment(
        self,
        op_id: uuid.UUID,
        reshipment_id: uuid.UUID,
        expected_version: int,
        user_agent: str | None = None,
    ) -> dict:
        reshipment = await self.reshipment_repo.get_by_id_for_update(reshipment_id)
        if reshipment is None:
            raise NotFoundError("Reshipment not found")

        if reshipment.version != expected_version:
            raise ConflictError("Reshipment was modified by another request; please retry")

        current_status = reshipment.status.value if hasattr(reshipment.status, 'value') else str(reshipment.status)
        validate_reshipment_transition(current_status, ReshipmentStatus.CANCELLED.value)

        # Restore stock
        missing_items: list[dict] = (
            reshipment.missing_items if isinstance(reshipment.missing_items, list) else []
        )
        if missing_items:
            product_ids = sorted(set(uuid.UUID(item["product_id"]) for item in missing_items))
            await self.product_repo.get_by_ids_for_update(product_ids)
            for item in missing_items:
                pid = uuid.UUID(item["product_id"])
                qty = int(item["quantity"])
                await self.product_repo.restore_stock(pid, qty)

        updated = await self.reshipment_repo.update_with_version(
            reshipment_id, expected_version,
            status=ReshipmentStatus.CANCELLED,
        )
        if updated is None:
            raise ConflictError("Reshipment was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=op_id, action="RESHIPMENT_CANCEL", resource_type="RESHIPMENT",
            resource_id=reshipment_id,
            changes={"status": "CANCELLED"},
            user_agent=user_agent,
        )
        return self._reshipment_response(updated)

    def _reshipment_response(self, r) -> dict:  # type: ignore[no-untyped-def]
        return {
            "id": str(r.id),
            "ticket_id": str(r.ticket_id),
            "original_order_id": str(r.original_order_id),
            "user_id": str(r.user_id),
            "reshipment_number": r.reshipment_number,
            "missing_items": r.missing_items,
            "shipping_address": r.shipping_address,
            "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            "tracking_number": r.tracking_number,
            "carrier": r.carrier,
            "shipped_at": r.shipped_at.isoformat() if r.shipped_at else None,
            "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
            "version": r.version,
            "processed_by": str(r.processed_by) if r.processed_by else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
