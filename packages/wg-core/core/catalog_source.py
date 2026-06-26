"""Catalog source adapters.

The build needs a product catalog snapshot for ``runtime_catalog`` collections.
The *only* thing the build cares about is the :class:`CatalogSourcePort`
contract (``fetch_snapshot() -> dict | None``); where the data physically comes
from (an HTTP runtime, a local file, an in-memory fake in tests) is an
infrastructure detail. This keeps wg-core independent of the Django runtime.
"""

from __future__ import annotations

import json
from urllib.request import Request, urlopen


class HttpCatalogSource:
    """Fetches a catalog snapshot from an HTTP endpoint (the runtime service)."""

    def __init__(self, url: str, *, timeout: int = 30) -> None:
        self.url = url
        self.timeout = timeout

    def fetch_snapshot(self) -> dict | None:
        request = Request(self.url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - URL is config-controlled
            payload = response.read()
        return json.loads(payload.decode("utf-8"))
