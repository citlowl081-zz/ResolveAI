"""Order state transition validation matrix."""

from app.exceptions import ConflictError
from app.models.enums import OrderStatus

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.PENDING_PAYMENT.value: {
        OrderStatus.PAID.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.PAID.value: {
        OrderStatus.SHIPPED.value,
    },
    OrderStatus.SHIPPED.value: {
        OrderStatus.DELIVERED.value,
    },
    OrderStatus.DELIVERED.value: set(),
    OrderStatus.CANCELLED.value: set(),
}

CANCELLABLE_STATUSES = {OrderStatus.PENDING_PAYMENT.value}

REQUIRES_AFTER_SALES = {
    OrderStatus.PAID.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
}


def validate_transition(current_status: str, target_status: str) -> None:
    """Raise ConflictError if the transition is not allowed."""
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise ConflictError(
            f"Cannot transition from '{current_status}' to '{target_status}'. "
            f"Allowed targets: {sorted(allowed) or 'none'}"
        )


def is_cancellable(status: str) -> bool:
    """Check if order can be cancelled in Phase 02A (PENDING_PAYMENT only)."""
    return status in CANCELLABLE_STATUSES
