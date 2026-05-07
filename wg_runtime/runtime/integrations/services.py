from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.urls import reverse

from wg_runtime.runtime.models import Order, OrderLine, PaymentAttempt, Refund
from .context import IntegrationResolutionError, get_runtime_integration_context
from .contracts import is_error_result
from .outbox import enqueue_integration_event
from .state_machine import transition_order_status


def normalize_amount(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def _normalize_payment_status(status: str, *, verified: bool) -> str:
    normalized = str(status).strip().lower()
    if normalized in {"paid", "success", "completed"} and verified:
        return PaymentAttempt.STATUS_PAID
    if normalized in {"cancelled", "canceled"}:
        return PaymentAttempt.STATUS_CANCELLED
    return PaymentAttempt.STATUS_FAILED


def _enqueue_order_created_events(order: Order) -> None:
    payload = {
        "event": "order_created",
        "order_id": order.order_id,
        "status": order.status,
        "total_amount": str(order.total_amount),
        "currency": order.currency,
        "provider": order.provider,
    }
    enqueue_integration_event(
        event_type="order_created",
        provider_domain="notifications",
        provider_name="",
        payload=payload,
        idempotency_key=f"order_created:{order.order_id}",
    )


def _enqueue_payment_events(order: Order, payment_attempt: PaymentAttempt) -> None:
    base_payload = {
        "order_id": order.order_id,
        "payment_attempt_id": payment_attempt.attempt_id,
        "status": payment_attempt.status,
        "reference": payment_attempt.reference,
        "amount": str(payment_attempt.amount),
        "currency": payment_attempt.currency,
        "provider": payment_attempt.provider,
    }
    if payment_attempt.status == PaymentAttempt.STATUS_PAID:
        enqueue_integration_event(
            event_type="payment_succeeded",
            provider_domain="notifications",
            provider_name="",
            payload={"event": "payment_succeeded", **base_payload},
            idempotency_key=f"payment_succeeded:{order.order_id}:{payment_attempt.attempt_id}",
        )
        enqueue_integration_event(
            event_type="payment_succeeded",
            provider_domain="accounting",
            provider_name="",
            payload={"event": "payment_succeeded", **base_payload},
            idempotency_key=f"acct_payment_succeeded:{order.order_id}:{payment_attempt.attempt_id}",
        )
        enqueue_integration_event(
            event_type="order_paid",
            provider_domain="shipping",
            provider_name="",
            payload={"event": "order_paid", **base_payload},
            idempotency_key=f"shipping_order_paid:{order.order_id}",
        )
        enqueue_integration_event(
            event_type="order_paid",
            provider_domain="accounting",
            provider_name="",
            payload={"event": "order_paid", **base_payload},
            idempotency_key=f"acct_order_paid:{order.order_id}",
        )
        return

    enqueue_integration_event(
        event_type="payment_failed",
        provider_domain="notifications",
        provider_name="",
        payload={"event": "payment_failed", **base_payload},
        idempotency_key=f"payment_failed:{order.order_id}:{payment_attempt.attempt_id}",
    )
    enqueue_integration_event(
        event_type="payment_failed",
        provider_domain="accounting",
        provider_name="",
        payload={"event": "payment_failed", **base_payload},
        idempotency_key=f"acct_payment_failed:{order.order_id}:{payment_attempt.attempt_id}",
    )


def enqueue_refund_events(refund: Refund, *, settled: bool = False) -> None:
    event_name = "refund_settled" if settled else "refund_created"
    payload = {
        "event": event_name,
        "refund_id": refund.refund_id,
        "order_id": refund.order.order_id,
        "payment_attempt_id": refund.payment_attempt.attempt_id if refund.payment_attempt else "",
        "amount": str(refund.amount),
        "currency": refund.currency,
        "status": refund.status,
    }
    enqueue_integration_event(
        event_type=event_name,
        provider_domain="accounting",
        provider_name="",
        payload=payload,
        idempotency_key=f"acct_{event_name}:{refund.refund_id}",
    )
    enqueue_integration_event(
        event_type=event_name,
        provider_domain="notifications",
        provider_name="",
        payload=payload,
        idempotency_key=f"notify_{event_name}:{refund.refund_id}",
    )


def _calculate_totals_with_adapters(
    *,
    lines: list[dict[str, Any]],
    currency: str,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    subtotal_amount = sum(
        normalize_amount(line.get("price", 0)) * int(line.get("quantity", 1))
        for line in lines
    )
    tax_amount = Decimal("0.00")
    shipping_amount = Decimal("0.00")
    total_amount = subtotal_amount

    context = get_runtime_integration_context()

    tax_adapter, tax_binding = context.resolve_adapter(domain="tax")
    if tax_adapter is not None and tax_binding is not None:
        tax_result = tax_adapter.calculate_totals(
            {
                "lines": lines,
                "currency": currency,
                "subtotal_amount": str(subtotal_amount),
            },
            dict(tax_binding.provider_config),
        )
        if isinstance(tax_result, dict) and not is_error_result(tax_result):
            tax_meta = dict(tax_result.get("metadata", {}) or {})
            tax_amount = normalize_amount(tax_meta.get("tax_amount", "0"))
            total_amount = normalize_amount(
                tax_meta.get("total_amount", subtotal_amount + tax_amount)
            )

    shipping_adapter, shipping_binding = context.resolve_adapter(domain="shipping")
    if shipping_adapter is not None and shipping_binding is not None:
        shipping_result = shipping_adapter.quote_shipping(
            {
                "lines": lines,
                "currency": currency,
                "subtotal_amount": str(subtotal_amount),
                "tax_amount": str(tax_amount),
            },
            dict(shipping_binding.provider_config),
        )
        if isinstance(shipping_result, dict) and not is_error_result(shipping_result):
            shipping_meta = dict(shipping_result.get("metadata", {}) or {})
            shipping_amount = normalize_amount(
                shipping_meta.get("shipping_amount", shipping_meta.get("amount", "0"))
            )

    # Ensure final total reflects subtotal + tax + shipping unless tax adapter already provided total.
    recomputed_total = subtotal_amount + tax_amount + shipping_amount
    if total_amount < recomputed_total:
        total_amount = recomputed_total
    return subtotal_amount, tax_amount, shipping_amount, total_amount


def create_checkout_order(
    *,
    request_base_url: str,
    validated_data: dict[str, Any],
) -> tuple[Order, PaymentAttempt, str]:
    lines = validated_data.pop("lines")
    success_url = validated_data.pop("success_url", "")
    failure_url = validated_data.pop("failure_url", "")
    status_url = validated_data.pop("status_url", "")
    metadata = dict(validated_data.pop("metadata", {}) or {})

    currency = str(validated_data.get("currency", "USD"))
    subtotal_amount, tax_amount, shipping_amount, total_amount = _calculate_totals_with_adapters(
        lines=lines,
        currency=currency,
    )

    context = get_runtime_integration_context()
    provider_override = str(validated_data.pop("provider", "")).strip()
    try:
        adapter, binding = context.resolve_adapter(domain="payments", provider_name=provider_override)
    except IntegrationResolutionError:
        adapter, binding = context.resolve_adapter(domain="payments", provider_name="")
    provider_name = binding.name if binding is not None else provider_override
    adapter_name = binding.adapter_name if binding is not None else ""

    order_kwargs = {
        "subtotal_amount": subtotal_amount,
        "tax_amount": tax_amount,
        "shipping_amount": shipping_amount,
        "total_amount": total_amount,
        "success_url": success_url,
        "failure_url": failure_url,
        "status_url": status_url,
        "provider": provider_name,
        "status": Order.STATUS_PENDING_PAYMENT,
        "metadata": {
            **metadata,
            "integration_provider": provider_name,
            "integration_adapter": adapter_name,
        },
    }
    order_kwargs.update(validated_data)
    order = Order.objects.create(**order_kwargs)

    for line in lines:
        OrderLine.objects.create(
            order=order,
            title=str(line.get("title", ""))[:240],
            sku=str(line.get("sku", ""))[:120],
            quantity=int(line.get("quantity", 1)),
            price=normalize_amount(line.get("price", 0)),
            currency=str(line.get("currency", order.currency)),
            metadata=dict(line.get("metadata", {}) or {}),
        )

    payment_attempt = PaymentAttempt.objects.create(
        order=order,
        provider=provider_name,
        amount=order.total_amount,
        currency=order.currency,
        status=PaymentAttempt.STATUS_PENDING,
        metadata={"source": "checkout_session"},
    )

    callback_url = f"{request_base_url.rstrip('/')}{reverse('payment-callback')}"
    gateway_url = f"{request_base_url.rstrip('/')}{reverse('gateway-mock')}"
    redirect_url = f"{gateway_url}?order_id={order.order_id}"

    if adapter is not None and binding is not None:
        provider_cfg = dict(binding.provider_config)
        provider_cfg.setdefault("callback_url", callback_url)
        provider_cfg.setdefault("gateway_url", gateway_url)
        session_result = adapter.create_checkout_session(
            {
                "order_id": order.order_id,
                "amount": str(order.total_amount),
                "currency": order.currency,
                "lines": lines,
                "success_url": order.success_url,
                "failure_url": order.failure_url,
                "status_url": order.status_url,
            },
            provider_cfg,
        )
        if isinstance(session_result, dict) and not is_error_result(session_result):
            session_meta = dict(session_result.get("metadata", {}) or {})
            redirect_url = str(session_meta.get("redirect_url", redirect_url))
            payment_attempt.metadata = {
                **payment_attempt.metadata,
                "adapter_session": session_meta,
            }
            payment_attempt.save(update_fields=["metadata"])

    _enqueue_order_created_events(order)
    return order, payment_attempt, redirect_url


def apply_payment_callback(
    *,
    order: Order,
    requested_status: str,
    reference: str,
    idempotency_key: str = "",
) -> tuple[Order, PaymentAttempt, bool]:
    normalized_status = str(requested_status).strip().lower()
    payment_idempotency_key = (
        idempotency_key.strip()
        or f"{order.order_id}:{normalized_status}:{reference.strip()}"
    )
    existing = order.payment_attempts.filter(
        event_idempotency_key=payment_idempotency_key
    ).first()
    if existing is not None:
        return order, existing, True

    context = get_runtime_integration_context()
    verified = normalized_status in {"paid", "success", "completed"}
    provider_name = order.provider
    try:
        adapter, binding = context.resolve_adapter(domain="payments", provider_name=provider_name)
    except IntegrationResolutionError:
        adapter, binding = context.resolve_adapter(domain="payments", provider_name="")
    provider_cfg = dict(binding.provider_config) if binding is not None else {}
    if adapter is not None:
        verify_result = adapter.verify_callback(
            {
                "order_id": order.order_id,
                "status": requested_status,
                "reference": reference,
                "authority": reference,
            },
            provider_cfg,
        )
        if isinstance(verify_result, dict):
            if is_error_result(verify_result):
                verified = False
            else:
                verify_meta = dict(verify_result.get("metadata", {}) or {})
                verified = bool(verify_meta.get("verified", verified))
                reference = str(verify_result.get("reference", reference))

    payment_status = _normalize_payment_status(requested_status, verified=verified)
    payment_attempt = order.payment_attempts.create(
        provider=provider_name,
        reference=reference,
        event_idempotency_key=payment_idempotency_key,
        amount=order.total_amount,
        currency=order.currency,
        status=payment_status,
        metadata={
            "requested_status": requested_status,
            "reference": reference,
            "idempotency_key": payment_idempotency_key,
            "verified": verified,
        },
    )

    if payment_status == PaymentAttempt.STATUS_PAID:
        transition_order_status(
            order=order,
            next_status=Order.STATUS_PAID,
            actor="runtime",
            reason="payment_succeeded",
            metadata={"payment_attempt_id": payment_attempt.attempt_id},
        )
    elif payment_status == PaymentAttempt.STATUS_CANCELLED:
        transition_order_status(
            order=order,
            next_status=Order.STATUS_CANCELLED,
            actor="runtime",
            reason="payment_cancelled",
            metadata={"payment_attempt_id": payment_attempt.attempt_id},
        )
    else:
        transition_order_status(
            order=order,
            next_status=Order.STATUS_FAILED,
            actor="runtime",
            reason="payment_failed",
            metadata={"payment_attempt_id": payment_attempt.attempt_id},
        )

    _enqueue_payment_events(order, payment_attempt)
    order.refresh_from_db()
    return order, payment_attempt, False
