from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


class CORSMiddleware:
    """Adds CORS headers, scoped to an explicit allow-list outside DEBUG.

    In DEBUG mode any origin is allowed for local convenience. In production the
    response only carries CORS headers when the request ``Origin`` is in
    ``settings.WG_CORS_ALLOWED_ORIGINS`` - it no longer reflects ``*`` to every
    site.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse()
            self._apply_cors(request, response)
            return response

        response = self.get_response(request)
        self._apply_cors(request, response)
        return response

    def _apply_cors(self, request, response: HttpResponse) -> HttpResponse:
        allowed_origin = self._resolve_allowed_origin(request)
        if allowed_origin is None:
            return response
        response["Access-Control-Allow-Origin"] = allowed_origin
        if allowed_origin != "*":
            response["Vary"] = "Origin"
        response["Access-Control-Allow-Headers"] = "Content-Type, Idempotency-Key"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @staticmethod
    def _resolve_allowed_origin(request) -> str | None:
        if getattr(settings, "DEBUG", False):
            return "*"
        origin = request.headers.get("Origin", "")
        allowed = getattr(settings, "WG_CORS_ALLOWED_ORIGINS", [])
        if origin and origin in allowed:
            return origin
        return None
