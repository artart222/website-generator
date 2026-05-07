from __future__ import annotations

from typing import Any

from wg_runtime.runtime.audit import log_audit_event
from wg_runtime.runtime.models import Order

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    Order.STATUS_DRAFT: {
        Order.STATUS_PENDING_PAYMENT,
        Order.STATUS_CANCELLED,
        Order.STATUS_FAILED,
    },
    Order.STATUS_PENDING_PAYMENT: {
        Order.STATUS_PAID,
        Order.STATUS_FAILED,
        Order.STATUS_CANCELLED,
    },
    Order.STATUS_PAID: {
        Order.STATUS_FULFILLED,
        Order.STATUS_PARTIALLY_REFUNDED,
        Order.STATUS_REFUNDED,
    },
    Order.STATUS_FULFILLED: {
        Order.STATUS_PARTIALLY_REFUNDED,
        Order.STATUS_REFUNDED,
    },
    Order.STATUS_PARTIALLY_REFUNDED: {Order.STATUS_REFUNDED},
    Order.STATUS_REFUNDED: set(),
    Order.STATUS_CANCELLED: set(),
    Order.STATUS_FAILED: {Order.STATUS_PENDING_PAYMENT, Order.STATUS_CANCELLED},
}


def transition_order_status(
    *,
    order: Order,
    next_status: str,
    actor: str = "system",
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> Order:
    current = str(order.status)
    target = str(next_status).strip()
    if not target:
        raise ValueError("next_status cannot be empty")

    if current == target:
        return order

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid order status transition '{current}' -> '{target}'.")

    order.status = target
    order.save(update_fields=["status", "updated_at"])
    log_audit_event(
        action="order.status_transition",
        actor=actor[:192],
        model_name="Order",
        object_id=str(order.pk),
        description=f"Order {order.order_id} transitioned from {current} to {target}.",
        metadata={
            "source": "runtime",
            "from_status": current,
            "to_status": target,
            "reason": reason,
            **(metadata or {}),
        },
    )
    return order
