from __future__ import annotations

from typing import Any

from .models import AuditEvent


def get_actor_label(user: Any) -> str:
    if user is None:
        return ""
    username = getattr(user, "get_username", None)
    if callable(username):
        value = username()
        if value:
            return str(value)
    return str(getattr(user, "username", "") or "")


def log_audit_event(
    *,
    action: str,
    actor: str = "",
    model_name: str = "",
    object_id: str = "",
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    return AuditEvent.objects.create(
        actor=actor[:192],
        action=action[:120],
        model_name=model_name[:120],
        object_id=object_id[:128],
        description=description,
        metadata=metadata or {},
    )


def log_model_audit_event(
    *,
    action: str,
    user: Any,
    instance: Any,
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    model_name = instance.__class__.__name__
    object_id = str(getattr(instance, "pk", "") or "")
    return log_audit_event(
        action=action,
        actor=get_actor_label(user),
        model_name=model_name,
        object_id=object_id,
        description=description,
        metadata=metadata or {},
    )
