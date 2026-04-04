from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from extensions.base import BaseExtension


COMMERCE_MODELS = {
    "product": {
        "fields": {
            "sku": {"type": "string", "required": True},
            "price": {"type": "number", "required": True},
            "currency": {"type": "string", "default": "IRR"},
            "availability": {"type": "string", "default": "in_stock"},
            "images": {"type": "list", "items_type": "string", "default": []},
            "variants": {"type": "list", "items_type": "object", "default": []},
            "attributes": {"type": "object", "default": {}},
            "payment_methods": {"type": "list", "items_type": "string", "default": []},
            "checkout_provider": {"type": "string", "default": ""},
        }
    },
    "category": {
        "fields": {
            "layout": {"type": "string", "default": "collection"},
        }
    },
}


class CommercePaymentAdapter(ABC):
    """Runtime interface for commerce payment providers."""

    name = ""

    @abstractmethod
    def create_checkout_session(
        self, order_input: dict[str, Any], store_config: dict[str, Any]
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def verify_callback(
        self, callback_input: dict[str, Any], store_config: dict[str, Any]
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_public_order_status(
        self, order_id: str, store_config: dict[str, Any]
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def supports_currency(self, currency_code: str) -> bool:
        raise NotImplementedError


class ShaparakLikePaymentAdapter(CommercePaymentAdapter):
    """Reference adapter contract for Iranian gateway-style integrations."""

    name = "commerce.payment.ir.shaparak_like"

    def create_checkout_session(
        self, order_input: dict[str, Any], store_config: dict[str, Any]
    ) -> dict[str, Any]:
        callback_url = str(store_config.get("callback_url", ""))
        gateway_url = str(store_config.get("gateway_url", "/payments/redirect"))
        return {
            "provider": self.name,
            "method": "redirect",
            "gateway_url": gateway_url,
            "callback_url": callback_url,
            "order_input": order_input,
        }

    def verify_callback(
        self, callback_input: dict[str, Any], store_config: dict[str, Any]
    ) -> dict[str, Any]:
        authority = str(callback_input.get("authority", ""))
        return {
            "provider": self.name,
            "verified": bool(authority),
            "reference": authority,
        }

    def get_public_order_status(
        self, order_id: str, store_config: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "order_id": order_id,
            "status": "pending",
            "provider": self.name,
        }

    def supports_currency(self, currency_code: str) -> bool:
        return str(currency_code).upper() in {"IRR", "IRT"}


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


def get_extension() -> CommerceExtension:
    return CommerceExtension()
