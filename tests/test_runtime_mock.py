import json
import os
import socket
import sys
import tempfile
from pathlib import Path
import pytest
from urllib import request

from wg_runtime.mock_server import run_mock_runtime_in_thread  # noqa: E402


class _NoRedirectHandler(request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        fp.status = code
        fp.code = code
        return fp

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _read_json_response(url: str, *, method: str = "GET", payload: dict | None = None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_mock_runtime_checkout_flow():
    try:
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
            (Path(temp_dir) / "probe").mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pytest.skip("Current interpreter cannot create directories in this environment.")

    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        config_path = temp_path / "config.yaml"
        port = _find_free_port()
        config_path.write_text(
            f"""version: 2
site:
  base_url: http://127.0.0.1:8000
extensions:
  enabled:
    - wg-commerce
runtime:
  targets:
    - name: commerce-api
      type: fastapi_service
      public_base_url: http://127.0.0.1:{port}
integrations:
  payments:
    default: iran_gateway
    providers:
      iran_gateway:
        adapter: commerce.payment.ir.shaparak_like
        runtime_target: commerce-api
        currency: IRR
        callback_url: http://127.0.0.1:{port}/payments/callback
""",
            encoding="utf-8",
        )

        with run_mock_runtime_in_thread(
            host="127.0.0.1",
            port=port,
            config_path=str(config_path),
        ):
            checkout_payload = _read_json_response(
                f"http://127.0.0.1:{port}/checkout/session",
                method="POST",
                payload={
                    "sku": "COPPER-TRAY-01",
                    "title": "Copper Tea Tray",
                    "price": "3290000",
                    "currency": "IRR",
                    "quantity": 1,
                    "variant_id": "tray-34",
                    "variant_label": "34 cm service tray",
                    "success_url": "http://example.com/order-confirmed/",
                    "failure_url": "http://example.com/payment-not-completed/",
                    "status_url": "http://example.com/order-status/",
                },
            )

            order_id = checkout_payload["order_id"]
            assert checkout_payload["redirect_url"].startswith(
                f"http://127.0.0.1:{port}/gateway/mock"
            )

            gateway_html = request.urlopen(
                checkout_payload["redirect_url"], timeout=5
            ).read().decode("utf-8")
            assert "Approve payment" in gateway_html
            assert order_id in gateway_html

            no_redirect = request.build_opener(_NoRedirectHandler())
            callback_response = no_redirect.open(
                f"http://127.0.0.1:{port}/payments/callback?order_id={order_id}&status=paid&reference=TEST-123",
                timeout=5,
            )
            assert callback_response.status == 302
            assert callback_response.headers["Location"].startswith(
                "http://example.com/order-confirmed/"
            )

            status_payload = _read_json_response(
                f"http://127.0.0.1:{port}/orders/{order_id}"
            )
            assert status_payload["status"] == "paid"
            assert status_payload["reference"] == "TEST-123"
            assert status_payload["variant_label"] == "34 cm service tray"
