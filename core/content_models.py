from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .page import Page


MODEL_ALIASES: dict[str, str] = {
    "blog": "post",
    "post": "post",
    "page": "page",
    "pages": "page",
    "doc": "doc",
    "docs": "doc",
    "product": "product",
    "shop": "product",
    "category": "category",
    "categories": "category",
    "landing": "landing",
    "event": "event",
    "events": "event",
    "index": "page",
    "home": "page",
}


DEFAULT_MODELS: dict[str, dict[str, Any]] = {
    "page": {
        "fields": {
            "title": {"type": "string", "required": True},
            "slug": {"type": "string"},
            "summary": {"type": "string", "default": ""},
            "description": {"type": "string", "default": ""},
            "layout": {"type": "string", "default": "document"},
            "blocks": {"type": "list", "items_type": "object", "default": []},
            "islands": {"type": "list", "items_type": "object", "default": []},
            "type": {"type": "string", "default": "page"},
        }
    },
    "post": {
        "fields": {
            "title": {"type": "string", "required": True},
            "slug": {"type": "string"},
            "summary": {"type": "string", "default": ""},
            "description": {"type": "string", "default": ""},
            "layout": {"type": "string", "default": "document"},
            "blocks": {"type": "list", "items_type": "object", "default": []},
            "date": {"type": "string"},
            "tags": {"type": "list", "items_type": "string", "default": []},
            "authors": {"type": "list", "items_type": "string", "default": []},
            "type": {"type": "string", "default": "post"},
        }
    },
    "doc": {
        "fields": {
            "title": {"type": "string", "required": True},
            "slug": {"type": "string"},
            "summary": {"type": "string", "default": ""},
            "description": {"type": "string", "default": ""},
            "layout": {"type": "string", "default": "document"},
            "blocks": {"type": "list", "items_type": "object", "default": []},
            "section": {"type": "string", "default": ""},
            "type": {"type": "string", "default": "doc"},
        }
    },
    "product": {
        "fields": {
            "title": {"type": "string", "required": True},
            "slug": {"type": "string"},
            "summary": {"type": "string", "default": ""},
            "description": {"type": "string", "default": ""},
            "sku": {"type": "string", "required": True},
            "price": {"type": "number", "required": True},
            "currency": {"type": "string", "default": "IRR"},
            "availability": {"type": "string", "default": "in_stock"},
            "images": {"type": "list", "items_type": "string", "default": []},
            "variants": {"type": "list", "items_type": "object", "default": []},
            "attributes": {"type": "object", "default": {}},
            "tax_class": {"type": "string", "default": ""},
            "shipping_class": {"type": "string", "default": ""},
            "payment_methods": {"type": "list", "items_type": "string", "default": []},
            "checkout_provider": {"type": "string", "default": ""},
            "layout": {"type": "string", "default": "document"},
            "blocks": {"type": "list", "items_type": "object", "default": []},
            "type": {"type": "string", "default": "product"},
        }
    },
    "category": {
        "fields": {
            "title": {"type": "string", "required": True},
            "slug": {"type": "string"},
            "summary": {"type": "string", "default": ""},
            "description": {"type": "string", "default": ""},
            "layout": {"type": "string", "default": "collection"},
            "blocks": {"type": "list", "items_type": "object", "default": []},
            "type": {"type": "string", "default": "category"},
        }
    },
    "landing": {
        "fields": {
            "title": {"type": "string", "required": True},
            "slug": {"type": "string"},
            "summary": {"type": "string", "default": ""},
            "description": {"type": "string", "default": ""},
            "layout": {"type": "string", "default": "document"},
            "blocks": {"type": "list", "items_type": "object", "default": []},
            "type": {"type": "string", "default": "landing"},
        }
    },
    "event": {
        "fields": {
            "title": {"type": "string", "required": True},
            "slug": {"type": "string"},
            "summary": {"type": "string", "default": ""},
            "description": {"type": "string", "default": ""},
            "layout": {"type": "string", "default": "document"},
            "blocks": {"type": "list", "items_type": "object", "default": []},
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "default": ""},
            "location": {"type": "string", "default": ""},
            "type": {"type": "string", "default": "event"},
        }
    },
}


class ContentModelError(ValueError):
    """Raised when page data fails model validation."""


