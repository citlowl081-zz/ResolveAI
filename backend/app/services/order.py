"""OrderService — create, pay, ship, deliver, cancel with transactions."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.enums import LogisticsStatus, OrderStatus
from app.repositories.audit_log import AuditLogRepository
from app.repositories.order import OrderRepository
from app.repositories.order_item import OrderItemRepository
from app.repositories.product import ProductRepository
from app.rules.state_transitions import (
    REQUIRES_AFTER_SALES,
    is_cancellable,
    validate_transition,
)


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.order_repo = OrderRepository(session)
        self.order_item_repo = OrderItemRepository(session)
        self.product_repo = ProductRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def create_order(
        self, user_id: uuid.UUID, items: list[dict], shipping_address: str,
        shipping_fee: str = "0", user_agent: str | None = None,
    ) -> dict:
        from decimal import Decimal

        # Aggregate duplicate product_ids
        aggregated: dict[uuid.UUID, int] = defaultdict(int)
        for item in items:
            pid = uuid.UUID(item["product_id"])
            aggregated[pid] += item["quantity"]

        # Validate products exist and are active
        product_ids = list(aggregated.keys())
        products = await self.product_repo.get_by_ids_for_update(product_ids)
        product_map = {p.id: p for p in products}

        missing = [str(pid) for pid in product_ids if pid not in product_map]
        if missing:
            raise NotFoundError(f"Products not found: {', '.join(missing)}")

        inactive = [str(p.id) for p in products if not p.is_active]
        if inactive:
            raise ValidationError(f"Products not available: {', '.join(inactive)}")

        # Stock pre-check (non-locking, early feedback)
        for pid, qty in aggregated.items():
            p = product_map[pid]
            if qty > p.stock:
                raise ValidationError(
                    f"Insufficient stock for {p.name}: requested {qty}, available {p.stock}"
                )

        # Compute order items
        order_items_data = []
        subtotals = []
        for pid, qty in aggregated.items():
            p = product_map[pid]
            unit_price = p.price
            subtotal = unit_price * qty
            order_items_data.append({
                "product_id": pid,
                "product_name": p.name,
                "unit_price": unit_price,
                "quantity": qty,
                "subtotal": subtotal,
            })
            subtotals.append(subtotal)

        total = sum(subtotals, Decimal("0")) + Decimal(shipping_fee)

        from app.models.order import Order
        order = Order(
            user_id=user_id,
            order_number=await self.order_repo.generate_order_number(),
            status=OrderStatus.PENDING_PAYMENT.value,
            total_amount=total,
            shipping_address=shipping_address,
            shipping_fee=Decimal(shipping_fee),
        )
        await self.order_repo.save(order)

        for item_data in order_items_data:
            item_data["order_id"] = order.id
        await self.order_item_repo.create_batch(order_items_data)

        await self.audit_repo.create_log(
            user_id=user_id, action="CREATE", resource_type="ORDER",
            resource_id=order.id, changes={"status": order.status},
            user_agent=user_agent,
        )

        return await self._order_response(order.id)

    async def pay_order(
        self, user_id: uuid.UUID, order_id: uuid.UUID,
        expected_version: int, user_agent: str | None = None,
    ) -> dict:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if order.user_id != user_id:
            raise NotFoundError("Order not found")

        validate_transition(order.status, OrderStatus.PAID.value)

        # Get order items
        order_items = await self.order_item_repo.list_by_order(order_id)
        if not order_items:
            raise ValidationError("Order has no items")

        # Lock products in sorted order
        product_ids = sorted([oi.product_id for oi in order_items])
        products = await self.product_repo.get_by_ids_for_update(product_ids)
        product_map = {p.id: p for p in products}

        # Validate and deduct stock
        for oi in order_items:
            p = product_map[oi.product_id]
            if oi.quantity > p.stock:
                raise ValidationError(
                    f"Insufficient stock for {p.name}: need {oi.quantity}, have {p.stock}"
                )
            ok = await self.product_repo.deduct_stock(oi.product_id, oi.quantity)
            if not ok:
                raise ValidationError(f"Stock deduction failed for {p.name}")

        # Update order with version check
        updated = await self.order_repo.update_with_version(
            order_id, expected_version,
            status=OrderStatus.PAID.value,
            paid_amount=order.total_amount,
            paid_at=datetime.now(UTC),
        )
        if updated is None:
            raise ConflictError("Order was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=user_id, action="PAY", resource_type="ORDER",
            resource_id=order_id,
            changes={"status": OrderStatus.PAID.value, "paid_amount": str(order.total_amount)},
            user_agent=user_agent,
        )
        return await self._order_response(order_id)

    async def ship_order(
        self, user_id: uuid.UUID, order_id: uuid.UUID,
        expected_version: int, tracking_number: str | None = None,
        carrier: str = "SF Express", user_agent: str | None = None,
    ) -> dict:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")

        validate_transition(order.status, OrderStatus.SHIPPED.value)

        updated = await self.order_repo.update_with_version(
            order_id, expected_version,
            status=OrderStatus.SHIPPED.value,
            shipped_at=datetime.now(UTC),
        )
        if updated is None:
            raise ConflictError("Order was modified by another request; please retry")

        # Create logistics record
        import random

        from app.models.logistics_record import LogisticsRecord
        tn = tracking_number or f"SF{random.randint(10000000000, 99999999999)}"
        logistics = LogisticsRecord(
            order_id=order_id, tracking_number=tn, carrier=carrier,
            status=LogisticsStatus.PICKED_UP.value,
            current_location="Distribution Center",
            events=[{
                "timestamp": datetime.now(UTC).isoformat(),
                "status": LogisticsStatus.PICKED_UP.value,
                "location": "Distribution Center",
                "description": "Package picked up",
            }],
        )
        await self.order_repo.session.flush()  # ensure logistics saved
        self.session.add(logistics)
        await self.session.flush()

        await self.audit_repo.create_log(
            user_id=user_id, action="SHIP", resource_type="ORDER",
            resource_id=order_id,
            changes={"status": OrderStatus.SHIPPED.value, "tracking_number": tn},
            user_agent=user_agent,
        )
        return await self._order_response(order_id)

    async def deliver_order(
        self, user_id: uuid.UUID, order_id: uuid.UUID,
        expected_version: int, user_agent: str | None = None,
    ) -> dict:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")

        validate_transition(order.status, OrderStatus.DELIVERED.value)

        updated = await self.order_repo.update_with_version(
            order_id, expected_version,
            status=OrderStatus.DELIVERED.value,
            delivered_at=datetime.now(UTC),
        )
        if updated is None:
            raise ConflictError("Order was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=user_id, action="DELIVER", resource_type="ORDER",
            resource_id=order_id,
            changes={"status": OrderStatus.DELIVERED.value},
            user_agent=user_agent,
        )
        return await self._order_response(order_id)

    async def cancel_order(
        self, user_id: uuid.UUID, order_id: uuid.UUID,
        expected_version: int, reason: str = "", user_agent: str | None = None,
    ) -> dict:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")

        if order.status in REQUIRES_AFTER_SALES:
            raise ConflictError(
                "Cannot cancel a paid/shipped/delivered order. "
                "Please use the after-sales process."
            )

        if not is_cancellable(order.status):
            raise ConflictError(f"Cannot cancel order in '{order.status}' status")

        updated = await self.order_repo.update_with_version(
            order_id, expected_version,
            status=OrderStatus.CANCELLED.value,
            cancelled_at=datetime.now(UTC),
            cancel_reason=reason or None,
        )
        if updated is None:
            raise ConflictError("Order was modified by another request; please retry")

        await self.audit_repo.create_log(
            user_id=user_id, action="CANCEL", resource_type="ORDER",
            resource_id=order_id,
            changes={"status": OrderStatus.CANCELLED.value, "cancel_reason": reason},
            user_agent=user_agent,
        )
        return await self._order_response(order_id)

    async def get_order(self, order_id: uuid.UUID, requesting_user_id: uuid.UUID, role: str) -> dict:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if role == "CUSTOMER" and order.user_id != requesting_user_id:
            raise NotFoundError("Order not found")
        return await self._order_response(order_id)

    async def list_my_orders(self, user_id: uuid.UUID, page: int = 1, page_size: int = 20) -> dict:
        orders, total = await self.order_repo.list_by_user(user_id, page, page_size)
        return {
            "items": [await self._order_summary(o) for o in orders],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 1,
        }

    async def _order_response(self, order_id: uuid.UUID) -> dict:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        items = await self.order_item_repo.list_by_order(order_id)
        return {
            "id": str(order.id),
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": str(order.total_amount),
            "discount_amount": str(order.discount_amount),
            "paid_amount": str(order.paid_amount),
            "shipping_address": order.shipping_address,
            "shipping_fee": str(order.shipping_fee),
            "coupon_code": order.coupon_code,
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
            "cancel_reason": order.cancel_reason,
            "version": order.version,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [{"id": str(i.id), "product_id": str(i.product_id), "product_name": i.product_name,
                        "unit_price": str(i.unit_price), "quantity": i.quantity,
                        "subtotal": str(i.subtotal)} for i in items],
        }

    async def _order_summary(self, order) -> dict:  # type: ignore[no-untyped-def]
        items = await self.order_item_repo.list_by_order(order.id)
        return {
            "id": str(order.id), "order_number": order.order_number,
            "status": order.status, "total_amount": str(order.total_amount),
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [
                {
                    "id": str(item.id),
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                }
                for item in items
            ],
        }
