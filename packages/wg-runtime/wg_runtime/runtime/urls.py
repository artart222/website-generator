from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    CatalogSnapshotAPIView,
    CheckoutSessionAPIView,
    OrderListAPIView,
    PaymentCallbackAPIView,
    PublicOrderStatusAPIView,
)

urlpatterns = [
    path("token/obtain/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("checkout/session", CheckoutSessionAPIView.as_view(), name="checkout-session"),
    path("catalog/snapshot", CatalogSnapshotAPIView.as_view(), name="catalog-snapshot"),
    path("payments/callback", PaymentCallbackAPIView.as_view(), name="payment-callback"),
    path("orders/<str:order_id>", PublicOrderStatusAPIView.as_view(), name="public-order-status"),
    path("staff/orders", OrderListAPIView.as_view(), name="staff-order-list"),
]
