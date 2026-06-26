from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
import json
import logging
from pathlib import Path
from typing import Any

from extensions.base import BaseExtension
from wg_contracts.integrations import (
    AdapterResult,
    error_result,
    ok_result,
)

COMMERCE_MODELS = {
    "product": {
        "fields": {
            "sku": {"type": "string", "required": True},
            "price": {"type": "number", "required": True},
            "price_compare_at": {"type": "number", "default": None},
            "currency": {"type": "string", "default": "IRR"},
            "availability": {"type": "string", "default": "in_stock"},
            "badge": {"type": "string", "default": ""},
            "images": {"type": "list", "items_type": "string", "default": []},
            "variants": {"type": "list", "items_type": "object", "default": []},
            "variant_name": {"type": "string", "default": "Edition"},
            "attributes": {"type": "object", "default": {}},
            "highlights": {"type": "list", "items_type": "string", "default": []},
            "shipping_note": {"type": "string", "default": ""},
            "lead_time": {"type": "string", "default": ""},
            "payment_methods": {"type": "list", "items_type": "string", "default": []},
            "checkout_provider": {"type": "string", "default": ""},
            "tax_class": {"type": "string", "default": ""},
            "shipping_class": {"type": "string", "default": ""},
        }
    },
    "category": {
        "fields": {
            "layout": {"type": "string", "default": "collection"},
        }
    },
}


