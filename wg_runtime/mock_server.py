from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
from threading import Lock, Thread
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

from core.bootstrap import bootstrap
from core.extension_manager import ExtensionManager
from utils.fs_manager import FileSystemManager

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class MockOrderStore:
    def __init__(self) -> None:
        self._orders: dict[str, dict[str, Any]] = {}
        self._lock = Lock()
        self._counter = 0

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._counter += 1
            order_id = f"ORD-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{self._counter:04d}"
            order = {
                "order_id": order_id,
                "status": "payment_pending",
                "reference": "",
                "created_at": _iso_now(),
                "updated_at": _iso_now(),
                **deepcopy(payload),
            }
            self._orders[order_id] = order
            return deepcopy(order)

    def get(self, order_id: str) -> dict[str, Any] | None:
        with self._lock:
            order = self._orders.get(order_id)
            return deepcopy(order) if order else None

    def update(self, order_id: str, **updates: Any) -> dict[str, Any] | None:
        with self._lock:
            if order_id not in self._orders:
                return None
            self._orders[order_id].update(deepcopy(updates))
            self._orders[order_id]["updated_at"] = _iso_now()
            return deepcopy(self._orders[order_id])


class RuntimeContext:
    def __init__(self, config_path: str, host: str, port: int) -> None:
        self.config_path = config_path
        self.host = host
        self.port = port
        self.config = bootstrap(config_path)
        self.extension_manager = ExtensionManager(self.config, FileSystemManager())
        self.extension_manager.detect_and_load_extensions()
        self.runtime_target = self._resolve_runtime_target()
        self.site_base_url = str(
            self.config.get("site.base_url", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.public_base_url = (
            str(self.runtime_target.get("public_base_url", "")).rstrip("/")
            or f"http://{host}:{port}"
        )
        self.default_provider_name, self.provider_config = self._resolve_payment_provider()
        self.adapter_name = str(self.provider_config.get("adapter", ""))
        adapter_cls = self.extension_manager.runtime_adapter_registry.get(self.adapter_name)
        self.adapter = adapter_cls() if adapter_cls is not None else None

    def _resolve_runtime_target(self) -> dict[str, Any]:
        targets = self.config.get("runtime.targets", [])
        if isinstance(targets, list) and targets:
            first = targets[0]
            if isinstance(first, dict):
                return deepcopy(first)
        return {"name": "commerce-api", "type": "mock_runtime", "public_base_url": ""}

    def _resolve_payment_provider(self) -> tuple[str, dict[str, Any]]:
        payments_cfg = self.config.get("integrations.payments", {})
        if not isinstance(payments_cfg, dict):
            return "", {}
        providers = payments_cfg.get("providers", {})
        if not isinstance(providers, dict):
            return "", {}
        default_name = str(payments_cfg.get("default", "")).strip()
        provider_cfg = providers.get(default_name, {}) if default_name else {}
        if not isinstance(provider_cfg, dict):
            provider_cfg = {}
        return default_name, deepcopy(provider_cfg)

    def get_store_config(self) -> dict[str, Any]:
        store_config = deepcopy(self.provider_config)
        store_config["callback_url"] = f"{self.public_base_url}/payments/callback"
        store_config["gateway_url"] = f"{self.public_base_url}/gateway/mock"
        return store_config

    def create_checkout_session(self, order_input: dict[str, Any], order_store: MockOrderStore) -> dict[str, Any]:
        try:
            quantity = int(order_input.get("quantity", 1) or 1)
        except (TypeError, ValueError):
            quantity = 1

        order = order_store.create(
            {
                "sku": str(order_input.get("sku", "")),
                "title": str(order_input.get("title", "Product")),
                "price": str(order_input.get("price", "")),
                "currency": str(order_input.get("currency", "IRR")),
                "quantity": quantity,
                "variant_id": str(order_input.get("variant_id", "")),
                "variant_label": str(order_input.get("variant_label", "")),
                "success_url": str(
                    order_input.get(
                        "success_url", f"{self.site_base_url}/order-confirmed/"
                    )
                ),
                "failure_url": str(
                    order_input.get(
                        "failure_url", f"{self.site_base_url}/payment-not-completed/"
                    )
                ),
                "status_url": str(
                    order_input.get(
                        "status_url", f"{self.site_base_url}/order-status/"
                    )
                ),
                "provider": self.default_provider_name,
            }
        )

        store_config = self.get_store_config()
        if self.adapter is not None:
            session = self.adapter.create_checkout_session(order, store_config)
        else:
            session = {
                "method": "redirect",
                "gateway_url": store_config["gateway_url"],
                "callback_url": store_config["callback_url"],
            }

        redirect_url = f"{store_config['gateway_url']}?order_id={quote(order['order_id'])}"
        return {
            "order_id": order["order_id"],
            "status": order["status"],
            "redirect_url": redirect_url,
            "provider": self.adapter_name or self.default_provider_name,
            "session": session,
        }

    def verify_callback(
        self,
        order_id: str,
        callback_input: dict[str, Any],
        order_store: MockOrderStore,
    ) -> dict[str, Any] | None:
        order = order_store.get(order_id)
        if order is None:
            return None

        callback_status = str(callback_input.get("status", "")).strip().lower()
        reference = str(callback_input.get("reference", "")).strip()
        authority = reference if callback_status == "paid" else ""

        if self.adapter is not None:
            verification = self.adapter.verify_callback(
                {"authority": authority, **callback_input},
                self.get_store_config(),
            )
            verification_meta = verification.get("metadata", {}) if isinstance(verification, dict) else {}
            verified = bool(
                verification.get("verified")
                if isinstance(verification, dict)
                else False
            ) or bool(
                verification_meta.get("verified")
                if isinstance(verification_meta, dict)
                else False
            )
            reference = str(
                verification.get("reference", reference)
                if isinstance(verification, dict)
                else reference
            )
            if isinstance(verification, dict) and str(verification.get("status", "")).lower() == "error":
                verified = False
        else:
            verified = callback_status == "paid"
            verification = {"verified": verified, "reference": reference}

        if callback_status == "paid" and verified:
            final_status = "paid"
        elif callback_status in {"cancelled", "canceled"}:
            final_status = "cancelled"
        else:
            final_status = "failed"

        return order_store.update(
            order_id,
            status=final_status,
            reference=reference,
            verification=verification,
        )

    def get_public_order_status(
        self, order_id: str, order_store: MockOrderStore
    ) -> dict[str, Any] | None:
        order = order_store.get(order_id)
        if order is None:
            return None
        return {
            "order_id": order["order_id"],
            "status": order.get("status", "payment_pending"),
            "reference": order.get("reference", ""),
            "title": order.get("title", ""),
            "sku": order.get("sku", ""),
            "price": order.get("price", ""),
            "currency": order.get("currency", ""),
            "quantity": order.get("quantity", 1),
            "variant_id": order.get("variant_id", ""),
            "variant_label": order.get("variant_label", ""),
            "provider": order.get("provider", self.default_provider_name),
            "updated_at": order.get("updated_at", ""),
        }


class MockRuntimeHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class,
        *,
        runtime_context: RuntimeContext,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.runtime_context = runtime_context
        self.order_store = MockOrderStore()


class MockRuntimeRequestHandler(BaseHTTPRequestHandler):
    server: MockRuntimeHTTPServer

    def log_message(self, format: str, *args) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if parsed.path.startswith("/orders/"):
            order_id = parsed.path.rsplit("/", 1)[-1]
            payload = self.server.runtime_context.get_public_order_status(
                order_id, self.server.order_store
            )
            if payload is None:
                self._send_json(404, {"error": "order_not_found"})
                return
            self._send_json(200, payload)
            return
        if parsed.path == "/gateway/mock":
            self._handle_gateway_mock(parsed)
            return
        if parsed.path == "/payments/callback":
            self._handle_callback(parsed)
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/checkout/session":
            payload = self._read_json_body()
            if not payload.get("sku"):
                self._send_json(400, {"error": "missing_sku"})
                return
            session = self.server.runtime_context.create_checkout_session(
                payload, self.server.order_store
            )
            self._send_json(200, session)
            return
        self._send_json(404, {"error": "not_found"})

    def _handle_gateway_mock(self, parsed) -> None:
        params = parse_qs(parsed.query)
        order_id = str(params.get("order_id", [""])[0])
        order = self.server.order_store.get(order_id)
        if order is None:
            self._send_html(404, "<h1>Order not found</h1>")
            return

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mock Gateway</title>
  <style>
    body {{ margin: 0; background: #f4e5cf; color: #23180f; font-family: 'Segoe UI', sans-serif; }}
    .shell {{ width: min(100% - 2rem, 48rem); margin: 3rem auto; padding: 2rem; border-radius: 28px; background: #fff8ec; box-shadow: 0 22px 45px rgba(99, 58, 22, 0.12); }}
    h1 {{ margin-top: 0; font-family: Georgia, serif; font-size: 2.4rem; }}
    .meta {{ display: grid; gap: 0.45rem; margin-bottom: 1.5rem; }}
    .meta strong {{ display: inline-block; min-width: 7rem; }}
    .actions {{ display: flex; gap: 0.8rem; flex-wrap: wrap; margin-top: 1.5rem; }}
    .button {{ display: inline-flex; align-items: center; justify-content: center; padding: 0.9rem 1.2rem; border-radius: 999px; border: none; font-weight: 700; cursor: pointer; text-decoration: none; }}
    .button--primary {{ background: #b5531d; color: #fff7ed; }}
    .button--secondary {{ background: #efe2d0; color: #7a3d18; }}
    .hint {{ color: #6f5d4f; }}
  </style>
</head>
<body>
  <main class="shell">
    <p class="hint">Mock gateway screen</p>
    <h1>Approve or cancel this checkout</h1>
    <div class="meta">
      <div><strong>Order</strong> {order['order_id']}</div>
      <div><strong>Product</strong> {order['title']}</div>
      <div><strong>Quantity</strong> {order['quantity']}</div>
      <div><strong>Total</strong> {order['currency']} {order['price']}</div>
      <div><strong>Variant</strong> {order.get('variant_label') or 'Default option'}</div>
    </div>
    <div class="actions">
      <a class="button button--primary" href="/payments/callback?order_id={quote(order['order_id'])}&status=paid&reference=MOCK-{quote(order['order_id'])}">Approve payment</a>
      <a class="button button--secondary" href="/payments/callback?order_id={quote(order['order_id'])}&status=cancelled">Cancel payment</a>
    </div>
  </main>
</body>
</html>"""
        self._send_html(200, html)

    def _handle_callback(self, parsed) -> None:
        params = parse_qs(parsed.query)
        order_id = str(params.get("order_id", [""])[0])
        status = str(params.get("status", ["failed"])[0])
        reference = str(params.get("reference", [""])[0])
        updated_order = self.server.runtime_context.verify_callback(
            order_id,
            {"status": status, "reference": reference},
            self.server.order_store,
        )
        if updated_order is None:
            self._send_json(404, {"error": "order_not_found"})
            return

        if updated_order["status"] == "paid":
            destination = updated_order.get("success_url", "")
        else:
            destination = updated_order.get("failure_url", "")

        separator = "&" if "?" in destination else "?"
        location = (
            f"{destination}{separator}order_id={quote(updated_order['order_id'])}"
            f"&status={quote(updated_order['status'])}"
        )
        if updated_order.get("reference"):
            location += f"&reference={quote(updated_order['reference'])}"
        self.send_response(302)
        self.send_header("Location", location)
        self._send_cors_headers()
        self.end_headers()

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            payload = {}
        return payload if isinstance(payload, dict) else {}

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status_code: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")


def create_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    *,
    config_path: str = "config.yaml",
) -> MockRuntimeHTTPServer:
    runtime_context = RuntimeContext(config_path, host, port)
    return MockRuntimeHTTPServer(
        (host, port), MockRuntimeRequestHandler, runtime_context=runtime_context
    )


def serve_mock_runtime(
    host: str = "127.0.0.1",
    port: int = 8787,
    *,
    config_path: str = "config.yaml",
) -> None:
    server = create_server(host, port, config_path=config_path)
    logger.info("Mock runtime listening on http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping mock runtime.")
    finally:
        server.server_close()


@contextmanager
def run_mock_runtime_in_thread(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    config_path: str = "config.yaml",
):
    server = create_server(host, port, config_path=config_path)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, thread
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
