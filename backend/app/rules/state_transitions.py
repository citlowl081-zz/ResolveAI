"""State transition validation matrices for orders, tickets, and reshipments."""

from app.exceptions import ConflictError
from app.models.enums import OrderStatus, ReshipmentStatus, TicketStatus

# ── Order Status Transitions ──────────────────────────────────────────

ALLOWED_ORDER_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.PENDING_PAYMENT.value: {
        OrderStatus.PAID.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.PAID.value: {
        OrderStatus.SHIPPED.value,
        OrderStatus.REFUNDED.value,
    },
    OrderStatus.SHIPPED.value: {
        OrderStatus.DELIVERED.value,
        OrderStatus.REFUNDED.value,
    },
    OrderStatus.DELIVERED.value: {
        OrderStatus.REFUNDED.value,
    },
    OrderStatus.CANCELLED.value: set(),
    OrderStatus.REFUNDED.value: set(),
}

CANCELLABLE_STATUSES = {OrderStatus.PENDING_PAYMENT.value}

REQUIRES_AFTER_SALES = {
    OrderStatus.PAID.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
}

# ── Ticket Status Transitions ─────────────────────────────────────────

ALLOWED_TICKET_TRANSITIONS: dict[str, set[str]] = {
    TicketStatus.APPROVED.value: {
        TicketStatus.COMPLETED.value,
        TicketStatus.NEEDS_REVIEW.value,
        TicketStatus.CANCELLED.value,
    },
    TicketStatus.NEEDS_REVIEW.value: {
        TicketStatus.APPROVED.value,
        TicketStatus.REJECTED.value,
        TicketStatus.CANCELLED.value,
    },
    TicketStatus.REJECTED.value: set(),
    TicketStatus.COMPLETED.value: set(),
    TicketStatus.CANCELLED.value: set(),
}

# ── Reshipment Status Transitions ─────────────────────────────────────

ALLOWED_RESHIPMENT_TRANSITIONS: dict[str, set[str]] = {
    ReshipmentStatus.CREATED.value: {
        ReshipmentStatus.SHIPPED.value,
        ReshipmentStatus.CANCELLED.value,
    },
    ReshipmentStatus.SHIPPED.value: {
        ReshipmentStatus.DELIVERED.value,
    },
    ReshipmentStatus.DELIVERED.value: set(),
    ReshipmentStatus.CANCELLED.value: set(),
}


# ── Validation Functions ──────────────────────────────────────────────

def validate_order_transition(current_status: str, target_status: str) -> None:
    """Raise ConflictError if the order transition is not allowed."""
    allowed = ALLOWED_ORDER_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise ConflictError(
            f"Cannot transition order from '{current_status}' to '{target_status}'. "
            f"Allowed targets: {sorted(allowed) or 'none'}"
        )


def validate_ticket_transition(current_status: str, target_status: str) -> None:
    """Raise ConflictError if the ticket transition is not allowed."""
    allowed = ALLOWED_TICKET_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise ConflictError(
            f"Cannot transition ticket from '{current_status}' to '{target_status}'. "
            f"Allowed targets: {sorted(allowed) or 'none'}"
        )


def validate_reshipment_transition(current_status: str, target_status: str) -> None:
    """Raise ConflictError if the reshipment transition is not allowed."""
    allowed = ALLOWED_RESHIPMENT_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise ConflictError(
            f"Cannot transition reshipment from '{current_status}' to '{target_status}'. "
            f"Allowed targets: {sorted(allowed) or 'none'}"
        )


def is_cancellable(status: str) -> bool:
    """Check if order can be cancelled in Phase 02A (PENDING_PAYMENT only)."""
    return status in CANCELLABLE_STATUSES


# Backward-compatible alias for Phase 02A code
validate_transition = validate_order_transition
