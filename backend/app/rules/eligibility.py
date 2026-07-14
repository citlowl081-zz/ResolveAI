"""After-sales eligibility rule engine — deterministic, no LLM."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.models.after_sales_ticket import AfterSalesTicket
from app.models.enums import IntentType


@dataclass
class EligibilityInput:
    user_id: uuid.UUID
    order_id: uuid.UUID
    order_status: str
    order_paid_at: datetime | None
    order_delivered_at: datetime | None
    intent: str
    requested_items: list[dict]
    order_items: list[dict]  # [{id, product_id, quantity, refunded_quantity, reshipped_quantity, unit_price}]
    products: list[dict]     # [{id, is_returnable, category}]
    existing_tickets: list[AfterSalesTicket] = field(default_factory=list)
    risk_level: str = "LOW"
    return_window_days: int = 7
    high_refund_threshold: Decimal = Decimal("1000.00")
    non_returnable_categories: list[str] = field(default_factory=lambda: ["FOOD"])


@dataclass
class EligibilityResult:
    is_eligible: bool
    reject_code: str | None = None
    reject_reason: str | None = None
    needs_review: bool = False
    review_reason: str | None = None


def check_eligibility(input_data: EligibilityInput) -> EligibilityResult:
    """Run all eligibility checks in order. Returns the first rejection or a pass result."""

    # 1. Order ownership
    # (Checked by caller — not re-checked here since user_id is already verified)

    # 2. Order status: PAID/SHIPPED/DELIVERED eligible
    refundable_statuses = {"PAID", "SHIPPED", "DELIVERED"}
    if input_data.order_status not in refundable_statuses:
        return EligibilityResult(
            is_eligible=False,
            reject_code="INVALID_STATUS",
            reject_reason=f"Order status '{input_data.order_status}' is not eligible for after-sales. "
                          f"Only PAID, SHIPPED, or DELIVERED orders are eligible.",
        )

    # 3. No full refund already
    if input_data.order_status == "REFUNDED":
        return EligibilityResult(
            is_eligible=False,
            reject_code="ALREADY_REFUNDED",
            reject_reason="Order has already been fully refunded.",
        )

    # 4. No active duplicate ticket
    active_statuses = {"APPROVED", "NEEDS_REVIEW"}
    for ticket in input_data.existing_tickets:
        if ticket.intent.value == input_data.intent and ticket.status.value in active_statuses:
            return EligibilityResult(
                is_eligible=False,
                reject_code="DUPLICATE_TICKET",
                reject_reason=f"An active ticket (status: {ticket.status.value}) already exists "
                              f"for this order with intent '{input_data.intent}'.",
            )

    # 5. Product returnable check + quantity validation
    product_map = {p["id"]: p for p in input_data.products}
    order_item_map = {oi["id"]: oi for oi in input_data.order_items}

    estimated_refund = Decimal("0")

    for item in input_data.requested_items:
        oi_id = item["order_item_id"]
        oi = order_item_map.get(oi_id)
        if oi is None:
            return EligibilityResult(
                is_eligible=False,
                reject_code="INVALID_ITEM",
                reject_reason=f"Order item '{oi_id}' does not belong to this order.",
            )

        pid = item["product_id"]
        if pid != oi["product_id"]:
            return EligibilityResult(
                is_eligible=False,
                reject_code="INVALID_ITEM",
                reject_reason=f"Product ID mismatch for order item '{oi_id}'.",
            )

        qty = item["quantity"]
        if not isinstance(qty, int) or qty <= 0:
            return EligibilityResult(
                is_eligible=False,
                reject_code="INVALID_QUANTITY",
                reject_reason=f"Quantity must be a positive integer, got {qty}.",
            )

        available = oi["quantity"] - oi.get("refunded_quantity", 0) - oi.get("reshipped_quantity", 0)
        if qty > available:
            return EligibilityResult(
                is_eligible=False,
                reject_code="QUANTITY_EXCEEDED",
                reject_reason=f"Requested {qty} but only {available} available for item '{oi_id}'.",
            )

        # For refund/exchange intents, check product returnability
        if input_data.intent in (IntentType.PRE_SHIP_REFUND.value, IntentType.QUALITY_REFUND.value, IntentType.EXCHANGE.value):
            prod = product_map.get(pid)
            if prod is None:
                return EligibilityResult(
                    is_eligible=False,
                    reject_code="INVALID_ITEM",
                    reject_reason=f"Product '{pid}' not found.",
                )
            if not prod.get("is_returnable", True):
                return EligibilityResult(
                    is_eligible=False,
                    reject_code="NOT_RETURNABLE",
                    reject_reason=f"Product '{prod.get('name', pid)}' is not returnable.",
                )
            if prod.get("category") in input_data.non_returnable_categories:
                return EligibilityResult(
                    is_eligible=False,
                    reject_code="NOT_RETURNABLE",
                    reject_reason=f"Category '{prod.get('category')}' is not eligible for return.",
                )

        estimated_refund += Decimal(str(oi.get("unit_price", "0"))) * qty

    # 6. Time limit check
    reference_date = input_data.order_delivered_at or input_data.order_paid_at
    if reference_date is not None:
        days_elapsed = (datetime.now(UTC) - reference_date.replace(tzinfo=UTC)).days
        if days_elapsed > input_data.return_window_days:
            return EligibilityResult(
                is_eligible=False,
                reject_code="OVER_TIME_LIMIT",
                reject_reason=f"Return window of {input_data.return_window_days} days has expired "
                              f"({days_elapsed} days elapsed).",
            )

    # 7. NEEDS_REVIEW triggers
    needs_review = False
    review_reasons: list[str] = []

    if input_data.risk_level == "HIGH":
        needs_review = True
        review_reasons.append("User has HIGH risk level")

    if estimated_refund > input_data.high_refund_threshold:
        needs_review = True
        review_reasons.append(
            f"Refund amount ({estimated_refund}) exceeds threshold ({input_data.high_refund_threshold})"
        )

    if input_data.intent == IntentType.EXCHANGE.value:
        needs_review = True
        review_reasons.append("Exchange requests require manual review")

    if len(input_data.requested_items) > 1:
        needs_review = True
        review_reasons.append("Multiple items affected — operator review required")

    if needs_review:
        return EligibilityResult(
            is_eligible=True,
            needs_review=True,
            review_reason="; ".join(review_reasons),
        )

    return EligibilityResult(is_eligible=True)
