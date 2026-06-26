"""Presentation helpers (view-model concerns kept out of the domain entity).

Formatting prices for display and choosing a safe share image are presentation
decisions, not properties of the ``Page`` domain entity. Keeping them here lets
``Page`` stay a data-focused model and makes the formatting independently
testable.
"""

from __future__ import annotations

from typing import Any

DEFAULT_SHARE_IMAGE = "/assets/default-share.png"


def format_price_display(value: Any) -> str:
    """Render a price value for human display (thousands separators, etc.)."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"
    if isinstance(value, str):
        return value.strip()
    return str(value)


def safe_image_url(image_value: Any) -> str:
    """Return a usable share-image URL, falling back to a default."""
    if isinstance(image_value, list):
        return str(image_value[0]) if image_value else DEFAULT_SHARE_IMAGE
    if isinstance(image_value, str) and image_value:
        return image_value
    return DEFAULT_SHARE_IMAGE
