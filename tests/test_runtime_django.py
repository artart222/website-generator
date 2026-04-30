import json
import os
import sys
import tempfile
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wg_runtime.settings")

import django  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.test import Client  # noqa: E402


temp_db = Path(tempfile.gettempdir()) / f"wg_runtime_test_{os.getpid()}.sqlite3"
if temp_db.exists():
    temp_db.unlink()
settings.DATABASES["default"]["NAME"] = str(temp_db)
if not django.apps.apps.ready:
    django.setup()
call_command("migrate", verbosity=0, interactive=False)


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
    assert status_payload["total_amount"] == "25.00"


def test_django_runtime_allows_cors_preflight():
    client = Client()
    response = client.options(
        "/checkout/session",
        HTTP_ORIGIN="http://localhost:8000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="Content-Type",
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"
    assert "Content-Type" in response["Access-Control-Allow-Headers"]
    assert "POST" in response["Access-Control-Allow-Methods"]


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
