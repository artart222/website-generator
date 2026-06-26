"""Backward-compatible shim.

The integration contracts now live in the dependency-free :mod:`wg_contracts`
package so that both the runtime and provider adapters can depend on them
without importing each other. This module re-exports them for existing
``wg_runtime`` internal imports.
"""

from __future__ import annotations

from wg_contracts.integrations import (
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