class ContentModelRegistry:
    """Stores content model definitions and validates pages against them."""

    def __init__(self) -> None:
        self.models: dict[str, dict[str, Any]] = {}

    def register(self, name: str, definition: dict[str, Any], *, source: str = "") -> None:
        normalized_name = self.resolve_name(name) or str(name).strip()
        normalized_definition = self._normalize_definition(normalized_name, definition)
        if normalized_name in self.models:
            normalized_definition = self._merge_definitions(
                self.models[normalized_name], normalized_definition
            )
        if source:
            normalized_definition["source"] = source
        self.models[normalized_name] = normalized_definition

    def register_many(
        self, definitions: dict[str, dict[str, Any]], *, source: str = ""
    ) -> None:
        for name, definition in definitions.items():
            if isinstance(definition, dict):
                self.register(name, definition, source=source)

    def get(self, name: str | None) -> dict[str, Any] | None:
        if not name:
            return None
        resolved_name = self.resolve_name(name) or str(name).strip()
        return deepcopy(self.models.get(resolved_name))

    def resolve_name(self, name: str | None) -> str | None:
        if not name:
            return None
        normalized = str(name).strip()
        alias = MODEL_ALIASES.get(normalized.lower())
        return alias or normalized

    def apply_to_page(self, page: Page) -> str | None:
        model_name = self._resolve_page_model_name(page)
        if not model_name:
            return None

        definition = self.get(model_name)
        if not definition:
            return None

        normalized_metadata = deepcopy(page.metadata)
        errors: list[str] = []

        for field_name, field_definition in definition.get("fields", {}).items():
            has_value = field_name in normalized_metadata and normalized_metadata[field_name] is not None
            if has_value:
                try:
                    normalized_metadata[field_name] = self._normalize_value(
                        normalized_metadata[field_name], field_definition
                    )
                except ContentModelError as exc:
                    errors.append(f"{field_name}: {exc}")
                continue

            if "default" in field_definition:
                normalized_metadata[field_name] = deepcopy(field_definition.get("default"))
                continue

            if field_definition.get("required", False):
                errors.append(f"{field_name}: field is required for model '{model_name}'")

        if errors:
            page.validation_errors = errors
            raise ContentModelError(
                f"Page '{page.source_filepath}' failed validation for model '{model_name}': "
                + "; ".join(errors)
            )

        page.metadata = normalized_metadata
        page.model_name = model_name
        page.model_data = deepcopy(normalized_metadata)
        page.validation_errors = []
        page._populate_attributes()
        return model_name

    def _resolve_page_model_name(self, page: Page) -> str | None:
        if getattr(page, "is_collection_index", False):
            return "page"

        candidates: list[str | None] = [
            page.metadata.get("model") if isinstance(page.metadata, dict) else None,
            page.collection_config.get("model") if isinstance(page.collection_config, dict) else None,
            page.page_type,
            page.collection,
        ]

        for candidate in candidates:
            resolved = self.resolve_name(candidate)
            if resolved and resolved in self.models:
                return resolved

        return "page" if "page" in self.models else None

    def _normalize_definition(self, name: str, definition: dict[str, Any]) -> dict[str, Any]:
        fields = definition.get("fields", {})
        if not isinstance(fields, dict):
            fields = {}

        normalized_fields: dict[str, dict[str, Any]] = {}
        for field_name, raw_field in fields.items():
            if isinstance(raw_field, str):
                field_cfg = {"type": raw_field}
            elif isinstance(raw_field, dict):
                field_cfg = deepcopy(raw_field)
            else:
                field_cfg = {"type": "string", "default": raw_field}

            normalized_field = {
                "type": str(field_cfg.get("type", "string")).lower(),
                "required": bool(field_cfg.get("required", False)),
            }
            if "default" in field_cfg:
                normalized_field["default"] = deepcopy(field_cfg["default"])
            if "items_type" in field_cfg:
                normalized_field["items_type"] = str(field_cfg["items_type"]).lower()

            normalized_fields[str(field_name)] = normalized_field

        return {"name": name, "fields": normalized_fields}

    def _merge_definitions(
        self, base: dict[str, Any], updates: dict[str, Any]
    ) -> dict[str, Any]:
        merged = deepcopy(base)
        merged_fields = merged.setdefault("fields", {})
        for field_name, field_definition in updates.get("fields", {}).items():
            if field_name in merged_fields and isinstance(merged_fields[field_name], dict):
                merged_fields[field_name] = {
                    **merged_fields[field_name],
                    **deepcopy(field_definition),
                }
            else:
                merged_fields[field_name] = deepcopy(field_definition)
        return merged

    def _normalize_value(self, value: Any, field_definition: dict[str, Any]) -> Any:
        field_type = str(field_definition.get("type", "string")).lower()

        if field_type == "string":
            return "" if value is None else str(value)

        if field_type == "number":
            try:
                return float(value)
            except (TypeError, ValueError) as exc:
                raise ContentModelError("must be a number") from exc

        if field_type == "integer":
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise ContentModelError("must be an integer") from exc

        if field_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"true", "1", "yes", "on"}
            return bool(value)

        if field_type == "object":
            if isinstance(value, dict):
                return deepcopy(value)
            raise ContentModelError("must be an object")

        if field_type == "list":
            item_type = str(field_definition.get("items_type", "any")).lower()
            items = value if isinstance(value, list) else [value]
            if item_type == "any":
                return deepcopy(items)
            return [
                self._normalize_value(item, {"type": item_type})
                for item in items
            ]

        return deepcopy(value)
