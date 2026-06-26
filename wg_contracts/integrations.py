"""Runtime integration ports (payment, notification, shipping, accounting, tax).

These define the contract between the commerce runtime and provider adapters.
Adapters live in ``wg-commerce`` (or third-party packages); the runtime resolves
and calls them through these Protocols. Both sides depend only on this module.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict

KIND_PAYMENT_PROVIDER = "payment_provider"
KIND_NOTIFICATION_PROVIDER = "notification_provider"
KIND_SHIPPING_PROVIDER = "shipping_provider"
KIND_ACCOUNTING_EXPORTER = "accounting_exporter"
KIND_TAX_PRICING_PROVIDER = "tax_pricing_provider"


class AdapterError(TypedDict, total=False):
    code: str
    message: str
    retryable: bool
    details: dict[str, Any]


class AdapterResult(TypedDict, total=False):
    status: Literal["ok", "error"]
    provider: str
    reference: str
    id: str
    metadata: dict[str, Any]
    error: AdapterError


def ok_result(
    *,
    provider: str,
    reference: str = "",
    result_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> AdapterResult:
    return {
        "status": "ok",
        "provider": provider,
        "reference": reference,
        "id": result_id,
        "metadata": metadata or {},
    }


def error_result(
    *,
    provider: str,
    code: str,
    message: str,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> AdapterResult:
    return {
        "status": "error",
        "provider": provider,
        "metadata": {},
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details or {},
        },
    }


def is_error_result(result: AdapterResult) -> bool:
    return str(result.get("status", "")).lower() == "error"


class PaymentProviderAdapter(Protocol):
    def create_checkout_session(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult: ...

    def verify_callback(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult: ...

    def get_public_order_status(
        self, order_id: str, provider_config: dict[str, Any]
    ) -> AdapterResult: ...

    def supports_currency(self, currency_code: str) -> bool: ...


class NotificationProviderAdapter(Protocol):
    def send_notification(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult: ...


class ShippingProviderAdapter(Protocol):
    def quote_shipping(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult: ...

    def create_shipment(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult: ...


class AccountingExporterAdapter(Protocol):
    def export_record(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult: ...


class TaxPricingProviderAdapter(Protocol):
    def calculate_totals(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult: ...
