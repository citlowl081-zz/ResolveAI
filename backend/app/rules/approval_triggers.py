"""Approval trigger rules — deterministic checks for when human approval is required.

Returns one or more ApprovalType reasons, or empty list (no approval needed).

Triggers:
1. HIGH_REFUND — estimated refund amount exceeds configured threshold
2. RISK_HIT — user risk_level is HIGH
3. EXCHANGE — exchange always requires manual review
4. MULTI_ITEM — more than 1 item affected
"""

from __future__ import annotations

from decimal import Decimal


def check_approval_required(
    *,
    intent: str,
    estimated_refund: Decimal,
    high_refund_threshold: Decimal,
    risk_level: str,
    item_count: int,
) -> list[str]:
    """Return the list of ApprovalType values that trigger, or empty list.

    Parameters are extracted from the verified pending_action context.
    """
    triggers: list[str] = []

    # 1. High refund amount
    if estimated_refund > high_refund_threshold:
        triggers.append("HIGH_REFUND")

    # 2. Risk hit
    if risk_level == "HIGH":
        triggers.append("RISK_HIT")

    # 3. Exchange always needs review
    if intent == "EXCHANGE":
        triggers.append("EXCHANGE")

    # 4. Multiple items
    if item_count > 1:
        triggers.append("MULTI_ITEM")

    return triggers
