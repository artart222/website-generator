from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .integrations.services import enqueue_refund_events
from .models import Refund


@receiver(post_save, sender=Refund)
def emit_refund_events(sender, instance: Refund, created: bool, **kwargs):
    if created:
        enqueue_refund_events(instance, settled=False)
        return
    if str(instance.status).strip().lower() == "settled":
        enqueue_refund_events(instance, settled=True)
