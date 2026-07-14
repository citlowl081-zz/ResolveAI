"""PendingActionBuilder — server-side construction of canonical_tool_input.

The LLM provides natural keys (order_number, product_name, etc.).
This builder resolves them to internal UUIDs from verified OrderService data.
Internal UUIDs are stored in context_snapshot but NEVER returned to the LLM or client.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from app.config.settings import settings


def _hash_canonical(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_pending_action(
    *,
    intent: str,
    order_context: dict,            # Verified order data from AgentState.context
    items_spec: list[dict],         # LLM output: [{product_name, quantity, reason_code}]
    description: str,
) -> dict | None:
    """Construct a pending_action from LLM natural keys + verified context.

    Returns None if the order items cannot be resolved (should not happen
    if the LLM is working correctly with the context provided).
    """
    order_items = order_context.get("items", [])
    if not order_items:
        return None

    requested_items: list[dict] = []
    for spec in items_spec:
        product_name = spec.get("product_name", "")
        quantity = spec.get("quantity", 1)
        reason_code = spec.get("reason_code", "OTHER")

        # Match product_name to order items
        match = None
        for oi in order_items:
            if oi.get("product_name", "").lower() == product_name.lower():
                match = oi
                break

        if match is None:
            return None  # Cannot resolve — builder fails safe

        available = match.get("quantity", 0) - match.get("refunded_quantity", 0) - match.get("reshipped_quantity", 0)
        if quantity > available:
            quantity = available  # Clamp to available (Service layer will also validate)

        if quantity <= 0:
            continue

        requested_items.append({
            "order_item_id": match["id"],
            "product_id": match["product_id"],
            "quantity": quantity,
            "reason_code": reason_code,
        })

    if not requested_items:
        return None

    order_id = order_context.get("id", "")

    canonical_tool_input = {
        "order_id": order_id,
        "intent": intent,
        "requested_items": requested_items,
        "customer_request": description or "",
    }

    action_id = uuid.uuid4()
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.agent_pending_action_expiry_seconds)

    return {
        "action_id": str(action_id),
        "tool_name": "create_after_sales_ticket",
        "canonical_tool_input": canonical_tool_input,
        "request_hash": _hash_canonical(canonical_tool_input),
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "status": "PENDING",
    }


def build_proposed_action_response(pending_action: dict) -> dict:
    """Return the client-safe proposed_action (no internal UUIDs)."""
    return {
        "action_id": pending_action["action_id"],
        "tool_name": pending_action["tool_name"],
        "description": pending_action.get("description", ""),
        "status": "pending_confirmation",
        "expires_at": pending_action["expires_at"],
    }


def validate_pending_action(
    pending_action: dict | None,
    confirm_action_id: str,
) -> tuple[bool, str | None]:
    """Validate a confirm_action_id against stored pending_action.

    Returns (is_valid, error_code).
    """
    if pending_action is None:
        return False, "ACTION_NOT_FOUND"

    if pending_action.get("action_id") != confirm_action_id:
        return False, "ACTION_NOT_FOUND"

    if pending_action.get("status") != "PENDING":
        return False, "ACTION_ALREADY_CONSUMED"

    expires_at_str = pending_action.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at < datetime.now(UTC):
                return False, "ACTION_EXPIRED"
        except (ValueError, TypeError):
            return False, "ACTION_EXPIRED"

    return True, None
