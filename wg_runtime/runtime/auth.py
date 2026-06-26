"""DRF authentication and permission helpers for the commerce runtime."""

from __future__ import annotations

from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated


class IsStaffUser(BasePermission):
    """Allow only authenticated staff users (admin tooling / JWT clients)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


# Storefront and webhook endpoints opt out of the default authenticated policy.
PUBLIC_STOREFRONT = [AllowAny]
