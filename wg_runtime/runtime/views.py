import uuid
from decimal import Decimal
from typing import Any

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderLine, PaymentAttempt, Product
from .serializers import (
    CatalogSnapshotSerializer,
    CheckoutSessionInputSerializer,
    OrderStatusSerializer,
)


def _normalize_amount(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _generate_order_id() -> str:
    return uuid.uuid4().hex


def _normalize_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"paid", "success", "completed"}:
        return Order.STATUS_PAID
    if normalized in {"cancelled", "canceled"}:
        return Order.STATUS_CANCELLED
    return Order.STATUS_FAILED


def _create_order(request: Request, validated_data: dict[str, Any]) -> tuple[Order, PaymentAttempt]:
    lines = validated_data.pop("lines")
    success_url = validated_data.pop("success_url", "")
    failure_url = validated_data.pop("failure_url", "")
    status_url = validated_data.pop("status_url", "")

    total_amount = sum(
        _normalize_amount(line.get("price", 0)) * int(line.get("quantity", 1)) for line in lines
    )
    order = Order.objects.create(
        order_id=_generate_order_id(),
        total_amount=total_amount,
        success_url=success_url,
        failure_url=failure_url,
        status_url=status_url,
        **validated_data,
    )

    for line in lines:
        OrderLine.objects.create(
            order=order,
            title=line.get("title", "")[:240],
            sku=line.get("sku", "")[:120],
            quantity=int(line.get("quantity", 1)),
            price=_normalize_amount(line.get("price", 0)),
            currency=line.get("currency", order.currency),
            metadata=line.get("metadata", {}),
        )

    payment_attempt = PaymentAttempt.objects.create(
        order=order,
        provider=order.provider,
        amount=order.total_amount,
        currency=order.currency,
        status=PaymentAttempt.STATUS_PENDING,
    )
    return order, payment_attempt


def _build_redirect_url(request: Request, order: Order) -> str:
    gateway_path = reverse("gateway-mock")
    return request.build_absolute_uri(f"{gateway_path}?order_id={order.order_id}")


def _update_payment_status(order: Order, status: str, reference: str | None = None) -> PaymentAttempt:
    final_status = _normalize_status(status)
    payment_attempt = order.payment_attempts.create(
        provider=order.provider,
        reference=reference or "",
        amount=order.total_amount,
        currency=order.currency,
        status=final_status,
        metadata={"requested_status": status, "reference": reference or ""},
    )
    order.status = final_status
    order.save(update_fields=["status", "updated_at"])
    return payment_attempt


@method_decorator(csrf_exempt, name="dispatch")
class CheckoutSessionAPIView(APIView):
    def post(self, request: Request) -> Response:
        serializer = CheckoutSessionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, payment_attempt = _create_order(request, serializer.validated_data)
        redirect_url = _build_redirect_url(request, order)
        return Response(
            {
                "order_id": order.order_id,
                "status": order.status,
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
        order = get_object_or_404(Order, order_id=order_id)
        _update_payment_status(order, status, reference)
        destination = order.success_url if order.status == Order.STATUS_PAID else order.failure_url
        dest_url = f"{destination}?order_id={order.order_id}&status={order.status}&reference={reference}"
        return HttpResponseRedirect(dest_url)

    def post(self, request: Request) -> Response:
        order_id = request.data.get("order_id", "")
        status = request.data.get("status", "paid")
        reference = request.data.get("reference", "")
        order = get_object_or_404(Order, order_id=order_id)
        _update_payment_status(order, status, reference)
        return Response({"order_id": order.order_id, "status": order.status})


class PublicOrderStatusAPIView(APIView):
    def get(self, request: Request, order_id: str) -> Response:
        order = get_object_or_404(Order, order_id=order_id)
        serializer = OrderStatusSerializer(
            {
                "order_id": order.order_id,
                "status": order.status,
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
        for product in Product.objects.filter(is_published=True).prefetch_related("variants"):
            variants = []
            for variant in product.variants.filter(is_published=True):
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
    def get(self, request: Request) -> HttpResponse:
        order_id = request.query_params.get("order_id", "")
        if not order_id:
            return HttpResponse("Missing order_id", status=400)
        return HttpResponse(
            f"<html><body>"
            f"<h1>Mock Payment Gateway</h1>"
            f"<p>Order ID: {order_id}</p>"
            f"<a href=\"/payments/callback?order_id={order_id}&status=paid\">Pay</a><br/>"
            f"<a href=\"/payments/callback?order_id={order_id}&status=cancelled\">Cancel</a>"
            f"</body></html>",
            content_type="text/html",
        )
