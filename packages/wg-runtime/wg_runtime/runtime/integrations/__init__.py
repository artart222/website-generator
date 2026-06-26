from .context import (
    IntegrationResolutionError,
    RuntimeIntegrationContext,
    get_runtime_integration_context,
    reset_runtime_integration_context_cache,
)

__all__ = [
    "IntegrationResolutionError",
    "RuntimeIntegrationContext",
    "apply_payment_callback",
    "create_checkout_order",
    "enqueue_integration_event",
    "enqueue_refund_events",
    "get_runtime_integration_context",
    "process_outbox_event",
    "requeue_dead_letter_event",
    "reset_runtime_integration_context_cache",
]

_lazy_exports = {
    "enqueue_integration_event": (".outbox", "enqueue_integration_event"),
    "process_outbox_event": (".outbox", "process_outbox_event"),
    "requeue_dead_letter_event": (".outbox", "requeue_dead_letter_event"),
    "apply_payment_callback": (".services", "apply_payment_callback"),
    "create_checkout_order": (".services", "create_checkout_order"),
    "enqueue_refund_events": (".services", "enqueue_refund_events"),
}


def __getattr__(name: str):
    if name in _lazy_exports:
        module_name, attr_name = _lazy_exports[name]
        module = __import__(f"wg_runtime.runtime.integrations{module_name}", fromlist=[attr_name])
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_lazy_exports.keys()))
