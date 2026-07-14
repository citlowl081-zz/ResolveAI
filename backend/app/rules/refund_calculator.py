"""Deterministic refund calculator — Decimal precision, no LLM."""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


@dataclass
class RefundCalcInput:
    order_paid_amount: Decimal
    order_shipping_fee: Decimal
    order_items: list[dict]  # [{id, product_id, unit_price, quantity, refunded_quantity}]
    refund_items: list[dict]  # [{order_item_id, quantity}]
    refund_type: str  # FULL, PARTIAL, SHIPPING_FEE
    cumulative_refund_amount: Decimal = Decimal("0")
    cumulative_shipping_refund: Decimal = Decimal("0")


@dataclass
class RefundCalcResult:
    items: list[dict] = field(default_factory=list)
    total_refund_amount: Decimal = Decimal("0")
    shipping_refund_amount: Decimal = Decimal("0")
    calculation_breakdown: dict = field(default_factory=dict)
    rule_version: str = "02B-v1"


def calculate_refund(input_data: RefundCalcInput) -> RefundCalcResult:
    """Calculate refund amount deterministically.

    Rules:
    1. Per-item: unit_price × quantity (from DB, not client)
    2. Shipping: only for FULL refund (all items) or SHIPPING_FEE type
    3. Cap: total ≤ paid_amount - cumulative_refund
    4. Shipping cap: ≤ shipping_fee - cumulative_shipping_refund
    5. Partial: cannot exceed available quantity
    6. All values quantized to 2 decimal places
    """
    TWO_PLACES = Decimal("0.01")
    items: list[dict[str, Any]] = []
    total_item_refund = Decimal("0")

    order_item_map = {str(oi["id"]): oi for oi in input_data.order_items}

    for ri in input_data.refund_items:
        oi_id = str(ri["order_item_id"])
        oi = order_item_map[oi_id]
        qty = int(ri["quantity"])

        unit_price = Decimal(str(oi["unit_price"]))
        item_refund = (unit_price * qty).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        items.append({
            "order_item_id": oi_id,
            "product_id": str(oi["product_id"]),
            "quantity": qty,
            "unit_price": str(unit_price),
            "item_refund_amount": str(item_refund),
        })
        total_item_refund += item_refund

    total_item_refund = total_item_refund.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    # Shipping refund determination
    shipping_refund = Decimal("0")
    is_full_refund = _is_full_refund(input_data)

    if input_data.refund_type == "SHIPPING_FEE" or input_data.refund_type == "FULL" and is_full_refund:
        shipping_refund = input_data.order_shipping_fee
    # PARTIAL: no shipping refund

    shipping_refund = shipping_refund.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    # Apply caps
    max_item_refund = (input_data.order_paid_amount - input_data.cumulative_refund_amount).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    if total_item_refund > max_item_refund:
        total_item_refund = max_item_refund

    max_shipping = (input_data.order_shipping_fee - input_data.cumulative_shipping_refund).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    if shipping_refund > max_shipping:
        shipping_refund = max_shipping

    total_refund = (total_item_refund + shipping_refund).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    breakdown: dict[str, Any] = {
        "items": items,
        "total_item_refund": str(total_item_refund),
        "shipping_refund": str(shipping_refund),
        "total_refund": str(total_refund),
        "is_full_refund": is_full_refund,
        "caps_applied": {
            "max_item_refund": str(max_item_refund),
            "max_shipping_refund": str(max_shipping),
        },
    }

    return RefundCalcResult(
        items=items,
        total_refund_amount=total_refund,
        shipping_refund_amount=shipping_refund,
        calculation_breakdown=breakdown,
    )


def _is_full_refund(input_data: RefundCalcInput) -> bool:
    """Check if this refund results in all order_items being fully refunded."""
    refund_qty_map: dict[str, int] = {}
    for ri in input_data.refund_items:
        oi_id = str(ri["order_item_id"])
        refund_qty_map[oi_id] = refund_qty_map.get(oi_id, 0) + int(ri["quantity"])

    for oi in input_data.order_items:
        oi_id = str(oi["id"])
        existing_refunded = int(oi.get("refunded_quantity", 0))
        requested_refund = refund_qty_map.get(oi_id, 0)
        total_refunded = existing_refunded + requested_refund
        if total_refunded < int(oi["quantity"]):
            return False
    return True
