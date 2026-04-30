from django.urls import path

from .views import CheckoutSessionAPIView, GatewayMockView, PaymentCallbackAPIView, PublicOrderStatusAPIView

urlpatterns = [
    path("checkout/session", CheckoutSessionAPIView.as_view(), name="checkout-session"),
    path("payments/callback", PaymentCallbackAPIView.as_view(), name="payment-callback"),
    path("orders/<str:order_id>", PublicOrderStatusAPIView.as_view(), name="public-order-status"),
    path("gateway/mock", GatewayMockView.as_view(), name="gateway-mock"),
]
