import hashlib
import hmac
from typing import Any

from django.conf import settings
from django.db.models import Prefetch
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .integrations import (
    IntegrationResolutionError,
    apply_payment_callback,
    create_checkout_order,
)
from .models import Order, Product, ProductVariant
from .serializers import (
    CatalogSnapshotSerializer,
    CheckoutSessionInputSerializer,
    OrderStatusSerializer,
)


def _request_base_url(request: Request) -> str:
    return request.build_absolute_uri("/").rstrip("/")


def _callback_signature_is_valid(order_id: str, status: str, reference: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature over the callback parameters.

    Enabled via ``WG_REQUIRE_SIGNED_CALLBACKS``; the shared secret is
    ``WG_PAYMENT_CALLBACK_SECRET``. This closes the forge-a-paid-order hole:
    without a valid signature the callback is rejected.
    """
    secret = getattr(settings, "WG_PAYMENT_CALLBACK_SECRET", "")
    if not secret:
        return False
    message = f"{order_id}:{status}:{reference}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(signature or ""))


def _enforce_callback_signature(order_id: str, status: str, reference: str, signature: str) -> None:
    if not getattr(settings, "WG_REQUIRE_SIGNED_CALLBACKS", False):
        return
    if not _callback_signature_is_valid(order_id, status, reference, signature):
        raise IntegrationResolutionError("Invalid or missing payment callback signature.")


@method_decorator(csrf_exempt, name="dispatch")
class CheckoutSessionAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = CheckoutSessionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order, payment_attempt, redirect_url = create_checkout_order(
                request_base_url=_request_base_url(request),
                validated_data=dict(serializer.validated_data),
            )
        except IntegrationResolutionError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response(
            {
                "order_id": order.order_id,
                "status": "pending"
                if order.status == Order.STATUS_PENDING_PAYMENT
                else order.status,
                "redirect_url": redirect_url,
                "payment_reference": payment_attempt.attempt_id,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentCallbackAPIView(APIView):
    def get(self, request: Request) -> HttpResponseRedirect:
        order_id = request.query_params.get("order_id", "")
        status = request.query_params.get("status", "paid")
        reference = request.query_params.get("reference", "")
        idempotency_key = request.query_params.get("idempotency_key", "")
        signature = request.query_params.get("signature", "")
        order = get_object_or_404(Order, order_id=order_id)
        try:
            _enforce_callback_signature(order_id, status, reference, signature)
            order, _, _ = apply_payment_callback(
                order=order,
                requested_status=status,
                reference=reference,
                idempotency_key=idempotency_key,
            )
        except IntegrationResolutionError as exc:
            destination = order.failure_url or ""
            return HttpResponseRedirect(
                f"{destination}?order_id={order.order_id}&status=failed&error={str(exc)}"
            )

        destination = order.success_url if order.status == Order.STATUS_PAID else order.failure_url
        dest_url = f"{destination}?order_id={order.order_id}&status={order.status}&reference={reference}"
        return HttpResponseRedirect(dest_url)

    def post(self, request: Request) -> Response:
        order_id = request.data.get("order_id", "")
        status = request.data.get("status", "paid")
        reference = request.data.get("reference", "")
        signature = (
            str(request.data.get("signature", "")).strip()
            or str(request.headers.get("X-Signature", "")).strip()
        )
        idempotency_key = (
            str(request.data.get("idempotency_key", "")).strip()
            or str(request.headers.get("Idempotency-Key", "")).strip()
        )
        order = get_object_or_404(Order, order_id=order_id)
        try:
            _enforce_callback_signature(order_id, status, reference, signature)
        except IntegrationResolutionError as exc:
            return Response({"detail": str(exc)}, status=400)
        order, _, _ = apply_payment_callback(
            order=order,
            requested_status=status,
            reference=reference,
            idempotency_key=idempotency_key,
        )
        return Response({"order_id": order.order_id, "status": order.status})


class PublicOrderStatusAPIView(APIView):
    def get(self, request: Request, order_id: str) -> Response:
        order = get_object_or_404(Order, order_id=order_id)
        serializer = OrderStatusSerializer(
            {
                "order_id": order.order_id,
                "status": order.status,
                "subtotal_amount": order.subtotal_amount,
                "tax_amount": order.tax_amount,
                "shipping_amount": order.shipping_amount,
                "total_amount": order.total_amount,
                "currency": order.currency,
                "provider": order.provider,
                "lines": [
                    {
                        "title": line.title,
                        "sku": line.sku,
                        "quantity": line.quantity,
                        "price": line.price,
                        "currency": line.currency,
                    }
                    for line in order.lines.all()
                ],
                "metadata": order.metadata,
            }
        )
        return Response(serializer.data)


class CatalogSnapshotAPIView(APIView):
    def get(self, request: Request) -> Response:
        products = []
        published_variants = Prefetch(
            "variants",
            queryset=ProductVariant.objects.filter(is_published=True),
            to_attr="published_variants",
        )
        product_qs = Product.objects.filter(is_published=True).prefetch_related(
            published_variants
        )
        for product in product_qs:
            variants = []
            for variant in product.published_variants:
                variants.append(
                    {
                        "sku": variant.sku,
                        "label": variant.label,
                        "price": variant.price,
                        "currency": variant.currency,
                        "metadata": variant.metadata,
                    }
                )

            products.append(
                {
                    "id": str(product.id),
                    "name": product.name,
                    "slug": product.slug,
                    "description": product.description,
                    "metadata": product.metadata,
                    "variants": variants,
                }
            )

        serializer = CatalogSnapshotSerializer({"products": products})
        return Response(serializer.data)


class GatewayMockView(APIView):
    """Development-only fake payment gateway.

    Disabled unless ``settings.WG_ENABLE_MOCK_GATEWAY`` (DEBUG by default) is on,
    so it can never run in production. All user-controlled values are HTML-escaped
    to prevent the reflected XSS the original implementation had.
    """

    def get(self, request: Request) -> HttpResponse:
        if not getattr(settings, "WG_ENABLE_MOCK_GATEWAY", False):
            raise Http404("Mock gateway is disabled.")

        order_id = request.query_params.get("order_id", "")
        if not order_id:
            return HttpResponse("Missing order_id", status=400)

        safe_order_id = escape(order_id)
        return HttpResponse(
            f"<html><body>"
            f"<h1>Mock Payment Gateway</h1>"
            f"<p>Order ID: {safe_order_id}</p>"
            f"<a href=\"/payments/callback?order_id={safe_order_id}&status=paid\">Pay</a><br/>"
            f"<a href=\"/payments/callback?order_id={safe_order_id}&status=cancelled\">Cancel</a>"
            f"</body></html>",
            content_type="text/html",
        )
