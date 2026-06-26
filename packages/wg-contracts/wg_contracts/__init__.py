"""Shared ports and contracts for the website-generator ecosystem.

This package contains ONLY interfaces and small value types. It has no heavy
dependencies (no Django, no markdown engine, no filesystem side effects) so that
every other package can depend on it without creating a dependency cycle:

    wg-core      --> wg_contracts
    wg-runtime   --> wg_contracts
    wg-commerce  --> wg_contracts

Nothing here imports wg-core or wg-runtime. This is the dependency sink that
breaks the former SSG <-> runtime cycle.
"""

from .extension import BaseExtension
from .integrations import (
    KIND_ACCOUNTING_EXPORTER,
    KIND_NOTIFICATION_PROVIDER,
    KIND_PAYMENT_PROVIDER,
    KIND_SHIPPING_PROVIDER,
    KIND_TAX_PRICING_PROVIDER,
    AccountingExporterAdapter,
    AdapterError,
    AdapterResult,
    NotificationProviderAdapter,
    PaymentProviderAdapter,
    ShippingProviderAdapter,
    TaxPricingProviderAdapter,
    error_result,
    is_error_result,
    ok_result,
)

__all__ = [
    "BaseExtension",
    "KIND_ACCOUNTING_EXPORTER",
    "KIND_NOTIFICATION_PROVIDER",
    "KIND_PAYMENT_PROVIDER",
    "KIND_SHIPPING_PROVIDER",
    "KIND_TAX_PRICING_PROVIDER",
    "AccountingExporterAdapter",
    "AdapterError",
    "AdapterResult",
    "NotificationProviderAdapter",
    "PaymentProviderAdapter",
    "ShippingProviderAdapter",
    "TaxPricingProviderAdapter",
    "error_result",
    "is_error_result",
    "ok_result",
]