class CommercePaymentAdapter(ABC):
    name = ""

    @abstractmethod
    def create_checkout_session(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        raise NotImplementedError

    @abstractmethod
    def verify_callback(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        raise NotImplementedError

    @abstractmethod
    def get_public_order_status(
        self, order_id: str, provider_config: dict[str, Any]
    ) -> AdapterResult:
        raise NotImplementedError

    @abstractmethod
    def supports_currency(self, currency_code: str) -> bool:
        raise NotImplementedError


class ShaparakLikePaymentAdapter(CommercePaymentAdapter):
    name = "commerce.payment.ir.shaparak_like"

    def create_checkout_session(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        callback_url = str(provider_config.get("callback_url", ""))
        gateway_url = str(provider_config.get("gateway_url", "/payments/redirect"))
        order_id = str(payload.get("order_id", ""))
        redirect_url = f"{gateway_url}?order_id={order_id}" if order_id else gateway_url
        return ok_result(
            provider=self.name,
            result_id=order_id,
            metadata={
                "method": "redirect",
                "gateway_url": gateway_url,
                "callback_url": callback_url,
                "redirect_url": redirect_url,
            },
        )

    def verify_callback(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        authority = str(payload.get("authority", payload.get("reference", ""))).strip()
        verified = bool(authority)
        if not verified:
            return error_result(
                provider=self.name,
                code="missing_authority",
                message="Missing authority/reference for callback verification.",
                retryable=False,
            )
        return ok_result(
            provider=self.name,
            reference=authority,
            metadata={"verified": True, "authority": authority},
        )

    def get_public_order_status(
        self, order_id: str, provider_config: dict[str, Any]
    ) -> AdapterResult:
        return ok_result(
            provider=self.name,
            result_id=order_id,
            metadata={"order_id": order_id, "status": "pending"},
        )

    def supports_currency(self, currency_code: str) -> bool:
        return str(currency_code).upper() in {"IRR", "IRT"}


class LocalConsoleNotificationAdapter:
    name = "commerce.notification.local_console"
    logger = logging.getLogger(__name__)

    def send_notification(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        destination = str(provider_config.get("destination", "console"))
        self.logger.info(
            "[notification:%s] %s",
            destination,
            json.dumps(payload, ensure_ascii=False),
        )
        return ok_result(
            provider=self.name,
            metadata={"destination": destination, "event": payload.get("event", "")},
        )


class FlatRateShippingAdapter:
    name = "commerce.shipping.flat_rate"

    def quote_shipping(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        flat_rate = Decimal(str(provider_config.get("flat_rate", "0")))
        currency = str(payload.get("currency", provider_config.get("currency", "USD")))
        return ok_result(
            provider=self.name,
            metadata={
                "shipping_amount": str(flat_rate.quantize(Decimal("0.01"))),
                "currency": currency,
                "quote_type": "flat_rate",
            },
        )

    def create_shipment(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        order_id = str(payload.get("order_id", "")).strip()
        if not order_id:
            return error_result(
                provider=self.name,
                code="missing_order_id",
                message="order_id is required to create shipment.",
                retryable=False,
            )
        tracking_prefix = str(provider_config.get("tracking_prefix", "TRK"))
        tracking_code = f"{tracking_prefix}-{order_id}"
        return ok_result(
            provider=self.name,
            reference=tracking_code,
            metadata={
                "order_id": order_id,
                "shipment_status": "created",
                "tracking_code": tracking_code,
                "tracking_url": f"/tracking/{tracking_code}",
            },
        )


class JsonlAccountingExporterAdapter:
    name = "commerce.accounting.jsonl_exporter"

    def export_record(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        output_file = str(
            provider_config.get("output_file", "./output/runtime/accounting-export.jsonl")
        )
        output_path = Path(output_file).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return ok_result(
            provider=self.name,
            metadata={"output_file": str(output_path), "exported": True},
        )


class SimpleVatTaxPricingAdapter:
    name = "commerce.tax.simple_vat"

    def calculate_totals(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> AdapterResult:
        subtotal = Decimal(str(payload.get("subtotal_amount", "0")))
        rate_percent = Decimal(str(provider_config.get("rate_percent", "0")))
        inclusive = bool(provider_config.get("inclusive", False))

        if rate_percent < 0:
            return error_result(
                provider=self.name,
                code="invalid_rate",
                message="Tax rate cannot be negative.",
                retryable=False,
            )

        if inclusive and rate_percent > 0:
            tax_amount = (subtotal * rate_percent) / (Decimal("100") + rate_percent)
            total_amount = subtotal
        else:
            tax_amount = (subtotal * rate_percent) / Decimal("100")
            total_amount = subtotal + tax_amount

        tax_amount = tax_amount.quantize(Decimal("0.01"))
        total_amount = total_amount.quantize(Decimal("0.01"))
        return ok_result(
            provider=self.name,
            metadata={
                "subtotal_amount": str(subtotal.quantize(Decimal("0.01"))),
                "tax_amount": str(tax_amount),
                "total_amount": str(total_amount),
                "rate_percent": str(rate_percent),
                "inclusive": inclusive,
            },
        )


class CommerceExtension(BaseExtension):
    name = "wg-commerce"

    def register_models(self, registry) -> None:
        registry.register_many(COMMERCE_MODELS, source=self.name)

    def register_runtime_adapters(self, registry) -> None:
        registry.register(
            ShaparakLikePaymentAdapter.name,
            ShaparakLikePaymentAdapter,
            metadata={
                "kind": "payment_provider",
                "currencies": ["IRR", "IRT"],
                "checkout_flow": "redirect_with_callback",
            },
        )
        registry.register(
            LocalConsoleNotificationAdapter.name,
            LocalConsoleNotificationAdapter,
            metadata={
                "kind": "notification_provider",
                "channels": ["console"],
            },
        )
        registry.register(
            FlatRateShippingAdapter.name,
            FlatRateShippingAdapter,
            metadata={
                "kind": "shipping_provider",
                "quote_mode": "flat_rate",
            },
        )
        registry.register(
            JsonlAccountingExporterAdapter.name,
            JsonlAccountingExporterAdapter,
            metadata={
                "kind": "accounting_exporter",
                "format": "jsonl",
            },
        )
        registry.register(
            SimpleVatTaxPricingAdapter.name,
            SimpleVatTaxPricingAdapter,
            metadata={
                "kind": "tax_pricing_provider",
                "mode": "percentage",
            },
        )


def get_extension() -> CommerceExtension:
    return CommerceExtension()
