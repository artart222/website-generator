from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from wg_runtime.runtime.models import IntegrationOutboxEvent
from .context import IntegrationResolutionError, get_runtime_integration_context
from wg_contracts.integrations import AdapterResult, is_error_result


RETRYABLE_DOMAINS = {"notifications", "shipping", "accounting"}


def _compute_backoff(attempts: int) -> timedelta:
    seconds = min(3600, max(10, 2 ** max(1, attempts)))
    return timedelta(seconds=seconds)


def enqueue_integration_event(
    *,
    event_type: str,
    provider_domain: str,
    provider_name: str,
    payload: dict[str, Any],
    idempotency_key: str = "",
    metadata: dict[str, Any] | None = None,
    max_attempts: int = 5,
) -> IntegrationOutboxEvent:
    event_idempotency_key = idempotency_key.strip()
    if event_idempotency_key:
        existing = IntegrationOutboxEvent.objects.filter(
            idempotency_key=event_idempotency_key
        ).first()
        if existing is not None:
            return existing

    event = IntegrationOutboxEvent.objects.create(
        event_type=str(event_type),
        provider_domain=str(provider_domain),
        provider_name=str(provider_name),
        payload=payload or {},
        metadata=metadata or {},
        max_attempts=max(1, int(max_attempts)),
        idempotency_key=event_idempotency_key,
        next_attempt_at=timezone.now(),
    )

    # Import lazily to avoid Celery import cycles during Django startup.
    try:
        from .tasks import dispatch_outbox_event

        dispatch_outbox_event.delay(event.id)
    except Exception:
        # Best effort enqueue: processing is retried by scanner task.
        pass
    return event


def _dispatch_with_adapter(
    *,
    domain: str,
    event_type: str,
    payload: dict[str, Any],
    provider_name: str,
) -> AdapterResult:
    context = get_runtime_integration_context()
    adapter, binding = context.resolve_adapter(domain=domain, provider_name=provider_name)
    if adapter is None or binding is None:
        return {
            "status": "error",
            "provider": "",
            "metadata": {},
            "error": {
                "code": "provider_not_configured",
                "message": f"No provider configured for domain '{domain}'.",
                "retryable": False,
                "details": {"domain": domain},
            },
        }

    provider_cfg = dict(binding.provider_config)
    if domain == "notifications":
        return adapter.send_notification(payload, provider_cfg)
    if domain == "shipping":
        if event_type == "order_paid":
            return adapter.create_shipment(payload, provider_cfg)
        return adapter.quote_shipping(payload, provider_cfg)
    if domain == "accounting":
        return adapter.export_record(payload, provider_cfg)
    raise IntegrationResolutionError(f"Unsupported outbox domain '{domain}'.")


@transaction.atomic
def process_outbox_event(event_id: int) -> IntegrationOutboxEvent:
    event = (
        IntegrationOutboxEvent.objects.select_for_update()
        .filter(id=event_id)
        .first()
    )
    if event is None:
        raise ValueError(f"Outbox event '{event_id}' was not found.")

    if event.status == IntegrationOutboxEvent.STATUS_SUCCEEDED:
        return event

    event.status = IntegrationOutboxEvent.STATUS_PROCESSING
    event.save(update_fields=["status", "updated_at"])

    try:
        result = _dispatch_with_adapter(
            domain=event.provider_domain,
            event_type=event.event_type,
            payload=dict(event.payload or {}),
            provider_name=event.provider_name,
        )
    except Exception as exc:
        result = {
            "status": "error",
            "provider": event.provider_name,
            "metadata": {},
            "error": {
                "code": "dispatch_exception",
                "message": str(exc),
                "retryable": True,
                "details": {"exception_type": exc.__class__.__name__},
            },
        }

    event.result_payload = dict(result.get("metadata", {}) or {})
    error_cfg = result.get("error", {}) if isinstance(result, dict) else {}
    retryable = bool(error_cfg.get("retryable", False))
    if not isinstance(result, dict) or is_error_result(result):
        event.attempts += 1
        event.last_error = str(error_cfg.get("message", "Unknown integration error"))
        if event.attempts >= event.max_attempts:
            event.status = IntegrationOutboxEvent.STATUS_DEAD_LETTER
            event.next_attempt_at = None
        else:
            event.status = IntegrationOutboxEvent.STATUS_FAILED
            if event.provider_domain in RETRYABLE_DOMAINS and retryable:
                event.next_attempt_at = timezone.now() + _compute_backoff(event.attempts)
            else:
                event.next_attempt_at = None
        event.save(
            update_fields=[
                "status",
                "attempts",
                "last_error",
                "result_payload",
                "next_attempt_at",
                "updated_at",
            ]
        )
        return event

    event.status = IntegrationOutboxEvent.STATUS_SUCCEEDED
    event.last_error = ""
    event.next_attempt_at = None
    event.save(
        update_fields=[
            "status",
            "last_error",
            "result_payload",
            "next_attempt_at",
            "updated_at",
        ]
    )
    return event


def requeue_dead_letter_event(event_id: int) -> IntegrationOutboxEvent:
    event = IntegrationOutboxEvent.objects.filter(id=event_id).first()
    if event is None:
        raise ValueError(f"Outbox event '{event_id}' was not found.")
    event.status = IntegrationOutboxEvent.STATUS_PENDING
    event.last_error = ""
    event.next_attempt_at = timezone.now()
    event.save(update_fields=["status", "last_error", "next_attempt_at", "updated_at"])
    return event


def list_due_outbox_event_ids(*, limit: int = 100) -> list[int]:
    now = timezone.now()
    due_qs = IntegrationOutboxEvent.objects.filter(
        status__in=[
            IntegrationOutboxEvent.STATUS_PENDING,
            IntegrationOutboxEvent.STATUS_FAILED,
        ],
    ).filter(
        Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now)
    )
    return list(due_qs.order_by("created_at").values_list("id", flat=True)[: max(1, int(limit))])
