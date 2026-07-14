"""TicketService — create, cancel, approve, reject after-sales tickets."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.after_sales_ticket import AfterSalesTicket
from app.models.enums import IntentType, TicketStatus
from app.models.product import Product
from app.models.system_config import SystemConfig
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.repositories.order import OrderRepository
from app.repositories.order_item import OrderItemRepository
from app.repositories.ticket import TicketRepository
from app.rules.eligibility import EligibilityInput, check_eligibility
from app.rules.fingerprint import compute_request_fingerprint
from app.rules.state_transitions import validate_ticket_transition


class TicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ticket_repo = TicketRepository(session)
        self.order_repo = OrderRepository(session)
        self.order_item_repo = OrderItemRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def create_ticket(
        self,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
        intent: str,
        requested_items: list[dict],
        customer_request: str = "",
        user_agent: str | None = None,
    ) -> dict:
        import decimal

        # Validate intent
        valid_intents = {e.value for e in IntentType}
        if intent not in valid_intents:
            raise ValidationError(f"Invalid intent '{intent}'. Must be one of: {sorted(valid_intents)}")

        # Load order
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if str(order.user_id) != str(user_id):
            raise NotFoundError("Order not found")

        # Load order items (non-locking read)
        order_items = await self.order_item_repo.list_by_order(order_id)
        if not order_items:
            raise ValidationError("Order has no items")

        # Validate requested_items structure
        self._validate_requested_items(requested_items, order_items)

        # Compute fingerprint
        fingerprint = compute_request_fingerprint(requested_items)

        # Check active duplicate
        existing = await self.ticket_repo.find_active_by_order_intent_fingerprint(
            order_id, intent, fingerprint,
        )
        if existing is not None:
            raise ConflictError(
                f"An active ticket ({existing.status.value}) already exists "
                f"for this order and intent with the same requested items."
            )

        # Load existing tickets for duplicate check within eligibility
        all_tickets = await self.ticket_repo.list_by_order(order_id)

        # Load user for risk level
        user_result = await self.session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        risk_level = user.risk_level.value if user else "LOW"

        # Load products (non-locking read)
        product_ids = list({uuid.UUID(item["product_id"]) for item in requested_items})
        prod_result = await self.session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = list(prod_result.scalars().all())

        product_list: list[dict] = []
        for p in products:
            product_list.append({
                "id": str(p.id),
                "is_returnable": bool(p.is_returnable),
                "category": p.category.value if hasattr(p.category, 'value') else str(p.category),
                "name": p.name,
            })

        # Load system configs
        config_result = await self.session.execute(select(SystemConfig))
        configs = {c.config_key: c.config_value for c in config_result.scalars().all()}

        raw_return_window = configs.get("return_window_days", 7)
        return_window_days = int(raw_return_window) if not isinstance(raw_return_window, dict) else 7
        raw_threshold = configs.get("high_refund_threshold", "1000.00")
        high_refund_threshold = decimal.Decimal(str(raw_threshold)) if not isinstance(raw_threshold, dict) else decimal.Decimal("1000.00")
        non_returnable = configs.get("non_returnable_categories", ["FOOD"])
        if isinstance(non_returnable, list):
            non_returnable_categories = non_returnable
        else:
            non_returnable_categories = [str(non_returnable)]

        # Run eligibility
        eligibility_input = EligibilityInput(
            user_id=user_id,
            order_id=order_id,
            order_status=str(order.status.value) if hasattr(order.status, 'value') else str(order.status),
            order_paid_at=order.paid_at,
            order_delivered_at=order.delivered_at,
            intent=intent,
            requested_items=requested_items,
            order_items=[{
                "id": str(oi.id), "product_id": str(oi.product_id),
                "quantity": oi.quantity, "refunded_quantity": oi.refunded_quantity,
                "reshipped_quantity": oi.reshipped_quantity, "unit_price": str(oi.unit_price),
            } for oi in order_items],
            products=product_list,
            existing_tickets=all_tickets,
            risk_level=risk_level,
            return_window_days=return_window_days,
            high_refund_threshold=high_refund_threshold,
            non_returnable_categories=non_returnable_categories,
        )

        result = check_eligibility(eligibility_input)

        if not result.is_eligible:
            ticket = AfterSalesTicket(
                user_id=user_id, order_id=order_id,
                ticket_number=await self.ticket_repo.generate_ticket_number(),
                intent=intent, status=TicketStatus.REJECTED,
                requested_items=requested_items, request_fingerprint=fingerprint,
                customer_request=customer_request,
                reject_reason=result.reject_reason, reject_code=result.reject_code,
            )
            await self.ticket_repo.save(ticket)
            await self.audit_repo.create_log(
                user_id=user_id, action="CREATE", resource_type="TICKET",
                resource_id=ticket.id,
                changes={"status": "REJECTED", "reject_code": result.reject_code or ""},
                user_agent=user_agent,
            )
            return await self._ticket_response(ticket.id)

        initial_status = TicketStatus.NEEDS_REVIEW if result.needs_review else TicketStatus.APPROVED

        ticket = AfterSalesTicket(
            user_id=user_id, order_id=order_id,
            ticket_number=await self.ticket_repo.generate_ticket_number(),
            intent=intent, status=initial_status,
            requested_items=requested_items, request_fingerprint=fingerprint,
            customer_request=customer_request,
            operator_notes=result.review_reason if result.needs_review else None,
        )
        await self.ticket_repo.save(ticket)

        await self.audit_repo.create_log(
            user_id=user_id, action="CREATE", resource_type="TICKET",
            resource_id=ticket.id,
            changes={"status": initial_status.value, "intent": intent},
            user_agent=user_agent,
        )
        return await self._ticket_response(ticket.id)

    async def cancel_ticket(
        self, user_id: uuid.UUID, ticket_id: uuid.UUID,
        expected_version: int, user_agent: str | None = None,
    ) -> dict:
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")
        if str(ticket.user_id) != str(user_id):
            raise NotFoundError("Ticket not found")

        current_status = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)
        validate_ticket_transition(current_status, TicketStatus.CANCELLED.value)

        updated = await self.ticket_repo.update_with_version(
            ticket_id, expected_version, status=TicketStatus.CANCELLED,
        )
        if updated is None:
            raise ConflictError("Ticket was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=user_id, action="CANCEL", resource_type="TICKET",
            resource_id=ticket_id, changes={"status": "CANCELLED"},
            user_agent=user_agent,
        )
        return await self._ticket_response(ticket_id)

    async def approve_ticket(
        self, user_id: uuid.UUID, ticket_id: uuid.UUID,
        expected_version: int, user_agent: str | None = None,
    ) -> dict:
        ticket = await self.ticket_repo.get_by_id_for_update(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")

        current_status = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)
        validate_ticket_transition(current_status, TicketStatus.APPROVED.value)

        updated = await self.ticket_repo.update_with_version(
            ticket_id, expected_version, status=TicketStatus.APPROVED,
        )
        if updated is None:
            raise ConflictError("Ticket was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=user_id, action="APPROVE", resource_type="TICKET",
            resource_id=ticket_id, changes={"status": "APPROVED"},
            user_agent=user_agent,
        )
        return await self._ticket_response(ticket_id)

    async def reject_ticket(
        self, user_id: uuid.UUID, ticket_id: uuid.UUID,
        expected_version: int, reject_reason: str = "",
        user_agent: str | None = None,
    ) -> dict:
        ticket = await self.ticket_repo.get_by_id_for_update(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")

        current_status = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)
        validate_ticket_transition(current_status, TicketStatus.REJECTED.value)

        fields: dict = {"status": TicketStatus.REJECTED}
        if reject_reason:
            fields["reject_reason"] = reject_reason

        updated = await self.ticket_repo.update_with_version(
            ticket_id, expected_version, **fields,
        )
        if updated is None:
            raise ConflictError("Ticket was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=user_id, action="REJECT", resource_type="TICKET",
            resource_id=ticket_id,
            changes={"status": "REJECTED", "reject_reason": reject_reason},
            user_agent=user_agent,
        )
        return await self._ticket_response(ticket_id)

    async def get_ticket(self, ticket_id: uuid.UUID, requesting_user_id: uuid.UUID, role: str) -> dict:
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")
        if role == "CUSTOMER" and str(ticket.user_id) != str(requesting_user_id):
            raise NotFoundError("Ticket not found")
        return await self._ticket_response(ticket_id)

    async def list_my_tickets(self, user_id: uuid.UUID, page: int = 1, page_size: int = 20) -> dict:
        tickets, total = await self.ticket_repo.list_by_user(user_id, page, page_size)
        items = [self._ticket_summary(t) for t in tickets]
        return {
            "items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
        }

    async def list_all_tickets(
        self, page: int = 1, page_size: int = 20,
        status: str | None = None, intent: str | None = None,
    ) -> dict:
        tickets, total = await self.ticket_repo.list_all(page, page_size, status, intent)
        items = [self._ticket_summary(t) for t in tickets]
        return {
            "items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
        }

    # ── Helpers ───────────────────────────────────────────────────────

    def _validate_requested_items(self, requested_items: list[dict], order_items: list) -> None:
        if not isinstance(requested_items, list) or len(requested_items) == 0:
            raise ValidationError("requested_items must be a non-empty array")

        oi_map = {str(oi.id): oi for oi in order_items}

        for item in requested_items:
            if not isinstance(item, dict):
                raise ValidationError("Each item in requested_items must be an object")
            for field in ("order_item_id", "product_id", "quantity"):
                if field not in item:
                    raise ValidationError(f"Each item must have '{field}'")

            oi_id = str(item["order_item_id"])
            if oi_id not in oi_map:
                raise ValidationError(f"Order item '{oi_id}' does not belong to this order")

            oi = oi_map[oi_id]
            if str(item["product_id"]) != str(oi.product_id):
                raise ValidationError(
                    f"Product ID mismatch for order item '{oi_id}'"
                )

            qty = item["quantity"]
            if not isinstance(qty, int) or qty <= 0:
                raise ValidationError(f"Quantity must be a positive integer, got {qty}")

            available = oi.quantity - oi.refunded_quantity - oi.reshipped_quantity
            if qty > available:
                raise ValidationError(
                    f"Insufficient available quantity for item '{oi_id}': "
                    f"requested {qty}, available {available}"
                )

    async def _ticket_response(self, ticket_id: uuid.UUID) -> dict:
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found")
        return {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "user_id": str(ticket.user_id),
            "order_id": str(ticket.order_id),
            "intent": ticket.intent.value if hasattr(ticket.intent, 'value') else str(ticket.intent),
            "status": ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
            "resolution_type": (
                ticket.resolution_type.value if ticket.resolution_type and hasattr(ticket.resolution_type, 'value')
                else (str(ticket.resolution_type) if ticket.resolution_type else None)
            ),
            "customer_request": ticket.customer_request,
            "requested_items": ticket.requested_items if isinstance(ticket.requested_items, list) else [],
            "operator_notes": ticket.operator_notes,
            "proposed_solution": ticket.proposed_solution,
            "resolution_result": ticket.resolution_result,
            "reject_reason": ticket.reject_reason,
            "reject_code": ticket.reject_code,
            "version": ticket.version,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "completed_at": ticket.completed_at.isoformat() if ticket.completed_at else None,
        }

    def _ticket_summary(self, ticket) -> dict:  # type: ignore[no-untyped-def]
        return {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "order_id": str(ticket.order_id),
            "intent": ticket.intent.value if hasattr(ticket.intent, 'value') else str(ticket.intent),
            "status": ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        }
