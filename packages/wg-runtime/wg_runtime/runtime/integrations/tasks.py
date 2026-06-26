from __future__ import annotations

from celery import shared_task

from .outbox import list_due_outbox_event_ids, process_outbox_event


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def dispatch_outbox_event(self, event_id: int) -> str:
    event = process_outbox_event(int(event_id))
    return f"{event.id}:{event.status}"


@shared_task(bind=True)
def retry_due_outbox_events(self, limit: int = 100) -> int:
    processed = 0
    for event_id in list_due_outbox_event_ids(limit=limit):
        dispatch_outbox_event.delay(event_id)
        processed += 1
    return processed
