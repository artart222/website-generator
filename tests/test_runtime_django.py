import json

import pytest
from django.test import Client

from wg_runtime.runtime.models import IntegrationOutboxEvent

# Every test in this module gets a clean, isolated database (rolled back after).
pytestmark = pytest.mark.django_db


def test_django_runtime_checkout_flow():
    client = Client()
    payload = {
        "provider": "local_gateway",
        "currency": "USD",
        "success_url": "http://example.com/success",
        "failure_url": "http://example.com/failure",
        "status_url": "http://example.com/status",
        "lines": [
            {
                "title": "Test Product",
                "sku": "SKU-001",
                "quantity": 2,
                "price": "12.50",
                "currency": "USD",
            }
        ],
    }

    response = client.post(
        "/checkout/session",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["redirect_url"].startswith("http://")
    assert data["order_id"]

    order_id = data["order_id"]
    callback = client.get(
        "/payments/callback",
        {
            "order_id": order_id,
            "status": "paid",
            "reference": "TEST-REF",
        },
    )
    assert callback.status_code == 302
    assert "success" in callback.url

    status_response = client.get(f"/orders/{order_id}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["order_id"] == order_id
    assert status_payload["status"] == "paid"
    assert status_payload["subtotal_amount"] == "25.00"
    assert status_payload["tax_amount"] == "2.25"
    assert status_payload["shipping_amount"] == "0.00"
    assert status_payload["total_amount"] == "27.25"

    outbox_types = set(IntegrationOutboxEvent.objects.values_list("event_type", flat=True))
    assert "order_created" in outbox_types
    assert "payment_succeeded" in outbox_types
    assert "order_paid" in outbox_types


def test_django_runtime_cors_preflight_echoes_allowed_origin_only():
    """CORS is scoped to an allow-list (no blanket ``*`` in production)."""
    from django.test import override_settings

    client = Client()
    allowed = "http://localhost:8000"
    with override_settings(DEBUG=False, WG_CORS_ALLOWED_ORIGINS=[allowed]):
        ok = client.options(
            "/checkout/session",
            HTTP_ORIGIN=allowed,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="Content-Type",
        )
        assert ok.status_code == 200
        assert ok["Access-Control-Allow-Origin"] == allowed
        assert "Content-Type" in ok["Access-Control-Allow-Headers"]
        assert "POST" in ok["Access-Control-Allow-Methods"]

        # A disallowed origin receives no CORS grant.
        denied = client.options(
            "/checkout/session",
            HTTP_ORIGIN="https://evil.example.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        assert "Access-Control-Allow-Origin" not in denied


def test_django_runtime_allows_cross_origin_post_without_csrf():
    client = Client(enforce_csrf_checks=True)
    payload = {
        "provider": "local_gateway",
        "currency": "USD",
        "success_url": "http://example.com/success",
        "failure_url": "http://example.com/failure",
        "status_url": "http://example.com/status",
        "lines": [
            {
                "title": "Test Product",
                "sku": "SKU-001",
                "quantity": 2,
                "price": "12.50",
                "currency": "USD",
            }
        ],
    }

    response = client.post(
        "/checkout/session",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["order_id"]


def test_django_runtime_catalog_snapshot_endpoint_returns_published_products():
    from wg_runtime.runtime.models import Product, ProductVariant

    product = Product.objects.create(
        name="Snapshot Product",
        slug="snapshot-product",
        description="Snapshot product description",
        is_published=True,
        metadata={"source": "runtime"},
    )
    ProductVariant.objects.create(
        product=product,
        sku="SNAP-001",
        label="Snapshot Variant",
        price="29.99",
        currency="USD",
        is_published=True,
        metadata={"inventory": "in_stock"},
    )

    unpublished = Product.objects.create(
        name="Hidden Product",
        slug="hidden-product",
        description="Should not be visible",
        is_published=False,
    )
    ProductVariant.objects.create(
        product=unpublished,
        sku="HIDDEN-001",
        label="Hidden Variant",
        price="9.99",
        currency="USD",
        is_published=True,
    )

    client = Client()
    response = client.get("/catalog/snapshot")
    assert response.status_code == 200
    payload = response.json()
    assert "products" in payload
    assert len(payload["products"]) == 1
    assert payload["products"][0]["slug"] == "snapshot-product"
    assert payload["products"][0]["variants"][0]["sku"] == "SNAP-001"


def test_django_runtime_callback_is_idempotent_for_duplicate_event_key():
    client = Client()
    payload = {
        "provider": "local_gateway",
        "currency": "USD",
        "success_url": "http://example.com/success",
        "failure_url": "http://example.com/failure",
        "status_url": "http://example.com/status",
        "lines": [
            {
                "title": "Test Product",
                "sku": "SKU-001",
                "quantity": 1,
                "price": "10.00",
                "currency": "USD",
            }
        ],
    }
    response = client.post(
        "/checkout/session",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    order_id = response.json()["order_id"]

    callback_payload = {
        "order_id": order_id,
        "status": "paid",
        "reference": "TEST-IDEMP",
        "idempotency_key": "evt-001",
    }
    first = client.post("/payments/callback", data=json.dumps(callback_payload), content_type="application/json")
    second = client.post("/payments/callback", data=json.dumps(callback_payload), content_type="application/json")
    assert first.status_code == 200
    assert second.status_code == 200

    from wg_runtime.runtime.models import Order, PaymentAttempt

    order = Order.objects.get(order_id=order_id)
    attempts = PaymentAttempt.objects.filter(order=order, event_idempotency_key="evt-001")
    assert attempts.count() == 1
    assert order.status == "paid"


def test_payment_callback_rejects_forged_request_when_signing_required():
    """With signed callbacks required, an unsigned callback cannot mark paid."""
    import hashlib
    import hmac

    from django.test import override_settings

    client = Client()
    checkout = client.post(
        "/checkout/session",
        data=json.dumps(
            {
                "currency": "USD",
                "success_url": "http://example.com/success",
                "failure_url": "http://example.com/failure",
                "status_url": "http://example.com/status",
                "lines": [
                    {"title": "P", "sku": "S-1", "quantity": 1, "price": "10.00", "currency": "USD"}
                ],
            }
        ),
        content_type="application/json",
    )
    order_id = checkout.json()["order_id"]

    secret = "top-secret"
    with override_settings(
        WG_REQUIRE_SIGNED_CALLBACKS=True, WG_PAYMENT_CALLBACK_SECRET=secret
    ):
        # Forged (unsigned) callback is rejected and the order is NOT paid.
        forged = client.post(
            "/payments/callback",
            data=json.dumps({"order_id": order_id, "status": "paid", "reference": "X"}),
            content_type="application/json",
        )
        assert forged.status_code == 400

        from wg_runtime.runtime.models import Order

        assert Order.objects.get(order_id=order_id).status != "paid"

        # Correctly signed callback succeeds.
        message = f"{order_id}:paid:X".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        signed = client.post(
            "/payments/callback",
            data=json.dumps(
                {"order_id": order_id, "status": "paid", "reference": "X", "signature": signature}
            ),
            content_type="application/json",
        )
        assert signed.status_code == 200
        assert Order.objects.get(order_id=order_id).status == "paid"
